"""CI runs only where it can change a result (brief #216): the texts of the three workflows.

proof no longer runs on `edited`; governance runs on `edited` only the steps that read the pull
request body; both cancel a superseded run; proof reports success for a status-only final commit
without running the suite; the router starts a job only for a comment that can change a state.
Workflow files checked as text, saved event payloads for the router. The required check names
`proof` and `governance` are unchanged. No network.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflow(name: str) -> str:
    """Read when a test runs: a copy of the kit tests in a project has no `.github/workflows`."""
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def steps(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for block in re.split(r"(?m)^      - ", text)[1:]:
        name = re.search(r"(?m)^(?:name: )?(.+)$", block.split("\n", 1)[0] + "\n")
        title = re.search(r"(?m)^\s*name: (.+)$", block) if not block.startswith("name:") else None
        label = (
            block.split("\n", 1)[0].removeprefix("name: ")
            if block.startswith("name:")
            else (title.group(1) if title else (name.group(1) if name else ""))
        )
        found[label.strip().strip('"')] = block
    return found


def types_of(text: str) -> set[str]:
    match = re.search(r"pull_request:\s*\n\s*types:\s*\[([^\]]*)\]", text)
    assert match
    return {t.strip() for t in match.group(1).split(",")}


# --- proof (answers 1, 3 and 4) -----------------------------------------------------------------


def test_proof_no_longer_runs_when_the_description_is_edited():
    """Brief #216 answer 1: a body cannot change a test."""
    assert types_of(workflow("proof.yml")) == {"opened", "synchronize", "reopened"}


def test_proof_and_governance_keep_their_job_names():
    """Brief #216 principle: the required check names stay."""
    assert re.search(r"^name: proof$", workflow("proof.yml"), flags=re.M)
    assert re.search(r"^jobs:\n  proof:\n", workflow("proof.yml"), flags=re.M)
    assert re.search(r"^name: governance$", workflow("governance.yml"), flags=re.M)
    assert re.search(r"^jobs:\n  governance:\n", workflow("governance.yml"), flags=re.M)


def test_proof_cancels_the_run_on_a_superseded_commit():
    """Brief #216 answer 3: one group per pull request, the older run cancelled."""
    assert re.search(
        r"^concurrency:\n  group: proof-\$\{\{ github\.event\.pull_request\.number \}\}\n"
        r"  cancel-in-progress: true\n",
        workflow("proof.yml"),
        flags=re.M,
    )


def test_governance_cancels_a_superseded_run_of_a_pull_request_and_never_a_push():
    """Brief #216 answer 3: a push to the default branch is never cancelled."""
    block = (
        workflow("governance.yml")
        .split("\nconcurrency:\n", 1)[1]
        .split("\n\n", 1)[0]
        .split("\njobs:", 1)[0]
    )
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in block
    assert "github.event.pull_request.number || github.sha" in block


def test_a_description_edit_cannot_cancel_the_full_governance_run():
    """Brief #216 answer 3 (a reading): `edited` runs have a group of their own, so a body edit
    during a full run does not cancel it and leave the partial run to report the check."""
    block = workflow("governance.yml").split("\nconcurrency:\n", 1)[1].split("\njobs:", 1)[0]
    assert "github.event.action == 'edited'" in block


def test_proof_decides_the_status_only_commit_with_one_get_and_the_script():
    """Brief #216 answer 4: the GET is in the workflow, the decision in the script."""
    assert "scripts/agk/status_only.py" in workflow("proof.yml")
    assert re.search(
        r"^permissions:\n  contents: read\n  checks: read\n", workflow("proof.yml"), flags=re.M
    )
    assert workflow("proof.yml").count("gh api --method GET") == 1
    assert "secrets." not in workflow("proof.yml") and "pull_request_target" not in workflow(
        "proof.yml"
    ).replace("never pull_request_target", "")


def test_the_suite_step_is_skipped_for_a_status_only_commit_and_still_reports_one_outcome():
    """Brief #216 answer 4: exactly one `outcome:` step succeeds, `skipped`, for a skipped run."""
    blocks = steps(workflow("proof.yml"))
    run = blocks["Red-then-green"]
    assert "steps.status.outputs.skip != 'true'" in run
    skipped = next(b for n, b in blocks.items() if n == "outcome: skipped")
    assert "steps.status.outputs.skip == 'true'" in skipped
    assert "steps.proof.outputs.outcome == 'skipped'" in skipped
    for outcome in ("proven", "not-proven", "unknown"):
        block = next(b for n, b in blocks.items() if n.startswith(f"outcome: {outcome}"))
        assert "steps.status.outputs.skip" not in block


def test_proof_with_an_unreadable_parent_check_runs_in_full():
    """Brief #216 answer 4: a failed GET leaves the conclusion empty, and an empty one runs."""
    block = steps(workflow("proof.yml"))["Status-only final commit"]
    assert "|| true" in block or "|| echo" in block


# --- governance on an edited description (answer 2) ----------------------------------------------

BODY_STEPS = {
    "Latest full run",
    "Base of the merge ref",
    "PR body file",
    "PR comments",
    "PR states and open pull requests",
    "check_specs",
    "check_pr_mode",
    "Open briefs",
    "PR body shape",
}


def test_governance_runs_only_the_steps_that_read_the_body_when_the_description_is_edited():
    """Brief #216 answer 2: the others carry `github.event.action != 'edited'`."""
    for name, block in steps(workflow("governance.yml")).items():
        head = block.split("\n        run:", 1)[0].split("\n        uses:", 1)[0]
        skipped = "github.event.action != 'edited'" in head
        if name in BODY_STEPS or name.startswith("uses: actions/"):
            assert not skipped, name
        elif name not in ("Secret scan",):
            assert skipped, name
    assert "github.event.action != 'edited'" in steps(workflow("governance.yml"))["Secret scan"]


def test_governance_still_runs_every_step_on_a_commit():
    """Brief #216 principle: no check that runs today is lost on a commit that can change it."""
    full = [n for n in steps(workflow("governance.yml")) if n.startswith(("check_", "reviewers"))]
    assert len(full) == 13
    assert types_of(workflow("governance.yml")) >= {"opened", "synchronize", "reopened", "edited"}


def test_the_checks_that_take_the_body_are_in_the_kept_set():
    """Brief #216 answer 2: every step with `--body` runs on an edited description."""
    for name, block in steps(workflow("governance.yml")).items():
        if "--body" in block or "PR_BODY" in block:
            assert name in BODY_STEPS, name


# --- the router on comments (answer 5) -----------------------------------------------------------

PREFIXES = ("Verdict:", "Approve:", "Approval:", "Correction:")


def router_condition() -> str:
    return workflow("agk-route.yml").split("    if: ", 1)[1].split("\n", 1)[0]


def runs_for(event: str, body: str | None = None) -> bool:
    """The job-level `if` evaluated by hand on a saved event: the first line starts a prefix."""
    cond = router_condition()
    prefixes = re.findall(r"startsWith\(github\.event\.comment\.body, '([^']+)'\)", cond)
    assert tuple(prefixes) == PREFIXES
    return event != "issue_comment" or any((body or "").startswith(p) for p in prefixes)


@pytest.mark.parametrize(
    "body",
    [
        "Verdict: cleared abc1234",
        "Approve: abc1234 SPEC-0001",
        "Approval: SPEC-0001 docs/specs/x.md Draft -> Approved",
        "Correction: a; b",
    ],
)
def test_the_router_runs_for_a_comment_that_can_change_a_state(body):
    """Brief #216 answer 5."""
    assert runs_for("issue_comment", body)


@pytest.mark.parametrize(
    "body",
    [
        "Report: abc1234 pushed",
        "Question: Q-1 why",
        "taken: builder-c 2026-10-25",
        "a note",
        " Verdict: x",
        "verdict: cleared x",
        "",
    ],
)
def test_the_router_starts_no_job_for_a_comment_that_changes_no_state(body):
    """Brief #216 answer 5: reports, questions and notes."""
    assert not runs_for("issue_comment", body)


def test_the_router_still_runs_for_the_other_events():
    """Brief #216 answer 5: pull request, workflow run and push are not comments."""
    for event in ("pull_request", "workflow_run", "push"):
        assert runs_for(event)
    assert (
        "github.event_name != 'push' || github.ref_name == github.event.repository.default_branch"
        in router_condition()
    )


def test_the_router_keeps_its_triggers_and_permissions():
    """Brief #216: only the job's `if` changes."""
    assert re.search(r"issue_comment:\n    types: \[created\]", workflow("agk-route.yml"))
    assert "permissions:\n  contents: read\n  pull-requests: write" in workflow("agk-route.yml")
