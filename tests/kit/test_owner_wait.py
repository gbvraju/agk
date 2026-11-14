"""Owner waits are bounded in minutes and rest hours park at once (brief #1282, ADR-0543; REQ-050).

A pull request whose newest open item waits on the owner (a `Question:` for the maintainers, an
`Owner needed:`, the router's `agk:approve` or `agk:owner-merge`) waits `owner_wait_minutes` of
`[flow]` from that post, or not at all inside `owner_rest_hours` (in the owner's fixed
`owner_utc_offset`); then `session.py watch` and `conductor.py sweep` park it: the label
`agk:parked` and one comment `Parked-by: wait <Q-id>`. The owner's answer unparks it on the next
sweep, and `session.py next` resumes it before a new brief. A person's own `agk:parked` is never
removed. The `gh` stub serves saved responses; invented names, no network.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_session import SHA, Stub, comment, iso, pull, session, watching

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import conductor  # noqa: E402
import session as session_mod  # noqa: E402

import config  # noqa: E402

REPO = "acme/widgets"
NOW = datetime(2026, 11, 14, 9, 0, tzinfo=UTC)  # 14:30 at +05:30, outside 20:00-08:00
LISTED = {"boss", "second"}
ANSWERERS = {"owner", "boss", "second"}
PLAIN = {"minutes": 30, "rest": None, "offset": 0}
NIGHTS = {"minutes": 30, "rest": (20 * 60, 8 * 60), "offset": 330}  # "20:00-08:00", "+05:30"
WATCH = ("watch", "--pr", "7", "--session", "s-me", "--interval", "0", "--timeout", "5")


def at(cid: int, login: str, body: str, minutes: float, now: datetime = NOW) -> dict:
    """A comment posted `minutes` before `now`."""
    when = (now - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


def asked(minutes: float, now: datetime = NOW) -> dict:
    return at(10, "builder", "Question: Q-7-1 for the maintainers: which runtime?", minutes, now)


def step(pr: dict, comments: list, settings: dict = PLAIN, now: datetime = NOW):
    return session_mod.owner_step(pr, comments, settings, now, LISTED, ANSWERERS)


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write(
        "config/reviewers.yaml",
        "version: 1\nverdict_authors: [boss, second]\nspec_approvers: [owner]\n",
    )
    return repo


# --- (a) an unanswered question past the wait parks, and the builder moves on -------------------


def test_1282a_a_question_unanswered_for_the_wait_parks_the_pull_request():
    """REQ-050: brief #1282 answers 2 and 3, test (a), by the judge."""
    assert step(pull(), [asked(31)]) == ("park", "Q-7-1")
    owner = at(11, "boss", "Owner needed: the scope of the acceptance check", 45)
    assert step(pull(), [owner]) == ("park", "owner-needed")
    assert step(pull(labels=("agk:owner-merge",)), [at(12, "builder", "Report: x", 40)]) == (
        "park",
        "owner-merge",
    )
    assert step(pull(), [asked(29)]) is None
    zero = {**PLAIN, "minutes": 0}
    assert step(pull(), [asked(0)], zero) == ("park", "Q-7-1")


def test_1282a_watch_parks_and_names_session_after_as_the_next_command(proj, stub):
    """REQ-050: brief #1282 answer 3 and test (a): one label write, one comment, then `after`."""
    question = comment(
        10,
        "builder",
        "Question: Q-7-1 for the maintainers: which runtime?",
        iso(-timedelta(hours=1)),
    )
    watching(stub, [(pull(), [question])], base=[question])
    stub.serve(f"repos/{REPO}/issues", [])  # no `agk-conductor` issue: messages are not read
    out = session(proj, stub, *WATCH)
    assert out.returncode == 0, out.stdout + out.stderr
    lines = out.stdout.strip().splitlines()
    assert lines[-2] == "parked #7 Q-7-1"
    assert lines[-1] == (
        f"next: post `Report: {SHA[:7]} handing over: blocked: Q-7-1 waits for the owner`, "
        "then run python3 scripts/agk/session.py after --session s-me"
    )
    writes = [c for c in stub.calls() if c[0] != "GET"]
    assert [w[1] for w in writes] == [
        f"repos/{REPO}/issues/7/labels",
        f"repos/{REPO}/issues/7/comments",
    ]
    assert "labels[]=agk:parked" in writes[0][2]
    assert "body=Parked-by: wait Q-7-1" in writes[1][2]


# --- (b) an answer within the wait parks nothing ------------------------------------------------


def test_1282b_an_answer_within_the_wait_parks_nothing():
    """REQ-050: brief #1282 test (b)."""
    answer = at(11, "owner", "Maintainer answer: Q-7-1 the smaller runtime", 20)
    assert step(pull(), [asked(40), answer]) is None
    by_id = at(11, "boss", "Answer: Q-7-1 the smaller runtime", 20)
    assert step(pull(), [asked(40), by_id]) is None
    other = at(11, "owner", "Answer: Q-7-9 another question", 20)
    assert step(pull(), [asked(40), other]) == ("park", "Q-7-1")
    stranger = at(11, "stranger", "Maintainer answer: Q-7-1 not listed", 20)
    assert step(pull(), [asked(40), stranger]) == ("park", "Q-7-1")


def test_1282b_a_plain_question_to_the_conductor_never_waits_on_the_owner():
    """REQ-050: brief #1282 answer 2: only a question for the maintainers is the owner's."""
    plain = at(10, "builder", "Question: Q-7-1 which reading?", 300)
    assert step(pull(), [plain]) is None


# --- (c) inside rest hours parking is immediate, also after midnight ----------------------------


@pytest.mark.parametrize(
    ("utc", "rests"),
    [
        (datetime(2026, 11, 14, 16, 30, tzinfo=UTC), True),  # 22:00 at +05:30
        (datetime(2026, 11, 14, 20, 0, tzinfo=UTC), True),  # 01:30 the next day
        (datetime(2026, 11, 14, 2, 29, tzinfo=UTC), True),  # 07:59
        (datetime(2026, 11, 14, 2, 30, tzinfo=UTC), False),  # 08:00, the end is not included
        (datetime(2026, 11, 14, 14, 29, tzinfo=UTC), False),  # 19:59
    ],
)
def test_1282c_rest_hours_cross_midnight_and_park_at_once(utc, rests):
    """REQ-050: brief #1282 answers 1 and 2, test (c), and the Measured line (22:00 parks)."""
    assert session_mod.resting(NIGHTS, utc) is rests
    expected = ("park", "Q-7-1") if rests else None
    assert step(pull(), [asked(1, utc)], NIGHTS, utc) == expected


def test_1282c_a_range_inside_one_day_rests_only_inside_it():
    """REQ-050: brief #1282 answer 1: a range that does not cross midnight."""
    lunch = {"minutes": 30, "rest": (12 * 60, 13 * 60), "offset": -300}
    assert session_mod.resting(lunch, datetime(2026, 11, 14, 17, 30, tzinfo=UTC)) is True
    assert session_mod.resting(lunch, datetime(2026, 11, 14, 18, 0, tzinfo=UTC)) is False
    assert session_mod.resting(PLAIN, NOW) is False


def test_1282c_a_parked_pull_request_no_longer_takes_a_builder_slot():
    """REQ-050: the Measured line: parking frees the slot that `next` and the plan count."""
    open_pr = {"number": 7, "labels": [{"name": "agk:build"}]}
    parked = {"number": 8, "labels": [{"name": "agk:parked"}]}
    assert session_mod.running_builders([open_pr, parked]) == [open_pr]


# --- (d) an answer after parking resumes the same pull request before a new brief --------------


PARKED_BY = "Parked-by: wait Q-7-1"


def test_1282d_the_answer_unparks_on_the_next_pass():
    """REQ-050: brief #1282 answer 4 and test (d), by the judge."""
    parked = pull(labels=("agk:parked",))
    mark = at(12, "builder", PARKED_BY, 30)
    assert step(parked, [asked(90), mark]) is None  # still waits: stays parked, no new comment
    answer = at(13, "owner", "Maintainer answer: Q-7-1 the smaller runtime", 5)
    assert step(parked, [asked(90), mark, answer]) == ("unpark", "Q-7-1")
    assert step(pull(), [asked(90), mark, answer]) is None  # unparked already


def test_1282d_sweep_parks_lists_once_and_unparks_with_the_resume_command(monkeypatch, tmp_path):
    """REQ-050: brief #1282 answers 3 and 4, test (d): `conductor.py sweep`'s owner lines."""
    comments: dict[int, list] = {7: [asked(90)]}
    labels: dict[int, tuple] = {7: ()}
    writes: list[tuple] = []

    def read(endpoint, what):
        return comments[int(endpoint.split("/issues/")[1].split("/")[0])]

    def park(repo, number, key):
        writes.append(("park", number, key))
        labels[number] = ("agk:parked",)
        comments[number].append(at(20 + len(writes), "boss", f"Parked-by: wait {key}", 0))
        return True

    def unpark(repo, number, key):
        writes.append(("unpark", number, key))
        labels[number] = ()
        return True

    monkeypatch.setattr(conductor, "read", read)
    monkeypatch.setattr(conductor.session, "park_pull", park)
    monkeypatch.setattr(conductor.session, "unpark_pull", unpark)
    monkeypatch.setattr(conductor, "parked_mark", lambda root: tmp_path / "parked")

    def lines() -> list[str]:
        pulls = [{**pull(labels=labels[7]), "number": 7}]
        return conductor.owner_lines("root", REPO, pulls, PLAIN, ["boss"], ["owner"], NOW)

    assert lines() == ["PARKED #7 Q-7-1"]
    assert lines() == []  # listed once, never each pass
    comments[7].append(at(30, "owner", "Maintainer answer: Q-7-1 the smaller runtime", 0))
    assert lines() == ["UNPARKED #7 Q-7-1; run: python3 scripts/agk/session.py resume --pr 7"]
    assert writes == [("park", 7, "Q-7-1"), ("unpark", 7, "Q-7-1")]


def test_1282d_next_offers_the_unparked_pull_request_before_a_new_brief(proj, stub):
    """REQ-050: brief #1282 answer 4 and test (d): `session.py next` resumes it first."""
    from test_session import FREE, issue, listing
    from test_session_plan import free

    listing(stub, [issue(5, FREE)])
    free(stub, 5)
    unparked = {**pull(), "number": 7, "draft": True, "title": "t", "body": "Brief: #4\n"}
    stub.serve(f"repos/{REPO}/pulls", [unparked])
    said = [
        comment(10, "builder", "Question: Q-7-1 for the maintainers: which runtime?"),
        comment(11, "builder", f"Report: {SHA[:7]} handing over: blocked: Q-7-1 waits"),
        comment(12, "boss", PARKED_BY),
        comment(13, "owner", "Maintainer answer: Q-7-1 the smaller runtime"),
        comment(14, "boss", "Unparked-by: answer Q-7-1"),
    ]
    stub.serve(f"repos/{REPO}/issues/7/comments", said)
    out = session(proj, stub, "next", "--session", "s-me")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "unparked #7" in out.stdout and "brief #5" not in out.stdout
    assert all(c[0] == "GET" for c in stub.calls())


# --- (e) a person's own agk:parked is never removed ---------------------------------------------


def test_1282e_a_persons_own_parked_label_is_never_removed():
    """REQ-050: brief #1282 answer 4 and test (e)."""
    held = pull(labels=("agk:parked",))
    answer = at(13, "owner", "Maintainer answer: Q-7-1 the smaller runtime", 5)
    assert step(held, [asked(90), answer]) is None
    # parked by a wait, unparked, then parked again by a person: the person's hold stays
    again = [
        asked(90),
        at(12, "boss", PARKED_BY, 60),
        at(13, "owner", "Maintainer answer: Q-7-1 the smaller runtime", 30),
        at(14, "boss", "Unparked-by: answer Q-7-1", 20),
        at(15, "owner", "Answer: Q-7-2 something else", 1),
    ]
    assert step(held, again) is None


# --- (f) and (g) the settings --------------------------------------------------------------------


def settings(tmp_path: Path, text: str) -> dict:
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return config.owner_wait_settings(tmp_path)


def test_1282f_the_defaults_and_good_values_are_read(tmp_path):
    """REQ-050: brief #1282 answer 1."""
    assert settings(tmp_path, "") == {"minutes": 30, "rest": None, "offset": 0}
    text = '[flow]\nowner_wait_minutes = 0\nowner_rest_hours = "20:00-08:00"\n'
    text += 'owner_utc_offset = "+05:30"\n'
    assert settings(tmp_path, text) == {"minutes": 0, "rest": (1200, 480), "offset": 330}
    west = settings(tmp_path, '[flow]\nowner_utc_offset = "-03:00"\n')
    assert west["offset"] == -180


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("owner_wait_minutes", "-1"),
        ("owner_wait_minutes", '"30"'),
        ("owner_wait_minutes", "true"),
        ("owner_wait_minutes", "2.5"),
        ("owner_rest_hours", '"8 PM to 8 AM"'),
        ("owner_rest_hours", '"20:00-20:00"'),
        ("owner_rest_hours", '"24:00-08:00"'),
        ("owner_rest_hours", "20"),
        ("owner_utc_offset", '"Asia/Kolkata"'),
        ("owner_utc_offset", '"+5:30"'),
        ("owner_utc_offset", "330"),
    ],
)
def test_1282f_a_bad_value_is_refused_naming_the_setting_never_the_value(tmp_path, key, value):
    """REQ-050: brief #1282 answer 1 and test (f)."""
    with pytest.raises(config.OwnerWaitSettingError) as refused:
        settings(tmp_path, f"[flow]\n{key} = {value}\n")
    assert f"setting: flow.{key}" in str(refused.value)
    assert value.strip('"') not in str(refused.value)


def test_1282f_watch_refuses_a_bad_value_naming_the_setting(proj, stub):
    """REQ-050: brief #1282 test (f), from the command."""
    proj.write("agk.toml", '[flow]\nowner_rest_hours = "late"\n')
    out = session(proj, stub, *WATCH)
    assert out.returncode != 0
    assert "setting: flow.owner_rest_hours" in out.stdout + out.stderr
    assert "late" not in out.stdout + out.stderr


def test_1282g_keys_under_a_commented_flow_header_are_not_read(tmp_path):
    """REQ-050: brief #1282 answer 1 and test (g) (#1245)."""
    text = '# [flow]\nowner_wait_minutes = 0\nowner_rest_hours = "late"\n'
    assert settings(tmp_path, text) == {"minutes": 30, "rest": None, "offset": 0}
    text = "[other]\n# [flow]\nowner_wait_minutes = -5\n"
    assert settings(tmp_path, text) == {"minutes": 30, "rest": None, "offset": 0}
    assert {"owner_wait_minutes", "owner_rest_hours", "owner_utc_offset"} <= config.TABLE_KEYS[
        "flow"
    ]
