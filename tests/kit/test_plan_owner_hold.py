"""The owner's hold of a brief (amendment 142; REQ-037 AC3).

A comment by a listed approver whose first line is `Hold: #<brief> <reason>` makes `plan`, `next`
and `claim` skip the brief with `held by the owner: <reason>`; a later `Release: #<brief>` by an
approver ends it; a hold by anyone else is ignored and named in the plan. Invented data; a `gh`
stub; no network.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from test_session import ISSUES, REPO, Stub, comment, iso, issue, listing, posts, session
from test_session_flow import brief
from test_session_plan import data, plan

OWNER = "owner-example"
OTHER = "stranger-example"
HOLD = "Hold: #5 wait for the design\n\nA note.\n"
REASON = "held by the owner: wait for the design"


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write(
        "config/reviewers.yaml",
        f"version: 1\nverdict_authors: [boss, second]\nspec_approvers: [{OWNER}]\n",
    )
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


def brief_with(stub, *comments, number: int = 5) -> None:
    listing(stub, [issue(number, brief("a/"))])
    stub.serve(f"{ISSUES}/{number}/comments", list(comments))


def ago(minutes: int) -> str:
    return iso(-timedelta(minutes=minutes))


def nxt(proj, stub):
    return session(proj, stub, "next", "--session", "s-me")


def claim(proj, stub):
    return session(proj, stub, "claim", "--session", "s-me", "--brief", "5")


def started(got: dict) -> list[int]:
    return [s["brief"] for s in got["start"]]


def test_ac3_a_hold_by_an_approver_is_skipped_by_plan_with_the_reason(proj, stub):
    """REQ-037 AC3"""
    brief_with(stub, comment(1, OWNER, HOLD))
    got = data(proj, stub)
    assert started(got) == []
    assert got["held"] == [{"brief": 5, "reason": "wait for the design"}]


def test_ac3_the_plan_words_list_the_held_brief_once(proj, stub):
    """REQ-037 AC3: the report's line, and not a second time under Skipped."""
    brief_with(stub, comment(1, OWNER, HOLD))
    out = plan(proj, stub)
    assert f"HELD: #5 {REASON}" in out.stdout
    assert "Skipped: #5" not in out.stdout


def test_ac3_next_skips_a_held_brief_and_prints_the_reason(proj, stub):
    """REQ-037 AC3"""
    brief_with(stub, comment(1, OWNER, HOLD))
    out = nxt(proj, stub)
    assert f"skip #5: {REASON}" in out.stdout
    assert "brief #5" not in out.stdout


def test_ac3_claim_refuses_a_held_brief_and_posts_nothing(proj, stub):
    """REQ-037 AC3"""
    brief_with(stub, comment(1, OWNER, HOLD))
    stub.serve(f"repos/{REPO}/pulls", [])
    out = claim(proj, stub)
    assert out.returncode == 1 and f"skip #5: {REASON}" in out.stdout
    assert posts(stub) == []


def test_ac3_a_release_by_an_approver_ends_the_hold(proj, stub):
    """REQ-037 AC3"""
    brief_with(
        stub,
        comment(1, OWNER, HOLD, ago(20)),
        comment(2, OWNER, "Release: #5", ago(10)),
    )
    got = data(proj, stub)
    assert got.get("held", []) == [] and started(got) == [5]


def test_ac3_a_hold_after_a_release_holds_again(proj, stub):
    """REQ-037 AC3: the latest line by an approver decides."""
    brief_with(
        stub,
        comment(1, OWNER, HOLD, ago(30)),
        comment(2, OWNER, "Release: #5", ago(20)),
        comment(3, OWNER, "Hold: #5 again", ago(10)),
    )
    assert data(proj, stub)["held"] == [{"brief": 5, "reason": "again"}]


def test_ac3_a_hold_by_someone_else_does_not_hold_and_is_named(proj, stub):
    """REQ-037 AC3"""
    brief_with(stub, comment(1, OTHER, HOLD))
    got = data(proj, stub)
    assert got.get("held", []) == [] and started(got) == [5]
    assert got["ignored_holds"] == [{"brief": 5, "by": OTHER}]
    assert f"HOLD IGNORED: #5 by {OTHER}" in plan(proj, stub).stdout


def test_ac3_a_verdict_author_who_is_not_an_approver_cannot_hold(proj, stub):
    """REQ-037 AC3: the list is `spec_approvers`, not `verdict_authors`."""
    brief_with(stub, comment(1, "boss", HOLD))
    got = data(proj, stub)
    assert got.get("held", []) == [] and got["ignored_holds"] == [{"brief": 5, "by": "boss"}]


def test_ac3_a_release_by_someone_else_does_not_end_the_hold(proj, stub):
    """REQ-037 AC3"""
    brief_with(
        stub,
        comment(1, OWNER, HOLD, ago(20)),
        comment(2, OTHER, "Release: #5", ago(10)),
    )
    assert data(proj, stub)["held"] == [{"brief": 5, "reason": "wait for the design"}]


@pytest.mark.parametrize(
    "text",
    [
        "Hold: #6 another brief",  # names another brief
        "Hold: #5",  # no reason
        "Please Hold: #5 not the first line",
        "A note.\nHold: #5 on the second line",
    ],
)
def test_ac3_only_a_first_line_naming_this_brief_with_a_reason_holds(proj, stub, text):
    """REQ-037 AC3"""
    brief_with(stub, comment(1, OWNER, text))
    got = data(proj, stub)
    assert got.get("held", []) == [] and started(got) == [5]
    assert got.get("ignored_holds", []) == []


def test_ac3_a_held_brief_with_a_stale_take_is_not_freed(proj, stub):
    """REQ-037 AC3: a take that has gone stale never offers a held brief again."""
    old = iso(-timedelta(hours=30))
    day = old[:10]
    brief_with(
        stub,
        comment(1, "someone", f"taken: s-old {day}", old),
        comment(2, OWNER, HOLD, ago(10)),
    )
    got = data(proj, stub)
    assert got["held"] == [{"brief": 5, "reason": "wait for the design"}] and started(got) == []


def test_ac3_a_held_brief_taken_by_a_running_session_is_listed(proj, stub):
    """REQ-037 AC3: the report lists every held brief, a taken one included."""
    day = iso()[:10]
    brief_with(
        stub,
        comment(1, "someone", f"taken: s-other {day}", ago(30)),
        comment(2, OWNER, HOLD, ago(10)),
    )
    assert data(proj, stub)["held"] == [{"brief": 5, "reason": "wait for the design"}]


def test_ac3_the_login_is_compared_in_any_case(proj, stub):
    """REQ-037 AC3: GitHub logins are case-insensitive."""
    brief_with(stub, comment(1, OWNER.upper(), HOLD))
    assert data(proj, stub)["held"] != []
