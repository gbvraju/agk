"""One machine runs at most one conductor (brief #1409, ADR-0592).

REQ-050. Before any conductor start (`watchdog`, `watchdog --pass`, `launch.py role conductor`
and the adapters), the kit reads this machine's job records of kind `conductor` and the process
list for a `claude --agent conductor` process; one alive starts nothing. An idle one, found by
its record, is stopped and replaced at most once an hour; a working one is left. Extras already
running are named once by the sweep. No start happens below `[flow] min_free_memory_mb`. The
process lists are recorded doubles for POSIX and Windows, the clock is fixed, a stop is a
recording double: no process is stopped, no network.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
POSIX_PS = (
    "    1     0 /sbin/init\n"
    " 5001     1 /home/u/.local/bin/claude --agent conductor\n"
    " 5002     1 /home/u/.local/bin/claude --agent steward\n"
    " 6000     1 bash -c wrapper agk-session\n"
    " 6001  6000 claude -p build it\n"
)
WINDOWS_CIM = (
    "4 0 System\n"
    '7001 1 "C:\\Users\\u\\.local\\bin\\claude.exe" --agent conductor\n'
    "7002 1 C:\\Windows\\explorer.exe\n"
)


def stamp(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed
    (root / "agk.toml").write_text("[flow]\n", encoding="utf-8")
    return root


def record(tmp_path: Path, name: str, pid: int, started: datetime, kind="conductor") -> Path:
    worktree = tmp_path / f"agk-{name}"
    worktree.mkdir(exist_ok=True)
    text = f"session={name}\npid={pid}\nstarted_utc={stamp(started)}\nbrief=\n"
    text += f"kind={kind}\n" if kind else ""
    (worktree / ".agk-session-pid").write_text(text, encoding="utf-8")
    old = (NOW - timedelta(hours=3)).timestamp()
    os.utime(worktree / ".agk-session-pid", (old, old))
    return worktree


class Machine:
    """The processes of a test machine: which ids are alive, the table, and the stops made."""

    def __init__(self, monkeypatch, alive=(), listed=None):
        import conductor
        import launch

        self.alive, self.stops, self.listed = set(alive), [], listed or []
        monkeypatch.setattr(launch, "process_alive", lambda pid: pid in self.alive)
        monkeypatch.setattr(launch, "command_lines", lambda: list(self.listed))
        monkeypatch.setattr(launch, "process_table", lambda: {p: (1, 3) for p in self.alive})
        monkeypatch.setattr(conductor, "stopped", self.stop)
        monkeypatch.setattr(conductor, "worktree_safe", lambda worktree: True)
        monkeypatch.setattr(conductor, "lock_base", lambda root: root.parent / "locks")
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/nonexistent-agk-runtime")

    def stop(self, pid: int) -> bool:
        self.stops.append(pid)
        self.alive.discard(pid)
        return True


def gate(root, now=NOW, **kw) -> bool:
    import conductor

    return conductor.conductor_gate(root, now, **kw)


# --- answer 1: one conductor per machine, read from the machine ------------------------------


def test_a_live_conductor_under_another_name_starts_nothing(tmp_path, monkeypatch, capsys):
    """REQ-050: brief #1409 answer 1 (a record of kind `conductor`, any name)."""
    root = project(tmp_path)
    record(tmp_path, "conductor-local-df", 4001, NOW - timedelta(minutes=5))
    Machine(monkeypatch, alive={4001})
    assert gate(root) is False
    out = capsys.readouterr().out
    assert (
        "watchdog: conductor conductor-local-df is running on this machine; nothing started" in out
    )


def test_no_conductor_on_the_machine_lets_one_start(tmp_path, monkeypatch):
    """REQ-050: brief #1409 answer 1 (an ended record and a builder are not conductors)."""
    root = project(tmp_path)
    record(tmp_path, "conductor-local-cc", 4002, NOW - timedelta(hours=2))
    record(tmp_path, "b1", 4003, NOW - timedelta(minutes=5), kind="build")
    Machine(monkeypatch, alive={4003})
    assert gate(root) is True


def test_a_record_written_before_the_kind_is_read_by_its_name(tmp_path, monkeypatch):
    """REQ-050: brief #1409 answer 4 (extras started before this build carry no kind)."""
    import launch

    root = project(tmp_path)
    record(tmp_path, "conductor-local-a4", 4004, NOW, kind=None)
    Machine(monkeypatch, alive={4004})
    assert [x[0] for x in launch.live_conductors(root)] == ["conductor-local-a4"]


# --- answer 2: an idle conductor is replaced, not doubled -------------------------------------


def test_a_working_conductor_with_a_lapsed_lease_is_left(tmp_path, monkeypatch, capsys):
    """REQ-050: brief #1409 answer 2 (a file change in its worktree is a sign of work)."""
    root = project(tmp_path)
    worktree = record(tmp_path, "conductor-local", 4010, NOW - timedelta(hours=3))
    (worktree / "notes.txt").write_text("x\n", encoding="utf-8")
    os.utime(worktree / "notes.txt", (NOW.timestamp(), NOW.timestamp()))
    machine = Machine(monkeypatch, alive={4010})
    for minutes in (0, 10, 20):
        assert gate(root, NOW + timedelta(minutes=minutes)) is False
    assert machine.stops == []
    assert "watchdog: conductor conductor-local left (working)\n" in capsys.readouterr().out


def test_an_idle_conductor_is_stopped_and_replaced_once_never_doubled(
    tmp_path, monkeypatch, capsys
):
    """REQ-050: brief #1409 answer 2 (two quiet reads, then one stop; once an hour)."""
    root = project(tmp_path)
    record(tmp_path, "conductor-local", 4020, NOW - timedelta(hours=3))
    machine = Machine(monkeypatch, alive={4020})
    assert gate(root) is False  # the first read of its process tree
    assert gate(root, NOW + timedelta(minutes=10)) is True
    assert machine.stops == [4020]
    out = capsys.readouterr().out
    assert "watchdog: conductor conductor-local idle -> stopped; one starts in its place" in out
    record(tmp_path, "conductor-local", 4021, NOW - timedelta(hours=2))  # the replacement
    machine.alive.add(4021)
    for minutes in (20, 30, 40):
        assert gate(root, NOW + timedelta(minutes=minutes)) is False
    assert machine.stops == [4020]
    assert "held (stopped within the hour)" in capsys.readouterr().out


def test_twenty_passes_with_a_lapsed_lease_leave_exactly_one_conductor(tmp_path, monkeypatch):
    """REQ-050: brief #1409 answer 7 and its Measured line (twenty simulated passes)."""
    root = project(tmp_path)
    record(tmp_path, "conductor-local", 5000, NOW - timedelta(hours=3))
    machine = Machine(monkeypatch, alive={5000})
    pid = 5000
    for n in range(20):
        when = NOW + timedelta(minutes=10 * n)
        if gate(root, when):
            pid += 1
            record(tmp_path, "conductor-local", pid, when)
            machine.alive.add(pid)
        assert len(machine.alive) == 1
    assert len(machine.alive) == 1 and len(machine.stops) <= 1 + 190 // 60  # once an hour


def test_a_persons_own_conductor_is_named_and_never_stopped(tmp_path, monkeypatch, capsys):
    """REQ-050: brief #1409 answers 2 and 4 (no record: the kit never stops it)."""
    root = project(tmp_path)
    machine = Machine(
        monkeypatch, listed=[(5001, 1, "/home/u/.local/bin/claude --agent conductor")]
    )
    for minutes in range(0, 120, 10):
        assert gate(root, NOW + timedelta(minutes=minutes)) is False
    assert machine.stops == []
    assert "watchdog: conductor process 5001 is running on this machine" in capsys.readouterr().out


# --- answer 4: extras already running are named once ------------------------------------------


@pytest.mark.parametrize(
    "platform, stop",
    [
        ("linux", "pkill -TERM -P 4031,5001; kill 4031 5001"),
        ("win32", "taskkill /T /F /PID 4031 /PID 5001"),
    ],
)
def test_the_sweep_names_the_extras_once_with_the_stop_line(tmp_path, monkeypatch, platform, stop):
    """REQ-050: brief #1409 answer 4 (keep the lease holder, close the others)."""
    import conductor

    root = project(tmp_path)
    record(tmp_path, "conductor-local", 4030, NOW)
    record(tmp_path, "conductor-local-df", 4031, NOW)
    Machine(monkeypatch, alive={4030, 4031}, listed=[(5001, 1, "claude --agent conductor")])
    monkeypatch.setattr(conductor.sys, "platform", platform)
    lines = conductor.extra_conductor_lines(root, holder="conductor-local")
    assert lines == [
        "NEEDS-YOU: 3 conductors on this machine: keep conductor-local, close "
        f"conductor-local-df, process 5001; stop with: {stop}"
    ]


def test_one_conductor_on_the_machine_is_no_sweep_line(tmp_path, monkeypatch):
    """REQ-050: brief #1409 answer 4 (nothing to name)."""
    import conductor

    root = project(tmp_path)
    record(tmp_path, "conductor-local", 4040, NOW)
    Machine(monkeypatch, alive={4040})
    assert conductor.extra_conductor_lines(root, holder="conductor-local") == []


# --- answer 5: memory before a start ----------------------------------------------------------


def test_a_start_below_the_memory_floor_is_refused_and_names_the_setting(
    tmp_path, monkeypatch, capsys
):
    """REQ-050: brief #1409 answer 5 (read at the start; the next pass tries again)."""
    import launch

    root = project(tmp_path)
    (root / "agk.toml").write_text("[flow]\nmin_free_memory_mb = 4096\n", encoding="utf-8")
    Machine(monkeypatch)
    monkeypatch.setattr(launch, "available_memory", lambda: 1024 * launch.MIB)
    assert gate(root) is False
    out = capsys.readouterr().out
    assert "[flow] min_free_memory_mb" in out and "1024" not in out
    monkeypatch.setattr(launch, "available_memory", lambda: 8192 * launch.MIB)
    assert gate(root) is True


def test_a_builder_restart_below_the_memory_floor_is_held(tmp_path, monkeypatch):
    """REQ-050: brief #1409 answer 5 (no builder starts below the floor either)."""
    import conductor
    import launch

    root = project(tmp_path)
    (root / "agk.toml").write_text("[flow]\nmin_free_memory_mb = 4096\n", encoding="utf-8")
    monkeypatch.setattr(launch, "available_memory", lambda: 1024 * launch.MIB)
    assert conductor.memory_floor(root) is False
    monkeypatch.setattr(launch, "available_memory", lambda: 8192 * launch.MIB)
    assert conductor.memory_floor(root) is True


# --- answer 6: every start path ---------------------------------------------------------------


def test_launch_role_conductor_starts_nothing_beside_a_live_conductor(
    tmp_path, monkeypatch, capsys
):
    """REQ-050: brief #1409 answer 6 (a person's `launch.py role conductor`)."""
    import launch

    root = project(tmp_path)
    record(tmp_path, "conductor-local", 4050, NOW)
    Machine(monkeypatch, alive={4050})
    called = []
    monkeypatch.setattr(launch.subprocess, "run", lambda *a, **k: called.append(a))
    args = ["role", "--role", "conductor", "--session", "c2", "--adapter", "echo"]
    assert launch.role_main(args, root=root) == 1
    assert called == []
    assert (
        "stuck: conductor c2 not started (conductor conductor-local is running on this machine)"
        in (capsys.readouterr().out)
    )


def test_the_watchdog_starts_nothing_while_a_lease_is_valid_on_another_machine(monkeypatch, capsys):
    """REQ-050: brief #1409 answer 6 (the lease stays the rule between machines)."""
    import conductor

    monkeypatch.setattr(conductor, "plan_comments", lambda repo, issue: [])
    monkeypatch.setattr(conductor, "verdict_authors", lambda root: [])
    monkeypatch.setattr(
        conductor, "lease_holder", lambda c, a, now: ("elsewhere", NOW + timedelta(minutes=5))
    )
    monkeypatch.setattr(conductor, "conductor_gate", lambda *a, **k: pytest.fail("gate read"))
    assert conductor.watchdog_once(Path("."), "conductor-local", "o/r", "echo", 1) == 0
    assert "lease held by elsewhere" in capsys.readouterr().out


def test_the_job_prompts_tell_a_conductor_to_end_when_it_is_not_the_holder():
    """REQ-050: brief #1409 answer 3 (the close-tab marker; release when nothing is left)."""
    import conductor
    import launch

    for text in (conductor.WATCHDOG_PROMPT, conductor.JOB_PROMPT, launch.CONDUCTOR_NOTE):
        assert "close-tab:" in text and "lease --show" in text and "lease --release" in text
    assert "do not release it" in conductor.JOB_PROMPT


# --- the process lists, recorded for POSIX and Windows ----------------------------------------


@pytest.mark.parametrize(
    "platform, out, pid", [("linux", POSIX_PS, 5001), ("win32", WINDOWS_CIM, 7001)]
)
def test_the_process_list_is_read_on_both_platforms(platform, out, pid):
    """REQ-050: brief #1409 answer 1 (`ps` on POSIX, `Get-CimInstance Win32_Process` on Windows)."""
    import autopilot

    seen = []

    def run(words, **kw):
        seen.append(words)
        return subprocess.CompletedProcess(words, 0, stdout=out, stderr="")

    table = autopilot.claude_processes(run=run, platform=platform)
    assert seen[0][0] == ("powershell" if platform == "win32" else "ps")
    conductors = [
        p for p, _, args in table if autopilot.is_claude(args) and "--agent conductor" in args
    ]
    assert conductors == [pid]


# --- the POSIX adapter ------------------------------------------------------------------------


def test_the_posix_adapter_starts_no_conductor_beside_a_live_one(tmp_path):
    """REQ-050: brief #1409 answer 6 (the adapter's own check, before the worktree)."""
    if shutil.which("bash") is None:
        pytest.skip("needs bash")
    root = project(tmp_path)
    shutil.copy(ROOT / "kit" / "templates" / "start-session-local.sh", root / "start.sh")
    record(tmp_path, "conductor-local-df", os.getpid(), NOW)
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "claude").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (fake / "claude").chmod(stat.S_IRWXU)
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}"}
    env.update(AGK_SESSION="conductor-local", AGK_JOB_KIND="conductor")
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["bash", str(root / "start.sh")], cwd=root, input="go", text=True, env=env,
        capture_output=True, timeout=60,
    )  # fmt: skip
    assert done.returncode == 3
    assert "conductor conductor-local-df is running on this machine; nothing started" in done.stderr
    assert not (tmp_path / "agk-conductor-local").exists()
