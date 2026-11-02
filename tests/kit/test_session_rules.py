"""config/session-rules.md and the role files that point at it (SPEC-0030 rule 1; REQ-037 AC1)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "config" / "session-rules.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ac1_the_rules_file_states_each_rule():
    """REQ-037 AC1"""
    text = read(RULES).lower()
    for phrase in (
        "verdict:",
        "listed verdict author",
        "names its current head",
        "merge of its pull request",
        "ignores every other comment",
        "never merges",
        "tags",
        "auto-merge",
        "posts a verdict",
        "touches a secret",
        "one open pull request",
        "depends-on: #n",
        "make governance",
        "check_final_clearance.py",
        "not the full suite",
        "stops and asks",
        "session.py watch",
    ):
        assert phrase in text, phrase


def test_ac1_the_rules_are_numbered_without_a_gap():
    """REQ-037 AC1"""
    numbers = [int(line.split(".")[0]) for line in read(RULES).splitlines() if line[:1].isdigit()]
    assert numbers == list(range(1, len(numbers) + 1)) and len(numbers) >= 6


def test_ac1_claude_md_and_the_architect_file_point_at_the_rules_file():
    """REQ-037 AC1"""
    for rel in ("CLAUDE.md", ".claude/agents/architect.md"):
        assert "config/session-rules.md" in read(ROOT / rel), rel


def test_ac1_nothing_in_the_operating_rules_contradicts_the_rules_file():
    """REQ-037 AC1: the rules file does not allow what CLAUDE.md forbids."""
    claude = read(ROOT / "CLAUDE.md").lower()
    assert "never merge" in claude and "never poll ci" in claude
    assert "never merges" in read(RULES).lower()


def test_ac8_the_rules_say_how_watch_is_started_so_that_its_end_wakes_the_session():
    """REQ-039 AC8: rule 4 (the Claude Code form; never in the foreground, never detached)."""
    text = " ".join(read(RULES).split())
    assert "run_in_background" in text
    assert "re-invokes the session" in text
    assert "never in the foreground" in text
    assert "`&`" in text and "`nohup`" in text
    assert "exits" in text and "each event is one wake" in text
    assert "session.py queue" in text and "first" in text
    assert "equivalent" in text


def test_ac6_ac7_the_rules_say_reproduce_first_and_what_a_correction_asks():
    """REQ-039 AC6 and AC7: rules 9 and 10 (a measured cause; the correction travels on)."""
    text = " ".join(read(RULES).split())
    assert "to reproduce that cause" in text and "`Measured:`" in text
    assert "`Question:`" in text and "builds nothing" in text
    assert "`Correction:`" in text
    assert "never force-pushes" in text
    assert "one `Report:`" in text
    assert "listed verdict author" in text and "`Correction:` comment" in text
