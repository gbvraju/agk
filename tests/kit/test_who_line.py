"""Every comment AGK posts ends with a light `Who: AGK` line (brief #1289, ADR-0546; REQ-050).

The owner and every AGK session post as one GitHub login, so the history cannot tell them apart
at a glance. The line is a marker, not a rule: `common.with_who` appends it once, the writers of
`session.py`, `conductor.py`, `route.py` and `merge_cleared.py` pass each comment body through
it, every parser that reads a first line (or a whole take) reads a body with the line exactly as
without it, and nothing refuses or blocks a body that has no line. Recorded doubles stand in for
`gh`; invented data only; no network. The tests were written first (answer 5).
"""

from __future__ import annotations

import subprocess  # nosec B404 - the doubles below replace subprocess.run; nothing is started
from datetime import UTC, datetime
from pathlib import Path

import common
import conductor
import merge_cleared
import pytest
import route
import session

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
SHA = "a" * 40
COMMENTS = "repos/example/project/issues/5/comments"
EDIT = "repos/example/project/issues/comments/77"


# --- (a) with_who appends once and never twice ----------------------------------------------


def test_with_who_appends_one_last_line():
    """REQ-050: brief #1289 answer 1."""
    assert common.with_who("Report: abc ready") == "Report: abc ready\n\nWho: AGK"
    assert common.with_who("Report: abc ready\n") == "Report: abc ready\n\nWho: AGK"


def test_with_who_names_the_role_when_known():
    """REQ-050: brief #1289 answer 1 (`Who: AGK <role>`)."""
    assert common.with_who("Tell: s1 hi", role="conductor") == "Tell: s1 hi\n\nWho: AGK conductor"


def test_with_who_never_appends_twice():
    """REQ-050: brief #1289 answer 1 (unless the body already ends with a `Who:` line)."""
    once = common.with_who("taken: s1 2026-11-14")
    assert common.with_who(once) == once
    assert common.with_who(once, role="router") == once
    owner = 'Owner decision 2026-11-14 10:00 IST: "yes"\n\nWho: ProductOwner'
    assert common.with_who(owner) == owner


def test_a_relayed_owner_decision_ends_with_who_productowner():
    """REQ-050: brief #1289 answer 3."""
    text = common.with_who('Owner, 2026-11-14 10:00 IST: "keep it"', who="ProductOwner")
    assert text.splitlines()[-1] == "Who: ProductOwner"


def test_without_who_takes_the_line_off_again():
    """REQ-050: brief #1289 answer 4 (the line is last, so a reader can drop it)."""
    assert common.without_who(common.with_who("Slot: x\nlast run: y")) == "Slot: x\nlast run: y"
    assert common.without_who("Unreadable: z") == "Unreadable: z"


# --- (b) the four posting scripts' comment bodies end with `Who: AGK` -------------------------


class Recorded:
    """A double of `subprocess.run` that records each argv and answers `{}`."""

    def __init__(self) -> None:
        self.argv: list[list[str]] = []

    def __call__(self, argv, **_kwargs):
        self.argv.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "{}", "")

    def bodies(self) -> list[str]:
        return [a.split("=", 1)[1] for argv in self.argv for a in argv if a.startswith("body=")]


@pytest.fixture
def recorded(monkeypatch):
    double = Recorded()
    monkeypatch.setattr(subprocess, "run", double)
    return double


def test_session_comments_end_with_who_agk(recorded):
    """REQ-050: brief #1289 answers 1 and 5b (session.py: claim, tell, slot and the rest)."""
    session.gh(COMMENTS, "-f", "body=taken: s1 2026-11-14", method="POST")
    session.gh(EDIT, "-f", "body=Slot: active 2026-11-14T10:00:00Z b1 r1", method="PATCH")
    assert recorded.bodies() == [
        "taken: s1 2026-11-14\n\nWho: AGK",
        "Slot: active 2026-11-14T10:00:00Z b1 r1\n\nWho: AGK",
    ]


def test_session_tell_posts_the_line_through_the_cli(tmp_path, monkeypatch, recorded):
    """REQ-050: brief #1289 answer 5b, through `tell` itself."""
    monkeypatch.setattr(session, "conductor_issue", lambda repo: 204)
    monkeypatch.setattr(session, "repo_name", lambda root: "example/project")
    assert session.tell(tmp_path, "builder-b", "merge main") == 0
    assert recorded.bodies() == ["Tell: builder-b merge main\n\nWho: AGK"]


def test_issue_bodies_and_labels_are_not_changed(recorded):
    """REQ-050: brief #1289 answer 1 (labels and issue bodies are not changed)."""
    session.gh("repos/example/project/issues", "-f", "body=Continues #4.", method="POST")
    session.gh("repos/example/project/issues/5", "-f", "body=brief", method="PATCH")
    session.gh("repos/example/project/issues/5/labels", "-f", "labels[]=agk:taken", method="POST")
    assert recorded.bodies() == ["Continues #4.", "brief"]
    assert ["-f", "labels[]=agk:taken"] == recorded.argv[-1][5:7]


def test_conductor_comments_end_with_who_agk_conductor(recorded):
    """REQ-050: brief #1289 answers 1 and 5b (conductor.py)."""
    conductor.post(COMMENTS, "refused", "-f", f"body=Report: {SHA} merge of main")
    conductor.write_marker("example/project", 5, ({"id": 77}, None), "body=Conductor: released x")
    assert recorded.bodies() == [
        f"Report: {SHA} merge of main\n\nWho: AGK conductor",
        "Conductor: released x\n\nWho: AGK conductor",
    ]


def test_route_comments_end_with_who_agk_router(recorded):
    """REQ-050: brief #1289 answers 1 and 5b (route.py)."""
    route.write(COMMENTS, "-f", "body=Correction needed: x (verdict comment 9)", method="POST")
    route.write("repos/example/project/issues", "-f", "body=red", method="POST")
    assert recorded.bodies() == [
        "Correction needed: x (verdict comment 9)\n\nWho: AGK router",
        "red",
    ]


def test_merge_cleared_comments_end_with_who_agk(recorded):
    """REQ-050: brief #1289 answers 1 and 5b (merge_cleared.py)."""
    merge_cleared.write_once(["--method", "POST", COMMENTS, "-f", "body=Auto merge: #5 abc"])
    merge_cleared.write_once(["--method", "PATCH", "repos/example/project/issues/5", "-f",
                              "state=closed"])  # fmt: skip
    assert recorded.bodies() == ["Auto merge: #5 abc\n\nWho: AGK"]
    assert recorded.argv[-1][-2:] == ["-f", "state=closed"]


# --- (c) every first-line parser reads a body with the line exactly as without it -------------


def marked(body: str) -> list[str]:
    """The body as posted before this brief, with the line, and with the runtime's footer too."""
    footer = "\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_"
    return [body, common.with_who(body), common.with_who(body, role="builder") + footer]


def note(cid: int, body: str, login: str = "boss", when: str = "2026-11-14T10:00:00Z") -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": when}


@pytest.mark.parametrize("body", marked("taken: s1 2026-11-14 reserves ADR-0546"))
def test_a_take_reads_the_same(body):
    """REQ-050: brief #1289 answers 4 and 5c (a take is read from the whole body)."""
    found = session.all_takes([note(1, body)])
    assert [(t[2], t[4]) for t in found] == [("s1", ("ADR-0546",))]


@pytest.mark.parametrize("body", marked("taken over: s2 2026-11-14"))
def test_a_takeover_reads_the_same(body):
    """REQ-050: brief #1289 answer 5c."""
    since = datetime(2026, 11, 1, tzinfo=UTC)
    assert session.takeover_lost([note(1, body)], since, "s9") == "s2"


@pytest.mark.parametrize("body", marked("released: s1"))
def test_a_release_reads_the_same(body):
    """REQ-050: brief #1289 answer 5c."""
    take = note(1, "taken: s1 2026-11-14")
    found = session.all_takes([take, note(2, body, when="2026-11-14T11:00:00Z")])
    assert [t[5] for t in found] == [True]  # the take is freed


@pytest.mark.parametrize("body", marked("Tell: s1 merge main"))
def test_a_tell_reads_the_same(body):
    """REQ-050: brief #1289 answer 5c."""
    assert session.tell_line(note(1, body), "s1", {"boss"}) == "Tell: s1 merge main"


@pytest.mark.parametrize(
    "body",
    marked(
        "Slot: active 2026-11-14T10:00:00Z b1 run1\nlast run: "
        "2026-11-14T09:00:00Z to 2026-11-14T09:05:00Z\ndecided: none"
    ),  # fmt: skip
)
def test_a_slot_marker_reads_the_same(body):
    """REQ-050: brief #1289 answer 5c (the marker and its log lines)."""
    found = session.slot_marker([note(1, body)], "b1", {"boss"})
    assert found is not None and found[1].group(4) == "run1"
    assert session.slot_log(found[0]) == ("2026-11-14T09:00:00Z", "2026-11-14T09:05:00Z", "none")


@pytest.mark.parametrize("body", marked("Parked-by: wait Q-1289-1"))
def test_a_park_reads_the_same(body):
    """REQ-050: brief #1289 answer 5c."""
    found = session.own_park([note(1, body)])
    assert found is not None and found[0] == "Q-1289-1"


@pytest.mark.parametrize("body", marked("Conductor: active 2026-11-14T10:00:00Z c1"))
def test_a_lease_reads_the_same(body):
    """REQ-050: brief #1289 answer 5c."""
    found = conductor.lease_comment([note(1, body)], ["boss"])
    assert found is not None and found[1].group(3) == "c1"


@pytest.mark.parametrize("body", marked(f"Verdict: cleared {SHA}"))
def test_a_verdict_reads_the_same(body):
    """REQ-050: brief #1289 answer 5c (`Verdict:` first lines)."""
    line = session.verdict_line([note(1, body)], 0, SHA, ["boss"])
    assert line == f"verdict cleared {SHA} (comment 1)"
    assert common.verdict_problem(body) is None


@pytest.mark.parametrize("body", marked(f"Verdict: fix list {SHA}\n1. Fix the test (rule: none)"))
def test_a_fix_list_reads_the_same(body):
    """REQ-050: brief #1289 answer 5c (the numbered items of a fix list)."""
    assert common.fix_items(body) == ["1. Fix the test (rule: none)"]


@pytest.mark.parametrize(
    "body", marked(f"Verdict: fix list {SHA}\nFinal: docs/adr/0001-x.md Proposed -> Accepted")
)
def test_final_lines_read_the_same(body):
    """REQ-050: brief #1289 answer 5c (`Final:` lines)."""
    assert common.covered_fix_list(body) == (SHA, [("docs/adr/0001-x.md", None, "Proposed",
                                                    "Accepted")])  # fmt: skip
    assert common.verdict_problem(body) is None


@pytest.mark.parametrize("body", marked(f"Report: {SHA} handing over: done"))
def test_a_report_reads_the_same(body):
    """REQ-050: brief #1289 answer 5c (`Report:` first lines)."""
    first = merge_cleared.first_line({"body": body})
    assert (
        route.HANDING_OVER.match(first) is not None and first == f"Report: {SHA} handing over: done"
    )


def test_the_merger_says_a_line_once_with_or_without_the_who_line(monkeypatch, recorded):
    """REQ-050: brief #1289 answer 5c (`post_once` matches the first line, so it never repeats)."""
    said = [note(1, common.with_who("merger: held"))]
    monkeypatch.setattr(merge_cleared, "read_comments", lambda repo, number: said)
    merge_cleared.post_once("example/project", 5, "merger: held")
    assert recorded.argv == []


def test_the_router_says_unreadable_once_with_or_without_the_who_line(monkeypatch, recorded):
    """REQ-050: brief #1289 answer 5c (an `Unreadable:` line is found again by its text)."""
    bad = note(9, "Verdict cleared: no colon where the router reads one")
    said = note(10, common.with_who("Unreadable: x (comment 9)", role="router"))
    route.report_unreadable("example/project", 5, [bad, said], [(bad, "x")])
    assert recorded.argv == []


# --- (d) nothing refuses a body without the line --------------------------------------------


@pytest.mark.parametrize(
    "body",
    ["taken: s1 2026-11-14", "Tell: s1 hi", f"Verdict: cleared {SHA}", f"Report: {SHA} done"],
)
def test_a_body_without_the_line_reads_as_before(body):
    """REQ-050: brief #1289 answer 4 (the owner's own comments carry nothing)."""
    assert common.without_who(body) == body
    assert common.verdict_problem(body) is None
    assert session.plain(body) == body


def test_no_check_reads_the_who_line():
    """REQ-050: brief #1289 answer 4: only the posting helper and the take reader name it."""
    allowed = {"common.py", "session.py"}
    readers = sorted(
        p.name
        for p in SCRIPTS.glob("*.py")
        if p.name not in allowed
        and any(name in p.read_text(encoding="utf-8") for name in ("WHO_LINE", "without_who("))
    )
    assert readers == ["route.py"]  # its `Unreadable:` dedupe compares bodies without the line
