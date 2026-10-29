"""A brief is closed when the pull request that finishes it merges (brief 302; REQ-039, ADR-0178).

A pull request body may carry one line `Finishes: #n` beside `Brief: #n` (the same number). When
such a pull request merges, the router closes issue #n as completed and comments on it with the
merge commit. It closes only that issue, only an open issue labelled `agk-brief`, and never when
`Brief:` names another number or the pull request was closed without a merge. The workflow wakes
on `closed` and its job runs for a closed pull request only when it merged. A `gh` stub serves
saved JSON copies of the GitHub responses; no network.
"""

from __future__ import annotations

import re

import pytest
from test_route import REPO, REPO_INFO, route, run_router, workflow
from test_route import Stub as RouteStub
from test_route import proj as route_proj  # noqa: F401  (the fixtures of test_route)
from test_route import stub as route_stub  # noqa: F401

MERGE = "f" * 40
BRIEF = 302


@pytest.fixture
def stub(request) -> RouteStub:
    return request.getfixturevalue("route_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("route_proj")


def body(*lines: str) -> str:
    return "\n".join([*lines, "Advances: REQ-039", "Summary: A plain sentence."]) + "\n"


FINISHING = body(f"Brief: #{BRIEF}", f"Finishes: #{BRIEF}")


def merged_pull(stub, n: int, text: str, merged: bool = True) -> None:
    stub.pull(n, state="closed", merged="2026-10-29T22:00:00Z" if merged else None)
    record = stub.fixtures[f"repos/{REPO}/pulls/{n}"]
    record.update(body=text, merged=merged, merge_commit_sha=MERGE if merged else None)


def brief_issue(stub, n: int = BRIEF, state: str = "open", labels=("agk-brief",), **extra) -> None:
    stub.serve(
        f"issues/{n}",
        {"number": n, "state": state, "labels": [{"name": x} for x in labels], **extra},
    )
    stub.fixtures.setdefault(f"repos/{REPO}/issues/{n}/comments", [])


def closed(n: int = 7, merged: bool = True) -> dict:
    return {
        "action": "closed",
        "pull_request": {"number": n, "merged": merged},
        "repository": REPO_INFO,
    }


def on_brief(stub, n: int = BRIEF) -> list[list]:
    return [w for w in stub.writes() if re.fullmatch(rf"repos/{REPO}/issues/{n}(/comments)?", w[1])]


# --- the line read from a body (answer 1) -------------------------------------------------------


def test_the_brief_a_body_finishes_is_read_only_when_brief_names_the_same_number():
    assert route.finished_brief(FINISHING) == BRIEF
    assert route.finished_brief(body("Brief: #302")) is None
    assert route.finished_brief(body("Brief: #301", "Finishes: #302")) is None
    assert route.finished_brief(body("Finishes: #302")) is None
    assert route.finished_brief(body("Brief: #302", "Finishes: 302")) is None
    assert route.finished_brief(body("Brief: #302", "Finishes: #302 and #303")) is None
    assert route.finished_brief(body("Brief: #302", "Finishes: #302", "Finishes: #302")) is None
    assert route.finished_brief("") is None and route.finished_brief(None) is None


# --- the router closes on merge (answers 1 and 4) -----------------------------------------------


def test_a_merged_pull_request_with_finishes_closes_its_brief_and_comments(proj, stub, tmp_path):
    merged_pull(stub, 7, FINISHING)
    brief_issue(stub)
    proc = run_router(proj, stub, tmp_path, "pull_request", closed())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    writes = on_brief(stub)
    assert [w[0] for w in writes] == ["POST", "PATCH"]
    comment = writes[0][2]
    assert any(a.startswith("body=") and MERGE in a and "#7" in a for a in comment), comment
    assert "state=closed" in writes[1][2] and "state_reason=completed" in writes[1][2]
    assert f"#{BRIEF} closed" in proc.stdout


def test_a_body_without_finishes_closes_nothing(proj, stub, tmp_path):
    merged_pull(stub, 7, body(f"Brief: #{BRIEF}"))
    brief_issue(stub)
    proc = run_router(proj, stub, tmp_path, "pull_request", closed())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert stub.writes() == []
    assert not any(c[1] == f"repos/{REPO}/issues/{BRIEF}" for c in stub.calls())


def test_finishes_with_another_brief_number_closes_nothing(proj, stub, tmp_path):
    merged_pull(stub, 7, body("Brief: #301", f"Finishes: #{BRIEF}"))
    brief_issue(stub)
    brief_issue(stub, 301)
    run_router(proj, stub, tmp_path, "pull_request", closed())
    assert stub.writes() == []


def test_a_pull_request_closed_without_a_merge_closes_nothing(proj, stub, tmp_path):
    merged_pull(stub, 7, FINISHING, merged=False)
    brief_issue(stub)
    run_router(proj, stub, tmp_path, "pull_request", closed(merged=False))
    assert stub.writes() == []


def test_only_a_closed_event_closes_a_brief(proj, stub, tmp_path):
    merged_pull(stub, 7, FINISHING)
    brief_issue(stub)
    edited = {"action": "edited", "pull_request": {"number": 7}, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "pull_request", edited)
    assert stub.writes() == []
    comment = {"issue": {"number": 7, "pull_request": {}}, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "issue_comment", comment)
    assert stub.writes() == []


def test_the_merge_is_read_from_github_not_from_the_event(proj, stub, tmp_path):
    """An event that says merged for a pull request GitHub reports unmerged closes nothing."""
    merged_pull(stub, 7, FINISHING, merged=False)
    brief_issue(stub)
    run_router(proj, stub, tmp_path, "pull_request", closed(merged=True))
    assert stub.writes() == []


def test_a_brief_already_closed_is_left_alone(proj, stub, tmp_path):
    merged_pull(stub, 7, FINISHING)
    brief_issue(stub, state="closed")
    proc = run_router(proj, stub, tmp_path, "pull_request", closed())
    assert proc.returncode == 0 and stub.writes() == []


def test_an_issue_that_is_not_a_brief_is_never_closed(proj, stub, tmp_path):
    merged_pull(stub, 7, FINISHING)
    brief_issue(stub, labels=("bug",))
    run_router(proj, stub, tmp_path, "pull_request", closed())
    assert stub.writes() == []
    brief_issue(stub, pull_request={"url": "x"})
    run_router(proj, stub, tmp_path, "pull_request", closed())
    assert stub.writes() == []


def test_a_second_run_does_not_comment_twice(proj, stub, tmp_path):
    """The comment carries a marker; a run after a failed close only closes."""
    merged_pull(stub, 7, FINISHING)
    brief_issue(stub)
    earlier = {
        "id": 1,
        "user": {"login": "github-actions[bot]"},
        "body": f"Finished by #7 (merge commit {MERGE}).",
    }
    stub.serve(f"issues/{BRIEF}/comments", [earlier])
    run_router(proj, stub, tmp_path, "pull_request", closed())
    assert [w[0] for w in on_brief(stub)] == ["PATCH"]


def test_the_router_writes_only_to_the_brief_it_closes(proj, stub, tmp_path):
    merged_pull(stub, 7, FINISHING)
    brief_issue(stub)
    run_router(proj, stub, tmp_path, "pull_request", closed())
    assert stub.writes() and stub.writes() == on_brief(stub)
    assert not any("merge" in c[1] for c in stub.calls() if c[0] != "GET")


def test_an_unreadable_brief_fails_naming_the_rule_and_writes_nothing(proj, stub, tmp_path):
    merged_pull(stub, 7, FINISHING)
    stub.serve(f"issues/{BRIEF}", "FAIL")
    proc = run_router(proj, stub, tmp_path, "pull_request", closed())
    assert proc.returncode == 1 and "FAIL route" in proc.stdout and "rule" in proc.stdout
    assert str(BRIEF) not in proc.stdout.split("FAIL route", 1)[1]
    assert stub.writes() == []


def test_a_read_only_token_skips_the_close(proj, stub, tmp_path):
    merged_pull(stub, 7, FINISHING)
    brief_issue(stub)
    proc = run_router(proj, stub, tmp_path, "pull_request", closed(), GH_STUB_FORBID="1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "skipped (read-only token)" in proc.stdout


def test_dry_run_closes_nothing(proj, stub, tmp_path):
    merged_pull(stub, 7, FINISHING)
    brief_issue(stub)
    run_router(proj, stub, tmp_path, "pull_request", closed(), "--dry-run")
    assert stub.writes() == []


# --- the workflow (the conductor's field note) --------------------------------------------------


def test_the_workflow_wakes_on_closed_and_its_job_runs_for_a_merge_only():
    text = workflow()
    on = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    types = re.search(r"  pull_request:\n\s+types: \[([^\]]*)\]", on)
    assert types, on
    assert [x.strip() for x in types.group(1).split(",")] == [
        "opened",
        "synchronize",
        "reopened",
        "edited",
        "closed",
    ]
    condition = re.search(r"^    if: \$\{\{ (.+) \}\}$", text, re.MULTILINE)
    assert condition, text
    assert (
        "(github.event_name != 'pull_request' || github.event.action != 'closed' "
        "|| github.event.pull_request.merged == true)"
    ) in condition.group(1)
    assert "pull_request_target" not in text


# --- the builder prompt and the session rules (answer 2) ----------------------------------------


def test_the_session_rules_tell_the_last_build_to_finish_its_brief():
    from test_route import SCRIPTS

    rules = (SCRIPTS.parents[1] / "config" / "session-rules.md").read_text(encoding="utf-8")
    rule = next(x for x in rules.splitlines() if x.startswith("28. "))
    assert "`Finishes: #<brief>`" in rule and "`Brief: #<brief>`" in rule
    assert "only one" in rule and "last build" in rule


def test_the_builder_prompt_tells_the_pull_request_that_finishes_a_brief_to_say_so():
    import launch

    text = launch.prompt_for("builder-a", 5)
    assert "Brief: #5" in text and "Finishes: #5" in text
    assert "build (" not in text  # a brief without builds, as before
    built = launch.prompt_for("builder-a", 5, "b")
    assert "Finishes: #5" in built and "last build" in built
