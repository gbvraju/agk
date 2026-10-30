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
    """Brief #216 answer 1: a body cannot change a test (brief #283: a draft made ready runs)."""
    types = {"opened", "synchronize", "reopened", "ready_for_review"}
    assert types_of(workflow("proof.yml")) == types


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
        if name in BODY_STEPS or name.startswith("uses: actions/") or name == "Paused":
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


# --- a draft's push starts two jobs, not five (brief #369, ADR-0207) -----------------------------
#
# GitHub bills every job as at least one whole minute. The jobs an event starts are read from the
# workflow files: the `on:` triggers, each job's `if:` (evaluated by hand on a saved event), and the
# router's `workflow_run` wake for each finished governance or proof run (a run whose every job was
# skipped concludes `skipped`).

KIT = ("governance.yml", "proof.yml", "agk-route.yml")


class Ctx:
    """A payload read by attribute, as a GitHub expression reads it; a missing key is empty."""

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key: str):
        value = self.data.get(key) if isinstance(self.data, dict) else None
        return Ctx(value) if isinstance(value, dict) or value is None else value

    def __bool__(self) -> bool:
        return bool(self.data)

    def __eq__(self, other) -> bool:
        return isinstance(other, Ctx) and self.data == other.data

    def __ne__(self, other) -> bool:
        return not self == other

    def __hash__(self) -> int:
        return 0


def starts_with(text, prefix) -> bool:
    return isinstance(text, str) and text.startswith(prefix)


def holds(condition: str, github: dict) -> bool:
    """A job-level `if:` of these workflows, evaluated on one event (a test reading, not GitHub)."""
    expr = condition.strip().removeprefix("${{").removesuffix("}}").strip()
    expr = expr.replace("||", " or ").replace("&&", " and ")
    expr = re.sub(r"!(?!=)", " not ", expr)
    expr = re.sub(r"\btrue\b", "True", re.sub(r"\bfalse\b", "False", expr))
    expr = expr.replace("startsWith(", "starts_with(")
    names = {"github": Ctx(github), "starts_with": starts_with}
    return bool(eval(expr, {"__builtins__": {}}, names))  # nosec B307 - the kit's own workflow text


def triggers(text: str) -> dict[str, dict[str, list[str]]]:
    """`on:` of a workflow: each event and its `types:` and `workflows:` lists."""
    block = text.split("\non:\n", 1)[1].split("\n\n", 1)[0]
    found: dict[str, dict[str, list[str]]] = {}
    event = ""
    for line in block.splitlines():
        top = re.match(r"^  ([a-z_]+):\s*$", line)
        if top:
            event = top.group(1)
            found[event] = {}
            continue
        key = re.match(r"^    (types|workflows): \[([^\]]*)\]", line)
        if key and event:
            found[event][key.group(1)] = [x.strip() for x in key.group(2).split(",")]
    return found


def job_conditions(text: str) -> list[str]:
    """The job-level `if:` of each job (always true when a job has none)."""
    jobs = text.split("\njobs:\n", 1)[1]
    out = []
    for block in re.split(r"(?m)^  (?=[a-z][\w-]*:\n)", jobs)[1:]:
        cond = re.search(r"(?m)^    if: (.+)$", block)
        out.append(cond.group(1) if cond else "true")
    return out


def started(text: str, github: dict) -> int:
    on = triggers(text).get(github["event_name"])
    if on is None:
        return 0
    action = github["event"].get("action")
    if "types" in on and action not in on["types"]:
        return 0
    if github["event_name"] == "workflow_run":
        if github["event"]["workflow_run"]["name"] not in on.get("workflows", []):
            return 0
    return sum(holds(c, github) for c in job_conditions(text))


def name_of(text: str) -> str:
    found = re.search(r"(?m)^name: (.+)$", text)
    assert found
    return found.group(1).strip()


def pr_event(action: str, draft: bool) -> dict:
    pull = {"number": 7, "draft": draft, "merged": False}
    return {
        "event_name": "pull_request",
        "ref_name": "7/merge",
        "event": {"action": action, "pull_request": pull, "repository": {"default_branch": "main"}},
    }


def comment_event(body: str) -> dict:
    issue = {"number": 7, "pull_request": {"url": "x"}}
    event = {"action": "created", "comment": {"body": body}, "issue": issue}
    event["repository"] = {"default_branch": "main"}
    return {"event_name": "issue_comment", "ref_name": "main", "event": event}


def jobs_started(github: dict) -> dict[str, int]:
    """The jobs one event starts, by workflow, the router's wakes counted under `agk-route wake`."""
    texts = {n: workflow(n) for n in KIT}
    count = {n: started(texts[n], github) for n in KIT}
    count["agk-route wake"] = 0
    for name in ("governance.yml", "proof.yml"):
        if triggers(texts[name]).get(github["event_name"]) is None:
            continue
        on = triggers(texts[name])[github["event_name"]]
        if "types" in on and github["event"].get("action") not in on["types"]:
            continue
        run = {"name": name_of(texts[name]), "conclusion": "success" if count[name] else "skipped"}
        wake = {
            "event_name": "workflow_run",
            "ref_name": "main",
            "event": {
                "action": "completed",
                "workflow_run": {**run, "pull_requests": [{"number": 7}]},
                "repository": {"default_branch": "main"},
            },
        }
        count["agk-route wake"] += started(texts["agk-route.yml"], wake)
    return count


@pytest.mark.parametrize(
    ("label", "github", "total"),
    [
        ("draft push", pr_event("synchronize", True), 2),
        ("draft edit", pr_event("edited", True), 2),
        ("ready push", pr_event("synchronize", False), 5),
        ("ready edit", pr_event("edited", False), 2),
        ("ready_for_review", pr_event("ready_for_review", False), 4),
        ("verdict comment", comment_event("Verdict: cleared abc1234"), 1),
    ],
)
def test_the_jobs_each_event_starts(label, github, total):
    """REQ-039: brief #369 answer 5 (2, 2, unchanged, 2, unchanged, unchanged)."""
    assert sum(jobs_started(github).values()) == total, (label, jobs_started(github))


def test_a_draft_push_starts_governance_and_its_one_router_wake():
    """REQ-039: brief #369 answers 1 and 2 (proof and the router's own run do not start)."""
    count = jobs_started(pr_event("synchronize", True))
    assert count == {"governance.yml": 1, "proof.yml": 0, "agk-route.yml": 0, "agk-route wake": 1}
    for action in ("opened", "reopened"):
        assert jobs_started(pr_event(action, True))["proof.yml"] == 0, action
        assert jobs_started(pr_event(action, True))["agk-route.yml"] == 0, action


def test_a_ready_pull_request_keeps_every_job():
    """REQ-039: brief #369 answer 3 (a ready push: governance, proof, the router and two wakes)."""
    count = jobs_started(pr_event("synchronize", False))
    assert count == {"governance.yml": 1, "proof.yml": 1, "agk-route.yml": 1, "agk-route wake": 2}
    ready = jobs_started(pr_event("ready_for_review", False))
    assert ready == {"governance.yml": 1, "proof.yml": 1, "agk-route.yml": 0, "agk-route wake": 2}


def test_proof_skips_a_draft_at_job_level():
    """REQ-039: brief #369 answer 1 (`if:` on the job, so no runner starts for a draft)."""
    (condition,) = job_conditions(workflow("proof.yml"))
    assert "github.event.pull_request.draft" in condition
    assert not holds(condition, pr_event("synchronize", True))
    assert holds(condition, pr_event("synchronize", False))
    assert holds(condition, pr_event("ready_for_review", False))


def test_the_router_starts_no_job_for_a_skipped_run_or_a_draft_event():
    """REQ-039: brief #369 answer 2."""
    condition = router_condition()
    assert "github.event.workflow_run.conclusion != 'skipped'" in condition
    assert "github.event.pull_request.draft" in condition
    assert "edited" not in triggers(workflow("agk-route.yml"))["pull_request"]["types"]
    for conclusion, runs in (("skipped", False), ("success", True), ("failure", True)):
        wake = {
            "event_name": "workflow_run",
            "ref_name": "main",
            "event": {
                "workflow_run": {"name": "proof", "conclusion": conclusion},
                "repository": {"default_branch": "main"},
            },
        }
        assert holds(condition, wake) is runs, conclusion


def test_a_merge_and_a_push_to_the_default_branch_still_start_the_router():
    """REQ-039: brief #369 answer 3 (merges and default-branch pushes keep their job)."""
    merged = pr_event("closed", False)
    merged["event"]["pull_request"]["merged"] = True
    assert jobs_started(merged)["agk-route.yml"] == 1
    push = {"event_name": "push", "ref_name": "main", "event": {"repository": {"default_branch": "main"}}}
    assert jobs_started(push)["agk-route.yml"] == 1
    for prefix in PREFIXES:
        assert jobs_started(comment_event(f"{prefix} x"))["agk-route.yml"] == 1, prefix


def test_a_skipped_proof_run_never_reports_green_over_a_failed_run_of_the_same_head():
    """REQ-039: brief #369 answer 5 (route.py ignores a skipped run while the name has another)."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts" / "agk"))
    import route

    failed = {"id": 1, "name": "proof", "status": "completed", "conclusion": "failure"}
    skipped = {"id": 2, "name": "proof", "status": "completed", "conclusion": "skipped"}
    green = {"id": 3, "name": "governance", "status": "completed", "conclusion": "success"}
    assert {r["id"] for r in route.latest_runs([failed, skipped, green])} == {1, 3}
    facts = {
        "head": "a" * 40,
        "mergeable_state": "clean",
        "checks": [green, skipped, failed],
        "statuses": [],
        "comments": [],
        "reviews": [],
        "authors": ["boss"],
        "approvers": ["maintainer"],
        "author": "builder",
        "files": [],
        "commit": {},
    }
    assert route.decide(facts) == "agk:ci-red"


def test_the_workflows_say_why():
    """REQ-039: brief #369 answer 4 (the comments name the brief and the billed minute)."""
    for name in ("proof.yml", "agk-route.yml"):
        head = workflow(name).split("\njobs:\n", 1)[0]
        assert "brief #369" in head, name
        assert "minute" in head, name
