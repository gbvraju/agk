"""The router reads the latest run of each check (brief 229; SPEC-0032 rules 2 and 7; REQ-039 AC3).

A cancelled or replaced run of a check name never makes a green head look red; a latest run that
failed or was cancelled still does. Commit statuses keep the latest status per context. Saved
responses as facts; no network, no model.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import route  # noqa: E402

HEAD = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"


def run(name: str, rid: int, conclusion: str | None = "success", started: str = "") -> dict:
    done = conclusion is not None
    return {
        "id": rid,
        "name": name,
        "status": "completed" if done else "in_progress",
        "conclusion": conclusion,
        "started_at": started or f"2026-10-26T00:{rid % 60:02d}:00Z",
        "html_url": f"https://example.invalid/runs/{rid}",
    }


def status(context: str, sid: int, state: str) -> dict:
    return {"id": sid, "context": context, "state": state, "target_url": f"https://x.invalid/{sid}"}


def facts(checks: list[dict], statuses: list[dict] | None = None) -> dict:
    return {
        "head": HEAD,
        "mergeable_state": "clean",
        "checks": checks,
        "statuses": statuses or [],
        "comments": [],
        "reviews": [],
        "authors": ["boss"],
        "approvers": ["maintainer"],
        "author": "builder",
        "files": [],
        "commit": {},
    }


def test_ac3_a_cancelled_run_followed_by_a_success_of_the_same_name_is_not_red():
    """REQ-039 AC3: the case of #226."""
    checks = [run("proof", 10, "cancelled"), run("proof", 11), run("governance", 12)]
    assert route.decide(facts(checks)) != "agk:ci-red"


def test_ac3_a_failure_replaced_by_a_success_is_not_red_and_a_success_replaced_by_a_failure_is():
    """REQ-039 AC3"""
    assert route.decide(facts([run("proof", 10, "failure"), run("proof", 11)])) != "agk:ci-red"
    assert route.decide(facts([run("proof", 10), run("proof", 11, "failure")])) == "agk:ci-red"


def test_ac3_a_latest_cancelled_run_still_counts_as_red():
    """REQ-039 AC3"""
    assert route.decide(facts([run("proof", 10), run("proof", 11, "cancelled")])) == "agk:ci-red"


def test_ac3_two_names_one_red_is_red_whatever_the_order_of_the_list():
    """REQ-039 AC3"""
    checks = [run("proof", 11), run("governance", 12, "failure"), run("proof", 10, "cancelled")]
    assert route.decide(facts(checks)) == "agk:ci-red"
    assert route.decide(facts(list(reversed(checks)))) == "agk:ci-red"


def test_ac3_the_newest_run_is_the_highest_id_and_the_start_time_breaks_a_tie():
    """REQ-039 AC3"""
    early, late = "2026-10-26T00:00:00Z", "2026-10-26T00:05:00Z"
    older = [run("proof", 20, "failure", early), run("proof", 21, "success", late)]
    assert route.decide(facts(older)) != "agk:ci-red"
    tie = [run("proof", 20, "failure", late), run("proof", 20, "success", early)]
    assert route.decide(facts(tie)) == "agk:ci-red"


def test_ac3_an_older_run_still_running_does_not_make_the_head_pending_when_a_newer_one_ended():
    """REQ-039 AC3: a replaced run that never ends is not what the head waits for."""
    checks = [run("proof", 10, None), run("proof", 11)]
    assert route.decide(facts(checks)) != "agk:ci-running"
    assert route.decide(facts([run("proof", 10), run("proof", 11, None)])) == "agk:ci-running"


def test_ac3_a_latest_status_per_context_decides_and_the_older_one_is_ignored():
    """REQ-039 AC3: as GitHub does."""
    old_red = [status("ci", 1, "failure"), status("ci", 2, "success")]
    assert route.decide(facts([run("proof", 3)], old_red)) != "agk:ci-red"
    new_red = [status("ci", 1, "success"), status("ci", 2, "failure")]
    assert route.decide(facts([run("proof", 3)], new_red)) == "agk:ci-red"


def test_ac3_the_default_branch_reads_the_latest_run_of_each_check_too():
    """REQ-039 AC3: branch_state."""
    assert route.branch_state([run("proof", 10, "cancelled"), run("proof", 11)], []) == "green"
    assert route.branch_state([run("proof", 10), run("proof", 11, "failure")], []) == "red"
    assert route.branch_state([run("proof", 10, "cancelled")], []) == "red"
    assert route.branch_state([run("proof", 10, None), run("proof", 11)], []) == "green"
    assert (
        route.branch_state([], [status("ci", 1, "failure"), status("ci", 2, "success")]) == "green"
    )


def test_ac3_failing_names_the_failing_check_of_its_latest_run_only():
    """REQ-039 AC3: failing()."""
    checks = [run("proof", 10, "cancelled"), run("proof", 11), run("governance", 12, "failure")]
    name, url = route.failing(checks, [], "o/r", HEAD)
    assert name == "governance" and url.endswith("/runs/12")
    name, url = route.failing([run("proof", 10, "cancelled"), run("proof", 11)], [], "o/r", HEAD)
    assert name == "" and url.endswith(f"/commit/{HEAD}/checks")
    name, url = route.failing([run("proof", 10), run("proof", 11, "failure")], [], "o/r", HEAD)
    assert name == "proof" and url.endswith("/runs/11")


def test_ac3_the_router_job_is_still_left_out():
    """REQ-039 AC3"""
    checks = [run("agk-route", 30, "failure"), run("proof", 31)]
    assert route.decide(facts(checks)) != "agk:ci-red"
    assert route.branch_state(checks, []) == "green"
