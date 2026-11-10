"""An approved spec cannot merge while it still reads `Draft` on the head.

Brief #797 answer 4, ADR-0373, amendment 144, REQ-046 (SPEC-0039 rule 5, SPEC-0032 rule 2).
`merge_cleared.py` holds such a pull request, naming the rule, and `route.py` keeps it at
`agk:approve`. Saved answers only; no network, invented logins.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest
from test_merge_cleared_verdict import (
    HEAD,
    ON,
    calls,
    cleared,
    comment,
    fake_gh,
    repo,
    run,
    toml,
)
from test_route import HEAD as ROUTE_HEAD
from test_route import facts, said

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import reviewers  # noqa: E402
import route  # noqa: E402

PATH = "docs/specs/0052-an-example-spec.md"
HELD = "an approved spec still reads Draft (rule 5)"
APPROVER = "owner-three"
MAINTAINER = "maintainer"


YAML = 'version: 1\nspec_approvers: ["@owner-three"]\nconductor_accounts: ["@conductor-two"]\n'


def spec_file(status: str = "modified") -> dict:
    return {"filename": PATH, "status": status, "patch": "+a line"}


def contents(word: str) -> dict:
    text = f"# SPEC-0052: An example\n\n- Status: {word}\n"
    encoded = base64.b64encode(text.encode()).decode()
    return {f"{PATH}": {"type": "file", "encoding": "base64", "content": encoded}}




def guarded(tmp_path, approve: str | None, word: str = "Draft", login: str = APPROVER):
    notes = [cleared(login="conductor-two")]
    if approve is not None:
        notes.append(comment(approve, login=login, at=6))
    root = repo(tmp_path, toml(ON), reviewers_yaml=YAML)
    bin_dir, log = fake_gh(tmp_path, comments=notes, files=[spec_file()], contents=contents(word))
    return run(root, bin_dir, "--pr", "7", "--sha", HEAD), calls(log)


@pytest.mark.parametrize("line", ["Approve: SPEC-0052", f"Approve: {HEAD} SPEC-0052"])
def test_the_merge_is_held_while_an_approved_spec_reads_draft(tmp_path, line):
    """REQ-046: brief #797 answer 4 (both forms of the approval, the rule named, no value)."""
    proc, made = guarded(tmp_path, line)
    assert HELD in proc.stdout, proc.stdout + proc.stderr
    assert "SPEC-0052" not in proc.stdout
    assert [c for c in made if "PUT" in c] == []


def test_a_spec_with_no_approval_is_not_held_by_this_rule(tmp_path):
    """REQ-046: brief #797 answer 4 (a Draft spec nobody approved merges as a draft intake)."""
    proc, _ = guarded(tmp_path, None)
    assert HELD not in proc.stdout, proc.stdout + proc.stderr


def test_a_spec_that_reads_approved_is_not_held_by_this_rule(tmp_path):
    """REQ-046: brief #797 answer 4 (the status commit made, the hold ends)."""
    proc, _ = guarded(tmp_path, f"Approve: {HEAD} SPEC-0052", word="Approved")
    assert HELD not in proc.stdout, proc.stdout + proc.stderr


def test_an_approve_line_by_anyone_else_counts_for_nothing(tmp_path):
    """REQ-046: brief #797 answer 4 (only `spec_approvers`; a stranger cannot hold a merge)."""
    proc, _ = guarded(tmp_path, "Approve: SPEC-0052", login="a-stranger")
    assert HELD not in proc.stdout, proc.stdout + proc.stderr


def test_the_approved_specs_are_read_from_the_two_comment_forms():
    """REQ-046: brief #797 answer 4 (the reading both commands share)."""
    notes = [
        {"user": {"login": "owner"}, "body": "Approve: SPEC-0001"},
        {"user": {"login": "Owner"}, "body": f"Approve: {HEAD} SPEC-0002\nmore"},
        {"user": {"login": "other"}, "body": "Approve: SPEC-0003"},
        {"user": {"login": "owner"}, "body": "I said Approve: SPEC-0004"},
    ]
    assert reviewers.specs_named_approved(notes, ["owner"]) == {"SPEC-0001", "SPEC-0002"}


# --- the label --------------------------------------------------------------------------------


def labelled(draft: set[str], *extra: dict, kind: str = "cleared") -> str:
    verdict = f"Verdict: {kind} {ROUTE_HEAD}\n\n1. a finding (rule: none)\n"
    notes = [said(1, "boss", verdict), *extra]
    return route.decide(facts(comments=notes, files=[spec_file()], draft_specs=draft))


def test_the_label_stays_approve_while_an_approved_spec_reads_draft():
    """REQ-046: brief #797 answer 4 (`route.py` keeps it at `agk:approve`)."""
    approved = said(2, MAINTAINER, "Approve: SPEC-0052")
    assert labelled({"SPEC-0052"}, approved) == "agk:approve"


def test_the_label_is_ready_once_the_spec_reads_approved():
    """REQ-046: brief #797 answer 4 (the status commit made, the label is `agk:merge-ready`)."""
    assert labelled(set(), said(2, MAINTAINER, "Approve: SPEC-0052")) == "agk:merge-ready"


def test_a_draft_spec_nobody_approved_does_not_wait():
    """REQ-046: brief #797 answer 4 (only a spec a person approved)."""
    assert labelled({"SPEC-0052"}) == "agk:merge-ready"


def test_a_fix_list_still_goes_to_the_builder():
    """REQ-046: brief #797 answer 4 (the builder's turn is not hidden behind the wait)."""
    approved = said(2, MAINTAINER, "Approve: SPEC-0052")
    assert labelled({"SPEC-0052"}, approved, kind="fix list") == "agk:fix"
