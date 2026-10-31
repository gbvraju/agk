"""The heavy-step lock with N slots, priority order and a cleanup after a dead run (brief #426,
ADR-0231).

`lock_slots` (agk.toml, a positive whole number, 1 by default) lets that many heavy runs hold the
lock at once: slot 1 is the folder `agk-lock-NAME`, as before, and slot k is `agk-lock-NAME.k`.
`lock.py run --priority P` (0 to 3, 2 by default) writes a ticket while it waits, under the lock's
mutex; a free slot goes to the lowest P, then to the oldest ticket, and the ticket of a process
that no longer runs is dropped. `lock_cleanup` (agk.toml, empty by default) is a shell command run
once when a dead run's lock is cleared, with `AGK_LOCK_SESSION` and `AGK_LOCK_PID` of that run;
its output is shown and a failure is reported, never blocking. The locked command gets
`AGK_LOCK_SESSION` too. With one slot nothing changes, the folder name included.

Every test points `lock_dir` (agk.toml) at its own folder, so no test touches the real temp lock.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import lock
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "lock.py"
KIT = Path(__file__).resolve().parents[2]
PY = sys.executable


def settings(repo, folder: Path, extra: str = "") -> None:
    repo.commit({"agk.toml": f"lock_dir = '{folder}'\n{extra}"}, "settings")


@pytest.fixture
def where(repo, tmp_path) -> Path:
    folder = tmp_path / "locks"
    settings(repo, folder)
    return folder


def popen(repo, *args: str) -> subprocess.Popen:
    return subprocess.Popen(  # nosec B603 - fixed argument list from sys.executable, no shell
        [PY, str(SCRIPT), *args],
        cwd=repo.root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )


def wait_until(test, seconds: float = 15.0, what: str = "condition") -> None:
    end = time.monotonic() + seconds
    while not test():
        assert time.monotonic() < end, f"{what} never held"
        time.sleep(0.05)


def dead_pid() -> int:
    proc = subprocess.Popen([PY, "-c", "pass"])  # nosec B603 - fixed argument list, no shell
    proc.wait()
    return proc.pid


def plant(folder: Path, *, pid: int, session: str = "builder-old", minutes: float = 0.0) -> Path:
    """A lock left by someone else in slot 1: its owner file as `lock.py` writes it."""
    held = folder / "agk-lock-heavy"
    held.mkdir(parents=True)
    started = datetime.now(UTC) - timedelta(minutes=minutes)
    owner = {
        "session": session,
        "pid": pid,
        "host": socket.gethostname(),
        "started": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": uuid.uuid4().hex,
    }
    (held / "owner.json").write_text(json.dumps(owner), encoding="utf-8")
    return held


def tickets(folder: Path) -> list[Path]:
    box = folder / ".agk-lock-heavy.tickets"
    return sorted(box.glob("*.json")) if box.is_dir() else []


HOLD = (
    "import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch();"
    "go = pathlib.Path(sys.argv[2])\n"
    "while not go.exists(): time.sleep(0.05)"
)
LOG = (
    "import pathlib,sys,time; p = pathlib.Path(sys.argv[1]);"
    "p.write_text(p.read_text() + sys.argv[2] + chr(10) if p.exists() else sys.argv[2] + chr(10));"
    "time.sleep(0.3)"
)


def test_two_slots_are_held_by_two_runs_while_a_third_waits(repo, tmp_path):
    """REQ-040: brief #426 answers 1 and 4 (two slots, two holders, a third waits; `status`)."""
    folder = tmp_path / "locks"
    settings(repo, folder, "lock_slots = 2\n")
    go = tmp_path / "go"
    marks = [tmp_path / f"s{i}" for i in (1, 2)]
    holders = [
        popen(
            repo,
            "run",
            "--name",
            "heavy",
            "--session",
            f"builder-{i}",
            "--",
            PY,
            "-c",
            HOLD,
            str(marks[i - 1]),
            str(go),
        )
        for i in (1, 2)
    ]
    try:
        wait_until(lambda: all(m.exists() for m in marks), what="both holders started")
        assert (folder / "agk-lock-heavy").is_dir() and (folder / "agk-lock-heavy.2").is_dir()
        status = repo.run("lock.py", "status", "--name", "heavy").stdout.splitlines()
        assert len(status) == 2
        assert status[0].startswith("lock heavy slot 1: held by builder-")
        assert status[1].startswith("lock heavy slot 2: held by builder-")
        third = repo.run(
            "lock.py", "run", "--name", "heavy", "--timeout", "1", "--", PY, "-c", "print('RAN')"
        )
        assert third.returncode == 3, third.stdout + third.stderr
        assert "RAN" not in third.stdout
        assert "lock heavy: not taken after 1 s;" in third.stdout
        assert (
            "slot 1 held by builder-" in third.stdout and "slot 2 held by builder-" in third.stdout
        )
        assert tickets(folder) == []  # a run that gives up takes its ticket away
        waiter = popen(repo, "run", "--name", "heavy", "--", PY, "-c", "print('RAN')")
        wait_until(lambda: len(tickets(folder)) == 1, what="the third run's ticket")
    finally:
        go.touch()
    assert all(h.wait(timeout=20) == 0 for h in holders)
    out, _ = waiter.communicate(timeout=20)
    assert waiter.returncode == 0, out
    assert "RAN" in out and "lock heavy: taken" in out
    assert sorted(p.name for p in folder.iterdir()) == []  # no slot, ticket or mutex left
    free = repo.run("lock.py", "status", "--name", "heavy").stdout.splitlines()
    assert free == ["lock heavy slot 1: free", "lock heavy slot 2: free"]


@pytest.mark.parametrize(
    "first, second, order",
    [
        ("3", "1", ["second", "first"]),  # the lower priority number goes first
        ("2", "2", ["first", "second"]),  # the same priority: the oldest ticket goes first
    ],
)
def test_a_free_slot_goes_to_the_lowest_priority_then_the_oldest_ticket(
    repo, where, tmp_path, first, second, order
):
    """REQ-040: brief #426 answers 2 and 4 (priority order between two waiting runs)."""
    go, started, log = tmp_path / "go", tmp_path / "started", tmp_path / "log"
    holder = popen(
        repo,
        "run",
        "--name",
        "heavy",
        "--session",
        "builder-h",
        "--",
        PY,
        "-c",
        HOLD,
        str(started),
        str(go),
    )
    waiters = []
    try:
        wait_until(started.exists, what="the holder")
        waiters.append(
            popen(
                repo,
                "run",
                "--name",
                "heavy",
                "--priority",
                first,
                "--",
                PY,
                "-c",
                LOG,
                str(log),
                "first",
            )
        )
        wait_until(lambda: len(tickets(where)) == 1, what="the first ticket")
        waiters.append(
            popen(
                repo,
                "run",
                "--name",
                "heavy",
                "--priority",
                second,
                "--",
                PY,
                "-c",
                LOG,
                str(log),
                "second",
            )
        )
        wait_until(lambda: len(tickets(where)) == 2, what="the second ticket")
        record = json.loads(tickets(where)[0].read_text(encoding="utf-8"))
        assert {"session", "pid", "host", "priority", "created", "token"} <= set(record)
    finally:
        go.touch()
    assert holder.wait(timeout=20) == 0
    for w in waiters:
        out, _ = w.communicate(timeout=30)
        assert w.returncode == 0, out
    assert log.read_text().split() == order
    assert tickets(where) == []


def test_the_ticket_of_a_process_that_no_longer_runs_is_dropped(repo, where):
    """REQ-040: brief #426 answers 2 and 4 (a dead ticket is dropped, and does not go first)."""
    box = where / ".agk-lock-heavy.tickets"
    box.mkdir(parents=True)
    dead = {
        "session": "builder-gone",
        "pid": dead_pid(),
        "host": socket.gethostname(),
        "priority": 0,
        "created": time.time_ns() - 10**9,
        "token": uuid.uuid4().hex,
    }
    (box / f"{dead['created']:020d}-{dead['token']}.json").write_text(
        json.dumps(dead), encoding="utf-8"
    )
    proc = repo.run(
        "lock.py", "run", "--name", "heavy", "--timeout", "5", "--", PY, "-c", "print('RAN')"
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "RAN" in proc.stdout
    assert (
        "lock heavy: dropped the ticket of builder-gone (its process no longer runs)" in proc.stdout
    )
    assert not box.exists()


def test_a_live_ticket_of_a_higher_priority_goes_first(repo, where):
    """REQ-040: brief #426 answer 2 (a free slot is not taken past a run that goes first)."""
    box = where / ".agk-lock-heavy.tickets"
    box.mkdir(parents=True)
    alive = {
        "session": "builder-first",
        "pid": os.getpid(),  # this test process runs, so the ticket is live
        "host": socket.gethostname(),
        "priority": 0,
        "created": time.time_ns(),
        "token": uuid.uuid4().hex,
    }
    (box / f"{alive['created']:020d}-{alive['token']}.json").write_text(
        json.dumps(alive), encoding="utf-8"
    )
    proc = repo.run(
        "lock.py", "run", "--name", "heavy", "--timeout", "1", "--", PY, "-c", "print('RAN')"
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "RAN" not in proc.stdout
    assert "1 waiting run goes first" in proc.stdout
    assert len(tickets(where)) == 1  # only the live one; the timed-out run removed its own


CLEANUP = (
    f"'{PY}' -c \"import os,pathlib; pathlib.Path(os.environ['AGK_CLEANUP_LOG']).write_text("
    "os.environ['AGK_LOCK_SESSION'] + ' ' + os.environ['AGK_LOCK_PID'])\"; echo CLEANUP-SAID"
)


def test_cleanup_runs_once_on_a_stale_clear_with_both_variables(repo, tmp_path):
    """REQ-040: brief #426 answers 3 and 4 (the cleanup command, its output shown)."""
    folder, log = tmp_path / "locks", tmp_path / "cleanup.log"
    settings(repo, folder, f"lock_cleanup = '''{CLEANUP}'''\n")
    pid = dead_pid()
    plant(folder, pid=pid)
    proc = repo.run(
        "lock.py",
        "run",
        "--name",
        "heavy",
        "--",
        PY,
        "-c",
        "print('RAN')",
        AGK_CLEANUP_LOG=str(log),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert log.read_text() == f"builder-old {pid}"
    assert "CLEANUP-SAID" in proc.stdout
    assert "lock heavy: cleared a stale lock of builder-old (its process no longer runs)" in (
        proc.stdout
    )
    assert "lock heavy: cleanup of builder-old done (setting: lock_cleanup)" in proc.stdout
    assert proc.stdout.index("CLEANUP-SAID") < proc.stdout.index("RAN")
    assert proc.stdout.count("CLEANUP-SAID") == 1


def test_a_failing_cleanup_is_reported_and_never_blocks(repo, tmp_path):
    """REQ-040: brief #426 answers 3 and 4 (a failure is reported; the run goes on)."""
    folder = tmp_path / "locks"
    settings(repo, folder, "lock_cleanup = 'echo cleanup-broke; exit 4'\n")
    plant(folder, pid=dead_pid())
    proc = repo.run("lock.py", "run", "--name", "heavy", "--", PY, "-c", "print('RAN')")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "cleanup-broke" in proc.stdout
    assert "lock heavy: the cleanup of builder-old failed (exit 4, setting: lock_cleanup)" in (
        proc.stdout
    )
    assert "RAN" in proc.stdout


def test_cleanup_is_not_run_for_a_lock_cleared_by_age(repo, tmp_path):
    """REQ-040: brief #426 answer 3, Q-426-2 (only a dead run is cleaned up after: a lock cleared
    by age may belong to a run that still goes on)."""
    folder, log = tmp_path / "locks", tmp_path / "cleanup.log"
    settings(repo, folder, f"lock_cleanup = '''{CLEANUP}'''\n")
    plant(folder, pid=os.getpid(), minutes=121)
    proc = repo.run(
        "lock.py",
        "run",
        "--name",
        "heavy",
        "--",
        PY,
        "-c",
        "print('RAN')",
        AGK_CLEANUP_LOG=str(log),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not log.exists()
    assert "lock heavy: cleanup not run (the run may still go on, setting: lock_cleanup)" in (
        proc.stdout
    )


def test_cleanup_is_not_run_for_a_lock_that_names_no_session(repo, tmp_path):
    """REQ-040: brief #426 answer 3, Q-426-2 (no session: the cleanup could not be aimed)."""
    folder, log = tmp_path / "locks", tmp_path / "cleanup.log"
    settings(repo, folder, f"lock_cleanup = '''{CLEANUP}'''\n")
    plant(folder, pid=dead_pid(), session="")
    proc = repo.run(
        "lock.py",
        "run",
        "--name",
        "heavy",
        "--",
        PY,
        "-c",
        "print('RAN')",
        AGK_CLEANUP_LOG=str(log),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not log.exists()
    assert "lock heavy: cleanup not run (the lock names no session, setting: lock_cleanup)" in (
        proc.stdout
    )


def test_without_a_cleanup_setting_nothing_runs(repo, where):
    """REQ-040: brief #426 answer 3 (empty by default; the kit ships none)."""
    plant(where, pid=dead_pid())
    proc = repo.run("lock.py", "run", "--name", "heavy", "--", PY, "-c", "print('RAN')")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "cleanup" not in proc.stdout.replace("cleared a stale lock", "")


def test_the_locked_command_gets_its_session(repo, where):
    """REQ-040: brief #426 answer 3 (`AGK_LOCK_SESSION` for the locked command)."""
    probe = "import os; print('SESSION=' + os.environ.get('AGK_LOCK_SESSION', '<unset>'))"
    proc = repo.run(
        "lock.py", "run", "--name", "heavy", "--session", "builder-x", "--", PY, "-c", probe
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SESSION=builder-x" in proc.stdout


@pytest.mark.parametrize("extra", ["", "lock_slots = 1\n"])
def test_one_slot_is_unchanged(repo, tmp_path, extra):
    """REQ-040: brief #426 answers 1 and 4 (with one slot nothing changes, the folder included)."""
    folder = tmp_path / "locks"
    settings(repo, folder, extra)
    probe = "import os,sys; print(sorted(os.listdir(sys.argv[1])))"
    proc = repo.run("lock.py", "run", "--name", "heavy", "--", PY, "-c", probe, str(folder))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "['agk-lock-heavy']" in proc.stdout
    assert repo.run("lock.py", "status", "--name", "heavy").stdout == "lock heavy: free\n"
    assert lock.lock_folder(repo.root, "heavy") == folder / "agk-lock-heavy"


def test_the_take_that_prepush_calls_works_with_one_slot(tmp_path):
    """REQ-040: brief #426 answer 1 (`prepush.py` takes the lock through `take` and releases it
    with `clear_if_same`, as merged in #422)."""
    held = tmp_path / "locks" / "agk-lock-heavy"
    token = uuid.uuid4().hex
    owner = {
        "session": "builder-p",
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": token,
    }
    assert lock.take(held, "heavy", owner, 120, None)
    assert lock.read_owner(held)["token"] == token
    assert lock.clear_if_same(held, token) is True
    assert sorted(p.name for p in held.parent.iterdir()) == []


@pytest.mark.parametrize("value", ["0", "-1", "'2'", "true", "1.5"])
def test_a_bad_lock_slots_is_refused(repo, tmp_path, value):
    """REQ-040: brief #426 answer 1 (a positive whole number; the refusal names the setting)."""
    settings(repo, tmp_path / "locks", f"lock_slots = {value}\n")
    for args in (("status", "--name", "heavy"), ("run", "--name", "heavy", "--", PY, "-c", "")):
        proc = repo.run("lock.py", *args)
        assert proc.returncode == 2
        assert "setting: lock_slots" in proc.stderr
        assert value not in proc.stdout + proc.stderr.replace("lock_slots", "")


def test_a_bad_lock_cleanup_is_refused(repo, tmp_path):
    """REQ-040: brief #426 answer 3 (a command line; the refusal names the setting)."""
    settings(repo, tmp_path / "locks", "lock_cleanup = ['docker']\n")
    proc = repo.run("lock.py", "run", "--name", "heavy", "--", PY, "-c", "")
    assert proc.returncode == 2
    assert "setting: lock_cleanup" in proc.stderr and "docker" not in proc.stderr


@pytest.mark.parametrize("value", ["4", "-1", "high", "1.0"])
def test_a_bad_priority_is_a_usage_error(repo, where, value):
    """REQ-040: brief #426 answer 2 (0 to 3)."""
    proc = repo.run("lock.py", "run", "--name", "heavy", "--priority", value, "--", PY, "-c", "")
    assert proc.returncode == 2
    assert "--priority" in proc.stderr
    assert repo.run("lock.py", "status", "--name", "heavy", "--priority", "1").returncode == 2


def test_the_templates_list_both_settings():
    """REQ-040: brief #426 answers 1 and 3 (commented optional lines; the invented example)."""
    for rel in ("kit/templates/agk.toml", "kit/templates/agk.adopt.toml"):
        text = (KIT / rel).read_text(encoding="utf-8")
        assert "# lock_slots = 1" in text, rel
        assert '# lock_cleanup = ""' in text, rel
        assert "docker ps -aq --filter label=agk.session=$AGK_LOCK_SESSION" in text, rel


def test_the_reference_names_the_new_settings():
    """REQ-040: brief #426 (the reference guide)."""
    text = (KIT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    for word in ("lock_slots", "--priority", "lock_cleanup", "AGK_LOCK_SESSION", "AGK_LOCK_PID"):
        assert word in text, word


# The verdict on 74659dc, finding 1: under session rule 31 `prepush.py` takes and finds its lock
# in any slot, so the slots apply to the pre-push gate too.


def gate_project(repo, outside: Path, area_cmd: str = "echo kit {files} >> LOG") -> None:
    from test_prepush_regression import project, toml

    project(repo, "lock_slots = 2\n" + toml(outside, area_cmd=area_cmd))


def gate_env(outside: Path) -> dict[str, str]:
    from test_prepush import path_with, scanner

    env = {**os.environ, "PATH": path_with(scanner(outside / "bin", 0))}
    for key in ("GITHUB_BASE_REF", "AGK_BASE", "CI"):
        env.pop(key, None)
    return env


def gate_ran(outside: Path) -> list[str]:
    log = outside / "ran.log"
    return log.read_text(encoding="utf-8").splitlines() if log.is_file() else []


def test_prepush_under_a_caller_in_slot_2_does_not_take_a_slot_again(repo, tmp_path):
    """REQ-040: verdict on 74659dc, finding 1 (rule 31: the caller holds slot 2, and the gate
    sees it, so it neither waits for slot 1 nor takes a slot of its own)."""
    outside = tmp_path / "outside"
    gate_project(repo, outside)
    slot1 = plant(outside / "locks", pid=os.getpid(), session="builder-a")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            PY,
            str(SCRIPT),
            "run",
            "--name",
            "heavy",
            "--session",
            "builder-b",
            "--timeout",
            "5",
            "--",
            PY,
            str(SCRIPT.parent / "prepush.py"),
        ],
        cwd=repo.root,
        capture_output=True,
        text=True,
        env=gate_env(outside),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "lock heavy: held by this run's caller (lock.py run); not taken again" in proc.stdout
    assert "waiting" not in proc.stdout
    assert gate_ran(outside) == ["kit tests/billing/test_pay.py"]
    assert slot1.exists()  # builder-a's slot is never touched
    assert not (outside / "locks" / "agk-lock-heavy.2").exists()  # released


def test_prepush_without_a_caller_takes_the_free_slot_2_and_releases_it(repo, tmp_path):
    """REQ-040: verdict on 74659dc, finding 1 (slot 1 held: the gate takes slot 2, at once)."""
    outside = tmp_path / "outside"
    slot2 = outside / "locks" / "agk-lock-heavy.2"
    gate_project(repo, outside, f"test -d {slot2} && echo slot2 >> LOG; echo kit {{files}} >> LOG")
    other = subprocess.Popen([PY, "-c", "import time; time.sleep(120)"])  # nosec B603 - fixed argument list, no shell
    try:
        # builder-a's live run in slot 1; not this test's process, which is the gate's parent
        slot1 = plant(outside / "locks", pid=other.pid, session="builder-a")
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [PY, str(SCRIPT.parent / "prepush.py")],
            cwd=repo.root,
            capture_output=True,
            text=True,
            env=gate_env(outside),
            timeout=60,
        )
    finally:
        other.kill()
        other.wait()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "waiting" not in proc.stdout
    assert gate_ran(outside) == ["slot2", "kit tests/billing/test_pay.py"]
    assert slot1.exists()
    assert not slot2.exists()
    assert not ticket_leftovers(outside / "locks")


def ticket_leftovers(folder: Path) -> list[str]:
    return [p.name for p in folder.iterdir() if p.name.startswith(".")]
