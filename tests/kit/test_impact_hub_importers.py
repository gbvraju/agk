"""Tests of `[testing] hub_importers` in scripts/agk/impact.py (brief #2055 answers 2, 4, 5).

ADR-0853.

A changed code file with more direct importers that are not test files than the limit is a hub: it
selects its own entries' tests, the tests that name it and the test files that import it, and not
the map tests of its importer scripts. Saved changed-file lists in a temporary git repository
(invented data, example.com); no network.
"""

from __future__ import annotations

import impact
import project_tests
import pytest
from common import CheckError

BASE = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
MAP = (
    'always_full = ["tests/conftest.py"]\n'
    'map = [ { code = "src/core.py", tests = ["tests/test_core.py"] },\n'
    '  { code = "src/a.py", tests = ["tests/test_a.py"] },\n'
    '  { code = "src/b.py", tests = ["tests/test_b.py"] },\n'
    '  { code = "src/c.py", tests = ["tests/test_c.py"] } ]\n'
)
FILES = {
    "src/core.py": 'HOME = "https://example.com"\n',
    "src/a.py": "import core\n",
    "src/b.py": "import core\n",
    "src/c.py": "import core\n",
    "tests/conftest.py": "# fixtures\n",
    "tests/test_core.py": "# core\n",
    "tests/test_a.py": "# a\n",
    "tests/test_b.py": "# b\n",
    "tests/test_c.py": "# c\n",
    "tests/test_direct.py": "from src import core\n",
    "tests/test_other.py": "# other\n",
}
HUB = "hub_importers must be a whole number of at least 1 (setting: testing.hub_importers)"
EXPANDED = [
    "tests/test_a.py",
    "tests/test_b.py",
    "tests/test_c.py",
    "tests/test_core.py",
    "tests/test_direct.py",
]


def start(repo, extra: str = "", profile: str = "balanced", head: str = "") -> None:
    toml = BASE + head + f'[testing]\nprofile = "{profile}"\n' + extra + MAP
    repo.commit({"agk.toml": toml, **FILES}, "base")
    repo.branch("feature")


def change(repo, *paths: str) -> impact.Impact:
    repo.commit({p: FILES.get(p, "") + "# changed\n" for p in paths}, "change")
    base = repo.git("rev-parse", "main").strip()
    return impact.impact(repo.root, base, repo.git("rev-parse", "HEAD").strip())


def names(found: impact.Impact) -> list[str]:
    return [s.test for s in found.selected]


def test_a_hub_adds_none_of_its_importers_map_tests(repo):
    """REQ-051: brief #2055 answer 2 (three importers above a limit of 2: none of their tests)."""
    start(repo, "hub_importers = 2\n")
    found = change(repo, "src/core.py")
    assert found.full is False and found.reason is None
    assert names(found) == ["tests/test_core.py", "tests/test_direct.py"]


def test_a_hub_keeps_a_test_file_that_imports_it(repo):
    """REQ-051: brief #2055 answer 2 (the test files that import a hub directly still run)."""
    start(repo, "hub_importers = 1\n")
    assert "tests/test_direct.py" in names(change(repo, "src/core.py"))


def test_a_hub_prints_the_hub_line_in_place_of_the_importers_line(repo):
    """REQ-051: brief #2055 answer 2 (the line names the count and the setting)."""
    start(repo, "hub_importers = 2\n")
    lines = impact.text(change(repo, "src/core.py"))
    assert (
        "selected: src/core.py -> 2 tests (hub: 3 importers, importers not expanded; "
        "setting: testing.hub_importers)"
    ) in lines
    assert not any("by importers" in line for line in lines)


def test_a_file_at_exactly_the_limit_is_not_a_hub(repo):
    """REQ-051: brief #2055 answer 5 (more than the limit; three importers and a limit of 3)."""
    start(repo, "hub_importers = 3\n")
    found = change(repo, "src/core.py")
    assert names(found) == EXPANDED
    assert "selected: src/core.py -> 5 tests (4 by importers)" in impact.text(found)


def test_without_the_key_the_plan_is_as_before(repo):
    """REQ-051: brief #2055 answer 2 (absent: today's expansion, the same lines)."""
    start(repo)
    found = change(repo, "src/core.py")
    assert names(found) == EXPANDED
    assert impact.text(found) == [
        "regression: 5 test files selected",
        "  file: tests/test_a.py (src/a.py imports src/core.py)",
        "  file: tests/test_b.py (src/b.py imports src/core.py)",
        "  file: tests/test_c.py (src/c.py imports src/core.py)",
        "  file: tests/test_core.py (src/core.py matches code src/core.py, tests "
        "tests/test_core.py)",
        "  file: tests/test_direct.py (imports src/core.py)",
        "selected: src/core.py -> 5 tests (4 by importers)",
    ]


def test_a_file_below_the_limit_expands_as_before(repo):
    """REQ-051: brief #2055 answer 2 (`src/a.py`, which nothing imports, is no hub)."""
    start(repo, "hub_importers = 1\n")
    found = change(repo, "src/a.py")
    assert names(found) == ["tests/test_a.py"]
    assert "selected: src/a.py -> 1 tests (0 by importers)" in impact.text(found)


@pytest.mark.parametrize("value", ["0", "-3", "true", "2.5", '"20"'])
def test_a_bad_limit_is_refused_naming_the_setting_never_the_value(repo, value):
    """REQ-051: brief #2055 answer 4 (0, negative, boolean, float and string are refused)."""
    start(repo, f"hub_importers = {value}\n")
    with pytest.raises(CheckError) as caught:
        impact.testing_table(repo.root)
    assert str(caught.value) == HUB
    assert value.strip('"') not in str(caught.value).replace("testing", "")


def test_the_config_tables_take_the_key():
    """REQ-051: brief #2055 answer 4 (`impact.KEYS` and `config.TABLE_KEYS["testing"]`)."""
    import config

    assert "hub_importers" in impact.KEYS
    assert "hub_importers" in config.TABLE_KEYS["testing"]


def test_always_full_wins_over_the_limit(repo):
    """REQ-051: brief #2055 answers 4 and 5 (a hub that matches `always_full` is full)."""
    toml = (
        BASE
        + "[testing]\nhub_importers = 1\n"
        + MAP.replace(
            '["tests/conftest.py"]', '["tests/conftest.py", "src/core.py"]  # full: invented'
        )
    )
    repo.commit({"agk.toml": toml, **FILES}, "base")
    repo.branch("feature")
    found = change(repo, "src/core.py")
    assert found.full is True and found.reason == "always_full src/core.py matches src/core.py"


def test_thorough_is_full_and_reads_no_limit(repo):
    """REQ-051: brief #2055 answer 4 (`thorough`: full, as before)."""
    start(repo, "hub_importers = 1\n", "thorough")
    found = change(repo, "src/core.py")
    assert found.full is True and found.reason == "profile thorough"


def test_fast_reads_the_limit(repo):
    """REQ-051: brief #2055 answer 4 (`fast` reads no names and the limit)."""
    start(repo, "hub_importers = 2\n", "fast")
    assert names(change(repo, "src/core.py")) == ["tests/test_core.py", "tests/test_direct.py"]


def test_fast_without_the_key_expands_as_before(repo):
    """REQ-051: brief #2055 answer 4 (`fast` without the key: today's expansion)."""
    start(repo, profile="fast")
    assert names(change(repo, "src/core.py")) == EXPANDED


PROOF = '[proof]\napp = { dirs = ["tests"], patterns = ["test_*.py"], command = "echo {files}" }\n'


def test_a_selected_project_run_uses_the_hub_selection(repo, monkeypatch):
    """REQ-051: brief #2055 answer 4 (`pr_tests = "selected"` on a pull request runs the plan)."""
    start(
        repo,
        'pr_tests = "selected"\nhub_importers = 2\n',
        head="project_tests = 'exit 0'\n" + PROOF,
    )
    repo.commit({"src/core.py": "# changed\n"}, "change")
    monkeypatch.setenv("EVENT", "pull_request")
    monkeypatch.setenv("AGK_BASE", repo.git("rev-parse", "main").strip())
    runs, lines = project_tests.plan(repo.root, "exit 0")
    assert [name for name, *_ in runs] == ["app"]
    assert "tests/test_direct.py" in runs[0][1] and "tests/test_a.py" not in runs[0][1]
    assert any("(hub: 3 importers" in line for line in lines)


def test_pr_tests_full_keeps_ci_full_and_the_plan_narrow(repo):
    """REQ-051: brief #2055 answer 4 (`pr_tests = "full"`: CI's full suite; the plan, which
    prepush, evidence and test_plan print, is still the narrower one)."""
    start(repo, 'pr_tests = "full"\nhub_importers = 2\n')
    found = change(repo, "src/core.py")
    assert impact.pr_tests(repo.root) == "full"
    assert found.full is False
    assert names(found) == ["tests/test_core.py", "tests/test_direct.py"]
