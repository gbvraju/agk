"""Kit-only tests of the getting-started fixes of rehearsal 1 (issue #156, fixes 1 to 4, 6 to 8)."""

from __future__ import annotations

import re

from conftest import KIT_ROOT

GUIDE = KIT_ROOT / "docs" / "guides" / "getting-started.md"
SKILL = KIT_ROOT / "skills" / "spec" / "SKILL.md"
TEMPLATE = KIT_ROOT / "docs" / "specs" / "TEMPLATE.md"


def guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def part(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_fix1_before_you_start_says_which_steps_need_gh_logged_in():
    """Issue #156 fix 1: steps 5 and 11 and the doctor's remote checks, not 3, 4, 6 and 7."""
    text = part(guide(), "## Before you start", "## Step 1.")
    assert "Steps 5 and 11 and the remote checks of the doctor need `gh` logged in" in text
    assert "steps 3, 4, 6 and 7 do not" in text


def test_fix2_each_slash_command_names_the_script_its_skill_runs():
    """Issue #156 fix 2: one sentence, from the SKILL.md of each command."""
    text = guide()
    for command, script in (
        ("init", "init.py"),
        ("ruleset", "ruleset.py"),
        ("start", "playbook.py"),
        ("spec", "intake.py"),
        ("doctor", "doctor.py"),
    ):
        skill = (KIT_ROOT / "skills" / command / "SKILL.md").read_text(encoding="utf-8")
        assert f"scripts/agk/{script}" in skill, command
        sentence = next(s for s in text.split("\n") if f"`/agk:{command}` runs" in s)
        assert f"`scripts/agk/{script}`" in sentence, command


def test_fix3_step_3_has_no_file_count_or_size():
    """Issue #156 fix 3: the figures go stale."""
    step = part(guide(), "## Step 3.", "## Step 4.")
    assert not re.search(r"\b\d+ files? would be created", step)
    assert "225 KB" not in step and "53 files" not in step and "0.28.0" not in step
    assert "`dry run: N files would be created; nothing was written`" in step


def test_fix4_step_4_describes_todays_governance_output():
    """Issue #156 fix 4: ten `ok`, two `skipped` in any order, one `specs:` line."""
    step = part(guide(), "## Step 4.", "## Step 5.")
    assert "ten lines starting with `ok`" in step
    assert "two lines starting with `skipped`" in step and "in either order" in step
    assert "one line that starts `specs:`" in step
    assert "each starting with `ok`" not in step


def test_fix5_the_guide_says_steps_6_and_7_need_origin():
    """Issue #156 fix 5: the remote is a precondition of both steps."""
    for start, end in (("## Step 6.", "## Step 7."), ("## Step 7.", "## Step 8.")):
        assert "`origin`" in part(guide(), start, end), start


def test_fix6_step_6_names_the_discovery_questions_and_the_valid_answer():
    """Issue #156 fix 6: six topics, at most three questions a round, `not known yet`."""
    step = part(guide(), "## Step 6.", "## Step 7.")
    for word in ("users", "existing", "where it runs", "data", "scale", "compliance"):
        assert word in step, word
    assert "at most three questions a round" in step and "`not known yet`" in step


def test_fix7_the_spec_template_and_the_skill_agree_on_the_sections():
    """Issue #156 fix 7: the template gains `## Proof` and `## Residual`, in the skill's order."""
    template = TEMPLATE.read_text(encoding="utf-8")
    headings = re.findall(r"(?m)^## .*$", template)
    assert headings == ["## Rules", "## Tests", "## Proof", "## Residual", "## Open questions"]
    skill = SKILL.read_text(encoding="utf-8")
    for name in ("`## Tests`", "`## Proof`", "`## Residual`", "`## Open questions`"):
        assert name in skill, name
    assert template.rstrip().endswith("none")


def test_fix8_the_skill_writes_no_questions_only_when_a_person_confirmed_it():
    """Issue #156 fix 8: with nobody to ask, the intake stops and says so."""
    text = " ".join(SKILL.read_text(encoding="utf-8").split())
    assert "only when a person confirmed that the sentence needs none" in text
    assert "if there is nobody to ask" in text and "stop before writing any file and say so" in text
