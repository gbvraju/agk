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
    # brief #1534 answer 2: the fresh read before the label write, and the one after it
    pr_path, said_path = f"repos/{REPO}/pulls/7", f"repos/{REPO}/issues/7/comments"
    stub.serve(pr_path, pull(), nth=2)
    stub.serve(said_path, [question], nth=3)
    stub.serve(pr_path, pull(labels=("agk:parked",)), nth=3)
    stub.serve(said_path, [question, comment(11, "boss", "Parked-by: wait Q-7-1")], nth=4)
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
    assert "body=Parked-by: wait Q-7-1\n\nWho: AGK" in writes[1][2]


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
    done = at(14, "boss", "Unparked-by: answer Q-7-1", 4)
    assert step(pull(), [asked(90), mark, answer, done]) is None  # unparked already


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

    def unpark(repo, number, key, labelled=True):
        writes.append(("unpark", number, key))
        labels[number] = ()
        return True

    def fresh(repo, number):  # brief #1534: the apply's own read before each write
        return {**pull(labels=labels[number]), "number": number}, list(comments[number])

    monkeypatch.setattr(conductor, "read", read)
    monkeypatch.setattr(conductor.session, "owner_read", fresh)
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


def test_1282f_sweep_refuses_a_bad_value_in_one_line_and_prints_the_rest(
    monkeypatch, tmp_path, capsys
):
    """REQ-050: brief #1282 answer 1 and test (f), from `conductor.py sweep`: one bad owner-wait
    value gives one refusal line naming the setting, parks nothing, and every other line stays."""
    (tmp_path / "agk.toml").write_text('[flow]\nowner_rest_hours = "8pm-8am"\n', encoding="utf-8")
    waiting = {**pull(), "number": 7, "draft": True, "created_at": iso()}
    writes: list = []

    def read(endpoint, what):
        if "/pulls" in endpoint:
            return [waiting]
        return [asked(90, datetime.now(UTC))] if "/issues/7/" in endpoint else []

    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "flow_int", lambda *a: 60)
    monkeypatch.setattr(conductor, "verdict_authors", lambda root: ["boss"])
    monkeypatch.setattr(conductor, "spec_approvers", lambda root: ["owner"])
    monkeypatch.setattr(conductor, "read", read)
    monkeypatch.setattr(
        conductor.session, "gh", lambda endpoint, *a, **k: {"default_branch": "main"}
    )
    monkeypatch.setattr(conductor.session, "park_pull", lambda *a: writes.append(a) or True)
    for name in ("proof_lines", "slot_lines", "unacted_lines", "start_lines"):
        monkeypatch.setattr(conductor, name, lambda *a: [])
    monkeypatch.setattr(conductor.caps, "over_lines", lambda *a: [])
    monkeypatch.setattr(conductor, "branch_line", lambda *a: "main: success at a1b2c3d")
    monkeypatch.setattr(conductor, "stall_report", lambda root, repo: [])
    assert conductor.sweep(tmp_path) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert "main: success at a1b2c3d" in out and out[0].startswith("#7 ")
    refusals = [line for line in out if line.startswith("owner waits:")]
    assert len(refusals) == 1 and "setting: flow.owner_rest_hours" in refusals[0]
    assert "8pm" not in "\n".join(out) and writes == []


def test_1282g_keys_under_a_commented_flow_header_are_not_read(tmp_path):
    """REQ-050: brief #1282 answer 1 and test (g) (#1245)."""
    text = '# [flow]\nowner_wait_minutes = 0\nowner_rest_hours = "late"\n'
    assert settings(tmp_path, text) == {"minutes": 30, "rest": None, "offset": 0}
    text = "[other]\n# [flow]\nowner_wait_minutes = -5\n"
    assert settings(tmp_path, text) == {"minutes": 30, "rest": None, "offset": 0}
    assert {"owner_wait_minutes", "owner_rest_hours", "owner_utc_offset"} <= config.TABLE_KEYS[
        "flow"
    ]


# --- brief #1534 (ADR-0646): an owner's answer is never missed by a park -----------------------

OLD_SHA = "0" * 40
ACCEPT_ASK = "Owner needed: accept the evidence of the current head"


class Hub:
    """`session.gh` recorded: pull request #7 in memory; `on` runs a hook before a write."""

    def __init__(self, comments: list, labels: tuple = (), head: str = SHA) -> None:
        self.comments, self.labels, self.head = list(comments), set(labels), head
        self.calls: list = []
        self.on: dict = {}
        self.missing_label = False

    def __call__(self, endpoint: str, *extra: str, method: str = "GET"):
        self.calls.append((method, endpoint, extra))
        if hook := self.on.pop((method, endpoint.rsplit("/", 1)[-1].split("?")[0]), None):
            hook(self)
        if method == "GET" and endpoint.endswith("/pulls/7"):
            return {
                "number": 7,
                "user": {"login": "builder"},
                "created_at": "2026-11-14T06:00:00Z",
                "head": {"sha": self.head},
                "labels": [{"name": n} for n in sorted(self.labels)],
            }
        if method == "GET" and "/issues/7/comments" in endpoint:
            return list(self.comments)
        if method == "POST" and endpoint.endswith("/labels"):
            self.labels.add(extra[1].split("=", 1)[1])
            return []
        if method == "DELETE" and "/labels/" in endpoint:
            if self.missing_label or "agk:parked" not in self.labels:
                session_mod.LAST_ERROR = "gh: Label does not exist (HTTP 404)"
                return None
            self.labels.discard("agk:parked")
            return {}
        if method == "POST" and endpoint.endswith("/comments"):
            body = extra[1].split("=", 1)[1]
            self.comments.append(at(100 + len(self.comments), "boss", body, 0))
            return {"id": 1}
        raise AssertionError((method, endpoint))

    def writes(self) -> list:
        return [(m, e.rsplit("/", 1)[-1], x) for m, e, x in self.calls if m != "GET"]

    def posted(self) -> list[str]:
        return [x[1].split("=", 1)[1] for m, e, x in self.calls if m == "POST" and "comments" in e]


@pytest.fixture
def hub(monkeypatch):
    def make(comments: list, labels: tuple = (), head: str = SHA) -> Hub:
        made = Hub(comments, labels, head)
        monkeypatch.setattr(session_mod, "gh", made)
        return made

    return make


def apply(seen=None, unpark_only: bool = False):
    return session_mod.owner_apply(
        REPO, 7, PLAIN, LISTED, ANSWERERS, NOW, seen=seen, unpark_only=unpark_only
    )


def answer(cid: int, body: str, minutes: float) -> dict:
    return at(cid, "owner", body, minutes)


def test_1534_an_answer_after_the_callers_read_parks_nothing(hub):
    """REQ-066: brief #1534 answers 1 and 2, edge 1: the caller read no answer, the fresh read
    before the label write sees it, so nothing is written and no second answer is asked for."""
    stale = [asked(90)]
    gh = hub([asked(90), answer(11, "Answer: Q-7-1 the smaller runtime", 0)])
    assert step(pull(), stale) == ("park", "Q-7-1")  # what the caller's own read says
    assert apply(seen=(pull(), stale)) is None
    assert gh.writes() == [] and gh.labels == set()


def test_1534_an_answer_between_the_label_and_the_comment_unparks_at_once(hub):
    """REQ-066: brief #1534 answer 2, edge 1: the read after the write sees the answer and the
    same call unparks; the end state has no label and exactly one `Unparked-by:`."""
    gh = hub([asked(90)])
    gh.on[("POST", "labels")] = lambda h: h.comments.append(
        answer(11, "Answer: Q-7-1 the smaller runtime", 0)
    )
    assert apply() == ("unpark", "Q-7-1")
    assert gh.labels == set()
    assert gh.posted() == ["Parked-by: wait Q-7-1", "Unparked-by: answer Q-7-1"]


def test_1534_an_answer_before_the_park_ends_it(hub):
    """REQ-066: brief #1534 answer 3: an answer older than the `Parked-by:` comment still closes
    the item it parked for (#1532: the answer one second before the mark)."""
    parked = pull(labels=("agk:parked",))
    said = [
        asked(90),
        answer(11, "Maintainer answer: Q-7-1 accept", 31),
        at(12, "boss", PARKED_BY, 30),
    ]
    assert step(parked, said) == ("unpark", "Q-7-1")
    gh = hub(said, labels=("agk:parked",))
    assert apply() == ("unpark", "Q-7-1")
    assert gh.labels == set() and gh.posted() == ["Unparked-by: answer Q-7-1"]
    assert apply() is None and len(gh.posted()) == 1  # a second pass writes nothing


def test_1534_an_answer_to_another_question_does_not_unpark():
    """REQ-066: brief #1534 answer 3, F-st-agk-84-1 (#1519): `Answer: Q-7-2` leaves `wait Q-7-1`."""
    parked = pull(labels=("agk:parked",))
    other = at(9, "builder", "Question: Q-7-2 for the maintainers: which region?", 95)
    said = [other, asked(90), at(12, "boss", PARKED_BY, 30)]
    assert step(parked, [*said, answer(13, "Answer: Q-7-2 the north", 5)]) is None
    assert step(parked, [*said, answer(13, "Maintainer answer: Q-7-2 north", 5)]) is None
    assert step(parked, [*said, answer(13, "Answer: Q-7-1 the smaller runtime", 5)]) == (
        "unpark",
        "Q-7-1",
    )


def test_1534_an_owner_needed_naming_an_answered_question_parks_as_owner_needed():
    """REQ-066: brief #1534 answer 4, F-st-agk-91-1 (#1511, #1516): the key is the open item."""
    said = [
        asked(120),
        answer(11, "Answer: Q-7-1 the smaller runtime", 100),
        at(12, "boss", "Owner needed: Q-7-1 is answered; accept the evidence", 45),
    ]
    assert step(pull(), said) == ("park", "owner-needed")
    still = [asked(120), at(12, "boss", "Owner needed: Q-7-1 is still open", 45)]
    assert step(pull(), still) == ("park", "Q-7-1")


def test_1534_an_accept_of_an_old_head_does_not_end_the_wait():
    """REQ-066: brief #1534 answer 4 and Q-2: only an accept naming the current head closes it."""
    ask = at(11, "boss", ACCEPT_ASK, 45)
    old = answer(12, f"Maintainer answer: accept {OLD_SHA}", 40)
    assert step(pull(), [ask, old]) == ("park", "owner-needed")
    now = answer(12, f"Maintainer answer: accept {SHA}", 40)
    assert step(pull(), [ask, now]) is None
    parked = pull(labels=("agk:parked",))
    mark = at(13, "boss", "Parked-by: wait owner-needed", 10)
    assert step(parked, [ask, mark, answer(14, f"Maintainer answer: accept {OLD_SHA}", 5)]) is None
    assert step(parked, [ask, mark, answer(14, f"Maintainer answer: accept {SHA}", 5)]) == (
        "unpark",
        "owner-needed",
    )


def test_1534_two_answers_write_one_unpark(hub):
    """REQ-066: brief #1534 edge 3: the second answer after the unpark writes nothing."""
    said = [asked(90), at(12, "boss", PARKED_BY, 30), answer(13, "Answer: Q-7-1 small", 5)]
    gh = hub(said, labels=("agk:parked",))
    assert apply(unpark_only=True) == ("unpark", "Q-7-1")
    gh.comments.append(answer(40, "Answer: Q-7-1 small, again", 0))
    assert apply(unpark_only=True) is None
    assert gh.posted() == ["Unparked-by: answer Q-7-1"]


def test_1534_a_label_removed_by_hand_gets_one_repair_unparked_by(hub):
    """REQ-066: brief #1534 answer 3, edge 9: no label, an open `Parked-by:` of this rule."""
    said = [asked(90), at(12, "boss", PARKED_BY, 30), answer(13, "Answer: Q-7-1 small", 5)]
    gh = hub(said)
    assert apply(unpark_only=True) == ("repair", "Q-7-1")
    assert gh.posted() == ["Unparked-by: answer Q-7-1"]
    assert [w[0] for w in gh.writes()] == ["POST"]  # no label write, no DELETE
    assert apply(unpark_only=True) is None and len(gh.posted()) == 1
    assert session_mod.unparked_owed(pull(), gh.comments)


def test_1534_a_delete_answered_404_counts_as_done(hub):
    """REQ-066: brief #1534 answer 3, edge 10: the label already gone is an unpark done."""
    said = [asked(90), at(12, "boss", PARKED_BY, 30), answer(13, "Answer: Q-7-1 small", 5)]
    gh = hub(said, labels=("agk:parked",))
    gh.missing_label = True
    assert apply(unpark_only=True) == ("unpark", "Q-7-1")
    assert gh.posted() == ["Unparked-by: answer Q-7-1"]


def test_1534_a_persons_own_park_is_never_touched_by_the_apply(hub):
    """REQ-066: brief #1534 answer 3, edge 6: no `Parked-by:` of this rule, no write at all."""
    gh = hub([asked(90), answer(13, "Answer: Q-7-1 small", 5)], labels=("agk:parked",))
    assert apply() is None and apply(unpark_only=True) is None
    assert gh.writes() == []


def test_1534_unpark_only_never_parks(hub):
    """REQ-066: brief #1534 answer 5: the router's half writes no park."""
    gh = hub([asked(90)])
    assert apply(unpark_only=True) is None and gh.writes() == []


def test_1534_the_fresh_read_skips_the_runs_memo(hub, monkeypatch):
    """REQ-066: brief #1534 answer 1: the read before a write never answers from the run's memo."""
    gh = hub([asked(90), answer(11, "Answer: Q-7-1 small", 0)])
    stale = {(f"repos/{REPO}/issues/7/comments?per_page=100&page=1",): [asked(90)]}
    monkeypatch.setattr(session_mod, "MEMO", stale)
    assert apply() is None and gh.writes() == []
    assert session_mod.MEMO is stale  # restored for the rest of the run


def test_1534_sweep_and_steward_write_only_through_the_apply(monkeypatch):
    """REQ-066: brief #1534 answer 1: `park_pull` and `unpark_pull` are called from `owner_apply`
    alone; every caller goes through it."""
    import inspect

    import steward_owner

    for module in (conductor, steward_owner):
        text = inspect.getsource(module)
        assert "park_pull(" not in text.replace("owner_apply", ""), module.__name__
    text = inspect.getsource(session_mod.owner_park)
    assert "owner_apply(" in text and "park_pull(" not in text


def test_1534_the_supervisor_runs_the_owner_step_while_a_job_runs(monkeypatch, capsys):
    """REQ-066: brief #1534 answer 6, edge 5: a pass that finds a job running still unparks, and
    moves no read mark, so the job that follows sees the change."""
    kept: list = []
    monkeypatch.setattr(conductor, "pass_state", lambda root: {"seen_at": "x"})
    monkeypatch.setattr(conductor, "job_running", lambda *a: True)
    monkeypatch.setattr(conductor, "keep_state", lambda root, state: kept.append(dict(state)))
    monkeypatch.setattr(
        conductor, "owner_pass", lambda root, repo, now: ["UNPARKED #7 Q-7-1; run: x"]
    )
    assert conductor.watchdog_pass("root", "c1", REPO, "none") == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["UNPARKED #7 Q-7-1; run: x", "watchdog: job c1 still running; nothing started"]
    assert kept == []


def test_1534_the_owner_pass_reads_only_waiting_pull_requests(monkeypatch):
    """REQ-066: brief #1534 answers 6 and 7, edge 13: a quiet pass makes no read; a pending one
    reads the comments of each waiting pull request only, and a member's machine writes nothing."""
    monkeypatch.setattr(conductor.common, "personal_table", lambda root: None)
    monkeypatch.setattr(conductor, "change_reads", lambda *a: (True, None))
    monkeypatch.setattr(conductor, "pass_state", lambda root: {})
    applied: list = []
    monkeypatch.setattr(
        conductor.session, "owner_apply", lambda *a, **k: applied.append(a[1]) or None
    )
    assert conductor.owner_pass("root", REPO, NOW) == [] and applied == []
    monkeypatch.setattr(conductor, "change_reads", lambda *a: (False, "d"))
    pulls = [
        {"number": 5, "labels": []},
        {"number": 7, "labels": [{"name": "agk:parked"}]},
        {"number": 8, "labels": [{"name": "agk:question"}]},
    ]
    monkeypatch.setattr(conductor.session, "pages", lambda endpoint: pulls)
    monkeypatch.setattr(conductor, "refused_here", lambda root: False)
    monkeypatch.setattr(conductor.session, "owner_wait_settings", lambda root: PLAIN)
    monkeypatch.setattr(conductor, "verdict_authors", lambda root: ["boss"])
    monkeypatch.setattr(conductor, "spec_approvers", lambda root: ["owner"])
    monkeypatch.setattr(conductor.common, "personal_table", lambda root: None)
    assert conductor.owner_pass("root", REPO, NOW) == [] and applied == [7, 8]
    applied.clear()
    monkeypatch.setattr(conductor, "refused_here", lambda root: True)
    assert conductor.owner_pass("root", REPO, NOW) == [] and applied == []


# --- brief #1567 (ADR-0657): the owner's Report on its own parked pull request unparks it -------

HAND_FLOW = "Flow: owner change, merged by hand with the owner's merge command"
BUILDER_FLOW = "Flow: builder cb40, one pull request for brief #40; the owner merges it by hand"
NEEDED = "Owner needed: add the body line, then run the owner's merge command"
OWNER_PARK = "Parked-by: wait owner-needed"
READY = f"Report: {SHA} ready for review: the local evidence is in the body"


def mine(body: str = HAND_FLOW, labels: tuple = ("agk:parked",), author: str = "owner") -> dict:
    """The owner's own pull request #7: a hand change by a spec approver."""
    return {**pull(author=author, labels=labels), "number": 7, "body": f"Brief: #40\n{body}\n"}


def reported(minutes: float = 5, text: str = READY, login: str = "owner") -> dict:
    return at(14, login, text, minutes)


def owner_wait(park: bool = True) -> list:
    said = [at(11, "boss", NEEDED, 80)]
    return [*said, at(12, "boss", OWNER_PARK, 40)] if park else said


def test_1567_a_head_report_closes_owner_needed_only_on_the_owners_own_pull_request():
    """REQ-066: brief #1567 answer 1: with `own`, the author's ready report on the current head,
    after the `Owner needed:`, closes the `owner-needed` item; without it nothing changes."""
    said = [*owner_wait(), reported()]
    assert session_mod.open_owner_items(mine(), said, LISTED, ANSWERERS) != {}
    assert session_mod.open_owner_items(mine(), said, LISTED, ANSWERERS, own=True) == {}
    assert step(mine(), said) is None  # today's reading: the park stays
    assert session_mod.owner_step(mine(), said, PLAIN, NOW, LISTED, ANSWERERS, own=True) == (
        "unpark",
        "owner-needed",
    )


@pytest.mark.parametrize(
    "late",
    [
        reported(text=f"Report: {OLD_SHA} ready for review"),  # an older head
        reported(text=f"Report: {SHA[:8]} handing over: blocked: the owner merges"),
        reported(login="builder"),  # not the pull request's author
        at(14, "owner", f"Question: Q-7-1 for the maintainers: {SHA}", 5),
    ],
)
def test_1567_an_old_head_a_hand_over_or_another_login_leaves_the_park(late):
    """REQ-066: brief #1567 edge cases 2 and 5: only a ready report on the head, by the author."""
    said = [*owner_wait(), late]
    assert session_mod.owner_step(mine(), said, PLAIN, NOW, LISTED, ANSWERERS, own=True) is None


def test_1567_a_report_before_the_owner_needed_leaves_the_park():
    """REQ-066: brief #1567 edge case 3: the report must follow the ask it closes."""
    said = [reported(90), *owner_wait()]
    assert session_mod.owner_step(mine(), said, PLAIN, NOW, LISTED, ANSWERERS, own=True) is None


def test_1567_an_owner_needed_with_an_open_question_stays_open():
    """REQ-066: brief #1567 edge case 4: a Q id question closes only by its answer."""
    ask = at(10, "owner", "Question: Q-7-1 for the maintainers: which runtime?", 95)
    named = at(11, "boss", "Owner needed: Q-7-1 is still open", 80)
    said = [ask, named, at(12, "boss", "Parked-by: wait Q-7-1", 40), reported()]
    assert session_mod.owner_step(mine(), said, PLAIN, NOW, LISTED, ANSWERERS, own=True) is None
    plain = [ask, *owner_wait(), reported()]  # the Q id stays open after the report
    assert session_mod.open_owner_items(mine(), plain, LISTED, ANSWERERS, own=True) == {
        "Q-7-1": session_mod.moment(ask["created_at"])
    }


@pytest.mark.parametrize("minutes", [0, 30, 600])
def test_1567_the_wait_setting_and_rest_hours_do_not_hold_the_report(minutes):
    """REQ-066: brief #1567 answer 3: `owner_wait_minutes` (any good value) and a rest-hours
    park unpark on the report the same way; a report before the wait passed parks nothing."""
    said = [*owner_wait(), reported()]
    for settings in ({**PLAIN, "minutes": minutes}, {**NIGHTS, "minutes": minutes}):
        night = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)  # 22:30 at +05:30, inside rest hours
        for now in (NOW, night):
            got = session_mod.owner_step(mine(), said, settings, now, LISTED, ANSWERERS, own=True)
            assert got == ("unpark", "owner-needed")
            early = [*owner_wait(park=False), reported()]
            unparked = mine(labels=())
            assert (
                session_mod.owner_step(unparked, early, settings, now, LISTED, ANSWERERS, own=True)
                is None
            )


def test_1567_a_persons_own_park_is_never_removed_by_a_report():
    """REQ-066: brief #1567 answer 3: an `agk:parked` with no `Parked-by:` of the rule stays."""
    said = [*owner_wait(park=False), reported()]
    assert session_mod.owner_step(mine(), said, PLAIN, NOW, LISTED, ANSWERERS, own=True) is None


class OwnHub(Hub):
    """Hub with the pull request's body and author, and the comments of its brief #40."""

    def __init__(self, comments, labels=("agk:parked",), body=HAND_FLOW, brief=(), author="owner"):
        super().__init__(comments, labels)
        self.body, self.brief, self.author = body, (None if brief is None else list(brief)), author

    def __call__(self, endpoint: str, *extra: str, method: str = "GET"):
        if method == "GET" and "/issues/40/comments" in endpoint:
            self.calls.append((method, endpoint, extra))
            return None if self.brief is None else list(self.brief)
        got = super().__call__(endpoint, *extra, method=method)
        if method == "GET" and endpoint.endswith("/pulls/7"):
            got = {**got, "state": "open", "body": f"Brief: #40\n{self.body}\n",
                   "user": {"login": self.author}}  # fmt: skip
        return got


@pytest.fixture
def own_hub(monkeypatch):
    monkeypatch.setattr(session_mod, "spec_approvers", lambda root: ["owner"])

    def make(comments: list, **kw) -> OwnHub:
        made = OwnHub(comments, **kw)
        monkeypatch.setattr(session_mod, "gh", made)
        return made

    return make


TAKEN = at(30, "builder", "taken: cb40 2026-11-14", 300)
RELEASED = at(31, "builder", "released: cb40", 290)


def test_1567_the_owners_hand_change_unparks_with_one_report_mark(own_hub):
    """REQ-066: brief #1567 answers 1 and 2, `Measured:` after: the #1561 comments replayed (an
    `Owner needed:`, the park, the owner's ready report) unpark at the report, with the label
    removed and one `Unparked-by: report <sha12>`; a second pass writes nothing."""
    gh = own_hub([*owner_wait(), reported()])
    assert apply() == ("unpark", "owner-needed")
    assert gh.labels == set()
    assert gh.posted() == [f"Unparked-by: report {SHA[:12]}"]
    assert session_mod.own_park(gh.comments) is None  # the park is over
    assert not session_mod.unparked_owed(mine(labels=()), gh.comments)  # no builder resumes it
    assert apply() is None and len(gh.posted()) == 1
    gh = own_hub([*owner_wait(), reported()])
    assert apply(unpark_only=True) == ("unpark", "owner-needed")  # the router's half too


def test_1567_a_live_take_on_the_brief_keeps_the_park(own_hub):
    """REQ-066: brief #1567 Q-1 with the answer to Q-1567-1: on a hand change, a live `taken:`
    newer than the `Owner needed:` with no hand-over keeps the park; a released take is not
    live; an unreadable brief keeps it."""
    fresh = at(32, "builder", "taken: cb41 2026-11-14", 60)  # after the ask of 80 minutes ago
    gh = own_hub([*owner_wait(), reported()], brief=[fresh])
    assert apply() is None and gh.writes() == []
    gh = own_hub(
        [*owner_wait(), reported()], brief=[fresh, at(33, "builder", "released: cb41", 50)]
    )
    assert apply() == ("unpark", "owner-needed")
    gh = own_hub([*owner_wait(), reported()], brief=None)
    assert apply() is None and gh.writes() == []


HANDED = f"Report: {SHA[:8]} handing over: blocked: the owner makes the commit"


def test_1567_an_old_or_handed_over_take_no_longer_counts(own_hub):
    """REQ-066: brief #1567, the answer to Q-1567-1 (2026-11-20 09:20Z): a take older than the
    `Owner needed:` (#1561: brief #1536's three takes of 11-19) or whose session then posted a
    `handing over` report, on the brief or the pull request, no longer keeps the park."""
    gh = own_hub([*owner_wait(), reported()], brief=[TAKEN])  # 300 minutes, before the ask
    assert apply() == ("unpark", "owner-needed")
    fresh = at(32, "builder", "taken: cb41 2026-11-14", 60)
    gh = own_hub([*owner_wait(), reported()], brief=[fresh, at(34, "builder", HANDED, 55)])
    assert apply() == ("unpark", "owner-needed")
    said = [*owner_wait(), at(13, "builder", HANDED, 20), reported()]
    gh = own_hub(said, brief=[fresh])  # the hand-over on the pull request itself
    assert apply() == ("unpark", "owner-needed")
    later = at(35, "builder", "taken: cb42 2026-11-14", 50)  # a new take after the hand-over
    gh = own_hub([*owner_wait(), reported()], brief=[fresh, at(34, "builder", HANDED, 55), later])
    assert apply() is None and gh.writes() == []
    early = at(36, "builder", HANDED, 70)  # a hand-over before the take ends nothing of it
    gh = own_hub([*owner_wait(), reported()], brief=[early, fresh])
    assert apply() is None and gh.writes() == []


def test_1567_a_builders_report_on_a_builders_pull_request_leaves_the_park(own_hub):
    """REQ-066: brief #1567 edge case 1: a builder's `Flow:` line, even one that says "by hand",
    is no hand change; a spec approver's pull request counts only when no take ever named its
    brief; another author's never does."""
    said = [*owner_wait(), reported(login="builder")]
    gh = own_hub(said, body=BUILDER_FLOW, author="builder")
    assert apply() is None and gh.writes() == []
    said = [*owner_wait(), reported()]
    gh = own_hub(said, body=BUILDER_FLOW, brief=[TAKEN, RELEASED])
    assert apply() is None and gh.writes() == []
    gh = own_hub(said, body=BUILDER_FLOW)  # the approver's own, no take ever
    assert apply() == ("unpark", "owner-needed")
    gh = own_hub(said, body=BUILDER_FLOW, author="stranger")
    assert apply() is None and gh.writes() == []


def test_1567_the_brief_is_read_only_when_a_report_could_close_the_wait(own_hub):
    """REQ-066: brief #1567 answer 2: a park with no head report reads no brief."""
    gh = own_hub(owner_wait())
    assert apply() is None
    assert not any("/issues/40/" in c[1] for c in gh.calls)


def test_1567_personal_mode_parks_nothing_and_reads_nothing(monkeypatch):
    """REQ-066: brief #1567 answer 3, `[personal] forge = "files"`: the owner pass is empty."""
    monkeypatch.setattr(conductor.common, "personal_table", lambda root: {"forge": "files"})
    monkeypatch.setattr(
        conductor.session, "owner_apply", lambda *a, **k: pytest.fail("no owner step")
    )
    assert conductor.owner_pass("root", REPO, NOW) == []


def test_1567_the_local_pass_unparks_through_the_one_owner_step(monkeypatch, own_hub):
    """REQ-066: brief #1567 answer 3, `execution` local: the conductor's sweep unparks on the
    report and prints the resume line, through `owner_apply`."""
    own_hub([*owner_wait(), reported()])
    monkeypatch.setattr(conductor, "parked_mark", lambda root: None)
    monkeypatch.setattr(conductor, "read", lambda endpoint, what: session_mod.gh(endpoint))
    pulls = [mine()]
    lines = conductor.owner_lines("root", REPO, pulls, PLAIN, ["boss"], ["owner"], NOW)
    assert lines == [conductor.unparked_line(7, "owner-needed")]
