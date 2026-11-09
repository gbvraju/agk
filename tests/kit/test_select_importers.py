"""Tests of the selection of a core file in scripts/agk/impact.py (brief #878 answer 2, ADR-0393).

A changed code file selects the tests its `[[testing.map]]` entries name and the tests of every file
that imports it, one level. Saved changed-file lists in a temporary git repository; no network.
"""

from __future__ import annotations

import impact

BASE = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
MAP = (
    'always_full = ["tests/conftest.py"]\n'
    'map = [ { code = "src/core.py", tests = ["tests/test_core.py"] },\n'
    '  { code = "src/user.py", tests = ["tests/test_user.py"] },\n'
    '  { code = "src/far.py", tests = ["tests/test_far.py"] } ]\n'
)
FILES = {
    "src/core.py": "VALUE = 1\n",
    "src/user.py": "import core\n",
    "src/far.py": "import user\n",
    "src/alone.py": "VALUE = 2\n",
    "tests/conftest.py": "# fixtures\n",
    "tests/test_core.py": "# core\n",
    "tests/test_user.py": "# user\n",
    "tests/test_far.py": "# far\n",
    "tests/test_direct.py": "from src import core\n",
    "tests/test_other.py": "# other\n",
}


def start(repo, profile: str = "balanced") -> None:
    toml = BASE + f'[testing]\nprofile = "{profile}"\n' + MAP
    repo.commit({"agk.toml": toml, **FILES}, "base")
    repo.branch("feature")


def change(repo, *paths: str) -> impact.Impact:
    repo.commit({p: FILES.get(p, "") + "# changed\n" for p in paths}, "change")
    base = repo.git("rev-parse", "main").strip()
    return impact.impact(repo.root, base, repo.git("rev-parse", "HEAD").strip())


def names(found: impact.Impact) -> list[str]:
    return [s.test for s in found.selected]


def test_a_core_file_selects_its_mapped_tests_and_its_importers_and_is_not_full(repo):
    """REQ-051: brief #878 answers 2 and 7 (a core file selects widely, not fully)."""
    start(repo)
    found = change(repo, "src/core.py")
    assert found.full is False and found.reason is None
    assert names(found) == ["tests/test_core.py", "tests/test_direct.py", "tests/test_user.py"]


def test_the_importers_are_one_level_only(repo):
    """REQ-051: brief #878 answer 2 (`src/far.py` imports an importer; its tests do not run)."""
    start(repo)
    assert "tests/test_far.py" not in names(change(repo, "src/core.py"))


def test_the_plan_prints_the_counts_of_a_file(repo):
    """REQ-051: brief #878 answer 2 (`selected: <file> -> <k> tests (<j> by importers)`)."""
    start(repo)
    lines = impact.text(change(repo, "src/core.py"))
    assert "selected: src/core.py -> 3 tests (2 by importers)" in lines


def test_a_file_nothing_imports_counts_no_importers(repo):
    """REQ-051: brief #878 answer 2 (the same line with none by importers)."""
    start(repo)
    found = change(repo, "src/far.py")
    assert names(found) == ["tests/test_far.py"]
    assert "selected: src/far.py -> 1 tests (0 by importers)" in impact.text(found)


def test_each_test_says_why_it_was_selected(repo):
    """REQ-051: brief #878 answer 2 (a test an importer brought names the importer's file)."""
    start(repo)
    lines = impact.text(change(repo, "src/core.py"))
    assert "  file: tests/test_user.py (src/user.py imports src/core.py)" in lines
    assert "  file: tests/test_direct.py (imports src/core.py)" in lines


def test_a_test_infrastructure_file_is_still_full(repo):
    """REQ-051: brief #878 answers 1 and 7 (a change to `conftest.py` is full)."""
    start(repo)
    found = change(repo, "tests/conftest.py")
    assert found.full is True
    assert found.reason == "always_full tests/conftest.py matches tests/conftest.py"


def test_the_fast_profile_selects_importers_too(repo):
    """REQ-051: brief #878 answer 2 (the rule has no profile: importers only add tests)."""
    start(repo, "fast")
    assert "tests/test_user.py" in names(change(repo, "src/core.py"))


def test_the_thorough_profile_stays_full(repo):
    """REQ-051: SPEC-0055 rule 6 as amendment 153 keeps it (`thorough` is unchanged)."""
    start(repo, "thorough")
    assert change(repo, "src/core.py").full is True


def test_a_file_with_an_unreadable_importer_still_selects_its_tests(repo):
    """REQ-051: brief #878 answer 2 (a file that cannot be parsed adds nothing)."""
    start(repo)
    repo.commit({"src/broken.py": "def (:\n"}, "broken")
    found = change(repo, "src/alone.py")
    assert found.full is True  # no map entry and no test names it: rule 6 unchanged
    found = change(repo, "src/core.py")
    assert "tests/test_core.py" in names(found)


def test_the_json_names_the_importer_selection(repo):
    """REQ-051: brief #878 answer 2 (the JSON of the plan marks a test an importer brought)."""
    start(repo)
    selected = {s["file"]: s for s in change(repo, "src/core.py").data()["selected"]}
    assert selected["tests/test_user.py"]["code"] == impact.IMPORTER
    assert selected["tests/test_user.py"]["changed"] == "src/core.py"
    assert selected["tests/test_core.py"]["code"] == "src/core.py"
