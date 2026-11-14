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
    monkeypatch.setattr(route, "search_once", lambda endpoint: None)  # 6b: a failed search
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
    monkeypatch.setattr(route, "search_once", lambda endpoint: None)  # 6b: a failed search
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


# --- brief #1263 answers 6, 6b and 7: local mode is decided cheaply -------------------------------

SEARCH = "search/issues"
NOT_LOCAL = f"repos/{REPO}/issues?state=open"
RATE_LIMITED = """#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
endpoint = args[args.index("--method") + 2]
if endpoint.startswith("search/"):
    with open(os.path.join(os.environ["GH_STUB_DIR"], "calls.log"), "a") as log:
        log.write('["GET", "search/issues", []]\\n')
    sys.stderr.write("gh: API rate limit exceeded (HTTP 403)\\n")
    sys.exit(1)
os.execv(sys.executable, [sys.executable, os.path.join(os.path.dirname(__file__), "gh-real")] + args)
"""


def two_pulls(stub: RouteStub) -> None:
    for n in (7, 8):
        stub.pull(n, labels=("agk:review",))  # green checks reported: review in either mode
    stub.open_list([7, 8])


def endpoints(stub: RouteStub) -> list[str]:
    return [call[1] for call in stub.calls() if call[0] == "GET"]


def reads_of_open_issues(stub: RouteStub) -> int:
    return sum(1 for e in endpoints(stub) if e.startswith(NOT_LOCAL))


def searches(stub: RouteStub) -> int:
    return sum(1 for e in endpoints(stub) if e.startswith(SEARCH))


def test_f_execution_local_answers_without_any_issue_read(stub, proj, tmp_path):
    """REQ-039: (f) `execution = "local"` in agk.toml decides local mode, as merge_cleared does."""
    (proj / "agk.toml").write_text('execution = "local"\n', encoding="utf-8")
    two_pulls(stub)
    result = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--all", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert reads_of_open_issues(stub) == 0
    assert searches(stub) == 0
    assert "#7 agk:review" in result.stdout and "#8 agk:review" in result.stdout


def test_f_the_reading_reuses_merge_cleared_local_mode(monkeypatch, tmp_path):
    """REQ-039: the router's local mode is `merge_cleared.local_mode`, not a copy of it."""
    seen: list = []
    monkeypatch.setattr(route, "local_mode", lambda data, issues: seen.append(data) or True)
    route.RECORD_OPEN.clear()
    (tmp_path / "agk.toml").write_text('execution = "local"\n', encoding="utf-8")
    assert route.record_open("o/r", tmp_path) is True
    assert seen == [{"execution": "local"}]
    route.RECORD_OPEN.clear()


def test_g_without_execution_one_search_call_decides(stub, proj, tmp_path):
    """REQ-039: (g) one search call, never paging the open issues."""
    two_pulls(stub)
    stub.fixtures[SEARCH] = {"total_count": 1, "items": [RECORD]}
    result = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--all", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert searches(stub) == 1
    assert reads_of_open_issues(stub) == 0
    query = next(e for e in endpoints(stub) if e.startswith(SEARCH))
    owner, name = REPO.split("/")
    for part in (f"repo%3A{owner}%2F{name}", "is%3Aissue", "is%3Aopen", "in%3Atitle", "Local%20mode%20since"):
        assert part in query


def test_h_all_over_two_pull_requests_makes_at_most_18_calls(stub, proj, tmp_path):
    """REQ-039: (h) the label list and the open pull request list are read once each."""
    two_pulls(stub)
    stub.fixtures[SEARCH] = {"total_count": 0, "items": []}
    result = run_router(
        proj,
        stub,
        tmp_path,
        "workflow_dispatch",
        {},
        "--all",
        AGK_PIPELINE_FILE=str(tmp_path / "pipeline.json"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "(changed)" not in result.stdout
    calls = stub.calls()
    assert len(calls) <= 18, calls
    gets = endpoints(stub)
    assert sum(1 for e in gets if e.startswith(f"repos/{REPO}/pulls?")) == 1
    assert sum(1 for e in gets if e.startswith(f"repos/{REPO}/labels")) <= 1


def rate_limited(stub: RouteStub) -> None:
    real = stub.bin / "gh-real"
    (stub.bin / "gh").rename(real)
    gh = stub.bin / "gh"
    gh.write_text(RATE_LIMITED, encoding="utf-8")
    gh.chmod(0o755)


def test_i_a_failed_search_falls_back_to_paging_and_labels_as_today(stub, proj, tmp_path):
    """REQ-039: (i) a 403 on the search is neither "record open" nor "no record": it pages."""
    stub.pull(7, labels=("agk:ci-running",))
    stub.serve("pulls/7", {**stub.fixtures[f"repos/{REPO}/pulls/7"], "body": "Brief: #77\n"})
    stub.serve(f"commits/{HEAD}/check-runs", {"total_count": 0, "check_runs": []})
    body = f"Report: {HEAD[:7]} ready for review\n\n{evidence()}\nUsage: not shown"
    stub.serve("issues/7/comments", [said(1, "builder", body)])
    stub.serve("issues", [RECORD])
    rate_limited(stub)
    result = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "#7 agk:review" in result.stdout
    assert searches(stub) == 1 and reads_of_open_issues(stub) == 1


def test_i_a_failed_search_without_a_record_issue_labels_as_ci_mode(stub, proj, tmp_path):
    """REQ-039: (i) the fallback finds no record issue: CI mode, as today."""
    stub.pull(7, labels=("agk:ci-running",))
    stub.serve(f"commits/{HEAD}/check-runs", {"total_count": 0, "check_runs": []})
    stub.serve("issues", [])
    rate_limited(stub)
    result = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert reads_of_open_issues(stub) == 1


def test_j_ci_mode_with_no_record_issue_one_search_then_todays_labels(stub, proj, tmp_path):
    """REQ-039: (j) in CI mode one search call, then the labels today's tests expect."""
    stub.pull(7, labels=("agk:review",))
    stub.serve(f"commits/{HEAD}/check-runs", {"total_count": 0, "check_runs": []})
    stub.serve("pulls/7", {**stub.fixtures[f"repos/{REPO}/pulls/7"], "body": "Brief: #77\n"})
    body = f"Report: {HEAD[:7]} ready for review\n\n{evidence()}\nUsage: not shown"
    stub.serve("issues/7/comments", [said(1, "builder", body)])
    stub.fixtures[SEARCH] = {"total_count": 0, "items": []}
    result = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "#7 agk:ci-running" in result.stdout  # (e): no record issue, missing checks run
    assert searches(stub) == 1 and reads_of_open_issues(stub) == 0


def test_search_once_never_waits_on_a_rate_limit(monkeypatch):
    """REQ-039: (6b) one call; a rate limit is a failed search, not a wait of `session.gh`."""
    calls: list = []

    class Done:
        returncode = 1
        stdout = ""
        stderr = "gh: API rate limit exceeded (HTTP 429)"

    monkeypatch.setattr(route.subprocess, "run", lambda *a, **k: calls.append(a) or Done())
    assert route.search_once("search/issues?q=x") is None
    assert len(calls) == 1
