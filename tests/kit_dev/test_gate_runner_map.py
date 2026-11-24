"""A gate-step change runs every gate-runner test (brief #1750; ADR-0731).

`run_gates.py` loads each gate step by name (`importlib.import_module`), so no test file imports
a module of `scripts/agk/gates/` and the importer rule selects nothing for one. The
`scripts/agk/gates/*.py` entry of `[[testing.map]]` in the kit's own `agk.toml` therefore names
every test file of `tests/kit/` and `tests/kit_dev/` that runs the runner: one with an
`import run_gates` or `from run_gates` line, or one that names `run_gates.py` in a string outside
a docstring (a command that starts it, Q-30A-1). The rule itself is
`check_kit_tests.runner_problems` (brief #1878, ADR-0777), so governance holds it with or without
`prepush.py --quick`; this file is the full suite's copy over the kit's whole tree.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import check_kit_tests  # noqa: E402  (brief #1878, ADR-0777: the rule's one source)

WILDCARD = check_kit_tests.GATES
FOLDERS = check_kit_tests.folders_of("tests/kit")
MISSING = check_kit_tests.MISSING
GONE = check_kit_tests.GONE


def problems(root: Path) -> list[str]:
    """One message per path class missing a runner test, and one for a named file gone."""
    table = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    entries = [
        {"code": e.get("code"), "tests": list(e.get("tests", []))}
        for e in table.get("testing", {}).get("map", [])
    ]
    return check_kit_tests.runner_problems(root, entries, FOLDERS)


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
