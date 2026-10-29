"""proof.py ends a timed-out test run, with its whole process tree, on every OS (brief #290, ADR-0167).

The Windows branch is tested with a fake process and a fake `taskkill`, so these tests run on any
OS; the POSIX branch is tested with a fake and, where `os.killpg` exists, with a real process tree.
No test sleeps for more than one second of real time.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only
import time
from pathlib import Path

import proof
import pytest

from test_proof import line, start


class FakeProc:
    """A Popen stand-in: `communicate` times out until the process is killed."""

    def __init__(self, pid: int = 4321, hangs_after_kill: bool = False) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self.killed = False
        self.hangs_after_kill = hangs_after_kill
        self.waits: list[float | None] = []

    def communicate(self, timeout: float | None = None):
        self.waits.append(timeout)
        if self.killed and not self.hangs_after_kill:
            self.returncode = 1
            return "", None
        raise subprocess.TimeoutExpired("sh", timeout or 0)

    def kill(self) -> None:
        self.killed = True


class FakeRun:
    """A `subprocess.run` stand-in that records the argument list; `taskkill` ends the fake tree."""

    def __init__(self, proc: FakeProc, returncode: int = 0, error: Exception | None = None) -> None:
        self.proc = proc
        self.returncode = returncode
        self.error = error
        self.calls: list[list[str]] = []

    def __call__(self, args, **_kwargs):
        self.calls.append(list(args))
        if self.error is not None:
            raise self.error
        if self.returncode == 0:
            self.proc.killed = True
        return subprocess.CompletedProcess(args, self.returncode, b"", b"")


@pytest.fixture
def no_killpg(monkeypatch):
    """Native Windows Python: no `os.killpg` and no `signal.SIGKILL`."""
    monkeypatch.delattr(proof.os, "killpg", raising=False)
    monkeypatch.delattr(proof.signal, "SIGKILL", raising=False)


def test_ac1_windows_starts_the_run_in_a_new_process_group():
    """REQ-016 AC1: brief #290 answer 1 (CREATE_NEW_PROCESS_GROUP, not a POSIX session)."""
    options = proof.popen_options(windows=True)
    assert options == {"creationflags": 0x00000200}
    assert proof.popen_options(windows=False) == {"start_new_session": True}


def test_ac1_windows_ends_the_tree_with_taskkill_and_never_calls_killpg(no_killpg):
    """REQ-016 AC1: brief #290 answer 1 (`taskkill /T /F /PID <pid>`; no AttributeError)."""
    proc = FakeProc(pid=777)
    run = FakeRun(proc)
    proof.kill_tree(proc, windows=True, run=run)
    assert run.calls == [["taskkill", "/T", "/F", "/PID", "777"]]
    assert proc.returncode == 1 and proc.waits and proc.waits[-1] is not None


@pytest.mark.parametrize("failure", ["exit", "missing", "hangs"])
def test_ac1_windows_falls_back_to_killing_the_shell_when_taskkill_fails(no_killpg, failure):
    """REQ-016 AC1: brief #290 (a failed or missing taskkill still ends the run it started)."""
    proc = FakeProc()
    run = {
        "exit": FakeRun(proc, returncode=128),
        "missing": FakeRun(proc, error=FileNotFoundError("taskkill")),
        "hangs": FakeRun(proc, error=subprocess.TimeoutExpired("taskkill", 1)),
    }[failure]
    proof.kill_tree(proc, windows=True, run=run)
    assert proc.killed and proc.returncode == 1


def test_ac1_posix_keeps_the_process_group_kill(monkeypatch):
    """REQ-016 AC1: brief #290 answer 1 (POSIX: SIGKILL to the process group)."""
    sent: list[tuple[int, int]] = []
    monkeypatch.setattr(proof.os, "killpg", lambda pid, sig: sent.append((pid, sig)), raising=False)
    monkeypatch.setattr(proof.signal, "SIGKILL", 9, raising=False)
    proc = FakeProc(pid=55)
    proc.killed = True  # the group is gone once the signal is sent
    run = FakeRun(proc)
    proof.kill_tree(proc, windows=False, run=run)
    assert sent == [(55, 9)] and run.calls == []


def test_ac1_posix_tolerates_a_group_that_is_already_gone(monkeypatch):
    """REQ-016 AC1: brief #290 (the group ended between the timeout and the kill)."""

    def gone(_pid, _sig):
        raise ProcessLookupError

    monkeypatch.setattr(proof.os, "killpg", gone, raising=False)
    monkeypatch.setattr(proof.signal, "SIGKILL", 9, raising=False)
    proc = FakeProc()
    proc.killed = True
    proof.kill_tree(proc, windows=False, run=FakeRun(proc))
    assert proc.returncode == 1


def test_ac1_a_tree_that_keeps_its_output_open_does_not_hang_proof(no_killpg):
    """REQ-016 AC1: brief #290 (reading the rest of the output after the kill is bounded)."""
    proc = FakeProc(hangs_after_kill=True)
    proof.kill_tree(proc, windows=True, run=FakeRun(proc))
    assert proc.waits and all(wait is not None for wait in proc.waits)


def test_ac1_a_windows_timeout_is_none_with_the_elapsed_time(no_killpg, tmp_path):
    """REQ-016 AC1: brief #290 answers 1 and 2 (execute on Windows, end to end with fakes)."""
    proc = FakeProc(pid=99)
    run = FakeRun(proc)
    started: list[dict] = []

    def popen(args, **kwargs):
        started.append(kwargs)
        return proc

    status, out, seconds = proof.execute("sleep 20", tmp_path, 1, windows=True, popen=popen, run=run)
    assert (status, out) == (None, "")
    assert seconds >= 0
    assert started[0]["creationflags"] == 0x00000200 and "start_new_session" not in started[0]
    assert run.calls == [["taskkill", "/T", "/F", "/PID", "99"]]


def test_ac1_the_timeout_line_names_the_elapsed_time_and_the_setting():
    """REQ-016 AC1: brief #290 answer 2 (the line says the time and the setting, not a failure)."""
    result = proof.Result("unknown", "timeout", "b", "h", [], elapsed=900)
    assert result.line() == "proof: unknown (timeout after 900 s, setting: proof_timeout)"
    assert result.data()["reason"] == "timeout"  # the reason the workflow and the facts read
    assert set(result.data()) == {"outcome", "reason", "base", "head", "test_files"}
    note = proof.timeout_note(900)
    assert "proof_timeout" in note and "900 s" in note and "ended" in note
    assert "fail" not in note.replace("did not fail", "")


def test_ac1_a_timed_out_run_is_never_proven_or_not_proven():
    """REQ-016 AC1: brief #290 must-not (either run timing out is unknown)."""
    for pair in ((None, None), (None, 0), (1, None), (0, None)):
        assert proof.decide(*pair) == ("unknown", "timeout")


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="a real process group needs POSIX")
def test_ac1_a_real_timeout_leaves_no_test_process_behind(repo):
    """REQ-016 AC1: brief #290 (the shell's background child dies with it; one real 1 s timeout)."""
    marker = repo.root.parent / f"grandchild-{os.getpid()}.pid"
    start(repo, f"sleep 30 & echo $! > {marker}; wait", "proof_timeout = 1\n")
    repo.commit({"tests/test_new.py": "# new\n"}, "add a test")
    proc = repo.run("proof.py")
    assert line(proc) == "proof: unknown (timeout after 1 s, setting: proof_timeout)"
    assert proc.returncode == 4
    assert "proof_timeout" in proc.stderr and "ended" in proc.stderr
    pid = int(Path(marker).read_text(encoding="utf-8"))
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and alive(pid):
        time.sleep(0.05)
    assert not alive(pid), "the background test process outlived the timeout"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # a zombie (killed, not yet reaped by init) counts as gone
    stat = Path(f"/proc/{pid}/stat")
    return not (stat.exists() and stat.read_text().split(") ", 1)[-1].startswith("Z"))


def test_ac1_the_guide_says_to_run_a_slow_proof_alone():
    """REQ-016 AC1: brief #290 answer 3 (the guide note)."""
    guide = Path(__file__).resolve().parents[2] / "docs" / "guides" / "existing-codebase.md"
    text = " ".join(guide.read_text(encoding="utf-8").split())
    assert "run it alone" in text
    assert "protected change" in text and "#289" in text
