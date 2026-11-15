"""The owner question, its relay and the steward's parking (SPEC-0059 rules 5, 10 and 14; brief
#1322, ADR-0559; REQ-066 AC3 and AC6).

A recorded `gh` double stands in for GitHub (each call kept); no network, no model, invented data
only (example.com).
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import conductor  # noqa: E402
import steward_owner  # noqa: E402

NOW = datetime(2026, 11, 15, 13, 0, tzinfo=UTC)
REPO = "acme/widgets"
PLAIN = {"minutes": 30, "rest": None, "offset": 0}
GOOD = (
    "Should the report go out on Friday as planned, or wait a week for the second data source? "
    "I recommend waiting: the first source alone misses two of the five totals."
)
PLANTED = [
    "Should we keep `report.md` or drop it? I recommend keeping it.",
    "Should the agk:parked label stay or go? I recommend it stays.",
    "Does rule 10 still hold, or not? I recommend it does.",
    "Is ADR-0559 right, or wrong? I recommend right.",
    "Should I run python3 now or later? I recommend now.",
    "Should the pull request wait, or go? I recommend wait.",
    "Should it run with --force or not? I recommend not.",
    "Should #42 close now or later? I recommend later.",
]


def at(cid: int, login: str, body: str, minutes: float) -> dict:
    when = (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


class GitHub:
    """`session.gh` recorded: one pull request #7 with its labels and comments in memory."""

    def __init__(self, comments: list, labels: tuple = ()) -> None:
        self.comments, self.labels, self.calls = list(comments), set(labels), []

    def __call__(self, endpoint: str, *extra: str, method: str = "GET"):
        self.calls.append((method, endpoint, extra))
        if method == "GET" and endpoint.endswith("/pulls/7"):
            return {
                "number": 7,
                "user": {"login": "builder1"},
                "created_at": "2026-11-15T10:00:00Z",
                "labels": [{"name": n} for n in sorted(self.labels)],
            }
        if method == "GET" and "/issues/7/comments" in endpoint:
            return list(self.comments)
        if method == "POST" and endpoint.endswith("/labels"):
            self.labels.add(extra[1].split("=", 1)[1])
            return []
        if method == "DELETE" and "/labels/" in endpoint:
            self.labels.discard("agk:parked")
            return {}
        if method == "POST" and endpoint.endswith("/comments"):
            body = extra[1].split("=", 1)[1]
            self.comments.append(at(100 + len(self.comments), "boss", body, 0))
            return {"id": 1}
        raise AssertionError((method, endpoint))

    def posted(self) -> list[str]:
        return [
            x[2][1].split("=", 1)[1] for x in self.calls if x[0] == "POST" and "comments" in x[1]
        ]


@pytest.fixture
def root(tmp_path, monkeypatch):
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    monkeypatch.setattr(steward_owner.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(
        steward_owner.session, "owner_people", lambda r, p: ({"boss"}, {"boss", "owner"})
    )
    monkeypatch.setattr(steward_owner.session, "owner_wait_settings", lambda r: PLAIN)
    told: list = []
    monkeypatch.setattr(steward_owner.session, "tell", lambda r, me, text: told.append((me, text)))
    records: list = []
    monkeypatch.setattr(
        steward_owner.steward,
        "record",
        lambda r, kind, text, gh: records.append((kind, text)) or (0, ["recorded"]),
    )
    return tmp_path, told, records


def personal(root: Path) -> None:
    (root / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")


def test_req066_the_owner_question_has_no_kit_term(root):
    """REQ-066 AC3: rule 5, one plain sentence with choices and a recommendation; each planted kit
    term is refused naming the rule, never the term."""
    assert steward_owner.question_problem(GOOD) is None
    for text in PLANTED:
        found = steward_owner.question_problem(text)
        assert found and "kit term" in found and "SPEC-0059 rule 5" in found, text
        assert not any(w in found for w in ("report.md", "agk:parked", "ADR-0559", "--force"))
    assert "recommendation" in steward_owner.question_problem("Ship it on Friday?")
    assert "one line" in steward_owner.question_problem(f"{GOOD}\nA second line.")


def test_req066_ask_records_tells_the_owner_and_posts_for_the_maintainers(
    root, monkeypatch, capsys
):
    """REQ-066 AC3: rule 5, the memory entry, the sentence for the chat and the `Question:` line."""
    base, _, records = root
    gh = GitHub([])
    monkeypatch.setattr(steward_owner.session, "gh", gh)
    code, lines = steward_owner.ask(base, "Q-7-1", 7, GOOD + "\n")
    assert code == 0 and lines[0] == f"ask the owner: {GOOD}"
    assert records == [("Owner question", f"Q-7-1 {GOOD}")]
    assert gh.posted() == [f"Question: Q-7-1 for the maintainers: {GOOD}\n\nWho: AGK steward"]


def test_req066_a_relay_without_the_owners_quote_or_a_malformed_one_is_refused():
    """REQ-066 AC3: rule 5, the three lines of a relayed owner answer."""
    good = steward_owner.relay_body(
        "Q-7-1", "wait a week", "Wait a week, the totals matter.", "2026-11-15T12:40Z"
    )
    assert good.splitlines() == [
        "Maintainer answer: Q-7-1 wait a week",
        'Owner said (2026-11-15T12:40Z): "Wait a week, the totals matter."',
        "Who: ProductOwner",
    ]
    assert steward_owner.relay_problem(good) is None
    missing = "Maintainer answer: Q-7-1 wait a week\nWho: ProductOwner\n"
    assert "second line" in steward_owner.relay_problem(missing)
    for said in (
        'Owner said: "Wait."',
        'Owner said (15 Nov 18:10 IST): "Wait."',
        "Owner said (2026-11-15T12:40Z): Wait.",
        'Owner said (2026-11-15T12:40Z): ""',
    ):
        body = f"Maintainer answer: Q-7-1 wait\n{said}\nWho: ProductOwner\n"
        assert "second line" in steward_owner.relay_problem(body), said
    no_who = 'Maintainer answer: Q-7-1 wait\nOwner said (2026-11-15T12:40Z): "Wait."\n'
    assert "last line" in steward_owner.relay_problem(no_who)


def relay_args(base: Path, words: str = "Wait a week, the totals matter.") -> list[str]:
    said = base / "said.txt"
    said.write_text(words + "\n", encoding="utf-8")
    return [
        "relay",
        "--qid",
        "Q-7-1",
        "--on",
        "7",
        "--answer",
        "wait a week",
        "--said",
        str(said),
        "--at",
        "2026-11-15T12:40Z",
        "--conductor",
        "c1",
    ]


def test_req066_rule10a_the_steward_parks_an_unanswered_owner_question(root, monkeypatch):
    """REQ-066 AC6: rule 10 (a), an owner question unanswered for the wait parks it."""
    base, told, _ = root
    gh = GitHub([at(1, "boss", "Question: Q-7-1 for the maintainers: Friday or a week?", 31)])
    monkeypatch.setattr(steward_owner.session, "gh", gh)
    assert steward_owner.park(base, 7, "c1", NOW) == (0, ["parked #7 Q-7-1"])
    assert "agk:parked" in gh.labels and gh.posted()[-1].startswith("Parked-by: wait Q-7-1")
    assert told == []


def test_req066_rule10b_an_answer_within_the_wait_parks_nothing(root, monkeypatch):
    """REQ-066 AC6: rule 10 (b), the owner's answer, or the steward's evidence answer, within the
    wait parks nothing."""
    base, _, _ = root
    asked = at(1, "boss", "Question: Q-7-1 for the maintainers: Friday or a week?", 31)
    for answer in ("Maintainer answer: Q-7-1 wait", "Answer: Q-7-1 wait (evidence: docs/x.md)"):
        gh = GitHub([asked, at(2, "boss", answer, 20)])
        monkeypatch.setattr(steward_owner.session, "gh", gh)
        assert steward_owner.park(base, 7, "c1", NOW) == (0, ["#7: nothing to park"])
        assert gh.labels == set()


def test_req066_rule10c_the_relay_unparks_and_tells_the_conductor_once(root, monkeypatch, capsys):
    """REQ-066 AC6: rule 10 (c), the owner's reply relayed after parking removes the label and
    sends one `Tell:` naming the pull request and the Q id."""
    base, told, _ = root
    gh = GitHub(
        [
            at(1, "boss", "Question: Q-7-1 for the maintainers: Friday or a week?", 90),
            at(2, "boss", "Parked-by: wait Q-7-1", 50),
        ],
        labels=("agk:parked",),
    )
    monkeypatch.setattr(steward_owner.session, "gh", gh)
    monkeypatch.setattr(steward_owner, "repo_root", lambda: base)
    assert steward_owner.main(relay_args(base)) == 0
    assert gh.posted()[0].startswith("Maintainer answer: Q-7-1 wait a week\nOwner said")
    assert gh.labels == set() and gh.posted()[-1].startswith("Unparked-by: answer Q-7-1")
    assert told == [("c1", "parked #7 answered Q-7-1")]
    assert "unparked #7 Q-7-1" in capsys.readouterr().out


def test_req066_rule10_a_conductor_with_no_steward_still_parks_and_resumes(monkeypatch, tmp_path):
    """REQ-066 AC6: rule 10, with no steward the conductor's sweep parks and unparks as before."""
    comments = [at(1, "builder1", "Question: Q-7-1 for the maintainers: Friday or a week?", 40)]
    labels: set = set()

    def park(repo, number, key):
        labels.add("agk:parked")
        comments.append(at(5, "boss", f"Parked-by: wait {key}", 0))
        return True

    monkeypatch.setattr(conductor, "read", lambda endpoint, what: list(comments))
    monkeypatch.setattr(conductor.session, "park_pull", park)
    monkeypatch.setattr(conductor.session, "unpark_pull", lambda *a: labels.clear() or True)
    monkeypatch.setattr(conductor, "parked_mark", lambda root: tmp_path / "parked")

    def lines() -> list[str]:
        pull = {
            "number": 7,
            "user": {"login": "builder1"},
            "created_at": "2026-11-15T10:00:00Z",
            "labels": [{"name": n} for n in labels],
        }
        return conductor.owner_lines("root", REPO, [pull], PLAIN, ["boss"], ["owner"], NOW)

    assert lines() == ["PARKED #7 Q-7-1"]
    comments.append(at(6, "owner", "Maintainer answer: Q-7-1 wait", 0))
    assert lines() == ["UNPARKED #7 Q-7-1; run: python3 scripts/agk/session.py resume --pr 7"]


def test_req066_rule14_personal_mode_prints_and_parks_nothing(root, monkeypatch, capsys):
    """REQ-066 AC3 and AC6: rule 14, in personal mode the question and the relay are printed,
    nothing is posted and nothing is parked."""
    base, told, records = root
    personal(base)
    gh = GitHub([])
    monkeypatch.setattr(steward_owner.session, "gh", gh)
    monkeypatch.setattr(steward_owner, "repo_root", lambda: base)
    code, lines = steward_owner.ask(base, "Q-7-1", 7, GOOD)
    assert code == 0 and lines[1] == f"post on #7: Question: Q-7-1 for the maintainers: {GOOD}"
    assert steward_owner.main(relay_args(base)) == 0
    out = capsys.readouterr().out
    assert 'Owner said (2026-11-15T12:40Z): "Wait a week, the totals matter."' in out
    assert steward_owner.park(base, 7, "c1", NOW) == (0, ["personal mode: nothing is parked"])
    assert gh.calls == [] and told == [] and len(records) == 1
