"""Two standing owner rulings (brief #1385, ADR-0583; REQ-037).

Ruling 1: a pull request whose changed lines (tests excluded) are at most three times its brief's
size guide (300 when the brief gives none), and whose latest verdict names no finding, is accepted
with the line `Size: <n> of <guide>, accepted by standing ruling (ADR-0583)`; otherwise the owner
is asked. Ruling 2: an instruction file's word count may rise by at most ten percent over its
`config/rule-budget.txt` baseline when its rule lines do not rise, with the body line
`Rule budget: <file> <old> to <new> words, standing ruling (ADR-0583)`; otherwise asked. No network.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_req037_size_at_two_and_a_half_times_with_no_finding_is_accepted():
    """REQ-037: 250 of 100 with no finding carries the size line, so no `Owner needed:`."""
    from rules import size_ruling

    line = size_ruling(250, 100, 0)
    assert line == "Size: 250 of 100, accepted by standing ruling (ADR-0583)"
    assert "Owner needed:" not in line


def test_req037_size_over_three_times_or_with_a_finding_is_asked():
    """REQ-037: 350 of 100, or one finding, leaves the owner's question as today."""
    from rules import size_ruling

    assert size_ruling(350, 100, 0) is None
    assert size_ruling(250, 100, 1) is None
    assert size_ruling(300, 100, 0) is not None


def test_req037_a_brief_with_no_size_guide_uses_300():
    """REQ-037: no guide is 300, so 900 passes and 901 is asked."""
    from rules import size_ruling

    assert size_ruling(900, None, 0) == "Size: 900 of 300, accepted by standing ruling (ADR-0583)"
    assert size_ruling(901, None, 0) is None


def test_req037_a_rule_budget_raise_of_eight_percent_with_no_new_rule_passes():
    """REQ-037: 1000 to 1080 words, rule lines unchanged, gives the body line."""
    from rules import budget_ruling

    assert budget_ruling(".claude/agents/x.md", 1000, 1080, 12, 12) == (
        "Rule budget: .claude/agents/x.md 1000 to 1080 words, standing ruling (ADR-0583)"
    )
    assert budget_ruling(".claude/agents/x.md", 1000, 1100, 12, 11) is not None


def test_req037_twelve_percent_or_one_new_rule_line_is_asked():
    """REQ-037: 1000 to 1120 words, or one rule line more, is asked as today."""
    from rules import budget_ruling

    assert budget_ruling(".claude/agents/x.md", 1000, 1120, 12, 12) is None
    assert budget_ruling(".claude/agents/x.md", 1000, 1010, 12, 13) is None


def test_req037_the_conductor_file_and_the_adr_carry_both_rulings():
    """REQ-037: the conductor's verdict steps name both lines; the ADR quotes the owner."""
    conductor = (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "accepted by standing ruling (ADR-0583)" in conductor
    assert "standing ruling (ADR-0583)`" in conductor and "Rule budget: <file>" in conductor
    adr = next((ROOT / "docs" / "adr").glob("0583-*.md")).read_text(encoding="utf-8")
    assert "- Status: " in adr and '"Go ahead"' in adr
