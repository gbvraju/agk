"""merge_cleared.py waits for an open owner ask or spec approval (brief #1134, ADR-0483).

Amendment 170 of SPEC-0039 rule 5, REQ-039. The hold list gains two holds: a pull request labelled
`agk:question` (an open owner ask, `owner ask`), and one whose clearing verdict carries an
`Approval: SPEC-nnnn` line for a spec with no approval for the head (`spec approval`), read as the
body's line is read. `--status` reports both as pending the same way. Every test runs on a git
repository in `tmp_path`, saved responses and a fake `gh`; no network, invented logins.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest
from test_merge_cleared_verdict import (
    BUILDER,
    HEAD,
    MERGE12,
    OLD,
    ON,
    OWNER,
    SHA12,
    calls,
    cleared,
    comment,
    fake_gh,
    merge_cleared_run,
    one_line,
    repo,
    run,
    toml,
    world,
)

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import merge_cleared  # noqa: E402

APPROVERS = f'version: 1\nspec_approvers: ["@{OWNER}"]\n'
MERGED = f"merge-cleared #7 {SHA12}: merged {MERGE12}"
ADR = "docs/adr/0099-an-invented-decision.md"
ADR_FILE = {"filename": ADR, "status": "added", "patch": "+x"}
CODE_FILE = {"filename": "scripts/agk/example.py", "status": "modified", "patch": "+x"}
QUESTION = {"name": "agk:question"}


def pull(**fields: object) -> dict:
    return {**world()["pull"], **fields}


def held(proc, reason: str) -> str:
    line = one_line(proc)
    assert line == f"merge-cleared #7 {SHA12}: held: {reason}", line
    assert proc.returncode == 3, line
    return line


def no_merge(made: list[list[str]]) -> None:
    assert [c for c in made if "PUT" in c] == [], made


def bare(sha: str = HEAD, at: int = 5, extra: str = "") -> dict:
    return cleared(sha, at=at, extra=extra)


def covered(sha: str = HEAD, approval: str = "Approval: SPEC-0030", at: int = 5) -> dict:
    """A covered fix list on SHA (rule 3a): one `Final:` line, and the verdict's APPROVAL line."""
    lines = [f"Verdict: fix list {sha}", "", "Reviewed against the brief.", "", approval]
    lines += [f"Final: {ADR} Proposed -> Accepted"]
    return comment("\n".join(lines) + "\n", OWNER, at)


def proposed() -> dict:
    """The contents answer of the ADR at the head: `- Status: Proposed`."""
    text = "# ADR-0099: An invented decision\n\n- Status: Proposed\n"
    data = base64.b64encode(text.encode()).decode()
    return {ADR: {"type": "file", "encoding": "base64", "content": data}}


def approve(spec: str = "SPEC-0030", sha: str = HEAD, login: str = OWNER, at: int = 7) -> dict:
    return comment(f"Approve: {sha} {spec}", login, at)


# --- (a) an open owner ask ----------------------------------------------------------------------


def test_req039_a_cleared_head_labelled_agk_question_is_held_naming_owner_ask(tmp_path):
    """REQ-039: brief #1134 answer 3 (a)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], pull=pull(labels=[QUESTION]))
    held(proc, "owner ask (rule 5)")
    no_merge(made)


def test_req039_the_owner_ask_holds_beside_other_labels(tmp_path):
    """REQ-039: brief #1134 answer 1 (a): the label alone decides, whatever else is on it."""
    labels = [{"name": "agk:merge-ready"}, QUESTION]
    proc, made = merge_cleared_run(tmp_path, toml(ON), [bare()], pull=pull(labels=labels))
    held(proc, "owner ask (rule 5)")
    no_merge(made)


# --- (b) the clearing verdict's Approval: line --------------------------------------------------


def test_req039_a_covered_fix_list_with_an_approval_line_and_no_approve_is_held(tmp_path):
    """REQ-039: brief #1134 answer 3 (b), the measured case of #1132."""
    proc, made = merge_cleared_run(
        tmp_path,
        toml(ON),
        [covered()],
        reviewers_yaml=APPROVERS,
        files=[ADR_FILE, CODE_FILE],
        contents=proposed(),
    )
    held(proc, "spec approval (rule 5)")
    no_merge(made)


def test_req039_the_same_verdict_merges_once_an_approver_names_the_head(tmp_path):
    """REQ-039: brief #1134 answer 3 (b): `Approve: <head> SPEC-0030` by a spec approver."""
    proc, _ = merge_cleared_run(
        tmp_path,
        toml(ON),
        [covered(), approve()],
        reviewers_yaml=APPROVERS,
        files=[ADR_FILE, CODE_FILE],
        contents=proposed(),
    )
    assert one_line(proc) == MERGED


@pytest.mark.parametrize(
    ("name", "later"),
    [
        ("no approve line", []),
        ("another head", [approve(sha=OLD)]),
        ("another spec", [approve("SPEC-0031")]),
        ("another account", [approve(login=BUILDER)]),
    ],
)
def test_req039_a_cleared_verdict_with_an_approval_line_needs_the_approve(tmp_path, name, later):
    """REQ-039: brief #1134 answer 1 (b): a plain `Verdict: cleared` is read the same way."""
    proc, made = merge_cleared_run(
        tmp_path,
        toml(ON),
        [bare(extra="Approval: SPEC-0030 docs/specs/0030-x.md\n"), *later],
        reviewers_yaml=APPROVERS,
    )
    held(proc, "spec approval (rule 5)")
    no_merge(made)


def test_req039_an_approval_line_of_an_older_verdict_does_not_hold(tmp_path):
    """REQ-039: brief #1134 answer 1 (b): only the clearing verdict, the latest, is read."""
    older = comment(f"Verdict: fix list {OLD}\n\nApproval: SPEC-0030\n", OWNER, 2)
    proc, _ = merge_cleared_run(tmp_path, toml(ON), [older, bare()], reviewers_yaml=APPROVERS)
    assert one_line(proc) == MERGED


# --- (c) and (d): no Approval: line and no owner ask still merges -------------------------------


def test_req039_a_verdict_without_an_approval_line_and_no_owner_ask_merges(tmp_path):
    """REQ-039: brief #1134 answer 3 (c)."""
    proc, _ = merge_cleared_run(tmp_path, toml(ON), [bare()], reviewers_yaml=APPROVERS)
    assert one_line(proc) == MERGED
    proc, _ = merge_cleared_run(
        tmp_path / "covered",
        toml(ON),
        [covered(approval="Reviewed in full.")],
        files=[ADR_FILE, CODE_FILE],
        contents=proposed(),
    )
    assert one_line(proc) == MERGED


# --- --status: the same two holds ---------------------------------------------------------------


def status_run(tmp_path: Path, **saved):
    root = repo(tmp_path, toml(ON), reviewers_yaml=APPROVERS)
    bin_dir, log = fake_gh(tmp_path, **saved)
    proc = run(root, bin_dir, "--status", "--pr", "7", "--sha", HEAD)
    return proc, calls(log)


def test_req039_status_reports_an_owner_ask_as_pending(tmp_path):
    """REQ-039: brief #1134 answer 2 (`--status` reports it as pending)."""
    proc, _ = status_run(tmp_path, pull=pull(labels=[QUESTION]), comments=[bare()])
    expected = f"merge-cleared #7 {SHA12}: status pending owner ask (rule 5)"
    assert proc.stdout.strip() == expected, proc.stdout + proc.stderr


def test_req039_status_names_the_spec_of_the_verdict_s_approval_line(tmp_path):
    """REQ-039: brief #1134 answer 2 (`approve SPEC-nnnn`, as for the body's line)."""
    proc, _ = status_run(
        tmp_path, comments=[covered()], files=[ADR_FILE, CODE_FILE], contents=proposed()
    )
    expected = f"merge-cleared #7 {SHA12}: status pending approve SPEC-0030"
    assert proc.stdout.strip() == expected, proc.stdout + proc.stderr


# --- the reading, unit by unit ------------------------------------------------------------------


def test_req039_unapproved_reads_the_body_and_the_clearing_verdict():
    """REQ-039: brief #1134 answer 2: `unapproved` reads the verdict's lines beside the body's."""
    approvers = [OWNER]
    verdict = bare(extra="Approval: SPEC-0030\n")
    assert merge_cleared.unapproved(pull(), [verdict], HEAD, approvers)
    assert not merge_cleared.unapproved(pull(), [verdict, approve()], HEAD, approvers)
    assert not merge_cleared.unapproved(pull(), [bare()], HEAD, approvers)
    both = pull(body="Approval: SPEC-0042\n")
    assert merge_cleared.unapproved(both, [verdict, approve()], HEAD, approvers)
    assert not merge_cleared.unapproved(
        both, [verdict, approve(), approve("SPEC-0042")], HEAD, approvers
    )
    assert merge_cleared.asked_specs(both, [verdict], HEAD) == ["SPEC-0030", "SPEC-0042"]
    assert merge_cleared.asked_specs(both, [bare(OLD, extra="Approval: SPEC-0030\n")], HEAD) == [
        "SPEC-0042"
    ]
