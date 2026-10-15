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


def test_ac3_reviewer_checks_every_decision_and_rule_against_the_whole_diff():
    """REQ-013 AC3: SPEC-0003 rules 11 and 12 as amended (shadow review 2)."""
    _, body = frontmatter_and_body()
    low = " ".join(body.lower().split())
    assert (
        "for every accepted adr decision and approved spec rule in the context, state whether "
        "the diff, including its effect on other files, contradicts it"
    ) in low
    assert "operating rules" in low and "changed files" in low


def test_ac3_reviewer_scope_stays_with_approved_text():
    """REQ-013 AC3: rule 11 is unchanged: only rules stated in Approved text, no style opinions."""
    _, body = frontmatter_and_body()
    low = " ".join(body.lower().split())
    assert "only rules stated in approved text" in low
    assert "no style opinions and no speculation about intent" in low
    assert "claude.md is context, not a source of rules to cite" in low
