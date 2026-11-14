"""session.py plan reads only what a pass needs, milestone by milestone, and counts its reads.

Brief #1251 build (a), ADR-0529; REQ-050. The plan judges the open briefs from their listing alone
(stale, parked, shape, a `Depends-on` brief that no open listing holds is closed, with no GET per
dependency), then reads the comments of the briefs that pass, in the milestone order of ADR-0523,
only until the free slots are filled, besides the briefs that carry the take label `agk:taken` or
that an open pull request names. It reads the open pull requests and the closed ones updated in its
window, never every pull request ever (`state=all`). It ends with `reads: <n> calls (<m> from
cache), <s> s`, and `--json` carries the same. A recorded GitHub double and invented data only."""

from __future__ import annotations

import json
import re
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from test_session import ISSUES, REPO, Stub, comment, iso, issue, posts, session
from test_session_flow import DAY, PULLS, brief, merged, pr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

MILESTONES = [
    {"number": 20 + k, "title": f"M{k + 1} demo", "due_on": f"2026-12-{k + 1:02d}T00:00:00Z"}
    for k in range(7)
]
READS = re.compile(r"reads: (\d+) calls \((\d+) from cache\), (\d+(?:\.\d+)?) s")


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def at(number: int, body: str, milestone: dict | None, labels: tuple[str, ...] = ()) -> dict:
    found = {**issue(number, body), "milestone": milestone}
    return found | {"labels": [{"name": n} for n in labels]}


def pages_of(stub: Stub, issues: list[dict]) -> None:
    """The open-briefs listing served 100 at a time, as GitHub pages it."""
    chunks = [issues[i : i + 100] for i in range(0, len(issues), 100)]
    if not chunks or len(chunks[-1]) == 100:
        chunks.append([])
    for n, chunk in enumerate(chunks, start=1):
        stub.serve(ISSUES, chunk, nth=n)
    stub.serve(PULLS, [])


def big_plan(count: int = 600) -> list[dict]:
    """`count` briefs spread over seven milestones, latest numbers in the earliest milestone, each
    touching its own folder so that no two overlap."""
    out = []
    for k in range(count):
        number = 1000 + k
        milestone = MILESTONES[6 - (k * 7 // count)]
        out.append(at(number, brief(f"area{number}/**"), milestone))
    return out


def comment_reads(stub: Stub) -> list[str]:
    found = (c[1].split("?")[0] for c in stub.calls())
    return [e for e in found if re.search(r"/issues/\d+/comments$", e)]


def plan(proj, stub, *extra: str):
    out = session(proj, stub, "plan", *extra)
    assert out.returncode == 0, out.stdout + out.stderr
    assert posts(stub) == [] and all(c[0] == "GET" for c in stub.calls())
    return out


# --- answer 1: read in milestone order and stop early ------------------------------------------


def test_six_hundred_briefs_with_two_free_slots_cost_at_most_twenty_calls(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    briefs = big_plan()
    pages_of(stub, briefs)
    earliest = sorted(b["number"] for b in briefs if b["milestone"] is MILESTONES[0])
    for number in earliest[:4]:
        stub.serve(f"{ISSUES}/{number}/comments", [])
    out = plan(proj, stub, "--json")
    data = json.loads(out.stdout)
    assert [s["brief"] for s in data["start"]] == earliest[:2]  # today's full read starts these
    assert len(stub.calls()) <= 20, len(stub.calls())
    assert len(comment_reads(stub)) == 2  # only the briefs it starts, none of the other 598
    assert data["reads"]["calls"] == len(stub.calls())


def test_a_brief_whose_comments_hold_it_makes_the_walk_read_one_more(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 1\n")
    pages_of(stub, [at(5, brief("a/**"), MILESTONES[0]), at(6, brief("b/**"), MILESTONES[0])])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "boss", f"taken: other {DAY}")])
    stub.serve(f"{ISSUES}/6/comments", [])
    out = plan(proj, stub, "--json")
    data = json.loads(out.stdout)
    assert data["start"] == [] or [s["brief"] for s in data["start"]] == [6]
    assert sorted(comment_reads(stub)) == [f"{ISSUES}/5/comments", f"{ISSUES}/6/comments"]


def test_a_later_milestone_is_read_only_while_slots_are_free(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(
        stub,
        [
            at(5, brief("a/**"), MILESTONES[0]),
            at(6, brief("b/**"), MILESTONES[1]),
            at(7, brief("c/**"), MILESTONES[2]),
        ],
    )
    for n in (5, 6, 7):
        stub.serve(f"{ISSUES}/{n}/comments", [])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [s["brief"] for s in data["start"]] == [5, 6]
    assert f"{ISSUES}/7/comments" not in comment_reads(stub)


# --- answer 1: a dependency judged from the listing --------------------------------------------


def test_a_closed_dependency_is_judged_without_a_get(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(stub, [at(6, brief("a/**") + "Depends-on: #3\n", MILESTONES[0])])
    stub.serve(f"{ISSUES}/6/comments", [])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [s["brief"] for s in data["start"]] == [6]
    assert not any(c[1] == f"{ISSUES}/3" for c in stub.calls())


def test_an_open_dependency_in_the_listing_waits_without_a_get(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(
        stub,
        [
            at(5, brief("a/**"), MILESTONES[1]),
            at(6, brief("b/**") + "Depends-on: #5\n", MILESTONES[0]),
        ],
    )
    stub.serve(f"{ISSUES}/5/comments", [])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [s["brief"] for s in data["start"]] == [5]
    assert {"brief": 6, "why": "depends on #5, which is open"} in data["skipped"]
    assert not any(c[1] == f"{ISSUES}/5" for c in stub.calls())
    assert f"{ISSUES}/6/comments" not in comment_reads(stub)


# --- answer 2: the take label ------------------------------------------------------------------


def test_a_take_shown_by_the_label_holds_its_brief_and_a_slot(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(
        stub,
        [
            at(5, brief("a/**"), MILESTONES[0]),
            at(6, brief("b/**"), MILESTONES[0]),
            at(9, brief("c/**"), MILESTONES[6], labels=("agk:taken",)),
        ],
    )
    for n in (5, 6):
        stub.serve(f"{ISSUES}/{n}/comments", [])
    stub.serve(f"{ISSUES}/9/comments", [comment(1, "someone", f"taken: builder-x {DAY}")])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [s["brief"] for s in data["start"]] == [5]  # builder-x holds the other slot
    assert data["running"] == [{"session": "builder-x", "brief": 9, "author": "someone"}]
    assert f"{ISSUES}/6/comments" not in comment_reads(stub)


def test_claim_adds_the_take_label(proj, stub):
    """REQ-050"""
    stub.serve(f"{ISSUES}/5", {"number": 5, "state": "open", "body": brief("a/**"), "labels": []})
    stub.serve(ISSUES, [issue(5, brief("a/**"))])
    stub.serve(PULLS, [])
    stub.serve(f"{ISSUES}/5/comments", [], nth=1)
    stub.serve(f"{ISSUES}/5/comments", [comment(9, "me", f"taken: s-me {DAY}")], nth=2)
    out = session(proj, stub, "claim", "--session", "s-me", "--brief", "5")
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.splitlines()[-1] == "claimed #5"
    sent = posts(stub)
    assert sent[0][1] == f"{ISSUES}/5/comments"
    assert sent[-1][1] == f"{ISSUES}/5/labels"
    assert "labels[]=agk:taken" in sent[-1][2]


# --- answer 4: the pull requests ---------------------------------------------------------------


def test_the_plan_reads_open_and_recently_closed_pull_requests_never_all(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(stub, [at(5, brief("a/**"), MILESTONES[0])])
    stub.serve(PULLS, [merged(30, 4, timedelta(hours=1)) | {"updated_at": iso()}])
    stub.serve(f"{ISSUES}/5/comments", [])
    plan(proj, stub)
    pulls = [c[1] for c in stub.calls() if c[1].startswith(PULLS + "?")]
    assert pulls and not any("state=all" in p for p in pulls)
    assert any("state=open" in p for p in pulls)
    assert any("state=closed" in p and "sort=updated" in p for p in pulls)


def test_a_build_merged_before_the_window_is_found_on_the_briefs_timeline(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    body = brief("a/**") + "Builds: (a) one; (b) two\n"
    pages_of(stub, [at(5, body, MILESTONES[0])])
    old = {**merged(30, 5, timedelta(days=40)), "title": "brief #5 build (a)"}
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "s", "taken: s-old 2026-10-01 build (a)")])
    event = {"number": 30, "title": old["title"], "state": "closed", "body": old["body"]}
    event["pull_request"] = {"merged_at": old["merged_at"]}
    stub.serve(f"{ISSUES}/5/timeline", [{"event": "cross-referenced", "source": {"issue": event}}])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [(s["brief"], s.get("build")) for s in data["start"]] == [(5, "b")]


# --- answer 5: the cost is printed -------------------------------------------------------------


def test_the_plan_prints_its_reads_and_the_data_carries_them(proj, stub):
    """REQ-050"""
    stub.serve(ISSUES, [at(5, brief("a/**"), MILESTONES[0])])
    stub.serve(PULLS, [])
    stub.serve(f"{ISSUES}/5/comments", [])
    out = plan(proj, stub)
    found = READS.fullmatch(out.stdout.rstrip().splitlines()[-1])
    assert found and int(found.group(1)) == len(stub.calls()) and found.group(2) == "0"
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert set(data["reads"]) == {"calls", "cached", "seconds"}
    assert data["reads"]["cached"] == 0


def test_the_checklist_reports_the_last_plans_reads(tmp_path):
    """REQ-050"""
    import checklist

    saved = tmp_path / "agk-plan-reads.json"
    saved.write_text(json.dumps({"calls": 12, "cached": 0, "seconds": 1.5}), encoding="utf-8")
    assert checklist.plan_reads(saved) == "plan reads 12 calls (0 from cache), 1.5 s"
    assert checklist.plan_reads(tmp_path / "missing.json") is None
