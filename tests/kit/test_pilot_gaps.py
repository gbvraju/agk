"""Brief #263 (REQ-039): the gaps a first organisation project met, as tests of the kit's checks.

Build (b), answer 4: while the default branch is red, the router's red-branch issue is open with the
label `agk-brief`; it is not a brief for SPEC-0034 rule 9, so a body needs no `Brief:` line for it.
"""

from __future__ import annotations

import json

import pytest

BODY = "Advances: REQ-039\nBuild-state row: 2026-10-30 REQ-039 x\nSummary: A change.\n"
RED_BODY = (
    'Sentence: "The default branch is red: the required checks of its head fail."\n'
    "Answers:\n1. Failing check: governance\n2. Head: abc\n3. Run: u\n"
    "Priority: 0\nAdvances: none\nTouches: **\nSize: S\n"
)


def red(number: int = 9, **change) -> dict:
    item = {
        "number": number,
        "title": "The default branch is red",
        "user": {"login": "github-actions[bot]"},
        "labels": [{"name": "agk-brief"}],
        "body": RED_BODY,
    }
    item.update(change)
    return item


def brief(number: int = 12) -> dict:
    return {
        "number": number,
        "title": "Brief: t",
        "user": {"login": "someone"},
        "labels": [{"name": "agk-brief"}],
        "body": "Sentence: x\nPriority: 1\n",
    }


def checked(repo, issues: list[dict], body: str = BODY):
    repo.write("issues.json", json.dumps(issues))
    return repo.run("check_pr_body.py", "--issues", "issues.json", "-", stdin=body)


def test_answer4_the_red_branch_issue_alone_is_not_a_brief_for_rule_9(repo):
    """REQ-039: brief #263 answer 4."""
    proc = checked(repo, [red()])
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout == "ok pr-body\n"


def test_answer4_another_open_brief_beside_the_red_branch_issue_still_needs_brief(repo):
    """REQ-039: brief #263 answer 4 (only the red-branch issue is left out)."""
    for issues in ([red(), brief()], [brief(), red()]):
        proc = checked(repo, issues)
        assert proc.returncode == 1 and "rule 9" in proc.stdout
        assert checked(repo, issues, BODY + "Brief: #12\n").returncode == 0


@pytest.mark.parametrize(
    "change",
    [
        {"user": {"login": "a-person"}},
        {"title": "The default branch is red (by hand)"},
        {"body": "Sentence: x\nPriority: 1\n"},
    ],
)
def test_answer4_an_issue_of_the_same_shape_not_written_by_the_router_is_a_brief(repo, change):
    """REQ-039: brief #263 answer 4 (the router's own issue only, as `session.is_red` reads it)."""
    proc = checked(repo, [red(**change)])
    assert proc.returncode == 1 and "rule 9" in proc.stdout


def test_answer4_the_message_names_the_rule_and_no_value(repo):
    """REQ-039: brief #263 answer 4 (principle 8)."""
    proc = checked(repo, [brief(), red()])
    assert "github-actions" not in proc.stdout and "#9" not in proc.stdout
    assert "#12" not in proc.stdout
