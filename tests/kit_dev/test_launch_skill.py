"""Kit-only tests of the skill `/agk:launch` and the words about it (brief 247 build (b)).

The skill runs `session.py plan`, asks the person to confirm and starts one session per planned
slot through an adapter; it starts nothing without a yes, creates no recurring task and holds no
credential. The name is the maintainers' ruling on Q-247-6: `/agk:start` is the vision command."""

from __future__ import annotations

import re

from conftest import KIT_ROOT

SKILL = KIT_ROOT / "skills" / "launch" / "SKILL.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "getting-started.md"
REFERENCE = KIT_ROOT / "docs" / "guides" / "reference.md"


def skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_the_skill_is_called_launch_and_the_vision_command_keeps_the_name_start():
    head = skill().split("---")[1]
    assert re.search(r"(?m)^name: launch$", head)
    assert re.search(r"(?m)^disable-model-invocation: true$", head)
    assert "# /agk:launch" in skill()
    start = (KIT_ROOT / "skills" / "start" / "SKILL.md").read_text(encoding="utf-8")
    assert re.search(r"(?m)^name: start$", start) and "constitution/vision.md" in start


def test_the_skill_runs_the_plan_asks_before_starting_and_uses_the_prompts():
    text = skill()
    for phrase in (
        "python3 scripts/agk/session.py plan",
        "python3 scripts/agk/session.py plan --json",
        "python3 scripts/agk/launch.py prompts --plan",
        "Only a plain `yes`",
        "nothing starts",
        "`Start 0`",
    ):
        assert phrase in text, phrase
    assert text.index("session.py plan") < text.index("(yes/no)") < text.index("launch.py prompts")


def test_the_skill_creates_no_recurring_task_holds_no_credential_and_starts_nothing_later():
    flat = " ".join(skill().split())
    for phrase in (
        "creates no recurring task",
        "holds no credential",
        "starts nothing later",
        "no `cron_expression`",
        "One task per session",
        "it never merges",
    ):
        assert phrase in flat, phrase


def test_every_runtime_fact_the_skill_cannot_confirm_is_marked_verify():
    text = skill()
    assert text.count("(verify)") >= 3
    assert "within a minute" in text and "launcher-test" in text  # the one measured fact


def test_the_skill_names_only_scripts_the_kit_installs():
    for script in set(re.findall(r"scripts/agk/(\w+\.py)", skill())):
        assert (KIT_ROOT / "scripts" / "agk" / script).is_file(), script
        assert f'"scripts/agk/{script}"' in (KIT_ROOT / "kit" / "manifest.json").read_text()


def test_the_guide_states_the_exception_to_the_rule_that_no_session_starts_another():
    text = GUIDE.read_text(encoding="utf-8")
    item = re.search(
        r"(?ms)^\d+\. \*\*Start builders by a launcher\.\*\*(.*?)(?=^\d+\. \*\*|\Z)", text
    )
    assert item, "no item 'Start builders by a launcher'"
    body = item.group(1)
    for phrase in (
        "no session starts, stops or reviews another",
        "except that a session starts other sessions when a person runs `/agk:launch`",
        "confirms its plan",
        "creates no recurring task",
        "starts nothing later",
    ):
        assert phrase in body, phrase


def test_the_reference_lists_the_command():
    row = [x for x in REFERENCE.read_text(encoding="utf-8").splitlines() if "`/agk:launch`" in x]
    assert len(row) == 1 and "launch.py prompts" in row[0] and "session.py plan" in row[0]
