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
    comment,
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
        "user": {"login": "github-actions[bot]"},
    }


def nxt(proj, stub, who: str = "s-me"):
    return session(proj, stub, "next", "--session", who, "--take")


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


@pytest.mark.parametrize("login", ["someone", "github-actions", "Github-Actions[bot]", None])
def test_ac5_an_issue_of_the_same_shape_written_by_hand_is_not_the_red_brief(login):
    """REQ-039 AC5: only the router's token opens it (the verdict on aa18501, item 2)."""
    import session as module

    by_hand = {**red(), "user": {"login": login} if login else None}
    assert not module.is_red(by_hand)
    no_user = {k: v for k, v in red().items() if k != "user"}
    assert not module.is_red(no_user)


def test_ac5_a_hand_written_red_shaped_brief_is_an_ordinary_priority_0_brief_not_an_exclusive_one(
    proj, stub
):
    """REQ-039 AC5: a priority-0 brief goes first among the free ones (the verdict on 01fc97c),
    but only the router's issue is handed out alone, and nobody is told `default branch red`."""
    by_hand = {**red(9), "user": {"login": "someone"}}
    listing(stub, [issue(5, FREE), by_hand])
    stub.serve(PRS, [])
    stub.serve(f"{ISSUES}/5/comments", [])
    stub.serve(f"{ISSUES}/9/comments", [], nth=1)
    stub.serve(f"{ISSUES}/9/comments", [take(1, "s-me", login="me")], nth=2)
    out = nxt(proj, stub)
    assert out.returncode == 0 and out.stdout.startswith("brief #9\n")
    assert "default branch red" not in out.stdout


def test_ac5_a_hand_written_red_shaped_brief_that_is_taken_does_not_stop_the_others(proj, stub):
    """REQ-039 AC5: it stops no other session; the ordinary brief is handed out (its `Touches:`
    is narrowed here, because a taken brief that touches everything overlaps every other)."""
    body = BODY.replace("Touches: **", "Touches: elsewhere/**")
    by_hand = {**red(9, body=body), "user": {"login": "someone"}}
    listing(stub, [issue(5, FREE), by_hand])
    stub.serve(PRS, [])
    stub.serve(f"{ISSUES}/9/comments", [take(1, "s-other", login="other")])
    stub.serve(f"{ISSUES}/5/comments", [], nth=1)
    stub.serve(f"{ISSUES}/5/comments", [take(1, "s-me", login="me")], nth=2)
    out = nxt(proj, stub)
    assert out.returncode == 0 and "brief #5" in out.stdout.splitlines()
    assert "default branch red" not in out.stdout


# --- a red branch's fix brief goes before the capacity and the overlap (brief #1052) ----------

FIX_FILE = "scripts/agk/example.py"
SLOTS = '[flow]\nbuilder_start = "assign"\nbuilder_slots = 2\n'


def fix_scene(proj, stub, said_by: str = "boss") -> None:
    """Alarm #9 (the router's), fix brief #10 named by `fix brief filed: #10` on the alarm, and an
    open builder pull request #20 that changes the file the fix touches (the case of #1048)."""
    from test_session_flow import brief, pr
    from test_session_plan import changed

    proj.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    proj.write("agk.toml", SLOTS)
    stub.serve(PRS, [pr(20, 1)])
    changed(stub, 20, ("modified", FIX_FILE))
    listing(stub, [red(9), issue(10, brief(FIX_FILE, priority=1))])
    stub.serve(f"{ISSUES}/9/comments", [comment(1, said_by, "Fix brief filed: #10")])
    stub.serve(f"{ISSUES}/10/comments", [])


def assigned(found: dict) -> list[int]:
    return [row["brief"] for row in found.get("assign", [])]


def test_1052_a_the_plan_assigns_the_fix_brief_and_keeps_is_fixed_by(proj, stub):
    """REQ-039 REQ-041: brief #1052 answers 1 and 2, test (a)."""
    from test_session_plan import data, plan

    fix_scene(proj, stub)
    found = data(proj, stub)
    assert assigned(found) == [10], found
    assert {"brief": 9, "fixed_by": 10, "why": "is fixed by #10"} in found["waits"]
    assert found["capacity"]["slots"] >= 1
    out = plan(proj, stub).stdout
    assert "#9 is fixed by #10." in out
    assert "no brief is ready" not in out
    assert posts(stub) == []


def test_1052_d_a_fix_brief_filed_by_an_unlisted_author_makes_no_fix_brief(proj, stub):
    """REQ-039 REQ-041: brief #1052 answer 1, test (d): only `red_fixes`' rule names a fix."""
    from test_session_plan import data

    fix_scene(proj, stub, said_by="someone")
    found = data(proj, stub)
    assert assigned(found) == [9], found
    assert not any(w.get("fixed_by") == 10 for w in found["waits"])


def test_1052_a_survey_with_no_fix_named_reads_no_pull_request(proj, stub):
    """REQ-039 AC5: brief #1052 answer 3, a red survey that names no fix reads no pull request."""
    import session as module

    listing(stub, [red(9), issue(5, FREE)])
    stub.serve(f"{ISSUES}/9/comments", [])
    found = session(proj, stub, "next", "--session", "s-me")
    assert "brief #9" in found.stdout and "brief #5" not in found.stdout
    assert not any(c[1].startswith(PRS) for c in stub.calls())
    assert module.RED_TITLE == TITLE


def test_1052_a_the_fix_brief_goes_before_a_full_capacity_and_a_taken_alarm(proj, stub):
    """REQ-039 REQ-041: brief #1052 answer 2, capacity at least one: with `max_builders = 1` held
    by the taken alarm (whose `Touches: **` overlaps everything) the fix brief is still assigned."""
    from test_session_plan import data

    fix_scene(proj, stub)
    proj.write("agk.toml", SLOTS + "max_builders = 1\n")
    said = [comment(1, "boss", "Fix brief filed: #10"), take(2, "s2", login="other")]
    stub.serve(f"{ISSUES}/9/comments", said)
    found = data(proj, stub)
    assert assigned(found) == [10], found
    assert found["capacity"]["slots"] == 1


def test_1052_b_next_offers_the_fix_brief_beside_a_taken_alarm(proj, stub):
    """REQ-039 REQ-041: brief #1052 answer 2: `next` offers the fix brief while the alarm, taken
    by another session, would overlap it, and still no other brief."""
    fix_scene(proj, stub)
    said = [comment(1, "boss", "Fix brief filed: #10"), take(2, "s-other", login="other")]
    stub.serve(f"{ISSUES}/9/comments", said)
    out = session(proj, stub, "next", "--session", "s-me")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "brief #10" in out.stdout.splitlines()
    assert posts(stub) == []


def test_1052_a_lower_pull_request_that_names_the_alarm_makes_no_fix_brief(proj, stub):
    """REQ-039 REQ-041: brief #1052 answer 1: an open pull request #8, lower than brief #10, that
    names the alarm is `red_fixes`' `fixed_by`, so #10 is no fix brief and is not kept."""
    from test_session_flow import pr
    from test_session_plan import data

    fix_scene(proj, stub)
    stub.serve(PRS, [pr(20, 1), {**pr(8, None), "body": "Fixes #9\nAdvances: REQ-039\n"}])
    found = data(proj, stub)
    assert assigned(found) == [], found
    assert {"brief": 9, "fixed_by": 8, "why": "is fixed by #8"} in found["waits"]
    out = session(proj, stub, "claim", "--session", "s-me", "--brief", "10")
    assert out.returncode == 1, out.stdout + out.stderr
    assert out.stdout.strip() == f"skip #10: waits for pull request #20 (it changes {FIX_FILE})"
    assert posts(stub) == []
