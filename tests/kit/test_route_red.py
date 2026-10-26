"""The red default branch: one priority-0 brief, opened, updated and closed (SPEC-0032 rule 7).

When the required checks of the default branch's head fail, `route.py` opens one issue `The
default branch is red`, labelled `agk-brief`, in the shape of a brief with `Priority: 0` and
`Advances: none`, naming the failing check, the sha and the run and no cause; it updates the open
one and closes it when the default branch is green. `session.py next` hands out only that brief
while it is open. A `gh` stub on `PATH`, saved responses, no network. REQ-039 AC5.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_route import (
    REPO,
    REPO_INFO,
    ok,
    run_router,
)
from test_route import (
    Stub as RouteStub,
)
from test_route import (
    proj as route_proj,  # noqa: F401  (the fixtures of test_route)
)
from test_route import (
    stub as route_stub,  # noqa: F401
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

TIP = "9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"
OTHER = "1111111111111111111111111111111111111111"
URL = "https://github.com/acme/widgets/actions/runs/42"
TITLE = "The default branch is red"
PUSH = {"ref": "refs/heads/main", "repository": REPO_INFO}


@pytest.fixture
def stub(request) -> RouteStub:
    return request.getfixturevalue("route_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("route_proj")


def bad(name: str = "proof", url: str = URL) -> dict:
    return {"name": name, "status": "completed", "conclusion": "failure", "html_url": url}


def branch(
    stub: RouteStub, checks: list[dict], statuses=(), sha: str = TIP, fill: bool = True
) -> None:
    # a required check that has not reported keeps the branch pending (brief 231): by default the
    # helper reports the default required checks that a case does not name
    if fill:
        named = {c["name"] for c in checks}
        checks = checks + [ok(n) for n in ("proof", "governance") if n not in named]
    stub.fixtures[f"repos/{REPO}/branches/main"] = {"commit": {"sha": sha}}
    stub.fixtures[f"repos/{REPO}/commits/{sha}/check-runs"] = {
        "total_count": len(checks),
        "check_runs": checks,
    }
    stub.fixtures[f"repos/{REPO}/commits/{sha}/status"] = {"statuses": list(statuses)}


def red_issue(number: int = 9, sha: str = OTHER, name: str = "proof", **extra) -> dict:
    import route

    return {
        "number": number,
        "title": TITLE,
        "body": route.red_body(name, sha, URL),
        "html_url": f"https://github.com/{REPO}/issues/{number}",
        "user": {"login": "github-actions[bot]"},
        **extra,
    }


def issues(stub: RouteStub, *items: dict) -> None:
    stub.fixtures[f"repos/{REPO}/issues"] = list(items)


def issue_writes(stub: RouteStub) -> list[list]:
    return [w for w in stub.writes() if "/labels" not in w[1]]


def push(proj, stub, tmp_path, *args: str):
    return run_router(proj, stub, tmp_path, "push", PUSH, *args)


# --- opening (AC5) ----------------------------------------------------------------------------


def test_ac5_a_red_default_branch_opens_one_brief_that_names_the_check_the_sha_and_the_run(
    proj, stub, tmp_path
):
    """REQ-039 AC5"""
    import session

    branch(stub, [ok("governance"), bad("proof")])
    proc = push(proj, stub, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    writes = issue_writes(stub)
    assert [(w[0], w[1]) for w in writes] == [("POST", f"repos/{REPO}/issues")]
    args = writes[0][2]
    assert f"title={TITLE}" in args and "labels[]=agk-brief" in args
    body = next(a for a in args if a.startswith("body="))[len("body=") :]
    assert session.brief_problems(body) == []
    for line in ("Priority: 0", "Advances: none", "Touches: **", "Size: S"):
        assert line in body.splitlines(), line
    assert "1. Failing check: proof" in body and f"2. Head: {TIP}" in body
    assert f"3. Run: {URL}" in body


def test_ac5_the_brief_names_no_cause(proj, stub, tmp_path):
    """REQ-039 AC5: rule 7 (the router measures nothing, so it says nothing of a cause)."""
    branch(stub, [bad("proof")])
    push(proj, stub, tmp_path)
    body = next(a for a in issue_writes(stub)[0][2] if a.startswith("body="))
    lowered = body.lower()
    for word in ("because", "cause", "due to", "regression", "broke", "faulty"):
        assert word not in lowered, word
    assert "Measured:" not in body


def test_ac5_a_failing_commit_status_counts_and_the_routers_own_check_does_not(
    proj, stub, tmp_path
):
    """REQ-039 AC5"""
    own = {"name": "agk-route", "status": "completed", "conclusion": "failure"}
    branch(stub, [ok("governance"), own])
    push(proj, stub, tmp_path)
    assert issue_writes(stub) == []
    (proj / "agk.toml").write_text('required_checks = ["governance", "ci/other"]\n')
    branch(stub, [ok("governance")], statuses=[{"context": "ci/other", "state": "failure"}])
    push(proj, stub, tmp_path)
    body = next(a for a in issue_writes(stub)[0][2] if a.startswith("body="))
    assert "Failing check: ci/other" in body


def test_ac5_the_label_agk_brief_is_created_when_the_repository_lacks_it(proj, stub, tmp_path):
    """REQ-039 AC5"""
    branch(stub, [bad()])
    push(proj, stub, tmp_path)
    created = [w for w in stub.writes() if w[1] == f"repos/{REPO}/labels"]
    assert any("name=agk-brief" in w[2] for w in created)


# --- updating, closing, waiting (AC5) --------------------------------------------------------


def test_ac5_an_open_red_brief_is_updated_for_a_new_head_and_not_opened_twice(proj, stub, tmp_path):
    """REQ-039 AC5"""
    branch(stub, [bad("governance")])
    issues(stub, red_issue(9, sha=OTHER, name="proof"))
    push(proj, stub, tmp_path)
    writes = issue_writes(stub)
    assert [(w[0], w[1]) for w in writes] == [("PATCH", f"repos/{REPO}/issues/9")]
    body = next(a for a in writes[0][2] if a.startswith("body="))
    assert f"2. Head: {TIP}" in body and "Failing check: governance" in body


def test_ac5_the_same_facts_write_nothing(proj, stub, tmp_path):
    """REQ-039 AC5"""
    branch(stub, [bad("proof")])
    issues(stub, red_issue(9, sha=TIP, name="proof"))
    push(proj, stub, tmp_path)
    assert issue_writes(stub) == []


def test_ac5_a_green_default_branch_closes_the_open_red_brief_without_a_comment(
    proj, stub, tmp_path
):
    """REQ-039 AC5"""
    branch(stub, [ok("governance"), ok("proof")])
    issues(stub, red_issue(9))
    push(proj, stub, tmp_path)
    writes = issue_writes(stub)
    assert [(w[0], w[1]) for w in writes] == [("PATCH", f"repos/{REPO}/issues/9")]
    assert "state=closed" in writes[0][2] and "state_reason=completed" in writes[0][2]
    assert not any("comments" in w[1] for w in stub.writes())


def test_ac5_a_green_default_branch_with_no_red_brief_writes_nothing(proj, stub, tmp_path):
    """REQ-039 AC5"""
    branch(stub, [ok("governance"), ok("proof")])
    push(proj, stub, tmp_path)
    assert issue_writes(stub) == []


def test_ac5_checks_still_running_neither_open_nor_close(proj, stub, tmp_path):
    """REQ-039 AC5: the verdict waits for the checks to finish."""
    running = {"name": "proof", "status": "in_progress", "conclusion": None}
    branch(stub, [bad("governance"), running], fill=False)
    push(proj, stub, tmp_path)
    assert issue_writes(stub) == []
    branch(stub, [running], fill=False)
    issues(stub, red_issue(9))
    push(proj, stub, tmp_path)
    assert issue_writes(stub) == []
    branch(stub, [], fill=False)
    push(proj, stub, tmp_path)
    assert issue_writes(stub) == []


def test_ac5_only_the_red_brief_is_touched_other_issues_and_briefs_are_left_alone(
    proj, stub, tmp_path
):
    """REQ-039 AC5"""
    branch(stub, [ok("governance"), ok("proof")])
    other = {"number": 4, "title": "Brief: something", "body": "Priority: 0\n"}
    pull = {"number": 5, "title": TITLE, "body": "", "pull_request": {}}
    renamed = {**red_issue(6), "title": "The default branch is not red"}
    issues(stub, other, pull, renamed)
    push(proj, stub, tmp_path)
    assert issue_writes(stub) == []


def test_ac5_the_events_that_check_the_default_branch(proj, stub, tmp_path):
    """REQ-039 AC5: a push to it and a finished workflow on it; nothing else."""
    branch(stub, [bad()])
    on_branch = {"workflow_run": {"head_branch": "main", "head_sha": TIP}, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "workflow_run", on_branch)
    assert len(issue_writes(stub)) == 1
    stub.fixtures.pop(f"repos/{REPO}/branches/main")
    off = {"workflow_run": {"head_branch": "feature", "head_sha": OTHER}, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "workflow_run", off)
    run_router(proj, stub, tmp_path, "push", {"ref": "refs/heads/feature", **PUSH})
    run_router(proj, stub, tmp_path, "issue_comment", {"issue": {"number": 7}})
    assert len(issue_writes(stub)) == 1  # no new write, and no read of the branch needed


def test_ac5_the_branch_alone_can_be_routed_from_the_command_line_and_dry_run_writes_nothing(
    proj, stub, tmp_path
):
    """REQ-039 AC5"""
    branch(stub, [bad()])
    proc = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--branch", "--dry-run")
    assert proc.returncode == 0 and "default branch red" in proc.stdout
    assert stub.writes() == []


def test_ac5_unreadable_checks_fail_naming_the_rule_and_write_nothing(proj, stub, tmp_path):
    """REQ-039 AC5"""
    branch(stub, [bad()])
    stub.fixtures[f"repos/{REPO}/commits/{TIP}/check-runs"] = "FAIL"
    proc = push(proj, stub, tmp_path)
    assert proc.returncode == 1 and "rule 7" in proc.stdout
    assert issue_writes(stub) == []


def test_ac5_a_read_only_token_skips_the_issue_write_and_exits_zero(proj, stub, tmp_path):
    """REQ-039 AC5"""
    branch(stub, [bad()])
    proc = run_router(proj, stub, tmp_path, "push", PUSH, GH_STUB_FORBID="1")
    assert proc.returncode == 0 and "skipped" in proc.stdout


def test_ac5_the_router_still_writes_no_comment_review_or_merge(proj, stub, tmp_path):
    """REQ-039 AC5: rule 8 (the issue of rule 7 is the only issue it opens or closes)."""
    branch(stub, [bad()])
    issues(stub, red_issue(9, sha=OTHER))
    push(proj, stub, tmp_path)
    for _, endpoint, _ in stub.writes():
        assert not endpoint.endswith("/comments") and "merge" not in endpoint, endpoint
        assert "/reviews" not in endpoint, endpoint


def test_ac5_a_hand_written_red_brief_is_not_updated_or_closed_by_the_router(proj, stub, tmp_path):
    """REQ-039 AC5: the router touches only an issue its own token opened."""
    by_hand = red_issue(9, sha=OTHER, user={"login": "someone"})
    branch(stub, [ok("governance"), ok("proof")])
    issues(stub, by_hand)
    push(proj, stub, tmp_path)
    assert issue_writes(stub) == []
    branch(stub, [bad("proof")])
    push(proj, stub, tmp_path)
    assert [(w[0], w[1]) for w in issue_writes(stub)] == [("POST", f"repos/{REPO}/issues")]
