"""This repository's intelligent testing (brief #578, ADR-0285).

`agk.toml` holds a `[testing]` table (`profile = "balanced"`, `pr_tests = "selected"`, an
`always_full` list for the shared core and a `map` from each script under `scripts/agk/` to the
test files that reach it) and a `[proof]` area for the kit's tests, so that a builder's prepush
runs a change's own tests and the tests its change can affect, while a push and a release run the
full suite. Nothing here changes code: the tests read the real `agk.toml` and run the kit's own
`test_plan.py`, `impact.py`, `prepush.regression_sets` and `project_tests.plan` on invented change
sets in a temporary git repository that mirrors the file names of this one (empty files).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import impact  # noqa: E402
import prepush  # noqa: E402
import project_tests  # noqa: E402
from common import proof_areas  # noqa: E402

CORE = [
    "scripts/agk/common.py",
    "kit/agk-kit.mk",
    "Makefile",
    "agk.mk",
    ".github/workflows/governance.yml",
    "tests/kit/conftest.py",
    "tests/kit/pytest.ini",
]


def table() -> dict:
    found = impact.testing_table(ROOT)
    assert found is not None, "agk.toml has no [testing] table"
    return found


def kit_tests() -> list[str]:
    return sorted(
        str(p.relative_to(ROOT))
        for folder in ("tests/kit", "tests/kit_dev")
        for p in (ROOT / folder).glob("test_*.py")
    )


def test_the_table_is_accepted_with_the_owners_settings():
    """REQ-016: brief #578 answer 1 and the third bullet of answer 2 (`impact.testing_table`
    accepts the table; balanced profile, selected pull-request tests)."""
    found = table()
    assert found["profile"] == "balanced"
    assert impact.pr_tests(ROOT) == "selected"
    assert found["map"], "the map is empty"
    assert proof_areas(ROOT) is not None


@pytest.mark.parametrize("path", CORE)
def test_the_shared_core_makes_the_selection_full(path):
    """REQ-016: brief #578 answer 1 (`always_full` covers the shared core)."""
    assert any(impact.matches(path, g) for g in table()["always_full"]), path


def test_every_script_is_covered_by_an_entry_or_always_full():
    """REQ-016: brief #578 answer 2, first bullet (nothing under `scripts/agk/` changes untested:
    each script matches `always_full`, or an entry whose tests select an existing test file)."""
    found, tests = table(), kit_tests()
    uncovered = []
    for script in sorted(SCRIPTS.glob("*.py")):
        path = str(script.relative_to(ROOT))
        if any(impact.matches(path, g) for g in found["always_full"]):
            continue
        entries = [e for e in found["map"] if impact.matches(path, e["code"])]
        if not any(impact.matches(t, g) for e in entries for g in e["tests"] for t in tests):
            uncovered.append(path)
    assert uncovered == []


def test_every_test_glob_of_the_map_names_an_existing_test_file():
    """REQ-016: brief #578 answer 1 (the map is built from the code; a stale name is caught)."""
    tests = kit_tests()
    globs = {g for e in table()["map"] for g in e["tests"]}
    stale = sorted(g for g in globs if not any(impact.matches(t, g) for t in tests))
    assert stale == []


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return proc.stdout


@pytest.fixture
def mirror(tmp_path: Path) -> Path:
    """A git repository with this repository's `agk.toml` and the names of its scripts and kit
    tests as empty files, so the real map selects from the real names."""
    root = tmp_path / "mirror"
    root.mkdir()
    shutil.copy(ROOT / "agk.toml", root / "agk.toml")
    names = [str(p.relative_to(ROOT)) for p in SCRIPTS.glob("*.py")] + kit_tests() + CORE
    names.append("docs/guides/example.md")
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "builder")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def change(root: Path, *paths: str) -> str:
    base = git(root, "rev-parse", "HEAD").strip()
    for path in paths:
        with (root / path).open("a", encoding="utf-8") as out:
            out.write("# invented change\n")
    git(root, "commit", "-q", "-am", "change")
    return base


def plan(root: Path, base: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "test_plan.py"), "--json", "--base", base, "--head", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)["regression"]


def test_one_script_gives_a_narrow_selection(mirror):
    """REQ-016: brief #578 answer 2, second bullet (one script: a narrow selection)."""
    base = change(mirror, "scripts/agk/stalls.py")
    found = plan(mirror, base)
    assert found["table"] is True and found["full"] is False
    files = [s["file"] for s in found["selected"]]
    assert "tests/kit/test_stalls.py" in files
    assert 0 < len(files) < len(kit_tests())
    assert found["unmapped"] == []


def test_the_shared_core_gives_the_full_suite(mirror):
    """REQ-016: brief #578 answer 2, second bullet (`common.py`: the full suite)."""
    base = change(mirror, "scripts/agk/common.py")
    found = plan(mirror, base)
    assert found["full"] is True
    assert found["reason"].startswith("always_full ")


def test_documentation_only_selects_none(mirror):
    """REQ-016: brief #578 answer 2, second bullet (documentation only: none)."""
    base = change(mirror, "docs/guides/example.md")
    found = plan(mirror, base)
    assert found["full"] is False and found["selected"] == []


def test_an_unmapped_file_makes_the_selection_full(mirror):
    """REQ-016: brief #578 answer 1 (balanced: a file no entry covers runs the full suite)."""
    (mirror / "kit").mkdir(exist_ok=True)
    (mirror / "kit" / "invented.json").write_text("{}\n", encoding="utf-8")
    git(mirror, "add", "-A")
    git(mirror, "commit", "-q", "-m", "add")
    base = change(mirror, "kit/invented.json")
    found = plan(mirror, base)
    assert found["full"] is True and found["unmapped"] == ["kit/invented.json"]


def test_prepush_runs_the_selection_through_the_proof_area(mirror):
    """REQ-016: brief #578 answer 1 (a builder's prepush runs the selected files, not the full
    `project_tests`, because the `[proof]` area takes single files)."""
    base = change(mirror, "scripts/agk/stalls.py")
    found = impact.impact(mirror, base, "HEAD")
    sets, notes = prepush.regression_sets(mirror, found, proof_areas(mirror))
    assert [name for name, *_ in sets] != ["full"]
    assert len(sets) == 1
    assert "tests/kit/test_stalls.py" in sets[0][1]
    assert not any("not run" in n for n in notes)


def test_a_push_still_runs_the_full_suite(mirror, monkeypatch):
    """REQ-016: brief #578 answer 3 (a push runs the full suite; SPEC-0044 rule 1)."""
    monkeypatch.setenv("EVENT", "push")
    runs, lines = project_tests.plan(mirror, "the full command")
    assert runs == [("full", "the full command", ".", "event push")]
    assert "project tests: full (event push)" in lines
    assert os.environ["EVENT"] == "push"
