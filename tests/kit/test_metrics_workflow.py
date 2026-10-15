"""Tests of .github/workflows/metrics.yml shape (SPEC-0007 rules 11, 17, 18)."""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "metrics.yml"
ALLOWED_GH = {"issue create", "issue edit", "issue list", "label create"}


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def top_block(name: str) -> str:
    """The indented lines under a top-level key."""
    match = re.search(rf"^{name}:\s*\n((?:[ \t]+.*\n|\n)*)", text(), flags=re.M)
    assert match, name
    return match.group(1)


def test_ac1_triggers_are_only_schedule_and_workflow_dispatch():
    """REQ-012 AC3: rule 11."""
    keys = re.findall(r"^  ([a-z_]+):", top_block("on"), flags=re.M)
    assert sorted(keys) == ["schedule", "workflow_dispatch"]


def test_ac1_one_weekly_cron_monday_0643_utc():
    """REQ-012 AC3: rule 11 (Monday 06:43 UTC, off the hour and half hour)."""
    crons = re.findall(r"^\s*-\s*cron:\s*[\"']([^\"']+)[\"']", text(), flags=re.M)
    assert crons == ["43 6 * * 1"]


def test_ac1_dispatch_takes_an_optional_today_input():
    """REQ-012 AC3: rule 11, 24 (backfill a week by hand)."""
    block = top_block("on").split("workflow_dispatch:", 1)[1]
    assert re.search(r"^      today:\s*$", block, flags=re.M)
    assert "required: false" in block


def test_ac1_the_input_reaches_the_script_through_env_not_inline():
    """REQ-012 AC3: no expression is interpolated into the shell."""
    assert "INPUT_TODAY: ${{ github.event.inputs.today }}" in text()
    run = text().split("run: |", 1)[1]
    assert "${{" not in run


def test_ac1_permissions_are_exactly_the_five_of_rule_17():
    """REQ-012 AC3: rule 17."""
    lines = [ln.strip() for ln in top_block("permissions").splitlines() if ln.strip()]
    assert sorted(lines) == [
        "actions: read",
        "checks: read",
        "contents: read",
        "issues: write",
        "pull-requests: read",
    ]
    assert text().count("permissions:") == 1  # none per job


def test_ac1_every_action_is_pinned_to_a_full_commit_sha():
    """REQ-012 AC3: rule 18."""
    uses = re.findall(r"^\s*-?\s*uses:\s*(.+)$", text(), flags=re.M)
    assert uses
    for line in uses:
        assert re.fullmatch(r"\S+@[0-9a-f]{40}\s+# v\d+(\.\d+){1,2}", line.strip()), line


def test_ac1_checkout_has_full_history():
    """REQ-012 AC3: rule 17 (the test counts read git objects)."""
    assert re.search(r"fetch-depth:\s*0", text())


def test_ac1_only_the_allowed_gh_verbs_are_used():
    """REQ-012 AC3: rule 17 (create or edit the one issue, create the label, read the list)."""
    verbs = set(
        re.findall(r"\bgh ((?:issue|label|pr|api|repo|run|workflow|release) [a-z-]+)", text())
    )
    assert verbs
    assert verbs <= ALLOWED_GH, verbs - ALLOWED_GH


def test_ac1_nothing_else_writes():
    """REQ-012 AC3: rule 17 (no git write, no push, no comment, no close, no merge)."""
    code = "\n".join(ln for ln in text().splitlines() if not ln.lstrip().startswith("#"))
    for forbidden in (
        "git push",
        "git commit",
        "gh pr",
        "issue close",
        "issue comment",
        "--method",
    ):
        assert forbidden not in code, forbidden


def test_ac1_runs_only_on_the_default_branch():
    """REQ-012 AC3: rule 11."""
    assert "github.ref_name == github.event.repository.default_branch" in text()


def test_ac1_an_incomplete_week_still_files_the_issue_then_fails_the_job():
    """REQ-012 AC3: rule 16 (the issue is the evidence; the job exit shows the flag)."""
    run = text().split("run: |", 1)[1]
    assert "|| status=$?" in run
    assert run.rstrip().endswith('exit "$status"')
    assert "grep -q '^agk metrics [0-9]'" in run
