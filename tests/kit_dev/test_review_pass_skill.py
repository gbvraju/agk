"""Kit-only tests of the skill `/agk:review-pass` and the words about it (brief 306).

The skill is the conductor's prompt for one pass: it reviews what `session.py review-queue` lists,
never twice on one head, and ends with one line per pull request. The guide documents a loop on
Linux, macOS and Windows that wakes only when the queue's fingerprint changes, from a clean
worktree of the default branch, after a guard check, and names the identity residual."""

from __future__ import annotations

import re

from conftest import KIT_ROOT

SKILL = KIT_ROOT / "skills" / "review-pass" / "SKILL.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "getting-started.md"
REFERENCE = KIT_ROOT / "docs" / "guides" / "reference.md"
ROLE = KIT_ROOT / ".claude" / "agents" / "conductor.md"


def flat(path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_the_skill_is_called_review_pass_and_only_a_person_or_a_loop_runs_it():
    text = SKILL.read_text(encoding="utf-8")
    head = text.split("---")[1]
    assert re.search(r"(?m)^name: review-pass$", head)
    assert re.search(r"(?m)^disable-model-invocation: true$", head)
    assert "# /agk:review-pass" in text


def test_the_skill_holds_every_rule_of_the_pilot():
    text = flat(SKILL)
    for phrase in (
        "labelled `agk:review`",
        "`Question:`, `Report:`, `Correction:` or `Maintainer answer:`",
        "**edited**",
        "differs from the head the last verdict names",
        "stale `agk:ci-running`",
        "at most one verdict per head",
        "python3 scripts/agk/session.py review-queue --all",
        "NEEDS-YOU: #<n>",
        "C:/Users/<user>/AppData/Local/Temp/agk-conductor-<n>/verdict.md",
        "no `--jq`",
        "Never write `Approve:` yourself and never merge",
    ):
        assert phrase in text, phrase


def test_the_skill_uses_the_queue_first_and_ends_with_one_line_per_pull_request():
    text = flat(SKILL)
    assert text.index("review-queue --all") < text.index("Review each one")
    assert "one line per pull request of the queue" in text
    assert "`#<n> <head7> <action>`" in text
    assert "Check again just before posting" in text


def test_the_guide_documents_a_loop_on_three_systems_that_wakes_only_on_a_change():
    text = flat(GUIDE)
    for phrase in (
        "/agk:review-pass",
        "review-queue --fingerprint",
        "Linux and macOS (bash)",
        "Windows (PowerShell",
        "git worktree add --detach",
        "a clean worktree of the default branch",
        "First, the guard check",
        "conductor_guard.py",
        "do not start the loop",
        "comment-only identity",
        "runs with your own GitHub identity",
    ):
        assert phrase in text, phrase
    assert text.index("First, the guard check") < text.index("Linux and macOS (bash)")


def test_the_reference_and_the_role_file_name_the_command():
    assert "| `/agk:review-pass` |" in REFERENCE.read_text(encoding="utf-8")
    role = flat(ROLE)
    assert "`review-pass` command" in role and "session.py review-queue" in role
    assert "never two verdicts on one head" in role


# --- the re-plan at the end of a pass (brief #331, ADR-0190) -------------------------------------

TEMPLATE = KIT_ROOT / "kit" / "templates" / "agk.toml"


def test_the_pass_ends_by_re_planning_after_its_verdicts_and_posts_nothing_new():
    """REQ-041: brief #331 answer 1 (the last step runs the plan and prints start and waits)."""
    text = flat(SKILL)
    assert "**Re-plan.**" in text
    replan = text.index("**Re-plan.**")
    assert text.index("Post the verdict") < replan < text.index("The last lines")
    for phrase in (
        "python3 scripts/agk/session.py plan --json",
        "`Start <n>: <session> takes #<brief>, ...`",
        "`#<brief> waits for",
        "the pass posts nothing new",
    ):
        assert phrase in text, phrase


def test_the_pass_prints_the_prompts_off_and_starts_through_the_adapter_on():
    """REQ-041: brief #331 answers 2 and 4."""
    text = flat(SKILL)
    for phrase in (
        "`auto_start`",
        "`launch_adapter`",
        "python3 scripts/agk/launch.py prompts --plan <the scratch file>",
        "launch.py prompts --plan <the scratch file> --adapter <launch_adapter>",
        "ready-to-paste",
        "never more than the plan's capacity",
        "never for a brief that is taken",
        "made by the started session itself, never by the conductor",
        "not retried",
    ):
        assert phrase in text, phrase


def test_the_template_carries_both_settings_off_and_names_their_adr():
    """REQ-041: brief #331 answer 2 (an optional setting, false by default, a protected change)."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "# auto_start = false" in text and '# launch_adapter = ""' in text
    flow = text[text.index("# [flow]") :]
    assert "auto_start" in flow and "launch_adapter" in flow
    assert "protected" in flat(TEMPLATE)


def test_the_guide_documents_two_example_adapters_each_marked_verify():
    """REQ-041: brief #331 answer 3 (a local terminal one and a cloud one; none installed)."""
    text = flat(GUIDE)
    start = text.index("Automatic starts after a review pass")
    part = text[start : start + 4000]
    for phrase in (
        "auto_start = true",
        "launch_adapter",
        "A local terminal adapter",
        "A cloud adapter",
        "The kit installs neither",
        "AGK_SESSION",
    ):
        assert phrase in part, phrase
    assert part.count("(verify") >= 2


def test_the_role_file_names_the_re_plan_and_the_one_command_it_may_run():
    """REQ-041: brief #331 answer 2 (the guard allows that one command)."""
    role = flat(ROLE)
    for phrase in (
        "session.py plan --json",
        "launch.py prompts --plan",
        "`auto_start = true`",
        "`launch_adapter`",
    ):
        assert phrase in role, phrase


def test_the_role_and_the_skill_end_an_empty_pass_the_same_way():
    """REQ-041: brief #331 answer 1 (the verdict on 2d53a5d, item 3: an empty pass re-plans)."""
    phrase = "`queue empty` followed by its `Start` and `waits for` lines"
    assert phrase in flat(SKILL)
    role = flat(ROLE)
    assert (
        "end with the line `queue empty` followed by the re-plan's `Start` and `waits for` lines"
        in role
    )
    assert "end with the one line `queue empty`" not in role
