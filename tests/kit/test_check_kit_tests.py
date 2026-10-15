"""Tests of scripts/agk/check_kit_tests.py: every installed check ships with an installed test."""

from __future__ import annotations

import json

CHECK = "scripts/agk/check_new.py"
TEST = "tests/kit/test_check_new.py"


def manifest(*verbatim: str) -> str:
    return json.dumps({"kit_version": "0.0.0", "verbatim": sorted(verbatim)}) + "\n"


def kit(repo, test_text: str | None, listed: bool = True, location: str = TEST) -> None:
    """A kit repository: one installed check, and (maybe) one test file for it."""
    listing = [CHECK, "tests/kit/test_other.py"] + ([location] if listed and test_text else [])
    files = {
        "kit/manifest.json": manifest(*listing),
        CHECK: "NAME = 'new'\n",
        "scripts/agk/reviewers.py": "x = 1\n",
        "tests/kit/test_other.py": "def test_x():\n    assert True\n",
    }
    if test_text is not None:
        files[location] = test_text
    repo.commit(files)


def test_ac1_installed_check_without_installed_tests_fails(repo):
    """REQ-009 AC2: a check whose tests sit outside the installed set (the reviewer case)."""
    kit(
        repo,
        '"""t"""\nrepo.run("check_new.py")\n',
        listed=False,
        location="tests/kit_dev/test_new.py",
    )
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1
    assert "FAIL kit-tests" in proc.stdout and CHECK in proc.stdout
    assert "tests/kit/" in proc.stdout


def test_ac1_test_file_present_but_not_in_the_manifest_set_fails(repo):
    """REQ-009 AC2: the test must be in the same verbatim set, not merely on disk."""
    kit(repo, 'repo.run("check_new.py")\n', listed=False)
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1 and CHECK in proc.stdout


def test_ac1_no_test_file_at_all_fails(repo):
    """REQ-009 AC2."""
    kit(repo, None)
    assert repo.run("check_kit_tests.py").returncode == 1


def test_ac1_installed_check_with_an_installed_test_that_runs_it_passes(repo):
    """REQ-009 AC2."""
    kit(repo, 'def test_a(repo):\n    assert repo.run("check_new.py")\n')
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.startswith("ok kit-tests")


def test_ac1_import_forms_and_path_strings_count(repo):
    """REQ-009 AC2: the test imports the check, or names its file in a string."""
    for text in (
        "import check_new\n",
        "from check_new import NAME\n",
        'PATH = "scripts/agk/check_new.py"\n',
        'run(["python3", "check_new.py"])\n',
    ):
        kit(repo, text)
        assert repo.run("check_kit_tests.py").returncode == 0, text


def test_ac1_a_mention_in_a_docstring_or_comment_does_not_count(repo):
    """REQ-009 AC2: a test must import or run the check, not talk about it."""
    kit(
        repo,
        '"""Tests of scripts/agk/check_new.py."""\n\n# check_new.py is covered elsewhere\n'
        'def test_a():\n    """check_new"""\n    assert True\n',
    )
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1 and CHECK in proc.stdout


def test_ac1_a_test_of_another_check_does_not_cover_this_one(repo):
    """REQ-009 AC2."""
    kit(repo, "import check_adrs\n")
    assert repo.run("check_kit_tests.py").returncode == 1


def test_ac1_only_test_files_count_not_helper_modules(repo):
    """REQ-009 AC2: tests/kit/helper.py is not a test file."""
    kit(repo, "import check_new\n", location="tests/kit/helper_new.py")
    assert repo.run("check_kit_tests.py").returncode == 1


def test_ac1_every_uncovered_check_is_reported_in_order(repo):
    """REQ-009 AC2."""
    repo.commit(
        {
            "kit/manifest.json": manifest(
                "scripts/agk/check_b.py", "scripts/agk/check_a.py", "tests/kit/test_x.py"
            ),
            "scripts/agk/check_a.py": "a = 1\n",
            "scripts/agk/check_b.py": "b = 1\n",
            "tests/kit/test_x.py": "x = 1\n",
        }
    )
    lines = [
        ln for ln in repo.run("check_kit_tests.py").stdout.splitlines() if ln.startswith("FAIL")
    ]
    assert len(lines) == 2
    assert "check_a.py" in lines[0] and "check_b.py" in lines[1]


def test_ac1_scripts_that_are_not_checks_need_no_test_here(repo):
    """REQ-009 AC2: only scripts/agk/check_*.py are covered by this rule."""
    repo.commit(
        {
            "kit/manifest.json": manifest(
                "scripts/agk/reviewers.py", "scripts/agk/review_context.py"
            ),
            "scripts/agk/reviewers.py": "x = 1\n",
        }
    )
    assert repo.run("check_kit_tests.py").returncode == 0


def test_ac1_without_a_kit_manifest_there_is_nothing_to_check(repo):
    """REQ-009 AC2: an installed repository has no kit/manifest.json; the check is a no-op."""
    repo.commit({"scripts/agk/check_new.py": "x = 1\n"})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0
    assert "no kit/manifest.json" in proc.stdout


def test_ac1_a_broken_manifest_fails_naming_the_path_not_a_value(repo):
    """REQ-009 AC2 (principle 8)."""
    repo.commit({"kit/manifest.json": '{"verbatim": [SECRET-TEXT\n'})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1
    assert "kit/manifest.json" in proc.stdout and "SECRET-TEXT" not in proc.stdout


def test_ac1_messages_name_paths_only(repo):
    """REQ-009 AC2 (principle 8)."""
    kit(repo, 'UNIQUE_VALUE = "must-not-be-echoed"\n')
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1
    assert "must-not-be-echoed" not in proc.stdout


def test_ac1_a_string_in_a_comparison_or_exclusion_list_does_not_count(repo):
    """REQ-009 AC2: the reviewer case. A test that skips the check by name does not test it."""
    kit(
        repo,
        "def test_all(names):\n    for name in names:\n"
        '        if name in ("check_new.py", "check_pr_body.py"):\n            continue\n'
        '    assert "check_new.py" != "x"\n',
    )
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1 and CHECK in proc.stdout


def test_ac1_a_string_in_a_data_table_that_a_test_uses_counts(repo):
    """REQ-009 AC2: a test may name the check in a table it later runs."""
    kit(repo, 'TABLE = {"F1": ("check_new.py", "needle")}\n')
    assert repo.run("check_kit_tests.py").returncode == 0
