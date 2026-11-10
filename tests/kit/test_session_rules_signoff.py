"""Session rule 29 names the design and inventory sign-off lines (brief #976, ADR-0418; REQ-044).

SPEC-0037 rule 9 holds the rule; `config/session-rules.md` rule 29 is where a session reads it.
No network.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "config" / "session-rules.md"


def rule(number: int) -> str:
    prefix = f"{number}. "
    for line in RULES.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    raise AssertionError(f"rule {number} not found")


def test_rule_29_names_the_design_sign_off_line():
    """REQ-044: brief #976 answer 1."""
    text = rule(29)
    assert "Approve: design" in text
    assert "docs/design/signoffs.md" in text


def test_rule_29_names_the_inventory_line_its_place_and_who_gives_it():
    """REQ-044: brief #976 answer 1, the rest of the sentence."""
    text = rule(29)
    for phrase in (
        "`Approve: inventory <full head ID>`",
        "`Approve: design <version> <full head ID>`",
        "`spec_approvers`",
        "never posts them",
        "`date -u`",
        "SPEC-0037 rule 9",
    ):
        assert phrase in text, phrase


def test_rule_29_keeps_its_single_line():
    """REQ-044: brief #976 answer 1, no new rule line."""
    lines = [
        line for line in RULES.read_text(encoding="utf-8").splitlines() if line.startswith("29. ")
    ]
    assert len(lines) == 1
    assert not any(
        line.startswith("38. ") for line in RULES.read_text(encoding="utf-8").splitlines()
    )
