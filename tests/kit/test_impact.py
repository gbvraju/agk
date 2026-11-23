"""The `[testing]` table and the regression selection (brief #373, ADR-0220; REQ-016).

`scripts/agk/impact.py` reads git and files only. For a change base..head it gives the test files
that the `map` of the `[testing]` table selects, each with the changed file and the entry that chose
it; `full`, with its reason, when a changed file matches `always_full` or the profile is
`thorough`; and the changed files outside the test folders that no entry covers (`unmapped`), which
make `full` under `balanced` and are only listed under `fast`. A change of only `*.md` files and
files under `docs/` selects nothing under every profile. `test_plan.py` prints the selection as its
`regression` section, in text and in `--json`; without the table it prints
`regression: full (no [testing] table)`. Nothing runs the selection yet (answer 4).
"""

from __future__ import annotations

import json
from pathlib import Path

import impact
import pytest
import session
from common import CheckError

BASE_TOML = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'

MAP = (
    "map = [\n"
    '  { code = "app/billing/**", tests = ["tests/billing/**"] },\n'
    '  { code = "app/shop/*.py", tests = ["tests/shop/test_*.py", "tests/test_smoke.py"] },\n'
    "]\n"
)

BASE_FILES = {
    "app/billing/pay.py": "# pay\n",
    "app/shop/cart.py": "# cart\n",
    "app/auth/login.py": "# login\n",
    "app/other.py": "# other\n",
    "tests/billing/test_pay.py": "# test pay\n",
    "tests/billing/conftest.py": "# not a test file\n",
    "tests/shop/test_cart.py": "# test cart\n",
    "tests/test_smoke.py": "# smoke\n",
    "tests/auth/test_login.py": "# test login\n",
    "docs/guide.md": "# guide\n",
    "README.md": "# readme\n",
}


def table_text(profile: str | None = None, always_full: str | None = None, body: str = MAP) -> str:
    text = "[testing]\n"
    if profile is not None:
        text += f'profile = "{profile}"\n'
    if always_full is not None:
        text += f"always_full = {always_full}\n"
    return text + body


def start(repo, table: str | None) -> None:
    toml = BASE_TOML + "project_tests = 'exit 0'\n" + (table or "")
    repo.commit({"agk.toml": toml, **BASE_FILES}, "base")
    repo.branch("feature")


def change(repo, *paths: str) -> None:
    repo.commit({p: "# changed\n" for p in paths}, "change")


def result(repo) -> impact.Impact:
    base = repo.git("rev-parse", "main").strip()
    head = repo.git("rev-parse", "HEAD").strip()
    return impact.impact(repo.root, base, head)


def plan(repo, *args: str):
    return repo.run("test_plan.py", "--base", "main", *args)


def regression(repo) -> dict:
    proc = plan(repo, "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)["regression"]


def test_a_mapped_change_selects_the_tests_of_its_entry_with_the_reason(repo):
    """REQ-016: brief #373 answer 2 (the selected test files, each with its file and entry)."""
    start(repo, table_text())
    change(repo, "app/billing/pay.py", "app/shop/cart.py")
    found = result(repo)
    assert found.table is True and found.profile == "balanced"
    assert found.full is False and found.reason is None
    assert found.unmapped == []
    assert [s.test for s in found.selected] == [
        "tests/billing/test_pay.py",
        "tests/shop/test_cart.py",
        "tests/test_smoke.py",
    ]
    pay = found.selected[0]
    assert (pay.changed, pay.code, pay.tests) == (
        "app/billing/pay.py",
        "app/billing/**",
        ["tests/billing/**"],
    )
    doc = regression(repo)
    assert doc["full"] is False and doc["reason"] is None
    assert doc["selected"][0] == {
        "file": "tests/billing/test_pay.py",
        "changed": "app/billing/pay.py",
        "code": "app/billing/**",
        "tests": ["tests/billing/**"],
    }
    out = plan(repo).stdout
    assert "regression: 3 test files selected\n" in out
    assert (
        "  file: tests/billing/test_pay.py (app/billing/pay.py matches code app/billing/**, "
        "tests tests/billing/**)\n" in out
    )


def test_only_existing_test_files_are_selected(repo):
    """REQ-016: brief #373 answer 2 (an existing test file, by test_dirs and test_patterns)."""
    start(repo, table_text())
    repo.commit({"app/billing/pay.py": "# changed\n", "tests/billing/test_pay.py": None}, "change")
    found = result(repo)
    # conftest.py is under the glob but is not a test file; the deleted test is not selected, so
    # the entry guards the change with no test and the file is unmapped (verdict on e258a97, 1).
    assert found.selected == [] and found.unmapped == ["app/billing/pay.py"]
    assert found.full is True and found.reason == "profile balanced: 1 unmapped file"


@pytest.mark.parametrize("profile", ["fast", "balanced"])
def test_an_entry_whose_tests_select_no_file_leaves_its_code_unmapped(repo, profile):
    """REQ-016: brief #373 answer 2 (verdict on e258a97, item 1: never silently fewer tests)."""
    typo = 'map = [{ code = "app/billing/**", tests = ["tests/biling/**"] }]\n'
    start(repo, table_text(profile=profile, body=typo))
    change(repo, "app/billing/pay.py")
    found = result(repo)
    assert found.selected == [] and found.unmapped == ["app/billing/pay.py"]
    assert found.full is (profile == "balanced")
    out = plan(repo).stdout
    assert "unmapped (no [testing] map entry covers it): app/billing/pay.py\n" in out


def test_an_always_full_path_makes_the_selection_full(repo):
    """REQ-016: brief #373 answer 2 (always_full)."""
    start(repo, table_text(always_full='["app/auth/**", "migrations/**"]'))
    change(repo, "app/billing/pay.py", "app/auth/login.py")
    found = result(repo)
    assert found.full is True
    assert found.reason == "always_full app/auth/** matches app/auth/login.py"
    out = plan(repo).stdout
    assert "regression: full (always_full app/auth/** matches app/auth/login.py)\n" in out


def test_an_unmapped_file_makes_balanced_full(repo):
    """REQ-016: brief #373 answer 2 (when unsure, run more)."""
    start(repo, table_text(profile="balanced"))
    change(repo, "app/billing/pay.py", "app/other.py")
    found = result(repo)
    assert found.unmapped == ["app/other.py"]
    assert found.full is True and found.reason == "profile balanced: 1 unmapped file"
    out = plan(repo).stdout
    assert "regression: full (profile balanced: 1 unmapped file)\n" in out
    assert "unmapped: app/other.py -> 0 tests that name it\n" in out


def test_an_unmapped_file_under_fast_is_only_listed(repo):
    """REQ-016: brief #373 answer 2 (under fast an unmapped file is only listed)."""
    start(repo, table_text(profile="fast"))
    change(repo, "app/billing/pay.py", "app/other.py")
    found = result(repo)
    assert found.full is False and found.reason is None
    assert found.unmapped == ["app/other.py"]
    assert [s.test for s in found.selected] == ["tests/billing/test_pay.py"]
    doc = regression(repo)
    assert doc["profile"] == "fast" and doc["unmapped"] == ["app/other.py"]
    out = plan(repo).stdout
    assert "regression: 1 test file selected\n" in out
    assert "unmapped (no [testing] map entry covers it): app/other.py\n" in out


def test_a_changed_test_file_is_not_unmapped(repo):
    """REQ-016: brief #373 answer 2 (unmapped files are outside the test folders)."""
    start(repo, table_text())
    change(repo, "tests/auth/test_login.py")
    found = result(repo)
    assert found.unmapped == [] and found.full is False and found.selected == []


@pytest.mark.parametrize("profile", ["fast", "balanced", "thorough"])
def test_a_docs_only_change_selects_nothing_under_every_profile(repo, profile):
    """REQ-016: brief #373 answer 2 (only *.md and docs/ files select nothing)."""
    start(repo, table_text(profile=profile, always_full='["app/auth/**"]'))
    repo.commit({"docs/guide.md": "# changed\n", "docs/img/a.svg": "<svg/>\n", "README.md": "x\n"})
    found = result(repo)
    assert found.full is False and found.reason is None
    assert found.selected == [] and found.unmapped == []
    assert "regression: nothing selected (only documentation changed)\n" in plan(repo).stdout


@pytest.mark.parametrize("profile", ["fast", "balanced", "thorough"])
def test_always_full_wins_over_a_docs_only_change(repo, profile):
    """REQ-016: brief #373 answer 2 (Q-373-1, answered on e258a97: the conservative reading)."""
    start(repo, table_text(profile=profile, always_full='["docs/**"]'))
    change(repo, "docs/guide.md")
    found = result(repo)
    assert found.full is True and found.reason == "always_full docs/** matches docs/guide.md"
    assert "regression: full (always_full docs/** matches docs/guide.md)\n" in plan(repo).stdout


@pytest.mark.parametrize("profile", ["fast", "balanced", "thorough"])
def test_an_empty_change_is_not_read_as_docs_only(repo, profile):
    """REQ-016: brief #373 answer 2 (verdict on e258a97, item 3)."""
    start(repo, table_text(profile=profile))
    repo.git("commit", "-q", "--allow-empty", "-m", "empty")
    found = result(repo)
    assert found.docs_only is False and found.selected == [] and found.unmapped == []
    assert found.full is (profile == "thorough")
    assert "only documentation changed" not in plan(repo).stdout


def test_a_helper_under_the_test_folder_is_unmapped(repo):
    """REQ-016: brief #373 answer 2 (verdict on e258a97, item 2; Q-373-4)."""
    start(repo, table_text())
    change(repo, "tests/conftest.py")
    found = result(repo)
    assert found.unmapped == ["tests/conftest.py"] and found.full is True


def test_test_dirs_dot_still_finds_unmapped_files(repo):
    """REQ-016: brief #373 answer 2 (verdict on e258a97, item 2; Q-373-4)."""
    toml = 'default_branch = "main"\ntest_dirs = ["."]\ntest_patterns = ["test_*.py"]\n'
    repo.commit({"agk.toml": toml + table_text(), **BASE_FILES}, "base")
    repo.branch("feature")
    change(repo, "app/other.py", "tests/auth/test_login.py")
    found = result(repo)
    assert found.unmapped == ["app/other.py"] and found.full is True


def test_a_markdown_file_beside_code_is_not_unmapped(repo):
    """REQ-016: brief #373 answer 2 (Q-373-2: a *.md or docs/ file is never unmapped)."""
    start(repo, table_text())
    change(repo, "app/billing/pay.py", "app/billing/NOTES.md", "docs/guide.md")
    found = result(repo)
    assert found.unmapped == [] and found.full is False


def test_thorough_is_always_full(repo):
    """REQ-016: brief #373 answer 2 (the thorough profile)."""
    start(repo, table_text(profile="thorough"))
    change(repo, "app/billing/pay.py")
    found = result(repo)
    assert found.full is True and found.reason == "profile thorough"
    assert "regression: full (profile thorough)\n" in plan(repo).stdout


BAD = [
    ('testing = "yes"\n', "setting: testing"),
    ('[testing]\nprofile = "quick"\n', "setting: testing.profile"),
    ('[testing]\nalways_full = "app/**"\n', "setting: testing.always_full"),
    ('[testing]\nalways_full = ["", "x/**"]\n', "setting: testing.always_full"),
    ('[testing]\nmap = { code = "a/**", tests = ["t/**"] }\n', "setting: testing.map"),
    ('[testing]\nmap = [{ code = "a/**" }]\n', "setting: testing.map[1].tests"),
    ('[testing]\nmap = [{ code = "a/**", tests = [] }]\n', "setting: testing.map[1].tests"),
    ('[testing]\nmap = [{ code = "", tests = ["t/**"] }]\n', "setting: testing.map[1].code"),
    (
        '[testing]\nmap = [{ code = "a/**", tests = ["t/**"], run = "x" }]\n',
        "setting: testing.map[1]",
    ),
    ('[testing]\nmap = [{ code = "../a/**", tests = ["t/**"] }]\n', "setting: testing.map[1].code"),
    ('[testing]\nmap = [{ code = "a/**", tests = ["/t/**"] }]\n', "setting: testing.map[1].tests"),
    ("[testing]\nbudget_seconds = 0\n", "setting: testing.budget_seconds"),
    ("[testing]\nbudget_seconds = true\n", "setting: testing.budget_seconds"),
    ('[testing]\nbudget_seconds = "300"\n', "setting: testing.budget_seconds"),
    ('[testing]\nprofiles = "fast"\n', "setting: testing"),
    ('[testing]\nalways_full = ["app\\\\auth\\\\**"]\n', "setting: testing.always_full"),
    (
        '[testing]\nmap = [{ code = "app\\\\b/**", tests = ["t/**"] }]\n',
        "setting: testing.map[1].code",
    ),
    (
        '[testing]\nmap = [{ code = "a/**", tests = ["tests\\\\b\\\\**"] }]\n',
        "setting: testing.map[1].tests",
    ),
]


@pytest.mark.parametrize(("table", "setting"), BAD)
def test_a_bad_table_is_refused_naming_the_setting(repo, table, setting):
    """REQ-016: brief #373 answer 1 (a bad entry is refused, naming the setting)."""
    start(repo, table)
    change(repo, "app/billing/pay.py")
    with pytest.raises(CheckError) as caught:
        result(repo)
    assert f"({setting})" in str(caught.value)
    proc = plan(repo)
    assert proc.returncode == 2
    assert proc.stdout.startswith("FAIL test-plan: ") and f"({setting})" in proc.stdout


def test_a_good_table_reads_its_settings(repo):
    """REQ-016: brief #373 answer 1 (profile, always_full, map, budget_seconds)."""
    table = table_text(profile="fast", always_full='["migrations/**"]') + "budget_seconds = 120\n"
    start(repo, table)
    found = impact.testing_table(repo.root)
    assert found == {
        "profile": "fast",
        "always_full": ["migrations/**"],
        "map": [
            {"code": "app/billing/**", "tests": ["tests/billing/**"]},
            {"code": "app/shop/*.py", "tests": ["tests/shop/test_*.py", "tests/test_smoke.py"]},
        ],
        "budget_seconds": 120,
    }
    assert impact.testing_table(repo.root.parent / "absent") is None


def test_an_empty_table_takes_the_defaults(repo):
    """REQ-016: brief #373 answer 1 (balanced and 300 seconds by default)."""
    start(repo, "[testing]\n")
    assert impact.testing_table(repo.root) == {
        "profile": "balanced",
        "always_full": [],
        "map": [],
        "budget_seconds": 300,
    }
    change(repo, "app/billing/pay.py")
    found = result(repo)
    assert found.full is True and found.unmapped == ["app/billing/pay.py"]


def test_no_table_prints_full_as_governance_runs_today(repo):
    """REQ-016: brief #373 answer 3 (no [testing] table)."""
    start(repo, None)
    change(repo, "app/billing/pay.py")
    found = result(repo)
    assert found.table is False and found.full is True
    assert found.reason == "no [testing] table"
    out = plan(repo).stdout
    assert "regression: full (no [testing] table)\n" in out
    doc = regression(repo)
    assert doc == {
        "table": False,
        "profile": None,
        "full": True,
        "reason": "no [testing] table",
        "selected": [],
        "unmapped": [],
    }


@pytest.mark.parametrize(
    ("glob", "path", "hit"),
    [
        ("app/**", "app/a/b.py", True),
        ("app/**", "app", False),
        ("app/", "app/a.py", True),
        ("app/*.py", "app/a.py", True),
        ("app/*.py", "app/x/a.py", False),
        ("**/test_*.py", "test_a.py", True),
        ("**/test_*.py", "x/y/test_a.py", True),
        ("src/?.c", "src/a.c", True),
        ("src/?.c", "src/ab.c", False),
        ("a.b", "aXb", False),
    ],
)
def test_globs_keep_star_in_one_folder_and_double_star_across(glob, path, hit):
    """REQ-016: brief #373 answer 1 (path globs, as the session plan reads them)."""
    assert impact.matches(path, glob) is hit
    assert (session.glob_regex(glob).fullmatch(path) is not None) is hit


INFRA = "tests/kit/test_always_full_infra.py"
MAP_FILES = {
    "app/a.py": "# a\n",
    "tests/test_a.py": "# a\n",
    "tests/test_b.py": "# b\n",
    "tests/test_config.py": "# reads agk.toml\n",
    INFRA: "# infra\n",
}


def map_toml(tests: str = '"tests/test_a.py"', builders: int = 2) -> str:
    return (
        BASE_TOML
        + f'[flow]\nmax_builders = {builders}\n[testing]\nprofile = "balanced"\n'
        + f'[[testing.map]]\ncode = "app/a.py"\ntests = [{tests}]\n'
    )


def map_change(repo, head_toml: str, base_toml: str | None = None) -> impact.Impact:
    repo.commit({"agk.toml": base_toml or map_toml(), **MAP_FILES}, "base")
    repo.branch("feature")
    repo.commit({"agk.toml": head_toml}, "change")
    return result(repo)


AB = '"tests/test_a.py", "tests/test_b.py"'


@pytest.mark.parametrize(
    ("base", "head", "picked"),
    [
        ('"tests/test_a.py"', AB, [INFRA, "tests/test_b.py"]),  # a name added
        (AB, '"tests/test_b.py"', [INFRA, "tests/test_a.py"]),  # a name removed
        ('"tests/test_a.py"', '"tests/test_a.py", "tests/gone.py"', [INFRA]),  # no such file
    ],
)
def test_a_test_map_only_change_of_agk_toml_selects_only_its_tests(repo, base, head, picked):
    """REQ-051: brief #1198 answers 1, 2 and 4a (the names the map changed, and the infra test)."""
    found = map_change(repo, map_toml(head), map_toml(base))
    assert found.full is False and found.unmapped == [] and found.named == {}
    assert [s.test for s in found.selected] == picked
    assert {(s.changed, s.code) for s in found.selected} == {("agk.toml", impact.MAP_ONLY)}
    assert "tests/test_config.py" not in [s.test for s in found.selected]
    doc = regression(repo)
    assert doc["selected"][0]["code"] == "agk.toml (testing map only)"
    assert f"  file: {INFRA} (agk.toml (testing map only))\n" in plan(repo).stdout


def test_a_name_moved_between_map_entries_is_selected(repo):
    """REQ-051: brief #1198 answer 1 (a name moved from one entry to another)."""
    moved = (
        map_toml('"tests/test_b.py"')
        + '[[testing.map]]\ncode = "app/b.py"\ntests = ["tests/test_a.py"]\n'
    )
    found = map_change(repo, moved, map_toml(AB))
    assert [s.test for s in found.selected] == [INFRA, "tests/test_a.py"]


@pytest.mark.parametrize(
    "head",
    [
        map_toml(builders=3),  # 4b: another setting changed
        map_toml(AB, builders=3),  # 4c: both
    ],
)
def test_any_other_change_of_agk_toml_keeps_the_tests_that_name_it(repo, head):
    """REQ-051: brief #1198 answers 1 and 4b, 4c (today's rule, exactly)."""
    found = map_change(repo, head)
    assert [(s.test, s.code) for s in found.selected] == [("tests/test_config.py", impact.NAMED)]
    assert found.unmapped == ["agk.toml"] and found.named == {"agk.toml": 1}


@pytest.mark.parametrize("end", ["base", "head"])
def test_an_agk_toml_that_does_not_parse_keeps_todays_rule(repo, end):
    """REQ-051: brief #1198 answers 1 and 4d (a file that does not parse at either end)."""
    good = map_toml(AB)
    repo.commit({"agk.toml": map_toml() + ("[[x\n" if end == "base" else ""), **MAP_FILES}, "base")
    repo.branch("feature")
    repo.commit({"agk.toml": good + ("[[x\n" if end == "head" else "")}, "change")
    repo.write("agk.toml", good)  # the working tree reads; the commits are what is compared
    found = result(repo)
    assert [(s.test, s.code) for s in found.selected] == [("tests/test_config.py", impact.NAMED)]
    assert found.named == {"agk.toml": 1}


# Brief #1792: a path built in parts is a name, and a shipped Markdown file is not documentation.
JOIN_TEST = (
    "from pathlib import Path\n"
    "ROOT = Path(__file__).resolve().parents[1]\n"
    'SKILL = ROOT / "skills" / "x" / "SKILL.md"\n'
    'RATES = ROOT / "app" / "data" / "rates.json"\n'
)
JOIN_FILES = {
    "guides/x.md": "# guide\n",
    "skills/x/SKILL.md": "# skill\n",
    "app/data/rates.json": "{}\n",
    "tests/test_join.py": JOIN_TEST,
    "config/protected-paths.txt": "# classes\nskills/\ndocs/requirements.md\n",
    "docs/requirements.md": "# requirements\n",
}


def start_joins(repo, body: str = MAP) -> None:
    toml = BASE_TOML + "project_tests = 'exit 0'\n" + table_text(body=body)
    repo.commit({"agk.toml": toml, **BASE_FILES, **JOIN_FILES}, "base")
    repo.branch("feature")


@pytest.mark.parametrize("path", ["skills/x/SKILL.md", "app/data/rates.json"])
def test_a_test_that_reads_a_file_by_a_literal_join_is_selected_by_its_change(repo, path):
    """REQ-062: brief #1792 answers 1 and 2 (a join of quoted literals names the file)."""
    start_joins(repo)
    change(repo, path)
    found = result(repo)
    assert found.docs_only is False and found.full is False
    assert [(s.test, s.code) for s in found.selected] == [("tests/test_join.py", impact.NAMED)]
    assert found.named == {path: 1}


def test_a_mapped_markdown_file_is_code_and_selects_its_entry(repo):
    """REQ-062: brief #1792 answer 2 (a mapped `*.md` outside docs/ is not documentation)."""
    guides = '  { code = "guides/**", tests = ["tests/test_smoke.py"] },\n'
    body = MAP.replace("map = [\n", "map = [\n" + guides)
    start_joins(repo, body)
    change(repo, "guides/x.md")
    found = result(repo)
    assert found.docs_only is False and found.full is False
    assert [s.test for s in found.selected] == ["tests/test_smoke.py"]


@pytest.mark.parametrize("path", ["docs/guide.md", "docs/requirements.md", "README.md"])
def test_documentation_stays_documentation(repo, path):
    """REQ-062: brief #1792 answers 2 and 5 (docs/ and an unmapped, unprotected `*.md`)."""
    start_joins(repo)
    change(repo, path)
    found = result(repo)
    assert found.docs_only is True and found.selected == [] and found.full is False


@pytest.mark.parametrize(
    ("source", "paths"),
    [
        ('os.path.join("a", "b.md")', {"a/b.md"}),
        ("Path('a', 'b.md')", {"a/b.md"}),
        ('PurePosixPath("a/b", "c.txt")', {"a/b/c.txt"}),
        ('ROOT / "kit" / "skills" / "*" / "SKILL.md"', {"kit/skills/"}),
        ('ROOT / "a" / name / "SKILL.md"', set()),  # one literal before the variable: no join
        ('ROOT / "a" / "b" / name / "c.md"', {"a/b"}),
        ('os.path.join(ROOT, "a", "b.md")', set()),  # an argument that is not a literal
        ('x = "a" + "b"', set()),
    ],
)
def test_the_paths_a_join_names(source, paths):
    """REQ-062: brief #1792 answers 1 and 5 (joins, calls, globs and variable parts)."""
    assert impact.joined_paths(source) == paths


def test_the_replay_of_the_upgrade_skill_change_selects_its_test():
    """REQ-062: brief #1792 answer 6 (the replay of #1773 on the kit's own history)."""
    root = Path(__file__).resolve().parents[2]
    base, head = "ee47218b", "11255059"
    if impact.git(root, "cat-file", "-t", head, check=False).strip() != "commit":
        pytest.skip("the replayed commits are not in this clone")
    found = impact.select(root, base, head)
    assert found.full or "tests/kit/test_upgrade_adr.py" in [s.test for s in found.selected]


# Brief #1796 (amendment 186 build (k), ADR-0650): `[testing] whole_tests`, the tests that read
# every file of a kind, added to every change that is not documentation only.
WHOLE = 'whole_tests = ["tests/test_smoke.py", "tests/auth/test_login.py"]\n'
WHOLE_LINES = "whole: tests/auth/test_login.py\nwhole: tests/test_smoke.py\n"


def whole_of(found: impact.Impact) -> list[str]:
    return [s.test for s in found.selected if s.code == impact.WHOLE]


def test_without_whole_tests_the_selection_is_todays(repo):
    """REQ-062: brief #1796 answer 6 (the key absent: no `whole:` line, no added test)."""
    start(repo, table_text())
    change(repo, "app/billing/pay.py")
    found = result(repo)
    assert [s.test for s in found.selected] == ["tests/billing/test_pay.py"]
    assert found.whole == [] and "whole" not in found.data()
    assert "whole:" not in plan(repo).stdout


@pytest.mark.parametrize("profile", ["fast", "balanced"])
def test_the_listed_tests_are_added_with_a_whole_line_under_each_profile(repo, profile):
    """REQ-062: brief #1796 answers 1 and 2 (added after the other steps, `whole:` lines last)."""
    start(repo, table_text(profile=profile) + WHOLE)
    change(repo, "app/billing/pay.py")
    found = result(repo)
    assert found.full is False
    assert [s.test for s in found.selected] == [
        "tests/auth/test_login.py",
        "tests/billing/test_pay.py",
        "tests/test_smoke.py",
    ]
    assert whole_of(found) == ["tests/auth/test_login.py", "tests/test_smoke.py"]
    assert found.whole == ["tests/auth/test_login.py", "tests/test_smoke.py"]
    assert found.unmapped == []  # the list covers no changed file
    out = plan(repo).stdout
    assert "regression: 3 test files selected\n" in out
    assert out.endswith(WHOLE_LINES), out
    assert "  file: tests/test_smoke.py" not in out
    assert regression(repo)["whole"] == ["tests/auth/test_login.py", "tests/test_smoke.py"]


def test_thorough_with_whole_tests_stays_full(repo):
    """REQ-062: brief #1796 answer 6 (`thorough` is full anyway)."""
    start(repo, table_text(profile="thorough") + WHOLE)
    change(repo, "app/billing/pay.py")
    found = result(repo)
    assert found.full is True and found.reason == "profile thorough"


def test_a_listed_test_also_selected_by_the_map_runs_once_with_its_map_reason(repo):
    """REQ-062: brief #1796 answer 2 (a file both listed and selected runs once)."""
    start(repo, table_text() + WHOLE)
    change(repo, "app/shop/cart.py")
    found = result(repo)
    tests = [s.test for s in found.selected]
    assert tests == sorted(set(tests))
    smoke = next(s for s in found.selected if s.test == "tests/test_smoke.py")
    assert smoke.code == "app/shop/*.py"
    assert whole_of(found) == ["tests/auth/test_login.py"]
    assert found.whole == ["tests/auth/test_login.py", "tests/test_smoke.py"]


def test_an_unmapped_file_stays_unmapped_beside_the_list(repo):
    """REQ-062: brief #1796 answer 2 (the list never covers a file; rule 6's fallback holds)."""
    start(repo, table_text() + WHOLE)
    change(repo, "app/other.py")
    found = result(repo)
    assert found.unmapped == ["app/other.py"]
    assert found.full is True and found.reason == "profile balanced: 1 unmapped file"


def test_a_docs_only_change_adds_no_whole_test(repo):
    """REQ-062: brief #1796 answers 2 and 3 (a change only under docs/ selects nothing)."""
    start(repo, table_text() + WHOLE)
    change(repo, "docs/guide.md", "README.md")
    found = result(repo)
    assert found.docs_only is True and found.selected == [] and found.whole == []


@pytest.mark.parametrize("path", ["skills/x/SKILL.md", "agents/a.md"])
def test_an_installed_or_protected_markdown_change_adds_the_list(repo, path):
    """REQ-062: brief #1796 answer 3 (an installed or protected `*.md` is not documentation)."""
    manifest = json.dumps({"verbatim": ["agents/a.md"], "templates": {}})
    toml = BASE_TOML + "project_tests = 'exit 0'\n" + table_text(profile="fast") + WHOLE
    files = {"agk.toml": toml, **BASE_FILES, **JOIN_FILES, "agents/a.md": "# agent\n"}
    repo.commit({**files, "kit/manifest.json": manifest}, "base")
    repo.branch("feature")
    change(repo, path)
    found = result(repo)
    assert found.docs_only is False
    assert set(whole_of(found)) == {"tests/auth/test_login.py", "tests/test_smoke.py"}


def test_an_installed_markdown_file_is_not_documentation(repo):
    """REQ-062: brief #1796 answer 3 (a path of the manifest's install lists is code)."""
    manifest = json.dumps({"verbatim": ["agents/a.md"], "templates": {"t/b.md": "b.md"}})
    repo.commit({**BASE_FILES, "kit/manifest.json": manifest, "agk.toml": BASE_TOML}, "base")
    doc = impact.doc_reader(repo.root, "HEAD")
    assert doc("agents/a.md") is False and doc("t/b.md") is False
    assert doc("agents/other.md") is True and doc("docs/guide.md") is True


WHOLE_BAD = [
    "whole_tests = []\n",
    'whole_tests = "tests/test_smoke.py"\n',
    'whole_tests = ["tests/missing_test.py"]\n',
    'whole_tests = ["tests/test_*.py"]\n',
    'whole_tests = ["/tests/test_smoke.py"]\n',
    'whole_tests = ["tests/../tests/test_smoke.py"]\n',
    'whole_tests = ["tests\\\\test_smoke.py"]\n',
    "whole_tests = [3]\n",
]


@pytest.mark.parametrize("line", WHOLE_BAD)
def test_a_bad_whole_tests_is_refused_naming_the_setting(repo, line):
    """REQ-062: brief #1796 answer 1 (each refused entry names the setting, never the value)."""
    start(repo, table_text() + line)
    change(repo, "app/billing/pay.py")
    with pytest.raises(CheckError) as caught:
        result(repo)
    message = str(caught.value)
    assert "(setting: testing.whole_tests)" in message
    assert "test_smoke" not in message and "missing_test" not in message
    proc = plan(repo)
    assert proc.returncode == 2 and "(setting: testing.whole_tests)" in proc.stdout


@pytest.mark.parametrize(
    ("base", "head", "files"),
    [
        ("6f7288da~1", "6f7288da", ["tests/kit_dev/test_distribution.py"]),
        ("0d4ba3a3~1", "0d4ba3a3", ["tests/kit/test_installed_imports.py"]),
    ],
)
def test_the_replays_select_the_whole_tests(monkeypatch, base, head, files):
    """REQ-062: brief #1796 answer 8 (the replays of #1516 and #1527 with a list set)."""
    root = Path(__file__).resolve().parents[2]
    if impact.git(root, "cat-file", "-t", head, check=False).strip() != "commit":
        pytest.skip("the replayed commits are not in this clone")
    listed = [
        "tests/kit_dev/test_distribution.py",
        "tests/kit_dev/test_playbook.py",
        "tests/kit/test_installed_imports.py",
    ]
    real = impact.testing_table
    monkeypatch.setattr(impact, "testing_table", lambda r: {**real(r), impact.WHOLE_KEY: listed})
    found = impact.select(root, base, head)
    picked = [s.test for s in found.selected]
    assert found.full or all(f in picked for f in files)
    assert found.full or all(f in found.whole for f in files)


# Brief #1839 answer 2: every written form of a test folder is one folder (`tests\` is what
# Windows writes; a TOML literal string keeps the back slash as it is).
FORMS = ["tests", "tests/", "./tests", "tests\\", ".\\tests", ".\\tests\\"]


@pytest.mark.parametrize("form", FORMS)
def test_each_written_form_of_test_dirs_selects_the_mapped_tests(repo, form):
    """REQ-079: brief #1839 answers 2 and 7 (red on main for the back-slash and `./` forms)."""
    toml = f'default_branch = "main"\ntest_dirs = [\'{form}\']\ntest_patterns = ["test_*.py"]\n'
    repo.commit({"agk.toml": toml + table_text(), **BASE_FILES}, "base")
    repo.branch("feature")
    change(repo, "app/shop/cart.py")
    found = result(repo)
    assert found.full is False and found.unmapped == []
    assert [s.test for s in found.selected] == ["tests/shop/test_cart.py", "tests/test_smoke.py"]
    assert "regression: 2 test files selected\n" in plan(repo).stdout
