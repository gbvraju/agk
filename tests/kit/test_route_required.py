"""The router judges only the checks a project requires (brief 231; SPEC-0032 rules 2, 7; REQ-039).

`required_checks` in `agk.toml` (default `["proof", "governance"]`) names the checks whose latest
run decides `agk:ci-running`, `agk:ci-red` or green, for pull requests and the default branch. A
check that is not listed is ignored for the label; a listed check that has not reported keeps the
pull request running; a listed check that is red stays red. Saved responses; no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_route import REPO_INFO, ok, run_router
from test_route import Stub as RouteStub
from test_route import proj as route_proj  # noqa: F401  (the fixtures of test_route)
from test_route import stub as route_stub  # noqa: F401

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import route  # noqa: E402
from test_route_latest import facts, run, status  # noqa: E402

REQUIRED = ["proof", "governance"]


def bad(name: str) -> dict:
    return run(name, 90, "failure")


@pytest.fixture
def stub(request) -> RouteStub:
    return request.getfixturevalue("route_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("route_proj")


def decide(checks, statuses=None, required=REQUIRED) -> str:
    return route.decide({**facts(checks, statuses), "required": required})


# --- the setting (rule 1) -----------------------------------------------------------------------


def test_the_default_is_proof_and_governance(tmp_path):
    assert common.required_checks(tmp_path) == ["proof", "governance"]


def test_the_setting_is_read_from_agk_toml(tmp_path):
    (tmp_path / "agk.toml").write_text('required_checks = ["proof", "build"]\n')
    assert common.required_checks(tmp_path) == ["proof", "build"]


@pytest.mark.parametrize(
    "value", ['"proof"', "[]", "[1]", '[""]', '["proof", ""]', '[["proof"]]', "true"]
)
def test_an_invalid_setting_is_refused_naming_the_setting(tmp_path, value):
    (tmp_path / "agk.toml").write_text(f"required_checks = {value}\n")
    with pytest.raises(common.CheckError) as err:
        common.required_checks(tmp_path)
    assert "required_checks" in str(err.value) and "agk.toml" in str(err.value)
    assert str(err.value).startswith("required_checks must be a list of check names")


# --- a pull request (rule 2) --------------------------------------------------------------------


def test_an_unlisted_failing_check_with_listed_green_checks_is_green():
    checks = [run("proof", 1), run("governance", 2), bad("preview-build")]
    assert decide(checks) == "agk:review"
    assert decide(checks, [status("deploy/preview", 3, "failure")]) == "agk:review"


def test_a_listed_failing_check_is_red_whatever_else_is_green():
    checks = [run("proof", 1), bad("governance"), run("preview-build", 3)]
    assert decide(checks) == "agk:ci-red"


def test_a_listed_check_that_has_not_reported_keeps_the_pull_request_running():
    assert decide([run("proof", 1)]) == "agk:ci-running"
    assert decide([run("preview-build", 3)]) == "agk:ci-running"
    assert decide([]) == "agk:ci-running"


def test_an_unlisted_running_check_does_not_hold_the_pull_request():
    checks = [run("proof", 1), run("governance", 2), run("preview-build", 3, None)]
    assert decide(checks) == "agk:review"


def test_a_listed_status_context_counts_and_an_unlisted_one_does_not():
    checks = [run("proof", 1), run("governance", 2)]
    assert decide(checks, [status("ci/legacy", 5, "pending")]) == "agk:review"
    assert decide(checks, [status("ci/legacy", 5, "pending")], ["proof", "ci/legacy"]) == (
        "agk:ci-running"
    )
    assert decide(checks, [status("ci/legacy", 5, "failure")], ["proof", "ci/legacy"]) == (
        "agk:ci-red"
    )


def test_a_project_can_list_one_more_check_and_it_then_counts():
    checks = [run("proof", 1), run("governance", 2), bad("preview-build")]
    assert decide(checks, required=[*REQUIRED, "preview-build"]) == "agk:ci-red"


def test_the_latest_run_of_a_listed_check_still_decides():
    checks = [run("proof", 1, "failure"), run("proof", 5), run("governance", 2)]
    assert decide(checks) == "agk:review"


def test_the_routers_own_job_is_never_judged_even_when_listed():
    checks = [run("proof", 1), run("governance", 2), run("agk-route", 3, "failure")]
    assert decide(checks, required=[*REQUIRED, "agk-route"]) == "agk:review"


# --- the default branch (rule 7) ----------------------------------------------------------------


def test_the_default_branch_ignores_an_unlisted_failing_check():
    checks = [run("proof", 1), run("governance", 2), bad("preview-build")]
    assert route.branch_state(checks, [], REQUIRED) == "green"
    assert route.branch_state([bad("proof"), run("governance", 2)], [], REQUIRED) == "red"
    assert route.branch_state([run("proof", 1)], [], REQUIRED) == "pending"
    assert route.branch_state(checks, [], [*REQUIRED, "preview-build"]) == "red"


def test_the_red_brief_names_a_listed_check_not_an_unlisted_one():
    checks = [bad("a-preview"), bad("proof")]
    name, _ = route.failing(checks, [], "acme/widgets", "abc", REQUIRED)
    assert name == "proof"


# --- the router end to end ----------------------------------------------------------------------


def test_the_router_labels_by_the_setting_of_the_project(proj, stub, tmp_path):
    (proj / "agk.toml").write_text('required_checks = ["proof"]\n')
    stub.pull(7, labels=["agk:ci-red"])
    stub.fixtures[f"repos/{route_repo()}/commits/{route_head()}/check-runs"] = {
        "total_count": 3,
        "check_runs": [ok("proof"), bad("governance"), bad("preview-build")],
    }
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    proc = run_router(proj, stub, tmp_path, "pull_request", event)
    assert proc.returncode == 0
    added = [w for w in stub.writes() if w[0] == "POST" and w[1].endswith("/issues/7/labels")]
    assert added and "agk:review" in " ".join(added[0][2])


def test_the_router_refuses_an_invalid_setting_and_writes_no_label(proj, stub, tmp_path):
    (proj / "agk.toml").write_text('required_checks = "proof"\n')
    stub.pull(7)
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    proc = run_router(proj, stub, tmp_path, "pull_request", event)
    assert proc.returncode == 1 and "required_checks" in proc.stdout
    assert "proof" not in proc.stdout.replace("required_checks", "")
    assert stub.writes() == []


def test_a_red_unlisted_check_on_the_default_branch_opens_no_brief(proj, stub, tmp_path):
    from test_route_red import branch, issue_writes, issues, push

    branch(stub, [ok("proof"), ok("governance"), bad("preview-build")])
    issues(stub)
    assert push(proj, stub, tmp_path).returncode == 0
    assert issue_writes(stub) == []
    branch(stub, [ok("proof"), bad("governance"), bad("preview-build")])
    push(proj, stub, tmp_path)
    (opened,) = issue_writes(stub)
    assert "governance" in " ".join(opened[2]) and "preview-build" not in " ".join(opened[2])


def route_repo() -> str:
    from test_route import REPO

    return REPO


def route_head() -> str:
    from test_route import HEAD

    return HEAD
