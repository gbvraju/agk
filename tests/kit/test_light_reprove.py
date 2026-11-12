"""A shared-index-only re-prove runs on the checks alone (SPEC-0050 amendment 171, brief #1163).

REQ-057. A pull request whose re-prove files (rule 6) are all shared indexes (rule 3) and whose
merge with the default branch is clean takes the light re-prove: `session_plan.reprove_kind`
says `light`, the sweep marks its line `light`, `conductor.py reprove --pr N --apply` brings the
branch up to date with one `PUT .../update-branch` pinned by `expected_head_sha` and posts the
`Report:` line, and `merge_cleared.py` lets the clearing verdict of the old head carry over to the
merge commit only when that commit adds nothing beyond the default branch's change. Every test
runs on git repositories in `tmp_path` and stubbed REST answers; invented data only, no network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import merge_cleared  # noqa: E402
import session_plan  # noqa: E402

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Example",
    "GIT_AUTHOR_EMAIL": "example@example.com",
    "GIT_COMMITTER_NAME": "Example",
    "GIT_COMMITTER_EMAIL": "example@example.com",
}
LINES = "".join(f"# line {i}\n" for i in range(1, 6))
SCRIPT = "scripts/agk/example.py"
BASE = {"agk.toml": LINES, SCRIPT: LINES, "docs/example.md": "a\n"}
TOP = LINES.replace("line 1", "the branch")  # each side changes its own line: a clean merge
BOTTOM = LINES.replace("line 5", "main")
REPO = "example/agk"
REPORT = "merge of main (light re-prove, SPEC-0050 amendment 171)"


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True,
        env={**os.environ, **GIT_ENV},
    ).stdout.strip()  # fmt: skip


def commit(root: Path, files: dict, message: str) -> str:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def world(tmp_path: Path, head_files: dict, main_files: dict) -> tuple[Path, str, str]:
    """A checkout whose `main` and branch `feature` each change the shared base: (the checkout,
    the branch's head, main's head)."""
    root = tmp_path / "work"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    commit(root, BASE, "base")
    git(root, "checkout", "-q", "-b", "feature")
    head = commit(root, {**head_files, "docs/feature.md": "the feature\n"}, "feature")
    git(root, "checkout", "-q", "main")
    main = commit(root, main_files, "main")
    return root, head, main


def update_branch(root: Path, head: str, main: str, extra: dict | None = None) -> str:
    """The merge commit `update-branch` makes (first parent HEAD, second MAIN), with EXTRA files
    added on top when given: (the merge commit)."""
    git(root, "checkout", "-q", "--detach", head)
    git(root, "merge", "-q", "--no-ff", "--no-edit", main)
    if extra:
        for name, text in extra.items():
            (root / name).write_text(text, encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-q", "--amend", "--no-edit")
    sha = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-q", "main")
    return sha


# (a) to (c): the kind of the re-prove


def test_a_lone_agk_toml_re_prove_with_a_clean_merge_is_light(tmp_path):
    root, head, _ = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    assert session_plan.reprove_state(root, "main", head) == (["agk.toml"], True)
    assert session_plan.reprove_kind(root, "main", head) == ("light", ["agk.toml"])


def test_a_script_the_default_branch_also_changed_makes_it_full(tmp_path):
    root, head, _ = world(
        tmp_path, {"agk.toml": TOP, SCRIPT: TOP}, {"agk.toml": BOTTOM, SCRIPT: BOTTOM}
    )
    assert session_plan.reprove_state(root, "main", head) == (["agk.toml", SCRIPT], False)
    assert session_plan.reprove_kind(root, "main", head) == ("full", ["agk.toml", SCRIPT])


def test_a_conflicting_merge_is_full(tmp_path):
    clash = LINES.replace("line 1", "main")
    root, head, _ = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": clash})
    assert session_plan.reprove_state(root, "main", head) == (["agk.toml"], True)
    assert session_plan.reprove_kind(root, "main", head) == ("conflict", ["agk.toml"])


def test_no_common_file_is_none_and_a_set_list_of_indexes_is_read(tmp_path):
    root, head, _ = world(tmp_path, {"docs/example.md": "b\n"}, {"agk.toml": BOTTOM})
    assert session_plan.reprove_kind(root, "main", head) == ("none", [])
    root2, head2, _ = world(tmp_path / "two", {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    assert session_plan.reprove_state(root2, "main", head2, ["kit/manifest.json"]) == (
        ["agk.toml"],
        False,
    )


def test_an_unreadable_head_is_unknown_never_light(tmp_path):
    root, _, _ = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    assert session_plan.reprove_kind(root, "main", "0" * 40) == (None, [])


# the sweep line


def test_the_sweep_marks_a_shared_index_only_re_prove_light(tmp_path, monkeypatch):
    root, _, _ = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    pulls = [
        {"number": 7, "head": {"sha": "a" * 40}, "body": "Brief: #70"},
        {"number": 8, "head": {"sha": "b" * 40}, "body": "Brief: #80"},
    ]
    files = {7: [{"filename": "agk.toml"}], 8: [{"filename": "agk.toml"}, {"filename": SCRIPT}]}
    main_files = [{"filename": "agk.toml"}, {"filename": SCRIPT}]
    monkeypatch.setattr(
        conductor.session, "pages", lambda e: files[int(e.split("/")[-2])]
    )
    monkeypatch.setattr(
        conductor.session, "gh", lambda e, *a, **k: {"files": main_files, "ahead_by": 0}
    )
    monkeypatch.setattr(conductor, "changed_by", lambda *a: 9)
    lines = conductor.proof_lines(root, REPO, pulls, "main")
    assert "re-prove: #7 agk.toml (changed by #9) light" in lines
    assert "re-prove: #8 agk.toml (changed by #9)" in lines


# (d) conductor.py reprove


class Stub:
    """The REST answers of one pull request #7 whose head moves to NEW after update-branch."""

    def __init__(self, head: str, new: str | None, refuse: bool = False) -> None:
        self.head, self.new, self.refuse, self.calls = head, new, refuse, []

    def __call__(self, endpoint: str, *extra: str, method: str = "GET"):
        self.calls.append((method, endpoint, *extra))
        if endpoint == f"repos/{REPO}/pulls/7" and method == "GET":
            return {"number": 7, "head": {"sha": self.head}, "base": {"ref": "main"}}
        if endpoint.endswith("/update-branch") and method == "PUT":
            if self.refuse:
                return None
            self.head = self.new or self.head
            return {"message": "Updating pull request branch."}
        if endpoint == f"repos/{REPO}/issues/7/comments" and method == "POST":
            return {"id": 1}
        return None


def reprove_world(tmp_path: Path, head_files: dict, main_files: dict):
    """An origin with `main` and `refs/pull/7/head`, and a clone of it: (the clone, the head)."""
    root, head, main = world(tmp_path, head_files, main_files)
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(root), str(origin))
    git(origin, "update-ref", "refs/pull/7/head", head)
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(origin), str(clone))
    return clone, head, main


def stubbed(monkeypatch, stub: Stub) -> None:
    monkeypatch.setattr(conductor.session, "gh", stub)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.time, "sleep", lambda s: None)


def test_reprove_apply_updates_the_branch_pinned_to_the_head_and_posts_the_report(
    tmp_path, monkeypatch, capsys
):
    root, head, _ = reprove_world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    new = "c" * 40
    stub = Stub(head, new)
    stubbed(monkeypatch, stub)
    assert conductor.main(["reprove", "--pr", "7", "--apply"], root) == 0
    puts = [c for c in stub.calls if c[0] == "PUT"]
    assert puts == [("PUT", f"repos/{REPO}/pulls/7/update-branch", "-f", f"expected_head_sha={head}")]
    posts = [c for c in stub.calls if c[0] == "POST"]
    assert posts == [
        ("POST", f"repos/{REPO}/issues/7/comments", "-f", f"body=Report: {new} {REPORT}")
    ]
    assert f"reprove: #7 {head[:12]}: light (agk.toml)" in capsys.readouterr().out


def test_reprove_without_apply_prints_the_update_and_writes_nothing(tmp_path, monkeypatch, capsys):
    root, head, _ = reprove_world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    stub = Stub(head, "c" * 40)
    stubbed(monkeypatch, stub)
    assert conductor.main(["reprove", "--pr", "7"], root) == 0
    assert all(c[0] == "GET" for c in stub.calls)
    out = capsys.readouterr().out
    assert f"PUT repos/{REPO}/pulls/7/update-branch expected_head_sha={head}" in out
    assert "add --apply to do it" in out


@pytest.mark.parametrize(
    ("head_files", "main_files", "why"),
    [
        ({"agk.toml": TOP, SCRIPT: TOP}, {"agk.toml": BOTTOM, SCRIPT: BOTTOM}, SCRIPT),
        ({"agk.toml": TOP}, {"agk.toml": LINES.replace("line 1", "main")}, "conflict"),
    ],
)
def test_reprove_of_a_full_re_prove_updates_nothing(
    tmp_path, monkeypatch, capsys, head_files, main_files, why
):
    root, head, _ = reprove_world(tmp_path, head_files, main_files)
    stub = Stub(head, "c" * 40)
    stubbed(monkeypatch, stub)
    assert conductor.main(["reprove", "--pr", "7", "--apply"], root) == 3
    assert all(c[0] == "GET" for c in stub.calls)
    out = capsys.readouterr().out
    assert "full re-prove" in out and why in out


def test_reprove_refused_by_github_is_an_error_and_posts_nothing(tmp_path, monkeypatch):
    root, head, _ = reprove_world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    stub = Stub(head, None, refuse=True)
    stubbed(monkeypatch, stub)
    assert conductor.main(["reprove", "--pr", "7", "--apply"], root) == 1
    assert not [c for c in stub.calls if c[0] == "POST"]


# (e) the merger's carried verdict


def verdict(sha: str, login: str = "conductor-example") -> dict:
    return {"id": 5, "created_at": "2026-11-12T10:00:00Z", "user": {"login": login},
            "body": f"Verdict: cleared {sha}\n\nAll good."}  # fmt: skip


def test_the_merger_carries_the_verdict_to_a_merge_that_adds_nothing(tmp_path):
    root, head, main = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    merged = update_branch(root, head, main)
    shared = list(session_plan.SHARED_INDEXES)
    assert session_plan.light_merge(root, head, merged, "main", shared)
    state = merge_cleared.judge_carried(root, [verdict(head)], merged, [], "main", shared)
    assert state == ("cleared", "")
    assert merge_cleared.judge(
        [verdict(head)], merged, ["conductor-example"]
    ) == ("held", "the latest verdict does not clear this head (rule 3)")


@pytest.mark.parametrize("case", ["extra", "script", "other-verdict", "author", "not-a-merge"])
def test_the_merger_holds_when_the_merge_adds_anything_or_the_verdict_is_not_the_parents(
    tmp_path, case
):
    head_files, main_files = {"agk.toml": TOP}, {"agk.toml": BOTTOM}
    if case == "script":
        head_files, main_files = {**head_files, SCRIPT: TOP}, {**main_files, SCRIPT: BOTTOM}
    root, head, main = world(tmp_path, head_files, main_files)
    merged = update_branch(root, head, main, {"docs/extra.md": "x\n"} if case == "extra" else None)
    if case == "not-a-merge":
        git(root, "checkout", "-q", "--detach", head)
        merged = commit(root, {"agk.toml": BOTTOM}, "edit")
        git(root, "checkout", "-q", "main")
    on = main if case == "other-verdict" else head
    allowed = ["someone-else"] if case == "author" else []
    shared = list(session_plan.SHARED_INDEXES)
    state, reason = merge_cleared.judge_carried(
        root, [verdict(on)], merged, allowed, "main", shared
    )
    assert state == "held"
    assert reason


def test_a_verdict_on_the_head_itself_still_clears_as_before(tmp_path):
    root, head, _ = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    shared = list(session_plan.SHARED_INDEXES)
    assert merge_cleared.judge_carried(root, [verdict(head)], head, [], "main", shared) == (
        "cleared",
        "",
    )


def test_the_new_test_file_is_mapped_to_the_three_scripts():
    import tomllib

    data = tomllib.loads((SCRIPTS.parents[1] / "agk.toml").read_text(encoding="utf-8"))
    mapped = {
        entry["code"]
        for entry in data["testing"]["map"]
        if "tests/kit/test_light_reprove.py" in entry.get("tests", [])
    }
    assert {
        "scripts/agk/conductor.py",
        "scripts/agk/session_plan.py",
        "scripts/agk/merge_cleared.py",
    } <= mapped
