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


def test_1168c_a_question_after_an_owner_needed_and_a_push_keeps_question():
    """REQ-039: the fix list on 26ee3af (a maintainers question never closes an `Owner needed:`)."""
    asked = at(5, "builder", "Question: Q-1-1 for the maintainers: may I edit it?", ASKED_AT)
    comments = [owner_needed(), asked]
    assert route.decide(facts(comments=comments, commit=PUSHED)) == "agk:question"
    answer = at(6, "maintainer", "Maintainer answer: yes to both", "2026-11-13T00:45:00Z")
    comments = [owner_needed(), asked, answer]
    assert route.decide(facts(comments=comments, commit=PUSHED)) == "agk:review"
    more = "Question: Q-1-2 for the maintainers: one more?"
    later = at(7, "builder", more, "2026-11-13T00:50:00Z")
    comments = [owner_needed(), answer, later]
    assert route.decide(facts(comments=comments, commit=PUSHED)) == "agk:question"


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


# --- brief #1656 answer 1 (ADR-0690): an owner ask for an approval reads agk:approve ----------


def ask(body: str, login: str = "boss") -> dict:
    return at(4, login, f"Owner needed: {body}", ASKED_AT)


def test_1656_an_amendment_or_spec_approval_ask_gives_approve_a_plain_one_question():
    """REQ-039: brief #1656 answers 1 and 4 (the case of #1654)."""
    for body in (
        "post `Maintainer answer: amendment 196 approved`",
        "post `Approve: SPEC-0032` on the head",
        "two asks: Maintainer answer: amendment 197 approved, and a size ruling",
    ):
        state = route.pr_state(facts(comments=[ask(body)], commit=PUSHED))
        assert state == ("agk:approve", "owner"), body
        assert route.decide(facts(draft=True, comments=[ask(body)])) == "agk:approve", body
    plain = ask("a size ruling on this pull request")
    assert route.decide(facts(comments=[plain], commit=PUSHED)) == "agk:question"
    stranger = ask("Maintainer answer: amendment 196 approved", login="stranger")
    assert route.decide(facts(comments=[stranger], commit=PUSHED)) == "agk:review"


def test_1656_the_owner_answers_close_the_approval_ask_as_today():
    """REQ-039: brief #1656 answer 1 (`asks_owner` closes both forms)."""
    asked = ask("post `Maintainer answer: amendment 196 approved`")
    for line in ("Maintainer answer: amendment 196 approved", f"Approve: {HEAD[:7]} SPEC-0032"):
        answer = at(6, "maintainer", line, "2026-11-13T00:45:00Z")
        comments = [asked, covered_fix_list(), answer]
        assert route.decide(facts(comments=comments, commit=PUSHED)) == "agk:merge-ready", line
    parked = facts(comments=[asked], labels=["agk:parked"])
    assert route.decide(parked) == "agk:parked"


# --- brief #1534 answer 5 (ADR-0646): the router unparks on the answer's own run ---------------


def comment_event(body: str, action: str = "created") -> dict:
    return {
        "action": action,
        "issue": {"number": 7, "pull_request": {}},
        "comment": {"body": body},
        "repository": REPO_INFO,
    }


def test_1534_only_an_owner_answer_on_a_pull_request_starts_the_unpark():
    """REQ-066: brief #1534 answer 5: a created answer comment on a pull request; nothing else."""
    for line in ("Maintainer answer: accept " + HEAD, "Answer: Q-7-1 yes", "Approve: x"):
        assert route.owner_answer_event("issue_comment", comment_event(line)), line
    assert not route.owner_answer_event("issue_comment", comment_event("Report: abc ready"))
    assert not route.owner_answer_event("issue_comment", comment_event("Answer: x", "edited"))
    brief = {**comment_event("Answer: Q-7-1 yes"), "issue": {"number": 7}}
    assert not route.owner_answer_event("issue_comment", brief)
    assert not route.owner_answer_event("pull_request", comment_event("Answer: Q-7-1 yes"))


def test_1534_the_router_unparks_through_the_one_owner_step(monkeypatch, tmp_path):
    """REQ-066: brief #1534 answer 5 and Q-1534-1: the unpark half only, with the shared people."""
    import session

    seen: list = []

    def apply(repo, n, settings, listed, answerers, now, **kw):
        assert callable(kw.pop("carried"))  # brief #1616 answer 2: a check that never fetches
        seen.append((repo, n, listed, answerers, kw))
        return ("unpark", "Q-7-1")

    monkeypatch.setattr(session, "owner_people", lambda root, pr: ({"boss"}, {"boss", "owner"}))
    monkeypatch.setattr(session, "owner_apply", apply)
    assert route.owner_unpark("acme/widgets", 7, tmp_path) == "#7 unparked Q-7-1 (brief #1534)"
    assert seen == [("acme/widgets", 7, {"boss"}, {"boss", "owner"}, {"unpark_only": True})]
    monkeypatch.setattr(session, "owner_apply", lambda *a, **k: None)
    assert route.owner_unpark("acme/widgets", 7, tmp_path) is None


def test_1534_the_answer_comment_run_removes_the_wait_park(proj, stub, tmp_path):  # noqa: F811
    """REQ-066: brief #1534 answer 5, `Measured:` after: the answer's own router run unparks."""
    stub.pull(7, labels=["agk:parked"])
    asked = at(3, "builder", "Question: Q-7-1 for the maintainers: which?", ASKED_AT)
    mark = at(4, "boss", "Parked-by: wait Q-7-1", "2026-11-13T00:50:00Z")
    answer = at(5, "maintainer", "Answer: Q-7-1 the smaller one", "2026-11-13T00:49:59Z")
    stub.serve("issues/7/comments", [asked, answer, mark])
    stub.serve(f"commits/{HEAD}", PUSHED)
    proc = run_router(proj, stub, tmp_path, "issue_comment", comment_event(answer["body"]))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "#7 unparked Q-7-1 (brief #1534)" in proc.stdout
    writes = stub.writes()
    assert any(w[0] == "DELETE" and "agk%3Aparked" in w[1] for w in writes), writes
    assert any("Unparked-by: answer Q-7-1" in " ".join(w[2]) for w in writes), writes


# --- brief #1567 (ADR-0657): the owner's Report on its own parked pull request unparks it -------


def labelled_event(body: str, labels=("agk:parked",), action: str = "created") -> dict:
    event = comment_event(body, action)
    event["issue"] = {**event["issue"], "labels": [{"name": n} for n in labels]}
    return event


def test_1567_a_ready_report_on_a_parked_pull_request_starts_the_unpark():
    """REQ-066: brief #1567 answer 2, `execution` hosted: the router's own run on a ready report
    on a parked pull request; any other report, label or event starts nothing."""
    assert route.owner_report_event(
        "issue_comment", labelled_event(f"Report: {HEAD} ready for review")
    )
    assert route.owner_report_event(
        "issue_comment", labelled_event("Report: abc1234 merge of main")
    )
    assert not route.owner_report_event(
        "issue_comment", labelled_event("Report: abc1234 handing over: done")
    )
    assert not route.owner_report_event(
        "issue_comment", labelled_event("Report: abc1234 ready for review", ())
    )
    assert not route.owner_report_event(
        "issue_comment", labelled_event("Report: abc1234 ready for review", action="edited")
    )
    brief = {**labelled_event("Report: abc1234 ready for review"), "issue": {"number": 7}}
    assert not route.owner_report_event("issue_comment", brief)
    assert not route.owner_answer_event("issue_comment", comment_event("Report: abc ready"))
