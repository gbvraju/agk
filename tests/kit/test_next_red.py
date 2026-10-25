"""`session.py next` hands out only the red-branch brief while it is open (SPEC-0032 rule 7).

The brief the router writes passes the shape of a brief with `Priority: 0` and `Advances: none`
(an amendment of SPEC-0034 rule 2); `next` offers it first and alone, takes it with the one
comment, and prints `default branch red` to every other session. A `gh` stub on `PATH`, saved
responses, no network. REQ-039 AC5.
"""

from __future__ import annotations

import pytest
from test_session import (
    FREE,
    ISSUES,
    REPO,
    issue,
    listing,
    posts,
    session,
    take,
)
from test_session import (
    proj as session_proj,  # noqa: F401  (the fixtures of test_session)
)
from test_session import (
    stub as session_stub,  # noqa: F401
)

TITLE = "The default branch is red"
BODY = (
    'Sentence: "The default branch is red: the required checks of its head fail."\n'
    "Answers:\n1. Failing check: proof\n2. Head: " + "a" * 40 + "\n3. Run: https://x.test/runs/1\n"
    "Priority: 0\nAdvances: none\nTouches: **\nSize: S\n"
)
PRS = f"repos/{REPO}/pulls"


@pytest.fixture
def stub(request):
    return request.getfixturevalue("session_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("session_proj")


def red(number: int = 9, body: str = BODY, title: str = TITLE) -> dict:
    return {
        "number": number,
        "title": title,
        "body": body,
        "html_url": f"https://github.com/{REPO}/issues/{number}",
    }


def nxt(proj, stub, who: str = "s-me"):
    return session(proj, stub, "next", "--session", who)


# --- the shape the router writes (the amendment of SPEC-0034 rule 2) --------------------------


def test_ac5_the_brief_the_router_writes_passes_the_shape():
    """REQ-039 AC5"""
    import session as module

    assert module.brief_problems(BODY) == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b.replace("Advances: none\n", "Advances: REQ-001\n"),
        lambda b: b.replace("Advances: none\n", ""),
        lambda b: b.replace("Priority: 0\n", "Priority: 1\n"),
        lambda b: b.replace("Priority: 0\n", ""),
        lambda b: b.replace("Priority: 0\n", "Priority: 4\n"),
        lambda b: b.replace("Priority: 0\n", "Priority: 0\nPriority: 0\n"),
        lambda b: b.replace("Touches: **\n", ""),
        lambda b: b.replace("Advances: none", "Advances: None"),
    ],
)
def test_ac5_advances_none_and_priority_0_are_allowed_only_together(mutation):
    """REQ-039 AC5: the pair is the router's; either alone is a problem."""
    import session as module

    assert module.brief_problems(mutation(BODY)) != []


def test_ac5_an_ordinary_brief_may_not_use_the_pair_apart_and_is_unchanged():
    """REQ-039 AC5"""
    import session as module

    plain = FREE
    assert module.brief_problems(plain) == []
    assert module.brief_problems(plain + "Priority: 2\n") == []
    assert module.brief_problems(plain + "Priority: 0\n") != []


def test_ac5_a_red_brief_is_the_one_titled_so_with_priority_0():
    """REQ-039 AC5"""
    import session as module

    assert module.is_red(red())
    assert not module.is_red(red(title="The default branch is not red"))
    assert not module.is_red(red(body=BODY.replace("Priority: 0\n", "")))
    assert not module.is_red({**red(), "pull_request": {}})


# --- next ---------------------------------------------------------------------------------------


def test_ac5_next_hands_out_the_red_brief_before_any_other_and_takes_it(proj, stub):
    """REQ-039 AC5"""
    listing(stub, [issue(5, FREE), red(9)])
    stub.serve(f"{ISSUES}/9/comments", [], nth=1)
    stub.serve(f"{ISSUES}/9/comments", [take(1, "s-me", login="me")], nth=2)
    out = nxt(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.startswith("brief #9\n") and "Priority: 0" in out.stdout
    assert len(posts(stub)) == 1 and posts(stub)[0][1].endswith("/issues/9/comments")
    assert not any("issues/5" in c[1] for c in stub.calls())


def test_ac5_next_does_not_offer_a_stalled_pull_request_while_the_branch_is_red(proj, stub):
    """REQ-039 AC5: only that brief."""
    listing(stub, [red(9)])
    stub.serve(PRS, [{"number": 7, "draft": True, "labels": []}])
    stub.serve(f"{ISSUES}/9/comments", [], nth=1)
    stub.serve(f"{ISSUES}/9/comments", [take(1, "s-me", login="me")], nth=2)
    out = nxt(proj, stub)
    assert out.stdout.startswith("brief #9\n")
    assert not any(c[1].startswith(PRS) for c in stub.calls())


def test_ac5_another_session_gets_default_branch_red_and_nothing_else(proj, stub):
    """REQ-039 AC5"""
    listing(stub, [issue(5, FREE), red(9)])
    stub.serve(f"{ISSUES}/9/comments", [take(1, "s-other")])
    out = nxt(proj, stub)
    assert out.returncode == 1
    assert out.stdout.splitlines()[-1] == "default branch red"
    assert "brief #" not in out.stdout and posts(stub) == []
    assert not any("issues/5" in c[1] for c in stub.calls())


def test_ac5_the_session_that_holds_the_red_brief_is_given_it_again(proj, stub):
    """REQ-039 AC5"""
    listing(stub, [red(9)])
    stub.serve(f"{ISSUES}/9/comments", [take(1, "s-me", login="me")])
    out = nxt(proj, stub)
    assert out.returncode == 0 and out.stdout.startswith("brief #9\n") and posts(stub) == []


def test_ac5_a_red_brief_that_fails_its_shape_still_stops_the_others(proj, stub):
    """REQ-039 AC5: the branch is red whatever the issue looks like."""
    listing(stub, [issue(5, FREE), red(9, body=BODY.replace("Size: S\n", ""))])
    out = nxt(proj, stub)
    lines = out.stdout.splitlines()
    assert (
        out.returncode == 1
        and lines[0].startswith("skip #9: ")
        and lines[-1] == "default branch red"
    )
    assert "brief #5" not in out.stdout


def test_ac5_a_closed_red_brief_changes_nothing_next_hands_out_the_ordinary_brief(proj, stub):
    """REQ-039 AC5: the router closes it when the branch is green, so it is not in the open list."""
    listing(stub, [issue(5, FREE)])
    stub.serve(PRS, [])
    stub.serve(f"{ISSUES}/5/comments", [], nth=1)
    stub.serve(f"{ISSUES}/5/comments", [take(1, "s-me", login="me")], nth=2)
    out = nxt(proj, stub)
    assert out.returncode == 0 and out.stdout.startswith("brief #5\n")


def test_ac5_a_pull_request_in_the_issue_list_is_not_a_red_brief(proj, stub):
    """REQ-039 AC5"""
    listing(stub, [{**red(9), "pull_request": {}}])
    stub.serve(PRS, [])
    out = nxt(proj, stub)
    assert out.stdout.strip() == "no brief"
