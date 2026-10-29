"""session.py review-queue: the pull requests that need a conductor's verdict, and why (brief 306).

REQ-039. The rules of a review pass, learned in a project pilot (#284): review on `agk:review`, on
a `Question:`, `Report:`, `Correction:` or `Maintainer answer:` comment newer than the last verdict
(created or edited), on a head that differs from the last verdict's, or on green checks under a
stale `agk:ci-running` label; never twice on one head. `--fingerprint` prints one line that changes
only when the queue's facts change, for a loop that wakes the conductor only then. A `gh` stub
serves saved JSON copies of the GitHub responses; no network, GET only."""

from __future__ import annotations

from datetime import timedelta

import pytest
from test_session import REPO, SHA, Stub, comment, iso, session

OPEN = f"repos/{REPO}/pulls"
OTHER = "b" * 40
SHORT = SHA[:7]


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def listed(n: int, label: str | None, head: str = SHA, draft: bool = False) -> dict:
    return {
        "number": n, "draft": draft, "user": {"login": "builder"}, "head": {"sha": head},
        "labels": [{"name": label}] if label else [], "body": "Advances: REQ-001\n",
    }  # fmt: skip


def at(minutes: int) -> str:
    return iso(timedelta(minutes=minutes - 600))


def note(cid: int, body: str, created: int, edited: int | None = None, login: str = "builder"):
    out = comment(cid, login, body, at(created))
    out["updated_at"] = at(created if edited is None else edited)
    return out


def verdict(cid: int, sha: str = SHA, when: int = 10, login: str = "boss", kind: str = "fix list"):
    return note(cid, f"Verdict: {kind} {sha[:7]}\n\n1. A finding.", when, login=login)


GREEN = [
    {"id": 1, "name": "proof", "status": "completed", "conclusion": "success"},
    {"id": 2, "name": "governance", "status": "completed", "conclusion": "success"},
]
RUNNING = [
    {"id": 1, "name": "proof", "status": "in_progress", "conclusion": None},
    {"id": 2, "name": "governance", "status": "completed", "conclusion": "success"},
]


def facts(stub: Stub, n: int, comments: list, checks: list | None = None, head: str = SHA) -> None:
    stub.serve(f"repos/{REPO}/issues/{n}/comments", comments)
    runs = GREEN if checks is None else checks
    stub.serve(
        f"repos/{REPO}/commits/{head}/check-runs", {"total_count": len(runs), "check_runs": runs}
    )
    stub.serve(f"repos/{REPO}/commits/{head}/status", {"state": "success", "statuses": []})


def queue(proj, stub, *extra: str):
    out = session(proj, stub, "review-queue", *extra)
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout.splitlines()


# --- the rules (answer 2) -------------------------------------------------------------------


def test_a_pull_request_labelled_for_review_with_no_verdict_qualifies(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:review")])
    facts(stub, 7, [])
    assert queue(proj, stub) == [f"#7 {SHORT} review: labelled agk:review; no verdict yet"]


def test_a_verdict_already_on_the_head_is_never_given_twice_under_a_stale_label(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:review")])
    facts(stub, 7, [note(1, "Report: done", 1), verdict(2)])
    assert queue(proj, stub) == ["empty"]
    assert queue(proj, stub, "--all") == [
        "empty",
        f"#7 {SHORT} skip: verdict on this head (comment 2)",
    ]


@pytest.mark.parametrize(
    "first",
    [
        "Question: Q-306-9 which file?",
        "Report: abc1234 pushed",
        "Correction: void",
        "Maintainer answer: yes",
    ],
)
def test_a_newer_question_report_correction_or_maintainer_answer_qualifies_on_the_same_head(
    proj, stub, first
):
    stub.serve(OPEN, [listed(7, "agk:fix")])
    facts(stub, 7, [verdict(2), note(3, f"{first}\n\nmore", 20)])
    kind = first.split(":")[0]
    assert queue(proj, stub) == [f"#7 {SHORT} review: {kind}: comment 3 since the last verdict"]


def test_an_edited_comment_counts_from_its_edit_and_an_older_one_does_not(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:fix"), listed(8, "agk:fix")])
    facts(stub, 7, [note(1, "Question: Q-1 why?", 1, edited=30), verdict(2)])
    facts(stub, 8, [note(1, "Question: Q-1 why?", 1, edited=5), verdict(2)])
    assert queue(proj, stub) == [f"#7 {SHORT} review: Question: comment 1 since the last verdict"]


def test_other_comments_after_the_verdict_do_not_qualify(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:fix")])
    progress = note(3, "Progress: abc1234 done 1/4; next: 2", 20)
    facts(stub, 7, [verdict(2), progress, note(4, "thanks, Question: later", 25)])
    assert queue(proj, stub) == ["empty"]


def test_a_head_that_differs_from_the_last_verdicts_qualifies(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:ci-red", head=OTHER)])
    facts(stub, 7, [verdict(2)], head=OTHER)
    assert queue(proj, stub) == [
        f"#7 {OTHER[:7]} review: head differs from the last verdict ({SHORT})"
    ]


def test_green_checks_under_a_stale_running_label_qualify_and_running_checks_wait(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:ci-running"), listed(8, "agk:ci-running", head=OTHER)])
    facts(stub, 7, [])
    facts(stub, 8, [note(3, "Question: Q-2 now?", 20)], checks=RUNNING, head=OTHER)
    assert queue(proj, stub, "--all") == [
        f"#7 {SHORT} review: no verdict yet; checks green under a stale agk:ci-running",
        f"#8 {OTHER[:7]} skip: checks running",
    ]


def test_a_required_check_that_has_not_reported_is_still_running(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:ci-running")])
    facts(stub, 7, [], checks=GREEN[:1])
    assert queue(proj, stub, "--all") == ["empty", f"#7 {SHORT} skip: checks running"]


def test_a_draft_is_not_reviewed_and_its_comments_are_not_read(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:review", draft=True)])
    assert queue(proj, stub, "--all") == ["empty", f"#7 {SHORT} skip: draft"]
    assert not any("comments" in call[1] for call in stub.calls())


def test_only_a_listed_author_gives_a_verdict_and_never_on_their_own_pull_request(proj, stub):
    mine = {**listed(8, "agk:fix"), "user": {"login": "boss"}}
    stub.serve(OPEN, [listed(7, "agk:fix"), mine])
    facts(stub, 7, [verdict(2, login="someone")])
    facts(stub, 8, [verdict(2, login="boss")])
    assert queue(proj, stub) == [
        f"#7 {SHORT} review: no verdict yet",
        f"#8 {SHORT} review: no verdict yet",
    ]


def test_the_latest_verdict_decides_and_a_later_question_is_answered_once(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:fix")])
    facts(stub, 7, [verdict(2, sha=OTHER), note(3, "Question: Q-3 ok?", 20), verdict(4, when=30)])
    assert queue(proj, stub) == ["empty"]


# --- reading, writing nothing, failing loudly ---------------------------------------------------


def test_nothing_open_is_empty_and_every_call_is_a_get(proj, stub):
    stub.serve(OPEN, [])
    assert queue(proj, stub) == ["empty"]
    stub.serve(OPEN, [listed(7, "agk:review")])
    facts(stub, 7, [])
    queue(proj, stub, "--all")
    queue(proj, stub, "--fingerprint")
    assert stub.calls() and all(call[0] == "GET" for call in stub.calls())


def test_an_unreadable_list_or_comments_fail_and_never_read_as_empty(proj, stub):
    stub.serve(OPEN, "FAIL")
    out = session(proj, stub, "review-queue")
    assert out.returncode == 2 and "FAIL session" in out.stdout
    stub.serve(OPEN, [listed(7, "agk:review")])
    facts(stub, 7, [])
    stub.serve(f"repos/{REPO}/issues/7/comments", "FAIL")
    out = session(proj, stub, "review-queue")
    assert out.returncode == 2 and "empty" not in out.stdout


def test_no_listed_verdict_author_fails_naming_the_setting(proj, stub):
    proj.write("config/reviewers.yaml", "version: 1\nverdict_authors: []\n")
    stub.serve(OPEN, [listed(7, "agk:review")])
    facts(stub, 7, [])
    out = session(proj, stub, "review-queue")
    assert out.returncode == 2 and "verdict_authors" in out.stdout


def test_usage(proj, stub):
    for extra in (("--pr", "7"), ("--all", "--fingerprint"), ("--fingerprint", "x")):
        assert session(proj, stub, "review-queue", *extra).returncode == 2, extra


# --- the fingerprint of a loop (answer 3) -------------------------------------------------------


def fingerprint(proj, stub) -> str:
    lines = queue(proj, stub, "--fingerprint")
    assert len(lines) == 1 and lines[0].startswith("fingerprint ") and len(lines[0]) == 12 + 64
    return lines[0]


def test_the_fingerprint_changes_with_heads_labels_comment_times_and_checks_only(proj, stub):
    stub.serve(OPEN, [listed(7, "agk:review")])
    facts(stub, 7, [note(1, "Report: x", 1)])
    first = fingerprint(proj, stub)
    assert fingerprint(proj, stub) == first
    stub.serve(OPEN, [listed(7, "agk:fix")])
    label = fingerprint(proj, stub)
    facts(stub, 7, [note(1, "Report: x", 1, edited=2)])
    edited = fingerprint(proj, stub)
    facts(stub, 7, [note(1, "Report: x", 1, edited=2)], checks=RUNNING)
    checks = fingerprint(proj, stub)
    stub.serve(OPEN, [listed(7, "agk:fix", head=OTHER)])
    facts(stub, 7, [note(1, "Report: x", 1, edited=2)], checks=RUNNING, head=OTHER)
    head = fingerprint(proj, stub)
    assert len({first, label, edited, checks, head}) == 5
