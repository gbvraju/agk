"""Tests of .claude/agents/reviewer.md and of the REQ-013 wiring (SPEC-0003 rules 2, 12, 13, 21)."""

from __future__ import annotations

import re

from conftest import KIT_ROOT, expected_files, manifest

AGENT = KIT_ROOT / ".claude" / "agents" / "reviewer.md"


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


def test_ac3_reviewer_and_scripts_are_installed_by_init_and_adopt():
    """REQ-013 AC3: rule 13."""
    wanted = {
        ".claude/agents/reviewer.md",
        "scripts/agk/review_context.py",
        "scripts/agk/check_review_report.py",
    }
    assert wanted <= set(manifest()["verbatim"])
    assert wanted <= expected_files()


def test_ac3_requirement_013_exists_and_is_planned():
    """REQ-013 AC3: rule 15 (an ADR adds the requirement). Never marked done by an agent."""
    text = (KIT_ROOT / "docs" / "requirements.md").read_text(encoding="utf-8")
    section = text.split("### REQ-013", 1)[1].split("\n### ", 1)[0]
    for ac in ("AC1", "AC2", "AC3", "AC4"):
        assert ac in section
    assert "- Status: planned" in section


def test_ac3_kit_version_is_0_5_0():
    """REQ-013 AC3: ADR-0011."""
    assert manifest()["kit_version"] == "0.5.0"


def test_ac3_the_template_requirements_are_not_changed_by_this_requirement():
    """REQ-013 AC3: installed repositories get no REQ-013."""
    template = (KIT_ROOT / "kit" / "templates" / "requirements.md").read_text(encoding="utf-8")
    assert "REQ-013" not in template
