"""Links across areas: a change in one part runs another part's tests (SPEC-0055 rule 7).

REQ-062 AC4, brief #828, build (e). `[[testing.links]]` in `agk.toml` and the links `test_map.py
build` derives for a schema file select a level on a pull request, only ever adding tests. Invented
projects in `tmp_path` (example.com); no network, no install.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell

import impact
import prepush
import project_tests
import pytest
import test_map
from common import CheckError

HEAD = (
    'default_branch = "main"\nproject_tests = "exit 0"\ntest_dirs = ["web/tests", "api/tests"]\n'
    'test_patterns = ["test_*"]\n'
)
AREAS = """
[proof.api]
dirs = ["api/tests"]
patterns = ["test_*"]
command = "run-api {files}"
[proof.web]
dirs = ["web/tests"]
patterns = ["test_*"]
command = "run-web {files}"
cwd = "web"
[proof.web.levels.unit]
dirs = ["web/tests/unit"]
command = "unit {files}"
when = ["pr", "main"]
[proof.web.levels.contract]
dirs = ["web/tests/contract"]
command = "contract {files}"
when = ["main"]
[proof.web.levels.e2e]
dirs = ["web/tests/e2e"]
command = "whole-e2e"
when = ["nightly"]
env = ["browser"]
"""
TESTING = (
    '[testing]\nprofile = "fast"\nmap = [{ code = "web/app/**", tests = ["web/tests/unit/**"] }]\n'
)
FILES = {
    "api/models.py": "# models\n",
    "api/schema/shop.proto": 'syntax = "proto3";\n',
    "web/app/cart.py": "# cart\n",
    "web/tests/unit/test_cart.py": "# unit\n",
    "web/tests/contract/test_a.py": "# a\n",
    "web/tests/contract/test_b.py": "# b\n",
    "web/tests/e2e/test_flow.py": "# flow\n",
    "docs/api.yaml": "# api\n",
}


def link(code: str, *run: str) -> str:
    names = ", ".join(f'"{n}"' for n in run)
    return f'[[testing.links]]\ncode = ["{code}"]\nrun = [{names}]\n'


def start(repo, links: str = "", extra: str = "", files: dict | None = None) -> None:
    toml = HEAD + AREAS + TESTING + extra + links
    repo.commit({"agk.toml": toml, **FILES, **(files or {})}, "base")
    repo.branch("feature")


def change(repo, *paths: str) -> None:
    repo.commit({p: "# changed\n" for p in paths}, "change")


def found(repo) -> impact.Impact:
    return impact.impact(repo.root, repo.git("rev-parse", "main").strip(), "HEAD")


def planned(repo) -> tuple[dict, list[str]]:
    result = found(repo)
    sets, notes = prepush.regression_sets(repo.root, result, project_tests.proof_areas(repo.root))
    return {s[0]: s for s in sets}, notes


@pytest.fixture(autouse=True)
def on_a_machine(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("AGK_TEST_ENV", raising=False)


BAD = [
    ('links = "x"\n', "testing.links"),
    ("links = [1]\n", "testing.links[1]"),
    ('links = [{ code = ["a/**"], run = ["web:unit"], more = 1 }]\n', "testing.links[1]"),
    ('links = [{ code = [], run = ["web:unit"] }]\n', "testing.links[1].code"),
    ('links = [{ code = ["/secret-glob"], run = ["web:unit"] }]\n', "testing.links[1].code"),
    ('links = [{ code = ["a/**"], run = [] }]\n', "testing.links[1].run"),
    ('links = [{ code = ["a/**"], run = ["no-colon"] }]\n', "testing.links[1].run"),
    ('links = [{ code = ["a/**"], run = ["web:secret-level"] }]\n', "testing.links[1].run"),
    ('links = [{ code = ["a/**"], run = ["secret-area:unit"] }]\n', "testing.links[1].run"),
]


@pytest.mark.parametrize(("body", "setting"), BAD)
def test_a_malformed_link_is_refused_naming_the_setting(repo, body, setting):
    """REQ-062 AC4: SPEC-0055 rule 7, brief #828 answer 1."""
    repo.write("agk.toml", HEAD + AREAS + "[testing]\n" + body)
    with pytest.raises(CheckError) as refused:
        impact.testing_table(repo.root)
    assert f"setting: {setting}" in str(refused.value) and "secret" not in str(refused.value)


def test_an_empty_table_changes_nothing(repo):
    """REQ-062 AC1: brief #828 answer 1 (an empty or absent table)."""
    start(repo, extra="links = []\n")
    change(repo, "web/app/cart.py")
    assert found(repo).linked == [] and "links" not in found(repo).data()
    sets, _ = planned(repo)
    assert list(sets) == ["web:unit"]


def test_a_link_selects_a_level_off_the_pull_request_whole_when_none_is_selected(repo):
    """REQ-062 AC4: SPEC-0055 rule 7 (a level whose `when` has no `pr`, all of it)."""
    start(repo, link("api/**", "web:contract"))
    change(repo, "api/models.py")
    sets, _ = planned(repo)
    name, command, cwd, reason = sets["web:contract"]
    assert command == "contract tests/contract/test_a.py tests/contract/test_b.py"
    assert cwd == "web" and "api/models.py" in reason and "api/**" in reason


def test_a_link_runs_the_selected_tests_of_its_level(repo):
    """REQ-062 AC4: brief #828 answer 2 (selected tests of the level, when there are some)."""
    start(repo, link("api/**", "web:contract"))
    toml = (
        (repo.root / "agk.toml")
        .read_text()
        .replace('tests = ["web/tests/unit/**"]', 'tests = ["web/tests/contract/test_a.py"]')
    )
    repo.commit({"agk.toml": toml, "web/app/cart.py": "# c\n", "api/models.py": "# m\n"}, "c")
    sets, notes = planned(repo)
    assert sets["web:contract"][1] == "contract tests/contract/test_a.py"
    assert not any(n.startswith("tests: web:contract runs on") for n in notes)


def test_a_level_without_files_runs_whole_and_a_selected_level_runs_once(repo, monkeypatch):
    """REQ-062 AC4: SPEC-0055 rules 3 and 7 (no `{files}`; a link adds no second run)."""
    monkeypatch.setenv("AGK_TEST_ENV", "browser")
    start(repo, link("web/app/**", "web:e2e", "web:unit"))
    change(repo, "web/app/cart.py")
    sets, _ = planned(repo)
    assert sets["web:e2e"][1] == "whole-e2e"
    assert sets["web:unit"][1] == "unit tests/unit/test_cart.py" and len(sets) == 2


def test_a_link_to_an_area_without_levels_is_its_unit_level_and_adds_no_second_run(repo):
    """REQ-062 AC4: SPEC-0055 rule 3 (the implicit `unit` level)."""
    files = {"api/tests/test_api.py": "# api\n"}
    start(repo, link("web/app/**", "api:unit"), files=files)
    change(repo, "web/app/cart.py")
    sets, _ = planned(repo)
    assert sets["api:unit"][1] == "run-api api/tests/test_api.py"


def test_a_link_never_removes_a_test_and_holds_on_full_and_documentation(repo):
    """REQ-062 AC4: SPEC-0055 rule 7 (a link only adds, whatever the selection is)."""
    start(repo, link("docs/api.yaml", "web:contract") + link("api/**", "web:contract"))
    change(repo, "docs/api.yaml")
    sets, _ = planned(repo)
    assert list(sets) == ["web:contract"]
    toml = (repo.root / "agk.toml").read_text().replace('"fast"', '"thorough"')
    repo.commit({"agk.toml": toml, "web/app/cart.py": "# d\n"}, "full")
    sets, _ = planned(repo)
    assert list(sets) == ["full", "web:contract"]
    assert sets["web:contract"][1].count("test_") == 2


def test_an_absent_environment_is_not_run_on_a_machine(repo):
    """REQ-062 AC4: SPEC-0055 rule 7, Q-S0055-8 (on a developer's machine)."""
    start(repo, link("api/**", "web:e2e"))
    change(repo, "api/models.py")
    sets, notes = planned(repo)
    assert sets == {} and "not run: web:e2e (env browser)" in notes


def test_an_absent_environment_fails_in_ci_naming_the_setting(repo, monkeypatch):
    """REQ-062 AC4: SPEC-0055 rule 7, Q-S0055-8 (`CI`, as common.resolve_base reads it)."""
    monkeypatch.setenv("CI", "true")
    start(repo, link("api/**", "web:e2e"))
    change(repo, "api/models.py")
    sets, notes = planned(repo)
    _, command, _, reason = sets["web:e2e"]
    run = ["sh", "-c", command]
    done = subprocess.run(run, capture_output=True, text=True)  # nosec B603 - fixed argument list
    assert done.returncode != 0 and "setting: testing.links" in done.stdout + reason
    assert "browser" not in reason and "not run: web:e2e (env browser)" in notes


@pytest.mark.parametrize("mode", ["full", "selected"])
def test_the_test_step_runs_a_link_and_fails_without_its_environment(repo, mode):
    """REQ-062 AC4: SPEC-0055 rule 7 (the CI step, under either `pr_tests`)."""
    start(repo, link("api/**", "web:e2e"), f'pr_tests = "{mode}"\n')
    change(repo, "api/models.py")
    env = {"EVENT": "pull_request", "AGK_BASE": "main"}
    bad = repo.run("project_tests.py", CI="true", **env)
    assert bad.returncode == 1 and "setting: testing.links" in bad.stdout
    (repo.root / "web").mkdir(exist_ok=True)
    good = repo.run("project_tests.py", AGK_TEST_ENV="browser", **env)
    assert "web:e2e" in good.stdout and "web:e2e FAIL" in good.stdout  # `whole-e2e` is no command


def test_the_test_step_is_unchanged_without_a_link_or_on_a_push(repo):
    """REQ-062 AC1: SPEC-0055 rule 2 (with no link, as today; a link is for a pull request)."""
    start(repo, "", 'pr_tests = "full"\n')
    change(repo, "api/models.py")
    assert repo.run("project_tests.py", EVENT="pull_request", AGK_BASE="main").stdout == ""
    repo.git("checkout", "-q", "main")
    repo.commit(
        {"agk.toml": HEAD + AREAS + TESTING + 'pr_tests = "full"\n' + link("api/**", "web:e2e")}
    )
    assert repo.run("project_tests.py", EVENT="push", CI="true").returncode == 0


def test_the_plan_shows_a_linked_level(repo):
    """REQ-062 AC4: the plan shown is the plan run (test_plan.py)."""
    start(repo, link("api/**", "web:contract"))
    change(repo, "api/models.py")
    out = repo.run("test_plan.py", "--base", "main").stdout
    assert "link: web:contract (api/models.py matches code api/**)" in out
    assert "web:contract: runs 2 test files" in out


# Derived links (`test_map.py build`).

GENERATED = 'map_source = "generated"\n'
BUF = 'import "api/schema/shop.proto";\n'


def built(repo) -> str:
    assert test_map.build(repo.root) == 0
    return (repo.root / test_map.OUT).read_text(encoding="utf-8")


def derived(path: str, level: str = "web:contract") -> str:
    return f'[[testing.links]]\ncode = ["{path}"]\nrun = ["{level}"]\n'


@pytest.mark.parametrize(
    ("schema", "text", "importer", "names"),
    [
        ("api/schema/shop.proto", 'syntax = "proto3";\n', "web/app/a.proto", BUF),
        ("api/p/g/any.proto", 'syntax = "proto3";\n', "web/b.proto", 'import "g/any.proto";\n'),
        (
            "api/shop.graphql",
            "type Q { a: Int }\n",
            "web/codegen.yml",
            "schema: ../api/shop.graphql\n",
        ),
        ("api/shop.gql", "type Q { a: Int }\n", "web/app/q.ts", 'import "../../api/shop.gql";\n'),
        (
            "api/open.yaml",
            "openapi: 3.1.0\n",
            "web/package.json",
            '"gen": "gen ../api/open.yaml"\n',
        ),
        (
            "api/old.json",
            '{\n  "swagger": "2.0"\n}\n',
            "web/gen.gradle",
            'x "$rootDir/api/old.json"\n',
        ),
    ],
)
def test_a_schema_another_area_imports_or_generates_from_derives_a_link(
    repo, schema, text, importer, names
):
    """REQ-062 AC4: brief #828 answer 3 (each file kind; a link naming the `contract` level)."""
    repo.commit({"agk.toml": HEAD + AREAS + TESTING, **FILES, schema: text, importer: names})
    assert derived(schema) in built(repo)


def test_a_tree_with_no_such_file_adds_nothing_and_gives_the_same_bytes(repo):
    """REQ-062 AC4: brief #828 answer 3 (a plain YAML file, an unimported schema)."""
    files = {"web/data.yaml": "a: 1\n", "api/schema/lone.proto": 'syntax = "proto3";\n'}
    repo.commit({"agk.toml": HEAD + AREAS + TESTING, **FILES, **files})
    first = built(repo)
    assert "testing.links" not in first
    assert built(repo) == first


def test_no_link_without_a_contract_level(repo):
    """REQ-062 AC4: brief #828 answer 3 (that area's `contract` level, when it has one)."""
    toml = HEAD + AREAS.replace("levels.contract", "levels.pact") + TESTING
    repo.commit({"agk.toml": toml, **FILES, "web/app/s.proto": BUF})
    assert "testing.links" not in built(repo)


def test_no_link_within_one_area(repo):
    """REQ-062 AC4: brief #828 answer 3 (a file of another area)."""
    files = {"web/app/a.proto": 'syntax = "proto3";\n', "web/app/b.proto": 'import "a.proto";\n'}
    repo.commit({"agk.toml": HEAD + AREAS + TESTING, **FILES, **files})
    assert "testing.links" not in built(repo)


def test_declared_and_derived_links_are_a_union(repo):
    """REQ-062 AC4: SPEC-0055 rule 7, brief #828 answer 2."""
    files = {"web/app/s.proto": BUF, "web/tests/e2e/test_x.py": "# x\n"}
    start(repo, link("api/**", "web:unit"), GENERATED, files)
    change(repo, "api/schema/shop.proto")
    built(repo)
    assert [x.run for x in found(repo).linked] == ["web:contract", "web:unit"]


def test_no_built_map_adds_nothing_and_says_nothing(repo):
    """REQ-062 AC1: SPEC-0055 rule 1 (no script asks which source it has; no file, no link)."""
    start(repo, "", GENERATED, {"web/app/s.proto": BUF})
    change(repo, "api/schema/shop.proto")
    assert found(repo).linked == [] and found(repo).link_notes == []


def test_a_map_of_another_tree_adds_no_link_and_says_so(repo):
    """REQ-062 AC4: SPEC-0055 rule 5 (the first line names the tree)."""
    start(repo, "", GENERATED, {"web/app/s.proto": BUF})
    built(repo)
    change(repo, "api/schema/shop.proto")
    result = found(repo)
    assert result.linked == [] and "setting: testing.links" in " ".join(result.link_notes)
