"""The generated test map is read and rebuilt before tests are chosen (SPEC-0055 rule 5).

REQ-062 AC3, brief #833. `impact.py` reads the entries of a `.agk-test-map.toml` of the head's tree
when `[testing] map_source = "generated"`, as a union with the project's own map, and writes
nothing; its callers rebuild a missing or stale file first. Invented projects in `tmp_path`
(example.com); no network, no install.
"""

from __future__ import annotations

import json

import impact
import prepush
import pytest
import test_map

SETTING = "setting: testing.map_source"
HEAD = (
    'default_branch = "main"\nproject_tests = "exit 0"\ntest_dirs = ["tests"]\n'
    'test_patterns = ["test_*"]\n'
)
OWN_MAP = 'map = [{ code = "own/**", tests = ["tests/test_own.py"] }]\n'
GENERATED = f'[testing]\nmap_source = "generated"\npr_tests = "selected"\n{OWN_MAP}'
FILES = {
    ".gitignore": f"{impact.MAP_FILE}\n",
    "src/checkout.py": "from src import pricing\n",
    "src/pricing.py": "RATE = 1\n",
    "own/thing.py": "THING = 1\n",
    "data/rates.txt": "1\n",
    "tests/test_checkout.py": "from src import checkout\n",
    "tests/test_own.py": "# own\n",
    "tests/test_rates.py": 'RATES = "data/rates.txt"\n',
}
PULL = {"EVENT": "pull_request", "AGK_BASE": "main"}


def start(repo, testing: str = GENERATED, files: dict | None = None) -> None:
    repo.commit({"agk.toml": HEAD + testing, **FILES, **(files or {})}, "base")
    repo.branch("feature")


def change(repo, *paths: str) -> None:
    repo.commit({p: "# changed\n" for p in paths}, "change")


def base(repo) -> str:
    return repo.git("rev-parse", "main").strip()


def found(repo) -> impact.Impact:
    return impact.impact(repo.root, base(repo), "HEAD")


def chosen(result: impact.Impact) -> list[str]:
    return [s.test for s in result.selected]


def map_path(repo):
    return repo.root / impact.MAP_FILE


def map_lines(result: impact.Impact) -> list[str]:
    return [line for line in impact.text(result) if SETTING in line]


def test_the_selection_is_the_union_of_the_generated_map_and_the_projects_own(repo):
    """REQ-062 AC3: brief #833 answer 1 (SPEC-0055 rule 5, the union)."""
    start(repo)
    change(repo, "src/pricing.py", "own/thing.py")
    test_map.main(["build", "--root", str(repo.root)])
    result = found(repo)
    assert chosen(result) == ["tests/test_checkout.py", "tests/test_own.py"]
    assert result.full is False and map_lines(result) == []
    assert impact.text(result)[0] == "tests: map generated"


def test_impact_reads_only_and_writes_nothing(repo):
    """REQ-062 AC3: brief #833 answer 1 (`impact.py` stays read-only)."""
    start(repo)
    change(repo, "src/pricing.py")
    result = found(repo)
    assert not map_path(repo).exists() and chosen(result) == []


def test_a_map_of_another_tree_adds_no_entries(repo):
    """REQ-062 AC3: brief #833 answer 1 (a file whose first line names the head's tree)."""
    start(repo)
    test_map.main(["build", "--root", str(repo.root)])
    change(repo, "src/pricing.py")
    before = map_path(repo).read_bytes()
    result = found(repo)
    assert chosen(result) == [] and map_path(repo).read_bytes() == before
    assert len(map_lines(result)) == 1


@pytest.mark.parametrize("body", ["not toml [", '[[testing.map]]\ncode = "/out"\ntests = ["a"]\n'])
def test_a_map_that_cannot_be_read_adds_no_entries(repo, body):
    """REQ-062 AC3: brief #833 answer 4 (hand-edited to something no selection can use)."""
    start(repo)
    change(repo, "src/pricing.py")
    tree = repo.git("rev-parse", "HEAD^{tree}").strip()
    map_path(repo).write_text(f"# tree {tree}\n{body}", encoding="utf-8")
    result = found(repo)
    assert chosen(result) == [] and len(map_lines(result)) == 1


def test_refresh_builds_a_missing_map(repo):
    """REQ-062 AC3: brief #833 answer 2 (missing)."""
    start(repo)
    change(repo, "src/pricing.py")
    test_map.refresh(repo.root)
    assert chosen(found(repo)) == ["tests/test_checkout.py"]


def test_refresh_rebuilds_a_stale_map(repo):
    """REQ-062 AC3: brief #833 answer 2 (its first line names another tree)."""
    start(repo)
    test_map.main(["build", "--root", str(repo.root)])
    change(repo, "src/pricing.py")
    test_map.refresh(repo.root)
    tree = repo.git("rev-parse", "HEAD^{tree}").strip()
    assert map_path(repo).read_text(encoding="utf-8").startswith(f"# tree {tree}\n")
    assert chosen(found(repo)) == ["tests/test_checkout.py"]


def test_refresh_prints_nothing(repo, capsys):
    """REQ-062 AC3: brief #833 answer 2 (a caller's output, JSON included, stays its own)."""
    start(repo)
    test_map.refresh(repo.root)
    assert map_path(repo).is_file() and capsys.readouterr() == ("", "")


def test_the_test_plan_rebuilds_so_the_plan_shown_is_the_plan_run(repo):
    """REQ-062 AC3: brief #833 answer 2 (`test_plan.py`, and its JSON stays JSON)."""
    start(repo)
    change(repo, "src/pricing.py")
    done = repo.run("test_plan.py", "--json", "--base", "main")
    assert done.returncode == 0, done.stdout + done.stderr
    selected = json.loads(done.stdout)["regression"]["selected"]
    assert [s["file"] for s in selected] == ["tests/test_checkout.py"]


def test_the_test_plan_of_another_head_builds_nothing(repo):
    """REQ-062 AC3: brief #833 answer 4 (`test_map.py build` reads only the checked-out head)."""
    start(repo)
    change(repo, "src/pricing.py")
    change(repo, "own/thing.py")
    done = repo.run("test_plan.py", "--base", "main", "--head", "HEAD~1")
    assert done.returncode == 0, done.stdout + done.stderr
    assert not map_path(repo).exists()
    assert sum(SETTING in line for line in done.stdout.splitlines()) == 1


def test_project_tests_rebuilds_before_the_selection(repo):
    """REQ-062 AC3: brief #833 answer 2 (`project_tests.py` in CI)."""
    start(repo)
    change(repo, "src/pricing.py")
    done = repo.run("project_tests.py", **PULL)
    assert done.returncode == 0, done.stdout + done.stderr
    assert map_path(repo).is_file() and "file: tests/test_checkout.py" in done.stdout


def test_project_tests_under_full_rebuilds_on_a_pull_request_only(repo):
    """REQ-062 AC3: brief #833 answer 2 (under `full` only a pull request's links select)."""
    start(repo, GENERATED.replace('pr_tests = "selected"\n', ""))
    change(repo, "src/pricing.py")
    assert repo.run("project_tests.py", EVENT="push").returncode == 0
    assert not map_path(repo).exists()
    assert repo.run("project_tests.py", **PULL).returncode == 0
    assert map_path(repo).is_file()


def test_prepush_rebuilds_before_the_selection(repo, monkeypatch):
    """REQ-062 AC3: brief #833 answer 2 (`prepush.py` on a machine)."""
    start(repo)
    change(repo, "src/pricing.py")
    seen = []

    def spy(_root, _own, result, *_rest):
        seen.append(chosen(result))
        return prepush.Step("ok", "")

    monkeypatch.setattr(prepush, "gate", spy)
    ran = prepush.Ran([], repo.root, 0, "")
    step = prepush.regression_step(repo.root, base(repo), [], [], ran, False)
    assert step.status == "ok" and seen == [["tests/test_checkout.py"]]


@pytest.mark.parametrize(
    "testing", [f"[testing]\n{OWN_MAP}", f'[testing]\nmap_source = "curated"\n{OWN_MAP}']
)
def test_curated_or_absent_reads_nothing_and_rebuilds_nothing(repo, testing):
    """REQ-062 AC3: brief #833 answer 3 (SPEC-0055 rule 1)."""
    start(repo, testing)
    change(repo, "src/pricing.py", "own/thing.py")
    without = repo.run("test_plan.py", "--base", "main")
    assert not map_path(repo).exists()
    test_map.main(["build", "--root", str(repo.root)])  # a current file, of this very tree
    before = map_path(repo).read_bytes()
    result = found(repo)
    assert chosen(result) == ["tests/test_own.py"] and map_lines(result) == []
    assert repo.run("test_plan.py", "--base", "main").stdout == without.stdout
    map_path(repo).write_text("# tree stale\n", encoding="utf-8")
    test_map.refresh(repo.root)
    assert map_path(repo).read_text(encoding="utf-8") == "# tree stale\n"
    assert before.startswith(b"# tree ")


def test_a_map_that_cannot_be_built_leaves_rule_6_to_the_files_it_would_have_covered(repo):
    """REQ-062 AC3: brief #833 answer 4 (a committed map is refused by `test_map.py build`)."""
    start(repo, files={".gitignore": "# none\n", impact.MAP_FILE: "# tree committed\n"})
    change(repo, "src/pricing.py", "data/rates.txt")
    test_map.refresh(repo.root)
    assert map_path(repo).read_text(encoding="utf-8") == "# tree committed\n"
    result = found(repo)
    assert chosen(result) == ["tests/test_rates.py"]
    assert result.named == {"data/rates.txt": 1, "src/pricing.py": 0} and result.full is True
    lines = map_lines(result)
    assert len(lines) == 1 and "committed" not in lines[0] and "tree" not in lines[0]
    assert result.data()["map_notes"] == lines


def test_a_build_that_breaks_does_not_stop_the_selection(repo, monkeypatch):
    """REQ-062 AC3: brief #833 answer 4 (any failure of the build adds no entries)."""
    start(repo)
    change(repo, "src/pricing.py")

    def broken(_root):
        raise ValueError("example failure")

    monkeypatch.setattr(test_map, "write_map", broken)
    test_map.refresh(repo.root)
    assert not map_path(repo).exists() and len(map_lines(found(repo))) == 1


def test_only_documentation_reads_no_map_and_says_nothing(repo):
    """REQ-062 AC3: a change that selects nothing needs no map, so no line says one is missing."""
    start(repo, files={"docs/a.md": "# a\n"})
    change(repo, "docs/a.md")
    assert map_lines(found(repo)) == []


def test_two_commits_with_one_tree_give_the_same_bytes(repo):
    """REQ-062 AC3: brief #833 tests (SPEC-0055 rule 5, the same tree gives the same bytes)."""
    start(repo)
    test_map.refresh(repo.root)
    first = map_path(repo).read_bytes()
    stamp = map_path(repo).stat().st_mtime_ns
    repo.git("commit", "-q", "--allow-empty", "-m", "same tree")
    test_map.refresh(repo.root)
    assert map_path(repo).stat().st_mtime_ns == stamp  # still current: not rebuilt
    map_path(repo).unlink()
    test_map.refresh(repo.root)
    assert map_path(repo).read_bytes() == first


def test_uncovered_counts_a_current_generated_map(repo):
    """REQ-062 AC3: the doctor's list of what would turn a selection full reads the union."""
    start(repo)
    assert "src/pricing.py" in impact.uncovered(repo.root)
    test_map.refresh(repo.root)
    assert "src/pricing.py" not in impact.uncovered(repo.root)
