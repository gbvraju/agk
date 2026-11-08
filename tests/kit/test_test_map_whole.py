"""Tests of the map-whole rule of scripts/agk/check_kit_tests.py (brief #773 answer 3, ADR-0359).

A pull request that adds a file under `config/`, `kit/`, `skills/` or `.claude/` that no
`[[testing.map]]` entry covers and no test names fails, naming the file and the rule. Saved
change sets in a temporary repository; no network.
"""

from __future__ import annotations

import json

import check_kit_tests

CHECK = "scripts/agk/check_x.py"
BASE = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
TABLE = '[testing]\nmap = [ { code = "config/covered/**", tests = ["tests/kit/test_x.py"] } ]\n'
MANIFEST = json.dumps({"kit_version": "0.0.0", "kit_tests": "tests/kit", "verbatim": [CHECK]})
TEST = 'def test_x():\n    assert "check_x.py"\n'


def start(repo, table: str = TABLE, test: str = TEST) -> None:
    repo.commit(
        {
            "agk.toml": BASE + table,
            "kit/manifest.json": MANIFEST,
            CHECK: "# x\n",
            "tests/kit/test_x.py": test,
        },
        "base",
    )
    repo.branch("feature")


def check(repo):
    return repo.run("check_kit_tests.py", "--base", "main")


def test_an_added_file_nothing_covers_fails_naming_file_and_rule(repo):
    """REQ-051: brief #773 answer 3 (fails, naming the file and the rule)."""
    start(repo)
    repo.commit({"config/new.txt": "x\n"})
    proc = check(repo)
    assert proc.returncode == 1
    assert "config/new.txt" in proc.stdout and "SPEC-0055 rule 6" in proc.stdout
    assert "setting: testing.map" in proc.stdout


def test_an_entry_covers_it(repo):
    """REQ-051: brief #773 answer 3 (an entry covers the added file)."""
    start(repo)
    repo.commit({"config/covered/new.txt": "x\n"})
    assert check(repo).returncode == 0


def test_a_test_that_names_it_covers_it(repo):
    """REQ-051: brief #773 answer 3 (a test names the added file)."""
    start(repo, test=TEST + 'P = "skills/new/data.json"\n')
    repo.commit({"skills/new/data.json": "{}\n"})
    assert check(repo).returncode == 0


def test_a_test_added_with_it_covers_it(repo):
    """REQ-051: brief #773 answer 3 (the new test of the same pull request counts)."""
    start(repo)
    repo.commit(
        {"kit/templates/new.txt": "x\n", "tests/kit/test_new.py": 'P = "kit/templates/new.txt"\n'}
    )
    assert check(repo).returncode == 0


def test_naming_only_the_folder_is_not_enough(repo):
    """REQ-051: brief #773 answer 3 (the check needs the file named, not only its folder)."""
    start(repo, test=TEST + 'P = "kit/templates/"\n')
    repo.commit({"kit/templates/new.txt": "x\n"})
    assert check(repo).returncode == 1


def test_each_guarded_folder_is_checked(repo):
    """REQ-051: brief #773 answer 3 (`config/`, `kit/`, `skills/` and `.claude/`)."""
    start(repo)
    repo.commit(
        {
            "kit/a.txt": "x\n",
            "skills/b/c.md": "x\n",
            ".claude/agents/d.md": "x\n",
            "config/e.md": "x\n",
        }
    )
    proc = check(repo)
    assert proc.returncode == 1
    for path in ("kit/a.txt", "skills/b/c.md", ".claude/agents/d.md", "config/e.md"):
        assert path in proc.stdout, path


def test_a_changed_or_other_file_is_not_checked(repo):
    """REQ-051: brief #773 answer 3 (only an added file, only under those folders)."""
    start(repo, test=TEST)
    repo.commit(
        {"kit/manifest.json": MANIFEST + "\n", "app/new.txt": "x\n", "other/config/new.txt": "x\n"}
    )
    assert check(repo).returncode == 0


def test_without_a_testing_table_nothing_is_checked(repo):
    """REQ-051: brief #773 answer 3 (no map to keep whole)."""
    start(repo, table="")
    repo.commit({"config/new.txt": "x\n"})
    assert check(repo).returncode == 0


def test_the_problem_function_takes_no_base_outside_ci(repo, monkeypatch):
    """REQ-051: brief #773 answer 3 (no base outside CI: skipped, as the other rule is)."""
    repo.commit(
        {"agk.toml": 'default_branch = "nowhere"\n[testing]\n', "kit/manifest.json": MANIFEST},
        "base",
    )
    monkeypatch.delenv("AGK_BASE", raising=False)
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    monkeypatch.delenv("CI", raising=False)
    assert check_kit_tests.map_problems(repo.root, []) == []
