"""Kit-only test of the launcher contract in the guide (SPEC-0034 rule 6; REQ-041 AC6).

AGK ships no launcher and no session starts, stops or reviews another. The guide shows the
contract with two examples, a scheduled task of a session runtime and a CI schedule, that start
`start` sessions from `session.py demand`, each running `session.py next` and ending on `no brief`
or `full`.
"""

from __future__ import annotations

import re

from conftest import KIT_ROOT

GUIDE = KIT_ROOT / "docs" / "guides" / "getting-started.md"


def section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    found = re.search(r"(?ms)^## Running the loop\n(.*?)(?=^## |\Z)", text)
    assert found, "no section 'Running the loop'"
    return found.group(1)


def contract() -> str:
    found = re.search(
        r"(?ms)^\d+\. \*\*Start builders by a launcher\.\*\*(.*?)(?=^\d+\. \*\*|\Z)", section()
    )
    assert found, "no item 'Start builders by a launcher'"
    return found.group(1)


def test_ac6_the_item_states_the_contract_and_that_agk_ships_no_launcher():
    """REQ-041 AC6"""
    body = contract()
    for phrase in (
        "python3 scripts/agk/session.py demand",
        '"ready"',
        '"open"',
        '"max"',
        '"start"',
        "min(ready, max - open)",
        "ships no launcher",
        "no session starts, stops or reviews another",
        "`no brief`",
        "`full`",
        "python3 scripts/agk/session.py next --session",
    ):
        assert phrase in body, phrase


def test_ac6_the_item_shows_two_examples_a_scheduled_task_and_a_ci_schedule():
    """REQ-041 AC6"""
    body = contract()
    assert "scheduled task of a session runtime" in body and "CI schedule" in body
    blocks = re.findall(r"(?ms)^\s*```(\w*)\n(.*?)^\s*```", body)
    assert len(blocks) >= 2, blocks
    texts = [b[1] for b in blocks]
    assert any("session.py demand" in t and "session.py next" in t for t in texts)
    assert any("schedule:" in t and "cron:" in t and "session.py demand" in t for t in texts)


def test_ac6_the_examples_start_sessions_and_nothing_else():
    """REQ-041 AC6: no merge, no tag, no review of another session."""
    for _, text in re.findall(r"(?ms)^\s*```(\w*)\n(.*?)^\s*```", contract()):
        lowered = text.lower()
        for word in ("merge", "gh pr", "git tag", "--admin", "force"):
            assert word not in lowered, word


def test_ac6_the_item_names_no_project_and_no_person():
    """REQ-041 AC6: generic text."""
    assert "gbvraju" not in contract().lower()
