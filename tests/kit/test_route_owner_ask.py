"""An owner ask stays open until the owner answers, even after a push (brief #1168, ADR-0497).

Amendment 172 to SPEC-0032, amending amendment 150 item 1 and Q-846-4: an `Owner needed:` by a
listed verdict author closes only at a later `Maintainer answer:` or `Approve:` by an account in
`spec_approvers`; a new head no longer closes it. A builder's `Question: Q-... for the maintainers`
still closes at a new head. The measured case is #1165 of 2026-11-13: an `Owner needed:` at
00:17Z, a merge of the default branch at 00:33Z, the label `agk:question` removed at 00:33Z.
Saved facts and a `gh` stub only; invented data, no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

from test_route import HEAD, REPO_INFO, facts, proj, run_router, stub  # noqa: F401

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import route  # noqa: E402

ASKED_AT = "2026-11-13T00:17:11Z"
PUSHED = {"commit": {"committer": {"date": "2026-11-13T00:33:00Z"}}}


def at(cid: int, login: str, body: str, when: str) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


def owner_needed() -> dict:
    return at(4, "boss", "Owner needed: a size ruling on this pull request", ASKED_AT)


def covered_fix_list() -> dict:
    return at(5, "boss", f"Verdict: cleared {HEAD[:7]}", "2026-11-13T00:43:48Z")


def test_1168a_an_owner_needed_followed_by_a_push_keeps_question():
    """REQ-039: brief #1168 test (a) (a new head no longer closes an `Owner needed:`)."""
    comments = [owner_needed()]
    assert route.pr_state(facts(comments=comments, commit=PUSHED)) == ("agk:question", "owner")
    cleared = [owner_needed(), covered_fix_list()]
    assert route.decide(facts(comments=cleared, commit=PUSHED)) == "agk:question"
    draft = facts(draft=True, comments=comments, commit=PUSHED)
    assert route.decide(draft) == "agk:question"


def test_1168b_a_later_maintainer_answer_by_a_spec_approver_clears_it():
    """REQ-039: brief #1168 test (b) (only the owner's answer closes it)."""
    for line in ("Maintainer answer: the size is fine", f"Approve: {HEAD[:7]} SPEC-0032"):
        answer = at(6, "maintainer", line, "2026-11-13T00:45:00Z")
        comments = [owner_needed(), covered_fix_list(), answer]
        assert route.decide(facts(comments=comments, commit=PUSHED)) == "agk:merge-ready", line
    stranger = at(6, "stranger", "Maintainer answer: the size is fine", "2026-11-13T00:45:00Z")
    comments = [owner_needed(), covered_fix_list(), stranger]
    assert route.decide(facts(comments=comments, commit=PUSHED)) == "agk:question"
    builder = at(6, "builder", "Maintainer answer: the size is fine", "2026-11-13T00:45:00Z")
    comments = [owner_needed(), covered_fix_list(), builder]
    assert route.decide(facts(comments=comments, commit=PUSHED)) == "agk:question"


def test_1168b_an_answer_before_the_ask_does_not_close_it():
    """REQ-039: brief #1168 answer 1 (a later answer, in the order GitHub lists the comments)."""
    early = at(3, "maintainer", "Maintainer answer: an earlier question", "2026-11-13T00:10:00Z")
    comments = [early, owner_needed(), covered_fix_list()]
    assert route.decide(facts(comments=comments, commit=PUSHED)) == "agk:question"


def test_1168c_a_question_for_the_maintainers_followed_by_a_push_still_clears():
    """REQ-039: brief #1168 test (c) (a builder's question closes at a new head as today)."""
    asked = at(4, "builder", "Question: Q-1-1 for the maintainers: may I edit it?", ASKED_AT)
    assert route.decide(facts(draft=True, comments=[asked], commit=PUSHED)) == "agk:build"
    early = {"commit": {"committer": {"date": "2026-11-13T00:00:00Z"}}}
    assert route.decide(facts(draft=True, comments=[asked], commit=early)) == "agk:question"


def test_1168c_an_unlisted_owner_needed_still_asks_nothing():
    """REQ-039: brief #1168 answer 1 (`Owner needed:` counts only by a listed verdict author)."""
    unlisted = at(4, "stranger", "Owner needed: anything", ASKED_AT)
    assert route.decide(facts(comments=[unlisted], commit=PUSHED)) == "agk:review"


def test_1168a_the_router_keeps_the_question_label_after_a_push(proj, stub, tmp_path):  # noqa: F811
    """REQ-039: brief #1168 `Measured:` after (the router run of #1165's push keeps the label)."""
    stub.pull(7, labels=["agk:question"])
    stub.serve("issues/7/comments", [owner_needed(), covered_fix_list()])
    stub.serve(f"commits/{HEAD}", PUSHED)
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    proc = run_router(proj, stub, tmp_path, "pull_request", event)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not any("agk%3Aquestion" in w[1] or "agk:question" in w[1] for w in stub.writes())
    assert not any("agk:merge-ready" in " ".join(w[2]) for w in stub.writes())


def test_1168_the_docstring_names_the_rule():
    """REQ-039: brief #1168 answer 2 (`asks_owner` says how each ask closes)."""
    text = route.asks_owner.__doc__ or ""
    assert "ADR-0497" in text and "new head" in text
