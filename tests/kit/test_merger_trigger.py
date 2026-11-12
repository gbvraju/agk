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
from test_route import HEAD, REPO, REPO_INFO, run_router, said  # noqa: F401
from test_route import proj, stub  # noqa: F401  (fixtures)

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


# --- (a) the router starts the merger for a pull request entering agk:merge-ready ------------------


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
    stub.serve("pulls", [{"number": 7, "head": {"sha": HEAD}, "labels": [{"name": "agk:ci-running"}]}])
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
        r"\n  workflow_dispatch:\n    inputs:\n      pr:\n(?:        .*\n)*?        required: false\n",
        head,
    )
    assert "github.event.issue.number || github.event.inputs.pr ||" in head


def test_the_router_may_start_a_workflow():
    """REQ-039: brief #1116 answer 2 (`actions: write`, the one new permission)."""
    head = text("agk-route.yml").split("\njobs:", 1)[0]
    assert re.search(r"^  actions: write$", head, re.M)
