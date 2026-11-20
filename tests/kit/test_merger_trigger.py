"""The merger starts only when a pull request can merge (brief #1116, ADR-0476; REQ-039).

A finished `governance` or `proof` run no longer starts the merger job: the router, when it labels a
pull request `agk:merge-ready` (cleared and checks green), starts `merger.yml` once for it with
`workflow_dispatch` and the input `pr`. The router runs with a `gh` stub over saved answers and the
workflow files are read as text; invented data, no network.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from test_route import HEAD, REPO, REPO_INFO, proj, run_router, said, stub  # noqa: F401

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
sys.path.insert(0, str(SCRIPTS))

import merge_cleared  # noqa: E402
import route  # noqa: E402

ON = 'default_branch = "main"\n\n[flow]\nauto_merge = true\nauto_merge_method = "squash"\n'
DISPATCH = f"repos/{REPO}/actions/workflows/merger.yml/dispatches"


def turn_on(root: Path, text: str = ON) -> None:
    (root / "agk.toml").write_text(text, encoding="utf-8")


def cleared_pull(stub, labels=("agk:ci-running",), verdict: str = "cleared") -> None:  # noqa: F811
    stub.pull(7, labels=list(labels))
    body = f"Verdict: {verdict} {HEAD[:7]}" + ("\n\n1. do this" if verdict == "fix list" else "")
    stub.serve("issues/7/comments", [said(1, "boss", body)])
    stub.open_list([7])


def finished_run() -> dict:
    run = {"head_branch": "feature", "head_sha": HEAD, "pull_requests": [{"number": 7}]}
    return {"workflow_run": run, "repository": REPO_INFO}


def dispatches(stub) -> list[list]:  # noqa: F811
    return [w for w in stub.writes() if w[1] == DISPATCH]


# --- (a) the router starts the merger for a pull request entering agk:merge-ready ---------------


def test_a_pull_request_entering_merge_ready_starts_the_merger_once(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1116 answer 2 (one `workflow_dispatch` with `pr`, on the default branch)."""
    turn_on(proj)
    cleared_pull(stub)
    proc = run_router(proj, stub, tmp_path, "workflow_run", finished_run())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    sent = dispatches(stub)
    assert len(sent) == 1
    assert sent[0][0] == "POST"
    assert "ref=main" in sent[0][2] and "inputs[pr]=7" in sent[0][2]
    assert "#7 merger started" in proc.stdout


@pytest.mark.parametrize(
    ("labels", "verdict"),
    [
        (("agk:merge-ready",), "cleared"),  # already there: started when it entered
        (("agk:ready",), "cleared"),  # the old name of the same state (amendment 150)
        (("agk:ci-running",), "fix list"),  # agk:fix
        (("agk:ci-running",), "rejected"),  # agk:fix
    ],
)
def test_no_other_state_starts_the_merger(proj, stub, tmp_path, labels, verdict):  # noqa: F811
    """REQ-039: brief #1116 answer 6a (for no other state, and not twice)."""
    turn_on(proj)
    cleared_pull(stub, labels=labels, verdict=verdict)
    proc = run_router(proj, stub, tmp_path, "workflow_run", finished_run())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert dispatches(stub) == []


def test_a_head_without_a_verdict_starts_nothing(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1116 answer 6a (agk:review)."""
    turn_on(proj)
    stub.pull(7, labels=["agk:ci-running"])
    run_router(proj, stub, tmp_path, "workflow_run", finished_run())
    assert dispatches(stub) == []


def test_auto_merge_off_starts_nothing(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1116 answer 2 (a project without the merger spends no minute on it)."""
    cleared_pull(stub)
    run_router(proj, stub, tmp_path, "workflow_run", finished_run())
    assert dispatches(stub) == []
    turn_on(proj, ON.replace('"main"\n', '"main"\nexecution = "local"\n', 1))
    run_router(proj, stub, tmp_path, "workflow_run", finished_run())
    assert dispatches(stub) == []


def test_a_comment_the_merger_starts_on_itself_starts_no_second_run(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1116 answer 2 (the `Verdict:` comment path stays and is not doubled)."""
    turn_on(proj)
    cleared_pull(stub)
    note = {"body": f"Verdict: cleared {HEAD[:7]}"}
    event = {
        "action": "created",
        "issue": {"number": 7, "pull_request": {}},
        "comment": note,
        "repository": REPO_INFO,
    }
    run_router(proj, stub, tmp_path, "issue_comment", event)
    assert dispatches(stub) == []


def test_another_comment_that_makes_it_merge_ready_starts_the_merger(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1116 answer 2 (a `Report:` the merger does not start on)."""
    turn_on(proj)
    cleared_pull(stub)
    event = {
        "action": "created",
        "issue": {"number": 7, "pull_request": {}},
        "comment": {"body": "Report: abc ready for review"},
        "repository": REPO_INFO,
    }
    run_router(proj, stub, tmp_path, "issue_comment", event)
    assert len(dispatches(stub)) == 1


def test_the_sweep_of_a_stale_label_starts_the_merger_too(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1116 answer 2 (a lost wake: the router's own sweep of agk:ci-running)."""
    turn_on(proj)
    cleared_pull(stub)
    stub.pull(8, labels=["agk:review"])
    stub.serve(
        "pulls", [{"number": 7, "head": {"sha": HEAD}, "labels": [{"name": "agk:ci-running"}]}]
    )
    run = {"head_branch": "feature", "head_sha": HEAD, "pull_requests": [{"number": 8}]}
    run_router(proj, stub, tmp_path, "workflow_run", {"workflow_run": run, "repository": REPO_INFO})
    sent = dispatches(stub)
    assert len(sent) == 1 and "inputs[pr]=7" in sent[0][2]


def test_a_person_routing_by_hand_starts_nothing(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1116 answer 2 (only the router's event job starts the merger)."""
    turn_on(proj)
    cleared_pull(stub)
    run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7")
    run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--all")
    assert dispatches(stub) == []


def test_a_refused_start_keeps_the_label_and_the_exit(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1116 answer 2 (a token without `actions: write`: the sweep still merges)."""
    turn_on(proj)
    cleared_pull(stub)
    script = (stub.bin / "gh").read_text(encoding="utf-8")
    refuse = 'if method != "GET" and endpoint.endswith("/dispatches"):\n'
    refuse += '    sys.stderr.write("gh: Resource not accessible by integration (HTTP 403)\\n")\n'
    refuse += "    sys.exit(1)\n"
    script = script.replace('if method != "GET":\n', refuse + 'if method != "GET":\n', 1)
    (stub.bin / "gh").write_text(script, encoding="utf-8")
    proc = run_router(proj, stub, tmp_path, "workflow_run", finished_run())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "merger: not started for #7" in proc.stdout
    assert "skipped (read-only token)" not in proc.stdout
    adds = [w for w in stub.writes() if w[1].endswith("/issues/7/labels")]
    assert adds and "labels[]=agk:merge-ready" in adds[0][2]


def test_the_merger_reads_the_dispatched_pull_request():
    """REQ-039: brief #1116 answer 2 (the input `pr` names the target; its head is read later)."""
    assert merge_cleared.event_target("workflow_dispatch", {"inputs": {"pr": "7"}}) == (7, None)
    for bad in ({"inputs": {"pr": ""}}, {"inputs": {"pr": "0"}}, {"inputs": {"pr": "x"}}, {}):
        assert merge_cleared.event_target("workflow_dispatch", bad) is None


def test_the_router_names_the_merger_workflow():
    """REQ-039: brief #1116 answer 2."""
    assert route.MERGER_WORKFLOW == "merger.yml"


# --- (b) the workflow texts -----------------------------------------------------------------------


def text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def job_if(name: str, job: str) -> str:
    body = re.search(rf"\n  {job}:\n(.*?)(?=\n  [a-z][a-z_-]*:\n|\Z)", text(name), re.S).group(1)
    return next(ln for ln in body.splitlines() if ln.startswith("    if: "))


def test_a_plain_finished_run_no_longer_starts_the_merger_job():
    """REQ-039: brief #1116 answer 6b (the `if:` of the merger job)."""
    line = job_if("merger.yml", "merger")
    assert "github.event.workflow_run.event == 'pull_request'" not in line
    assert "github.event.workflow_run.conclusion == 'success'" not in line
    # what stays: a failed merge queue run (brief #972) and the new dispatch with `pr`
    assert "github.event.workflow_run.event == 'merge_group'" in line
    assert "(github.event_name == 'workflow_dispatch' && github.event.inputs.pr != '')" in line


def test_a_plain_finished_run_no_longer_sweeps():
    """REQ-039: brief #1116 answer 6b (the `if:` of the sweep's gate)."""
    line = job_if("merger.yml", "sweep-gate")
    assert "workflow_run" not in line
    assert "github.event_name == 'schedule'" in line
    assert "(github.event_name == 'workflow_dispatch' && github.event.inputs.pr == '')" in line


def test_the_dispatch_takes_the_input_pr_and_groups_by_it():
    """REQ-039: brief #1116 answer 2 (one group per pull request, as for its comments)."""
    head = text("merger.yml").split("\njobs:", 1)[0]
    assert re.search(
        r"\n  workflow_dispatch:\n    inputs:\n      pr:\n"
        r"(?:        .*\n)*?        required: false\n",
        head,
    )
    assert "github.event.issue.number || github.event.inputs.pr ||" in head


def test_the_router_may_start_a_workflow():
    """REQ-039: brief #1116 answer 2 (`actions: write`, the one new permission)."""
    head = text("agk-route.yml").split("\njobs:", 1)[0]
    assert re.search(r"^  actions: write$", head, re.M)


# --- (c) the merger runs on triggers; the schedule stays only for what nothing else starts ------
# Brief #1143 answer 2: a review of every start found three paths that only the schedule covers,
# so the schedule stays (ADR-0485): (1) a start the router's token is refused (`start_merger`
# prints one line and the label stays, see the test above); (2) a merger run that ends without a
# merge (a GitHub error, an environment wait past the job's limit) on a pull request whose label
# does not change, so no router run starts it again; (3) the conductor's `SWEEP late` signal,
# which counts finished sweep runs of merger.yml (`conductor.SWEEP_EVENTS`).


def test_1143_the_schedule_stays_for_the_three_paths_only_it_covers():
    """REQ-039: brief #1143 answer 3e (the workflow keeps `schedule:`; the test names the paths)."""
    import conductor

    head = text("merger.yml").split("\njobs:", 1)[0]
    assert '\n  schedule:\n    - cron: "*/15 * * * *"\n' in head  # paths (1), (2) and (3)
    assert "\n  workflow_dispatch:\n" in head  # a sweep by hand
    assert "schedule" in conductor.SWEEP_EVENTS  # path (3)
    assert "the merger's schedule still sweeps" in " ".join(route.__doc__.split())  # path (1)


def test_1143_the_router_documents_the_start_on_a_green_branch():
    """REQ-039: brief #1143 answer 1 (the router's docstring names the new trigger)."""
    doc = " ".join(route.__doc__.split())
    assert "Brief #1143 (ADR-0485)" in doc
    assert "turns green" in doc


# --- brief #1554 (ADR-0654): the merger starts only where it can act ------------------------------

OFF = {"AGK_MERGER": "off"}


def merger_if() -> str:
    from test_ci_saving import job_conditions

    return job_conditions(text("merger.yml"))[0]


def gate_if() -> str:
    from test_ci_saving import job_conditions

    return job_conditions(text("merger.yml"))[1]


def test_1554_the_merger_starts_on_exactly_the_lines_its_reader_holds():
    """REQ-039: brief #1554 answer 5 (the trigger list and the reader's list are one list)."""
    from test_route_triggers import COMMENT_LINE, acting_lines

    cond = merger_if()
    assert acting_lines(cond, "created") == set(merge_cleared.MERGER_CREATED)
    assert acting_lines(cond, "edited") == set(merge_cleared.MERGER_EDITED)
    assert set(COMMENT_LINE.findall(cond)) == (
        set(merge_cleared.MERGER_CREATED) | set(merge_cleared.MERGER_EDITED)
    )
    assert set(route.MERGER_STARTS) == set(merge_cleared.MERGER_CREATED)  # the router's reading


@pytest.mark.parametrize(
    "line",
    ["Progress:", "Tell:", "Conductor:", "Slot:", "Report:", "Question:", "Answer:", "taken:"],
)
def test_1554_a_session_line_starts_no_merger(line):
    """REQ-039: brief #1554 answer 5 (only the merge lines start the merger's job)."""
    from test_ci_saving import holds
    from test_route_triggers import comment_on

    for action in ("created", "edited"):
        assert not holds(merger_if(), comment_on(f"{line} x", action)), (line, action)


def test_1554_the_merger_chain_listens_only_to_the_merge_queue():
    """REQ-039: brief #1554 answer 2 (`branches` on the merger's `workflow_run`; verify it)."""
    head = text("merger.yml").split("\njobs:", 1)[0]
    chain = head.split("\n  workflow_run:\n", 1)[1].split("\n  status:", 1)[0]
    assert chain.splitlines() == [
        "    workflows: [governance, proof]",
        "    types: [completed]",
        "    branches: ['gh-readonly-queue/**']",
    ]


def github_glob(pattern: str, name: str) -> bool:
    """GitHub's branch filter as its documentation reads it: `**` any text, `*` any but `/`."""
    parts = re.split(r"(\*\*|\*)", pattern)
    rx = "".join({"**": ".*", "*": "[^/]*"}.get(p, re.escape(p)) for p in parts)
    return re.fullmatch(rx, name) is not None


@pytest.mark.parametrize(
    ("branch", "event", "starts"),
    [
        ("gh-readonly-queue/main/pr-7-" + "0123456789abcdef" * 2 + "01234567", "merge_group", True),
        ("feat/x", "pull_request", False),
        ("main", "push", False),
    ],
)
def test_1554_only_a_failed_queue_run_passes_the_filter_and_reaches_the_report(
    branch, event, starts
):
    """REQ-039: brief #1554 answers 2 and 8 (the filter's `**` takes the slashes of a queue
    branch; a finished run of another branch makes no merger run at all)."""
    from test_ci_saving import holds

    pattern = re.search(r"branches: \['([^']+)'\]", text("merger.yml")).group(1)
    assert github_glob(pattern, branch) is starts
    run = {"event": event, "conclusion": "failure", "head_branch": branch}
    github = {"event_name": "workflow_run", "event": {"workflow_run": run}}
    assert holds(merger_if(), github, OFF) is starts  # the variable never gates the report
    assert holds(merger_if(), github) is starts


@pytest.mark.parametrize("body", ["Verdict: cleared abc1234", "Approve: abc1234 SPEC-0001"])
def test_1554_the_variable_off_keeps_the_merger_job_from_a_comment(body):
    """REQ-039: brief #1554 answers 4 and 8 (with it unset, or any other value, as before)."""
    from test_ci_saving import holds
    from test_route_triggers import comment_on

    event = comment_on(body)
    assert holds(merger_if(), event)
    assert holds(merger_if(), event, {"AGK_MERGER": "on"})
    assert not holds(merger_if(), event, OFF)
    edited = comment_on("Final: docs/adr/0001-x.md Proposed -> Accepted", "edited")
    assert holds(merger_if(), edited) and not holds(merger_if(), edited, OFF)


def test_1554_the_variable_off_keeps_the_scheduled_gate_from_starting():
    """REQ-039: brief #1554 answer 4 (a sweep by hand and the dispatch with `pr` stay)."""
    from test_ci_saving import holds

    schedule = {"event_name": "schedule", "event": {}}
    by_hand = {"event_name": "workflow_dispatch", "event": {"inputs": {"pr": ""}}}
    dispatch = {"event_name": "workflow_dispatch", "event": {"inputs": {"pr": "7"}}}
    status = {"event_name": "status", "event": {"context": "agk/verdict", "state": "success"}}
    assert holds(gate_if(), schedule) and not holds(gate_if(), schedule, OFF)
    assert holds(gate_if(), by_hand, OFF)
    for github in (dispatch, status):
        assert holds(merger_if(), github, OFF), github["event_name"]


def test_1554_the_router_dispatches_the_merger_when_the_variable_is_off(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1554 answer 8 (`Verdict: cleared <sha>` with `AGK_MERGER = off`: the router
    alone starts, and it dispatches the merger once, so no merge is lost)."""
    turn_on(proj)
    cleared_pull(stub)
    note = {"body": f"Verdict: cleared {HEAD[:7]}"}
    event = {
        "action": "created",
        "issue": {"number": 7, "pull_request": {}},
        "comment": note,
        "repository": REPO_INFO,
    }
    proc = run_router(proj, stub, tmp_path, "issue_comment", event, AGK_MERGER="off")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(dispatches(stub)) == 1
    assert route.merger_starts_itself("issue_comment", event)  # unset: the merger starts itself


def test_1554_merger_starts_itself_reads_the_variable(monkeypatch):
    """REQ-039: brief #1554 answer 4 (`route.merger_starts_itself` is false when it is `off`)."""
    event = {"action": "created", "comment": {"body": "Verdict: cleared abc1234"}}
    monkeypatch.delenv("AGK_MERGER", raising=False)
    assert route.merger_starts_itself("issue_comment", event)
    monkeypatch.setenv("AGK_MERGER", "on")
    assert route.merger_starts_itself("issue_comment", event)
    monkeypatch.setenv("AGK_MERGER", "off")
    assert not route.merger_starts_itself("issue_comment", event)


# brief #1554 answers 3, 5 and 8 for the router: here, beside the module's other `route` readers


def test_1554_the_router_starts_on_exactly_the_lines_its_reader_holds():
    """REQ-039: brief #1554 answer 5 (the trigger list and the reader's list are one list)."""
    from test_ci_saving import router_condition
    from test_route_triggers import COMMENT_LINE, acting_lines

    cond = router_condition()
    assert acting_lines(cond, "created") == set(route.ROUTER_CREATED)
    assert acting_lines(cond, "edited") == set(route.ROUTER_EDITED)
    assert set(COMMENT_LINE.findall(cond)) == set(route.ROUTER_CREATED) | set(route.ROUTER_EDITED)
    # every owner answer the router unparks on starts it (the gap `Answer:` was, brief #1534 Q-4)
    assert set(route.OWNER_ANSWER_LINES) <= set(route.ROUTER_CREATED)


def test_1554_answer_wakes_the_router_when_created_only():
    """REQ-039: brief #1554 answers 3 and 8 (`Answer:` created starts it; edited does not)."""
    from test_ci_saving import holds, router_condition
    from test_route_triggers import comment_on

    cond = router_condition()
    assert "Answer:" in route.ROUTER_CREATED and "Answer:" not in route.ROUTER_EDITED
    assert holds(cond, comment_on("Answer: Q-1-1 the evidence settles it"))
    assert not holds(cond, comment_on("Answer: Q-1-1 the evidence settles it", "edited"))


@pytest.mark.parametrize(
    "line", ["Owner needed:", "Maintainer answer:", "Answer:", "Report:", "Question:"]
)
def test_1554_an_edited_ask_or_answer_starts_no_router(line):
    """REQ-039: brief #1554 answer 8 (an edited ask, answer or report starts none, as today)."""
    from test_ci_saving import holds, router_condition
    from test_route_triggers import comment_on

    assert line not in route.ROUTER_EDITED
    assert not holds(router_condition(), comment_on(f"{line} x", "edited"))


def test_1554_an_owner_line_under_another_first_line_starts_and_unparks_nothing():
    """REQ-039: brief #1554 answer 8 (the owner's line must lead the comment)."""
    from test_ci_saving import holds, router_condition
    from test_route_triggers import comment_on

    event = comment_on("Thanks\nMaintainer answer: yes")
    assert not holds(router_condition(), event)
    payload = {**event["event"], "issue": {"number": 7, "pull_request": {}}}
    assert not route.owner_answer_event("issue_comment", payload)
    payload["comment"] = {"body": "Maintainer answer: yes\nThanks"}
    assert route.owner_answer_event("issue_comment", payload)
