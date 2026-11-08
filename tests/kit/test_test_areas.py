"""Areas with levels, their environment and the map's source (SPEC-0055 rules 1 to 4, brief #788).

`[testing] map_source` says where the map comes from, and a repository that sets it sees one
`tests: map <source>` line first in every selection. A `[proof]` area may hold levels, each with its
own command, its events (`when`) and the environment it needs (`AGK_TEST_ENV`); an area without
levels reads as it always did, and with no new key nothing a command prints or runs changes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import common
import impact
import pytest
from common import CheckError
from test_prepush_regression import MAP, RUN_LINE, prepush, project, ran
from test_prepush_regression import toml as old_toml

ROOT = Path(__file__).resolve().parents[2]
SPECS = sorted((ROOT / "docs" / "specs").glob("0055-*.md"))
OWN_REPOSITORY = pytest.mark.skipif(not SPECS, reason="reads files only this repository has")
BASE = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
AREA = '[proof.web]\ndirs = ["tests"]\npatterns = ["test_*.py"]\ncommand = "echo area {files}"\n'
UNIT = '[proof.web.levels.unit]\ncommand = "echo unit {files}"\nwhen = ["pr", "main"]\n'
ALL_EVENTS = ["pr", "main", "nightly", "release"]


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("outside")


def areas_of(tmp_path: Path, text: str) -> list[dict] | None:
    (tmp_path / "agk.toml").write_text(BASE + text, encoding="utf-8")
    return common.proof_areas(tmp_path)


def refusal(tmp_path: Path, text: str) -> str:
    with pytest.raises(CheckError) as caught:
        areas_of(tmp_path, text)
    return str(caught.value)


def level(name: str, extra: str, command: str = "echo {files}") -> str:
    return f"[proof.web.levels.{name}]\ncommand = '{command}'\n{extra}\n"


def repo_toml(outside: Path, levels: str, testing: str | None = 'profile = "fast"\n' + MAP) -> str:
    log = outside / "ran.log"
    text = (
        BASE + f"project_tests = 'echo full >> {log}'\nlock_dir = '{outside / 'locks'}'\n"
        '[proof.web]\ndirs = ["tests"]\npatterns = ["test_*.py"]\n'
        f"command = 'echo area {{files}} >> {log}'\n" + levels.replace("LOG", str(log))
    )
    return text + ("[testing]\n" + testing if testing is not None else "")


UNIT_LOG = "[proof.web.levels.unit]\ncommand = 'echo unit {files} >> LOG'\nwhen = ['pr', 'main']\n"
E2E_LOG = (
    "[proof.web.levels.e2e]\ncommand = 'echo e2e {files} >> LOG'\nwhen = ['pr', 'main']\n"
    "env = ['browser']\ndirs = ['tests/billing']\n"
)


# --- rule 1: the map's source ---------------------------------------------------------------------


@pytest.mark.parametrize("source", ["curated", "generated"])
def test_the_selection_prints_the_map_source_first(repo, outside, source):
    """REQ-062 AC1: SPEC-0055 rule 1 (`tests: map <source>` first, in the plan and in prepush)."""
    testing = f'profile = "fast"\nmap_source = "{source}"\n' + MAP
    project(repo, old_toml(outside, testing=testing))
    plan = repo.run("test_plan.py", "--base", "main")
    assert plan.returncode == 0, plan.stdout + plan.stderr
    lines = plan.stdout.splitlines()
    at = lines.index(f"tests: map {source}")
    assert lines[at + 1].startswith("regression:")
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"tests: map {source}\n" in proc.stdout


def test_the_map_line_also_leads_a_selection_of_nothing(repo, outside):
    """REQ-062 AC1: SPEC-0055 rule 1 (the line comes before `nothing selected`)."""
    testing = 'profile = "fast"\nmap_source = "curated"\n'
    project(repo, old_toml(outside, testing=testing), {"docs/a.md": "x\n"})
    out = prepush(repo, outside).stdout.splitlines()
    assert out.index("tests: map curated") + 1 == out.index(
        "tests: regression: nothing selected (only documentation changed)"
    )


def test_the_json_names_the_source_only_when_it_is_set(repo, outside):
    """REQ-062 AC1: SPEC-0055 rules 1 and 2 (the key appears only in a repository that sets it)."""
    project(repo, old_toml(outside))
    plain = json.loads(repo.run("test_plan.py", "--json", "--base", "main").stdout)
    assert "map_source" not in plain["regression"]
    repo.commit(
        {"agk.toml": old_toml(outside, testing='map_source = "generated"\n' + MAP)}, "source"
    )
    doc = json.loads(repo.run("test_plan.py", "--json", "--base", "main").stdout)
    assert doc["regression"]["map_source"] == "generated"


@pytest.mark.parametrize("value", ['"learned"', "1", "true", '["curated"]'])
def test_a_malformed_map_source_is_refused_naming_the_setting(tmp_path, value):
    """REQ-062 AC1: SPEC-0055 rule 2 (the setting is named, never the value)."""
    (tmp_path / "agk.toml").write_text(BASE + f"[testing]\nmap_source = {value}\n")
    with pytest.raises(CheckError) as caught:
        impact.testing_table(tmp_path)
    assert "setting: testing.map_source" in str(caught.value)
    assert "learned" not in str(caught.value)


@OWN_REPOSITORY
def test_this_repository_sets_curated_and_keeps_its_entries():
    """REQ-062 AC1: SPEC-0055 rule 1 (AGK itself is `curated`, by data and not by a code path)."""
    table = impact.testing_table(ROOT)
    assert table is not None and table["map_source"] == "curated"
    assert len(table["map"]) > 0


@OWN_REPOSITORY
def test_the_guide_opens_with_the_two_sentences():
    """REQ-062 AC1: SPEC-0055 rule 1 (the third place the difference is remembered)."""
    spec = SPECS[0].read_text(encoding="utf-8")
    start = spec.index("AGK itself has one area")
    end = spec.index("depend on the environment.", start) + len("depend on the environment.")
    guide = (ROOT / "docs" / "guides" / "testing.md").read_text(encoding="utf-8")
    opening = guide.split("\n\n")[1].replace("\n", " ")
    assert opening == spec[start:end]


def test_no_script_asks_whether_it_runs_in_the_kit():
    """REQ-062 AC1: SPEC-0055 rule 1 (one mechanism: the source is only read and printed)."""
    used = [
        path.name
        for path in (ROOT / "scripts" / "agk").glob("*.py")
        if re.search(r"map_source\s*(==|!=|in\b)", path.read_text(encoding="utf-8"))
    ]
    assert used == []


# --- rule 2: nothing is lowered -------------------------------------------------------------------


def test_with_no_new_key_prepush_runs_and_prints_what_it_did(repo, outside):
    """REQ-062 AC1: SPEC-0055 rule 2 (no new key: the same commands, and no new line)."""
    project(repo, old_toml(outside))
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["kit tests/billing/test_pay.py"]
    assert "tests: map" not in proc.stdout
    assert "prepush: all steps passed" in proc.stdout


def test_with_no_new_key_the_plan_is_unchanged(repo, outside):
    """REQ-062 AC1: SPEC-0055 rule 2 (no new key in the plan's JSON or text)."""
    project(repo, old_toml(outside), {"src/billing/pay.py": "c\n", "tests/test_new.py": "# n\n"})
    plan = repo.run("test_plan.py", "--json", "--base", "main")
    doc = json.loads(plan.stdout)
    assert set(doc) == {
        "regression", "base", "head", "proof_table", "runs", "nothing_to_run",
        "not_run_by_proof", "deleted", "project_tests",
    }  # fmt: skip
    assert [r["name"] for r in doc["runs"]] == ["kit"]
    text = repo.run("test_plan.py", "--base", "main").stdout
    assert "tests: map" not in text and "level" not in text


def test_a_level_never_reaches_the_full_selection(repo, outside):
    """REQ-062 AC1: SPEC-0055 rule 2 (a full selection stays `project_tests`, once)."""
    change = {"src/billing/pay.py": "c\n", "src/other.py": "c\n"}
    text = repo_toml(outside, UNIT_LOG, 'profile = "balanced"\n' + MAP)
    project(repo, text, change)
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full"]


# --- rule 3: levels -------------------------------------------------------------------------------


def test_an_area_without_levels_is_one_implicit_unit_level(tmp_path):
    """REQ-062 AC2: SPEC-0055 rule 3 (today's areas read as they do)."""
    areas = areas_of(tmp_path, AREA)
    assert areas is not None and "levels" not in areas[0]
    found = common.area_levels(areas[0])
    assert [(x["name"], x["when"], x["env"]) for x in found] == [("unit", ALL_EVENTS, [])]
    assert found[0]["command"] == "echo area {files}" and found[0]["cwd"] == "."
    assert found[0]["dirs"] == ["tests"] and found[0]["patterns"] == ["test_*.py"]


def test_a_level_reads_its_keys_and_defaults_to_the_area(tmp_path):
    """REQ-062 AC2: SPEC-0055 rule 3 (every key of a level, and the area's defaults)."""
    extra = level(
        "smoke-1",
        'when = ["main", "nightly", "release", "pr"]\nenv = ["browser"]\ndirs = ["tests/a"]\n'
        'patterns = ["t_*.py"]\ncwd = "tests"\njunit = "out/*.xml"\nrerun = "run {id}"',
        "run-all",
    )
    areas = areas_of(tmp_path, AREA + UNIT + extra)
    assert areas is not None
    unit, smoke = areas[0]["levels"]
    assert unit["dirs"] == ["tests"] and unit["cwd"] == "." and unit["env"] == []
    assert unit["junit"] is None and unit["rerun"] is None
    assert smoke == {
        "name": "smoke-1",
        "command": "run-all",
        "when": ["main", "nightly", "release", "pr"],
        "env": ["browser"],
        "dirs": ["tests/a"],
        "patterns": ["t_*.py"],
        "cwd": "tests",
        "junit": "out/*.xml",
        "rerun": "run {id}",
    }


@pytest.mark.parametrize(
    ("body", "setting"),
    [
        ('[proof.web.levels]\n"a b" = { command = "x", when = ["main"] }\n', "proof.web.levels"),
        ("[proof.web.levels.u]\nwhen = ['main']\n", "proof.web.levels.u.command"),
        ("[proof.web.levels.u]\ncommand = '  '\nwhen = ['main']\n", "proof.web.levels.u.command"),
        ("[proof.web.levels.u]\ncommand = 'x'\n", "proof.web.levels.u.when"),
        ("[proof.web.levels.u]\ncommand = 'x'\nwhen = []\n", "proof.web.levels.u.when"),
        ("[proof.web.levels.u]\ncommand = 'x'\nwhen = ['soon']\n", "proof.web.levels.u.when"),
        ("[proof.web.levels.u]\ncommand = 'x'\nwhen = ['pr']\n", "proof.web.levels.u.when"),
        ("[proof.web.levels.u]\ncommand = 'x'\nwhen = ['pr', 'pr']\n", "proof.web.levels.u.when"),
        (
            "[proof.web.levels.u]\ncommand = 'x'\nwhen = ['main']\nenv = 'browser'\n",
            "proof.web.levels.u.env",
        ),
        (
            "[proof.web.levels.u]\ncommand = 'x'\nwhen = ['main']\nenv = ['a,b']\n",
            "proof.web.levels.u.env",
        ),
        (
            "[proof.web.levels.u]\ncommand = 'x'\nwhen = ['main']\ndirs = []\n",
            "proof.web.levels.u.dirs",
        ),
        (
            "[proof.web.levels.u]\ncommand = 'x'\nwhen = ['main']\npatterns = 'p'\n",
            "proof.web.levels.u.patterns",
        ),
        (
            "[proof.web.levels.u]\ncommand = 'x'\nwhen = ['main']\ncwd = '../up'\n",
            "proof.web.levels.u.cwd",
        ),
        (
            "[proof.web.levels.u]\ncommand = 'x'\nwhen = ['main']\njunit = '/abs.xml'\n",
            "proof.web.levels.u.junit",
        ),
        (
            "[proof.web.levels.u]\ncommand = 'x'\nwhen = ['main']\nrerun = 'no id here'\n",
            "proof.web.levels.u.rerun",
        ),
        ("[proof.web.levels.u]\ncommand = 'x'\nwhen = ['main']\nextra = 1\n", "proof.web.levels.u"),
    ],
)
def test_a_malformed_level_is_refused_naming_the_setting(tmp_path, body, setting):
    """REQ-062 AC2: SPEC-0055 rules 2 and 3 (each bad key, and `when` of only `pr`)."""
    message = refusal(tmp_path, AREA + body)
    assert f"(setting: {setting})" in message
    assert "soon" not in message and "browser" not in message


def test_empty_levels_are_refused(tmp_path):
    """REQ-062 AC2: SPEC-0055 rule 3 (`levels` is a table of one or more levels)."""
    assert "(setting: proof.web.levels)" in refusal(tmp_path, AREA + "[proof.web.levels]\n")


def test_the_areas_own_keys_stay_required(tmp_path):
    """REQ-062 AC2: SPEC-0055 rule 3 (a level does not replace the area's command)."""
    text = '[proof.web]\ndirs = ["tests"]\npatterns = ["test_*.py"]\n' + UNIT
    assert "(setting: proof.web.command)" in refusal(tmp_path, text)


def web(levels: list[dict]) -> dict:
    filled = [
        {"dirs": ["tests"], "patterns": ["test_*.py"], "cwd": ".", "env": [], **item}
        for item in levels
    ]
    return {"name": "web", "dirs": ["tests"], "patterns": ["test_*.py"], "levels": filled}


def test_a_file_belongs_to_the_first_level_that_matches():
    """REQ-062 AC2: SPEC-0055 rule 3 (first match, in table order)."""
    area = web(
        [
            {"name": "e2e", "when": ["pr", "main"], "dirs": ["tests/e2e"]},
            {"name": "unit", "when": ["pr", "main"]},
        ]
    )
    groups, notes = impact.level_groups(area, ["tests/e2e/test_a.py", "tests/test_b.py"], "pr", "")
    assert [(g["level"]["name"], g["files"]) for g in groups] == [
        ("e2e", ["tests/e2e/test_a.py"]),
        ("unit", ["tests/test_b.py"]),
    ]
    assert groups[0]["label"] == "web:e2e" and notes == []


@pytest.mark.parametrize("event", ALL_EVENTS)
def test_each_event_runs_the_levels_that_name_it(event):
    """REQ-062 AC2: SPEC-0055 rule 3 (each `when`)."""
    area = web(
        [
            {"name": "a", "when": [event, "main"], "dirs": ["tests/a"]},
            {"name": "b", "when": [e for e in ALL_EVENTS if e != event], "dirs": ["tests/b"]},
        ]
    )
    groups, _ = impact.level_groups(area, ["tests/a/test_1.py", "tests/b/test_2.py"], event, "")
    assert [g["level"]["name"] for g in groups] == ["a"]


def test_a_level_not_on_this_event_says_so_and_is_not_counted_not_run():
    """REQ-062 AC2: SPEC-0055 rule 3 (a level at another time is a timetable, not a miss)."""
    area = web([{"name": "slow", "when": ["main", "nightly"]}])
    groups, notes = impact.level_groups(area, ["tests/test_a.py"], "pr", "")
    assert groups == []
    assert notes == ["tests: web:slow runs on main, nightly"]
    assert not any("not run" in n for n in notes)


def test_a_file_in_no_level_raises_naming_the_setting():
    """REQ-062 AC2: SPEC-0055 rule 3 (never left out)."""
    area = web([{"name": "e2e", "when": ["main"], "dirs": ["tests/e2e"]}])
    with pytest.raises(CheckError) as caught:
        impact.level_groups(area, ["tests/test_b.py"], "pr", "")
    assert "(setting: proof.web.levels)" in str(caught.value)
    assert "test_b" not in str(caught.value)


def test_the_plan_refuses_a_test_file_in_no_level(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 3 and Q-S0055-3 (any test file of the area, even unchanged)."""
    only_e2e = "[proof.web.levels.e2e]\ncommand = 'x'\nwhen = ['main']\ndirs = ['tests/e2e']\n"
    project(repo, repo_toml(outside, only_e2e), {"src/other.py": "c\n"})
    plan = repo.run("test_plan.py", "--base", "main")
    assert plan.returncode == 2
    assert "(setting: proof.web.levels)" in plan.stdout
    assert "test_pay" not in plan.stdout
    proc = prepush(repo, outside)
    assert proc.returncode != 0 and "(setting: proof.web.levels)" in proc.stdout


def test_the_plan_shows_each_level_run_and_its_command(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 3 (a level's own command, on `pr`)."""
    project(repo, repo_toml(outside, UNIT_LOG), {"tests/test_new.py": "# n\n"})
    doc = json.loads(repo.run("test_plan.py", "--json", "--base", "main").stdout)
    assert doc["runs"][0]["name"] == "web"  # proof's own plan is not rewritten
    assert [(r["name"], r["files"]) for r in doc["level_runs"]] == [
        ("web:unit", ["tests/test_new.py"])
    ]
    assert "echo unit" in doc["level_runs"][0]["command"]
    text = repo.run("test_plan.py", "--base", "main").stdout
    assert "web:unit: runs 1 test file" in text


def test_prepush_runs_a_level_command_for_own_and_selected_tests(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 3 (`pr` is prepush's selection, through the level's command)."""
    change = {"src/billing/pay.py": "c\n", "tests/test_new.py": "# n\n"}
    project(repo, repo_toml(outside, UNIT_LOG), change)
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["unit tests/test_new.py", "unit tests/billing/test_pay.py"]
    assert [r[0] for r in RUN_LINE.findall(proc.stdout)] == ["web:unit", "web:unit"]


def test_a_level_without_files_placeholder_runs_whole(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 3 (a command with no `{files}` runs the whole level)."""
    whole = "[proof.web.levels.unit]\ncommand = 'echo whole >> LOG'\nwhen = ['pr', 'main']\n"
    project(repo, repo_toml(outside, whole))
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["whole"]


def test_a_level_runs_in_its_own_folder(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 3 (`{files}` relative to the level's `cwd`)."""
    in_tests = (
        "[proof.web.levels.unit]\ncommand = 'echo unit {files} >> LOG'\nwhen = ['pr', 'main']\n"
        "cwd = 'tests'\n"
    )
    project(repo, repo_toml(outside, in_tests))
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["unit billing/test_pay.py"]


# --- rule 4: the environment ----------------------------------------------------------------------


def test_a_level_whose_environment_is_absent_is_not_run():
    """REQ-062 AC2: SPEC-0055 rule 4 (the exact line; the first absent name)."""
    area = web([{"name": "e2e", "when": ["pr", "main"], "env": ["browser", "database"]}])
    groups, notes = impact.level_groups(area, ["tests/test_a.py"], "pr", "database")
    assert groups == [] and notes == ["not run: web:e2e (env browser)"]


def test_a_level_whose_environment_is_present_runs():
    """REQ-062 AC2: SPEC-0055 rule 4 (a comma-separated list, spaces forgiven)."""
    area = web([{"name": "e2e", "when": ["pr", "main"], "env": ["browser", "macos"]}])
    groups, notes = impact.level_groups(area, ["tests/test_a.py"], "pr", " macos, browser ")
    assert [g["label"] for g in groups] == ["web:e2e"] and notes == []


def test_a_level_with_no_environment_always_runs():
    """REQ-062 AC2: SPEC-0055 rule 4 (an empty `env` needs nothing)."""
    area = web([{"name": "unit", "when": ["pr", "main"]}])
    groups, notes = impact.level_groups(area, ["tests/test_a.py"], "pr", "")
    assert len(groups) == 1 and notes == []


def env_project(repo, outside: Path, testing: str | None = 'profile = "fast"\n' + MAP) -> None:
    project(repo, repo_toml(outside, E2E_LOG + UNIT_LOG, testing))


def test_prepush_prints_not_run_and_never_counts_it_passed(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 4 (absent: `not run`, and the end line says so)."""
    env_project(repo, outside)
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "not run: web:e2e (env browser)\n" in proc.stdout
    assert ran(outside) == []
    assert "prepush: passed; not run: tests" in proc.stdout
    assert "prepush: all steps passed" not in proc.stdout


def test_prepush_runs_the_level_when_the_environment_is_present(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 4 (`AGK_TEST_ENV` names it: the level runs)."""
    env_project(repo, outside)
    proc = prepush(repo, outside, AGK_TEST_ENV="browser")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["e2e tests/billing/test_pay.py"]
    assert "prepush: all steps passed" in proc.stdout


def test_the_plan_lists_a_missing_environment(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 4 (the plan says what will not run, in text and JSON)."""
    project(repo, repo_toml(outside, E2E_LOG + UNIT_LOG), {"tests/billing/test_x.py": "# n\n"})
    assert "not run: web:e2e (env browser)" in repo.run("test_plan.py", "--base", "main").stdout
    doc = json.loads(repo.run("test_plan.py", "--json", "--base", "main").stdout)
    assert doc["level_runs"] == []
    assert doc["level_notes"] == ["not run: web:e2e (env browser)"]


def test_an_env_level_takes_the_heavy_lock_without_a_testing_table(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 4 (a level with `env` runs under the heavy-step lock)."""
    held = outside / "locks" / "agk-lock-heavy"
    probe = (
        "[proof.web.levels.e2e]\n"
        f"command = 'test -e {held} && echo locked >> LOG'\n"
        "when = ['pr', 'main']\nenv = ['browser']\n"
    )
    project(repo, repo_toml(outside, probe, None), {"tests/test_new.py": "# n\n"})
    proc = prepush(repo, outside, AGK_TEST_ENV="browser")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["locked"]
    assert not held.exists()


def test_a_level_without_env_takes_no_new_lock_without_a_testing_table(repo, outside):
    """REQ-062 AC2: SPEC-0055 rule 2 (no `env`, no `[testing]`: no lock, as today)."""
    project(repo, repo_toml(outside, UNIT_LOG, None), {"tests/test_new.py": "# n\n"})
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["unit tests/test_new.py"]
    assert "lock heavy" not in proc.stdout


# --- the spec itself ------------------------------------------------------------------------------


@OWN_REPOSITORY
def test_every_rule_states_the_four_places():
    """REQ-062 AC1: SPEC-0055 Tests (rules 1 to 14 state AGK itself, GitHub, local and personal)."""
    text = SPECS[0].read_text(encoding="utf-8")
    rules = text[text.index("## Rules") : text.index("## Tests")]
    parts = re.split(r"^(\d+)\. ", rules, flags=re.M)
    found = {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    for number in range(1, 15):
        for place in ("AGK itself:", "Project, GitHub:", "Project, local:", "Project, personal:"):
            assert place in found[number], (number, place)
