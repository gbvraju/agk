"""The heavy-step lock (brief #337, ADR-0191).

`scripts/agk/lock.py run --name heavy -- <command...>` takes a machine-wide lock (a folder made
atomically, holding the owner's session, process id, host and start time), runs the command
without a shell, and releases the lock when the command ends, also on failure or interrupt. A
second run waits its turn, printing who holds the lock; `--timeout S` gives up. A lock whose
process no longer runs on this machine, or older than `lock_stale_minutes`, is cleared with a line
saying so. `lock.py status` prints the holder or `free`.

Every test points `lock_dir` (agk.toml) at its own folder, so no test touches the real temp lock.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import lock
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "lock.py"
PY = sys.executable


@pytest.fixture
def where(repo, tmp_path) -> Path:
    """A repository whose agk.toml puts the locks in a folder of the test."""
    folder = tmp_path / "locks"
    repo.commit({"agk.toml": f"lock_dir = '{folder}'\n"}, "base")
    return folder


def lock_run(repo, *args: str, **env: str):
    return repo.run("lock.py", *args, **env)


def popen(repo, *args: str) -> subprocess.Popen:
    return subprocess.Popen(  # nosec B603 - fixed argument list from sys.executable, no shell
        [PY, str(SCRIPT), *args],
        cwd=repo.root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )


def plant(folder: Path, *, pid: int, host: str | None = None, minutes: float = 0.0) -> Path:
    """A lock left by someone else: its owner file as `lock.py` writes it."""
    held = folder / "agk-lock-heavy"
    held.mkdir(parents=True)
    started = datetime.now(UTC) - timedelta(minutes=minutes)
    owner = {
        "session": "builder-old",
        "pid": pid,
        "host": host or socket.gethostname(),
        "started": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": "planted",
    }
    (held / "owner.json").write_text(json.dumps(owner), encoding="utf-8")
    return held


def dead_pid() -> int:
    proc = subprocess.Popen([PY, "-c", "pass"])  # nosec B603 - fixed argument list, no shell
    proc.wait()
    return proc.pid


def wait_for(path: Path, seconds: float = 10.0) -> None:
    end = time.monotonic() + seconds
    while not path.exists():
        assert time.monotonic() < end, f"{path} never appeared"
        time.sleep(0.05)


def test_take_run_and_release(repo, where):
    """REQ-040: brief #337 answers 1 and 6 (take and release; the owner is recorded)."""
    probe = (
        "import json,sys; d=json.load(open(sys.argv[1], encoding='utf-8'));"
        "print('OWNER', d['session'], d['pid'] > 0, d['host'] != '', d['started'][-1])"
    )
    owner = where / "agk-lock-heavy" / "owner.json"
    proc = lock_run(
        repo, "run", "--name", "heavy", "--session", "builder-x", "--", PY, "-c", probe, str(owner)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OWNER builder-x True True Z" in proc.stdout
    assert not (where / "agk-lock-heavy").exists()
    assert lock_run(repo, "status", "--name", "heavy").stdout.strip() == "lock heavy: free"


def test_the_exit_code_is_the_commands_and_a_failure_releases(repo, where):
    """REQ-040: brief #337 answers 1 and 6 (release on a failing command)."""
    proc = lock_run(repo, "run", "--name", "heavy", "--", PY, "-c", "raise SystemExit(7)")
    assert proc.returncode == 7, proc.stdout + proc.stderr
    assert not (where / "agk-lock-heavy").exists()


def test_the_command_runs_without_a_shell(repo, where):
    """REQ-040: brief #337 answer 1 (the arguments reach the command as they are)."""
    proc = lock_run(
        repo,
        "run",
        "--name",
        "heavy",
        "--",
        PY,
        "-c",
        "import sys; print(sys.argv[1])",
        "$HOME; echo no",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "$HOME; echo no" in proc.stdout


def test_a_command_that_cannot_start_releases_and_says_so(repo, where):
    """REQ-040: brief #337 answer 1 (a missing program: the lock is released, exit 127)."""
    proc = lock_run(repo, "run", "--name", "heavy", "--", "no-such-program-agk")
    assert proc.returncode == 127
    assert "cannot be started" in proc.stdout + proc.stderr
    assert "no-such-program-agk" not in proc.stdout + proc.stderr  # the value is never echoed
    assert not (where / "agk-lock-heavy").exists()


def test_a_second_run_waits_for_the_first(repo, where, tmp_path):
    """REQ-040: brief #337 answers 2 and 6 (waiting with a second process, the holder named)."""
    started, first_end, second_start = (tmp_path / n for n in ("s1", "e1", "s2"))
    hold = (
        "import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(2);"
        "pathlib.Path(sys.argv[2]).write_text(str(time.time()))"
    )
    first = popen(
        repo,
        "run",
        "--name",
        "heavy",
        "--session",
        "builder-one",
        "--",
        PY,
        "-c",
        hold,
        str(started),
        str(first_end),
    )
    wait_for(started)
    second = lock_run(
        repo,
        "run",
        "--name",
        "heavy",
        "--session",
        "builder-two",
        "--",
        PY,
        "-c",
        "import pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text(str(time.time()))",
        str(second_start),
    )
    assert first.wait(timeout=20) == 0
    assert second.returncode == 0, second.stdout + second.stderr
    assert float(second_start.read_text()) >= float(first_end.read_text())
    waiting = [ln for ln in second.stdout.splitlines() if ln.startswith("lock heavy: waiting")]
    assert len(waiting) == 1  # one line now, then one a minute
    assert "held by builder-one" in waiting[0] and "for 0 min" in waiting[0]
    assert "lock heavy: taken" in second.stdout


def test_status_names_the_holder(repo, where):
    """REQ-040: brief #337 answer 4 (`status` prints the holder)."""
    plant(where, pid=os.getpid(), minutes=5)
    out = lock_run(repo, "status", "--name", "heavy").stdout
    assert out.startswith("lock heavy: held by builder-old")
    assert f"pid {os.getpid()}" in out and "for 5 min" in out


def test_a_lock_of_a_dead_process_is_cleared(repo, where):
    """REQ-040: brief #337 answers 3 and 6 (stale by a dead process id on this machine)."""
    plant(where, pid=dead_pid())
    proc = lock_run(repo, "run", "--name", "heavy", "--", PY, "-c", "print('RAN')")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (
        "lock heavy: cleared a stale lock of builder-old (its process no longer runs)"
        in proc.stdout
    )
    assert "RAN" in proc.stdout
    assert not (where / "agk-lock-heavy").exists()


def test_status_says_a_dead_holder_is_stale_and_clears_nothing(repo, where):
    """REQ-040: brief #337 answer 4 (`status` only reads)."""
    held = plant(where, pid=dead_pid())
    out = lock_run(repo, "status", "--name", "heavy").stdout
    assert "stale (its process no longer runs)" in out
    assert held.exists()


def test_a_lock_older_than_the_setting_is_cleared(repo, where):
    """REQ-040: brief #337 answers 3 and 6 (stale by age; the default is 120 minutes)."""
    plant(where, pid=os.getpid(), minutes=121)
    proc = lock_run(repo, "run", "--name", "heavy", "--", PY, "-c", "print('RAN')")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (
        "cleared a stale lock of builder-old (older than 120 min, setting: lock_stale_minutes)"
        in (proc.stdout)
    )


def test_lock_stale_minutes_is_read(repo, where):
    """REQ-040: brief #337 answer 3 (an optional setting)."""
    repo.commit({"agk.toml": f"lock_dir = '{where}'\nlock_stale_minutes = 300\n"}, "setting")
    plant(where, pid=os.getpid(), minutes=121)
    proc = lock_run(
        repo, "run", "--name", "heavy", "--timeout", "1", "--", PY, "-c", "print('RAN')"
    )
    assert proc.returncode == 3
    assert "RAN" not in proc.stdout


def test_a_bad_lock_stale_minutes_is_refused(repo, where):
    """REQ-040: brief #337 answer 3 (refusals name the setting, never the value)."""
    repo.commit({"agk.toml": f"lock_dir = '{where}'\nlock_stale_minutes = -4\n"}, "setting")
    proc = lock_run(repo, "status", "--name", "heavy")
    assert proc.returncode == 2
    assert "lock_stale_minutes" in proc.stdout + proc.stderr and "-4" not in proc.stdout


def test_a_dead_process_on_another_host_is_not_cleared(repo, where):
    """REQ-040: brief #337 answer 3 (the process id is checked only on this machine)."""
    plant(where, pid=dead_pid(), host="another-machine.invalid")
    proc = lock_run(
        repo, "run", "--name", "heavy", "--timeout", "1", "--", PY, "-c", "print('RAN')"
    )
    assert proc.returncode == 3
    assert (where / "agk-lock-heavy").exists()


def test_the_timeout_gives_up_with_a_clear_message(repo, where):
    """REQ-040: brief #337 answers 2 and 6 (the timeout)."""
    held = plant(where, pid=os.getpid())
    proc = lock_run(
        repo, "run", "--name", "heavy", "--timeout", "1", "--", PY, "-c", "print('RAN')"
    )
    assert proc.returncode == 3
    assert "lock heavy: not taken after 1 s; held by builder-old" in proc.stdout
    assert "RAN" not in proc.stdout
    assert held.exists()  # someone else's lock is never removed


@pytest.mark.skipif(os.name == "nt", reason="POSIX signals")
@pytest.mark.parametrize("sig, code", [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_an_interrupt_releases_the_lock(repo, where, tmp_path, sig, code):
    """REQ-040: brief #337 answer 1 (release on interrupt)."""
    started = tmp_path / "started"
    hold = "import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(30)"
    proc = popen(repo, "run", "--name", "heavy", "--", PY, "-c", hold, str(started))
    wait_for(started)
    proc.send_signal(sig)
    assert proc.wait(timeout=20) == code
    assert not (where / "agk-lock-heavy").exists()


def test_the_default_folder_is_the_users_temp(repo, monkeypatch, tmp_path):
    """REQ-040: brief #337 answer 1 (under the user's temp, or `lock_dir`)."""
    monkeypatch.setattr(lock.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    assert lock.lock_folder(repo.root, "heavy") == tmp_path / "tmp" / "agk-lock-heavy"


def test_usage_errors(repo, where):
    """REQ-040: brief #337 answer 1 (exit 2: no command, a bad name, an unknown option)."""
    assert lock_run(repo, "run", "--name", "heavy").returncode == 2
    assert lock_run(repo, "run", "--name", "heavy", "--").returncode == 2
    assert lock_run(repo, "run", "--name", "../x", "--", PY, "-c", "pass").returncode == 2
    assert lock_run(repo, "status", "--fast").returncode == 2
    assert lock_run(repo, "nothing").returncode == 2


def test_windows_checks_a_process_without_signalling_it():
    """REQ-040: brief #337 answer 4 (Windows: OpenProcess and GetExitCodeProcess, never a signal;
    `os.kill` there would end the process)."""

    class Kernel:
        def __init__(self, code: int | None) -> None:
            self.code, self.closed = code, False

        def OpenProcess(self, access, inherit, pid):  # noqa: N802 - the Win32 name
            return 0 if self.code is None else 42

        def GetExitCodeProcess(self, handle, out):  # noqa: N802 - the Win32 name
            out._obj.value = self.code
            return 1

        def CloseHandle(self, handle):  # noqa: N802 - the Win32 name
            self.closed = True
            return 1

    running = Kernel(259)  # STILL_ACTIVE
    assert lock.pid_alive(1234, windows=True, kernel=running) is True and running.closed
    assert lock.pid_alive(1234, windows=True, kernel=Kernel(0)) is False
    assert lock.pid_alive(1234, windows=True, kernel=Kernel(None)) is False


def test_the_guide_and_the_session_rules_point_to_lock_py():
    """REQ-040: brief #337 answer 5 (no hand-made lock snippet left)."""
    root = Path(__file__).resolve().parents[2]
    guide = (root / "docs" / "guides" / "local-mode.md").read_text(encoding="utf-8")
    assert "scripts/agk/lock.py run --name heavy --" in guide
    assert 'mkdir "$lock"' not in guide and "trap " not in guide
    rules = (root / "config" / "session-rules.md").read_text(encoding="utf-8")
    thirty = next(ln for ln in rules.splitlines() if ln.startswith("30. "))
    assert "scripts/agk/lock.py run --name heavy" in thirty
    rule = next(ln for ln in rules.splitlines() if ln.startswith("31. "))
    assert "lock.py run --name heavy --session ID -- python3 scripts/agk/prepush.py" in rule
