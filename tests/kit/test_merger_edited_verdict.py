"""An edited verdict starts the merger and the router (brief #836 answer 1, ADR-0383).

REQ-046 (SPEC-0039 rule 2): a verdict corrected in place used to start neither workflow, so a
cleared head waited for a person. Saved event payloads and the workflow files only; no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_merge_cleared_merger import comment_event, event, writes
from test_merge_cleared_verdict import HEAD, cleared, comment

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def edited(body: str) -> dict:
    return {**comment_event(body), "action": "edited"}


def text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def condition(name: str, job: str) -> str:
    """The `if:` line of JOB in workflow NAME."""
    body = text(name).split(f"\n  {job}:\n", 1)[1]
    return next(ln for ln in body.splitlines() if ln.strip().startswith("if:"))


@pytest.mark.parametrize(
    "first", [f"Verdict: cleared {HEAD}", "Approve: SPEC-0039", "Final: docs/adr/x.md a -> b"]
)
def test_an_edited_clearing_comment_names_the_pull_request(tmp_path, first):
    """REQ-046: brief #836 answer 1 (`Verdict:`, `Final:` or `Approve:`, the same reading)."""
    proc, made = event(tmp_path, edited(first), "issue_comment", comments=[cleared()])
    assert proc.stdout.strip() == f"7 {HEAD}", proc.stdout + proc.stderr
    assert writes(made) == []


def test_an_edit_that_does_not_clear_the_head_starts_nothing(tmp_path):
    """REQ-046: brief #836 answers 1 and 6 (the comments decide, as for a new one)."""
    note = comment(f"Verdict: fix list {HEAD}\n\n1. Fix the test.", at=6)
    proc, made = event(tmp_path, edited(note["body"]), "issue_comment", comments=[note])
    assert proc.stdout.strip() == ""
    assert writes(made) == []


def test_a_new_final_comment_stays_outside_the_event_job(tmp_path):
    """REQ-046: brief #836 answer 1 (`Final:` counts for an edit; a created one is as today)."""
    payload = comment_event("Final: docs/adr/x.md a -> b")
    proc, made = event(tmp_path, payload, "issue_comment", comments=[cleared()])
    assert proc.stdout.strip() == ""
    assert writes(made) == []


def test_an_edited_report_starts_nothing(tmp_path):
    """REQ-046: brief #836 answer 1 (only the three first lines)."""
    proc, made = event(tmp_path, edited("Report: edited"), "issue_comment", comments=[cleared()])
    assert proc.stdout.strip() == ""
    assert writes(made) == []


@pytest.mark.parametrize("name", ["merger.yml", "agk-route.yml"])
def test_both_workflows_start_on_an_edited_comment(name):
    """REQ-046: brief #836 answer 1 (`issue_comment` `edited`, in both workflows)."""
    assert "\n  issue_comment:\n    types: [created, edited]\n" in text(name)


@pytest.mark.parametrize(
    ("name", "job"), [("merger.yml", "merger"), ("agk-route.yml", "agk-route")]
)
def test_an_edit_starts_a_job_only_for_the_three_first_lines(name, job):
    """REQ-046: brief #836 answer 1 (an edited `Final:` starts it; a created `Final:` does not)."""
    line = condition(name, job)
    edit = "github.event.action == 'edited' && startsWith(github.event.comment.body, 'Final:')"
    assert edit in line
    assert "startsWith(github.event.comment.body, 'Verdict:')" in line
    assert "startsWith(github.event.comment.body, 'Approve:')" in line


def test_the_router_keeps_its_other_first_lines_for_a_new_comment_only():
    """REQ-046: brief #836 answer 1 (an edited `Assign:` or `Correction:` changes no state)."""
    line = condition("agk-route.yml", "agk-route")
    created = line.split("github.event.action == 'created' && (", 1)[1]
    for word in ("Approval:", "Correction:", "Assign:", "Request:"):
        assert f"startsWith(github.event.comment.body, '{word}')" in created, word
