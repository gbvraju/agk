"""conductor.py watch wakes when work is ready to start (brief #1151, ADR-0489; REQ-039).

When a poll of `watch` finds no new line, and at most once a minute, it reads the plan the way
`session.py plan` does and returns `START #<brief>[ build (<x>)] <kind>` for each `Assign` row
whose brief has no `Started: cb` comment and no `taken:` in the last 2 hours; a brief titled as the
red default branch comes first as `START #<brief> red`. A brief returned once is not returned again
for 10 minutes. The plan and the comments are stubbed; invented names, no network.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_pool_health import Clock
from test_session import REPO

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import conductor  # noqa: E402

NOW = datetime(2026, 11, 12, 23, 0, tzinfo=UTC)
RED = "The default branch is red"


def row(brief: int, kind: str = "build", title: str = "a brief", build: str | None = None) -> dict:
    found = {"session": "s1", "brief": brief, "title": title, "kind": kind}
    return found | ({"build": build} if build else {})


def said(cid: int, text: str, minutes: int) -> dict:
    moment = (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": cid, "user": {"login": "owner"}, "body": text, "created_at": moment}


@pytest.fixture
def plan(monkeypatch, tmp_path):
    """A stubbed plan: `rows` are its `assign` rows, `comments` each brief's comments."""

    class Plan:
        rows: list[dict] = []
        comments: dict[int, list] = {}
        builds = 0
        mark = tmp_path / "agk" / "starts"

    def build(root, record=False):
        Plan.builds += 1
        return {"start": [], "assign": [r | {"line": "Assign: x"} for r in Plan.rows]}

    def read(endpoint, what):
        number = int(endpoint.split("/issues/")[1].split("/")[0])
        return Plan.comments.get(number, [])

    monkeypatch.setattr(conductor.session_plan, "build", build)
    monkeypatch.setattr(conductor.session, "builder_start", lambda root: "assign")
    monkeypatch.setattr(conductor, "read", read)
    monkeypatch.setattr(conductor, "start_mark", lambda root: Plan.mark)
    return Plan


def starts(plan, minutes: float = 0) -> list[str]:
    return conductor.start_lines("root", REPO, NOW + timedelta(minutes=minutes))


def test_1151a_an_offered_brief_with_no_start_ends_the_watch(plan):
    """REQ-039: brief #1151 answer 1 and test (a)."""
    plan.rows = [row(21), row(22, "design", build="b")]
    assert starts(plan) == ["START #21 build", "START #22 build (b) design"]
    marks = json.loads(plan.mark.read_text(encoding="utf-8"))
    assert set(marks) == {"checked", "said"} and set(marks["said"]) == {"21", "22 (b)"}


def test_1151b_a_started_comment_in_the_last_2_hours_holds_the_brief(plan):
    """REQ-039: brief #1151 test (b); a `taken:` holds it too, an older start does not."""
    plan.rows = [row(21), row(22), row(23)]
    plan.comments = {
        21: [said(1, "Started: cb21 2026-11-12T22:10Z by the conductor (build)", 50)],
        22: [said(2, "taken: cb22 2026-11-12", 30)],
        23: [said(3, "Started: cb23 2026-11-12T20:00Z by the conductor (build)", 180)],
    }
    assert starts(plan) == ["START #23 build"]


def test_1151c_a_red_branch_brief_comes_first_with_red(plan):
    """REQ-039: brief #1151 answer 1 and test (c)."""
    plan.rows = [row(21), row(30, "mechanical", title=RED), row(22, "small")]
    assert starts(plan) == ["START #30 red", "START #21 build", "START #22 small"]


def test_1151d_a_returned_brief_returns_again_only_after_10_minutes(plan):
    """REQ-039: brief #1151 answer 1 and test (d)."""
    plan.rows = [row(21)]
    assert starts(plan) == ["START #21 build"]
    assert starts(plan, 2) == []
    assert starts(plan, 9) == []
    plan.rows = [row(21), row(22)]
    assert starts(plan, 10.5) == ["START #21 build", "START #22 build"]


def test_1151e_the_plan_is_read_at_most_once_a_minute(plan):
    """REQ-039: brief #1151 test (e)."""
    plan.rows = [row(21)]
    starts(plan)
    starts(plan, 0.5)
    assert plan.builds == 1
    starts(plan, 1.1)
    assert plan.builds == 2


def test_1151_no_plan_is_read_without_assign_or_without_a_checkout(plan, monkeypatch):
    """REQ-039: with `builder_start = "start"` the conductor starts nothing; no mark, no read."""
    plan.rows = [row(21)]
    monkeypatch.setattr(conductor.session, "builder_start", lambda root: "start")
    assert starts(plan) == [] and plan.builds == 0
    monkeypatch.setattr(conductor.session, "builder_start", lambda root: "assign")
    monkeypatch.setattr(conductor, "start_mark", lambda root: None)
    assert starts(plan) == [] and plan.builds == 0


def test_1151_a_plan_that_cannot_be_read_says_nothing(plan, monkeypatch):
    """REQ-039: an unread plan returns no `START` line and is tried again a minute later."""

    def broken(root, record=False):
        plan.builds += 1
        raise conductor.CheckError("rule 3: the open briefs cannot be read")

    monkeypatch.setattr(conductor.session_plan, "build", broken)
    assert starts(plan) == [] and starts(plan, 0.5) == [] and plan.builds == 1


def test_1151_a_start_line_ends_the_bounded_watch_after_the_held_check(monkeypatch, capsys):
    """REQ-039: the polling watch returns the start lines when nothing else woke it."""
    clock = Clock()
    seen: list[float] = []

    def start(root, repo, now=None):
        seen.append(clock.spent)
        return ["START #30 red"]

    monkeypatch.setattr(conductor, "time", clock)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "flow_int", lambda *a: 60)
    monkeypatch.setattr(conductor, "spec_approvers", lambda root: [])
    monkeypatch.setattr(conductor, "new_lines", lambda repo, since, approvers=(): [])
    monkeypatch.setattr(conductor, "renew_lease", lambda root: 0)
    monkeypatch.setattr(conductor, "green_lines", lambda root, repo, since: [])
    monkeypatch.setattr(conductor, "stall_report", lambda root, repo: [])
    monkeypatch.setattr(conductor, "sweep_late", lambda root, repo: [])
    monkeypatch.setattr(conductor, "held_lines", lambda root, repo: [])
    monkeypatch.setattr(conductor, "start_lines", start)
    assert conductor.watch("root", datetime.now(UTC) - timedelta(minutes=1), False) == 0
    assert capsys.readouterr().out.strip() == "START #30 red"
    assert seen and seen[0] <= 60


def test_1151_a_held_line_wins_over_a_start_line(monkeypatch, capsys):
    """REQ-039: the start check runs only when the poll found no other line."""
    called: list[int] = []
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "flow_int", lambda *a: 60)
    monkeypatch.setattr(conductor, "spec_approvers", lambda root: [])
    monkeypatch.setattr(conductor, "new_lines", lambda repo, since, approvers=(): [])
    monkeypatch.setattr(conductor, "renew_lease", lambda root: 0)
    monkeypatch.setattr(conductor, "green_lines", lambda root, repo, since: [])
    monkeypatch.setattr(conductor, "sweep_late", lambda root, repo: [])
    monkeypatch.setattr(conductor, "held_lines", lambda root, repo: ["HELD VERDICT #7"])
    monkeypatch.setattr(conductor, "start_lines", lambda *a: called.append(1) or ["START #1 x"])
    assert conductor.watch("root", datetime.now(UTC), True) == 0
    assert capsys.readouterr().out.strip() == "HELD VERDICT #7" and not called
