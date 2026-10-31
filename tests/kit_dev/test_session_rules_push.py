"""Kit-only tests of when a builder pushes (brief #415, ADR-0225; REQ-040).

A builder still commits a `checkpoint:` at every step, but pushes only at milestones: the first
checkpoint, which opens the draft; the tests written so far expected-red; the tests green; marking
the pull request ready; and before any stop it can foresee (answer 1). The `Progress:` comment of
rule 8 is posted at each push, not each checkpoint, and rule 23 is unchanged (answer 2). The
getting-started guide says the same in one line where it shows a builder's loop (answer 3). Rules
7, 8 and 31 no longer disagree on when to push (answer 4). Files only; no network.
"""

from __future__ import annotations

import re

from conftest import KIT_ROOT

RULES = KIT_ROOT / "config" / "session-rules.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "getting-started.md"


def rules() -> dict[int, str]:
    """The numbered rules of the file, by number; a rule is one line."""
    found: dict[int, str] = {}
    for line in RULES.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"(\d+)\. (.+)", line):
            found[int(m.group(1))] = m.group(2)
    return found


def test_ac_rule_7_commits_every_checkpoint_and_pushes_only_at_milestones():
    """Answer 1: every step is still a commit; the push is not."""
    seven = rules()[7]
    assert seven.startswith("A builder commits a `checkpoint:` at every step that leaves")
    assert "green or expected-red" in seven
    assert "pushes its branch only at these milestones" in seven
    assert "commits and pushes" not in seven


def test_ac_rule_7_names_each_milestone_in_order():
    """Answer 1: the five milestones, in the brief's order."""
    seven = rules()[7]
    milestones = (
        "the first checkpoint, which opens the pull request as a draft",
        "the tests written so far expected-red",
        "the tests green",
        "marking the pull request ready",
        "before any stop it can foresee (a usage limit near, a question it will wait on, "
        "the end of its turn)",
    )
    at = [seven.find(m) for m in milestones]
    assert all(i >= 0 for i in at), [m for m, i in zip(milestones, at, strict=True) if i < 0]
    assert at == sorted(at)


def test_ac_rule_7_keeps_its_draft_and_ready_parts():
    """Answer 1 changes when to push, nothing else of rule 7."""
    seven = rules()[7]
    for phrase in (
        "so that the work is visible and owned at once",
        "A checkpoint never carries a `Final:` status line",
        "ready for review only when its own checks pass",
    ):
        assert phrase in seven, phrase


def test_ac_rule_8_posts_the_progress_line_at_each_push():
    """Answer 2: at each push, not each checkpoint."""
    eight = rules()[8]
    assert eight.startswith("At each push of rule 7, not at each checkpoint,")
    assert "Progress: <head> done <n>/<m>; next: <step>" in eight
    assert "After each checkpoint" not in eight


def test_ac_rule_23_is_unchanged():
    """Answer 2: GitHub unreachable still means commit locally and push later."""
    text = rules()[23]
    assert text.startswith(
        "When GitHub cannot be reached at all, a session keeps committing locally"
    )
    assert "with its `checkpoint:` steps, and loses nothing" in text


def test_ac_rules_7_8_and_31_agree_on_when_to_push():
    """Answer 4: no rule still says a builder pushes at every step or checkpoint."""
    found = rules()
    assert "before each push" in found[31]
    stale = re.compile(
        r"push(?:es)? (?:its branch )?(?:at|after) (?:every|each) (?:step|checkpoint)", re.I
    )
    for number, text in found.items():
        assert not stale.search(text), number
        assert "commits and pushes" not in text, number
    # Only rule 7 defines the milestones; rules 8 and 31 hang on "each push".
    assert [n for n, t in found.items() if "milestones" in t] == [7]


def test_ac_the_guide_says_it_in_one_line_in_the_builder_loop():
    """Answer 3: one line in step 2, where the guide shows a builder's loop."""
    text = GUIDE.read_text(encoding="utf-8")
    hits = [ln for ln in text.splitlines() if "pushes only at milestones" in ln]
    assert len(hits) == 1
    assert hits[0].startswith("2. **Start a builder session.**")
    assert "commits a `checkpoint:` at every step" in hits[0]
    assert "session rule 7" in hits[0]
