"""The router reads local evidence in local mode (brief #1212, ADR-0513; SPEC-0032 rule 2; REQ-039).

While the one open local-mode record issue exists, a required check of the head that never
reported is satisfied by the `Evidence:` line of the builder's newest `Report:` on that head, and
failed when that report records a failed step; it never makes the head `agk:ci-running`.
`agk:merge-ready` additionally needs the verdict's `Local evidence:` and `Evidence check: agrees`
for the head, read as `merge_cleared.py` reads them. Without the record issue nothing changes.
Saved responses as facts; invented data; no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_route import REPO, run_router
from test_route import Stub as RouteStub
from test_route import proj as route_proj  # noqa: F401  (the fixtures of test_route)
from test_route import stub as route_stub  # noqa: F401

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import route  # noqa: E402
from test_route_latest import HEAD, facts, run  # noqa: E402

OLD = "0f1e2d3c4b5a69788796a5b4c3d2e1f001234567"
REQUIRED = ["proof", "governance"]
RECORD = {"number": 90, "title": "Local mode since 2026-11-14", "body": "Actions is blocked."}


def said(cid: int, who: str, body: str) -> dict:
    return {
        "id": cid,
        "user": {"login": who},
        "body": body,
        "created_at": f"2026-11-14T05:{cid:02d}:00Z",
    }


def evidence(head: str = HEAD, record: str = "abcdefabcdef") -> str:
    return f"Evidence: prepush schema 1, head {head[:12]}, 6 steps ok, record {record}"


def report(cid: int, head: str = HEAD, *extra: str) -> dict:
    lines = [f"Report: {head[:7]} ready for review", "", *extra, "Usage: not shown"]
    return said(cid, "builder", "\n".join(lines))


def cleared(cid: int, *extra: str) -> dict:
    return said(cid, "boss", "\n".join([f"Verdict: cleared {HEAD[:7]}", "", *extra]))


def local(comments: list[dict], checks: list[dict] | None = None, on: bool = True) -> dict:
    f = facts(checks or [])
    f.update(
        {
            "comments": comments,
            "required": REQUIRED,
            "body": "Brief: #77\n",
            "local": on,
        }
    )
    return f


AGREES = (
    f"Evidence check: agrees, head {HEAD[:12]}, record abcdefabcdef, governance ok, sample 1 of 6"
)
LOCAL_LINE = f"Local evidence: {HEAD} Evidence check: agrees (conductor's run); tests 9 passed"


# --- (a) to (d): the record issue is open --------------------------------------------------------


def test_a_report_with_matching_evidence_and_no_check_runs_is_review():
    """REQ-039: (a) local evidence stands in for the checks that never reported."""
    assert route.decide(local([report(1, HEAD, evidence())])) == "agk:review"


def test_a_report_without_evidence_is_never_ci_running_in_local_mode():
    """REQ-039: no check ever reports, so `agk:ci-running` would never end (Q-1212-2)."""
    label = route.decide(local([report(1)]))
    assert label != "agk:ci-running"
    assert label == "agk:build"


def test_evidence_naming_another_head_does_not_satisfy_the_checks():
    """REQ-039: an `Evidence:` line of an older head is no evidence."""
    assert route.decide(local([report(1, HEAD, evidence(OLD))])) == "agk:build"


def test_only_the_newest_report_on_the_head_counts():
    """REQ-039: a later report without evidence replaces an earlier one with it."""
    comments = [report(1, HEAD, evidence()), report(2)]
    assert route.decide(local(comments)) == "agk:build"
    comments = [report(1), report(2, HEAD, evidence())]
    assert route.decide(local(comments)) == "agk:review"


def test_a_report_by_another_author_is_not_the_builders_evidence():
    """REQ-039: only the pull request's author gives builder evidence."""
    other = said(1, "someone", f"Report: {HEAD[:7]} ready for review\n\n{evidence()}")
    assert route.decide(local([report(0), other])) == "agk:build"


@pytest.mark.parametrize(
    "failed", ["prepush: stopped at tests; nothing after it ran", "failed: step tests exited 1"]
)
def test_b_evidence_that_records_a_failed_step_is_ci_red(failed):
    """REQ-039: (b) a failed step of the local run is a red check."""
    assert route.decide(local([report(1, HEAD, evidence(), failed)])) == "agk:ci-red"


def test_a_reported_red_check_still_blocks_in_local_mode():
    """REQ-039: session rule 30, a red check still blocks."""
    checks = [run("governance", 5, "failure")]
    assert route.decide(local([report(1, HEAD, evidence())], checks)) == "agk:ci-red"


def test_a_reported_check_still_running_stays_ci_running():
    """REQ-039: only checks that never reported are read from the evidence."""
    checks = [run("governance", 5, None)]
    assert route.decide(local([report(1, HEAD, evidence())], checks)) == "agk:ci-running"


def test_c_cleared_verdict_with_evidence_check_agrees_is_merge_ready():
    """REQ-039: (c) the merger's local evidence, read as merge_cleared.py reads it."""
    comments = [report(1, HEAD, evidence()), cleared(2, LOCAL_LINE, AGREES)]
    assert route.decide(local(comments)) == "agk:merge-ready"


def test_d_evidence_check_differs_is_not_merge_ready():
    """REQ-039: (d) a check that differs holds the merge."""
    differs = AGREES.replace("agrees", "differs")
    comments = [report(1, HEAD, evidence()), cleared(2, LOCAL_LINE, differs)]
    label = route.decide(local(comments))
    assert label != "agk:merge-ready"
    assert label == "agk:review"


def test_d_differs_answered_by_a_maintainer_is_merge_ready_as_the_merger_reads_it():
    """REQ-039: the same answer that lets `merge_cleared.py` merge."""
    differs = AGREES.replace("agrees", "differs")
    answer = said(3, "maintainer", f"Maintainer answer: accept {HEAD}")
    comments = [report(1, HEAD, evidence()), cleared(2, LOCAL_LINE, differs), answer]
    assert route.decide(local(comments)) == "agk:merge-ready"


def test_d_an_evidence_check_of_a_stale_head_is_not_merge_ready():
    """REQ-039: (d) the check must name the current head."""
    stale = AGREES.replace(HEAD[:12], OLD[:12])
    comments = [report(1, HEAD, evidence()), cleared(2, LOCAL_LINE, stale)]
    assert route.decide(local(comments)) == "agk:review"


def test_d_a_cleared_verdict_without_the_local_evidence_line_is_not_merge_ready():
    """REQ-039: the verdict must name the local evidence it relied on."""
    comments = [report(1, HEAD, evidence()), cleared(2, AGREES)]
    assert route.decide(local(comments)) == "agk:review"


# --- (e): no record issue -----------------------------------------------------------------------


def test_e_without_the_record_issue_missing_checks_are_ci_running_as_today():
    """REQ-039: (e) today's behaviour, unchanged."""
    assert route.decide(local([report(1, HEAD, evidence())], on=False)) == "agk:ci-running"
    f = local([report(1, HEAD, evidence())])
    del f["local"]
    assert route.decide(f) == "agk:ci-running"


def test_e_without_the_record_issue_a_cleared_green_head_is_merge_ready_without_evidence():
    """REQ-039: (e) CI mode reads check runs as today."""
    checks = [run("proof", 1), run("governance", 2)]
    comments = [report(1), cleared(2)]
    assert route.decide(local(comments, checks, on=False)) == "agk:merge-ready"


# --- the record issue is read from GitHub -------------------------------------------------------


def test_record_open_reads_the_open_issues(monkeypatch):
    """REQ-039: the one open local-mode record issue, as merge_cleared.py finds it."""
    route.RECORD_OPEN.clear()
    monkeypatch.setattr(route, "pages", lambda endpoint: [RECORD])
    assert route.record_open("o/r") is True
    route.RECORD_OPEN.clear()
    pull = {**RECORD, "pull_request": {}}
    monkeypatch.setattr(route, "pages", lambda endpoint: [pull, {"title": "Other"}])
    assert route.record_open("o/r") is False
    route.RECORD_OPEN.clear()
    monkeypatch.setattr(route, "pages", lambda endpoint: None)
    assert route.record_open("o/r") is False  # unreadable: today's behaviour
    route.RECORD_OPEN.clear()


def test_record_open_is_read_once_per_run(monkeypatch):
    """REQ-039: `--all` reads the open issues once, not once per pull request."""
    route.RECORD_OPEN.clear()
    seen: list[str] = []
    monkeypatch.setattr(route, "pages", lambda endpoint: seen.append(endpoint) or [RECORD])
    assert route.record_open("o/r") and route.record_open("o/r")
    assert len(seen) == 1 and seen[0].startswith("repos/o/r/issues?state=open")
    route.RECORD_OPEN.clear()


@pytest.fixture
def stub(request) -> RouteStub:
    return request.getfixturevalue("route_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("route_proj")


def test_route_pr_in_local_mode_labels_review_from_the_evidence(stub, proj, tmp_path):
    """REQ-039: `route.py --pr N` with the person's own gh: no check runs, the record issue open."""
    stub.pull(7, labels=("agk:ci-running",))
    stub.serve("pulls/7", {**stub.fixtures[f"repos/{REPO}/pulls/7"], "body": "Brief: #77\n"})
    stub.serve(f"commits/{HEAD}/check-runs", {"total_count": 0, "check_runs": []})
    body = f"Report: {HEAD[:7]} ready for review\n\n{evidence()}\nUsage: not shown"
    stub.serve("issues/7/comments", [said(1, "builder", body)])
    stub.serve("issues", [RECORD])
    result = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "#7 agk:review" in result.stdout
    stub.serve("issues", [])
    result = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert "#7 agk:ci-running" in result.stdout  # (e) no record issue: as today
