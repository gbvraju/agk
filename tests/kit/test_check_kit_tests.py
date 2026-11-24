"""Tests of scripts/agk/check_kit_tests.py: each installed check has a test in the kit repo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CHECK = "scripts/agk/check_new.py"
TEST = "tests/kit/test_check_new.py"


def manifest(*verbatim: str) -> str:
    data = {"kit_version": "0.0.0", "kit_tests": "tests/kit", "verbatim": sorted(verbatim)}
    return json.dumps(data) + "\n"


def kit(repo, test_text: str | None, location: str = TEST) -> None:
    """A kit repository: one installed check, and (maybe) one test file for it.

    The tests are not installed (lean install): the manifest lists the check and no test file.
    """
    files = {
        "kit/manifest.json": manifest(CHECK),
        CHECK: "NAME = 'new'\n",
        "scripts/agk/reviewers.py": "x = 1\n",
        "tests/kit/test_other.py": "def test_x():\n    assert True\n",
    }
    if test_text is not None:
        files[location] = test_text
    repo.commit(files)


def test_ac1_installed_check_without_a_test_under_tests_kit_fails(repo):
    """REQ-009 AC2: a check whose tests sit outside tests/kit/ (the reviewer case)."""
    kit(repo, '"""t"""\nrepo.run("check_new.py")\n', location="tests/kit_dev/test_new.py")
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1
    assert "FAIL kit-tests" in proc.stdout and CHECK in proc.stdout
    assert "kit_tests" in proc.stdout


def test_ac1_a_test_file_need_not_be_listed_in_the_manifest(repo):
    """REQ-009 AC2: lean install (ADR-0052): the test is on disk under tests/kit/, not installed."""
    kit(repo, 'repo.run("check_new.py")\n')
    assert "tests/kit/test_new" not in (repo.root / "kit" / "manifest.json").read_text()
    assert repo.run("check_kit_tests.py").returncode == 0


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


# Brief #1798 (amendment 186 build (m), ADR-0650): the kit sets its own `[testing] whole_tests`.
WHOLE = "tests/kit/test_whole.py"
KIT_MAKE = "kit/agk-kit.mk"


def the_kit(repo, testing: str | None) -> None:
    """The kit repository itself (`kit/agk-kit.mk` marks it, as governance reads it)."""
    if not (repo.root / KIT_MAKE).exists():
        kit(repo, 'repo.run("check_new.py")\n')
    files = {KIT_MAKE: "# the kit\n", WHOLE: "def test_w():\n    assert True\n"}
    toml = 'default_branch = "main"\n'
    files["agk.toml"] = toml if testing is None else toml + "[testing]\n" + testing
    repo.commit(files)


def test_the_kit_without_whole_tests_fails_naming_the_setting(repo):
    """REQ-062: brief #1798 answer 2 (absent: the key, and the whole `[testing]` table)."""
    for testing in ('profile = "balanced"\n', None):
        the_kit(repo, testing)
        proc = repo.run("check_kit_tests.py")
        assert proc.returncode == 1, proc.stdout
        assert "FAIL kit-tests" in proc.stdout and "setting: testing.whole_tests" in proc.stdout


def test_the_kit_with_an_empty_whole_tests_fails_naming_the_setting(repo):
    """REQ-062: brief #1798 answer 2 (empty)."""
    the_kit(repo, "whole_tests = []\n")
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "setting: testing.whole_tests" in proc.stdout + proc.stderr
    assert "[]" not in proc.stdout + proc.stderr


def test_the_kit_with_a_whole_test_passes(repo):
    """REQ-062: brief #1798 answer 2."""
    the_kit(repo, f'whole_tests = ["{WHOLE}"]\n')
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_a_kit_like_repository_without_the_kit_make_file_needs_no_list(repo):
    """REQ-062: brief #1798 answer 3 (a project's list stays empty until it sets one)."""
    kit(repo, 'repo.run("check_new.py")\n')
    repo.commit({"agk.toml": 'default_branch = "main"\n[testing]\nprofile = "balanced"\n'})
    assert repo.run("check_kit_tests.py").returncode == 0


def whole_block(text: str) -> list[str]:
    """The lines of the `whole_tests = [` ... `]` block of the kit's `agk.toml`."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("whole_tests = ["))
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "]")
    return [line for line in lines[start + 1 : end] if line.strip()]


def test_the_kits_own_list_is_set_each_file_exists_with_a_whole_reason():
    """REQ-062: brief #1798 answers 1 and 8 (16 files, each with a `# whole:` reason)."""
    from pathlib import Path

    import impact

    root = Path(__file__).resolve().parents[2]
    listed = impact.testing_table(root)["whole_tests"]
    assert "tests/kit/test_core_contradictions.py" in listed  # Q-F7-1
    assert all((root / name).is_file() for name in listed)
    block = whole_block((root / "agk.toml").read_text(encoding="utf-8"))
    assert len(block) == len(listed)
    for line in block:
        entry, _, reason = line.partition("# whole:")
        assert entry.strip().strip(",").strip('"') in listed, line
        assert reason.strip(), line


# Brief #1814 (ADR-0755 decision 4): the retired `every_script_tests` is refused by name, in the
# kit and in a project alike.
RETIRED_KEY = f'every_script_tests = ["{WHOLE}"]\n'
REFUSED = (
    "FAIL kit-tests: every_script_tests is retired: list its files in testing.whole_tests "
    "(setting: testing.every_script_tests)"
)


def test_the_kit_that_sets_the_retired_key_fails_naming_the_setting(repo):
    """REQ-062: brief #1812 answers 1 and 7, brief #1814 answer 6 (the kit, `[]` too)."""
    for value in (RETIRED_KEY, "every_script_tests = []\n"):
        the_kit(repo, f'whole_tests = ["{WHOLE}"]\n' + value)
        proc = repo.run("check_kit_tests.py")
        assert proc.returncode == 1, proc.stdout + proc.stderr
        assert REFUSED in proc.stdout


def test_a_project_that_sets_the_retired_key_is_refused_naming_the_setting(repo):
    """REQ-062: brief #1814 answer 1 (the release after the warning refuses a project's key)."""
    kit(repo, 'repo.run("check_new.py")\n')
    toml = 'default_branch = "main"\n[testing]\n' + RETIRED_KEY
    repo.commit({"agk.toml": toml, WHOLE: "def test_w():\n    assert True\n"})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert REFUSED in proc.stdout and WHOLE not in proc.stdout


# Brief #1878 (ADR-0777): the rules of the kit's own testing map that a quick record could miss
# (every test that runs the gate runner is in the gates' entry; every map test name matches a test
# file) live in the check, so prepush's governance step fails with or without --quick. The fixture
# texts build the runner's file name in two parts and start no line with an import of it, so this
# file is not itself a runner test.
RUNNER = "run_gates"
IMPORTS = f"import {RUNNER}\n"
COMMAND = 'CMD = ["python3", "scripts/agk/' + RUNNER + '.py"]\n'
DOC_ONLY = '"""Names scripts/agk/' + RUNNER + '.py in a docstring only."""\n'
GATES = "scripts/agk/gates/*.py"
LISTED = "tests/kit/test_listed.py"
NEW = "tests/kit/test_a.py"
MISSING_KIT = (
    "FAIL kit-tests: 1 test files of tests/kit/ that run the gate runner are missing from "
    "testing.map (setting: testing.map)"
)
GONE_LINE = (
    "FAIL kit-tests: testing.map names a test file that does not exist for the gate steps "
    "(setting: testing.map)"
)
STALE_LINE = "FAIL kit-tests: 1 testing.map test names match no test file (setting: testing.map)"


def gates_toml(tests: list[str], branch: str = "main", extra: str = "") -> str:
    names = ", ".join(f'"{t}"' for t in tests)
    return (
        f'default_branch = "{branch}"\n[testing]\nwhole_tests = ["{WHOLE}"]\n'
        f'[[testing.map]]\ncode = "{GATES}"\ntests = [{names}]\n' + extra
    )


def gate_kit(repo, tests: list[str] | None = None, branch: str = "main") -> None:
    """The kit with a gates entry naming `tests` and one listed runner test, on `main`."""
    the_kit(repo, f'whole_tests = ["{WHOLE}"]\n')
    toml = gates_toml([LISTED] if tests is None else tests, branch)
    repo.commit({"agk.toml": toml, LISTED: IMPORTS})


def test_a_new_runner_test_missing_from_the_gates_entry_fails_naming_the_class(repo):
    """REQ-062: brief #1878 answers 2 and 7 (red on main: the #1870 miss)."""
    gate_kit(repo)
    repo.branch()
    repo.commit({NEW: IMPORTS})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert MISSING_KIT in proc.stdout
    assert "test_a" not in proc.stdout


def test_a_listed_runner_test_and_a_docstring_mention_pass(repo):
    """REQ-062: brief #1878 answers 6 and 7 (listed; a docstring is not a runner test)."""
    gate_kit(repo)
    repo.branch()
    repo.commit({NEW: COMMAND, "agk.toml": gates_toml([LISTED, NEW])})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    repo.commit({"tests/kit_dev/test_doc.py": DOC_ONLY})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines()[-1].startswith("ok kit-tests (")


def test_a_command_that_starts_the_runner_counts_in_the_dev_folder(repo):
    """REQ-062: brief #1878 answer 2 (Q-30A-1: a command naming the runner's file counts)."""
    gate_kit(repo)
    repo.branch()
    repo.commit({"tests/kit_dev/test_c.py": COMMAND})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert MISSING_KIT.replace("tests/kit/", "tests/kit_dev/") in proc.stdout


def test_a_listed_runner_test_deleted_is_gone_and_stale(repo):
    """REQ-062: brief #1878 answers 2, 3 and 6 (a deleted or renamed test leaves its name)."""
    gate_kit(repo)
    repo.branch()
    repo.commit({LISTED: None})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert GONE_LINE in proc.stdout and STALE_LINE in proc.stdout
    assert "test_listed" not in proc.stdout


def test_a_map_name_that_matches_no_test_file_fails(repo):
    """REQ-062: brief #1878 answer 3 (each glob of every entry, read every run)."""
    gate_kit(repo)
    extra = (
        '[[testing.map]]\ncode = "scripts/agk/check_new.py"\ntests = ["tests/kit/test_no_*.py"]\n'
    )
    repo.commit({"agk.toml": gates_toml([LISTED], extra=extra)})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert STALE_LINE in proc.stdout and "test_no_" not in proc.stdout


def test_with_a_base_an_untouched_runner_test_is_read_only_when_the_map_changes(repo):
    """REQ-062: brief #1878 answers 2 and 7 (with a base, the change's own test files)."""
    gate_kit(repo)
    repo.commit({NEW: IMPORTS})  # on main itself: the base, so the change reads nothing
    assert repo.run("check_kit_tests.py").returncode == 0
    repo.branch()
    repo.commit({"scripts/agk/reviewers.py": "x = 2\n"})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    repo.commit({"agk.toml": gates_toml([LISTED]) + "# the map changes\n"})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1 and MISSING_KIT in proc.stdout, proc.stdout


def test_without_a_base_every_test_file_is_read(repo):
    """REQ-062: brief #1878 answer 5 (no base resolves outside CI: every file, never a skip)."""
    gate_kit(repo, branch="trunk")
    repo.commit({NEW: IMPORTS})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1 and MISSING_KIT in proc.stdout, proc.stdout


def test_an_untracked_runner_test_is_read(repo):
    """REQ-062: brief #1878 answer 6 (an untracked new test is an added file)."""
    gate_kit(repo)
    repo.branch()
    repo.write(NEW, IMPORTS)
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1 and MISSING_KIT in proc.stdout, proc.stdout


def test_a_kit_without_a_gates_entry_misses_every_runner_test(repo):
    """REQ-062: brief #1878 answer 5 (`[testing]` present without the gates entry)."""
    gate_kit(repo)
    extra = f'[[testing.map]]\ncode = "scripts/agk/check_new.py"\ntests = ["{LISTED}"]\n'
    toml = f'default_branch = "main"\n[testing]\nwhole_tests = ["{WHOLE}"]\n' + extra
    repo.branch()
    repo.commit({"agk.toml": toml})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1 and MISSING_KIT in proc.stdout, proc.stdout


def test_a_test_file_that_cannot_be_parsed_is_named_by_its_folder(repo):
    """REQ-062: brief #1878 answer 6 (a parse error is a FAIL naming the path class, no crash)."""
    gate_kit(repo)
    repo.branch()
    repo.commit({"tests/kit/test_bad.py": "def (\n"})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "FAIL kit-tests: a test file of tests/kit/ cannot be read (path class: tests/kit/)" in (
        proc.stdout
    )
    assert "Traceback" not in proc.stderr


def test_a_bad_tests_value_is_refused_naming_the_setting(repo):
    """REQ-062: brief #1878 answer 5 (refused by impact.testing_table before either rule)."""
    gate_kit(repo)
    toml = f'default_branch = "main"\n[testing]\nwhole_tests = ["{WHOLE}"]\n'
    repo.commit({"agk.toml": toml + f'[[testing.map]]\ncode = "{GATES}"\ntests = "x-value"\n'})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode != 0
    assert "setting: testing.map[1].tests" in proc.stdout + proc.stderr
    assert "x-value" not in proc.stdout + proc.stderr


def test_the_rules_read_only_the_kit_with_its_testing_table(repo):
    """REQ-062: brief #1878 answer 4 (no table, no kit make file, no manifest: no rule)."""
    the_kit(repo, None)  # the kit without [testing]: only the whole_tests line, no map rule
    repo.commit({NEW: IMPORTS})
    proc = repo.run("check_kit_tests.py")
    assert "gate runner" not in proc.stdout and "testing.map" not in proc.stdout
    repo.commit({KIT_MAKE: None, "agk.toml": gates_toml(["tests/kit/test_gone.py"])})
    proc = repo.run("check_kit_tests.py")  # a kit-like repository: neither rule
    assert proc.returncode == 0, proc.stdout + proc.stderr
    repo.commit({"kit/manifest.json": None})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0 and "nothing to check" in proc.stdout


def test_a_quick_record_fails_at_governance_with_the_same_five_steps(repo, tmp_path):
    """REQ-062: brief #1878 answers 1 and 7 (no passing quick record; the record is unchanged)."""
    from test_prepush import path_with, scanner

    script = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "check_kit_tests.py"
    gate_kit(repo)
    mk = f'agk-governance:\n\t@"{sys.executable}" "{script}"\n'
    repo.commit({"agk.mk": mk, "Makefile": "lint:\n\t@true\n"})
    repo.branch()
    repo.commit({NEW: IMPORTS})
    outside = tmp_path / "outside"
    record = outside / "record.json"
    scan = scanner(outside / "bin", 0)
    proc = repo.run(
        "prepush.py", "--quick", "--no-lock", "--record", str(record), PATH=path_with(scan)
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    data = json.loads(record.read_text(encoding="utf-8"))
    names = [s["name"] for s in data["steps"]]  # the run stops at the first failure
    assert data["schema"] == 1
    assert names == ["pr-body", "lint", "governance", "secret-scan", "tests"][: len(names)]
    assert names[-1] == "governance"
    governance = next(s for s in data["steps"] if s["name"] == "governance")
    assert governance["outcome"] == "FAIL" and data["result"] == "failed"
