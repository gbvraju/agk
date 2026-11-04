"""merge_cleared.py build (c): after the merge, governance under the heavy lock, the red-branch stop
and the record line.

Brief #551, ADR-0273, REQ-046 (SPEC-0039 rule 6 after its first sentence, rule 7, rule 12 (c)).
Every test runs on a git repository in `tmp_path` whose origin is a local bare repository holding
the fixed merge commit, a fake `gh` that answers from saved responses and records its argument
lists, and a fake `make` that records its argument list and environment. No network; invented
logins, addresses at example.com.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_merge_cleared_verdict import (
    AUTO_ISSUE,
    BASE,
    HEAD,
    HIDDEN,
    MERGE,
    MERGE12,
    ON,
    REPO,
    SCRIPT,
    SCRIPTS,
    SHA12,
    calls,
    cleared,
    fake_gh,
    git,
    one_line,
    repo,
    run,
    toml,
)

sys.path.insert(0, str(SCRIPTS))

import merge_cleared  # noqa: E402
import route  # noqa: E402

MERGED = f"merge-cleared #7 {SHA12}: merged {MERGE12}"
STOPPED = "merge-cleared: stopped: default branch red after #7"
RED_TITLE = "The default branch is red"
LOCAL_RECORD = {"number": 40, "title": "Local mode since 2026-11-01", "body": "Actions is blocked."}
RECORD = re.compile(
    rf"Auto merge: #7 {MERGE} \d{{4}}-\d\d-\d\dT\d\d:\d\d:\d\dZ "
    rf"https://github\.com/{REPO}/pull/7#issuecomment-1005"
)


def verdict() -> dict:
    """A cleared verdict for the head with no evidence lines (CI mode, green runs)."""
    return cleared(HEAD, extra="")


def after_run(tmp_path: Path, issues: list | None = None, main: str | None = None, **saved):
    """One run of the command; (the process, the gh calls, the make calls, the checkout)."""
    root = repo(tmp_path, main or toml(ON))
    world = {"issues": [AUTO_ISSUE] if issues is None else issues, **saved}
    bin_dir, log = fake_gh(tmp_path, comments=[verdict()], **world)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    return proc, calls(log), makes(tmp_path), root


def makes(tmp_path: Path) -> list[dict]:
    log = tmp_path / "make-calls.jsonl"
    if not log.exists():
        return []
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]


def writes(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if c[1:3] != ["--method", "GET"]]


def body_of(call: list[str]) -> str:
    return next(a[len("body=") :] for a in call if a.startswith("body="))


def worktrees(root: Path) -> list[str]:
    out = git(root, "worktree", "list", "--porcelain")
    return [x[len("worktree ") :] for x in out.splitlines() if x.startswith("worktree ")]


# --- rule 7: the record line --------------------------------------------------------------------


def test_a_green_run_posts_one_record_line_on_the_auto_merge_issue(tmp_path):
    """REQ-046 AC6: SPEC-0039 rule 7 (one line per merge, on the `agk-auto-merge` issue)."""
    proc, made, _, _ = after_run(tmp_path)
    assert one_line(proc) == MERGED and proc.returncode == 0
    posted = [c for c in writes(made) if c[3].endswith("/comments")]
    assert len(posted) == 1, made
    assert posted[0][:4] == ["api", "--method", "POST", f"repos/{REPO}/issues/41/comments"]
    assert RECORD.fullmatch(body_of(posted[0])), body_of(posted[0])


def test_the_local_mode_record_issue_takes_the_line_while_it_is_open(tmp_path):
    """REQ-046 AC6: SPEC-0039 rule 7 (the local-mode record issue first)."""
    local = cleared(HEAD)  # local evidence for the head
    root = repo(tmp_path, toml(ON))
    bin_dir, log = fake_gh(tmp_path, comments=[local], issues=[LOCAL_RECORD, AUTO_ISSUE])
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == MERGED
    posted = [c for c in writes(calls(log)) if c[3].endswith("/comments")]
    assert [c[3] for c in posted] == [f"repos/{REPO}/issues/40/comments"]


@pytest.mark.parametrize(
    ("name", "issues"),
    [
        ("no record issue", []),
        ("a pull request labelled agk-auto-merge", [{**AUTO_ISSUE, "pull_request": {}}]),
        ("two agk-auto-merge issues", [AUTO_ISSUE, {**AUTO_ISSUE, "number": 42}]),
        ("another label", [{**AUTO_ISSUE, "labels": [{"name": "agk-brief"}]}]),
    ],
)
def test_without_the_one_record_issue_nothing_merges(tmp_path, name, issues):
    """REQ-046 AC6: SPEC-0039 rule 7 (with neither issue open the command merges nothing)."""
    proc, made, ran, _ = after_run(tmp_path, issues=issues)
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: held: no record issue (rule 7)", name
    assert proc.returncode == 3
    assert writes(made) == [] and ran == []


def test_a_record_line_github_refuses_leaves_the_merge_and_exits_1(tmp_path):
    """REQ-046 AC6: SPEC-0039 rule 7 (the merge stands; the line says the record is missing)."""
    proc, made, ran, _ = after_run(tmp_path, comment_fails=True)
    assert one_line(proc) == f"{MERGED}: the record line cannot be posted (rule 7)"
    assert proc.returncode == 1
    assert len(ran) == 1, "governance still runs after the merge"


# --- rule 6: governance after the merge ---------------------------------------------------------


def test_governance_runs_once_on_the_merge_commit_in_a_removed_worktree(tmp_path):
    """REQ-046 AC6: SPEC-0039 rule 6 (`make -C <worktree> governance AGK_BASE=<parent>`)."""
    proc, _, ran, root = after_run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(ran) == 1
    args = ran[0]["args"]
    assert args[0] == "-C" and args[2:] == ["governance", f"AGK_BASE={BASE}"]
    tree = Path(args[1])
    assert not tree.is_relative_to(root), "the worktree is outside the checkout"
    assert not tree.exists(), "the worktree is removed afterwards"
    assert worktrees(root) == [str(root)]
    assert git(root, "rev-parse", "refs/remotes/origin/main").strip() == MERGE, "fetched"


def test_the_governance_run_gets_no_token_and_a_scratch_home(tmp_path, monkeypatch):
    """REQ-046 AC6: SPEC-0039 rule 6 (`env -i PATH=... HOME=<scratch>`: no token reaches it)."""
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "AGK_LOCK_TOKEN", "AGK_SESSION"):
        monkeypatch.setenv(name, HIDDEN)
    proc, _, ran, _ = after_run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    env = ran[0]["env"]
    assert set(env) <= {"PATH", "HOME", "PWD", "MAKELEVEL", "MAKEFLAGS", "MFLAGS"}, sorted(env)
    assert HIDDEN not in json.dumps(env)
    assert Path(env["HOME"]) != Path.home()


def test_the_governance_run_holds_the_heavy_lock(tmp_path):
    """REQ-046 AC6: SPEC-0039 rule 6 (under `lock.py run --name heavy --session merge-cleared`)."""
    locks = tmp_path / "locks"
    main = f'lock_dir = "{locks.as_posix()}"\n{toml(ON)}'
    root = repo(tmp_path, main)
    bin_dir, _ = fake_gh(tmp_path, comments=[verdict()])
    seen = tmp_path / "seen.json"
    probe = (  # a make that reads the heavy lock's owner while it runs
        f"#!{sys.executable}\nimport json, pathlib, sys\n"
        f"owner = pathlib.Path({str(locks / 'agk-lock-heavy' / 'owner.json')!r})\n"
        f"pathlib.Path({str(seen)!r}).write_text(owner.read_text() if owner.exists() else 'null')\n"
    )
    (bin_dir / "make").write_text(probe, encoding="utf-8")
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == MERGED, proc.stdout + proc.stderr
    owner = json.loads(seen.read_text(encoding="utf-8"))
    assert owner and owner["session"] == "merge-cleared"
    assert not (locks / "agk-lock-heavy").exists(), "the lock is released"


# --- rule 6: the red-branch stop ----------------------------------------------------------------


def red_writes(made: list[list[str]]) -> list[list[str]]:
    return [c for c in writes(made) if c[3] == f"repos/{REPO}/issues"]


def test_red_governance_opens_the_red_branch_issue_stops_and_exits_1(tmp_path):
    """REQ-046 AC6: SPEC-0039 rule 6 (the router's issue, the stop line, exit 1, no revert)."""
    proc, made, ran, root = after_run(tmp_path, make_exit=2)
    assert one_line(proc) == STOPPED and proc.returncode == 1
    opened = red_writes(made)
    assert len(opened) == 1, made
    assert f"title={RED_TITLE}" in opened[0] and "labels[]=agk-brief" in opened[0]
    body = body_of(opened[0])
    assert body == route.red_body(
        "make governance", MERGE, f"https://github.com/{REPO}/commit/{MERGE}"
    )
    assert "Priority: 0" in body.splitlines()
    assert not Path(ran[0]["args"][1]).exists() and worktrees(root) == [str(root)]
    record = [c for c in writes(made) if c[3].endswith("/comments")]
    assert len(record) == 1, "the merge is still recorded"
    assert len([c for c in made if "PUT" in c]) == 1, "one merge call"
    assert not any("revert" in a for c in made for a in c)


def test_a_fetch_that_does_not_bring_the_merge_commit_is_red(tmp_path):
    """REQ-046 AC6: SPEC-0039 rule 6 (a run that cannot show green stops merging)."""
    other = "d" * 40
    answer = {"sha": other, "merged": True, "message": "Pull Request successfully merged"}
    proc, made, ran, _ = after_run(tmp_path, merge=answer)
    assert one_line(proc) == STOPPED and proc.returncode == 1
    assert ran == [], "make never runs without the merge commit"
    body = body_of(red_writes(made)[0])
    assert "Failing check: fetch" in body and other in body


def test_an_open_router_red_issue_is_updated_not_duplicated(tmp_path, monkeypatch):
    """REQ-046 AC6: SPEC-0039 rule 6, Q-S0039-6 (one issue, through the router's function)."""
    router_red = {
        "number": 88,
        "title": RED_TITLE,
        "body": "Priority: 0\nAdvances: none\n",
        "user": {"login": "github-actions[bot]"},
    }
    done: list[tuple] = []
    monkeypatch.setattr(merge_cleared, "read_pages", lambda endpoint, what, key=None: [router_red])
    monkeypatch.setattr(
        route, "write", lambda endpoint, *extra, **kw: done.append((endpoint, extra))
    )
    assert merge_cleared.file_red(REPO, "make governance", MERGE) is True
    assert done == [
        (
            f"repos/{REPO}/issues/88",
            (
                "-f",
                "body="
                + route.red_body("make governance", MERGE, merge_cleared.commit_url(REPO, MERGE)),
            ),
        )
    ]


def test_a_red_issue_that_cannot_be_written_is_said(tmp_path):
    """REQ-046 AC6: SPEC-0039 rule 6 (the stop line says the issue is missing; still exit 1)."""
    proc, _, _, _ = after_run(tmp_path, make_exit=1, issue_fails=True)
    assert one_line(proc) == f"{STOPPED} (the red-branch issue cannot be written)"
    assert proc.returncode == 1


def test_the_next_run_is_held_by_the_issue_the_stop_opened(tmp_path):
    """REQ-046 AC6: brief #551 answer 2 (build b's hold meets build c's issue)."""
    proc, made, _, _ = after_run(tmp_path / "first", make_exit=2)
    assert one_line(proc) == STOPPED
    opened = red_writes(made)[0]
    issue = {"number": 95, "title": RED_TITLE, "body": body_of(opened)}
    issue["user"] = {"login": "owner-three"}  # the conductor's login, not the router's
    proc, made, ran, _ = after_run(tmp_path / "second", issues=[issue, AUTO_ISSUE])
    line = one_line(proc)
    assert line == f"merge-cleared #7 {SHA12}: held: the default branch is red (rule 5)"
    assert proc.returncode == 3 and writes(made) == [] and ran == []


# --- what the command never does ----------------------------------------------------------------


def test_the_command_writes_no_file_and_pushes_nothing(tmp_path):
    """REQ-046 AC6: SPEC-0039 rules 7 and 8 (no file of the checkout, no push, no tag)."""
    proc, made, _, root = after_run(tmp_path, make_exit=2)
    assert proc.returncode == 1
    assert git(root, "status", "--porcelain") == ""
    allowed = {("PUT", "merge"), ("POST", "comments"), ("POST", "issues"), ("POST", "labels")}
    for call in writes(made):
        assert (call[2], call[3].rsplit("/", 1)[-1]) in allowed, call
    text = SCRIPT.read_text(encoding="utf-8")
    for word in ("git push", '"push"', '"tag"', "reviews", "Timer(", "revert"):
        assert word not in text, word


def test_the_governance_argument_list_is_the_same_on_a_fake_windows_platform(monkeypatch):
    """REQ-046 AC5: SPEC-0039 rules 2 and 6 (one argument list, no shell, on every platform)."""
    seen: list[tuple[list[str], dict]] = []

    def fake_run(argv, **kwargs):
        seen.append((list(argv), kwargs))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(merge_cleared.subprocess, "run", fake_run)
    root, tree, home = Path("checkout"), Path("tree"), Path("home")
    for platform in ("linux", "win32"):
        monkeypatch.setattr(sys, "platform", platform)
        assert merge_cleared.run_governance(root, tree, home, BASE) is True
    assert seen[0][0] == seen[1][0]
    argv = seen[0][0]
    lock_py = str(Path(merge_cleared.__file__).resolve().parent / "lock.py")
    assert argv[:8] == [sys.executable, lock_py, "run", "--name", "heavy", "--session",
                        "merge-cleared", "--"]  # fmt: skip
    assert argv[8:10] == ["env", "-i"] and argv[10].startswith("PATH=")
    assert argv[11:] == [f"HOME={home}", "make", "-C", str(tree), "governance", f"AGK_BASE={BASE}"]
    assert all(not kwargs.get("shell") for _, kwargs in seen)


# --- route.py: the writer made callable, unchanged --------------------------------------------


class FakeLabels:
    def __init__(self) -> None:
        self.ensured: list[str] = []

    def ensure(self, name: str) -> None:
        self.ensured.append(name)


@pytest.mark.parametrize(
    ("name", "open_red", "expected"),
    [
        ("none open: one POST", [], "POST"),
        ("open with another body: one PATCH", [{"number": 88, "body": "old"}], "PATCH"),
        ("open with the same body: nothing", [{"number": 88, "body": "SAME"}], None),
    ],
)
def test_write_red_opens_or_updates_the_one_issue(monkeypatch, name, open_red, expected):
    """REQ-046 AC6: SPEC-0039 rule 6 (route.py's writer, callable and unchanged)."""
    done: list[tuple] = []
    monkeypatch.setattr(
        route, "write", lambda endpoint, *extra, method, what="": done.append((method, endpoint))
    )
    body = "SAME" if open_red and open_red[0]["body"] == "SAME" else "new body"
    labels = FakeLabels()
    route.write_red(REPO, open_red, body, labels)
    if expected is None:
        assert done == [], name
    elif expected == "POST":
        assert done == [("POST", f"repos/{REPO}/issues")] and labels.ensured == ["agk-brief"]
    else:
        assert done == [("PATCH", f"repos/{REPO}/issues/88")] and labels.ensured == []


def test_route_branch_still_writes_through_the_one_writer():
    """REQ-046 AC6: SPEC-0039 rule 6 (the router calls the same function)."""
    text = (SCRIPTS / "route.py").read_text(encoding="utf-8")
    branch = text.split("def route_branch(", 1)[1].split("\ndef ", 1)[0]
    assert "write_red(repo, open_red, body, labels)" in branch
    assert branch.count("method=") == 1, "only the close of a green branch writes here"
