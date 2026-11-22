"""A gate-step change runs every gate-runner test (brief #1750; ADR-0731).

`run_gates.py` loads each gate step by name (`importlib.import_module`), so no test file imports
a module of `scripts/agk/gates/` and the importer rule selects nothing for one. The
`scripts/agk/gates/*.py` entry of `[[testing.map]]` in the kit's own `agk.toml` therefore names
every test file of `tests/kit/` and `tests/kit_dev/` that runs the runner: one with an
`import run_gates` or `from run_gates` line, or one that names `run_gates.py` in a string outside
a docstring (a command that starts it, Q-30A-1). This test lives in `tests/kit_dev/` because
`tests/kit/` runs in every project, whose `agk.toml` has no kit map.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

SELF = Path(__file__).resolve()  # names the runner in its own fixtures, and runs no gate
ROOT = SELF.parents[2]
WILDCARD = "scripts/agk/gates/*.py"
FOLDERS = ("tests/kit", "tests/kit_dev")
IMPORT = re.compile(r"^\s*(import|from)\s+run_gates\b", re.MULTILINE)
MISSING = "{n} test files of {folder}/ that run the gate runner are missing from testing.map"
GONE = "testing.map names a test file that does not exist for the gate steps"
SCOPES = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def docstrings(tree: ast.AST) -> set[int]:
    """The ids of the string nodes that are docstrings."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, SCOPES) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                found.add(id(first.value))
    return found


def runs_runner(text: str) -> bool:
    """True when the file imports the runner or names `run_gates.py` in a non-docstring."""
    if IMPORT.search(text):
        return True
    tree = ast.parse(text)
    skip = docstrings(tree)
    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and "run_gates.py" in node.value
        and id(node) not in skip
        for node in ast.walk(tree)
    )


def runner_tests(root: Path) -> dict[str, set[str]]:
    """The test files of each folder that run the gate runner."""
    return {
        folder: {
            p.relative_to(root).as_posix()
            for p in (root / folder).glob("test_*.py")
            if p.resolve() != SELF and runs_runner(p.read_text(encoding="utf-8"))
        }
        for folder in FOLDERS
    }


def problems(root: Path) -> list[str]:
    """One message per path class missing a runner test, and one for a named file gone."""
    table = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    entries = [e for e in table.get("testing", {}).get("map", []) if e.get("code") == WILDCARD]
    named = {t for e in entries for t in e.get("tests", [])}
    out = []
    for folder, files in runner_tests(root).items():
        if files - named:
            out.append(MISSING.format(n=len(files - named), folder=folder))
    if any(not (root / t).is_file() for t in named):
        out.append(GONE)
    return out


def fake(tmp_path: Path, files: dict[str, str], tests: str) -> Path:
    for rel in FOLDERS:
        (tmp_path / rel).mkdir(parents=True)
    for rel, text in files.items():
        (tmp_path / rel).write_text(text, encoding="utf-8")
    toml = f'[[testing.map]]\ncode = "{WILDCARD}"\ntests = [{tests}]\n'
    (tmp_path / "agk.toml").write_text(toml, encoding="utf-8")
    return tmp_path


def test_gate_entry_names_every_runner_test() -> None:
    """REQ-016: a change to any gate step selects every test that runs the gate steps."""
    assert problems(ROOT) == []


def test_missing_runner_test_is_named_by_class(tmp_path: Path) -> None:
    """REQ-016: a runner test left out is refused naming its path class and the setting."""
    root = fake(
        tmp_path,
        {
            "tests/kit/test_a.py": "import run_gates\n",
            "tests/kit_dev/test_b.py": '"""Names run_gates.py in a docstring only."""\n',
        },
        "",
    )
    assert problems(root) == [MISSING.format(n=1, folder="tests/kit")]


def test_subprocess_command_counts_and_gone_file_is_refused(tmp_path: Path) -> None:
    """REQ-016: a command starting `run_gates.py` counts (Q-30A-1); a gone named file fails."""
    command = 'CMD = ["python3", "scripts/agk/run_gates.py"]\n'
    root = fake(tmp_path, {"tests/kit_dev/test_c.py": command}, '"tests/kit/test_gone.py"')
    assert problems(root) == [MISSING.format(n=1, folder="tests/kit_dev"), GONE]
