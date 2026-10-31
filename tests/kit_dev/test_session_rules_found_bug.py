"""Kit-only tests of the found-bug session rule (brief #405, ADR-0221; REQ-037).

A builder that finds a bug its brief does not cover leaves its own pull request unchanged (unless
the bug blocks that pull request's own gate and the fix is one line), adds its evidence to the open
issue for it or files one bug brief labelled `found-bug`, says in its `Report:` that the failure is
known and unrelated, and never takes a `found-bug` brief unless the conductor assigns it (answer 1).
The same rule says it removes the images and build cache it made for a probe (answer 2). The label
the rule names is never the label `session.py next` offers, so no builder takes a found-bug brief
on its own (answer 3, Q-405-1). Files only; no network.
"""

from __future__ import annotations

import re
import sys

from conftest import KIT_ROOT

RULES = KIT_ROOT / "config" / "session-rules.md"
SCRIPTS = KIT_ROOT / "scripts" / "agk"
LABEL = "found-bug"


def rules() -> dict[int, str]:
    """The numbered rules of the file, by number; a rule is one line."""
    found: dict[int, str] = {}
    for line in RULES.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"(\d+)\. (.+)", line):
            found[int(m.group(1))] = m.group(2)
    return found


def found_bug_rule() -> str:
    hits = [text for text in rules().values() if f"`{LABEL}`" in text]
    assert len(hits) == 1, f"one session rule names the label {LABEL}, found {len(hits)}"
    return hits[0]


def test_ac_the_rules_stay_numbered_one_by_one():
    numbers = sorted(rules())
    assert numbers == list(range(1, len(numbers) + 1))


def test_ac_a_bug_outside_the_brief_is_not_fixed_in_the_pull_request():
    """Answer 1, part 1, with its one exception."""
    text = found_bug_rule()
    assert "its brief does not cover" in text
    assert "leaves its own pull request unchanged" in text
    assert "blocks the pull request's own gate" in text
    assert "the fix is one line" in text


def test_ac_the_builder_first_searches_the_open_issues_and_adds_its_evidence():
    """Answer 1, part 2: by the test name or the symptom, evidence as a comment."""
    text = found_bug_rule()
    assert "first searches the open issues" in text
    assert "by the test name or the symptom" in text
    assert "adds its evidence there as a comment" in text


def test_ac_otherwise_it_files_one_found_bug_brief_and_reports_it_as_known():
    """Answer 1, part 3: one brief with the label, the evidence and how to reproduce it."""
    text = found_bug_rule()
    assert f"files one bug brief labelled `{LABEL}`" in text
    assert "the evidence and how to reproduce it" in text
    assert "`Report:`" in text and "known and unrelated" in text
    # Part 2 comes before part 3: the search is first.
    assert text.index("first searches the open issues") < text.index("files one bug brief")


def test_ac_builders_never_take_a_found_bug_brief_unless_assigned():
    """Answer 1, part 4."""
    text = found_bug_rule()
    assert f"never takes a `{LABEL}` brief unless the conductor assigns it" in text
    assert "`Assign:`" in text


def test_ac_the_probe_images_and_build_cache_are_removed():
    """Answer 2: in the same rule."""
    text = found_bug_rule()
    assert "removes the images and build cache it made for a probe" in text
    assert "when the check ends" in text


def test_ac_the_label_is_not_the_one_next_offers():
    """Answer 3 (Q-405-1): the brief skill writes a file and no label; the label the rule names
    is one that `session.py next` never reads, so part 4 holds without a change to the script."""
    sys.path.insert(0, str(SCRIPTS))
    try:
        import session
    finally:
        sys.path.remove(str(SCRIPTS))
    assert LABEL != session.LABEL
    text = found_bug_rule()
    assert f"not `{session.LABEL}`" in text
    labels = set(re.findall(r"labelled `([^`]+)`", text))
    assert labels == {LABEL}


def test_ac_the_brief_skill_writes_no_other_label():
    """Answer 3: the brief skill names no label that could differ from the rule's."""
    skill = (KIT_ROOT / "skills" / "brief" / "SKILL.md").read_text(encoding="utf-8")
    named = set(re.findall(r"label(?:led|s)?[ =:]+`?([a-z][a-z0-9:-]+)`?", skill))
    assert named <= {LABEL}
