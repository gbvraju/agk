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
import os
import re
import signal
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
import time
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
    world,
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


# run_governance's first four arguments: the checkout, the worktree, the home, the body file
GOVERN = (Path("checkout"), Path("tree"), Path("home"), Path("home") / "pr-body.md")


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
    # LC_CTYPE is set by the fake make's own Python (PEP 538), not passed by the command
    names = {"PATH", "HOME", "AGK_PR_BODY", "AGK_RECORD_COMMENTS"}  # amendment 122 (brief #601)
    assert set(env) - {"LC_CTYPE"} == names, sorted(env)
    assert HIDDEN not in json.dumps(env)
    assert Path(env["HOME"]) != Path.home()


COVERED_BODY = "Brief: #500\nAdvances: REQ-046\nCovered-by: ADR-0261\n"
NEEDS_BODY = """
import json, os, sys
body = os.environ.get('AGK_PR_BODY')
text = open(body, encoding='utf-8').read() if body and os.path.isfile(body) else None
with open(LOG, 'a', encoding='utf-8') as fh:
    seen = {'args': sys.argv[1:], 'env': dict(os.environ), 'body': text}
    fh.write(json.dumps(seen) + '\\n')
sys.exit(0 if text and 'Covered-by: ADR-0261' in text.splitlines() else 1)
"""


def body_world(tmp_path: Path, body: str):
    """A run whose fake make passes only when AGK_PR_BODY names a file with the Covered-by line,
    as check_protected_changes.py needs for a covered build (brief #576)."""
    root = repo(tmp_path, toml(ON))
    pull = {**world()["pull"], "body": body}
    bin_dir, log = fake_gh(tmp_path, pull=pull, comments=[verdict()])
    log_path = str(tmp_path / "make-calls.jsonl")
    (bin_dir / "make").write_text(
        f"#!{sys.executable}\nLOG = {log_path!r}\n" + NEEDS_BODY, encoding="utf-8"
    )
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    return proc, calls(log), makes(tmp_path), root


def test_a_covered_by_merge_gets_its_body_and_is_not_reported_red(tmp_path):
    """REQ-046 AC6: brief #576 answer 1 (the merged body reaches governance as AGK_PR_BODY)."""
    proc, made, ran, root = body_world(tmp_path, COVERED_BODY)
    assert one_line(proc) == MERGED and proc.returncode == 0, proc.stdout + proc.stderr
    assert red_writes(made) == [], "no red-branch issue"
    assert len(ran) == 1 and ran[0]["body"] == COVERED_BODY
    body_file = Path(ran[0]["env"]["AGK_PR_BODY"])
    assert body_file.parent == Path(ran[0]["env"]["HOME"]), "in the run's temporary home"
    assert not body_file.is_relative_to(root), "outside the checkout"
    assert not body_file.exists(), "removed with the run's temporary folder"


def test_the_body_is_the_one_read_before_the_merge_with_no_second_read(tmp_path):
    """REQ-046 AC6: brief #576 answer 1 (the body already read; change nothing else)."""
    proc, made, ran, _ = body_world(tmp_path, COVERED_BODY)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    pulls = [c for c in made if c[3] == f"repos/{REPO}/pulls/7"]
    assert len(pulls) == 1, made


def test_a_pull_request_with_no_body_gets_an_empty_body_file(tmp_path):
    """REQ-046 AC6: brief #576 answer 1 (a missing body is an empty file; the check decides)."""
    proc, _, ran, _ = body_world(tmp_path, "")
    assert proc.returncode == 1 and one_line(proc) == STOPPED, proc.stdout + proc.stderr
    assert ran[0]["body"] == ""


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
    for word in ("git push", '"push"', '"tag"', "reviews", "Timer(", '"revert"'):
        assert word not in text, word


def test_the_governance_argument_list_is_the_same_on_a_fake_windows_platform(monkeypatch):
    """REQ-046 AC5: SPEC-0039 rules 2 and 6 (one argument list, no shell, on every platform)."""
    seen: list[tuple[list[str], dict]] = []

    def fake_run(argv, **kwargs):
        seen.append((list(argv), kwargs))
        return FakeChild()

    class FakeChild:
        returncode = 0

        def communicate(self):
            return ("", None)

    monkeypatch.setattr(merge_cleared.subprocess, "Popen", fake_run)
    root, tree, home = Path("checkout"), Path("tree"), Path("home")
    body = home / "pr-body.md"
    for platform in ("linux", "win32"):
        monkeypatch.setattr(sys, "platform", platform)
        assert merge_cleared.run_governance(root, tree, home, body, BASE, 1800.0) is None
    assert seen[0][0] == seen[1][0]
    argv = seen[0][0]
    lock_py = str(Path(merge_cleared.__file__).resolve().parent / "lock.py")
    assert argv[:10] == [sys.executable, lock_py, "run", "--name", "heavy", "--session",
                         "merge-cleared", "--timeout", "1800", "--"]  # fmt: skip
    assert argv[10:12] == ["env", "-i"] and argv[12].startswith("PATH=")
    assert argv[13:] == [f"HOME={home}", f"AGK_PR_BODY={body}",
                         f"AGK_RECORD_COMMENTS={home / 'record-comments.json'}", "make", "-C",
                         str(tree), "governance", f"AGK_BASE={BASE}"]  # fmt: skip
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


# --- the fix list on 9782ebb: a run after the merge that cannot finish is red ------------------

NOT_FINISHED = "governance not finished"
LOCK_PY = SCRIPTS / "lock.py"


def in_process(tmp_path: Path, monkeypatch, main: str | None = None, **saved) -> Path:
    """The world of `after_run` for a call of `merge_cleared.main` in this process (so that one
    function can be replaced); the fake `gh` and `make` are found on PATH. The checkout."""
    root = repo(tmp_path, main or toml(ON))
    world = {"issues": [AUTO_ISSUE], **saved}
    bin_dir, _ = fake_gh(tmp_path, comments=[verdict()], **world)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    for name in ("GITHUB_BASE_REF", "AGK_BASE", "CI"):
        monkeypatch.delenv(name, raising=False)
    temp = tmp_path / "temp"
    temp.mkdir()
    for name in ("TMPDIR", "TEMP", "TMP"):
        monkeypatch.setenv(name, str(temp))
    monkeypatch.setattr(tempfile, "tempdir", None)  # read TMPDIR again
    monkeypatch.setattr(merge_cleared, "PAUSE", 0.0)
    return root


def main_in(root: Path, capsys) -> tuple[int, list[str], list[list[str]]]:
    """One in-process run: (the exit code, the standard output lines, the gh calls)."""
    code = merge_cleared.main(["--pr", "7", "--sha", HEAD], root=root)
    lines = capsys.readouterr().out.splitlines()
    return code, lines, calls(root.parent / "gh-calls.jsonl")


def red_body_of(made: list[list[str]]) -> str:
    opened = red_writes(made)
    assert len(opened) == 1, made
    return body_of(opened[0])


def test_the_heavy_lock_wait_is_bounded_by_a_timeout_in_the_argument_list():
    """REQ-046 AC6: fix list item 1 (`lock.py run ... --timeout S`, never an endless wait)."""
    home = Path("home")
    argv = merge_cleared.governance_argv(Path("tree"), home, home / "pr-body.md", BASE, 1800.0)
    cut = argv.index("--")
    assert argv[cut - 2 : cut] == ["--timeout", "1800"]
    assert argv[cut + 1 : cut + 3] == ["env", "-i"]


@pytest.mark.parametrize(
    ("flow", "seconds"),
    [({}, 1800.0), ({"after_merge_timeout": 5}, 300.0), ({"after_merge_timeout": 240}, 14400.0)],
)
def test_after_merge_timeout_is_minutes_and_30_by_default(flow, seconds):
    """REQ-046 AC6: fix list item 1 (`[flow] after_merge_timeout`, 30 minutes by default)."""
    assert merge_cleared.after_merge_seconds({"flow": {**flow}}) == seconds


@pytest.mark.parametrize("value", ["0", "-5", "true", '"30"', "1.5", f'"{HIDDEN}"'])
def test_a_bad_after_merge_timeout_merges_nothing_and_names_the_setting(tmp_path, value):
    """REQ-046 AC6: fix list item 1 (the setting is read before the merge; the value is never
    shown)."""
    main = toml(ON + f"after_merge_timeout = {value}\n")
    proc, made, ran, _ = after_run(tmp_path, main=main)
    line = one_line(proc)
    assert line.startswith(f"merge-cleared #7 {SHA12}: refused: "), line
    assert "after_merge_timeout" in line and HIDDEN not in line and value not in line.split(":")[-1]
    assert proc.returncode == 1
    assert writes(made) == [] and ran == []


def test_the_setting_reaches_the_governance_run(tmp_path, monkeypatch, capsys):
    """REQ-046 AC6: fix list item 1 (the minutes of the default branch, as seconds)."""
    root = in_process(tmp_path, monkeypatch, main=toml(ON + "after_merge_timeout = 5\n"))
    seen: list[float] = []

    def fake(root_, tree, home, body, base, wait):
        seen.append(wait)

    monkeypatch.setattr(merge_cleared, "run_governance", fake)
    code, lines, _ = main_in(root, capsys)
    assert lines == [MERGED] and code == 0
    assert seen == [300.0]


@pytest.mark.parametrize(
    ("code", "step"), [(0, None), (3, "heavy lock"), (2, "make governance"), (1, "make governance")]
)
def test_lock_py_exit_3_is_the_heavy_lock_step(monkeypatch, code, step):
    """REQ-046 AC6: fix list item 1 (`lock.py`'s exit 3, not taken in time, is a failed step)."""

    class Child:
        returncode = code

        def __init__(self, argv, **kwargs):
            assert not kwargs.get("shell")

        def communicate(self):
            return ("out\n", None)

    monkeypatch.setattr(merge_cleared.subprocess, "Popen", Child)
    got = merge_cleared.run_governance(*GOVERN, BASE, 60.0)
    assert got == step


def test_an_interrupt_while_governance_runs_stops_the_child_and_goes_on(monkeypatch):
    """REQ-046 AC6: fix list item 1 (the child is ended, the interrupt reaches the caller)."""
    done: list[str] = []

    class Child:
        returncode = None

        def __init__(self, argv, **kwargs):
            pass

        def communicate(self):
            raise KeyboardInterrupt

        def poll(self):
            return None

        def terminate(self):
            done.append("terminate")

        def wait(self, timeout=None):
            done.append("wait")
            return -15

    monkeypatch.setattr(merge_cleared.subprocess, "Popen", Child)
    with pytest.raises(KeyboardInterrupt):
        merge_cleared.run_governance(*GOVERN, BASE, 60.0)
    assert done[:2] == ["terminate", "wait"]


def hold_heavy(root: Path, locks: Path, temp: Path) -> subprocess.Popen:
    """Another run holding the heavy lock until the test ends it."""
    env = {**os.environ, "TMPDIR": str(temp), "TEMP": str(temp), "TMP": str(temp)}
    holder = subprocess.Popen(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(LOCK_PY), "run", "--name", "heavy", "--session", "holder", "--",
         sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    owner = locks / "agk-lock-heavy" / "owner.json"
    for _ in range(200):
        if owner.exists() and "child" in owner.read_text(encoding="utf-8"):
            return holder
        time.sleep(0.05)
    holder.kill()
    raise AssertionError("the holder never took the heavy lock")


def test_a_heavy_lock_still_busy_at_the_timeout_is_red(tmp_path, monkeypatch, capsys):
    """REQ-046 AC6: fix list item 2 (the heavy lock still busy at the timeout: the red-branch
    issue names `heavy lock`, the stop line, exit 1, make never runs)."""
    locks = tmp_path / "locks"
    root = in_process(tmp_path, monkeypatch, main=f'lock_dir = "{locks.as_posix()}"\n{toml(ON)}')
    monkeypatch.setattr(merge_cleared, "MINUTE", 0.02)  # 30 minutes become 0.6 s here
    holder = hold_heavy(root, locks, tmp_path / "temp")
    try:
        code, lines, made = main_in(root, capsys)
    finally:
        holder.terminate()
        holder.wait(timeout=30)
    assert lines == [STOPPED] and code == 1
    assert "Failing check: heavy lock" in red_body_of(made)
    assert makes(tmp_path) == []
    assert worktrees(root) == [str(root)]


@pytest.mark.parametrize("raised", [KeyboardInterrupt, OSError, RuntimeError, SystemExit])
def test_an_interrupt_or_error_during_the_run_is_red(tmp_path, monkeypatch, capsys, raised):
    """REQ-046 AC6: fix list item 2 (an interrupt during the run: the red-branch issue
    `governance not finished`, the stop line, a non-zero exit, the worktree removed)."""
    root = in_process(tmp_path, monkeypatch)

    def cut(*args):
        raise raised

    monkeypatch.setattr(merge_cleared, "run_governance", cut)
    code, lines, made = main_in(root, capsys)
    assert lines == [STOPPED] and code == 1
    assert f"Failing check: {NOT_FINISHED}" in red_body_of(made)
    assert len([c for c in writes(made) if c[3].endswith("/comments")]) == 1, "still recorded"
    assert worktrees(root) == [str(root)]


def test_a_temporary_folder_that_cannot_be_made_is_red(tmp_path, monkeypatch, capsys):
    """REQ-046 AC6: fix list item 2 (no temporary folder: the red-branch issue, the stop line)."""
    root = in_process(tmp_path, monkeypatch)

    made_by = tempfile.mkdtemp

    def refuse(*args, **kwargs):  # only the folder of the governance run; lock.py's still made
        if str(kwargs.get("prefix", "")).startswith("agk-merge-cleared-"):
            raise OSError(28, "No space left on device")
        return made_by(*args, **kwargs)

    monkeypatch.setattr(merge_cleared.tempfile, "mkdtemp", refuse)
    code, lines, made = main_in(root, capsys)
    assert lines == [STOPPED] and code == 1
    assert f"Failing check: {NOT_FINISHED}" in red_body_of(made)
    assert makes(tmp_path) == []


def test_an_interrupt_with_no_red_issue_written_says_so(tmp_path, monkeypatch, capsys):
    """REQ-046 AC6: fix list item 2 (or the stop line saying the issue cannot be written)."""
    root = in_process(tmp_path, monkeypatch, issue_fails=True)

    def cut(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(merge_cleared, "run_governance", cut)
    code, lines, _ = main_in(root, capsys)
    assert lines == [f"{STOPPED} (the red-branch issue cannot be written)"] and code == 1


def test_an_interrupt_while_the_red_issue_is_written_says_it_cannot_be(
    tmp_path, monkeypatch, capsys
):
    """REQ-046 AC6: fix list item 1 (nothing after the merge escapes as a traceback)."""
    root = in_process(tmp_path, monkeypatch, make_exit=2)

    def cut(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(merge_cleared, "file_red", cut)
    code, lines, _ = main_in(root, capsys)
    assert lines == [f"{STOPPED} (the red-branch issue cannot be written)"] and code == 1


@pytest.mark.skipif(not hasattr(signal, "SIGTERM") or os.name == "nt", reason="POSIX signals")
def test_sigterm_during_the_run_opens_the_red_branch_issue(tmp_path):
    """REQ-046 AC6: fix list items 1 and 2 (SIGTERM while governance waits: the red-branch
    issue, the stop line, exit 1, the heavy lock released and the worktree removed)."""
    locks = tmp_path / "locks"
    root = repo(tmp_path, f'lock_dir = "{locks.as_posix()}"\n{toml(ON)}')
    bin_dir, log = fake_gh(tmp_path, comments=[verdict()])
    started, stop = tmp_path / "make-started", tmp_path / "make-stop"
    (bin_dir / "make").write_text(
        f"#!{sys.executable}\nimport pathlib, time\n"
        f"pathlib.Path({str(started)!r}).write_text('x')\n"
        f"for _ in range(600):\n"
        f"    if pathlib.Path({str(stop)!r}).exists():\n        break\n    time.sleep(0.05)\n",
        encoding="utf-8",
    )
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    temp = tmp_path / "temp"
    temp.mkdir()
    env["TMPDIR"] = env["TEMP"] = env["TMP"] = str(temp)
    proc = subprocess.Popen(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--pr", "7", "--sha", HEAD],
        cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )  # fmt: skip
    try:
        for _ in range(600):
            if started.exists() or proc.poll() is not None:
                break
            time.sleep(0.05)
        assert started.exists(), "governance never started"
        proc.send_signal(signal.SIGTERM)
        out, err = proc.communicate(timeout=60)
    finally:
        stop.write_text("x", encoding="utf-8")
        if proc.poll() is None:
            proc.kill()
    assert out.splitlines() == [STOPPED], out + err
    assert proc.returncode == 1
    assert f"Failing check: {NOT_FINISHED}" in red_body_of(calls(log))
    assert not (locks / "agk-lock-heavy").exists(), "the heavy lock is released"
    assert worktrees(root) == [str(root)]
