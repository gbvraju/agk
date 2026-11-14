"""Bodies open with a plain summary and verdicts list only what failed (brief #1270; REQ-050).

The pull request template opens with `Summary:` and keeps every checked field one line; the
conductor's role file and the review-pass skill name the short verdict form while every line the
router and the merger parse keeps its name. Files only; no network.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
CONDUCTOR = ROOT / ".claude" / "agents" / "conductor.md"
SKILL = ROOT / "skills" / "review-pass" / "SKILL.md"
FIELDS = ("Advances:", "Issue:", "Behaviour:", "Build-state row:", "Decisions taken:", "Questions:", "Verified:")
PARSED = ("Verdict:", "Local evidence:", "Evidence check:", "Checklist:", "Playbook evidence:", "Approval:")


def test_b_the_template_opens_with_the_summary_then_the_fields_in_order():
    """REQ-050: brief #1270 answer 4 (b)."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert text.startswith("Summary:\n<!--")
    assert "at most three plain lines" in text
    at = [text.index(f"\n{f}") for f in FIELDS]
    assert at == sorted(at) and text.index("Summary:") < at[0]


def test_b_the_template_has_no_prose_under_a_field():
    """REQ-050: brief #1270 answer 1, one line each; `Verified:` lists commands and counts."""
    text = re.sub(r"<!--.*?-->", "", TEMPLATE.read_text(encoding="utf-8"), flags=re.S)
    for line in text.splitlines():
        line = line.strip()
        assert not line or line.startswith("- ") or re.match(r"^[A-Z][A-Za-z -]*:", line), line
    assert "- <command>: <verbatim count>" in text


def test_c_the_conductor_names_the_short_verdict_form():
    """REQ-050: brief #1270 answer 4 (c)."""
    text = CONDUCTOR.read_text(encoding="utf-8")
    assert "only the failing and not-proven items" in text
    assert "`Passed: <n> rules`" in text and "`Read: <n> files`" in text
    assert "only what changed since the last verdict on that pull request" in text
    for line in PARSED:
        assert f"`{line}" in text, line


def test_c_the_skill_names_the_short_verdict_form():
    """REQ-050: brief #1270 answer 4 (c)."""
    text = SKILL.read_text(encoding="utf-8")
    assert "only the failing and not-proven items" in text
    assert "`Passed: <n> rules`" in text and "`Read: <n> files`" in text
    assert "only what changed since the last verdict on that pull request" in text
    for line in PARSED:
        assert f"`{line}" in text, line
