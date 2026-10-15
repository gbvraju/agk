"""Tests of .github/workflows/drift-audit.yml shape (SPEC-0004 rules 2, 4, 13, 17, 21, 23)."""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "drift-audit.yml"
ALLOWED_GH = {"issue create", "issue edit", "issue list", "label create"}


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def top_block(name: str) -> str:
    """The indented lines under a top-level key."""
    match = re.search(rf"^{name}:\s*\n((?:[ \t]+.*\n|\n)*)", text(), flags=re.M)
    assert match, name
    return match.group(1)


def test_ac1_triggers_are_only_schedule_and_workflow_dispatch():
    """REQ-011 AC1: rule 4 and 21."""
    keys = re.findall(r"^  ([a-z_]+):", top_block("on"), flags=re.M)
    assert sorted(keys) == ["schedule", "workflow_dispatch"]


def test_ac1_exactly_one_weekly_cron_saturday_0617_utc():
    """REQ-011 AC1: rule 4, 21 and Q-ON-18 (Saturday 06:17 UTC)."""
    crons = re.findall(r"^\s*-\s*cron:\s*[\"']([^\"']+)[\"']", text(), flags=re.M)
    assert crons == ["17 6 * * 6"]
    minute, hour, dom, month, dow = crons[0].split()
    assert dom == "*" and month == "*" and dow.isdigit() and minute not in ("0", "30")


def test_ac3_permissions_are_exactly_contents_read_and_issues_write():
    """REQ-011 AC3: rules 2 and 21."""
    lines = [ln.strip() for ln in top_block("permissions").splitlines() if ln.strip()]
    assert lines == ["contents: read", "issues: write"]
    assert text().count("permissions:") == 1  # none per job


def test_ac3_every_action_is_pinned_to_a_full_commit_sha():
    """REQ-011 AC3: rules 17 and 21."""
    uses = re.findall(r"^\s*-?\s*uses:\s*(.+)$", text(), flags=re.M)
    assert uses
    for line in uses:
        assert re.fullmatch(r"\S+@[0-9a-f]{40}\s+# v\d+(\.\d+){1,2}", line.strip()), line


def test_ac3_only_the_allowed_gh_verbs_are_used():
    """REQ-011 AC3: rule 21 (amendments 8 adds the read-only `issue list`)."""
    verbs = set(
        re.findall(r"\bgh ((?:issue|label|pr|api|repo|run|workflow|release) [a-z-]+)", text())
    )
    assert verbs
    assert verbs <= ALLOWED_GH, verbs - ALLOWED_GH


def test_ac3_nothing_that_writes_elsewhere():
    """REQ-011 AC3: rules 2 and 21."""
    body = text()
    run_lines = "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith("#"))
    for forbidden in (
        "git push",
        "gh pr",
        "gh issue close",
        "gh issue comment",
        "gh api",
        "--force",
    ):
        assert forbidden not in run_lines, forbidden
    assert "pull_request" not in run_lines and "\n  push:" not in body


def test_ac3_only_the_workflow_token_is_used():
    """REQ-011 AC3: rule 16 (no secret)."""
    assert set(re.findall(r"secrets\.\w+", text())) == {"secrets.GITHUB_TOKEN"}


def test_ac1_job_runs_on_the_default_branch_with_full_history():
    """REQ-011 AC1: rule 4."""
    body = text()
    assert "if: ${{ github.ref_name == github.event.repository.default_branch }}" in body
    assert re.search(r"fetch-depth:\s*0\b", body)


def test_ac1_workflow_asks_the_script_for_title_action_and_report():
    """REQ-011 AC2: rules 13-15. The decision stays in the tested script."""
    body = text()
    for flag in ("--open-issues", "--print-action", "--print-title"):
        assert flag in body, flag
    assert "scripts/agk/drift_audit.py" in body
    assert "agk-drift-audit" in body


def test_ac1_header_comment_documents_that_schedules_may_be_disabled():
    """REQ-011 AC1: rule 23."""
    head = []
    for line in text().splitlines():
        if not line.startswith("#"):
            break
        head.append(line.lower())
    comment = " ".join(head)
    assert "inactivity" in comment and "workflow_dispatch" in comment and "scheduled" in comment
