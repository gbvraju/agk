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
    assert "/agk:review-pass" in role and "session.py review-queue" in role
    assert "never two verdicts on one head" in role
