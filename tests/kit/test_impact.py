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

import impact
import pytest
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


def testing(profile: str | None = None, always_full: str | None = None, body: str = MAP) -> str:
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
    start(repo, testing())
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
    start(repo, testing())
    repo.commit({"app/billing/pay.py": "# changed\n", "tests/billing/test_pay.py": None}, "change")
    found = result(repo)
    # conftest.py is under the glob but is not a test file; the deleted test is not selected.
    assert found.selected == [] and found.full is False and found.unmapped == []
    assert "regression: nothing selected\n" in plan(repo).stdout


def test_an_always_full_path_makes_the_selection_full(repo):
    """REQ-016: brief #373 answer 2 (always_full)."""
    start(repo, testing(always_full='["app/auth/**", "migrations/**"]'))
    change(repo, "app/billing/pay.py", "app/auth/login.py")
    found = result(repo)
    assert found.full is True
    assert found.reason == "always_full app/auth/** matches app/auth/login.py"
    out = plan(repo).stdout
    assert "regression: full (always_full app/auth/** matches app/auth/login.py)\n" in out


def test_an_unmapped_file_makes_balanced_full(repo):
    """REQ-016: brief #373 answer 2 (when unsure, run more)."""
    start(repo, testing(profile="balanced"))
    change(repo, "app/billing/pay.py", "app/other.py")
    found = result(repo)
    assert found.unmapped == ["app/other.py"]
    assert found.full is True and found.reason == "profile balanced: 1 unmapped file"
    out = plan(repo).stdout
    assert "regression: full (profile balanced: 1 unmapped file)\n" in out
    assert "unmapped (no [testing] map entry covers it): app/other.py\n" in out


def test_an_unmapped_file_under_fast_is_only_listed(repo):
    """REQ-016: brief #373 answer 2 (under fast an unmapped file is only listed)."""
    start(repo, testing(profile="fast"))
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
    start(repo, testing())
    change(repo, "tests/auth/test_login.py")
    found = result(repo)
    assert found.unmapped == [] and found.full is False and found.selected == []


@pytest.mark.parametrize("profile", ["fast", "balanced", "thorough"])
def test_a_docs_only_change_selects_nothing_under_every_profile(repo, profile):
    """REQ-016: brief #373 answer 2 (only *.md and docs/ files select nothing)."""
    start(repo, testing(profile=profile, always_full='["docs/**"]'))
    repo.commit({"docs/guide.md": "# changed\n", "docs/img/a.svg": "<svg/>\n", "README.md": "x\n"})
    found = result(repo)
    assert found.full is False and found.reason is None
    assert found.selected == [] and found.unmapped == []
    assert "regression: nothing selected (only documentation changed)\n" in plan(repo).stdout


def test_a_markdown_file_beside_code_is_not_unmapped(repo):
    """REQ-016: brief #373 answer 2 (Q-373-2: a *.md or docs/ file is never unmapped)."""
    start(repo, testing())
    change(repo, "app/billing/pay.py", "app/billing/NOTES.md", "docs/guide.md")
    found = result(repo)
    assert found.unmapped == [] and found.full is False


def test_thorough_is_always_full(repo):
    """REQ-016: brief #373 answer 2 (the thorough profile)."""
    start(repo, testing(profile="thorough"))
    change(repo, "app/billing/pay.py")
    found = result(repo)
    assert found.full is True and found.reason == "profile thorough"
    assert "regression: full (profile thorough)\n" in plan(repo).stdout


BAD = [
    ('testing = "yes"\n', "setting: testing"),
    ('[testing]\nprofile = "quick"\n', "setting: testing.profile"),
    ("[testing]\nalways_full = \"app/**\"\n", "setting: testing.always_full"),
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
    table = testing(profile="fast", always_full='["migrations/**"]') + "budget_seconds = 120\n"
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
    """REQ-016: brief #373 answer 1 (path globs)."""
    assert impact.matches(path, glob) is hit
