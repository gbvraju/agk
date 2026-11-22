"""Tests of SPEC-0055 rule 6 in scripts/agk/impact.py: an uncovered file selects its tests.

Brief #773, ADR-0359. Saved changed-file lists in a temporary git repository; no network.
Answers 1, 2 and 5 of the brief: the data-file entries of this repository's map, the rule
itself, and the same rule in a project's run.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import doctor
import impact
import project_tests
import pytest

ROOT = Path(__file__).resolve().parents[2]
MAP = (
    'map = [ { code = "app/billing/**", tests = ["tests/test_pay.py"] },\n'
    '  { code = "app/stale/**", tests = ["tests/test_gone.py"] } ]\n'
)
BASE = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
FILES = {
    "app/billing/pay.py": "# pay\n",
    "app/stale/old.py": "# old\n",
    "data/prices.json": "{}\n",
    "lone/alone.json": "{}\n",
    "kit/new.json": "{}\n",
    "tests/test_pay.py": "# pay\n",
    "tests/test_prices.py": 'FILE = "data/prices.json"\n',
    "tests/test_other.py": "# nothing here\n",
    "README.md": "# readme\n",
}


def start(repo, profile: str = "balanced", extra: str = "", files: dict | None = None) -> None:
    toml = BASE + "project_tests = 'exit 0'\n[testing]\n" + f'profile = "{profile}"\n' + extra + MAP
    repo.commit({"agk.toml": toml, **FILES, **(files or {})}, "base")
    repo.branch("feature")


def change(repo, *paths: str) -> impact.Impact:
    repo.commit({p: "# changed\n" for p in paths}, "change")
    return result(repo)


def result(repo) -> impact.Impact:
    base = repo.git("rev-parse", "main").strip()
    return impact.impact(repo.root, base, repo.git("rev-parse", "HEAD").strip())


def picked(found: impact.Impact) -> list[str]:
    return [s.test for s in found.selected]


def test_a_named_data_file_selects_the_tests_that_name_it(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (the test that names the path runs, not the full suite)."""
    start(repo)
    found = change(repo, "data/prices.json")
    assert found.full is False and found.reason is None
    assert picked(found) == ["tests/test_prices.py"]
    assert found.unmapped == ["data/prices.json"]
    assert "unmapped: data/prices.json -> 1 tests that name it" in impact.text(found)


def test_a_file_whose_folder_is_named_selects_those_tests(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (a test that names the file's folder is selected)."""
    start(
        repo,
        files={"tests/test_folder.py": 'WHERE = "config/extra/"\n', "config/extra/a.txt": "a\n"},
    )
    found = change(repo, "config/extra/a.txt")
    assert found.full is False and picked(found) == ["tests/test_folder.py"]


def test_a_two_part_folder_named_without_its_slash_counts(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (`config/extra` names the folder as `config/extra/` does)."""
    start(
        repo,
        files={"tests/test_folder.py": 'WHERE = "config/extra"\n', "config/extra/a.txt": "a\n"},
    )
    assert picked(change(repo, "config/extra/a.txt")) == ["tests/test_folder.py"]


def test_the_word_for_a_top_folder_does_not_name_it(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (the bare word `kit` in prose is not the folder `kit/`)."""
    start(repo, files={"tests/test_word.py": "# the kit is here\n"})
    found = change(repo, "kit/new.json")
    assert found.full is True and picked(found) == []


def test_a_top_folder_named_as_a_path_counts(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (`kit/other.json` names the folder `kit/`)."""
    start(repo, files={"tests/test_kit.py": 'OTHER = "kit/other.json"\n'})
    found = change(repo, "kit/new.json")
    assert found.full is False and picked(found) == ["tests/test_kit.py"]


def test_a_longer_path_does_not_name_the_file_or_its_folder(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (`tests/kit/new.json` names neither file nor `kit/`)."""
    start(repo, files={"tests/test_long.py": 'OTHER = "tests/kit/new.json"\n'})
    assert change(repo, "kit/new.json").full is True


def test_no_test_names_it_and_the_selection_is_full(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (full only when no test names it, and the line says 0)."""
    start(repo)
    found = change(repo, "lone/alone.json")
    assert found.full is True and found.reason == "profile balanced: 1 unmapped file"
    assert "unmapped: lone/alone.json -> 0 tests that name it" in impact.text(found)


def test_the_reason_counts_only_the_files_no_test_names(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (one named and one not: full, and the count is of the one)."""
    start(repo)
    found = change(repo, "data/prices.json", "lone/alone.json")
    assert found.full is True and found.reason == "profile balanced: 1 unmapped file"


def test_a_mapped_and_a_named_file_select_together(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (a name only adds to what the entries select)."""
    start(repo)
    found = change(repo, "app/billing/pay.py", "data/prices.json")
    assert found.full is False
    assert picked(found) == ["tests/test_pay.py", "tests/test_prices.py"]


NAMES_PAY = {"tests/test_names_pay.py": 'P = "app/billing/pay.py"\n'}


def test_a_covered_file_also_selects_a_test_the_entry_forgot(repo):
    """REQ-016: brief #1649 answer 1 (a covered file also selects the tests that name it)."""
    start(repo, files=NAMES_PAY)
    found = change(repo, "app/billing/pay.py")
    assert found.full is False and found.reason is None and found.unmapped == []
    assert picked(found) == ["tests/test_names_pay.py", "tests/test_pay.py"]
    assert "  file: tests/test_names_pay.py (names app/billing/pay.py)" in impact.text(found)


def test_a_test_the_entry_lists_keeps_its_entry_reason(repo):
    """REQ-016: brief #1649 answer 3 (a selection already holding the test is unchanged)."""
    start(repo, files={"tests/test_pay.py": 'P = "app/billing/pay.py"\n'})
    found = change(repo, "app/billing/pay.py")
    assert picked(found) == ["tests/test_pay.py"]
    assert "(names app/billing/pay.py)" not in impact.text(found)


def test_the_changes_own_test_that_names_a_covered_file_is_not_added(repo):
    """REQ-016: brief #1649 answer 3 (the change's own test runs as its own, not as regression)."""
    start(repo)
    own = {"app/billing/pay.py": "# changed\n", "tests/test_new.py": 'P = "app/billing/pay.py"\n'}
    repo.commit(own, "change")
    assert picked(result(repo)) == ["tests/test_pay.py"]


def test_a_covered_file_in_thorough_is_unchanged(repo):
    """REQ-016: brief #1649 answer 2 (`thorough` unchanged: full)."""
    start(repo, "thorough", files=NAMES_PAY)
    found = change(repo, "app/billing/pay.py")
    assert found.full is True and found.reason == "profile thorough"


def test_a_covered_file_in_fast_selects_only_the_entry(repo):
    """REQ-016: brief #1649 answer 2 (a lighter profile: unchanged)."""
    start(repo, "fast", files=NAMES_PAY)
    assert picked(change(repo, "app/billing/pay.py")) == ["tests/test_pay.py"]


def test_a_deleted_covered_file_selects_the_tests_that_name_it(repo):
    """REQ-016: brief #1649 answer 3 (a test that names a deleted file is selected)."""
    start(repo, files=NAMES_PAY)
    repo.commit({"app/billing/pay.py": None}, "delete")
    assert picked(result(repo)) == ["tests/test_names_pay.py", "tests/test_pay.py"]


def test_a_deleted_file_still_selects_the_tests_that_name_it(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (a deletion is a change of that path)."""
    start(repo)
    repo.commit({"data/prices.json": None}, "delete")
    assert picked(result(repo)) == ["tests/test_prices.py"]


def test_the_names_are_read_at_the_head_not_the_working_tree(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 (the selection is of base..head, the tree is not read)."""
    start(repo)
    repo.commit({"data/prices.json": "# changed\n"}, "change")
    repo.write("tests/test_prices.py", "# no name now\n")
    assert picked(result(repo)) == ["tests/test_prices.py"]


def test_a_stale_entry_stays_unmapped_and_full(repo):
    """REQ-062 AC3: SPEC-0055 rule 6 is about a file no entry covers; a covered file whose
    entry selects no existing test keeps today's full selection (brief #373)."""
    start(repo, files={"tests/test_names_it.py": 'P = "app/stale/old.py"\n'})
    found = change(repo, "app/stale/old.py")
    assert found.full is True and picked(found) == []
    assert "unmapped (no [testing] map entry covers it): app/stale/old.py" in impact.text(found)


def test_fast_only_lists_as_before(repo):
    """REQ-062 AC1: SPEC-0055 rule 2 (the narrowing is of `balanced`; `fast` is unchanged)."""
    start(repo, "fast")
    found = change(repo, "data/prices.json")
    assert found.full is False and picked(found) == []
    assert "unmapped (no [testing] map entry covers it): data/prices.json" in impact.text(found)


def test_thorough_is_unchanged(repo):
    """REQ-062 AC1: SPEC-0055 rule 6 (`thorough` is unchanged)."""
    start(repo, "thorough")
    found = change(repo, "data/prices.json")
    assert found.full is True and found.reason == "profile thorough"


def test_always_full_is_unchanged(repo):
    """REQ-062 AC1: SPEC-0055 rule 6 (`always_full` is unchanged)."""
    start(repo, extra='always_full = ["data/prices.json"]\n')
    found = change(repo, "data/prices.json")
    assert (
        found.full is True
        and found.reason == "always_full data/prices.json matches data/prices.json"
    )


def test_documentation_only_still_selects_nothing(repo):
    """REQ-062 AC1: SPEC-0055 rule 2 (a documentation change selects nothing, as today)."""
    start(repo, files={"tests/test_readme.py": 'P = "README.md"\n'})
    found = change(repo, "README.md")
    assert found.docs_only is True and picked(found) == []


def test_a_project_run_uses_the_same_rule(repo, monkeypatch):
    """REQ-062 AC3: brief #773 answer 5 (`Project tests` reads the same rule and map)."""
    toml = (
        BASE + "project_tests = 'exit 0'\n[proof]\n"
        'app = { dirs = ["tests"], patterns = ["test_*.py"], command = "echo {files}" }\n'
        '[testing]\npr_tests = "selected"\n' + MAP
    )
    repo.commit({"agk.toml": toml, **FILES}, "base")
    repo.branch("feature")
    repo.commit({"data/prices.json": "# changed\n"}, "change")
    monkeypatch.setenv("EVENT", "pull_request")
    monkeypatch.setenv("AGK_BASE", repo.git("rev-parse", "main").strip())
    runs, lines = project_tests.plan(repo.root, "exit 0")
    assert [name for name, *_ in runs] == ["app"]
    assert "tests/test_prices.py" in runs[0][1]
    assert "unmapped: data/prices.json -> 1 tests that name it" in lines


def test_doctor_lists_only_the_files_that_would_run_everything(repo):
    """REQ-062 AC3: brief #773 answer 5 (doctor lists a file no entry covers and no test names)."""
    start(repo, extra='always_full = ["data/guarded.json"]\n', files={"data/guarded.json": "{}\n"})
    assert doctor.unmapped_lines(repo.root) == [
        f"tests: unmapped: {p} (no entry, no test names it)"
        for p in ("agk.toml", "kit/new.json", "lone/alone.json")
    ]


def test_doctor_says_nothing_without_a_table_or_with_a_bad_one(repo):
    """REQ-062 AC1: SPEC-0055 rule 2 (no `[testing]` table, no line; a bad one, none here)."""
    repo.commit({"agk.toml": BASE, "lone/alone.json": "{}\n"}, "base")
    assert doctor.unmapped_lines(repo.root) == []
    repo.commit({"agk.toml": BASE + '[testing]\nprofile = "nope"\n'}, "bad")
    assert doctor.unmapped_lines(repo.root) == []


def test_doctor_shortens_a_long_list(repo):
    """REQ-062 AC3: brief #773 answer 5 (the list is capped and says how many more)."""
    many = {f"lone/n{i:02d}.json": "{}\n" for i in range(25)}
    start(repo, files=many)
    lines = doctor.unmapped_lines(repo.root)
    assert len(lines) == 21 and lines[-1] == "tests: unmapped: and 8 more"


EVERY = 'every_script_tests = ["tests/test_every.py"]\n'
SCRIPTS = {
    "scripts/agk/old.py": "# old\n",
    "tests/test_every.py": "# reads each kit script by a glob\n",
    "tests/test_old.py": 'P = "scripts/agk/old.py"\n',
}
NEW = {"scripts/agk/new.py": "# new\n", "tests/test_new.py": 'P = "scripts/agk/new.py"\n'}


def test_an_added_script_selects_the_every_script_tests(repo):
    """REQ-016: brief #1651 answer 1 (an added script also selects the every-script tests)."""
    start(repo, extra=EVERY, files=SCRIPTS)
    repo.commit(NEW, "add")
    found = result(repo)
    assert found.full is False and picked(found) == [
        "tests/test_every.py",
        "tests/test_new.py",
        "tests/test_old.py",
    ]
    assert "  file: tests/test_every.py (new script) scripts/agk/new.py" in impact.text(found)


def test_a_modified_script_does_not_select_them(repo):
    """REQ-016: brief #1651 answer 3 (a modified script: its map entry and names rule)."""
    start(repo, extra=EVERY, files=SCRIPTS)
    assert picked(change(repo, "scripts/agk/old.py")) == ["tests/test_old.py"]


def test_a_renamed_script_selects_them(repo):
    """REQ-016: brief #1651 answer 3 (a renamed script is an added path)."""
    start(repo, extra=EVERY, files=SCRIPTS)
    repo.commit({"scripts/agk/old.py": None, **NEW}, "rename")
    assert "tests/test_every.py" in picked(result(repo))


def test_a_deleted_script_selects_nothing_new(repo):
    """REQ-016: brief #1651 answer 3 (a deleted script adds no every-script test)."""
    start(repo, extra=EVERY, files=SCRIPTS)
    repo.commit({"scripts/agk/old.py": None}, "delete")
    assert picked(result(repo)) == ["tests/test_old.py"]


def test_an_added_document_or_other_file_selects_nothing_new(repo):
    """REQ-016: brief #1651 answer 1 (only a script: not documentation, nor outside the folder)."""
    start(repo, extra=EVERY, files=SCRIPTS)
    repo.commit({"scripts/agk/notes.md": "# notes\n", **{"app/new.py": "# n\n"}}, "add")
    assert "tests/test_every.py" not in picked(result(repo))


def test_without_the_setting_nothing_changes(repo):
    """REQ-016: brief #1651 answer 2 (a project using AGK: an empty list by default)."""
    start(repo, files=SCRIPTS)
    repo.commit(NEW, "add")
    assert picked(result(repo)) == ["tests/test_new.py", "tests/test_old.py"]


@pytest.mark.parametrize("profile", ["fast", "thorough"])
def test_other_profiles_are_unchanged(repo, profile):
    """REQ-016: brief #1651 answer 2 (`thorough` stays full; the rule is of `balanced`)."""
    start(repo, profile, extra=EVERY, files=SCRIPTS)
    repo.commit(NEW, "add")
    found = result(repo)
    assert "tests/test_every.py" not in picked(found)
    assert found.full is (profile == "thorough")


@pytest.mark.parametrize(
    "value", ['"tests/test_every.py"', '["tests/test_gone.py"]', "[1]", '["tests/*.py"]']
)
def test_a_bad_setting_is_refused_by_name(repo, value):
    """REQ-016: brief #1651 answer 2 (not a list of existing test files: refused by name)."""
    start(repo, extra=f"every_script_tests = {value}\n", files=SCRIPTS)
    with pytest.raises(impact.CheckError) as err:
        impact.testing_table(repo.root)
    assert "setting: testing.every_script_tests" in str(err.value)
    assert "test_gone" not in str(err.value)


def test_this_repository_names_the_three_contract_tests():
    """REQ-016: brief #1651 answer 2 (the kit's default: the three every-script tests)."""
    assert impact.testing_table(ROOT)["every_script_tests"] == [
        "tests/kit/test_isolated_mode.py",
        "tests/kit/test_installed_imports.py",
        "tests/kit/test_core_contradictions.py",
    ]


DATA_FILES = (
    "kit/manifest.json",
    "kit/hashes.json",
    "config/playbooks/*.toml",
    "config/*.md",
    "config/*.txt",
    "skills/**",
    ".claude/agents/*.md",
)


@pytest.mark.parametrize("pattern", DATA_FILES)
def test_this_repository_maps_its_data_files(pattern):
    """REQ-051: brief #773 answer 1 (each data file has an entry that selects a real test)."""
    table = impact.testing_table(ROOT)
    tree = [
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file() and ".git/" not in p.as_posix()
    ]
    files = [p for p in tree if fnmatch.fnmatch(p, pattern)]
    assert files, pattern
    for path in files:
        tests = [g for e in table["map"] if impact.matches(path, e["code"]) for g in e["tests"]]
        assert tests, path
        assert any(g in tree or any(impact.matches(t, g) for t in tree) for g in tests), path
