"""`Closes #n` is a review item and closes a brief; numbers and the red branch (brief #854).

REQ-039. Answer 3: the router closes the brief named by `Finishes:` or `Closes`, as it does for
`Finishes:` today. Answer 6: a take writes the brief's own `Reserved:` numbers and refuses numbers
held elsewhere, naming both. Answer 7: the red-branch issue is a record the plan offers. Answer 8:
the plan reads the merge rate while the branch is red. A `gh` stub serves saved JSON; no network.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_route import REPO as ROUTE_REPO
from test_route import REPO_INFO, route, run_router
from test_route import Stub as RouteStub
from test_route import proj as route_proj  # noqa: F401  (the fixtures of test_route)
from test_route import stub as route_stub  # noqa: F401
from test_session import ISSUES, REPO, Stub, comment, issue, listing, posts, session
from test_session_flow import PULLS, base, brief, flow, pr
from test_session_plan import changed, data, free, plan

ROOT = Path(__file__).resolve().parents[2]
BRIEF = 854
MERGE = "f" * 40


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def body(*lines: str) -> str:
    return "\n".join([*lines, "Advances: REQ-039", "Summary: A plain sentence."]) + "\n"


# --- answer 3 --------------------------------------------------------------------------------


def test_the_brief_a_body_closes_needs_the_brief_line():
    assert route.closing_brief(body(f"Brief: #{BRIEF}", f"Closes #{BRIEF}")) == BRIEF
    assert route.closing_brief(body(f"Brief: #{BRIEF}", f"Finishes: #{BRIEF}")) == BRIEF
    assert route.closing_brief(body(f"Closes #{BRIEF}")) is None
    assert route.closing_brief(body("Brief: #1", f"Closes #{BRIEF}")) is None
    assert route.closing_brief(body(f"Brief: #{BRIEF}")) is None


def test_a_bad_finishes_line_is_not_rescued_by_closes():
    text = body(f"Brief: #{BRIEF}", "Finishes: #1", f"Closes #{BRIEF}")
    assert route.closing_brief(text) is None


def merged_pull(stub_: RouteStub, n: int, text: str, merged: bool = True) -> None:
    stub_.pull(n, state="closed", merged="2026-10-29T22:00:00Z" if merged else None)
    record = stub_.fixtures[f"repos/{ROUTE_REPO}/pulls/{n}"]
    record.update(body=text, merged=merged, merge_commit_sha=MERGE if merged else None)


def closed_event(n: int = 7) -> dict:
    return {"action": "closed", "pull_request": {"number": n, "merged": True}, "repository": REPO_INFO}


def test_a_merged_pull_request_with_closes_closes_its_brief(route_proj, route_stub):  # noqa: F811
    proj, stub = route_proj, route_stub
    merged_pull(stub, 7, body(f"Brief: #{BRIEF}", f"Closes #{BRIEF}"))
    stub.serve(f"issues/{BRIEF}", {"number": BRIEF, "state": "open", "labels": [{"name": "agk-brief"}]})
    stub.fixtures.setdefault(f"repos/{ROUTE_REPO}/issues/{BRIEF}/comments", [])
    run_router(proj, stub, "pull_request", closed_event())
    writes = [
        w for w in stub.writes() if re.fullmatch(rf"repos/{ROUTE_REPO}/issues/{BRIEF}(/comments)?", w[1])
    ]
    assert any("state=closed" in " ".join(map(str, w)) for w in writes), stub.writes()


def test_the_review_checklist_names_the_closes_line():
    text = (ROOT / "config" / "review-checklist.md").read_text(encoding="utf-8")
    assert "`Closes #<brief>`" in text and "`Finishes:`" in text and "fix item" in text


# --- answer 6: the numbers of a take ---------------------------------------------------------

RESERVED = "Reserved: ADR-0800\n"


def claim(proj_, stub_, number: int = 6):
    return session(proj_, stub_, "claim", "--session", "s-me", "--brief", str(number))


def taken(stub_) -> str:
    return next(c for c in posts(stub_) if "taken:" in " ".join(map(str, c)))[-1]


def setup_take(proj_, stub_, issues: list, pulls: list | None = None) -> None:
    base(proj_, adrs=3)
    listing(stub_, issues)
    stub_.serve(PULLS, pulls or [])
    free(stub_, *(i["number"] for i in issues))
    stub_.serve(f"{ISSUES}/6", issues[-1])


def test_a_claim_writes_the_briefs_own_reserved_numbers(proj, stub):
    setup_take(proj, stub, [issue(6, brief() + RESERVED)])
    out = claim(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    assert taken(stub).endswith(" reserves ADR-0800")


def test_next_take_writes_the_briefs_own_reserved_numbers(proj, stub):
    setup_take(proj, stub, [issue(6, brief() + RESERVED)])
    out = session(proj, stub, "next", "--session", "s-me", "--take")
    assert out.returncode == 0, out.stdout + out.stderr
    assert taken(stub).endswith(" reserves ADR-0800")


def test_a_brief_with_no_reserved_line_gets_the_next_free_number(proj, stub):
    setup_take(proj, stub, [issue(6, brief())])
    assert claim(proj, stub).returncode == 0
    assert taken(stub).endswith(" reserves ADR-0004")


def test_the_next_free_number_skips_what_another_open_brief_reserves(proj, stub):
    setup_take(proj, stub, [issue(5, brief("other/**") + "Reserved: ADR-0004\n"), issue(6, brief())])
    assert claim(proj, stub).returncode == 0
    assert taken(stub).endswith(" reserves ADR-0005")


def test_a_claim_is_refused_when_an_open_pull_request_adds_its_number(proj, stub):
    pull = pr(20, 5)
    setup_take(proj, stub, [issue(6, brief() + RESERVED)], [pull])
    changed(stub, 20, ("added", "docs/adr/0800-another.md"))
    out = claim(proj, stub)
    assert out.returncode == 1
    assert "Reserved ADR-0800 of #6 is also held by #20" in out.stdout
    assert posts(stub) == []


def test_a_claim_is_refused_when_an_earlier_open_brief_reserves_its_number(proj, stub):
    setup_take(proj, stub, [issue(4, brief("other/**") + RESERVED), issue(6, brief() + RESERVED)])
    out = claim(proj, stub)
    assert out.returncode == 1 and "is also held by #4" in out.stdout
    assert posts(stub) == []


def test_a_claim_is_refused_when_a_live_take_elsewhere_reserves_its_number(proj, stub):
    setup_take(proj, stub, [issue(5, brief("other/**")), issue(6, brief() + RESERVED)])
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "b", f"taken: s-other {day} reserves ADR-0800")])
    out = claim(proj, stub)
    assert out.returncode == 1 and "is also held by #5" in out.stdout
    assert posts(stub) == []


def test_the_pull_request_of_the_same_brief_does_not_hold_its_number(proj, stub):
    setup_take(proj, stub, [issue(6, brief() + RESERVED)], [pr(20, 6)])
    changed(stub, 20, ("added", "docs/adr/0800-mine.md"))
    assert claim(proj, stub).stdout.count("is also held") == 0


# --- answers 7 and 8: the red branch in the plan ----------------------------------------------

RED_BODY = (
    'Sentence: "The default branch is red: the required checks of its head fail."\n'
    "Answers:\n1. Failing check: governance\n2. Head: abc\n3. Run: https://example.com/1\n"
    "Priority: 0\nAdvances: none\nTouches: **\nSize: S\n"
    "Broad: a red default branch can start in any file\n"
)


def red_issue(number: int = 66) -> dict:
    return {
        **issue(number, RED_BODY, title="x"),
        "title": "The default branch is red",
        "user": {"login": "github-actions[bot]"},
    }


def with_plan_issue(proj_, stub_) -> None:
    flow(proj_, "plan_issue = 1")
    stub_.serve(f"{ISSUES}/1", {"number": 1, "body": "## Wave 1\n", "title": "plan", "milestone": None})
    stub_.serve(f"repos/{REPO}/milestones", [])


def test_the_red_branch_issue_is_offered_and_not_malformed(proj, stub):
    with_plan_issue(proj, stub)
    listing(stub, [red_issue()])
    stub.serve(PULLS, [])
    free(stub, 66)
    out = plan(proj, stub, "--json")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "MALFORMED" not in out.stdout
    assert '"brief": 66' in out.stdout


def test_a_copy_by_hand_of_the_red_issue_stays_a_malformed_brief(proj, stub):
    with_plan_issue(proj, stub)
    listing(stub, [{**red_issue(), "user": {"login": "someone"}}])
    stub.serve(PULLS, [])
    free(stub, 66)
    out = plan(proj, stub)
    assert "MALFORMED: #66" in out.stdout


def test_the_merge_rate_is_read_while_the_branch_is_red(proj, stub):
    listing(stub, [red_issue()])
    free(stub, 66)
    at = (datetime.now(UTC) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stub.serve(PULLS, [{**pr(20, 5, state="closed"), "merged_at": at}])
    out = plan(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "Your merge rate over the last 14 days is 1 an hour." in out.stdout
    assert "unknown" not in out.stdout


def test_the_merge_limit_stays_off_for_a_red_fix(proj, stub):
    """The fix of a red branch is offered at once, whatever waits in the merge queue."""
    listing(stub, [red_issue()])
    free(stub, 66)
    at = (datetime.now(UTC) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ready = {**pr(21, 7), "labels": [{"name": "agk:ready"}]}
    stub.serve(PULLS, [{**pr(20, 5, state="closed"), "merged_at": at}, ready, {**ready, "number": 22}])
    assert data(proj, stub)["start"], "the red brief is started"


def test_a_failed_read_of_the_merged_pull_requests_is_not_an_unknown_rate(proj, stub):
    listing(stub, [red_issue()])
    free(stub, 66)
    (stub.dir / f"repos__{REPO.replace('/', '__')}__pulls.GET.json").unlink()
    out = plan(proj, stub)
    assert "the pull requests cannot be read" in out.stdout + out.stderr


def test_the_role_file_says_a_red_fix_brief_carries_the_wave():
    text = (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "A brief that fixes a red default branch carries `Wave:` of the current wave" in text


