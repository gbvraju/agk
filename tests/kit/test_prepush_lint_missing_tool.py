"""prepush names a missing lint tool in one line (brief #507, ADR-0256).

When `make lint` exits non-zero and its output shows that a command could not be started
(`CreateProcess(NULL, <cmd> ...) failed`, `<cmd>: command not found`, `<cmd>: not found`,
`<cmd>: No such file or directory` for the first word, or an exit of 127), the lint step is a
FAIL with one line naming `<cmd>` and how to install it, and the raw output is not echoed. Any
other lint failure prints as before. Lint stays a FAIL, never `not run`: it is a rule of the
project, unlike the optional secret scan.

The `run` results are fakes, except one test that runs a real `make` on a Makefile under
`tmp_path` whose recipe names a command that does not exist.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import prepush
import pytest


def line(cmd: str) -> str:
    return (
        f"lint: the lint target runs {cmd}, which is not installed (target: lint); install it "
        f"(for example: uv tool install {cmd} or pip install {cmd}) and run prepush again"
    )


WINDOWS = (
    "ruff check --isolated --line-length 100 scripts/agk\n"
    "process_begin: CreateProcess(NULL, ruff check --isolated --line-length 100 scripts/agk, "
    "...) failed.\n"
    "make (e=2): The system cannot find the file specified.\n"
    "make: *** [agk.mk:24: agk-lint] Error 2"
)
BASH = (
    "ruff check --isolated scripts/agk | cat\n"
    "bash: line 1: ruff: command not found\n"
    "make: *** [agk.mk:24: agk-lint] Error 127"
)
DASH = "ruff check scripts/agk | cat\n/bin/sh: 1: ruff: not found\nmake: *** [agk.mk:24] Error 127"
DIRECT = (
    "ruff check --isolated scripts/agk\n"
    "make: ruff: No such file or directory\n"
    "make: *** [agk.mk:24: agk-lint] Error 127"
)
ORDINARY = (
    "ruff check --isolated scripts/agk\n"
    "scripts/agk/example.py:1:8: F401 [*] `os` imported but unused\n"
    "Found 1 error.\n"
    "make: *** [agk.mk:24: agk-lint] Error 1"
)


@pytest.fixture
def fake(tmp_path, monkeypatch):
    """A project with a lint target, `make` found, and `make lint` answering what a test sets."""
    (tmp_path / "Makefile").write_text("lint:\n\t@true\n", encoding="utf-8")
    result: dict = {"code": 0, "out": ""}
    real_which = shutil.which
    monkeypatch.setattr(
        prepush.shutil, "which", lambda n: "/usr/bin/make" if n == "make" else real_which(n)
    )

    def run(cmd, cwd, env=None):
        if cmd == ["make", "-n", "lint"]:
            return 0, ""
        assert cmd == ["make", "lint"]
        return result["code"], result["out"]

    monkeypatch.setattr(prepush, "run", run)

    def lint(code: int, out: str) -> prepush.Step:
        result.update(code=code, out=out)
        return prepush.lint(tmp_path)

    return lint


def test_the_windows_createprocess_output_gives_the_one_line(fake):
    """REQ-016: brief #507 answers 1 and 3 (the Windows CreateProcess output names ruff)."""
    step = fake(2, WINDOWS)
    assert step.outcome == "FAIL" and not step.not_run
    assert step.text == line("ruff")
    assert "CreateProcess" not in step.text and "e=2" not in step.text


def test_the_posix_command_not_found_output_gives_the_one_line(fake):
    """REQ-016: brief #507 answers 1 and 3 (the POSIX `command not found` output names ruff)."""
    step = fake(2, BASH)
    assert step.outcome == "FAIL"
    assert step.text == line("ruff")


def test_a_shell_not_found_output_gives_the_one_line(fake):
    """REQ-016: brief #507 answer 1 (`<cmd>: not found`, as dash prints it)."""
    assert fake(2, DASH).text == line("ruff")


def test_make_no_such_file_for_the_first_word_gives_the_one_line(fake):
    """REQ-016: brief #507 answer 1 (`No such file or directory` for the first word)."""
    assert fake(2, DIRECT).text == line("ruff")


def test_a_make_exit_127_gives_the_one_line(fake):
    """REQ-016: brief #507 answers 1 and 3 (make exit 127 names the first word, ruff)."""
    step = fake(127, "ruff check --isolated scripts/agk")
    assert step.outcome == "FAIL"
    assert step.text == line("ruff")


def test_an_ordinary_lint_failure_is_unchanged(fake):
    """REQ-016: brief #507 answers 1 and 3 (any other lint failure prints as today)."""
    step = fake(2, ORDINARY)
    assert step.outcome == "FAIL"
    assert step.text == ORDINARY


def test_a_passing_lint_is_unchanged(fake):
    """REQ-016: brief #507 answer 1 (only a non-zero exit is read)."""
    step = fake(0, "All checks passed!")
    assert step.outcome == "ok" and step.text == "All checks passed!"


def test_the_command_is_named_by_its_file_name(fake):
    """REQ-016: brief #507 answer 1 (`<cmd>` is the first word; a path or `.exe` is not shown)."""
    out = 'process_begin: CreateProcess(NULL, "C:\\tools\\ruff.exe" check scripts, ...) failed.'
    assert fake(2, out).text == line("ruff")
    out = ".venv/bin/ruff: No such file or directory\nmake: *** [Makefile:2: lint] Error 127"
    assert fake(2, out).text == line("ruff")


def test_a_missing_makefile_is_not_read_as_a_missing_tool(fake):
    """REQ-016: brief #507 answer 1 (a file make cannot read is not a command it cannot start)."""
    out = (
        "make: agk.mk: No such file or directory\n"
        "make: *** No rule to make target 'agk.mk'.  Stop."
    )
    step = fake(2, out)
    assert step.outcome == "FAIL" and step.text == out


def test_the_record_keeps_what_ran(fake):
    """REQ-016: brief #507 answer 1 (the record of brief #374 still holds the real exit)."""
    step = fake(2, WINDOWS)
    assert step.ran is not None and step.ran.argv == ["make", "lint"] and step.ran.code == 2


def test_the_rule_is_in_the_module_docstring():
    """REQ-016: brief #507 answer 2 (lint stays a FAIL; the rule is in the docstring)."""
    doc = " ".join((prepush.__doc__ or "").split())
    assert "Brief #507 (ADR-0256)" in doc
    assert "lint is a rule of the project" in doc


@pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")
def test_a_real_make_with_a_missing_command_gives_the_one_line(tmp_path: Path):
    """REQ-016: brief #507 answer 1 (a real `make lint` whose recipe cannot start)."""
    cmd = "agk-no-such-tool-507"
    (tmp_path / "Makefile").write_text(f"lint:\n\t{cmd} check scripts\n", encoding="utf-8")
    step = prepush.lint(tmp_path)
    assert step.outcome == "FAIL"
    assert step.text == line(cmd)
