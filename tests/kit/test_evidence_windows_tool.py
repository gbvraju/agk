"""`evidence.py check` reads a Windows record's secret-scan tool as gitleaks (brief #504, ADR-0253).

On Windows, prepush records the secret scan's tool as `shutil.which` gives it, for example
`C:\\Tools\\gitleaks.EXE`. `evidence.py check` reads the executable's base name, lower-cased
and with one trailing `.exe` removed, so that any case of `gitleaks`, with or without `.exe`, is
the same tool and the scan is repeated. Nothing else is loosened: another tool name, or a changed
tail, still reads `not what prepush runs: secret-scan (field: argv)`. The records are invented,
under `tmp_path`, and the tests run on a POSIX runner.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from test_evidence import LINE, check, project, step, write
from test_prepush import scanner

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    """A folder outside the fixture repository: the record, the lock folder, the temp folder."""
    return tmp_path_factory.mktemp("outside")


DIFFERS = "evidence: not what prepush runs: secret-scan (field: argv)"


def tail(repo) -> list[str]:
    """The arguments prepush passes to gitleaks for the fixture's head."""
    head = repo.git("rev-parse", "HEAD").strip()
    mb = repo.git("merge-base", "main", "HEAD").strip()
    return ["git", "--no-banner", "--redact", "--exit-code", "1", f"--log-opts={mb}..{head}", "."]


def scan_record(repo, outside: Path, tool: str, args: list[str] | None = None) -> Path:
    argv = [tool, *(tail(repo) if args is None else args)]
    return write(outside / "record.json", repo, [step("secret-scan", argv)])


@pytest.mark.parametrize(
    "value,name",
    [
        ("C:\\Program Files\\gitleaks\\gitleaks.EXE", "gitleaks"),
        ("C:/Tools/GITLEAKS.exe", "gitleaks"),
        ("GITLEAKS.exe", "gitleaks"),
        ("gitleaks", "gitleaks"),
        ("/usr/local/bin/gitleaks", "gitleaks"),
        ("D:\\bin\\gitleaks.exe.exe", "gitleaks.exe"),
        ("C:\\bin\\gitleaks2.exe", "gitleaks2"),
        ("/opt/leaks.exe", "leaks"),
        ("leaks", "leaks"),
    ],
)
def test_tool_name_is_the_base_name_lower_cased_without_one_exe(value, name):
    """REQ-016: brief #504 answer 1 (a Windows path on any OS; one trailing `.exe` removed)."""
    import evidence

    assert evidence.tool_name(value) == name


@pytest.mark.parametrize(
    "tool",
    ["C:\\Program Files\\gitleaks\\gitleaks.EXE", "C:\\Tools\\GITLEAKS.exe", "gitleaks"],
)
def test_any_case_of_gitleaks_with_or_without_exe_is_the_same_tool(repo, outside, tool):
    """REQ-016: brief #504 answers 1 and 3 (the scan is repeated, the record agrees)."""
    project(repo, outside)
    scan = scanner(outside / "bin", 0)
    record = scan_record(repo, outside, tool)
    proc = check(repo, outside, str(record), "--sample", "10", scan=scan)
    assert DIFFERS not in proc.stdout, proc.stdout + proc.stderr
    assert re.search(
        r"^evidence: re-ran secret-scan: exit 0 \(recorded 0\) same", proc.stdout, re.M
    ), proc.stdout
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert LINE.search(proc.stdout).group(1) == "agrees"


def test_a_windows_record_without_gitleaks_here_is_not_repeatable_not_differs(repo, outside):
    """REQ-016: brief #504 answer 1 (`not repeatable` when gitleaks is not installed stays)."""
    project(repo, outside)
    record = scan_record(repo, outside, "C:\\Tools\\gitleaks.EXE")
    proc = check(repo, outside, str(record), "--sample", "10")
    assert DIFFERS not in proc.stdout, proc.stdout
    assert "evidence: not repeatable: secret-scan (gitleaks is not installed here)" in proc.stdout


@pytest.mark.parametrize(
    "tool", ["C:\\Tools\\gitleaks2.exe", "leaks", "leaks.exe", "C:\\Tools\\gitleaks.exe.exe"]
)
def test_another_tool_name_still_differs_on_argv(repo, outside, tool):
    """REQ-016: brief #504 answers 2 and 3 (nothing else is loosened)."""
    project(repo, outside)
    scan = scanner(outside / "bin", 0)
    record = scan_record(repo, outside, tool)
    proc = check(repo, outside, str(record), "--sample", "10", scan=scan)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert DIFFERS in proc.stdout
    assert "re-ran secret-scan" not in proc.stdout
    assert not (outside / "bin" / "args.txt").exists()


def test_a_changed_tail_still_differs_on_argv(repo, outside):
    """REQ-016: brief #504 answers 2 and 3 (the tail must still match exactly)."""
    project(repo, outside)
    scan = scanner(outside / "bin", 0)
    changed = [*tail(repo)[:-1], "--no-git", "."]
    record = scan_record(repo, outside, "C:\\Tools\\gitleaks.EXE", changed)
    proc = check(repo, outside, str(record), "--sample", "10", scan=scan)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert DIFFERS in proc.stdout
    assert "re-ran secret-scan" not in proc.stdout
