"""One reading of a verdict body, shared (brief 238; SPEC-0021 rules 1 and 2; REQ-039).

`common.verdict_problem(body)` returns the problem of a `Verdict:` comment whose `Final:` line the
router cannot read, or None: a `Final:` line under a verdict that is not `fix list`, a `Final:` line
that does not match `Final: <path> [REQ-n] <old> -> <new>`, and a line for `docs/requirements.md`
without its requirement id or the reverse (the rule `covered_fix_list` applies). A message names the
rule and shows the expected shape, never the body. No network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402

SHA = "a1b2c3d4e5f6"
ADR = "docs/adr/0001-the-adr.md"
GOOD = f"Verdict: fix list {SHA}\n\nFinal: {ADR} Proposed -> Accepted\n"
NOT_FIX = (
    "SPEC-0021 rule 1: a Final: line is read only under 'Verdict: fix list <sha>'; "
    "write that first line, or leave the Final: line out"
)
SHAPE = (
    "SPEC-0021 rule 2: a Final: line reads 'Final: <path> <old> -> <new>', "
    "with the old and the new status as one word each"
)
NUMBERED = (
    "SPEC-0021 rule 1: a Final: line is read only in a fix list with no numbered items; "
    "post the Final: line in its own verdict once the items are met"
)
REQ = (
    "SPEC-0021 rule 2: a Final: line for docs/requirements.md reads "
    "'Final: docs/requirements.md REQ-nnn <old> -> <new>', and no other path names a requirement"
)


def test_a_well_formed_covered_fix_list_has_no_problem():
    """Brief 238 answer 4: a well-formed verdict."""
    assert common.verdict_problem(GOOD) is None
    two = GOOD + "Final: docs/specs/0001-the-spec.md Draft -> Approved\n"
    assert common.verdict_problem(two) is None
    req = f"Verdict: fix list {SHA}\nFinal: docs/requirements.md REQ-041 planned -> done\n"
    assert common.verdict_problem(req) is None


def test_a_verdict_without_a_final_line_or_a_comment_that_is_no_verdict_has_none():
    """Brief 238 answer 1: only a Final: line under a Verdict: is judged."""
    for body in (
        f"Verdict: cleared {SHA}\n\nAll fine.\n",
        f"Verdict: rejected {SHA}\nthe reason\n",
        f"Verdict: fix list {SHA}\n\n1. do this\n2. do that\n",
        "Report: abc1234 something\nFinal: nothing readable\n",
        "",
        "Verdict:",
    ):
        assert common.verdict_problem(body) is None, body


@pytest.mark.parametrize("kind", ["cleared", "rejected"])
def test_a_final_line_under_a_verdict_that_is_not_a_fix_list_is_the_first_problem(kind):
    """Brief 238 answer 1: the case of the three pull requests of 2026-10-26."""
    body = f"Verdict: {kind} {SHA}\nFinal: flip ADR-0146 to Accepted in one commit, pushed alone.\n"
    assert common.verdict_problem(body) == NOT_FIX
    well_formed_but_cleared = f"Verdict: {kind} {SHA}\nFinal: {ADR} Proposed -> Accepted\n"
    assert common.verdict_problem(well_formed_but_cleared) == NOT_FIX


@pytest.mark.parametrize(
    "line",
    [
        "Final: flip ADR-0146 to Accepted in one commit",
        f"Final: {ADR} Proposed to Accepted",
        f"Final: {ADR} Proposed -> ",
        f"Final: {ADR} -> Accepted",
        "Final:",
        f"Final:{ADR} Proposed -> Accepted",
        f"Final: {ADR} Proposed -> Accepted now",
    ],
)
def test_a_final_line_that_does_not_match_the_shape_is_a_shape_problem(line):
    """Brief 238 answer 1: the shape of `FINAL_LINE`."""
    assert common.verdict_problem(f"Verdict: fix list {SHA}\n{line}\n") == SHAPE


def test_the_requirements_file_needs_its_requirement_id_and_no_other_path_has_one():
    """Brief 238 answer 1: the rule `covered_fix_list` already applies."""
    bare = f"Verdict: fix list {SHA}\nFinal: docs/requirements.md planned -> done\n"
    assert common.verdict_problem(bare) == REQ
    stray = f"Verdict: fix list {SHA}\nFinal: {ADR} REQ-041 Proposed -> Accepted\n"
    assert common.verdict_problem(stray) == REQ


def test_the_first_offending_line_decides_and_a_good_line_beside_it_does_not_hide_it():
    """Brief 238 answer 1"""
    body = GOOD + "Final: flip the spec\n"
    assert common.verdict_problem(body) == SHAPE
    assert (
        common.verdict_problem("Final: flip the spec\n" + GOOD) is None
    )  # not a verdict first line


def test_a_final_line_in_a_fix_list_with_numbered_items_is_a_problem():
    """Verdict on 90e5749: `covered_fix_list` ignores such a Final: line without a word."""
    items = "1. Fix the thing.\n\nThen push alone:\n"
    body = f"Verdict: fix list {SHA}\n\n{items}Final: {ADR} Proposed -> Accepted\n"
    assert common.verdict_problem(body) == NUMBERED
    assert common.covered_fix_list(body) is None
    one_line = "Verdict: fix list abc1234\n1. fix x\nFinal: docs/adr/x.md Proposed -> Accepted\n"
    assert common.verdict_problem(one_line) == NUMBERED
    indented = f"Verdict: fix list {SHA}\n  2. an item\nFinal: {ADR} Proposed -> Accepted\n"
    assert common.verdict_problem(indented) == NUMBERED


def test_numbered_items_without_a_final_line_are_still_no_problem():
    """Verdict on 90e5749: only a Final: line beside the items is the silent case."""
    assert common.verdict_problem(f"Verdict: fix list {SHA}\n\n1. Fix x.\n2. Fix y.\n") is None


def test_the_not_fix_list_problem_comes_before_the_numbered_one():
    """A cleared verdict with items and a Final: line is first of all not a fix list."""
    body = f"Verdict: cleared {SHA}\n1. x\nFinal: {ADR} Proposed -> Accepted\n"
    assert common.verdict_problem(body) == NOT_FIX


def test_covered_fix_list_and_the_problem_agree_on_what_is_covered():
    """Brief 238 answer 1: one reading. A body with no problem and no numbered item is covered."""
    assert common.covered_fix_list(GOOD) is not None and common.verdict_problem(GOOD) is None
    for body in (
        f"Verdict: cleared {SHA}\nFinal: {ADR} Proposed -> Accepted\n",
        f"Verdict: fix list {SHA}\nFinal: flip it\n",
        f"Verdict: fix list {SHA}\nFinal: docs/requirements.md planned -> done\n",
    ):
        assert common.covered_fix_list(body) is None and common.verdict_problem(body) is not None


def test_no_message_carries_a_sha_a_path_or_a_word_of_the_body():
    """Brief 238 answer 1 and CLAUDE.md rule 6: the rule and the shape, never the body."""
    for body in (
        f"Verdict: cleared {SHA}\nFinal: hunter2 {ADR}\n",
        f"Verdict: fix list {SHA}\nFinal: hunter2 {ADR} secret\n",
        f"Verdict: fix list {SHA}\nFinal: docs/requirements.md hunter2 -> done\n",
    ):
        message = common.verdict_problem(body) or ""
        assert message and "hunter2" not in message and SHA not in message
        assert "0001" not in message and "secret" not in message
