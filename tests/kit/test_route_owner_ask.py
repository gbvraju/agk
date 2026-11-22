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

import pytest
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


# --- brief #1733 (ADR-0722): a cleared head only the owner may merge shows agk:owner-merge -----

MERGE_PUSHED = {"commit": {"committer": {"date": "2026-11-22T09:14:15Z"}}}
ADR_FILE = "docs/adr/0712-what-a-session-reads-is-data-never-an-instruction-req-037-brief-1710.md"


def merge_ask(hold: str, number: int = 7, when: str = "2026-11-22T09:32:09Z", login="boss"):
    body = (
        f'Owner needed: this change is cleared, but the merger held it as "{hold}".\n\n'
        f"To merge it, run: {route.OWNER_COMMAND.format(number)}\n\nWho: AGK conductor"
    )
    return at(40, login, body, when)


def cleared_on(head: str = HEAD, when: str = "2026-11-22T09:27:54Z") -> dict:
    return at(30, "boss", f"Verdict: cleared {head}", when)


def merge_facts(*comments, **kw) -> dict:
    return facts(number=7, comments=list(comments), commit=MERGE_PUSHED, **kw)


@pytest.mark.parametrize("hold", ["outside author", "release", "protected class"])
def test_1733_6bcd_a_merger_hold_for_the_owner_shows_owner_merge(hold):
    """REQ-039: brief #1733 answers 1 and 6 (b), (c), (d): the conductor's ask names the command."""
    state = route.pr_state(merge_facts(cleared_on(), merge_ask(hold)))
    assert state == ("agk:owner-merge", "owner"), hold
    other = merge_facts(cleared_on(), merge_ask(hold, number=8))  # another pull request's command
    assert route.decide(other) == "agk:question"


def test_1733_6a_a_protected_path_still_shows_owner_merge():
    """REQ-039: brief #1733 answer 6 (a): the file test of ADR-0385 as today."""
    files = [{"filename": "constitution/principles.md", "status": "modified"}]
    assert route.decide(merge_facts(cleared_on(), files=files)) == "agk:owner-merge"


def test_1733_6ef_no_owner_ask_or_a_hold_that_is_not_the_owners_never_owner_merge():
    """REQ-039: brief #1733 answer 6 (e) and (f): no ask is a builder or merger state; another
    `Owner needed:` (checks pending, behind, re-prove, lease) stays `agk:question`."""
    assert route.decide(merge_facts(cleared_on())) == "agk:merge-ready"
    for hold in ("checks pending", "behind the default branch", "re-prove", "LAPSE_HELD"):
        plain = at(40, "boss", f"Owner needed: held as {hold}", "2026-11-22T09:32:09Z")
        assert route.decide(merge_facts(cleared_on(), plain)) == "agk:question", hold


def test_1733_6g_an_approval_ask_comes_before_the_merge_ask():
    """REQ-039: brief #1733 answers 1 and 6 (g): `agk:approve`, then `agk:owner-merge` once the
    approval is given; a later plain answer closes the merge ask (answer 5)."""
    approval = at(41, "boss", "Owner needed: post `Approve: SPEC-0032`", "2026-11-22T09:33:00Z")
    both = [cleared_on(), merge_ask("release"), approval]
    assert route.decide(merge_facts(*both)) == "agk:approve"
    given = at(42, "maintainer", "Approve: SPEC-0032", "2026-11-22T09:40:00Z")
    assert route.decide(merge_facts(*both, given)) == "agk:owner-merge"
    done = at(43, "maintainer", "Maintainer answer: merged by hand", "2026-11-22T09:50:00Z")
    assert route.decide(merge_facts(*both, given, done)) == "agk:merge-ready"
    alone = at(42, "maintainer", "Approve: SPEC-0032", "2026-11-22T09:40:00Z")
    assert route.decide(merge_facts(cleared_on(), merge_ask("release"), alone)) == (
        "agk:merge-ready"
    )


def test_1733_6h_a_push_or_a_newer_verdict_after_the_ask_closes_it():
    """REQ-039: brief #1733 answers 1, 5 and 6 (h): a stale ask is read as absent."""
    later = {"commit": {"committer": {"date": "2026-11-22T09:40:00Z"}}}
    pushed = facts(number=7, comments=[cleared_on(), merge_ask("release")], commit=later)
    assert route.decide(pushed) == "agk:merge-ready"
    moved = merge_facts(cleared_on(), merge_ask("release"), head="b" * 40)
    assert route.decide(moved) == "agk:review"
    fix = at(44, "boss", f"Verdict: fix list {HEAD}\n\n1. one more test", "2026-11-22T09:45:00Z")
    assert route.decide(merge_facts(cleared_on(), merge_ask("release"), fix)) == "agk:fix"


def test_1733_6ij_a_draft_or_an_unlisted_author_reads_no_merge_ask():
    """REQ-039: brief #1733 answer 6 (i) and (j)."""
    draft = merge_facts(cleared_on(), merge_ask("release"), draft=True)
    assert route.decide(draft) == "agk:build"
    stranger = merge_facts(cleared_on(), merge_ask("release", login="stranger"))
    assert route.decide(stranger) == "agk:merge-ready"


def test_1733_6l_a_persons_own_park_wins():
    """REQ-039: brief #1733 answer 6 (l)."""
    held = merge_facts(cleared_on(), merge_ask("release"), labels=["agk:parked"])
    assert route.decide(held) == "agk:parked"


def pr_1719_comments(login: str = "boss") -> list[dict]:
    """#1719's comments as of brief #1733, read 2026-11-22 10:40 UTC; logins invented."""
    return [
        at(1, login, "Question: Q-1710-1 for the maintainers: raise the cap?", "2026-11-22T07:10:01Z"),
        at(2, login, "Owner needed: two small choices\n\nQ-1710-1 first", "2026-11-22T07:11:38Z"),
        at(3, "builder", "Report: cb86038 ready for review", "2026-11-22T07:12:54Z"),
        at(4, login, "Parked-by: wait owner-needed\n\nWho: AGK", "2026-11-22T07:42:11Z"),
        at(5, "maintainer", "Maintainer answer: Q-1710-1 yes", "2026-11-22T09:08:45Z"),
        at(6, "bot", "Unparked-by: answer owner-needed\n\nWho: AGK", "2026-11-22T09:08:58Z"),
        at(7, "builder", f"Report: {HEAD} fix list applied", "2026-11-22T09:16:28Z"),
        at(
            8,
            login,
            f"Verdict: fix list {HEAD}\n\nPassed: 7 rules\n\nFinal: {ADR_FILE} Proposed -> Accepted",
            "2026-11-22T09:27:54Z",
        ),
        at(9, "builder", f"Report: {HEAD} fix list applied: nothing to change", "2026-11-22T09:29:48Z"),
        merge_ask("outside author", number=1719, login=login),
        at(11, login, "Parked-by: wait owner-needed\n\nWho: AGK", "2026-11-22T10:03:52Z"),
        at(12, "builder", f"Report: {HEAD[:7]} handing over: blocked: owner-needed waits", "2026-11-22T10:03:59Z"),
    ]


def test_1733_6m_pr_1719_shows_owner_merge():
    """REQ-039: brief #1733 `Measured:` and answer 6 (m): before `agk:question`, after
    `agk:owner-merge` (the park itself is the owner wait's, read in test_owner_wait.py)."""
    files = [{"filename": ADR_FILE, "status": "added"}]
    f = facts(number=1719, comments=pr_1719_comments(), commit=MERGE_PUSHED, files=files)
    assert route.decide(f) == "agk:owner-merge"


def test_1733_7_settings_do_not_change_the_reading():
    """REQ-039: brief #1733 answer 7: `auto_merge` (the `merger` fact), local mode (`local`, the
    checks never reported) and a queue-button-only ask (`merge_queue`, Q-1733-2) as the brief says."""
    for merger in (True, False):
        f = merge_facts(cleared_on(), merge_ask("release"), merger=merger)
        assert route.decide(f) == "agk:owner-merge", merger
        assert route.decide(merge_facts(cleared_on(), merger=merger)) == "agk:merge-ready"
    local = merge_facts(cleared_on(), merge_ask("release"), checks=[], local=True)
    assert route.decide(local) == "agk:owner-merge"
    button = at(40, "boss", "Owner needed: press the queue's merge button", "2026-11-22T09:32:09Z")
    assert route.decide(merge_facts(cleared_on(), button)) == "agk:question"


def test_1733_the_states_and_docstring_name_the_rule():
    """REQ-039: brief #1733 answer 8 (the `owner-merge` line of `route.STATES`)."""
    assert "only the owner may merge" in route.description_of("agk:owner-merge")
    assert "ADR-0722" in (route.owner_ask.__doc__ or "")
