"""The watchdog keeps builders alive, one session per name (brief #1355, ADR-0568).

REQ-050. Both adapters write `<worktree>/.agk-session-pid` before a session's first turn;
`launch.py` reads a session as `ended`, `live` or `idle`, refuses to start a second session of a
name whose process is still there, and `conductor.py watchdog` restarts an ended or idle builder
once an hour at most, never one that is parked or handed over. The process table and the clock
are test doubles, the adapter is a recording double and `gh` is the stub: no terminal, no
process is stopped, no network.
"""

from __future__ import annotations

import hashlib
import subprocess  # nosec B404 - fixed argument lists only, no shell
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_conductor_watchdog import (  # noqa: F401
    ROOT,
    marker,
    posix,
    start_posix,
    starts,
    stub,
    world,
)
from test_session import REPO, comment, iso

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
SILENT = 30


def at(minutes: int) -> datetime:
    return NOW - timedelta(minutes=minutes)


# --- answer 1: the three states of a session -----------------------------------------------


@pytest.mark.parametrize(
    "alive, exited, own, owed, has_pr, state",
    [
        (False, False, at(5), None, True, "ended"),  # the process is gone
        (True, True, at(5), None, True, "ended"),  # the exit file is newer than the record
        (True, False, at(5), None, False, "live"),  # posted or pushed within silent_minutes
        (True, False, at(45), None, False, "idle"),  # nothing since the take for 45 minutes
        (True, False, at(90), None, True, "live"),  # its own Report: is newest: it waits
        (True, False, at(90), at(40), True, "idle"),  # a verdict 40 minutes old, no move since
        (True, False, at(90), at(10), True, "live"),  # a verdict 10 minutes old: not yet
        (True, False, at(5), at(40), True, "live"),  # it moved after the verdict
    ],
)
def test_each_state_of_a_session(alive, exited, own, owed, has_pr, state):
    """REQ-050: brief #1355 answer 1 (a fake process table and a fake clock)."""
    import conductor

    assert conductor.builder_state(alive, exited, own, owed, NOW, SILENT, has_pr) == state


def write_record(worktree: Path, session: str, pid: int, started: str, brief: int = 7) -> None:
    worktree.mkdir(parents=True, exist_ok=True)
    text = f"session={session}\npid={pid}\nstarted_utc={started}\nbrief={brief}\n"
    (worktree / ".agk-session-pid").write_text(text, encoding="utf-8")


def test_the_record_and_the_exit_file_are_read(tmp_path):
    """REQ-050: brief #1355 answer 1 (the record's fields; the exit file decides `exited`)."""
    import launch

    write_record(tmp_path, "b1", 4242, "2026-11-15T10:00:00Z")
    record = launch.read_record(tmp_path)
    assert record == {
        "session": "b1",
        "pid": 4242,
        "started_utc": "2026-11-15T10:00:00Z",
        "brief": 7,
    }
    assert launch.exited(tmp_path, record) is False
    (tmp_path / ".agk-session-exit").write_text(
        "exit_code=0\nended_utc=2026-11-15T09:00:00Z\n", encoding="utf-8"
    )
    assert launch.exited(tmp_path, record) is False  # an exit file of the earlier start
    (tmp_path / ".agk-session-exit").write_text(
        "exit_code=1\nended_utc=2026-11-15T11:00:00Z\n", encoding="utf-8"
    )
    assert launch.exited(tmp_path, record) is True
    assert launch.read_record(tmp_path / "none") is None
    (tmp_path / ".agk-session-pid").write_text("pid=x\n", encoding="utf-8")
    assert launch.read_record(tmp_path) is None  # a record that cannot be read is no record


# --- answer 2: restart, leave and hold ------------------------------------------------------


@pytest.mark.parametrize(
    "state, facts, action",
    [
        ("live", {}, ("left", None)),
        ("ended", {}, ("restart", None)),
        ("idle", {}, ("restart", None)),
        ("ended", {"parked": True}, ("left", "parked")),
        ("idle", {"final": True}, ("left", "final report")),
        ("ended", {"recent": True}, ("held", "restarted within the hour")),
        ("idle", {"safe": False}, ("held", "unpushed work")),
        ("ended", {"safe": False}, ("restart", None)),  # an ended one is never stopped
        ("ended", {"room": False}, ("held", "no room: max_builders or builder_memory_gb")),
    ],
)
def test_the_action_for_each_state(state, facts, action):
    """REQ-050: brief #1355 answers 2 and 3 (parked and final are never restarted; one an hour)."""
    import conductor

    given = {"final": False, "parked": False, "recent": False, "room": True, "safe": True}
    assert conductor.builder_action(state, **{**given, **facts}) == action


# --- answer 3: one session per name ---------------------------------------------------------


def test_launch_refuses_a_second_session_of_one_name(tmp_path, monkeypatch, capsys):
    """REQ-050: brief #1355 answer 3 (the record shows a live process: no adapter call)."""
    import launch

    root = tmp_path / "proj"
    root.mkdir()
    name = "b-" + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:8]
    write_record(tmp_path / f"agk-{name}", name, 4242, "2026-11-15T10:00:00Z")
    monkeypatch.setattr(launch, "process_alive", lambda pid: pid == 4242)
    calls = tmp_path / "calls.txt"
    adapter = f"python3 -c \"open({str(calls)!r}, 'a').write('x')\""
    code = launch.start_with(adapter, [(name, 7, None)], root=root)
    err = capsys.readouterr().err
    assert code == 1 and not calls.exists()
    assert f"session {name} is still running (one session per name)" in err
    assert str(tmp_path) not in err  # the session is named, never a path
    monkeypatch.setattr(launch, "process_alive", lambda pid: False)
    assert launch.start_with(adapter, [(name, 7, None)], root=root) == 0
    assert calls.read_text(encoding="utf-8") == "x"


def git(where: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=where, check=True, capture_output=True, text=True
    ).stdout


def test_a_worktree_is_safe_to_stop_only_when_clean_and_pushed(tmp_path):
    """REQ-050: brief #1355 answer 3 (nothing to lose: clean, and every commit on a remote)."""
    import conductor

    origin, work = tmp_path / "origin.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    for args in (
        ["config", "user.email", "t@example.invalid"],
        ["config", "user.name", "t"],
        ["config", "commit.gpgsign", "false"],
        ["commit", "-q", "--allow-empty", "-m", "first"],
        ["push", "-q", "origin", "HEAD:main"],
    ):
        git(work, *args)
    assert conductor.worktree_safe(work) is True
    (work / "notes.txt").write_text("work\n", encoding="utf-8")
    assert conductor.worktree_safe(work) is False  # a change not committed
    (work / "notes.txt").unlink()
    git(work, "commit", "-q", "--allow-empty", "-m", "second")
    assert conductor.worktree_safe(work) is False  # a commit not pushed
    assert conductor.worktree_safe(tmp_path / "missing") is False


def test_stopping_names_only_the_recorded_process_tree(monkeypatch):
    """REQ-050: brief #1355 answer 3 (the one new action: the record's process and its children)."""
    import launch

    table = "  10     1\n  11    10\n  12    11\n  13     1\n"
    seen: list = []

    def run(words, **_):
        seen.append(words)
        return subprocess.CompletedProcess(words, 0, stdout=table if words[0] == "ps" else "")

    killed: list = []
    monkeypatch.setattr(launch.os, "kill", lambda pid, sig: killed.append(pid))
    launch.stop_tree(10, run=run, platform="linux")
    assert sorted(killed) == [10, 11, 12]  # never 13, which the record does not name
    seen.clear()
    launch.stop_tree(10, run=run, platform="win32")
    assert seen == [["taskkill", "/PID", "10", "/T", "/F"]]


# --- the pass in the recorded double ----------------------------------------------------------


@pytest.fixture
def builders(world, tmp_path, monkeypatch):  # noqa: F811
    """One builder session `name` with a record in its worktree beside the checkout, a live take
    of brief #7 and an open pull request #70; the process table is a double."""
    import launch

    name = "b-" + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:8]
    worktree = world["repo"].root.parent / f"agk-{name}"
    write_record(worktree, name, 4242, iso(timedelta(hours=-3)))
    table = {4242: True}
    monkeypatch.setattr(launch, "process_alive", lambda pid: table.get(pid, False))
    stopped: list = []
    monkeypatch.setattr(launch, "stop_tree", lambda pid, **_: (stopped.append(pid), table.pop(pid)))
    import conductor

    monkeypatch.setattr(conductor, "worktree_safe", lambda path: True)
    double = world["stub"]
    double.serve(f"repos/{REPO}/issues/61/comments", [marker(3)])  # a live conductor holds it
    double.serve(
        f"repos/{REPO}/issues/7/comments",
        [comment(1, "builder", f"taken: {name} 2026-11-15", iso(timedelta(hours=-3)))],
    )
    head = {"sha": "a" * 40, "ref": "claude/brief-7"}
    double.serve(
        f"repos/{REPO}/pulls",
        [{"number": 70, "state": "open", "body": "Brief: #7", "head": head, "labels": [],
          "user": {"login": "builder"}, "created_at": iso(timedelta(hours=-2))}],
    )  # fmt: skip
    double.serve(
        f"repos/{REPO}/commits/{'a' * 40}",
        {"commit": {"committer": {"date": iso(timedelta(hours=-2))}}},
    )
    yield {**world, "name": name, "worktree": worktree, "table": table, "stopped": stopped}
    import shutil

    shutil.rmtree(worktree, ignore_errors=True)


def pr_comments(builders, *found: dict) -> None:
    builders["stub"].serve(f"repos/{REPO}/issues/70/comments", list(found))


def watchdog(builders, capsys) -> tuple[int, str]:
    import conductor

    code = conductor.main(["watchdog"], root=builders["repo"].root)
    return code, capsys.readouterr().out


def builder_line(out: str) -> str:
    return next(x for x in out.splitlines() if x.startswith("watchdog: builder "))


def test_an_ended_builder_is_restarted_once_under_its_name(builders, capsys):
    """REQ-050: brief #1355 answer 2 (ended -> restarted with the resume prompt; posts nothing)."""
    builders["table"].clear()
    pr_comments(builders, comment(2, "builder", "Report: aaaaaaa ready for review", iso()))
    code, out = watchdog(builders, capsys)
    name = builders["name"]
    assert code == 0
    assert builder_line(out) == f"watchdog: builder {name} #7 ended -> restarted"
    got = starts(builders)
    assert len(got) == 1 and got[0]["AGK_SESSION"] == name and got[0]["AGK_BRIEF"] == "7"
    assert "resume --pr 70" in got[0]["prompt"]
    assert [c for c in builders["stub"].calls() if c[0] != "GET"] == []
    # a second need within the hour is held, and the next sweep names it
    code, out = watchdog(builders, capsys)
    assert (
        builder_line(out)
        == f"watchdog: builder {name} #7 ended -> held (restarted within the hour)"
    )
    assert len(starts(builders)) == 1
    import conductor

    assert conductor.held_builder_lines(builders["repo"].root) == [
        f"NEEDS-YOU: builder {name} #7 held (restarted within the hour)"
    ]


def test_an_idle_builder_is_stopped_then_restarted(builders, capsys):
    """REQ-050: brief #1355 answers 2 and 5 (a verdict waits 40 minutes with no move)."""
    pr_comments(
        builders,
        comment(2, "builder", "Report: aaaaaaa ready for review", iso(timedelta(hours=-1))),
        comment(3, "boss", "Verdict: fix list aaaaaaa", iso(timedelta(minutes=-40))),
    )
    code, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 idle -> restarted"
    assert builders["stopped"] == [4242] and len(starts(builders)) == 1


def test_an_idle_builder_with_unpushed_work_is_held(builders, capsys, monkeypatch):
    """REQ-050: brief #1355 answer 3 (nothing is stopped while work could be lost)."""
    import conductor

    monkeypatch.setattr(conductor, "worktree_safe", lambda path: False)
    pr_comments(
        builders, comment(3, "boss", "Verdict: fix list aaaaaaa", iso(timedelta(minutes=-40)))
    )
    _, out = watchdog(builders, capsys)
    assert (
        builder_line(out) == f"watchdog: builder {builders['name']} #7 idle -> held (unpushed work)"
    )
    assert builders["stopped"] == [] and starts(builders) == []


def test_a_live_builder_waiting_on_a_review_is_left(builders, capsys):
    """REQ-050: brief #1355 answer 2 (its own Report: is newest: it waits on someone else)."""
    pr_comments(
        builders,
        comment(2, "builder", "Report: aaaaaaa ready for review", iso(timedelta(hours=-2))),
    )
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 live -> left"
    assert starts(builders) == [] and builders["stopped"] == []


@pytest.mark.parametrize(
    "found, labels, why",
    [
        (comment(2, "builder", "Report: aaaaaaa handing over: done", iso()), [], "final report"),
        (
            comment(2, "builder", "Report: aaaaaaa ready for review", iso()),
            ["agk:parked"],
            "parked",
        ),
    ],
)
def test_a_parked_or_handed_over_builder_is_never_restarted(builders, capsys, found, labels, why):
    """REQ-050: brief #1355 answer 2 (the owner's wait and a final Report:)."""
    builders["table"].clear()
    pr_comments(builders, found)
    head = {"sha": "a" * 40, "ref": "claude/brief-7"}
    builders["stub"].serve(
        f"repos/{REPO}/pulls",
        [{"number": 70, "state": "open", "body": "Brief: #7", "head": head,
          "labels": [{"name": x} for x in labels], "user": {"login": "builder"},
          "created_at": iso()}],
    )  # fmt: skip
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 ended -> left ({why})"
    assert starts(builders) == []


def test_a_session_without_a_live_take_is_not_this_watchdogs(builders, capsys):
    """REQ-050: brief #1355 answer 2 (only live takes; a released one is left without a line)."""
    builders["table"].clear()
    name = builders["name"]
    builders["stub"].serve(
        f"repos/{REPO}/issues/7/comments",
        [comment(1, "builder", f"taken: {name} 2026-11-15", iso(timedelta(hours=-3))),
         comment(2, "builder", f"released: {name}", iso(timedelta(hours=-1)))],
    )  # fmt: skip
    pr_comments(builders)
    builders["stub"].serve(f"repos/{REPO}/pulls", [])
    _, out = watchdog(builders, capsys)
    assert not any(x.startswith("watchdog: builder ") for x in out.splitlines())
    assert starts(builders) == []


def test_no_output_names_a_path(builders, capsys):
    """REQ-050: brief #1355 answer 7 (no path, token or login value in what the pass prints)."""
    builders["table"].clear()
    pr_comments(builders)
    _, out = watchdog(builders, capsys)
    assert str(builders["worktree"]) not in out and str(builders["repo"].root) not in out


# --- answer 1: the adapters write the record --------------------------------------------------


def test_the_posix_adapter_writes_the_process_record_and_keeps_it_out_of_git(posix):  # noqa: F811
    """REQ-050: brief #1355 answer 1 (the record is written before claude starts)."""
    posix["env"]["AGK_BRIEF"] = "7"
    done = start_posix(posix)
    assert done.returncode == 0, done.stderr
    record = posix["worktree"] / ".agk-session-pid"
    for _ in range(300):
        if (posix["worktree"] / ".agk-session-exit").exists():
            break
        import time

        time.sleep(0.1)
    lines = record.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "session=builder-x" and lines[3] == "brief=7"
    assert lines[1].startswith("pid=") and lines[1][4:].isdigit()
    assert lines[2].startswith("started_utc=")
    assert git(posix["worktree"], "status", "--porcelain", "--untracked-files=all") == ""


def test_the_windows_adapter_writes_the_process_record():
    """REQ-050: brief #1355 answer 1 (no PowerShell runs here: the template's lines)."""
    text = (ROOT / "kit" / "templates" / "start-session-windows.ps1").read_text(encoding="utf-8")
    assert ".agk-session-pid" in text and "session=$Session" in text and "pid=$PID" in text
    assert "\\.agk-session-(exit|pid)$" in text  # the reuse check ignores both files


def test_the_guide_names_the_record_and_the_install(tmp_path):
    """REQ-050: brief #1355 answer 6."""
    text = (ROOT / "docs" / "guides" / "local-mode.md").read_text(encoding="utf-8")
    assert ".agk-session-pid" in text and "watchdog --install --pass" in text
    assert "keeps builders" in text
