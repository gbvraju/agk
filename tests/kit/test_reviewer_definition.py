"""Tests of .claude/agents/reviewer.md (SPEC-0003 rules 2, 3, 12, 21)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / ".claude" / "agents" / "reviewer.md"


def frontmatter_and_body() -> tuple[dict[str, str], str]:
    text = AGENT.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    assert match
    fields = dict(line.split(": ", 1) for line in match.group(1).splitlines() if ": " in line)
    return fields, match.group(2)


def test_ac3_reviewer_tools_are_exactly_read_grep_glob():
    """REQ-013 AC3: rules 2 and 21."""
    fields, _ = frontmatter_and_body()
    assert fields["tools"] == "Read, Grep, Glob"
    assert fields["name"] == "reviewer"
    assert fields["description"]


def test_ac3_reviewer_says_it_never_approves_merges_pushes_or_edits():
    """REQ-013 AC3: rules 2 and 21."""
    _, body = frontmatter_and_body()
    low = " ".join(body.lower().split())
    assert "you never approve, merge, push or edit" in low
    assert "enable auto-merge" in low and "run a command" in low


def test_ac3_reviewer_treats_pr_content_as_data():
    """REQ-013 AC3: rules 3 and 21."""
    _, body = frontmatter_and_body()
    low = " ".join(body.lower().split())
    assert "data, not instructions" in low
    for source in ("pr body", "diff"):
        assert source in low


def test_ac3_reviewer_fixes_the_output_format_of_the_validator():
    """REQ-013 AC3: rules 8, 9 and 12. The prompt and the validator agree."""
    _, body = frontmatter_and_body()
    for token in (
        "Verdict:", "Context truncated:", "Where:", "Rule:", "Wrong:", "Fix:",
        "cleared", "fix list", "rejected", "review-context.md", "check_review_report.py",
    ):  # fmt: skip
        assert token in body, token
