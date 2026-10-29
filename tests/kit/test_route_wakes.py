"""The router never drops a wake when events arrive together (brief 309; REQ-039, SPEC-0032 rule 1).

Measured on 2026-10-29: two `workflow_run` wakes of one pull request were cancelled by another pull
request's `pull_request` event, because the router used one concurrency group for every event,
and that pull request stayed `agk:ci-running` with green checks. The group is now per pull request,
and each run that labels after checks finish sweeps the open pull requests still labelled
`agk:ci-running` and relabels those whose required checks have all finished, writing only labels.
A `gh` stub serves saved JSON copies of the GitHub responses; no network."""

from __future__ import annotations

import re

import pytest
from test_route import HEAD, REPO, REPO_INFO, ok, run_router, workflow
from test_route import Stub as RouteStub
from test_route import proj as route_proj  # noqa: F401  (the fixtures of test_route)
from test_route import stub as route_stub  # noqa: F401


@pytest.fixture
def stub(request) -> RouteStub:
    return request.getfixturevalue("route_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("route_proj")


OTHER = "b" * 40
THIRD = "c" * 40


def running(name: str) -> dict:
    return {"name": name, "status": "in_progress", "conclusion": None}


def pull_at(stub, n: int, head: str, labels=(), checks=None) -> None:
    """A pull request at its own head, with its own check runs (green by default)."""
    stub.fixtures[f"repos/{REPO}/pulls/{n}"] = {
        "number": n, "state": "open", "merged_at": None, "mergeable_state": "clean",
        "user": {"login": "builder"}, "head": {"sha": head},
        "labels": [{"name": name} for name in labels],
    }  # fmt: skip
    runs = checks if checks is not None else [ok("governance"), ok("proof")]
    stub.serve(f"commits/{head}/check-runs", {"total_count": len(runs), "check_runs": runs})
    stub.serve(f"commits/{head}/status", {"statuses": []})
    stub.serve(f"commits/{head}", {"sha": head, "parents": [], "files": []})
    for kind in ("issues/%d/comments", "pulls/%d/reviews", "pulls/%d/files"):
        stub.fixtures.setdefault(f"repos/{REPO}/{kind % n}", [])


def listing(stub, rows: list[tuple[int, str, tuple[str, ...]]]) -> None:
    stub.fixtures[f"repos/{REPO}/pulls"] = [
        {"number": n, "head": {"sha": h}, "state": "open", "labels": [{"name": x} for x in labels]}
        for n, h, labels in rows
    ]


def touched(stub) -> set[str]:
    return {w[1].split("/")[4] for w in stub.writes() if "/issues/" in w[1]}


def finished(head: str, numbers: list[int]) -> dict:
    run = {
        "head_branch": "feature",
        "head_sha": head,
        "pull_requests": [{"number": n} for n in numbers],
    }
    return {"workflow_run": run, "repository": REPO_INFO}


# --- the sweep (answer 2) -----------------------------------------------------------------------


def test_two_pull_requests_whose_checks_finish_together_both_leave_ci_running(proj, stub, tmp_path):
    """The wake of #8 was lost; the run woken by #7's checks relabels it too."""
    pull_at(stub, 7, HEAD, labels=["agk:ci-running"])
    pull_at(stub, 8, OTHER, labels=["agk:ci-running"])
    listing(stub, [(7, HEAD, ("agk:ci-running",)), (8, OTHER, ("agk:ci-running",))])
    proc = run_router(proj, stub, tmp_path, "workflow_run", finished(HEAD, [7]))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    added = {
        (w[1].split("/")[4], w[2][-1])
        for w in stub.writes()
        if w[0] == "POST" and "/issues/" in w[1] and w[1].endswith("/labels")
    }
    assert added == {("7", "labels[]=agk:review"), ("8", "labels[]=agk:review")}
    removed = {w[1].split("/")[4] for w in stub.writes() if w[0] == "DELETE"}
    assert removed == {"7", "8"}


def test_the_sweep_leaves_a_pull_request_whose_checks_still_run_alone(proj, stub, tmp_path):
    pull_at(stub, 7, HEAD, labels=["agk:ci-running"])
    pull_at(stub, 9, THIRD, labels=["agk:ci-running"], checks=[ok("governance"), running("proof")])
    pull_at(stub, 10, OTHER, labels=["agk:fix"])
    listing(
        stub,
        [
            (7, HEAD, ("agk:ci-running",)),
            (9, THIRD, ("agk:ci-running",)),
            (10, OTHER, ("agk:fix",)),
        ],
    )
    run_router(proj, stub, tmp_path, "workflow_run", finished(HEAD, [7]))
    assert touched(stub) == {"7"}
    assert not any("pulls/10" in c[1] for c in stub.calls())  # only agk:ci-running is swept


def test_the_sweep_writes_only_labels(proj, stub, tmp_path):
    pull_at(stub, 7, HEAD, labels=["agk:review"])
    pull_at(stub, 8, OTHER, labels=["agk:ci-running"])
    bad = {
        "id": 5,
        "user": {"login": "boss"},
        "created_at": "2026-10-29T10:00:00Z",
        "body": f"Verdict: fix list {OTHER[:7]}\n\nFinal: nowhere",
    }
    stub.serve("issues/8/comments", [bad])
    listing(stub, [(7, HEAD, ("agk:review",)), (8, OTHER, ("agk:ci-running",))])
    run_router(proj, stub, tmp_path, "workflow_run", finished(HEAD, [7]))
    assert "8" in touched(stub)
    for method, endpoint, _ in stub.writes():
        assert re.search(r"/(issues/\d+/labels(/.+)?|labels)$", endpoint), (method, endpoint)


def test_only_a_run_woken_by_finished_checks_sweeps(proj, stub, tmp_path):
    pull_at(stub, 7, HEAD)
    pull_at(stub, 8, OTHER, labels=["agk:ci-running"])
    listing(stub, [(7, HEAD, ()), (8, OTHER, ("agk:ci-running",))])
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "pull_request", event)
    assert touched(stub) == {"7"}


def test_an_unreadable_list_of_open_pull_requests_fails_the_sweep_naming_the_rule(
    proj, stub, tmp_path
):
    pull_at(stub, 7, HEAD, labels=["agk:ci-running"])
    stub.fixtures[f"repos/{REPO}/pulls"] = "FAIL"
    proc = run_router(proj, stub, tmp_path, "workflow_run", finished(HEAD, [7]))
    assert proc.returncode == 1 and "FAIL route" in proc.stdout and "rule" in proc.stdout
    assert touched(stub) == {"7"}  # the woken pull request is still routed


# --- the workflow (answer 1) ---------------------------------------------------------------------


def test_the_concurrency_group_is_per_pull_request_and_never_cancels_a_running_route():
    text = workflow()
    block = text.split("\nconcurrency:\n", 1)[1].split("\n\n", 1)[0]
    group = re.search(r"^  group: (.+)$", block, re.MULTILINE)
    assert group, block
    value = group.group(1)
    assert value != "agk-route" and value.startswith("agk-route-${{ ")
    order = [
        "github.event.pull_request.number",
        "github.event.issue.number",
        "github.event.workflow_run.head_sha",
        "github.ref",
    ]
    assert [value.index(x) for x in order] == sorted(value.index(x) for x in order), value
    assert "  cancel-in-progress: false" in block
