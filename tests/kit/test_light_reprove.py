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
LISTED = ["conductor-example"]  # the trusted verdict authors (brief #1709)


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
    root.mkdir(parents=True)
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
    monkeypatch.setattr(conductor.session, "pages", lambda e: files[int(e.split("/")[-2])])
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
        if endpoint.startswith(f"repos/{REPO}/issues?state=open") and method == "GET":
            return []  # no local-mode record issue (brief #1969)
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
    assert puts == [
        ("PUT", f"repos/{REPO}/pulls/7/update-branch", "-f", f"expected_head_sha={head}")
    ]
    posts = [c for c in stub.calls if c[0] == "POST"]
    assert posts == [
        (
            "POST",
            f"repos/{REPO}/issues/7/comments",
            "-f",
            f"body=Report: {new} {REPORT}\n\nWho: AGK conductor",
        )
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
    state = merge_cleared.judge_carried(root, [verdict(head)], merged, LISTED, "main", shared)
    assert state == ("cleared", "")
    assert merge_cleared.judge([verdict(head)], merged, ["conductor-example"]) == (
        "held",
        "the latest verdict does not clear this head (rule 3)",
    )


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
    allowed = ["someone-else"] if case == "author" else LISTED
    shared = list(session_plan.SHARED_INDEXES)
    state, reason = merge_cleared.judge_carried(
        root, [verdict(on)], merged, allowed, "main", shared
    )
    assert state == "held"
    assert reason


def test_a_verdict_on_the_head_itself_still_clears_as_before(tmp_path):
    root, head, _ = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM})
    shared = list(session_plan.SHARED_INDEXES)
    assert merge_cleared.judge_carried(root, [verdict(head)], head, LISTED, "main", shared) == (
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


# (f) brief #1714: a covered fix list whose only `Final:` lines accept the pull request's own ADRs
# carries to the light merge as a plain clearing verdict does, and its ADRs are still accepted.

ADR = "docs/adr/0999-example.md"
ADR_TEXT = "# ADR-0999\n\n- Status: Proposed\n"


def fix_list(sha: str, login: str = "conductor-example", cid: int = 7, extra: str = "") -> dict:
    body = f"Verdict: fix list {sha}\n\n{extra}Final: {ADR} Proposed -> Accepted\n"
    return {"id": cid, "created_at": "2026-11-22T10:00:00Z", "user": {"login": login},
            "body": body}  # fmt: skip


def adr_world(tmp_path: Path, main_toml: str = BOTTOM) -> tuple[Path, str, str, str]:
    """A pull request that adds ADR and changes agk.toml, the default branch that changes
    agk.toml, and the clean `update-branch` merge: (the checkout, old head, main, merge)."""
    root, head, main = world(tmp_path, {"agk.toml": TOP, ADR: ADR_TEXT}, {"agk.toml": main_toml})
    git(root, "update-ref", "refs/remotes/origin/main", main)
    return root, head, main, update_branch(root, head, main)


def test_a_covered_fix_list_on_the_old_head_carries_to_its_light_merge(tmp_path):
    root, head, _, merged = adr_world(tmp_path)
    shared = list(session_plan.SHARED_INDEXES)
    comments = [fix_list(head)]
    assert merge_cleared.judge(comments, head, ["conductor-example"]) == ("cleared", "")
    assert merge_cleared.judge_carried(
        root, comments, merged, ["conductor-example"], "main", shared
    ) == ("cleared", "")
    assert (
        merge_cleared.carried_from(root, comments, merged, ["conductor-example"], "main", shared)
        == head
    )
    assert merge_cleared.judge_named(root, 1, comments, merged, ["conductor-example"]) == (
        "cleared",
        "",
        head,
    )


def test_the_carried_fix_list_still_accepts_its_adr_in_the_squash(tmp_path, monkeypatch):
    root, head, _, merged = adr_world(tmp_path)
    reads = []

    def status(repo, sha, path, what=""):
        reads.append((sha, path))
        return "Proposed"

    monkeypatch.setattr(merge_cleared, "adr_status", status)
    lines = merge_cleared.acceptance_lines(REPO, merged, fix_list(head, cid=41), head)
    assert lines == ["ADR-0999 Accepted (Final 41)", merge_cleared.MERGED_BY]
    assert reads == [(merged, ADR)]  # the status is read at the new head
    assert merge_cleared.acceptance_lines(REPO, merged, fix_list(head, cid=41)) == []


def test_an_adr_already_accepted_at_the_new_head_holds(tmp_path, monkeypatch):
    root, head, _, merged = adr_world(tmp_path)
    monkeypatch.setattr(merge_cleared, "adr_status", lambda *a, **k: "Accepted")
    with pytest.raises(merge_cleared.Held, match="not Proposed at the head"):
        merge_cleared.acceptance_lines(REPO, merged, fix_list(head), head)


@pytest.mark.parametrize(
    "case", ["numbered", "requirement", "author", "own-file", "conflict", "twice", "later"]
)
def test_a_fix_list_that_is_not_only_adr_finals_or_not_light_never_carries(tmp_path, case):
    head_files, main_files = {"agk.toml": TOP, ADR: ADR_TEXT}, {"agk.toml": BOTTOM}
    if case == "own-file":
        head_files, main_files = {**head_files, SCRIPT: TOP}, {**main_files, SCRIPT: BOTTOM}
    if case == "conflict":
        main_files = {"agk.toml": TOP.replace("the branch", "main")}
    root, head, main = world(tmp_path, head_files, main_files)
    shared = list(session_plan.SHARED_INDEXES)
    if case == "conflict":
        assert session_plan.light_merge(root, head, main, "main", shared) is False
        comments = [fix_list(head)]
        state = merge_cleared.judge_carried(root, comments, main, [], "main", shared)
        assert state[0] == "held"
        return
    merged = update_branch(root, head, main)
    comments = [fix_list(head)]
    allowed = ["conductor-example"]
    if case == "numbered":
        comments = [fix_list(head, extra="1. Fix the example.\n")]
    elif case == "requirement":
        body = f"Verdict: fix list {head}\n\nFinal: docs/requirements.md REQ-057 Draft -> Built\n"
        comments = [{**fix_list(head), "body": body}]
    elif case == "author":
        allowed = ["someone-else"]
    elif case == "twice":
        git(root, "checkout", "-q", "main")
        newer = commit(root, {"docs/example.md": "b\n"}, "main again")
        merged = update_branch(root, merged, newer)
    elif case == "later":
        later = {**fix_list(merged, cid=9), "created_at": "2026-11-22T11:00:00Z"}
        comments = [fix_list(head), {**later, "body": f"Verdict: fix list {merged}\n\n1. Fix.\n"}]
    state, reason = merge_cleared.judge_carried(root, comments, merged, allowed, "main", shared)
    assert state == "held"
    assert reason
    named = merge_cleared.carried_from(root, comments, merged, allowed, "main", shared)
    assert named is None


@pytest.mark.parametrize(
    "indexes, carries",
    [(None, True), ('["kit/manifest.json"]', False), ('["docs/"]', False), ('"agk.toml"', False)],
)
def test_the_carry_reads_flow_shared_indexes_of_the_default_branch(tmp_path, indexes, carries):
    toml = BOTTOM if indexes is None else BOTTOM + f"\n[flow]\nshared_indexes = {indexes}\n"
    root, head, _, merged = adr_world(tmp_path, toml)
    state, reason, named = merge_cleared.judge_named(
        root, 1, [fix_list(head)], merged, ["conductor-example"]
    )
    assert (state == "cleared") is carries
    assert named == (head if carries else merged)
    if not carries:
        assert reason == "the latest verdict does not clear this head (rule 3)"


def test_auto_merge_off_is_refused_before_any_carry_is_read(tmp_path):
    toml = BOTTOM + "\n[flow]\nauto_merge = false\n"
    root, *_ = adr_world(tmp_path, toml)
    with pytest.raises(merge_cleared.Refused, match="setting: flow.auto_merge|auto_merge"):
        merge_cleared.ruled(root)


def test_a_carried_head_in_local_mode_still_needs_its_own_evidence(tmp_path):
    root, head, _, merged = adr_world(tmp_path)
    verdict_ = {**fix_list(head), "body": fix_list(head)["body"]
                + f"Local evidence: {head[:12]} governance passed\n"}  # fmt: skip
    assert (
        merge_cleared.judge_named(root, 1, [verdict_], merged, ["conductor-example"])[0]
        == "cleared"
    )
    with pytest.raises(merge_cleared.Held, match=r"no local evidence for this head \(rule 4\)"):
        merge_cleared.local_evidence(verdict_, [verdict_], merged, [])


def test_a_carried_head_behind_more_than_max_behind_merges_holds(tmp_path):
    root, head, main, merged = adr_world(tmp_path)
    git(root, "checkout", "-q", "main")
    newer = commit(root, {"docs/example.md": "b\n"}, "main again")
    newest = commit(root, {"docs/example.md": "c\n"}, "main once more")
    assert newer != newest
    with pytest.raises(merge_cleared.Held, match="max_behind_merges"):
        merge_cleared.reprove_check(root, newest, merged, 1)


# (g) brief #1969 (ADR-0818, amendment 253): in local mode the light re-prove makes and posts the
# record of the head it made, so the first verdict on that head needs no builder.

EVIDENCE_LINE = "Evidence check: agrees, head {}, record 0123456789ab, governance passed"
RECORD_TEXT = (
    '{{"head": "{}", "result": "passed", "steps": [{{"name": "pr-body", "outcome": "ok"}}]}}'
)
BODY = "Brief: #70\nSummary: An example change.\n"


class LocalStub(Stub):
    """Stub whose update-branch moves `refs/pull/7/head` of ORIGIN to the real merge commit."""

    def __init__(self, origin: Path, head: str, new: str, body=BODY, issues=None, moved=None):
        super().__init__(head, new)
        self.origin, self.body, self.issues, self.moved = origin, body, issues or [], moved
        self.reads = 0

    def __call__(self, endpoint: str, *extra: str, method: str = "GET"):
        if endpoint == f"repos/{REPO}/pulls/7" and method == "GET":
            self.calls.append((method, endpoint, *extra))
            self.reads += 1
            sha = self.moved if self.moved and self.reads > 2 else self.head
            return {"number": 7, "head": {"sha": sha}, "base": {"ref": "main"}, "body": self.body}
        if endpoint.endswith("/update-branch") and method == "PUT":
            git(self.origin, "update-ref", "refs/pull/7/head", self.new)
        if endpoint.startswith(f"repos/{REPO}/issues?state=open") and method == "GET":
            self.calls.append((method, endpoint, *extra))
            return self.issues
        return super().__call__(endpoint, *extra, method=method)


def local_world(tmp_path: Path, execution: str | None = "local", toml: str = ""):
    """An origin whose `main` sets EXECUTION and holds the clean merge commit update-branch makes:
    (the clone, the origin, the head, the merge commit)."""
    line = "" if execution is None else f'execution = "{execution}"\n'
    root, head, main = world(tmp_path, {"agk.toml": TOP}, {"agk.toml": BOTTOM + line + toml})
    merged = update_branch(root, head, main)
    git(root, "update-ref", "refs/heads/merged", merged)
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(root), str(origin))
    git(origin, "update-ref", "refs/pull/7/head", head)
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(origin), str(clone))
    return clone, origin, head, merged


class Runs:
    """The stubbed prepush and evidence runs: each checks it runs in the scratch worktree of the
    new head, and the prepush run writes the record to the clone's shared evidence folder."""

    def __init__(self, clone: Path, new: str, prepush: int = 0, check: str = "agrees"):
        self.clone, self.new, self.prepush, self.check, self.argv = clone, new, prepush, check, []
        self.record = clone / ".git" / "agk-evidence" / f"{new}.json"

    def __call__(self, argv: list[str], cwd: Path) -> tuple[int, str]:
        self.argv.append(argv)
        assert git(cwd, "rev-parse", "HEAD") == self.new
        assert Path(cwd).resolve() != self.clone.resolve()
        if argv[1].endswith("prepush.py"):
            assert argv[2:5] == ["--quick", "--record", "--body"]
            assert Path(argv[5]).read_text(encoding="utf-8").startswith("Brief: #70")
            self.record.parent.mkdir(parents=True, exist_ok=True)
            text = RECORD_TEXT.format(self.new)
            if self.prepush:
                text = text.replace('"pr-body", "outcome": "ok"', '"governance", "outcome": "FAIL"')
            self.record.write_text(text, encoding="utf-8")
            line = f"Evidence: prepush schema 1, head {self.new[:12]}, 1 steps ok, record ab12"
            return self.prepush, line + " in the shared evidence folder\n"
        assert argv[2:4] == ["check", "--head"] and argv[4] == self.new
        line = EVIDENCE_LINE.format(self.new[:12]).replace("agrees", self.check)
        return (0 if self.check == "agrees" else 1), f"evidence: one note\n{line}\n"


def local_stubbed(monkeypatch, stub, runs, gitleaks: bool = True) -> None:
    stubbed(monkeypatch, stub)
    monkeypatch.setattr(conductor, "reprove_run", runs)
    monkeypatch.setattr(conductor.shutil, "which", lambda name: "/bin/x" if gitleaks else None)


def posted(stub) -> list[str]:
    return [c[-1] for c in stub.calls if c[0] == "POST"]


def no_worktree(clone: Path) -> None:
    assert len(git(clone, "worktree", "list").splitlines()) == 1
    assert not (clone / ".git" / "agk" / "reprove-7").exists()


def test_local_mode_posts_the_record_and_the_local_evidence_line(tmp_path, monkeypatch, capsys):
    clone, origin, head, new = local_world(tmp_path)
    stub, runs = LocalStub(origin, head, new), Runs(clone, new)
    local_stubbed(monkeypatch, stub, runs)
    assert conductor.main(["reprove", "--pr", "7", "--apply"], clone) == 0
    [body] = posted(stub)
    check = EVIDENCE_LINE.format(new[:12])
    local = f"Local evidence: {new} {check} (the conductor's light re-prove record)"
    assert body.startswith(f"body=Report: {new} {REPORT}\n\nEvidence: prepush schema 1, head")
    assert f"\n{local}\n" in body
    assert f"```json\n{RECORD_TEXT.format(new)}\n```" in body
    assert local in capsys.readouterr().out
    assert [a[1].rsplit("/", 1)[-1] for a in runs.argv] == ["prepush.py", "evidence.py"]
    no_worktree(clone)
    verdict_ = {**verdict(new), "body": f"Verdict: cleared {new}\n\n{local}\n"}
    merge_cleared.local_evidence(verdict_, [verdict_], new, [])  # the copied line passes
    with pytest.raises(merge_cleared.Held, match="no local evidence"):
        old = {**verdict(head), "body": verdict_["body"].replace(new[:12], head[:12])}
        merge_cleared.local_evidence(old, [old], new, [])


@pytest.mark.parametrize("execution", [None, "hosted", "hybrid", "pool"])
def test_other_modes_post_todays_report_and_run_nothing(tmp_path, monkeypatch, execution):
    clone, origin, head, new = local_world(tmp_path, execution)
    stub, runs = LocalStub(origin, head, new), Runs(clone, new)
    local_stubbed(monkeypatch, stub, runs)
    assert conductor.main(["reprove", "--pr", "7", "--apply"], clone) == 0
    assert posted(stub) == [f"body=Report: {new} {REPORT}\n\nWho: AGK conductor"]
    assert runs.argv == []


def test_the_open_record_issue_takes_the_local_path_in_hosted_mode(tmp_path, monkeypatch):
    clone, origin, head, new = local_world(tmp_path, "hosted")
    issue = {"number": 3, "title": "Local mode since 2026-11-17"}
    stub, runs = LocalStub(origin, head, new, issues=[issue]), Runs(clone, new)
    local_stubbed(monkeypatch, stub, runs)
    assert conductor.main(["reprove", "--pr", "7", "--apply"], clone) == 0
    assert "```json" in posted(stub)[0]


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("step", "prepush step governance"),
        ("gitleaks", "gitleaks"),
        ("deferred", "Secret-scan"),
        ("differs", "evidence differs"),
    ],
)
def test_a_failed_record_posts_none_and_exits_held(tmp_path, monkeypatch, capsys, case, reason):
    clone, origin, head, new = local_world(tmp_path)
    body = BODY + ("Secret-scan: deferred to CI\n" if case == "deferred" else "")
    stub = LocalStub(origin, head, new, body=body)
    check = "differs" if case == "differs" else "agrees"
    runs = Runs(clone, new, prepush=1 if case == "step" else 0, check=check)
    local_stubbed(monkeypatch, stub, runs, gitleaks=case != "gitleaks")
    assert conductor.main(["reprove", "--pr", "7", "--apply"], clone) == 3
    [text] = posted(stub)
    assert text.startswith(f"body=Report: {new} {REPORT}\n")
    assert "Local evidence: none (" in text and reason in text
    assert "```json" not in text and f"Local evidence: {new}" not in text
    if case in ("gitleaks", "deferred"):
        assert runs.argv == []
    no_worktree(clone)


def test_a_head_that_moves_again_posts_nothing(tmp_path, monkeypatch, capsys):
    clone, origin, head, new = local_world(tmp_path)
    stub = LocalStub(origin, head, new, moved="d" * 40)
    local_stubbed(monkeypatch, stub, Runs(clone, new))
    stub.reads = -10  # the update's own reads see NEW; the read after the record sees D
    monkeypatch.setattr(conductor, "REPROVE_WAITS", 1)

    def moved_after_record(argv, cwd):
        stub.reads = 99
        return Runs(clone, new)(argv, cwd)

    monkeypatch.setattr(conductor, "reprove_run", moved_after_record)
    assert conductor.main(["reprove", "--pr", "7", "--apply"], clone) == 3
    assert posted(stub) == []
    assert "head moved" in capsys.readouterr().out
    no_worktree(clone)


def test_paused_updates_nothing(tmp_path, monkeypatch, capsys):
    clone, origin, head, new = local_world(tmp_path)
    stub = LocalStub(origin, head, new)
    local_stubbed(monkeypatch, stub, Runs(clone, new))
    monkeypatch.setattr(conductor.session, "paused_default", lambda root: True)
    assert conductor.main(["reprove", "--pr", "7", "--apply"], clone) == 0
    assert all(c[0] == "GET" for c in stub.calls)
    assert "reprove: agk paused; nothing updated" in capsys.readouterr().out


def test_a_malformed_execution_is_refused_before_the_update(tmp_path, monkeypatch, capsys):
    clone, origin, head, new = local_world(tmp_path, "cloudy")
    stub = LocalStub(origin, head, new)
    local_stubbed(monkeypatch, stub, Runs(clone, new))
    assert conductor.main(["reprove", "--pr", "7", "--apply"], clone) == 1
    assert all(c[0] == "GET" for c in stub.calls)
    err = capsys.readouterr().err
    assert "(setting: execution in agk.toml)" in err and "cloudy" not in err


def test_personal_mode_is_refused_naming_forge_before_any_read(tmp_path, monkeypatch, capsys):
    clone, origin, head, new = local_world(tmp_path)
    (clone / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    stub = LocalStub(origin, head, new)
    local_stubbed(monkeypatch, stub, Runs(clone, new))
    assert conductor.main(["reprove", "--pr", "7", "--apply"], clone) == 1
    assert stub.calls == []
    assert "(setting: forge)" in capsys.readouterr().err


def test_the_conductor_agent_text_names_the_light_re_prove_record():
    text = (SCRIPTS.parents[1] / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    local = next(p for p in text.split("\n\n") if p.startswith("Local mode."))
    assert (
        "the builder's `Local evidence:` line, or on your light re-prove's head that `Report:`'s"
        in local
    )


def test_reprove_is_the_one_place_the_conductor_makes_a_head():
    call = '/update-branch"'  # the endpoint string a PUT goes to; merge_cleared only names it
    found = sorted(p.name for p in SCRIPTS.glob("*.py") if call in p.read_text("utf-8"))
    assert found == ["conductor.py"]
