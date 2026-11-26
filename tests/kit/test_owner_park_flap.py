"""An owner-wait park holds until every asked Q id is answered (brief #1968, ADR-0815; REQ-066).

The owner wait reads one rule, `session.open_owner_items`: an `Owner needed:` naming several Q
ids stays open until each is answered after it, an approval ask stays open from its comments and
never from the router's `agk:approve` label (which the park itself makes the router remove), and
a label-only `approve` park holds until an approval line after its `Parked-by:`. The replays
follow #1945, #1949 and #1961 with invented logins (example.com accounts) and shas; no network.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import check_amendments  # noqa: E402
import common  # noqa: E402
import route  # noqa: E402
import session  # noqa: E402

import config  # noqa: E402

NOW = datetime(2026, 11, 26, 6, 0, tzinfo=UTC)
CONDUCTOR = "conductor-example"
OWNER = "owner-example"
LISTED = {CONDUCTOR}
ANSWERERS = {CONDUCTOR, OWNER}
PLAIN = {"minutes": 30, "rest": None, "offset": 0}
HEAD = "d" * 40
AMENDMENT = "docs/runs/proposed-spec-amendments-245.md"
SPEC = "docs/specs/0075-an-example-spec.md"


def at(cid: int, login: str, body: str, minutes: float) -> dict:
    when = (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


def pull(labels: tuple = (), files: list | None = None, **extra) -> dict:
    pr = {
        "number": 1945,
        "user": {"login": "builder-example"},
        "created_at": "2026-11-25T08:00:00Z",
        "head": {"sha": HEAD},
        "labels": [{"name": n} for n in labels],
        "draft": False,
        **extra,
    }
    if files is not None:
        pr["files"] = [{"filename": f, "status": "added", "patch": ""} for f in files]
    return pr


def step(pr: dict, comments: list):
    return session.owner_step(pr, comments, PLAIN, NOW, LISTED, ANSWERERS)


def items(pr: dict, comments: list) -> dict:
    return session.open_owner_items(pr, comments, LISTED, ANSWERERS)


def router_labels(labels: set[str]) -> set[str]:
    """The label set `route.apply` leaves while `agk:parked` holds: every other state label of
    `route.LABELS` removed (`route.base_state` returns `agk:parked`)."""
    assert route.base_state({"labels": sorted(labels)}) == route.PARKED
    return {x for x in labels if x not in route.LABELS or x == route.PARKED}


def same_under_router(pr_labels: tuple, comments: list, files=None) -> tuple:
    """Answer 10: the wait's step with the labels as set and as the router leaves them."""
    before = step(pull(pr_labels, files), comments)
    after = step(pull(tuple(sorted(router_labels(set(pr_labels)))), files), comments)
    assert before == after, (before, after)
    return after


# --- Case 1: #1945, an approval ask parks by the ask and never flaps ----------------------------

ASK_1945 = at(
    1,
    CONDUCTOR,
    "Owner needed: amendment 245 waits for the owner's approval\n\n"
    "`Maintainer answer: amendment 245 approved`\n",
    120,
)
LATER = at(2, "builder-example", "Report: dddddddd ready for review", 100)
PARKED_APPROVE = at(3, CONDUCTOR, "Parked-by: wait approve", 80)
PARKED_ASK = at(3, CONDUCTOR, "Parked-by: wait owner-needed", 80)


@pytest.mark.parametrize("files", [None, [AMENDMENT]])
def test_1968_1945_the_approval_ask_parks_keyed_by_the_ask(files):
    """REQ-066: brief #1968 answer 2: the label adds no `approve` beside an open approval ask."""
    pr = pull(("agk:approve",), files)
    assert "approve" not in items(pr, [ASK_1945, LATER])
    assert step(pr, [ASK_1945, LATER]) == ("park", "owner-needed")


@pytest.mark.parametrize("files", [None, [AMENDMENT]])
def test_1968_1945_the_removed_label_does_not_unpark(files):
    """REQ-066: brief #1968 answers 2, 3 and 8: neither the ask's park nor an `approve` park
    written before the build is ended by the router's removal of `agk:approve`."""
    for mark in (PARKED_ASK, PARKED_APPROVE):
        said = [ASK_1945, LATER, mark]
        assert same_under_router(("agk:approve", "agk:parked"), said, files) is None
        assert step(pull(("agk:parked",), files), said) is None
    answer = at(4, OWNER, "Maintainer answer: amendment 245 approved", 10)
    assert step(pull(("agk:parked",), files), [ASK_1945, LATER, PARKED_ASK, answer]) == (
        "unpark",
        "owner-needed",
    )
    assert step(pull(("agk:parked",), files), [ASK_1945, LATER, PARKED_APPROVE, answer]) == (
        "unpark",
        "approve",
    )


# --- Case 1: #1949, a label-only approval park holds until an approval line ---------------------

VERDICT_1949 = at(
    1,
    CONDUCTOR,
    "Verdict: fix list dddddddd\n"
    "Approval: SPEC-0075 dddddddd Draft -> Approved, waiting for a person\n",
    120,
)


def test_1968_1949_a_label_only_park_holds_until_an_approval_line_after_it():
    """REQ-066: brief #1968 answer 3: one park, held until `Approve: SPEC-0075`."""
    said = [VERDICT_1949, LATER]
    assert step(pull(("agk:approve",)), said) == ("park", "approve")
    said = [*said, PARKED_APPROVE]
    assert same_under_router(("agk:approve", "agk:parked"), said) is None
    talk = at(4, "builder-example", "Report: dddddddd waiting", 50)
    assert step(pull(("agk:parked",)), [*said, talk]) is None
    approve = at(5, OWNER, "Approve: SPEC-0075", 10)
    assert step(pull(("agk:parked",)), [*said, talk, approve]) == ("unpark", "approve")


@pytest.mark.parametrize(
    "line, closes",
    [
        ("Approve: SPEC-0075", True),
        ("Maintainer answer: amendment 245 approved", True),
        (f"Maintainer answer: accept {HEAD}", True),
        ("Maintainer answer: go ahead", True),
        (f"Maintainer answer: accept {'e' * 40}", False),
        ("Maintainer answer: Q-1949-1 yes", False),
        ("Answer: Q-1949-1 yes", False),
    ],
)
def test_1968_1949_the_lines_that_end_a_label_only_park(line, closes):
    """REQ-066: brief #1968 answer 3: the approval lines, accept of the head, or a general answer."""
    said = [VERDICT_1949, LATER, PARKED_APPROVE, at(5, OWNER, line, 10)]
    assert step(pull(("agk:parked",)), said) == (("unpark", "approve") if closes else None)


def test_1968_1949_an_approval_before_the_park_or_by_another_login_does_not_end_it():
    """REQ-066: brief #1968 answers 3 and 8: only an answerer's line after the `Parked-by:`."""
    early = at(5, OWNER, "Approve: SPEC-0075", 90)
    stranger = at(6, "visitor-example", "Approve: SPEC-0075", 10)
    said = [VERDICT_1949, LATER, early, PARKED_APPROVE, stranger]
    assert step(pull(("agk:parked",)), sorted(said, key=lambda c: c["created_at"])) is None


def test_1968_a_hand_removed_label_is_repaired_as_today():
    """REQ-066: brief #1968 answer 3: a person removing `agk:parked` is repaired."""
    assert step(pull(()), [VERDICT_1949, LATER, PARKED_APPROVE]) == ("repair", "approve")


# --- Case 2: #1961, one answer does not end a three-question park -------------------------------

ASK_1961 = at(
    1,
    CONDUCTOR,
    "Owner needed: three questions on the domain model\n\n"
    "Q-1954-A: the glossary's home?\nQ-1954-B: the rule prefix?\nQ-1954-C: the harvest scope?\n",
    300,
)
PARKED_1961 = at(2, CONDUCTOR, "Parked-by: wait owner-needed", 270)


def answers(*lines: str) -> list:
    return [at(10 + i, OWNER, line, 100 - i) for i, line in enumerate(lines)]


def test_1968_1961_the_park_holds_until_the_last_asked_id_is_answered():
    """REQ-066: brief #1968 answer 1, the #1961 replay."""
    parked = pull(("agk:parked",))
    said = [ASK_1961, PARKED_1961]
    a, b, c = "Answer: Q-1954-A here", "Answer: Q-1954-B BR", "Maintainer answer: Q-1954-C all"
    assert step(parked, [*said, *answers(a)]) is None
    assert step(parked, [*said, *answers(a, b)]) is None
    assert same_under_router(("agk:parked", "agk:question"), [*said, *answers(a, b)]) is None
    assert step(parked, [*said, *answers(a, b, c)]) == ("unpark", "owner-needed")


def test_1968_an_answer_before_the_ask_does_not_count_for_it():
    """REQ-066: brief #1968 answer 1 (ADR-0685 edge 4): a re-ask is open again."""
    early = at(5, OWNER, "Answer: Q-1954-A here", 400)
    said = [early, ASK_1961, PARKED_1961, *answers("Answer: Q-1954-B x", "Answer: Q-1954-C y")]
    assert step(pull(("agk:parked",)), said) is None
    assert step(pull(("agk:parked",)), [*said, at(30, OWNER, "Answer: Q-1954-A z", 5)]) == (
        "unpark",
        "owner-needed",
    )


def test_1968_a_one_id_ask_closes_on_its_answer_as_today():
    """REQ-066: brief #1968 answer 1: a one-id ask is unchanged (ADR-0685 decision 1)."""
    ask = at(1, CONDUCTOR, "Owner needed: one question\n\nQ-1954-A: the glossary's home?\n", 300)
    said = [ask, PARKED_1961, *answers("Maintainer answer: Q-1954-A docs")]
    assert step(pull(("agk:parked",)), said) == ("unpark", "owner-needed")


def test_1968_a_general_answer_or_an_accept_closes_every_id():
    """REQ-066: brief #1968 answer 2: a general answer and the head's accept close all."""
    for line in ("Maintainer answer: proceed as recommended", f"Maintainer answer: accept {HEAD}"):
        said = [ASK_1961, PARKED_1961, *answers(line)]
        assert step(pull(("agk:parked",)), said) == ("unpark", "owner-needed")


def test_1968_an_approval_line_on_an_ask_with_ids_closes_the_approvals_only():
    """REQ-066: brief #1968 answer 2 and Q-PF-2: the ids stay open after the approval."""
    ask = at(
        1,
        CONDUCTOR,
        "Owner needed: approve and answer\n\n`Approve: SPEC-0075`\n\nQ-1954-A: the home?\n",
        300,
    )
    parked = pull(("agk:parked",), [SPEC])
    said = [ask, PARKED_1961, *answers("Approve: SPEC-0075")]
    assert step(parked, said) is None
    assert step(parked, [*said, at(40, OWNER, "Answer: Q-1954-A docs", 5)]) == (
        "unpark",
        "owner-needed",
    )


def test_1968_a_correction_closes_only_the_question_items_of_its_body():
    """REQ-066: brief #1968 answer 8 (ADR-0685 edge 6): unchanged."""
    said = [ASK_1961, PARKED_1961, at(5, CONDUCTOR, "Correction: Q-1954-A was withdrawn", 50)]
    assert step(pull(("agk:parked",)), said) is None


def test_1968_ids_the_newest_ask_does_not_repeat_are_not_asked():
    """REQ-066: brief #1968 answer 8: the newest `Owner needed:` of a key names the open ids."""
    again = at(3, CONDUCTOR, "Owner needed: one left\n\nQ-1954-C: the harvest scope?\n", 200)
    said = [ASK_1961, again, at(4, CONDUCTOR, "Parked-by: wait owner-needed", 150)]
    assert step(pull(("agk:parked",)), [*said, *answers("Answer: Q-1954-C x")]) == (
        "unpark",
        "owner-needed",
    )


def test_1968_a_mixed_answer_set_and_a_stranger():
    """REQ-066: brief #1968 answers 1 and 8: `Answer:` and `Maintainer answer:` both count; an
    answer by a login that is not an answerer counts nothing."""
    said = [ASK_1961, PARKED_1961, *answers("Maintainer answer: Q-1954-A x", "Answer: Q-1954-B y")]
    stranger = at(40, "visitor-example", "Answer: Q-1954-C z", 5)
    assert step(pull(("agk:parked",)), [*said, stranger]) is None
    assert step(pull(("agk:parked",)), [*said, at(41, OWNER, "Answer: Q-1954-C z", 4)]) == (
        "unpark",
        "owner-needed",
    )


# --- answer 4: the settled line counts in the wait as in the router -----------------------------


def settled(number: int, digest: str) -> dict:
    first = check_amendments.SETTLED_FORM.format(
        number, "the code matches", "implementation", "SPEC-0059 rule 3"
    )
    return at(20, OWNER, f"{first}\nText: {digest}\n\n{check_amendments.WHO}\n", 10)


def test_1968_a_settled_line_closes_the_amendment_in_the_wait_only_with_the_setting():
    """REQ-066: brief #1968 answer 4 (ADR-0813 answer 3)."""
    digest = "0123456789abcdef"
    said = [ASK_1945, LATER, PARKED_ASK, settled(245, digest)]
    on = pull(("agk:parked",), [AMENDMENT], settles={"amendment 245": digest}, settlers=[OWNER])
    assert step(on, said) == ("unpark", "owner-needed")
    assert step(pull(("agk:parked",), [AMENDMENT]), said) is None  # the setting off
    other = pull(("agk:parked",), [AMENDMENT], settles={"amendment 245": "f" * 16}, settlers=[OWNER])
    assert step(other, said) is None  # another text was settled
    stranger = pull(("agk:parked",), [AMENDMENT], settles={"amendment 245": digest}, settlers=[])
    assert step(stranger, said) is None


def test_1968_owner_read_reads_the_settles_only_with_the_setting_on(monkeypatch):
    """REQ-066: brief #1968 answer 4: one read per amendment file, only with the setting on."""
    pr = {"number": 1945, "head": {"sha": HEAD}}
    files = [{"filename": AMENDMENT, "status": "added"}]
    reads = {"repos/o/r/pulls/1945": pr, "repos/o/r/pulls/1945/files": files}
    monkeypatch.setattr(session, "gh", lambda endpoint, *a, **k: reads.get(endpoint))
    monkeypatch.setattr(session, "pages", lambda endpoint, *a, **k: reads.get(endpoint, [ASK_1945]))
    calls = []

    def settles(repo, files, head, root):
        calls.append(head)
        return {"amendment 245": "0123456789abcdef"}

    monkeypatch.setattr(route, "amendment_settles", settles)
    monkeypatch.setattr(session, "spec_approvers", lambda root: [OWNER])
    monkeypatch.setattr(check_amendments, "settle_on", lambda root: False)
    found = session.owner_read("o/r", 1945)
    assert found is not None and "settles" not in found[0] and calls == []
    monkeypatch.setattr(check_amendments, "settle_on", lambda root: True)
    found = session.owner_read("o/r", 1945)
    assert found[0]["settles"] == {"amendment 245": "0123456789abcdef"}
    assert found[0]["settlers"] == [OWNER] and calls == [HEAD]


# --- answer 5: the closing lines name what is left ----------------------------------------------


def test_1968_ask_lines_prints_the_two_open_ids_after_one_answer(monkeypatch, capsys, tmp_path):
    """REQ-066: brief #1968 answer 5: one line per open id in the ask's order."""
    said = [ASK_1961, PARKED_1961, *answers("Answer: Q-1954-B y")]
    monkeypatch.setattr(session, "personal_table", lambda root: None)
    monkeypatch.setattr(session, "repo_name", lambda root: "o/r")
    monkeypatch.setattr(session, "owner_read", lambda repo, number: (pull(("agk:parked",)), said))
    monkeypatch.setattr(session, "owner_people", lambda root, pr: (LISTED, ANSWERERS))
    monkeypatch.setattr(session, "carried_check", lambda root: None)
    assert session.ask_lines(tmp_path, 1961) == 0
    assert capsys.readouterr().out.splitlines() == [
        "owner-needed: Maintainer answer: Q-1954-A <your answer>",
        "owner-needed: Maintainer answer: Q-1954-C <your answer>",
    ]


def test_1968_closing_lines_add_the_open_approvals_and_keep_todays_line_without_ids():
    """REQ-066: brief #1968 answer 5; an ask with no id keeps the line of ADR-0747."""
    ask = at(
        1,
        CONDUCTOR,
        "Owner needed: approve and answer\n\n`Approve: SPEC-0075`\n\nQ-1954-A: the home?\n",
        300,
    )
    pr = pull((), [SPEC])
    assert session.closing_lines("owner-needed", pr, [ask], LISTED, ANSWERERS) == [
        "Maintainer answer: Q-1954-A <your answer>",
        "Approve: SPEC-0075",
    ]
    plain = at(1, CONDUCTOR, "Owner needed: the scope\n", 300)
    assert session.closing_lines("owner-needed", pr, [plain], LISTED, ANSWERERS) == [
        f"Maintainer answer: accept {HEAD}"
    ]
    assert session.closing_line("owner-needed", pr, [ask]) == f"Maintainer answer: accept {HEAD}"


# --- answer 7: the settings, each with a test ---------------------------------------------------


@pytest.mark.parametrize(
    "key, value",
    [
        ("owner_wait_minutes", "-1"),
        ("owner_wait_minutes", "1.5"),
        ("owner_wait_minutes", '"30"'),
        ("owner_rest_hours", '"08:00-08:00"'),
        ("owner_rest_hours", '"late"'),
        ("owner_utc_offset", '"+5:30"'),
    ],
)
def test_1968_owner_wait_settings_refuse_naming_the_setting(tmp_path, key, value):
    """REQ-066: brief #1968 answer 7: refused by setting name, never the value, as today."""
    (tmp_path / "agk.toml").write_text(f"[flow]\n{key} = {value}\n", encoding="utf-8")
    with pytest.raises(config.OwnerWaitSettingError) as refused:
        config.owner_wait_settings(tmp_path)
    assert f"flow.{key}" in str(refused.value) and value.strip('"') not in str(refused.value)


@pytest.mark.parametrize("minutes", [0, 30])
def test_1968_the_wait_minutes_decide_when_a_park_is_written_not_how_it_ends(minutes):
    """REQ-066: brief #1968 answer 7: `owner_wait_minutes` unchanged; the park holds by answer 1."""
    wait = {**PLAIN, "minutes": minutes}
    fresh = at(1, CONDUCTOR, ASK_1961["body"], 10)
    expect = ("park", "owner-needed") if minutes == 0 else None
    assert session.owner_step(pull(), [fresh], wait, NOW, LISTED, ANSWERERS) == expect
    said = [ASK_1961, PARKED_1961, *answers("Answer: Q-1954-A x")]
    assert session.owner_step(pull(("agk:parked",)), said, wait, NOW, LISTED, ANSWERERS) is None


def test_1968_rest_hours_park_at_once_and_the_park_holds():
    """REQ-066: brief #1968 answer 7: `owner_rest_hours` and `owner_utc_offset` unchanged."""
    nights = {"minutes": 30, "rest": (0, 23 * 60 + 59), "offset": 0}
    fresh = at(1, CONDUCTOR, ASK_1961["body"], 1)
    assert session.owner_step(pull(), [fresh], nights, NOW, LISTED, ANSWERERS) == (
        "park",
        "owner-needed",
    )


@pytest.mark.parametrize("value", ['"yes"', "1"])
def test_1968_a_bad_settle_value_is_refused_and_reads_as_off(tmp_path, value):
    """REQ-066: brief #1968 answer 7: `[steward] settle_amendments` refused by name; off."""
    (tmp_path / "agk.toml").write_text(f"[steward]\nsettle_amendments = {value}\n", "utf-8")
    with pytest.raises(config.StewardSettingError) as refused:
        config.steward_settings(tmp_path)
    assert "steward.settle_amendments" in str(refused.value)
    assert check_amendments.settle_on(tmp_path) is False
    assert check_amendments.settle_on(None) is False


@pytest.mark.parametrize(
    "line, reader, named",
    [
        ('review_mode = "duo"\n', common.review_mode, "review_mode"),
        ('execution = "cloud"\n', common.execution, "execution"),
    ],
)
def test_1968_review_mode_and_execution_refuse_by_name(tmp_path, line, reader, named):
    """REQ-066: brief #1968 answer 7: refused by setting name, never the value."""
    (tmp_path / "agk.toml").write_text(line, encoding="utf-8")
    with pytest.raises(common.CheckError) as refused:
        reader(tmp_path)
    assert f"setting: {named}" in str(refused.value)
    assert line.split('"')[1] not in str(refused.value)


def test_1968_no_listed_verdict_author_parks_nothing():
    """REQ-066: brief #1968 answer 7: with no listed verdict author no `Owner needed:` counts."""
    assert session.owner_step(pull(), [ASK_1961], PLAIN, NOW, set(), {OWNER}) is None


def test_1968_the_owner_merge_hand_over_is_never_parked():
    """REQ-066: brief #1968 answer 7 (ADR-0722): unchanged."""
    assert step(pull(("agk:owner-merge",)), [LATER]) == ("handover", "owner-merge")
