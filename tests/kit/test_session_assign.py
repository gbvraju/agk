"""Per-build claims, `watch --assign` and `[flow] assign` (SPEC-0034 rules 5 and 12; REQ-041).

`claim` takes one build of a brief with `taken: <id> <date> build (<x>)`. A live take of a build is
never taken twice, a take without a build part still claims the whole brief, `released:` frees at
once. `watch --assign <id>` ends on an `Assign:` line by a listed verdict author on the
`agk-conductor` issue. `after` reads `[flow] assign`. A `gh` stub on `PATH`, saved responses, no
network.
"""

from __future__ import annotations

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_session import (
    FREE,
    ISSUES,
    comment,
    issue,
    listing,
    posts,
    session,
)
from test_session import (
    proj as session_proj,  # noqa: F401  (the fixtures of test_session)
)
from test_session import (
    stub as session_stub,  # noqa: F401
)

ROOT = Path(__file__).resolve().parents[2]
DAY = datetime.now(UTC).strftime("%Y-%m-%d")
BRIEF = f"{ISSUES}/5/comments"
CONDUCTOR = ISSUES  # the stub ignores the query
CONDUCTOR_ISSUE = {"number": 204, "title": "Conductor: assignments"}
COMMENTS = f"{ISSUES}/204/comments"


@pytest.fixture
def stub(request):
    return request.getfixturevalue("session_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("session_proj")


def took(cid: int, who: str, build: str | None = None, login: str = "someone") -> dict:
    part = f" build ({build})" if build else ""
    return comment(cid, login, f"taken: {who} {DAY}{part}")


def claim(proj, stub, build: str | None = "b", who: str = "s-me"):
    extra = ("--build", build) if build else ()
    return session(proj, stub, "claim", "--session", who, "--brief", "5", *extra)


def test_ac4_a_build_is_claimed_with_one_post_that_names_the_build(proj, stub):
    """REQ-041 AC4"""
    stub.serve(BRIEF, [], nth=1)
    stub.serve(BRIEF, [took(1, "s-me", "b", "me")], nth=2)
    out = claim(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #5 build (b)"
    assert posts(stub) == [["POST", BRIEF, ["-f", f"body=taken: s-me {DAY} build (b)"]]]


def test_ac4_a_live_take_of_the_same_build_is_never_taken_twice(proj, stub):
    """REQ-041 AC4"""
    stub.serve(BRIEF, [took(1, "s-other", "b")])
    out = claim(proj, stub)
    assert out.returncode == 1 and "taken by s-other" in out.stdout and posts(stub) == []


def test_ac4_another_build_of_the_same_brief_is_free(proj, stub):
    """REQ-041 AC4"""
    stub.serve(BRIEF, [took(1, "s-other", "a")], nth=1)
    stub.serve(BRIEF, [took(1, "s-other", "a"), took(2, "s-me", "b", "me")], nth=2)
    out = claim(proj, stub)
    assert out.returncode == 0 and len(posts(stub)) == 1


def test_ac4_a_whole_brief_take_by_another_session_blocks_every_build(proj, stub):
    """REQ-041 AC4"""
    stub.serve(BRIEF, [took(1, "s-other")])
    assert claim(proj, stub).returncode == 1 and posts(stub) == []


def test_ac4_a_claim_without_a_build_claims_the_whole_brief(proj, stub):
    """REQ-041 AC4"""
    stub.serve(BRIEF, [], nth=1)
    stub.serve(BRIEF, [took(1, "s-me", None, "me")], nth=2)
    out = claim(proj, stub, build=None)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #5"
    assert posts(stub)[0][2] == ["-f", f"body=taken: s-me {DAY}"]


def test_ac4_a_build_take_by_another_session_blocks_a_whole_brief_claim(proj, stub):
    """REQ-041 AC4"""
    stub.serve(BRIEF, [took(1, "s-other", "a")])
    assert claim(proj, stub, build=None).returncode == 1


def test_ac4_released_frees_a_build_and_names_the_session(proj, stub):
    """REQ-041 AC4"""
    released = comment(2, "someone", "released: s-other build (b)")
    stub.serve(BRIEF, [took(1, "s-other", "b"), released], nth=1)
    stub.serve(BRIEF, [took(1, "s-other", "b"), released, took(3, "s-me", "b", "me")], nth=2)
    assert claim(proj, stub).returncode == 0
    stub.serve(BRIEF, [took(1, "s-other", "b"), comment(2, "x", "released: s-other")])
    assert claim(proj, stub).returncode == 0  # a release without a build frees every build


def test_ac4_released_of_another_build_frees_nothing(proj, stub):
    """REQ-041 AC4"""
    stub.serve(BRIEF, [took(1, "s-other", "b"), comment(2, "x", "released: s-other build (a)")])
    assert claim(proj, stub).returncode == 1


def test_ac4_next_leaves_a_brief_with_a_live_build_take_of_another_session(proj, stub):
    """REQ-041 AC4"""
    listing(stub, [issue(5, FREE)])
    stub.serve(BRIEF, [took(1, "s-other", "b")])
    out = session(proj, stub, "next", "--session", "s-me")
    assert "skip #5: taken by s-other" in out.stdout and posts(stub) == []


def test_ac4_claim_needs_a_session_a_brief_and_a_plain_build(proj, stub):
    """REQ-041 AC4"""
    assert session(proj, stub, "claim", "--session", "s-me").returncode == 2
    assert session(proj, stub, "claim", "--session", "s-me", "--brief", "x").returncode == 2
    bad = ("claim", "--session", "s-me", "--brief", "5", "--build", "a b")
    assert session(proj, stub, *bad).returncode == 2


# --- watch --assign -------------------------------------------------------------------------------


def request(cid: int, who: str = "s-me") -> dict:
    return comment(cid, "builder", f"Request: {who} new")


def asked(stub, comments: list, polls: list[list] | None = None) -> None:
    stub.serve(CONDUCTOR, [CONDUCTOR_ISSUE])
    stub.serve(COMMENTS, comments, nth=1)
    for i, poll in enumerate(polls or [], start=2):
        stub.serve(COMMENTS, poll, nth=i)


def assign(proj, stub, timeout: str = "5"):
    args = ("watch", "--assign", "s-me", "--interval", "0", "--timeout", timeout)
    return session(proj, stub, *args)


@pytest.mark.parametrize(
    ("line", "printed"),
    [
        ("Assign: s-me #9 build (b)", "assign #9 build (b)"),
        ("Assign: s-me #9", "assign #9"),
        ("Assign: s-me none", "assign none"),
    ],
)
def test_ac5_assign_ends_on_a_line_for_this_session_by_a_listed_author(proj, stub, line, printed):
    """REQ-041 AC5"""
    answer = comment(2, "boss", f"{line}\n\nbecause the plan says so")
    asked(stub, [request(1)], [[request(1), answer]])
    out = assign(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == printed
    assert posts(stub) == []


def test_ac5_assign_ignores_an_unlisted_account_and_another_session_and_other_lines(proj, stub):
    """REQ-041 AC5"""
    c = [request(1)]
    wrong = [
        comment(2, "stranger", "Assign: s-me #9"),
        comment(3, "boss", "Assign: s-other #9"),
        comment(4, "boss", "Assign: s-me #9 and more"),
        comment(5, "boss", "see Assign: s-me #9"),
    ]
    asked(stub, c, [c + wrong, c + wrong + [comment(6, "second", "Assign: s-me #7")]])
    assert assign(proj, stub).stdout.strip() == "assign #7"


def test_ac5_assign_takes_only_a_line_after_the_request_of_this_session(proj, stub):
    """REQ-041 AC5"""
    old = comment(1, "boss", "Assign: s-me #3")
    asked(stub, [old, request(2)], [[old, request(2), comment(3, "boss", "Assign: s-me #9")]])
    assert assign(proj, stub).stdout.strip() == "assign #9"


def test_ac5_assign_ends_with_assign_timeout_when_no_answer_comes(proj, stub):
    """REQ-041 AC5"""
    asked(stub, [request(1)])
    out = assign(proj, stub, timeout="0")
    assert out.returncode == 0 and out.stdout.strip() == "assign-timeout"


def test_ac5_assign_needs_exactly_one_open_conductor_issue(proj, stub):
    """REQ-041 AC5"""
    stub.serve(CONDUCTOR, [])
    out = assign(proj, stub)
    assert out.returncode == 2 and "agk-conductor" in out.stdout
    stub.serve(CONDUCTOR, [CONDUCTOR_ISSUE, {"number": 205}])
    assert assign(proj, stub).returncode == 2


def test_ac5_watch_takes_one_of_pr_merged_or_assign(proj, stub):
    """REQ-041 AC5"""
    assert session(proj, stub, "watch", "--assign", "s-me", "--pr", "7").returncode == 2
    assert session(proj, stub, "watch", "--assign", "a b").returncode == 2


# --- after and [flow] assign ----------------------------------------------------------------------


def configure(proj, value: str | None) -> None:
    text = "" if value is None else f'[flow]\nassign = "{value}"\n'
    proj.write("agk.toml", f'default_branch = "main"\npr_mode = "flow"\n{text}')


def after(proj, stub):
    return session(proj, stub, "after", "--session", "s-me")


def test_ac5_assign_next_is_the_default_and_runs_next(proj, stub):
    """REQ-041 AC5"""
    listing(stub, [issue(5, FREE)])
    stub.serve(BRIEF, [took(1, "s-me", None, "me")])
    for value in (None, "next"):
        configure(proj, value)
        out = after(proj, stub)
        assert out.returncode == 0 and out.stdout.startswith("brief #5")


def test_ac5_assign_conductor_names_the_issue_and_starts_nothing(proj, stub):
    """REQ-041 AC5"""
    configure(proj, "conductor")
    stub.serve(CONDUCTOR, [CONDUCTOR_ISSUE])
    out = after(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "ask the conductor on #204"
    assert posts(stub) == [] and not any(
        ISSUES + "?state=open&labels=agk-brief" in str(c) for c in stub.calls()
    )


@pytest.mark.parametrize("value", ["both", "", "Conductor"])
def test_ac5_an_invalid_assign_is_refused_naming_the_setting_not_the_value(proj, stub, value):
    """REQ-041 AC5"""
    configure(proj, value)
    out = after(proj, stub)
    assert out.returncode == 2 and "assign" in out.stdout and "[flow]" in out.stdout
    assert value not in out.stdout or value == ""


def test_ac5_this_repository_sets_assign_to_conductor():
    """REQ-041 AC5"""
    data = tomllib.loads((ROOT / "agk.toml").read_text(encoding="utf-8"))
    assert data["flow"]["assign"] == "conductor"
