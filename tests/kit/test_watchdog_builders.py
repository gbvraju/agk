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
IDLE = 60  # `[flow] idle_minutes`, never below `silent_minutes`


def at(minutes: int) -> datetime:
    return NOW - timedelta(minutes=minutes)


# --- answer 1: the three states of a session -----------------------------------------------


@pytest.mark.parametrize(
    "alive, exited, own, owed, has_pr, state",
    [
        (False, False, at(5), None, True, "ended"),  # the process is gone
        (True, True, at(5), None, True, "ended"),  # the exit file is newer than the record
        (True, False, at(5), None, False, "live"),  # posted or pushed within idle_minutes
        (True, False, at(45), None, False, "live"),  # 45 minutes: a heavy step may run that long
        (True, False, at(75), None, False, "idle"),  # nothing since the take for 75 minutes
        (True, False, at(90), None, True, "live"),  # its own Report: is newest: it waits
        (True, False, at(90), at(70), True, "idle"),  # a verdict 70 minutes old, no move since
        (True, False, at(90), at(40), True, "live"),  # a verdict 40 minutes old: not yet
        (True, False, at(5), at(70), True, "live"),  # it moved after the verdict
    ],
)
def test_each_state_of_a_session(alive, exited, own, owed, has_pr, state):
    """REQ-050: brief #1355 answer 1 (a fake process table and a fake clock)."""
    import conductor

    assert conductor.builder_state(alive, exited, own, owed, NOW, IDLE, has_pr) == state


@pytest.mark.parametrize("sign", ["transcript", "commit", "files", "lock"])
def test_any_one_sign_of_work_makes_a_quiet_builder_live(sign):
    """REQ-050: brief #1355 answer 1 as corrected (any one sign of work is `live`)."""
    import conductor

    args = (True, False, at(90), at(70), NOW, IDLE, True)
    assert conductor.builder_state(*args) == "idle"
    assert conductor.builder_state(*args, busy=[sign]) == "live"
    assert conductor.builder_state(False, False, at(5), None, NOW, IDLE, True, busy=[sign]) == (
        "ended"
    )


@pytest.mark.parametrize(
    "flow, minutes", [("", 60), ("idle_minutes = 90\n", 90), ("silent_minutes = 120\n", 120)]
)
def test_idle_minutes_is_never_below_silent_minutes(tmp_path, flow, minutes):
    """REQ-050: brief #1355 answer 1 as corrected (`[flow] idle_minutes`, 60 by default)."""
    import conductor

    (tmp_path / "agk.toml").write_text("[flow]\n" + flow, encoding="utf-8")
    assert conductor.idle_minutes(tmp_path) == minutes


def quiet_worktree(tmp_path: Path) -> Path:
    """A worktree whose only files are the adapter's record, written long ago."""
    import os

    worktree = tmp_path / "agk-b1"
    write_record(worktree, "b1", 4242, "2026-11-15T09:00:00Z")
    old = (NOW - timedelta(hours=3)).timestamp()
    os.utime(worktree / ".agk-session-pid", (old, old))
    return worktree


def signs(tmp_path, monkeypatch, worktree, processes=None) -> list[str]:
    import conductor
    import launch

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(conductor, "lock_base", lambda root: tmp_path / "locks")
    table = processes if processes is not None else {4242: (1, 10), 4243: (4242, 50)}
    record = launch.read_record(worktree)
    return conductor.busy_signs(tmp_path, worktree, record, table, NOW, IDLE)


def test_a_builder_whose_only_sign_is_a_transcript_write_is_live(tmp_path, monkeypatch):
    """REQ-050: brief #1355 answer 7 as corrected (the runtime's transcript was written)."""
    import os

    import conductor

    worktree = quiet_worktree(tmp_path)
    assert signs(tmp_path, monkeypatch, worktree) == []
    folder = conductor.transcript_folder(worktree)
    assert folder.parent == tmp_path / "runtime" / "projects"
    folder.mkdir(parents=True)
    turn = folder / "0000.jsonl"
    turn.write_text("{}\n", encoding="utf-8")
    written = (NOW - timedelta(minutes=20)).timestamp()
    os.utime(turn, (written, written))
    assert signs(tmp_path, monkeypatch, worktree) == ["transcript"]
    stale = (NOW - timedelta(minutes=90)).timestamp()
    os.utime(turn, (stale, stale))
    assert signs(tmp_path, monkeypatch, worktree) == []


def test_a_file_change_in_the_worktree_is_a_sign_of_work(tmp_path, monkeypatch):
    """REQ-050: brief #1355 answer 1 as corrected (a file change; the record files are not)."""
    import os

    worktree = quiet_worktree(tmp_path)
    (worktree / "notes.txt").write_text("x\n", encoding="utf-8")
    written = (NOW - timedelta(minutes=10)).timestamp()
    os.utime(worktree / "notes.txt", (written, written))
    assert signs(tmp_path, monkeypatch, worktree) == ["files"]


def write_lock(tmp_path: Path, session: str, beat_minutes: int, pid: int = 9, now=NOW) -> None:
    import json

    held = tmp_path / "locks" / "agk-lock-heavy"
    held.mkdir(parents=True, exist_ok=True)
    owner = {
        "session": session,
        "pid": pid,
        "started": (now - timedelta(minutes=90)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "beat": (now - timedelta(minutes=beat_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (held / "owner.json").write_text(json.dumps(owner), encoding="utf-8")


def test_a_heavy_step_under_the_lock_is_a_sign_of_work(tmp_path, monkeypatch):
    """REQ-050: brief #1355 answer 1 as corrected (a lock of this session with a fresh heartbeat,
    by its name or by a process of its tree; another session's lock or a stale beat is not)."""
    worktree = quiet_worktree(tmp_path)
    write_lock(tmp_path, "b1", beat_minutes=1)
    assert signs(tmp_path, monkeypatch, worktree) == ["lock"]
    write_lock(tmp_path, "other", beat_minutes=1, pid=4243)  # its tree holds the lock
    assert signs(tmp_path, monkeypatch, worktree) == ["lock"]
    write_lock(tmp_path, "other", beat_minutes=1)
    assert signs(tmp_path, monkeypatch, worktree) == []
    write_lock(tmp_path, "b1", beat_minutes=20)
    assert signs(tmp_path, monkeypatch, worktree) == []


@pytest.mark.parametrize(
    "stdout, platform, table",
    [
        (" 10 1 00:01:02\n 11 10 1-00:00:03\n x y z\n", "linux", {10: (1, 62), 11: (10, 86403)}),
        ("10 1 0:00.70\n", "darwin", {10: (1, 0)}),
        ("10 1 62\r\n11 10 5\r\n", "win32", {10: (1, 62), 11: (10, 5)}),
    ],
)
def test_the_process_table_and_the_trees_cpu_time(stdout, platform, table):
    """REQ-050: brief #1355 answer 1 as corrected (the process tree's CPU seconds)."""
    import launch

    def run(words, **_):
        return subprocess.CompletedProcess(words, 0, stdout=stdout)

    assert launch.process_table(run=run, platform=platform) == table
    assert launch.tree_cpu(10, {**table, 12: (99, 7)}) == {
        p: c for p, (_, c) in table.items()
    }  # never 12, which is not below 10
    failed = subprocess.CompletedProcess([], 1, stdout="")
    assert launch.process_table(run=lambda w, **_: failed, platform=platform) is None


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
    processes = {4242: (1, 10), 4243: (4242, 50)}  # the wrapper and the runtime below it
    monkeypatch.setattr(launch, "process_table", lambda **_: dict(processes))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(conductor, "lock_base", lambda root: tmp_path / "locks")
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
    yield {**world, "name": name, "worktree": worktree, "table": table, "stopped": stopped,
           "processes": processes, "tmp": tmp_path}  # fmt: skip
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
    """REQ-050: brief #1355 answer 2 (ended -> restarted with the resume prompt; posts nothing);
    since brief #1389 (ADR-0586) an ended builder is restarted on its event, here a fix list."""
    builders["table"].clear()
    pr_comments(
        builders,
        comment(2, "builder", "Report: aaaaaaa ready for review", iso(timedelta(hours=-2))),
        comment(3, "boss", "Verdict: fix list aaaaaaa", iso(timedelta(minutes=-30))),
    )
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


def read_before(builders, minutes: int = 6, cpu: dict | None = None) -> None:
    """The first of the two reads, MINUTES ago, with the process tree's CPU seconds CPU."""
    import conductor

    root = builders["repo"].root
    memo = conductor.builder_memo(root)
    seen = cpu if cpu is not None else {"4242": 10, "4243": 50}
    then = datetime.now(UTC) - timedelta(minutes=minutes)
    memo.setdefault("checks", {})[builders["name"]] = {"at": conductor.stamp_of(then), "cpu": seen}
    conductor.keep_builder_memo(root, memo)


def owes_a_verdict(builders, minutes: int = 70) -> None:
    pr_comments(
        builders,
        comment(2, "builder", "Report: aaaaaaa ready for review", iso(timedelta(hours=-2))),
        comment(3, "boss", "Verdict: fix list aaaaaaa", iso(timedelta(minutes=-minutes))),
    )


def test_an_idle_builder_is_stopped_then_restarted(builders, capsys):
    """REQ-050: brief #1355 answers 2, 3 and 5 (a verdict waits 70 minutes with no move, every
    sign is quiet, and two reads 5 minutes apart give the same result)."""
    owes_a_verdict(builders)
    read_before(builders)
    code, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 idle -> restarted"
    assert builders["stopped"] == [4242] and len(starts(builders)) == 1


def test_an_idle_builder_with_unpushed_work_is_held(builders, capsys, monkeypatch):
    """REQ-050: brief #1355 answer 3 (nothing is stopped while work could be lost)."""
    import conductor

    monkeypatch.setattr(conductor, "worktree_safe", lambda path: False)
    owes_a_verdict(builders)
    read_before(builders)
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


def test_a_builder_in_a_90_minute_heavy_step_is_live_and_never_stopped(builders, capsys):
    """REQ-050: brief #1355 answer 7 as corrected (a fresh lock heartbeat, a child process
    running, no post for 90 minutes: `live`, never stopped, never restarted)."""
    owes_a_verdict(builders, minutes=90)
    read_before(builders)
    builders["processes"][4244] = (4243, 900)  # the heavy step's child, still running
    write_lock(builders["tmp"], "other", beat_minutes=1, pid=4244, now=datetime.now(UTC))
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 live -> left"
    assert builders["stopped"] == [] and starts(builders) == []


def test_a_builder_whose_transcript_was_written_is_left(builders, capsys):
    """REQ-050: brief #1355 answer 7 as corrected (its only sign is a transcript write)."""
    import conductor

    owes_a_verdict(builders)
    read_before(builders)
    folder = conductor.transcript_folder(builders["worktree"])
    folder.mkdir(parents=True)
    (folder / "0000.jsonl").write_text("{}\n", encoding="utf-8")
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 live -> left"
    assert builders["stopped"] == []


@pytest.mark.parametrize(
    "before",
    [
        None,  # the first read: a second one is due
        {"minutes": 2},  # too close: two reads are 5 minutes apart
        {"minutes": 45},  # too old to be the same quiet spell
        {"minutes": 6, "cpu": {"4242": 10, "4243": 41}},  # the tree used CPU between the reads
        {"minutes": 6, "cpu": {"4242": 10}},  # a process below it started between the reads
    ],
)
def test_an_idle_stop_needs_two_reads_5_minutes_apart_with_the_same_result(
    builders, capsys, before
):
    """REQ-050: brief #1355 answer 3 as corrected (otherwise `held (working)`, no NEEDS-YOU)."""
    import conductor

    owes_a_verdict(builders)
    if before is not None:
        read_before(builders, **before)
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 idle -> held (working)"
    assert builders["stopped"] == [] and starts(builders) == []
    assert conductor.held_builder_lines(builders["repo"].root) == []
    # this read is kept, so the next pass 5 or more minutes later can stop it
    checks = conductor.builder_memo(builders["repo"].root)["checks"][builders["name"]]
    assert checks["cpu"] == {"4242": 10, "4243": 50}


def test_an_unreadable_process_table_never_stops_a_builder(builders, capsys, monkeypatch):
    """REQ-050: brief #1355 answer 3 as corrected (a read that fails is not a quiet read)."""
    import launch

    monkeypatch.setattr(launch, "process_table", lambda **_: None)
    owes_a_verdict(builders)
    read_before(builders)
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 idle -> held (working)"
    assert builders["stopped"] == []


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
    assert "keeps builders" in text and "idle_minutes" in text and "two reads" in text
