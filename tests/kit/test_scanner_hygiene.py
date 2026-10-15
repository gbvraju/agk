"""Kit source under a project's own scanners: justified suppressions and clean types (ADR-0010).

Pure checks of the source text; bandit and mypy are run only where they are installed.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KIT_SOURCE = ("scripts/agk", ".claude/hooks", "tests/kit")
SPAWNERS = {"run", "Popen", "call", "check_call", "check_output"}
# Built from parts so that this file carries no suppression comment of its own.
MARK = "# " + "nosec"
WITH_REASON = re.compile(re.escape(MARK) + r" (B\d{3}(?: B\d{3})*) - \S")
IGNORE = "type" + ": ignore"


def sources() -> list[Path]:
    found = []
    for rel in KIT_SOURCE:
        base = ROOT / rel
        if base.is_dir():
            found.extend(sorted(base.glob("*.py")))
    return found


def codes_on(line: str) -> set[str]:
    match = WITH_REASON.search(line)
    return set(match.group(1).split()) if match else set()


def partial_path_executable(call: ast.Call) -> bool:
    """True when the first argument is a list whose first item is a bare program name."""
    if not call.args or not isinstance(call.args[0], (ast.List, ast.Tuple)):
        return False
    elements = call.args[0].elts
    first = elements[0] if elements else None
    return (
        isinstance(first, ast.Constant)
        and isinstance(first.value, str)
        and not first.value.startswith("/")
    )


def test_kit_source_is_found():
    """REQ-010: the scan below is not vacuous."""
    names = {p.name for p in sources()}
    assert {"common.py", "stop_check.py", "conftest.py"} <= names


def test_every_subprocess_import_and_call_has_a_justified_suppression():
    """REQ-010: ADR-0010 decision 1. Each import and each call names its codes and a reason."""
    problems = []
    for path in sources():
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import) and any(a.name == "subprocess" for a in node.names):
                if "B404" not in codes_on(lines[node.lineno - 1]):
                    problems.append(f"{path.name}:{node.lineno} import needs B404 and a reason")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
                and node.func.attr in SPAWNERS
            ):
                want = {"B603"} | ({"B607"} if partial_path_executable(node) else set())
                have = codes_on(lines[node.lineno - 1])
                if have != want:
                    where = f"{path.name}:{node.lineno}"
                    problems.append(f"{where} needs exactly {sorted(want)}, has {sorted(have)}")
    assert not problems, "\n".join(problems)


def test_no_blanket_suppression_and_no_type_ignore():
    """REQ-010: ADR-0010 decisions 1 and 2. Every suppression has codes and a reason."""
    problems = []
    for path in sources():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if MARK in line and not WITH_REASON.search(line):
                problems.append(f"{path.name}:{number} suppression without codes and a reason")
            if IGNORE in line:
                problems.append(f"{path.name}:{number} type comment instead of a fix")
    assert not problems, "\n".join(problems)


def installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


@pytest.mark.skipif(not installed("bandit"), reason="bandit is not installed")
def test_bandit_finds_only_asserts_in_kit_source():
    """REQ-010: ADR-0010. Without the bare-assert rule B101, bandit is quiet on kit source."""
    proc = subprocess.run(  # nosec B603 - fixed argument list from sys.executable, no shell
        [sys.executable, "-m", "bandit", "-q", "-r", *KIT_SOURCE, "--skip", "B101"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-800:]


@pytest.mark.skipif(not installed("mypy"), reason="mypy is not installed")
def test_mypy_is_clean_on_scripts():
    """REQ-010: ADR-0010 decision 2. The four findings are fixed in the code."""
    proc = subprocess.run(  # nosec B603 - fixed argument list from sys.executable, no shell
        [sys.executable, "-m", "mypy", "scripts/agk"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-800:]
