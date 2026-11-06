"""The check before the merge also runs the kit tests that read the whole tree (brief #667).

ADR-0320, amendment 132 of SPEC-0039 rule 6, REQ-046. Twice on 2026-11-06 (#657, #659) two pull
requests, each green alone, made the default branch red once both had merged: the rule budget
test reads the whole tree, and governance, the one run of the check before the merge, does not
run it. Now, after governance passes on the would-be merge, the command runs the test files of
`[testing] pre_merge_tests` (agk.toml on the default branch; without the key, the budget, testing
map and manifest tests in the kit repository, none in a project) with `AGK_KIT_TESTS=1 python3
-m pytest -q -c tests/kit/pytest.ini <files>` in the same detached worktree, under the heavy lock
and `env -i`; a failure holds with `held: the merge with the default branch fails pre-merge tests
(<file>::<test>)`, exit 3, nothing merged. Every test runs on a checkout in `tmp_path` whose
origin is a local bare repository, a fake `gh` answering from saved responses and a fake `make`;
the pre-merge tests are real pytest runs of a small invented budget test. No network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_merge_cleared_after import makes, worktrees, writes
from test_merge_cleared_verdict import (
    AUTO_ISSUE,
    GIT_ENV,
    MERGE,
    ON,
    SCRIPTS,
    calls,
    cleared,
    fake_gh,
    git,
    one_line,
    repo,
    run,
    toml,
    world,
)

sys.path.insert(0, str(SCRIPTS))

import impact  # noqa: E402
import merge_cleared  # noqa: E402
from common import CheckError  # noqa: E402

TESTS_FAIL = "held: the merge with the default branch fails pre-merge tests"
BUDGET_TEST = "tests/kit/test_budget.py"
BUDGET_ID = f"{BUDGET_TEST}::test_the_rules_fit_the_budget"
PLANTED = "AGK_EXAMPLE_PLANTED"  # set in the command's environment; must not reach the tests
BUDGET_SOURCE = f'''
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_rules_fit_the_budget():
    words = len((ROOT / "rules.md").read_text(encoding="utf-8").split())
    assert words <= int((ROOT / "budget.txt").read_text(encoding="utf-8"))


def test_the_run_is_bounded():
    assert os.environ.get("AGK_KIT_TESTS") == "1"
    assert "{PLANTED}" not in os.environ
'''
BASE_FILES = {
    "tests/kit/pytest.ini": "[pytest]\ntestpaths = .\n",
    BUDGET_TEST: BUDGET_SOURCE,
    "rules.md": "one two three\n",
    "budget.txt": "5\n",
}
WIDER = {"rules.md": "one two three four five\n"}  # the default branch: 5 words, budget 5
LOWER = {"budget.txt": "3\n"}  # the pull request: budget 3, rules 3 words
SETTING = f'[testing]\npre_merge_tests = ["{BUDGET_TEST}"]\n'


def commit_in(bare: Path, files: dict[str, str], parent: str, message: str) -> str:
    """One commit in the bare repository BARE holding FILES on top of PARENT, made with a
    temporary index (no work tree)."""
    env = {**os.environ, **GIT_ENV, "GIT_INDEX_FILE": str(bare / f"index-{message}")}

    def g(*args: str, text: str | None = None) -> str:
        return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=bare, input=text, capture_output=True, text=True, check=True,
            env=env,
        ).stdout.strip()  # fmt: skip

    g("read-tree", parent)
    for name, body in files.items():
        blob = g("hash-object", "-w", "--stdin", text=body)
        g("update-index", "--add", "--cacheinfo", f"100644,{blob},{name}")
    tree = g("write-tree")
    return g("commit-tree", tree, "-p", parent, "-m", message)


def bare_of(root: Path) -> Path:
    url = git(root, "remote", "get-url", "origin").strip()
    return Path(url.removeprefix("file://"))


def budget_world(tmp_path: Path, head_files: dict, main_files: dict, setting: str = SETTING):
    """A checkout whose default branch (agk.toml with SETTING) and pull request #7 each change
    the shared base X (BASE_FILES on the fixed merge commit) by MAIN_FILES and HEAD_FILES: (the
    checkout, the head's sha)."""
    root = repo(tmp_path, toml(ON) + setting)
    bare = bare_of(root)
    base = commit_in(bare, BASE_FILES, MERGE, "x")
    main = commit_in(bare, main_files, base, "main")
    head = commit_in(bare, head_files, base, "head")
    git(bare, "update-ref", "refs/heads/main", main)
    git(bare, "update-ref", "refs/pull/7/head", head)
    return root, head


def budget_run(tmp_path: Path, head_files: dict, main_files: dict, setting: str = SETTING):
    """One run of the command: (the process, the gh calls, the make calls, the checkout)."""
    root, head = budget_world(tmp_path, head_files, main_files, setting)
    pull = {**world()["pull"], "head": {"sha": head}}
    commits = [{"sha": head, "commit": {"message": "Example change\n"}}]
    bin_dir, log = fake_gh(
        tmp_path, pull=pull, comments=[cleared(head, extra="")], issues=[AUTO_ISSUE],
        commits=commits,
    )  # fmt: skip
    old = os.environ.get(PLANTED)
    os.environ[PLANTED] = "example"
    try:
        proc = run(root, bin_dir, "--pr", "7", "--sha", head)
    finally:
        if old is None:
            os.environ.pop(PLANTED)
        else:
            os.environ[PLANTED] = old
    return proc, calls(log), makes(tmp_path), root, head


def merges(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if "PUT" in c]


# --- answer 4: green alone, red together -------------------------------------------------------


def test_each_side_alone_meets_the_budget():
    """REQ-046: brief #667 answer 4 (the fixture: main alone and the branch alone are green)."""
    for files in ({**BASE_FILES, **WIDER}, {**BASE_FILES, **LOWER}):
        words = len(files["rules.md"].split())
        assert words <= int(files["budget.txt"])
    merged = {**BASE_FILES, **WIDER, **LOWER}
    assert len(merged["rules.md"].split()) > int(merged["budget.txt"])


def test_a_merge_that_fails_the_budget_test_is_held_and_not_merged(tmp_path):
    """REQ-046: brief #667 answers 1 and 4 (green alone, red together: held, exit 3)."""
    proc, made, ran, root, head = budget_run(tmp_path, LOWER, WIDER)
    assert one_line(proc) == f"merge-cleared #7 {head[:12]}: {TESTS_FAIL} ({BUDGET_ID})"
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert merges(made) == [] and writes(made) == [], "nothing merged, recorded or filed"
    assert len(ran) == 1, "governance ran once, before the merge"
    assert worktrees(root) == [str(root)], "the worktree is removed"
    assert git(root, "status", "--porcelain") == ""


def test_a_merge_that_meets_the_budget_merges(tmp_path):
    """REQ-046: brief #667 answer 4 (the green case merges; the run is bounded: `env -i` with
    AGK_KIT_TESTS=1, nothing else of the command's environment)."""
    proc, made, ran, root, _ = budget_run(tmp_path, {"budget.txt": "6\n"}, WIDER)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert one_line(proc).endswith(f"merged {MERGE[:12]}")
    assert len(merges(made)) == 1
    assert worktrees(root) == [str(root)]


def test_a_red_governance_holds_before_any_test_runs(tmp_path):
    """REQ-046: brief #667 answer 1 (the tests run after governance passes)."""
    root, head = budget_world(tmp_path, LOWER, WIDER)
    pull = {**world()["pull"], "head": {"sha": head}}
    commits = [{"sha": head, "commit": {"message": "Example change\n"}}]
    bin_dir, log = fake_gh(
        tmp_path, pull=pull, comments=[cleared(head, extra="")], commits=commits, premerge_exit=2
    )
    proc = run(root, bin_dir, "--pr", "7", "--sha", head)
    assert one_line(proc).endswith("fails governance (make governance)")
    assert proc.returncode == 3


def test_a_listed_name_that_is_not_a_file_in_the_merge_holds_naming_the_setting(tmp_path):
    """REQ-046: brief #667 answer 2 (fail-closed: a missing file holds, naming the setting)."""
    setting = '[testing]\npre_merge_tests = ["tests/kit/test_gone.py"]\n'
    proc, made, _, _, head = budget_run(tmp_path, {"budget.txt": "6\n"}, WIDER, setting)
    assert one_line(proc) == (
        f"merge-cleared #7 {head[:12]}: {TESTS_FAIL} (setting: testing.pre_merge_tests)"
    )
    assert proc.returncode == 3 and merges(made) == []


@pytest.mark.parametrize("value", ["'tests/kit/test_budget.py'", "[]", "[3]", '["../x.py"]',
                                   '["/abs/test_x.py"]', '["tests/*.py"]'])  # fmt: skip
def test_a_bad_setting_on_the_default_branch_is_refused_naming_it(tmp_path, value):
    """REQ-046: brief #667 answer 2 (a bad setting is refused before anything runs)."""
    setting = f"[testing]\npre_merge_tests = {value}\n"
    proc, made, ran, _, _ = budget_run(tmp_path, LOWER, WIDER, setting)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "refused:" in one_line(proc) and "setting: testing.pre_merge_tests" in one_line(proc)
    assert "/abs" not in one_line(proc) and "../" not in one_line(proc), "never the value"
    assert merges(made) == [] and ran == []


def test_without_the_key_a_project_runs_no_pre_merge_test(tmp_path):
    """REQ-046: brief #667 answer 2 (absent: the default list, which runs only where the kit's
    tests are, `kit/agk-kit.mk`; the would-be merge here has none, so the red budget is not run)."""
    proc, made, _, _, _ = budget_run(tmp_path, LOWER, WIDER, setting="")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(merges(made)) == 1


# --- answer 2: impact.testing_table accepts the key -------------------------------------------


def write_toml(root: Path, text: str, files: tuple[str, ...] = ()) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "agk.toml").write_text('default_branch = "main"\n' + text, encoding="utf-8")
    for name in files:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("# test\n", encoding="utf-8")
    return root


def test_the_table_accepts_the_key_and_names_its_files(tmp_path):
    """REQ-046: brief #667 answer 2."""
    root = write_toml(tmp_path, SETTING, (BUDGET_TEST,))
    assert impact.testing_table(root) is not None
    assert impact.pre_merge_tests(root) == [BUDGET_TEST]


def test_a_name_that_is_not_a_file_is_refused_naming_the_setting(tmp_path):
    """REQ-046: brief #667 answer 2."""
    root = write_toml(tmp_path, SETTING)
    with pytest.raises(CheckError, match=r"setting: testing\.pre_merge_tests\)") as err:
        impact.testing_table(root)
    assert BUDGET_TEST not in str(err.value), "never the value"


def test_without_the_key_the_default_list_runs_in_the_kit_repository(tmp_path):
    """REQ-046: brief #667 answer 2 (the default list; in a project, none)."""
    kit = write_toml(tmp_path / "kit-repo", "[testing]\n", ("kit/agk-kit.mk",))
    assert impact.pre_merge_tests(kit) == list(impact.PRE_MERGE_TESTS)
    project = write_toml(tmp_path / "project", "[testing]\n")
    assert impact.pre_merge_tests(project) == []
    assert impact.pre_merge_tests(write_toml(tmp_path / "bare", "")) == []


def test_the_default_list_names_files_of_this_repository():
    """REQ-046: brief #667 (each default name exists on the default branch, followed from the
    code: the testing map test is tests/kit_dev/test_intelligent_testing.py)."""
    root = SCRIPTS.parents[1]
    assert impact.PRE_MERGE_TESTS == (
        "tests/kit/test_rule_budget.py",
        "tests/kit_dev/test_intelligent_testing.py",
        "tests/kit_dev/test_kit_manifest.py",
    )
    for name in impact.PRE_MERGE_TESTS:
        assert (root / name).is_file(), name
    assert impact.pre_merge_tests(root) == list(impact.PRE_MERGE_TESTS)


def test_the_test_run_is_one_bounded_argument_list():
    """REQ-046: brief #667 answer 1 (the heavy lock, `env -i`, the brief's pytest command)."""
    tree, home = Path("/scratch/tree"), Path("/scratch/home")
    argv = merge_cleared.tests_argv(tree, home, [BUDGET_TEST], 60.0)
    assert argv[2:5] == ["run", "--name", "heavy"]
    end = argv.index("--")
    assert argv[end + 1 : end + 3] == ["env", "-i"]
    assert "AGK_KIT_TESTS=1" in argv and f"HOME={home}" in argv
    assert not any(a.startswith("GH_") or a.startswith("GITHUB_") for a in argv)
    tail = argv[argv.index("pytest") - 1 :]
    assert tail[:3] == ["-m", "pytest", "-q"]
    assert ["-c", str(tree / "tests/kit/pytest.ini")] == tail[tail.index("-c") : tail.index("-c") + 2]
    assert tail[-1] == str(tree / BUDGET_TEST)


@pytest.mark.parametrize(
    ("out", "found"),
    [
        (f"FAILED {BUDGET_ID} - assert 5 <= 3\n1 failed", BUDGET_ID),
        (f"ERROR {BUDGET_TEST} - ImportError\n", BUDGET_TEST),
        ("1 failed in 0.1s\n", "pytest"),
    ],
)
def test_the_hold_names_the_first_failing_test(out, found):
    """REQ-046: brief #667 answer 1 (`(<file>::<test>)`; with no test named, the step)."""
    assert merge_cleared.first_failure(out, Path("/scratch/tree")) == found
