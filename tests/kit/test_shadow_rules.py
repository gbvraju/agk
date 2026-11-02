"""The shapes of `Shadow:` and `Marks:` and where each lives (SPEC-0035 rules 1, 3, 7; AC8).

Session rules 25 and 26 moved to the shadow role file, each leaving a pointer line (ADR-0243).
Text only. No network.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def session_rules() -> str:
    return (ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")


def rules() -> str:
    """The section of the shadow role file that holds session rules 25 and 26 (ADR-0243)."""
    text = (ROOT / ".claude" / "agents" / "shadow.md").read_text(encoding="utf-8")
    return text.split("## Moved from the session rules", 1)[1].split("\n## ", 1)[0]


def test_ac8_the_session_rules_point_at_the_shadow_role_file_for_both_shapes():
    """REQ-042 AC8: rule 7 (the session rules say where the shapes are, ADR-0243)."""
    for number in (25, 26):
        line = f"{number}. Moved to `.claude/agents/shadow.md` (ADR-0243)."
        assert line in session_rules().splitlines(), number


def test_ac8_the_rules_number_without_a_gap_after_the_shadow_rules():
    """REQ-042 AC8"""
    lines = session_rules().splitlines()
    numbers = [int(line.split(".")[0]) for line in lines if line[:1].isdigit()]
    assert numbers == list(range(1, len(numbers) + 1)) and len(numbers) >= 26


def test_ac8_the_rules_give_the_shadow_shape_and_where_it_lives():
    """REQ-042 AC8: rules 1 and 7."""
    text = " ".join(rules().split())
    for phrase in (
        "`Shadow: #<pr> <sha> cleared|fix list|rejected`",
        "numbered findings `S1.`, `S2.`",
        "on the one open issue labelled `agk-shadow`",
        "Only the shadow reviewer posts a `Shadow:` comment",
        "reads the pull request, its checks and its diff and never the verdict comments",
    ):
        assert phrase in text, phrase


def test_ac8_the_rules_give_the_marks_shape_who_marks_and_where():
    """REQ-042 AC8: rules 3 and 7."""
    text = " ".join(rules().split())
    for phrase in (
        "`Marks:`",
        "`<C|S><sha7>-<n> right|wrong|both`",
        "on the pull request, after it merges",
        "the maintainer writes the marks, or at least confirms every `wrong` mark",
        "the person who merges it",
        "never marks its own findings",
        "an unmarked head is `unmarked`, never zero",
    ):
        assert phrase in text, phrase


def test_ac8_the_shadow_rules_start_stop_and_review_no_session_and_name_no_project():
    """REQ-042 AC8"""
    shadow = " ".join(rules().split()).split("Shadow:", 1)[1]
    assert "starts, stops or reviews no session" in shadow
    assert not re.search(r"#\d{2,}", shadow)
