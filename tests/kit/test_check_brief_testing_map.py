"""A brief names agk.toml in Touches when its build needs a testing map change (brief #1856).

Rule 4c of `check_brief.brief_result`: a new kit script that no `[[testing.map]]` entry or
`always_full` covers (answer 1), a stated whole test (answer 2) or a test outside the map entry of
a code path the brief touches (answer 3), while `Touches:` does not name `agk.toml`, is warned, and
answers 1 and 2 fail for a brief filed on or after `[flow] brief_study_fails_from`. In a project
(no `kit/agk-kit.mk`) a new file of a folder the curated map covers file by file is warned only
(answer 4); a Reserved line whose path classes leave `agk.toml` out is warned (answer 5). Each case
is a stub root in `tmp_path`. Invented data only (example.com); no network. REQ-037.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import check_brief  # noqa: E402
import plan_intake  # noqa: E402
import steward_owner  # noqa: E402
from common import CheckError  # noqa: E402
from test_check_brief_study import STUDIED, tree  # noqa: E402

DAY = "2026-12-14"
BEFORE, AFTER = "2026-12-13", "2026-12-15"
M1 = (
    "rule 4c: Adds names a new script of the class scripts/agk/ that no [[testing.map]] entry or "
    "always_full covers, and Touches does not name agk.toml (setting: testing.map)"
)
M2 = (
    "rule 4c: line {} adds a whole test and Touches does not name agk.toml "
    "(setting: testing.whole_tests)"
)
M2C = (
    "rule 4c: an Adds test file of the class {} stands beside an answer **The class stays "
    "closed.**; a whole test joins testing.whole_tests in agk.toml, which Touches does not name"
)
M3 = (
    "rule 4c: a test file of the class {} is not among the tests of the [[testing.map]] entry of "
    "a code path Touches names; a test that names that code joins the entry in agk.toml, which "
    "Touches does not name (setting: testing.map)"
)
M4 = (
    "rule 4c: Adds names a new file of the class {} that no [[testing.map]] entry or always_full "
    "covers, and Touches does not name agk.toml (setting: testing.map)"
)
M5 = "rule 4b: Touches names agk.toml and the Reserved line's path classes leave it out"
TOUCHES = "Touches: scripts/agk/tool.py, docs/x.md\n"
KIT_TESTING = (
    '[testing]\nalways_full = ["scripts/agk/full_*.py"]\n'
    'whole_tests = ["tests/kit/test_whole.py"]\n'
    '[[testing.map]]\ncode = "scripts/agk/tool.py"\ntests = ["tests/kit/test_tool.py"]\n'
    '[[testing.map]]\ncode = "scripts/agk/old_*.py"\ntests = ["tests/kit/test_old.py"]\n'
)
PROJECT_TESTING = (
    '[testing]\nprofile = "{profile}"\n{source}'
    '[[testing.map]]\ncode = "src/app/a.py"\ntests = ["tests/test_a.py"]\n'
)


def root_of(
    tmp_path: Path, testing: str | None = KIT_TESTING, day: str | None = DAY, kit: bool = True
) -> Path:
    root = tree(tmp_path)
    flow = f'[flow]\nbrief_study_fails_from = "{day}"\n' if day else ""
    (root / "agk.toml").write_text(flow + (testing or ""), encoding="utf-8")
    (root / "config").mkdir()
    (root / "config" / "protected-paths.txt").write_text("agk.toml\nscripts/agk/\n", "utf-8")
    (root / "config" / "neutrality.txt").write_text("", "utf-8")
    for rel in ("tests/kit/test_whole.py", "tests/kit/test_tool.py", "src/app/a.py",
                "src/other/x.py", "scripts/agk/gates/old.py"):  # fmt: skip
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("x = 1\n", encoding="utf-8")
    if kit:
        (root / "kit").mkdir()
        (root / "kit" / "agk-kit.mk").write_text("# the kit\n", encoding="utf-8")
    return root


def body(adds: str, touches: str = "", answer: str = "", reserved: str = "") -> str:
    entries = ", ".join(x for x in ("scripts/agk/tool.py, docs/x.md", touches, adds) if x)
    text = STUDIED.replace(TOUCHES, f"Touches: {entries}\nAdds: {adds or 'none'}\n{reserved}")
    return text.replace("2. two\n", f"2. two\n3. {answer}\n") if answer else text


def result(root: Path, text: str, today: str = BEFORE, filed: object = None):
    return check_brief.brief_result(text, root, today=today, filed=filed)


def four_c(warnings: list[str]) -> list[str]:
    return [w for w in warnings if w.startswith(("rule 4c", M5))]


# --- answer 1: a new kit script the map must cover ------------------------------------------------


def test_req037_a_new_unmapped_kit_script_warns_before_the_day(tmp_path):
    """REQ-037: answer 1 (a warning for a brief filed before the day)."""
    failures, warnings = result(root_of(tmp_path), body("scripts/agk/new_probe.py"))
    assert failures == [] and four_c(warnings) == [M1]


@pytest.mark.parametrize(
    ("today", "filed"),
    [(DAY, None), (AFTER, None), (BEFORE, f"{DAY}T00:00:00Z"), (AFTER, f"{AFTER}T09:00:00Z")],
)
def test_req037_a_new_unmapped_kit_script_fails_from_the_day(tmp_path, today, filed):
    """REQ-037: answer 1 (a failure on and after the day, by created_at, else today)."""
    failures, _ = result(root_of(tmp_path), body("scripts/agk/new_probe.py"), today, filed)
    assert failures == [M1]
    _, warned = result(root_of(tmp_path / "w"), body("scripts/agk/new_probe.py"), AFTER,
                       f"{BEFORE}T23:59:59Z")  # fmt: skip
    assert four_c(warned) == [M1]


@pytest.mark.parametrize("glob", ["agk.toml", "*.toml", "agk.*", "**/agk.toml", "*"])
def test_req037_touches_that_name_agk_toml_give_no_line(tmp_path, glob):
    """REQ-037: answers 1 and 7 (a Touches glob that names agk.toml)."""
    failures, warnings = result(root_of(tmp_path), body("scripts/agk/new_probe.py", glob), AFTER)
    assert failures == [] and four_c(warnings) == []


def test_req037_a_glob_beside_agk_toml_does_not_name_it(tmp_path):
    """REQ-037: answer 7 (`config/*.toml` does not name agk.toml)."""
    failures, _ = result(root_of(tmp_path), body("scripts/agk/new_probe.py", "config/*.toml"), DAY)
    assert failures == [M1]


@pytest.mark.parametrize(
    "adds", ["scripts/agk/old_probe.py", "scripts/agk/full_probe.py", "", "docs/new.md",
             "scripts/agk/gates/new_gate.py"],
    ids=["map-glob", "always-full", "adds-none", "not-a-script", "subfolder"],
)  # fmt: skip
def test_req037_a_covered_script_or_no_new_script_gives_no_line(tmp_path, adds):
    """REQ-037: answers 1, 7 and 8 (covered, always_full, `Adds: none`, a subfolder script)."""
    failures, warnings = result(root_of(tmp_path), body(adds), AFTER)
    assert failures == [] and four_c(warnings) == []


@pytest.mark.parametrize("source", ['map_source = "generated"\n', 'profile = "thorough"\n'])
def test_req037_the_kit_reads_its_curated_map_under_every_source_and_profile(tmp_path, source):
    """REQ-037: answer 7 (in the kit answer 1 still applies for `generated`)."""
    root = root_of(tmp_path, KIT_TESTING.replace("[testing]\n", "[testing]\n" + source))
    assert result(root, body("scripts/agk/new_probe.py"), AFTER)[0] == [M1]


def test_req037_no_testing_table_gives_no_line(tmp_path):
    """REQ-037: answer 7 (`[testing]` absent: nothing maps a file)."""
    failures, warnings = result(root_of(tmp_path, None), body("scripts/agk/new_probe.py"), AFTER)
    assert failures == [] and four_c(warnings) == []


def test_req037_a_bad_testing_table_is_refused_naming_its_setting(tmp_path):
    """REQ-037: answer 7 (refused by `impact.testing_table`, as today)."""
    root = root_of(tmp_path, '[testing]\nprofile = "slow"\n')
    with pytest.raises(CheckError, match=r"\(setting: testing.profile\)"):
        result(root, body("scripts/agk/new_probe.py"), AFTER)


def test_req037_unset_day_only_warns(tmp_path):
    """REQ-037: answer 7 (`brief_study_fails_from` unset: every rule 4c line warns)."""
    root = root_of(tmp_path, day=None)
    failures, warnings = result(root, body("scripts/agk/new_probe.py"), "2999-01-01")
    assert failures == [] and four_c(warnings) == [M1]


# --- answer 2: a whole test -----------------------------------------------------------------------


def stated(text: str) -> int:
    return next(i for i, x in enumerate(text.splitlines(), 1) if "Whole test" in x)


def test_req037_a_stated_whole_test_fails_from_the_day_naming_the_line(tmp_path):
    """REQ-037: answer 2 (a body line naming the test with whole_tests)."""
    text = body("tests/kit/test_new_all.py", answer="Whole test: test_new_all.py joins the list.")
    assert result(root_of(tmp_path), text, AFTER)[0] == [M2.format(stated(text))]
    joins = M3.format("tests/kit/")  # the stub also touches a mapped script (answer 3)
    assert four_c(result(root_of(tmp_path / "b"), text)[1]) == [M2.format(stated(text)), joins]
    unset = KIT_TESTING.replace('whole_tests = ["tests/kit/test_whole.py"]\n', "")
    without = root_of(tmp_path / "c", unset)
    assert four_c(result(without, text, AFTER)[1]) == [joins]


def test_req037_an_adds_test_beside_a_closed_class_answer_warns(tmp_path):
    """REQ-037: answer 2 (beside `**The class stays closed.**`: a warning, never a failure)."""
    text = body("tests/kit/test_new_all.py", answer="**The class stays closed.** Every later one.")
    failures, warnings = result(root_of(tmp_path), text, AFTER)
    assert failures == [] and four_c(warnings) == [
        M2C.format("tests/kit/"),
        M3.format("tests/kit/"),
    ]


# --- answer 3: a test that joins a map entry ------------------------------------------------------


def test_req037_a_test_outside_the_touched_entry_warns_once(tmp_path):
    """REQ-037: answer 3 (one warning per brief naming the folder classes, never a failure)."""
    text = body("tests/kit/test_tool_more.py, tests/kit_dev/test_tool_dev.py")
    failures, warnings = result(root_of(tmp_path), text, AFTER)
    assert failures == [] and four_c(warnings) == [M3.format("tests/kit/, tests/kit_dev/")]
    listed = KIT_TESTING.replace('["tests/kit/test_tool.py"]', '["tests/kit/test_tool*.py"]')
    _, quiet = result(root_of(tmp_path / "b", listed), body("tests/kit/test_tool_more.py"), AFTER)
    assert four_c(quiet) == []


# --- answer 4: a project's own map ----------------------------------------------------------------


def project(tmp_path: Path, profile: str = "balanced", source: str = "") -> Path:
    return root_of(tmp_path, PROJECT_TESTING.format(profile=profile, source=source), kit=False)


@pytest.mark.parametrize("profile", ["balanced", "fast"])
def test_req037_a_project_folder_mapped_file_by_file_only_warns(tmp_path, profile):
    """REQ-037: answer 4 (a warning only, on any day)."""
    failures, warnings = result(project(tmp_path, profile), body("src/app/b.py"), AFTER)
    assert failures == [] and four_c(warnings) == [M4.format("src/app/")]
    _, kit_like = result(project(tmp_path / "k"), body("scripts/agk/new_probe.py"), AFTER)
    assert four_c(kit_like) == []  # the project maps no other file of scripts/agk/


@pytest.mark.parametrize(
    ("profile", "source", "adds"),
    [("balanced", 'map_source = "generated"\n', "src/app/b.py"), ("thorough", "", "src/app/b.py"),
     ("balanced", "", "src/other/c.py"), ("balanced", 'map_source = "curated"\n', "src/app/a2.py")],
    ids=["generated", "thorough", "unmapped-folder", "curated"],
)  # fmt: skip
def test_req037_a_project_is_silent_outside_a_curated_folder(tmp_path, profile, source, adds):
    """REQ-037: answer 4 (silent for `generated`, `thorough` or an unmapped folder)."""
    _, warnings = result(project(tmp_path, profile, source), body(adds), AFTER)
    assert four_c(warnings) == ([M4.format("src/app/")] if adds.endswith("a2.py") else [])


# --- answer 5: the Reserved line names the class --------------------------------------------------


def test_req037_a_reserved_line_without_agk_toml_warns(tmp_path):
    """REQ-037: answer 5 (rule 4b's new line; no line when the classes name agk.toml)."""
    leaves = "Reserved: ADR-0999 (names the path classes scripts/agk/ and tests/kit/)\n"
    names = "Reserved: ADR-0999 (names the path classes scripts/agk/ and agk.toml)\n"
    root = root_of(tmp_path)
    _, warnings = result(root, body("scripts/agk/new_probe.py", "agk.toml", reserved=leaves))
    assert four_c(warnings) == [M5]
    _, quiet = result(root, body("scripts/agk/new_probe.py", "agk.toml", reserved=names))
    assert four_c(quiet) == []


# --- answer 6: one reading for every writer -------------------------------------------------------


def test_req037_the_cli_prints_the_line_before_ok_and_no_brief_value(tmp_path):
    """REQ-037: answers 6 and 9 (`warning: rule 4c: ...` before `ok brief`; no brief path)."""
    root = root_of(tmp_path, day="2999-01-01")
    (tmp_path / "brief.md").write_text(body("scripts/agk/new_probe.py"), encoding="utf-8")
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "check_brief.py"), str(tmp_path / "brief.md"), "--root",
         str(root)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert out.returncode == 0, out.stdout + out.stderr
    lines = out.stdout.splitlines()
    assert lines.index(f"warning: {M1}") < lines.index("ok brief")
    assert "new_probe" not in out.stdout


def test_req037_every_writer_refuses_or_warns_alike(tmp_path):
    """REQ-037: answer 6 (the event, the steward and plan publish read the same lines)."""
    root, text = root_of(tmp_path), body("scripts/agk/new_probe.py")
    issue = {"number": 9, "body": text, "labels": [{"name": "agk-brief"}]}
    failed = check_brief.event_result({"action": "opened", "issue": {**issue,
        "created_at": f"{AFTER}T00:00:00Z"}}, root, None, today=AFTER)  # fmt: skip
    assert failed["action"] == "fail" and failed["problems"] == [M1]
    passed = check_brief.event_result({"action": "opened", "issue": {**issue,
        "created_at": f"{BEFORE}T00:00:00Z"}}, root, None, today=AFTER)  # fmt: skip
    assert passed["action"] == "pass" and M1 in passed["warnings"]
    early = root_of(tmp_path / "early", day="2999-01-01")
    warned: list[str] = []
    assert steward_owner.brief_refusal(early, text, 9, warned) is None
    assert f"warning: {M1}" in warned
    refusal = steward_owner.brief_refusal(root_of(tmp_path / "late", day="2000-01-01"), text, 9)
    assert refusal is not None and M1 in refusal
    published: list[str] = []
    assert (
        plan_intake.brief_check(
            early, [{"key": "b1", "body": text, "milestone": "Wave 4"}], {}, published
        )
        == []
    )
    assert f"briefs b1: warning: {M1}" in published


# --- answer 8: this repository's open brief of #1835's shape --------------------------------------


def test_req037_the_kit_warns_an_open_brief_of_1835s_shape():
    """REQ-037: answers 8 and 9 (the kit's own map: a new script, no agk.toml, before the day)."""
    text = (
        STUDIED.replace(
            TOUCHES,
            "Touches: scripts/agk/check_brief.py, scripts/agk/example_scan.py,"
            " docs/x.md\nAdds: scripts/agk/example_scan.py\n",
        )  # fmt: skip
        .replace("Advances: new", "Advances: REQ-037")
        .replace("Priority: 1\n", "Priority: 1\nWave: 4\n")
    )
    failures, warnings = check_brief.brief_result(text, KIT_ROOT, today="2026-11-24")
    assert failures == [] and M1 in warnings
