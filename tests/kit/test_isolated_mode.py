"""Every kit script runs under `python3 -I` (brief #270, ADR-0161).

The conductor's guard allows Python only as `python3 -I <scratch>/scripts/agk/<name>.py`. Isolated
mode leaves the script's own folder off the import path, so a kit script that imports another
(`from common import ...`) failed at once. Each such script now puts its own resolved folder first
on the path before those imports, and nothing else: not the current directory, not the environment.
"""

from __future__ import annotations

import ast
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
NAMES = {p.stem for p in SCRIPTS.glob("*.py")}
LINE = "sys.path.insert(0, str(Path(__file__).resolve().parent))"


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def kit_imports(path: Path) -> list[ast.stmt]:
    """The import statements of PATH, at any depth, that name another kit script."""
    found = []
    for node in ast.walk(tree(path)):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in NAMES:
                found.append(node)
        elif isinstance(node, ast.Import):
            if any(a.name.split(".")[0] in NAMES for a in node.names):
                found.append(node)
    return found


def with_main() -> list[str]:
    return sorted(
        p.name
        for p in SCRIPTS.glob("*.py")
        if any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree(p).body)
    )


@pytest.mark.parametrize("name", with_main())
def test_every_script_with_a_main_starts_under_isolated_mode(tmp_path, name):
    """Brief #270 answer 2 (REQ-039): `python3 -I <script> --help` from an unrelated folder, no
    import error; what the script then says about `--help` is its own usage."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / name), "--help"],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert "ModuleNotFoundError" not in proc.stderr, proc.stderr
    assert "ImportError" not in proc.stderr, proc.stderr


def test_the_folder_goes_first_on_the_path_before_any_kit_import_and_nothing_else():
    """Brief #270 answer 1 (REQ-039): by the script's resolved location only; no `os.getcwd()`,
    no environment variable, no relative path."""
    importing = sorted(p for p in SCRIPTS.glob("*.py") if kit_imports(p))
    assert len(importing) > 30
    for path in importing:
        text = path.read_text(encoding="utf-8")
        assert text.count(LINE) == 1, path.name
        line = next(i for i, ln in enumerate(text.splitlines(), 1) if ln.startswith(LINE))
        assert all(node.lineno > line for node in kit_imports(path)), path.name
    for path in SCRIPTS.glob("*.py"):
        for node in ast.walk(tree(path)):
            if isinstance(node, ast.Attribute) and node.attr in ("insert", "append"):
                if isinstance(node.value, ast.Attribute) and node.value.attr == "path":
                    segment = ast.get_source_segment(path.read_text(encoding="utf-8"), node)
                    assert segment in ("sys.path.insert",), (path.name, segment)


def test_the_measured_check_brief_runs_under_isolated_mode(tmp_path):
    """Brief #270 Measured (REQ-039): `python3 -I scripts/agk/check_brief.py <a brief file>`."""
    brief = tmp_path / "brief.md"
    brief.write_text("Brief: a test\n", encoding="utf-8")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_brief.py"), str(brief)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert "ModuleNotFoundError" not in proc.stderr, proc.stderr
    assert proc.stdout.startswith(("ok brief", "FAIL brief")), proc.stdout + proc.stderr
