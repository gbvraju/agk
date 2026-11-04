"""proof, evidence and prepush use the long form of the temporary folder on Windows (brief #508,
ADR-0257). REQ-016

On Windows (`os.name == "nt"`) `common.long_temp_dir()` is `tempfile.gettempdir()` expanded with
`GetLongPathNameW` through ctypes, or the value unchanged when the call fails; elsewhere it is
`Path(tempfile.gettempdir())`. `proof.py` and `evidence.py` make their temporary folders in it, and
`prepush.py`, `proof.py` and `evidence.py` run project test commands with `TEMP`, `TMP` and `TMPDIR`
set to it. Nothing changes on POSIX.

`os.name` and the ctypes call are monkeypatched; the paths are invented. With `os.name` patched the
tests read `long_temp_name()`, the text that `long_temp_dir()` wraps in a `Path`, because Python
3.11 refuses a `WindowsPath` on POSIX. The fake test command is
a real `sh -c` line that writes the three variables to a file, so the environment it is handed is
read back as the command saw it.
"""

from __future__ import annotations

import ctypes
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import common
import evidence
import prepush
import proof
import pytest

SHORT = r"C:\Users\EXAMPL~1.USR\AppData\Local\Temp"
LONG = r"C:\Users\example.user\AppData\Local\Temp"
VARS = ("TEMP", "TMP", "TMPDIR")
WRITE_ENV = 'printf "%s\\n%s\\n%s\\n" "$TEMP" "$TMP" "$TMPDIR" > "$AGK_ENV_OUT"'


class FakeKernel32:
    """`GetLongPathNameW(path, buffer, size)`: the length needed when the buffer is too small,
    else the length written; 0 when `result` is None (the call failed)."""

    def __init__(self, result: str | None) -> None:
        self.result = result
        self.calls: list[str] = []

    def GetLongPathNameW(self, path, buffer, size):  # noqa: N802 - the Windows API name
        self.calls.append(path)
        if self.result is None:
            return 0
        if buffer is None or size <= len(self.result):
            return len(self.result) + 1
        buffer.value = self.result
        return len(self.result)


def as_windows(monkeypatch, result: str | None) -> FakeKernel32:
    kernel32 = FakeKernel32(result)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: SHORT)
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(kernel32=kernel32), raising=False)
    monkeypatch.setattr(os, "name", "nt")
    return kernel32


# --- answer 1: long_temp_dir ---------------------------------------------------------------------


def test_a_short_path_is_expanded_on_windows(monkeypatch):
    kernel32 = as_windows(monkeypatch, LONG)
    got = common.long_temp_name()
    monkeypatch.undo()
    assert got == LONG
    assert kernel32.calls and kernel32.calls[0] == SHORT


def test_a_failing_call_falls_back_unchanged(monkeypatch):
    as_windows(monkeypatch, None)
    got = common.long_temp_name()
    monkeypatch.undo()
    assert got == SHORT


def test_a_call_that_raises_falls_back_unchanged(monkeypatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: SHORT)
    monkeypatch.delattr(ctypes, "windll", raising=False)  # no windll: an AttributeError or KeyError
    monkeypatch.setattr(os, "name", "nt")
    got = common.long_temp_name()
    monkeypatch.undo()
    assert got == SHORT


def test_posix_is_unchanged(monkeypatch, tmp_path):
    kernel32 = FakeKernel32(LONG)
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(kernel32=kernel32), raising=False)
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    assert common.long_temp_dir() == Path(tmp_path)
    assert kernel32.calls == []


def test_posix_env_is_unchanged(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    base = {"PATH": "/usr/bin", "TEMP": "kept"}
    assert common.temp_env(base) == base
    assert common.temp_env(base) is not base


# --- answer 2: the folders and the environment ----------------------------------------------------


@pytest.fixture
def windows_temp(monkeypatch, tmp_path):
    """Windows as `common` sees it, with a long temporary folder that exists on this machine."""
    long = tmp_path / "long temp"
    long.mkdir()
    monkeypatch.setattr(common, "on_windows", lambda: True)
    monkeypatch.setattr(common, "long_path_name", lambda path: str(long) if path == SHORT else None)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: SHORT)
    for name in VARS:
        monkeypatch.setenv(name, SHORT)
    return long


def seen(out: Path) -> list[str]:
    return out.read_text(encoding="utf-8").splitlines()


def test_long_temp_dir_is_the_long_name_as_a_path(windows_temp):
    assert common.long_temp_dir() == windows_temp


def test_temp_env_sets_all_three_variables(windows_temp):
    env = common.temp_env({"PATH": "/usr/bin", "TEMP": SHORT})
    assert [env[name] for name in VARS] == [str(windows_temp)] * 3
    assert env["PATH"] == "/usr/bin"


def test_proof_runs_both_trees_with_the_long_path(windows_temp, tmp_path, monkeypatch):
    out = tmp_path / "env.txt"
    monkeypatch.setenv("AGK_ENV_OUT", str(out))
    trees = [tmp_path / "base", tmp_path / "head"]
    for tree in trees:
        tree.mkdir()
    run = proof.Run("project_tests", [], WRITE_ENV, ".")
    status1, status2, _, _ = proof.run_pair(trees, run, 60)
    assert (status1, status2) == (0, 0)
    assert seen(out) == [str(windows_temp)] * 3


def test_proof_regression_runs_with_the_long_path(windows_temp, tmp_path, monkeypatch):
    out = tmp_path / "env.txt"
    monkeypatch.setenv("AGK_ENV_OUT", str(out))
    run = proof.Run("unit", [], WRITE_ENV, ".")
    proof.run_regression(tmp_path, proof.Regression([run], None), 60)
    assert run.outcome == "passed"
    assert seen(out) == [str(windows_temp)] * 3


def test_proof_makes_its_worktrees_in_the_long_path(windows_temp, tmp_path):
    trees = proof.Trees(tmp_path, "base", "head", {})
    try:
        assert trees.temp.parent == windows_temp
    finally:
        trees.temp.rmdir()


def test_prepush_runs_the_tests_with_the_long_path(windows_temp, tmp_path, monkeypatch):
    out = tmp_path / "env.txt"
    monkeypatch.setenv("AGK_ENV_OUT", str(out))
    runs = [{"name": "project_tests", "command": WRITE_ENV, "cwd": ".", "files": []}]
    ran = prepush.Ran(["test_plan.py"], tmp_path, 0, "")
    step = prepush.proof_runs(tmp_path, runs, ran)
    assert step.outcome == "ok", step.text
    assert seen(out) == [str(windows_temp)] * 3


def test_prepush_gate_runs_with_the_long_path(windows_temp, tmp_path, monkeypatch):
    out = tmp_path / "env.txt"
    monkeypatch.setenv("AGK_ENV_OUT", str(out))
    runs = [{"name": "project_tests", "command": WRITE_ENV, "cwd": ".", "files": []}]
    ran = prepush.Ran(["test_plan.py"], tmp_path, 0, "")
    found = prepush.Impact(table=True, profile=None, full=False, reason=None)
    step = prepush.gate(tmp_path, runs, found, None, 60, ran)
    assert step.outcome == "ok", step.text
    assert seen(out) == [str(windows_temp)] * 3


def test_evidence_reruns_with_the_long_path(windows_temp, tmp_path, monkeypatch):
    out = tmp_path / "env.txt"
    monkeypatch.setenv("AGK_ENV_OUT", str(out))
    env = evidence.run_env("0" * 40)
    assert env["AGK_BASE"] == "0" * 40
    unit = evidence.Unit("project_tests", tmp_path, 0, None, command=WRITE_ENV)
    code, _ = evidence.rerun(unit, env, 60)
    assert code == 0
    assert seen(out) == [str(windows_temp)] * 3


def test_evidence_makes_its_worktree_in_the_long_path(windows_temp, tmp_path, monkeypatch):
    asked: list = []

    def mkdtemp(**kwargs):
        asked.append(kwargs.get("dir"))
        raise OSError("refused")

    monkeypatch.setattr(evidence.tempfile, "mkdtemp", mkdtemp)
    with pytest.raises(evidence.Unreadable):
        evidence.in_worktree(tmp_path, {"base": "0" * 40}, "1" * 40, 1)
    assert [str(d) for d in asked] == [str(windows_temp)]


def test_posix_runs_keep_the_callers_environment(monkeypatch, tmp_path):
    out = tmp_path / "env.txt"
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setenv("AGK_ENV_OUT", str(out))
    monkeypatch.setenv("TEMP", "/kept/temp")
    monkeypatch.setenv("TMP", "/kept/tmp")
    monkeypatch.delenv("TMPDIR", raising=False)
    run = proof.Run("unit", [], WRITE_ENV, ".")
    proof.run_regression(tmp_path, proof.Regression([run], None), 60)
    assert seen(out) == ["/kept/temp", "/kept/tmp", ""]
