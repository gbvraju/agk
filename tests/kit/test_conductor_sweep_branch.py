"""conductor.py sweep: the default branch line reads its required checks (brief #736).

REQ-037. The sweep's line `<branch>: <state> at <sha7>` reads the newest run of each check named
in `required_checks` on the default branch's head, never the newest run of any workflow: a
skipped `agk-route` run over a failed `governance` run prints `failure`, all passed prints
`success`, one still running prints `pending` and none reported prints `no run`. A `gh` stub
serves saved copies of the GitHub responses; no network, GET only, nothing written."""

from __future__ import annotations

from test_conductor_commands import proj, run, stub  # noqa: F401 - fixtures
from test_session import REPO

HEAD = "c" * 40
LINE = f"main: {{}} at {HEAD[:7]}"


def check(cid: int, name: str, status: str, conclusion: str | None) -> dict:
    return {"id": cid, "name": name, "status": status, "conclusion": conclusion}


def serve_head(stub, checks: list, statuses: list | None = None) -> None:  # noqa: F811
    stub.serve(f"repos/{REPO}/branches/main", {"name": "main", "commit": {"sha": HEAD}})
    stub.serve(f"repos/{REPO}/commits/{HEAD}/check-runs", {"total_count": len(checks), "check_runs": checks})
    stub.serve(f"repos/{REPO}/commits/{HEAD}/status", {"state": "", "statuses": statuses or []})
    # the read the sweep made before the fix: its newest run is a skipped router run
    stub.serve(
        f"repos/{REPO}/actions/runs",
        {"workflow_runs": [{"name": "agk-route", "head_sha": HEAD, "status": "completed",
                            "conclusion": "skipped"}]},
    )  # fmt: skip


def branch_line(proj, stub) -> str:  # noqa: F811
    out = run(proj, stub, "sweep")
    assert out.returncode == 0, out.stdout + out.stderr
    assert all(c[0] == "GET" for c in stub.calls())
    return [x for x in out.stdout.splitlines() if x.startswith("main:")][0]


def test_a_skipped_router_run_over_a_failed_governance_run_is_failure(proj, stub):  # noqa: F811
    serve_head(
        stub,
        [check(9, "agk-route", "completed", "skipped"), check(5, "governance", "completed", "failure")],
    )
    assert branch_line(proj, stub) == LINE.format("failure")


def test_all_required_passed_is_success(proj, stub):  # noqa: F811
    serve_head(
        stub,
        [check(3, "proof", "completed", "success"), check(4, "governance", "completed", "success"),
         check(9, "agk-route", "completed", "skipped")],
    )  # fmt: skip
    assert branch_line(proj, stub) == LINE.format("success")


def test_one_required_still_running_is_pending(proj, stub):  # noqa: F811
    serve_head(
        stub,
        [check(3, "proof", "completed", "success"), check(4, "governance", "in_progress", None)],
    )
    assert branch_line(proj, stub) == LINE.format("pending")


def test_none_reported_is_no_run(proj, stub):  # noqa: F811
    serve_head(stub, [check(9, "agk-route", "completed", "success")])
    assert branch_line(proj, stub) == LINE.format("no run")


def test_a_failed_required_status_is_failure(proj, stub):  # noqa: F811
    serve_head(stub, [], [{"id": 1, "context": "governance", "state": "failure"}])
    assert branch_line(proj, stub) == LINE.format("failure")


def test_a_newer_rerun_that_passed_replaces_an_older_failure(proj, stub):  # noqa: F811
    serve_head(
        stub,
        [check(4, "governance", "completed", "failure"), check(8, "governance", "completed", "success")],
    )
    assert branch_line(proj, stub) == LINE.format("success")


def test_the_checks_that_cannot_be_read_fail_the_sweep(proj, stub):  # noqa: F811
    serve_head(stub, [])
    stub.serve(f"repos/{REPO}/commits/{HEAD}/check-runs", "FAIL")
    out = run(proj, stub, "sweep")
    assert out.returncode == 1
    assert "cannot be read" in out.stderr
