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

import pytest
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
        f = facts(comments=comments, commit=PUSHED, files=CHANGES_0032)  # brief #1735: its spec
        assert route.decide(f) == "agk:merge-ready", line
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


# brief #1735 (ADR-0723): the line is offered alone, for a spec or amendment the change touches
CHANGES_0032 = [
    {"filename": "docs/specs/0032-an-invented-spec.md"},
    {"filename": "docs/runs/proposed-spec-amendments-196.md"},
    {"filename": "docs/runs/proposed-spec-amendments-197.md"},
]


def test_1656_an_amendment_or_spec_approval_ask_gives_approve_a_plain_one_question():
    """REQ-039: brief #1656 answers 1 and 4 (the case of #1654)."""
    for body in (
        "post this line:\n\n`Maintainer answer: amendment 196 approved`",
        "post on the head:\n\nApprove: SPEC-0032\n",
        "two asks, a size ruling and:\n\nMaintainer answer: amendment 197 approved",
    ):
        state = route.pr_state(facts(comments=[ask(body)], commit=PUSHED, files=CHANGES_0032))
        assert state == ("agk:approve", "owner"), body
        draft = facts(draft=True, comments=[ask(body)], files=CHANGES_0032)
        assert route.decide(draft) == "agk:approve", body
    for body in (  # brief #1735 Q-1: with the files unread, a line in a sentence counts as before
        "post `Maintainer answer: amendment 196 approved`",
        "post `Approve: SPEC-0032` on the head",
    ):
        unread = facts(comments=[ask(body)], commit=PUSHED, files=None)
        assert route.pr_state(unread) == ("agk:approve", "owner"), body
    plain = ask("a size ruling on this pull request")
    assert route.decide(facts(comments=[plain], commit=PUSHED)) == "agk:question"
    stranger = ask("Maintainer answer: amendment 196 approved", login="stranger")
    assert route.decide(facts(comments=[stranger], commit=PUSHED)) == "agk:review"


def test_1656_the_owner_answers_close_the_approval_ask_as_today():
    """REQ-039: brief #1656 answer 1 (`asks_owner` closes both forms)."""
    asked = ask("post:\n\n`Maintainer answer: amendment 196 approved`")
    for line in ("Maintainer answer: amendment 196 approved", "Maintainer answer: yes, all"):
        answer = at(6, "maintainer", line, "2026-11-13T00:45:00Z")
        comments = [asked, covered_fix_list(), answer]
        f = facts(comments=comments, commit=PUSHED, files=CHANGES_0032)
        assert route.decide(f) == "agk:merge-ready", line
    other = at(6, "maintainer", f"Approve: {HEAD[:7]} SPEC-0032", "2026-11-13T00:45:00Z")
    f = facts(comments=[asked, covered_fix_list(), other], commit=PUSHED, files=CHANGES_0032)
    assert route.decide(f) == "agk:approve"  # brief #1735 answer 2: another approval, not this one
    unread = facts(comments=[asked, covered_fix_list(), other], commit=PUSHED, files=None)
    assert route.decide(unread) == "agk:merge-ready"  # Q-1735-1: unread files close as before
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
D = "2026-11-22T"  # #1719's day
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
    offered = "Owner needed: post:\n\n`Approve: SPEC-0032`"  # brief #1735: offered alone
    approval = at(41, "boss", offered, "2026-11-22T09:33:00Z")
    both = [cleared_on(), merge_ask("release"), approval]
    spec = {"files": CHANGES_0032}
    assert route.decide(merge_facts(*both, **spec)) == "agk:approve"
    given = at(42, "maintainer", "Approve: SPEC-0032", "2026-11-22T09:40:00Z")
    assert route.decide(merge_facts(*both, given, **spec)) == "agk:owner-merge"
    done = at(43, "maintainer", "Maintainer answer: merged by hand", "2026-11-22T09:50:00Z")
    assert route.decide(merge_facts(*both, given, done, **spec)) == "agk:merge-ready"
    alone = at(42, "maintainer", "Approve: SPEC-0032", "2026-11-22T09:40:00Z")
    assert route.decide(merge_facts(cleared_on(), merge_ask("release"), alone, **spec)) == (
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
        at(
            1,
            login,
            "Question: Q-1710-1 for the maintainers: raise the cap?",
            D + "07:10:01Z",
        ),
        at(2, login, "Owner needed: two small choices\n\nQ-1710-1 first", D + "07:11:38Z"),
        at(3, "builder", "Report: cb86038 ready for review", D + "07:12:54Z"),
        at(4, login, "Parked-by: wait owner-needed\n\nWho: AGK", D + "07:42:11Z"),
        at(5, "maintainer", "Maintainer answer: Q-1710-1 yes", D + "09:08:45Z"),
        at(6, "bot", "Unparked-by: answer owner-needed\n\nWho: AGK", D + "09:08:58Z"),
        at(7, "builder", f"Report: {HEAD} fix list applied", D + "09:16:28Z"),
        at(
            8,
            login,
            f"Verdict: fix list {HEAD}\n\nFinal: {ADR_FILE} Proposed -> Accepted",
            D + "09:27:54Z",
        ),
        at(
            9,
            "builder",
            f"Report: {HEAD} fix list applied: nothing to change",
            D + "09:29:48Z",
        ),
        merge_ask("outside author", number=1719, login=login),
        at(11, login, "Parked-by: wait owner-needed\n\nWho: AGK", D + "10:03:52Z"),
        at(
            12,
            "builder",
            f"Report: {HEAD[:7]} handing over: blocked: owner-needed waits",
            D + "10:03:59Z",
        ),
    ]


def test_1733_6m_pr_1719_shows_owner_merge():
    """REQ-039: brief #1733 `Measured:` and answer 6 (m): before `agk:question`, after
    `agk:owner-merge` (the park itself is the owner wait's, read in test_owner_wait.py)."""
    files = [{"filename": ADR_FILE, "status": "added"}]
    f = facts(number=1719, comments=pr_1719_comments(), commit=MERGE_PUSHED, files=files)
    assert route.decide(f) == "agk:owner-merge"


def test_1733_7_settings_do_not_change_the_reading():
    """REQ-039: brief #1733 answer 7: `auto_merge` (the `merger` fact), local mode (`local`, the
    checks never reported) and a queue-button-only ask (`merge_queue`, Q-1733-2), as the brief
    says."""
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


# --- brief #1735 (ADR-0723): an approval ask is an offered line for this pull request's own spec --

SPEC_0059 = "docs/specs/0059-a-steward-answers-what-the-evidence-settles.md"
SPEC_0050 = "docs/specs/0050-overlapping-work-never-runs-at-once.md"
AMEND_215 = "docs/runs/proposed-spec-amendments-215.md"
AMEND_216 = "docs/runs/proposed-spec-amendments-216.md"
FILES_1723 = [{"filename": AMEND_215, "status": "added"}, {"filename": SPEC_0059}]
FILES_1726 = [{"filename": AMEND_216, "status": "added"}, {"filename": SPEC_0050}]
OFFER = "\n\nIf you agree, post this line on its own:\n\n{}\n\nWho: AGK conductor"


def pr_1723_comments(note: str = "Owner needed:") -> list[dict]:
    """#1723's comments up to 11:57:19Z (read 2026-11-22 12:16 UTC), trimmed, logins invented;
    NOTE is the first word of the conductor's notice at 11:57:19Z."""
    command = route.OWNER_COMMAND.format(1723)
    return [
        at(1, "boss", "Owner needed: the steward rules change (amendment 215)."
           + OFFER.format("Maintainer answer: amendment 215 approved"), D + "07:36:16Z"),
        at(2, "maintainer", "Maintainer answer: amendment 215 approved\nWho: ProductOwner",
           D + "09:09:48Z"),
        at(3, "boss", "Owner needed: the changed rule text needs your approval."
           + OFFER.format("Approve: SPEC-0059"), D + "09:14:08Z"),
        at(4, "maintainer", "Approve: SPEC-0059", D + "10:31:47Z"),
        at(5, "boss", "Owner needed: this change is cleared. To merge it, use the Merge button "
           f"on this pull request (squash), or run on your computer:\n\n{command}\n\nWho: AGK",
           D + "10:34:19Z"),
        at(6, "maintainer", "Maintainer answer: merge it now; I merge with the owner command",
           D + "11:12:54Z"),
        at(7, "maintainer", "Approve: SPEC-0050", D + "11:56:38Z"),
        at(8, "boss", f"{note} the line `Approve: SPEC-0050` just posted here belongs on #1726, "
           "the change that edits SPEC-0050; it does nothing here.\n\nWho: AGK conductor",
           D + "11:57:19Z"),
    ]  # fmt: skip


def f_1723(comments, files=FILES_1723, **kw) -> dict:
    return facts(number=1723, comments=comments, commit=MERGE_PUSHED, files=files, **kw)


def test_1735_5a_pr_1723_a_quoted_misplaced_line_asks_no_approval():
    """REQ-039: brief #1735 `Measured:` and answer 5 (a). Before: `agk:approve`. The conductor's
    notice still is an `Owner needed:` that asks nothing, so it is an owner question (answer 1,
    Q-1735-1); posted as `Note:` (answer 4 (c)) it is no ask at all and nothing is open."""
    f = f_1723(pr_1723_comments())
    assert route.owner_ask(f, f["comments"], f["authors"]) == "agk:question"
    noted = f_1723(pr_1723_comments(note="Note:"))
    assert route.owner_ask(noted, noted["comments"], noted["authors"]) is None
    assert route.approval_ask(pr_1723_comments()[-1]["body"], FILES_1723) == set()


def test_1735_5b_the_real_asks_on_their_own_pull_requests_still_ask():
    """REQ-039: brief #1735 answer 5 (b): amendment 215 and SPEC-0059 on #1723, SPEC-0050 on
    #1726, each `agk:approve` until its line is posted."""
    said = pr_1723_comments()
    assert route.decide(f_1723(said[:1])) == "agk:approve"
    assert route.decide(f_1723(said[:2])) == "agk:review"
    assert route.decide(f_1723(said[:3])) == "agk:approve"
    assert route.decide(f_1723(said[:4])) == "agk:review"
    ask_1726 = at(1, "boss", "Owner needed: the rule text." + OFFER.format("Approve: SPEC-0050"),
                  D + "11:50:46Z")  # fmt: skip
    f = facts(number=1726, comments=[ask_1726], commit=MERGE_PUSHED, files=FILES_1726)
    assert route.decide(f) == "agk:approve"
    given = at(2, "maintainer", "Approve: SPEC-0050", D + "12:10:05Z")
    f = facts(number=1726, comments=[ask_1726, given], commit=MERGE_PUSHED, files=FILES_1726)
    assert route.decide(f) == "agk:review"


def test_1735_5b_an_ask_for_an_amendment_this_pull_request_does_not_change_asks_nothing():
    """REQ-039: brief #1735 answer 1: #1726's first ask named amendment 215, but #1726 changes
    amendment 216; the answer for 216 closes it as a plain owner question."""
    offered = OFFER.format("Maintainer answer: amendment 215 approved")
    wrong = at(1, "boss", "Owner needed: the rule change." + offered, D + "07:34:18Z")
    f = facts(number=1726, comments=[wrong], commit=MERGE_PUSHED, files=FILES_1726)
    assert route.decide(f) == "agk:question"
    answer = at(2, "maintainer", "Maintainer answer: amendment 216 approved", D + "09:10:16Z")
    f = facts(number=1726, comments=[wrong, answer], commit=MERGE_PUSHED, files=FILES_1726)
    assert route.decide(f) == "agk:review"


RECAP = (
    "Owner needed: thank you, your Approve: SPEC-0059 is in. To merge, run "
    + route.OWNER_COMMAND.format(1723)
)


def test_1735_5c_a_merge_ask_that_recaps_an_approval_stays_owner_merge():
    """REQ-039: brief #1735 `Measured:` and answer 5 (c): before `agk:approve`."""
    f = f_1723([cleared_on(), at(40, "boss", RECAP, D + "10:34:19Z")])
    assert route.decide(f) == "agk:owner-merge"


def test_1735_5d_a_merge_ask_with_a_real_approval_ask_approves_first():
    """REQ-039: brief #1735 answer 5 (d) (ADR-0722 decision 2)."""
    ask = at(41, "boss", "Owner needed: the rule text." + OFFER.format("Approve: SPEC-0059"),
             D + "10:35:00Z")  # fmt: skip
    said = [cleared_on(), at(40, "boss", RECAP, D + "10:34:19Z"), ask]
    assert route.decide(f_1723(said)) == "agk:approve"
    given = at(42, "maintainer", "Approve: SPEC-0059", D + "10:40:00Z")
    assert route.decide(f_1723([*said, given])) == "agk:owner-merge"


def open_q(misplaced: str = "Approve: SPEC-0050") -> list[dict]:
    return [
        at(1, "builder", "Question: Q-1723-9 for the maintainers: a or b?", D + "11:00:00Z"),
        at(2, "boss", "Owner needed: Q-1723-9 pick a or b", D + "11:01:00Z"),
        at(3, "maintainer", misplaced, D + "11:56:38Z"),
    ]


def test_1735_5e_a_misplaced_approval_closes_no_open_question():
    """REQ-039: brief #1735 `Measured:` and answer 3, 5 (e): before None."""
    for line in ("Approve: SPEC-0050", f"Approve: {HEAD} SPEC-0050",
                 "Maintainer answer: amendment 216 approved"):  # fmt: skip
        f = f_1723(open_q(line))
        assert route.owner_ask(f, f["comments"], f["authors"]) == "agk:question", line


def test_1735_5f_the_same_approval_on_the_pull_request_that_changes_the_spec_closes():
    """REQ-039: brief #1735 answer 5 (f): it closes as today."""
    f = f_1723(open_q(), files=FILES_1726)
    assert route.owner_ask(f, f["comments"], f["authors"]) is None
    plain = f_1723(open_q("Maintainer answer: no Q id, all done"))
    assert route.owner_ask(plain, plain["comments"], plain["authors"]) is None


@pytest.mark.parametrize(
    ("body", "asked"),
    [
        ("post this:\n\n```\nApprove: SPEC-0059\n```\n", {"SPEC-0059"}),
        ("post this:\n\n`Approve: SPEC-0059`\n", {"SPEC-0059"}),
        ("post this:\n\n   Approve: SPEC-0059   \n", {"SPEC-0059"}),
        ("post\n\nMaintainer answer: amendment 215 approved\n", {"amendment 215"}),
        ("post `Approve: SPEC-0059` on the head", set()),
        ("> Approve: SPEC-0059", set()),
        ("Approve: SPEC-0059 and more", set()),
        ("``Approve: SPEC-0059``", set()),
        ("Approve: SPEC-0050", set()),
        ("Maintainer answer: amendment 216 approved", set()),
    ],
)
def test_1735_5g_a_line_counts_alone_never_inside_a_sentence(body, asked):
    """REQ-039: brief #1735 answers 1 and 5 (g): alone, in a fence or in one pair of backticks."""
    assert route.approval_ask(body, FILES_1723) == asked


def test_1735_5h_an_ask_naming_two_specs_asks_only_the_changed_one():
    """REQ-039: brief #1735 answer 5 (h); and answer 2: each approval closes its own ask."""
    body = "Owner needed: two lines.\n\nApprove: SPEC-0059\n\nApprove: SPEC-0050\n"
    assert route.approval_ask(body, FILES_1723) == {"SPEC-0059"}
    both = FILES_1723 + FILES_1726
    assert route.approval_ask(body, both) == {"SPEC-0059", "SPEC-0050"}
    ask = at(1, "boss", body, D + "10:00:00Z")
    one = at(2, "maintainer", "Approve: SPEC-0050", D + "10:05:00Z")
    two = at(3, "maintainer", "Approve: SPEC-0059", D + "10:06:00Z")
    assert route.decide(f_1723([ask, one], files=both)) == "agk:approve"
    assert route.decide(f_1723([ask, one, two], files=both)) == "agk:review"


def test_1735_5i_a_note_holds_no_state():
    """REQ-039: brief #1735 answers 4 (c) and 5 (i) (Q-1735-2: `Note:` is read by no reader)."""
    note = at(9, "boss", "Note: `Approve: SPEC-0050` belongs on #1726.", D + "11:57:19Z")
    f = f_1723([note])
    assert route.owner_ask(f, f["comments"], f["authors"]) is None
    assert route.decide(f) == "agk:review"


def test_1735_5j_files_that_cannot_be_read_keep_todays_reading():
    """REQ-039: brief #1735 answers 1 and 3 and Q-1735-1 (files None: every match counts, and an
    approval line closes as today)."""
    assert route.approval_ask("post `Approve: SPEC-0050` on the head", None) == {"SPEC-0050"}
    f = f_1723(pr_1723_comments(), files=None)
    assert route.owner_ask(f, f["comments"], f["authors"]) == "agk:approve"
    f = f_1723(open_q(), files=None)
    assert route.owner_ask(f, f["comments"], f["authors"]) is None


@pytest.mark.parametrize("merger", [True, False])
def test_1735_6_settings_do_not_change_the_reading(merger):
    """REQ-039: brief #1735 answer 6 (`auto_merge` as the `merger` fact, local mode, an unlisted
    author, no approvers)."""
    f = f_1723([cleared_on(), at(40, "boss", RECAP, D + "10:34:19Z")], merger=merger)
    assert route.decide(f) == "agk:owner-merge"
    local = f_1723(open_q(), merger=merger, checks=[], local=True)
    assert route.owner_ask(local, local["comments"], local["authors"]) == "agk:question"
    nobody = f_1723(open_q(), files=FILES_1726, approvers=[])
    assert route.owner_ask(nobody, nobody["comments"], nobody["authors"]) == "agk:question"
    stranger = at(1, "stranger", "Owner needed:" + OFFER.format("Approve: SPEC-0059"), D + "09:00Z")
    assert route.decide(f_1723([stranger])) == "agk:review"


def test_1735_the_docstring_names_the_rule():
    """REQ-039: brief #1735 answer 7."""
    assert "ADR-0723" in (route.owner_ask.__doc__ or "")
    assert "ADR-0723" in (route.approval_ask.__doc__ or "")
