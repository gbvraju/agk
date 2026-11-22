"""Tests of scripts/agk/steward_daily.py: the daily list, the override share and its warning, and
the fresh re-check of a requirement answer (SPEC-0059 rules 3 and 13; brief #1323, ADR-0560;
REQ-066).

Invented data only (example.com); no network, no model: the reviewer agent of the re-check is a
stub answer, and GitHub is a recorded double that counts each call.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "agk"))

sys.path.insert(0, str(HERE))

import steward  # noqa: E402
import steward_daily as daily  # noqa: E402
import steward_evidence as ev  # noqa: E402
from test_steward_memory import GitHub  # noqa: E402

NOW = datetime(2026, 11, 15, 9, 0, tzinfo=UTC)
WHO = "Who: AGK steward"
SPEC = {"source": 2, "answer": "weekly", "place": "docs/specs/0001-report.md rule 3", "rule": "3"}


def c(cid, body, when, number=45):
    return {
        "id": cid,
        "body": body,
        "created_at": when,
        "updated_at": when,
        "issue_url": f"https://api.example.com/repos/o/r/issues/{number}",
    }


def answer(cid, qid, text, when, cls="technical"):
    line = f"Answer: {qid} {text} (evidence: AGK rule or code Makefile:12; rule: session rule 31)"
    return c(cid, f"{line}\nClass: {cls}\n\n{WHO}\n", when)


# The fixture day: 2026-11-14, two steward answers, one owner override, one pass, one filing.
REPO = [
    answer(201, "Q-7-1", "make lint", "2026-11-14T08:00:00Z"),
    answer(202, "Q-7-2", "weekly", "2026-11-14T09:00:00Z", cls="requirement"),
    c(
        203,
        'Maintainer answer: Q-7-2 monthly\nOwner said (2026-11-14T10:00Z): "monthly"',
        "2026-11-14T10:00:00Z",
    ),
    c(204, "Maintainer answer: Q-7-1 make lint", "2026-11-14T11:00:00Z"),
    c(205, "Answer: Q-9-9 by someone else", "2026-11-14T12:00:00Z"),
    answer(206, "Q-7-3", "today's", "2026-11-15T08:00:00Z"),
]
MEMORY = [
    c(101, "Daily: 2026-11-14\n...", "2026-11-14T07:00:00Z", 9),
    c(102, "Owner question: Q-7-4 should totals round?", "2026-11-14T12:00:00Z", 9),
    c(103, "Decision: Q-7-0 totals are in euros", "2026-11-14T13:00:00Z", 9),
    c(104, "Ended: steward s1 calls 12; tokens 3400", "2026-11-14T14:00:00Z", 9),
    c(105, "Ended: steward s2", "2026-11-14T15:00:00Z", 9),
]
ISSUES = [
    {"number": 50, "created_at": "2026-11-14T16:00:00Z", "body": f"Priority: 2\n\n{WHO}"},
    {
        "number": 51,
        "created_at": "2026-11-14T16:30:00Z",
        "body": f'Priority: 1\nOwner said (2026-11-14T16:00Z): "file it"\n\n{WHO}',
    },
    {"number": 52, "created_at": "2026-11-14T17:00:00Z", "body": "Priority: 3\nby a person"},
]


# --- rule 13: the daily list --------------------------------------------------------------------


def test_req066_the_days_listed_start_after_the_last_daily_list_and_name_the_missed_ones():
    """REQ-066: rule 13, Q-S0059-9: no scheduler; the next start lists the days missed."""
    assert daily.days_to_list(MEMORY, date(2026, 11, 15)) == [date(2026, 11, 14)]
    assert daily.days_to_list(MEMORY, date(2026, 11, 17)) == [
        date(2026, 11, 14),
        date(2026, 11, 15),
        date(2026, 11, 16),
    ]
    assert (
        daily.days_to_list([*MEMORY, c(106, "Daily: 2026-11-15", "x", 9)], date(2026, 11, 15)) == []
    )
    assert daily.days_to_list([], date(2026, 11, 15)) == [date(2026, 11, 14)]


def test_req066_the_daily_list_of_a_fixture_day():
    """REQ-066: rule 13, each answer with its id and evidence, each pass, filing and count."""
    text = daily.daily_text(date(2026, 11, 15), [date(2026, 11, 14)], REPO, MEMORY, ISSUES)
    lines = text.splitlines()
    assert lines[0] == "Daily: 2026-11-15"
    assert any("comment 201 on #45" in x and "Makefile:12" in x for x in lines)
    assert any("comment 202 on #45" in x for x in lines)
    assert not any("206" in x or "Q-9-9" in x for x in lines)
    assert "- steward s1: calls 12; tokens 3400" in lines
    assert "- steward s2: calls not shown; tokens not shown" in lines
    assert "- #50 priority 2" in lines and not any("#51" in x or "#52" in x for x in lines)
    assert "Owner questions (2026-11-14): asked 1; answered 1" in lines
    assert "Override share (2026-11-14): 1/2" in lines
    assert text.rstrip().endswith(WHO)


def test_req066_an_override_changes_the_share():
    """REQ-066: rule 13, an owner answer that changes a steward answer is one override."""
    answers = daily.steward_answers(REPO)
    assert [a["qid"] for a in answers] == ["Q-7-1", "Q-7-2", "Q-7-3"]
    found = daily.overrides(REPO, answers)
    assert [(o["qid"], o["cls"], o["id"]) for o in found] == [("Q-7-2", "requirement", 203)]
    more = [*REPO, c(207, "Correction: Q-7-1 is `make governance`", "2026-11-14T18:00:00Z")]
    text = daily.daily_text(date(2026, 11, 15), [date(2026, 11, 14)], more, MEMORY, ISSUES)
    assert "Override share (2026-11-14): 2/2" in text.splitlines()


def test_req066_a_figure_that_cannot_be_read_is_unknown_never_zero():
    """REQ-066: rule 13, unread comments or issues are `unknown`, never 0."""
    text = daily.daily_text(date(2026, 11, 15), [date(2026, 11, 14)], None, MEMORY, None)
    lines = text.splitlines()
    assert "Answers (2026-11-14): unknown" in lines
    assert "Override share (2026-11-14): unknown" in lines
    assert "Filed without the owner's word (2026-11-14): unknown" in lines
    assert not any(re.search(r": 0\b", x) for x in lines if "unknown" in x)


def test_req066_the_daily_list_is_posted_once_with_its_override_entries():
    """REQ-066: rules 8 and 13, one `Daily:` and one `Override:` per new override; once a day."""
    posted: list[str] = []
    calls: list[tuple[str, str]] = []

    def gh(method, endpoint, fields=None):
        calls.append((method, endpoint))
        if method == "POST":
            posted.append(fields["body"])
            return {
                "id": 900 + len(posted),
                "body": fields["body"],
                "created_at": "2026-11-15T09:00:00Z",
            }
        return REPO if "issues/comments" in endpoint else ISSUES

    cache = {"issue": 9, "comments": list(MEMORY)}
    code, lines = daily.post_daily(cache, gh, NOW)
    assert code == 0
    assert posted[0].startswith("Override: Q-7-2 class requirement:")
    assert posted[-1].startswith("Daily: 2026-11-15")
    assert len(posted) == 2 and len(calls) <= 5
    assert daily.post_daily(cache, gh, NOW) == (0, ["daily: already posted for 2026-11-15"])
    assert len(posted) == 2


def test_req066_a_pass_writes_its_calls_and_tokens_or_not_shown(tmp_path, monkeypatch):
    """REQ-066: rules 13 and 18, each pass's counted calls and tokens; `not shown`, never 0."""
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "cache.json"))
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    gh = GitHub()
    steward.start(tmp_path, "s1", gh, NOW)
    steward.end(tmp_path, "s1", gh, NOW, 9, None)
    body = gh.issues[1]["c"][-1]["body"]
    assert body.startswith("Ended: steward s1 calls 9; tokens not shown")
    memory = [c(1, body, "2026-11-14T10:00:00Z", 9)]
    text = daily.daily_text(date(2026, 11, 15), [date(2026, 11, 14)], [], memory, [])
    assert "- steward s1: calls 9; tokens not shown" in text.splitlines()


# --- rule 3 by stage (d): the override warning ----------------------------------------------------


def test_req066_two_overrides_of_one_class_in_seven_days_send_it_to_the_owner():
    """REQ-066: rule 3 (d), a warning, not a gate; a `Decision:` naming the class lifts it."""
    one = c(301, "Override: Q-1 class technical: owner comment 1", "2026-11-10T10:00:00Z", 9)
    two = c(302, "Override: Q-2 class technical: owner comment 2", "2026-11-14T10:00:00Z", 9)
    old = c(303, "Override: Q-3 class requirement: owner comment 3", "2026-11-01T10:00:00Z", 9)
    new = c(304, "Override: Q-4 class requirement: owner comment 4", "2026-11-14T10:00:00Z", 9)
    assert daily.warned([one, two, old, new], NOW) == {"technical"}
    lifted = c(305, "Decision: class technical goes back to the steward", "2026-11-14T12:00:00Z", 9)
    assert daily.warned([one, two, lifted], NOW) == set()
    found = ev.settle(
        {"id": "Q-7-1", "class": "technical", "findings": [SPEC | {"source": 5}]},
        "build",
        warned={"technical"},
    )
    assert found["to"] == "owner" and "overrode" in found["reason"]
    text = daily.daily_text(date(2026, 11, 15), [date(2026, 11, 14)], REPO, [one, two], ISSUES)
    assert any(x.startswith("Warning: class technical") for x in text.splitlines())


# --- rule 13: the fresh re-check ---------------------------------------------------------------


def requirement():
    return {
        "id": "Q-7-2",
        "class": "requirement",
        "text": "How often is the report?",
        "findings": [SPEC],
    }


def test_req066_the_recheck_bundle_holds_the_question_and_evidence_only():
    """REQ-066: rule 13, the reviewer is not given the steward's answer or context."""
    bundle = daily.recheck_bundle(requirement())
    assert "How often is the report?" in bundle and "docs/specs/0001-report.md rule 3" in bundle
    assert "weekly" not in bundle


@pytest.mark.parametrize(
    ("recheck", "to"),
    [(None, "owner"), ({"answer": "Weekly."}, "answer"), ({"answer": "monthly"}, "owner")],
)
def test_req066_a_requirement_answer_is_posted_only_when_the_recheck_agrees(recheck, to):
    """REQ-066: rules 4 and 13, a disagreeing re-check sends both answers to the owner."""
    found = ev.settle(requirement(), "build", recheck=recheck)
    assert found["to"] == to
    if recheck and to == "owner":
        assert "weekly" in found["reason"] and "monthly" in found["reason"]
    if to == "answer":
        assert ev.answer_body(found).splitlines()[1] == "Class: requirement"


# --- brief #1716: an override only from the owner, once per steward answer ----------------------

FOOT = "\n\n---\n_Generated by [Claude Code](https://claude.example.com/code)_\n"
# The six shapes of the run of 2026-11-20 (invented text): two steward answers, the owner's two
# `Maintainer answer:` comments (no `Who:` line), and two conductor `Correction:` comments.
ROLES = [
    answer(401, "Q-8-1", "keep the draft", "2026-11-14T08:00:00Z"),
    c(402, "Maintainer answer: Q-8-1 install the scanner first", "2026-11-14T08:10:00Z"),
    answer(403, "Q-8-2", "commit each proposal whole", "2026-11-14T09:00:00Z"),
    c(
        404,
        "Correction: my note on Q-8-2 missed a decision; the steward's Answer above stands\n\n"
        f"Who: AGK conductor{FOOT}",
        "2026-11-14T09:01:00Z",
    ),
    c(405, "Maintainer answer: Q-8-2 I make the edits by hand", "2026-11-14T09:02:00Z"),
    c(
        406,
        "Correction: the owner's `Maintainer answer: Q-8-2` rules it\n\nWho: AGK conductor",
        "2026-11-14T09:03:00Z",
    ),
]


def ids(found):
    return [(o["qid"], o["id"]) for o in found]


def test_req066_only_the_owner_overrides_once_per_steward_answer():
    """REQ-066: brief #1716, the six-comment day is two overrides, not four."""
    found = daily.overrides(ROLES, daily.steward_answers(ROLES))
    assert ids(found) == [("Q-8-1", 402), ("Q-8-2", 405)]
    text = daily.daily_text(date(2026, 11, 15), [date(2026, 11, 14)], ROLES, MEMORY, ISSUES)
    assert "Override share (2026-11-14): 2/2" in text.splitlines()


def test_req066_a_roles_correction_that_upholds_an_answer_is_no_override():
    """REQ-066: brief #1716 answer 1, a `Who: AGK conductor` correction is never one (Q-1716-2)."""
    for who in ("AGK conductor", "AGK steward", "AGK builder", "AGK reviewer"):
        both = [ROLES[2], c(404, f"Correction: Q-8-2 stands\n\nWho: {who}", "2026-11-14T09:01Z")]
        assert daily.overrides(both, daily.steward_answers(both)) == []


@pytest.mark.parametrize(
    "body",
    [
        "Correction: Q-8-2 is `make governance`",
        'Correction: Q-8-2 is `make governance`\nOwner said (2026-11-14T09:05Z): "governance"\n\n'
        f"Who: ProductOwner{FOOT}",
        'Maintainer answer: Q-8-2 by hand\nOwner said (2026-11-14T09:05Z): "by hand"\n\n'
        "Who: ProductOwner",
    ],
)
def test_req066_the_owners_own_or_relayed_comment_is_one_override(body):
    """REQ-066: brief #1716 answers 1 and 4, no `Who:` line or `Who: ProductOwner` counts."""
    both = [ROLES[2], c(407, body, "2026-11-14T09:05:00Z")]
    assert ids(daily.overrides(both, daily.steward_answers(both))) == [("Q-8-2", 407)]


def test_req066_three_owner_comments_on_one_answer_are_one_override():
    """REQ-066: brief #1716 answer 2, the earliest that qualifies is the one override."""
    many = [
        ROLES[2],
        c(404, "Correction: Q-8-2 stands\n\nWho: AGK conductor", "2026-11-14T09:01:00Z"),
        c(408, "Correction: Q-8-2 is by hand", "2026-11-14T09:04:00Z"),
        c(409, "Maintainer answer: Q-8-2 by hand", "2026-11-14T09:06:00Z"),
        c(410, "Correction: Q-8-2 by hand, all of it", "2026-11-14T09:07:00Z"),
    ]
    assert ids(daily.overrides(many, daily.steward_answers(many))) == [("Q-8-2", 408)]


def test_req066_the_last_who_line_is_read_and_an_equal_answer_is_none():
    """REQ-066: brief #1716 answer 4, a `Who:` line above another; the same answer is none."""
    quoted = "Correction: Q-8-2 quoted\nWho: ProductOwner\n\nWho: AGK conductor"
    above = "Correction: Q-8-2 by hand\nWho: AGK conductor\n\nWho: ProductOwner"
    same = "Maintainer answer: Q-8-2 Commit each proposal whole."
    for body, want in ((quoted, []), (above, [("Q-8-2", 411)]), (same, [])):
        both = [ROLES[2], c(411, body, "2026-11-14T09:05:00Z")]
        assert ids(daily.overrides(both, daily.steward_answers(both))) == want


@pytest.mark.parametrize("mode", ["solo", "team"])
def test_req066_the_rule_is_the_same_in_solo_and_team_mode(tmp_path, mode):
    """REQ-066: brief #1716 answer 3, `review_mode` is not read: a reviewer's own answer counts."""
    (tmp_path / "agk.toml").write_text(f'review_mode = "{mode}"\n', encoding="utf-8")
    both = [ROLES[2], c(412, "Maintainer answer: Q-8-2 by hand", "2026-11-14T09:05:00Z")]
    assert ids(daily.overrides(both, daily.steward_answers(both))) == [("Q-8-2", 412)]
    role = [ROLES[2], c(413, "Correction: Q-8-2\n\nWho: AGK reviewer", "2026-11-14T09:05:00Z")]
    assert daily.overrides(role, daily.steward_answers(role)) == []


def double(repo, posted):
    def gh(method, endpoint, fields=None):
        if method == "POST":
            posted.append(fields["body"])
            return {"id": 950 + len(posted), "body": fields["body"], "created_at": "2026-11-15"}
        return repo if "issues/comments" in endpoint else ISSUES

    return gh


def test_req066_one_answer_overridden_is_posted_as_one_override_entry():
    """REQ-066: brief #1716 answer 2, two entries for the six comments; none posted twice."""
    posted: list[str] = []
    code, _ = daily.post_daily({"issue": 9, "comments": list(MEMORY)}, double(ROLES, posted), NOW)
    entries = [p for p in posted if p.startswith("Override:")]
    assert code == 0 and len(entries) == 2
    assert entries[0].startswith("Override: Q-8-1 class technical: owner comment 402 ")
    assert entries[1].startswith("Override: Q-8-2 class technical: owner comment 405 ")


def test_req066_an_override_already_in_the_read_comments_is_not_posted_again():
    """REQ-066: brief #1716 answer 2, an entry on a rolled-over memory issue counts as recorded."""
    old = c(99, "Override: Q-8-2 class technical: owner comment 405", "2026-11-14T10:00Z", 8)
    posted: list[str] = []
    daily.post_daily({"issue": 9, "comments": list(MEMORY)}, double([*ROLES, old], posted), NOW)
    assert [p.split(":")[1].split()[0] for p in posted if p.startswith("Override:")] == ["Q-8-1"]


def test_req066_personal_mode_prints_unknown_and_posts_no_override(tmp_path, monkeypatch, capsys):
    """REQ-066: brief #1716 answer 3, `[personal]` reads no comments: `unknown`, no entry."""
    (tmp_path / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    monkeypatch.setattr(daily, "repo_root", lambda: tmp_path)
    assert daily.main(["daily"]) == 0
    out = capsys.readouterr().out
    assert "Override share (" in out and ": unknown" in out and "Override:" not in out
