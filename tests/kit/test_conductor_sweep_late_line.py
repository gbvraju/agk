"""The conductor's report names a late sweep (brief #857, the follow-up of Q-836-1).

REQ-046, ADR-0390: `conductor.py watch` prints `SWEEP late <m> min` (ADR-0383 decision 4), and the
conductor's role file says that line goes under `Needs a fix`. The role file as text; no network.
"""

from __future__ import annotations

import re
from pathlib import Path

ROLE = Path(__file__).resolve().parents[2] / ".claude" / "agents" / "conductor.md"


def sentences() -> list[str]:
    """The role file's sentences: a line split where a full stop ends one."""
    text = ROLE.read_text(encoding="utf-8")
    return [s for line in text.splitlines() for s in re.split(r"(?<=\.)\s+", line)]


def needs_a_fix_sentence() -> str:
    found = [s for s in sentences() if "`SWEEP late`" in s and "`Needs a fix`" in s]
    assert len(found) == 1, f"one sentence names both, found {len(found)}"
    return found[0]


def test_one_sentence_names_the_late_sweep_and_needs_a_fix() -> None:
    """REQ-046: brief #857 answer 2 (`SWEEP late` and `Needs a fix` in one sentence)."""
    assert "`conductor.py watch`" in needs_a_fix_sentence()


def test_the_sentence_still_routes_malformed_lines_in_every_hourly_report() -> None:
    """REQ-046: brief #857 answer 1 (what the sentence required before still stands)."""
    sentence = needs_a_fix_sentence()
    assert "`MALFORMED:` lines of `session.py plan`" in sentence
    assert "every hourly report" in sentence
    assert "until the brief passes" in sentence
