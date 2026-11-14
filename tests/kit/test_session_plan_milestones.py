"""session.py plan: builders take ready work milestone by milestone, most-unblocking first.

Brief #1232, ADR-0523; REQ-050. The earliest milestone (its GitHub milestone, by `due_on` and then
number; a brief without one last) fills the free slots first, and a later milestone only when the
earlier ones have no ready, non-overlapping brief; within a milestone the brief whose dependants
carry the most remaining hours starts first, then priority, then the smaller `Expected:`, then
number. `[plan] active_milestones` keeps every other milestone out. The plan names each start's
milestone and unblocked hours, and each free slot it cannot fill. Invented plans only."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from test_session import ISSUES, REPO, Stub, iso, issue, listing, posts, session, state
from test_session_flow import PULLS, brief, pr

ROOT = Path(__file__).resolve().parents[2]

M1 = {"number": 11, "title": "M1 first demo", "due_on": "2026-12-01T00:00:00Z"}
M2 = {"number": 12, "title": "M2 second demo", "due_on": "2026-12-15T00:00:00Z"}
M3 = {"number": 9, "title": "M3 later", "due_on": None}


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


def toml(proj, text: str) -> None:
    proj.write("agk.toml", text)


def at(number: int, body: str, milestone: dict | None) -> dict:
    return {**issue(number, body), "milestone": milestone}


def free(stub: Stub, *numbers: int) -> None:
    for n in numbers:
        stub.serve(f"{ISSUES}/{n}/comments", [])


def after(body: str, *numbers: int) -> str:
    return body + "".join(f"Depends-on: #{n}\n" for n in numbers)


def expected(body: str, low: int, high: int) -> str:
    return body + f"Expected: {low}-{high} hours\n"


def sized(body: str, size: str) -> str:
    return body.replace("Size: M\n", f"Size: {size}\n")


def plan(proj, stub, *extra: str):
    return session(proj, stub, "plan", *extra)


def lines(proj, stub) -> list[str]:
    out = plan(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    assert posts(stub) == [] and all(c[0] == "GET" for c in stub.calls())
    return out.stdout.splitlines()


def data(proj, stub) -> dict:
    out = plan(proj, stub, "--json")
    assert out.returncode == 0, out.stdout + out.stderr
    return json.loads(out.stdout)


# --- answer 1: the earliest milestone first ---------------------------------------------------


def test_an_earlier_milestones_ready_brief_beats_a_later_one(proj, stub):
    toml(proj, "[flow]\nmax_builders = 1\n")
    listing(stub, [at(5, brief("a/"), M2), at(6, brief("b/"), M1)])
    free(stub, 5, 6)
    got = lines(proj, stub)
    assert got[0] == "Start 1: builder-a takes #6."
    assert "#6 M1 first demo: unblocks 0 h." in got


def test_a_brief_without_a_milestone_and_a_later_due_date_come_after(proj, stub):
    listing(
        stub,
        [
            at(4, brief("a/"), None),
            at(5, brief("b/"), M3),
            at(6, brief("c/"), M2),
            at(7, brief("d/"), M1),
        ],
    )
    free(stub, 4, 5, 6, 7)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [7, 6, 5]  # due_on, then none due, then none
    assert got["milestones"]["starts"] == [
        {"brief": 7, "milestone": "M1 first demo", "unblocks": 0},
        {"brief": 6, "milestone": "M2 second demo", "unblocks": 0},
        {"brief": 5, "milestone": "M3 later", "unblocks": 0},
    ]


def test_with_none_ready_in_the_earliest_milestone_the_next_fills_the_slot(proj, stub):
    listing(stub, [at(5, brief("b/**"), M2), at(6, brief("a/**"), M1)])
    stub.serve(PULLS, [{**pr(20, 1), "created_at": iso(-timedelta(days=1))}])
    stub.serve(f"{PULLS}/20/files", [{"filename": "a/x.py", "status": "modified"}])
    free(stub, 5, 6)
    got = lines(proj, stub)
    assert got[0] == "Start 1: builder-a takes #5."
    assert "#5 M2 second demo: unblocks 0 h." in got
    idle = (
        "idle: no ready brief in M1 first demo, M2 second demo; "
        "first wait: #6 waits for pull request #20 (it changes a/x.py)."
    )
    assert got.count(idle) == 1  # three builders, one running, one started: one slot is idle


def test_an_earlier_milestones_brief_wins_an_overlap_with_a_later_one(proj, stub):
    listing(stub, [at(5, brief("a/b", priority=1), M2), at(6, brief("a/"), M1)])
    free(stub, 5, 6)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [6]
    assert got["waits"] == [{"brief": 5, "waits_for": 6, "why": "both touch a/b"}]


# --- answer 2: the brief that unblocks the most remaining hours first ------------------------


def test_a_brief_that_unblocks_more_hours_starts_first(proj, stub):
    toml(proj, "[flow]\nmax_builders = 1\n")
    listing(
        stub,
        [
            at(5, brief("a/", priority=1), M1),
            at(6, brief("b/"), M1),
            at(7, expected(after(brief("c/"), 6), 4, 8), M1),  # mid point 6 hours
            at(8, sized(after(brief("d/"), 7), "S"), M2),  # no Expected: S counts 3 hours
        ],
    )
    free(stub, 5, 6, 7, 8)
    state(stub, 6, "open")
    state(stub, 7, "open")
    got = lines(proj, stub)
    assert got[0] == "Start 1: builder-a takes #6."  # 9 hours wait on it, further down too
    assert "#6 M1 first demo: unblocks 9 h." in got


def test_within_a_milestone_priority_then_the_smaller_expected_then_number(proj, stub):
    listing(
        stub,
        [
            at(5, expected(brief("a/"), 6, 10), M1),
            at(6, expected(brief("b/"), 1, 3), M1),
            at(7, sized(brief("c/", priority=3), "S"), M1),
            at(8, sized(brief("d/"), "S"), M1),
        ],
    )
    free(stub, 5, 6, 7, 8)
    toml(proj, "[flow]\nmax_builders = 4\n")
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [6, 8, 5, 7]  # 2 h, S 3 h, 8 h; priority 3 last


def test_a_dependant_is_counted_once_and_a_cycle_ends(proj, stub):
    toml(proj, "[flow]\nmax_builders = 1\n")
    listing(
        stub,
        [
            at(5, brief("a/"), M1),
            at(6, expected(after(brief("b/"), 5, 7), 2, 2), M1),
            at(7, expected(after(brief("c/"), 5, 6), 4, 4), M1),
        ],
    )
    free(stub, 5, 6, 7)
    for n in (5, 6, 7):
        state(stub, n, "open")
    got = data(proj, stub)
    assert got["milestones"]["starts"] == [
        {"brief": 5, "milestone": "M1 first demo", "unblocks": 6}
    ]


# --- answer 3: `[plan] active_milestones` ----------------------------------------------------


def test_active_milestones_keeps_a_later_milestone_out(proj, stub):
    toml(proj, '[plan]\nactive_milestones = ["M2 second demo"]\n')
    listing(stub, [at(5, brief("a/"), M1), at(6, brief("b/"), M2), at(7, brief("c/"), None)])
    free(stub, 5, 6, 7)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [6]
    why = "not in an active milestone (setting: [plan] active_milestones)"
    assert {"brief": 5, "why": why} in got["skipped"]
    assert {"brief": 7, "why": why} in got["skipped"]


def test_without_active_milestones_every_milestone_is_active(proj, stub):
    listing(stub, [at(5, brief("a/"), M1), at(6, brief("b/"), M2)])
    free(stub, 5, 6)
    assert [s["brief"] for s in data(proj, stub)["start"]] == [5, 6]


@pytest.mark.parametrize("value", ['"M1"', "[1]", '[""]'])
def test_a_wrong_active_milestones_is_refused_naming_the_setting(proj, stub, value):
    toml(proj, f"[plan]\nactive_milestones = {value}\n")
    listing(stub, [at(5, brief("a/"), M1)])
    free(stub, 5)
    out = plan(proj, stub)
    assert out.returncode != 0
    assert "setting: [plan] active_milestones" in out.stdout + out.stderr
    assert "M1" not in out.stdout + out.stderr


# --- answer 4: the idle line --------------------------------------------------------------------


def test_each_slot_it_cannot_fill_says_idle_with_the_milestones(proj, stub):
    listing(stub, [at(5, brief("a/"), M1)])
    free(stub, 5)
    got = lines(proj, stub)
    assert got[0] == "Start 1: builder-a takes #5."
    assert got.count("idle: no ready brief in M1 first demo.") == 2  # three slots, one start


def test_no_open_brief_says_idle_in_any_milestone(proj, stub):
    toml(proj, '[flow]\nmax_builders = 1\n[plan]\nactive_milestones = ["M1 first demo"]\n')
    listing(stub, [])
    got = lines(proj, stub)
    assert got[0] == "Start 0: no brief is ready."
    assert got.count("idle: no ready brief in any milestone.") == 1


def test_a_merge_hold_is_no_idle_slot(proj, stub):
    """The merge queue holds every start on purpose: no slot is reported idle."""
    from test_session_plan import history, ready_prs, with_history

    listing(stub, [at(5, brief("a/"), M1)])
    free(stub, 5)
    with_history(stub, history(30, 30.2, 50, 50.1), ready_prs(20, 21, 22))
    toml(proj, "[flow]\nmax_builders = 9\n")
    got = data(proj, stub)
    assert got["merge"]["hold"] is True and got["start"] == []
    assert got["milestones"]["idle"] == []


def test_with_no_milestone_and_no_setting_the_plan_prints_as_before(proj, stub):
    """Q-1232-2: a project that uses no milestone sees no new line and no new key."""
    listing(stub, [at(5, brief("a/"), None), issue(6, brief("b/"))])
    free(stub, 5, 6)
    got = lines(proj, stub)
    assert not [x for x in got if "unblocks" in x or x.startswith("idle:")]
    assert "milestones" not in data(proj, stub)


# --- the guide -------------------------------------------------------------------------------


def test_the_guide_names_the_milestone_order_and_the_setting():
    text = (ROOT / "docs/guides/getting-started.md").read_text(encoding="utf-8")
    assert "[plan] active_milestones" in text
    assert "idle: no ready brief in" in text
