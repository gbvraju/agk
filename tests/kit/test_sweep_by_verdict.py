"""The sweep picks pull requests by their cleared verdict, never by label (brief #836 answer 2).

REQ-046, ADR-0383, amendment 148 (SPEC-0039 rule 2): a stale label hid a cleared head from the
sweep. Saved pull request lists and a recorded merge; no network, invented logins.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

from test_merge_cleared_verdict import comment
from test_merger_sweep import NOW, World, a_pull, clearing, sha_of, sweep

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import merge_cleared  # noqa: E402


class Routed:
    """The pull requests the router was re-run for."""

    def __init__(self, monkeypatch):
        self.numbers: list[int] = []
        monkeypatch.setattr(merge_cleared, "reroute", lambda root, repo, n: self.numbers.append(n))


def test_a_stale_fix_label_with_a_cleared_head_is_merged(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answers 2 and 6 (the label is never an input)."""
    world = World(monkeypatch, [a_pull(5, labels=("agk:fix",))], {5: clearing(5)})
    Routed(monkeypatch)
    lines = sweep(tmp_path, capsys)
    assert world.ran == [(5, sha_of(5))]
    assert "LABEL #5 agk:fix but cleared" in lines


def test_no_label_at_all_is_swept_too(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 2 (every open, non-draft pull request)."""
    world = World(monkeypatch, [a_pull(5, labels=())], {5: clearing(5)})
    Routed(monkeypatch)
    sweep(tmp_path, capsys)
    assert world.ran == [(5, sha_of(5))]


def test_a_ready_label_with_no_clearing_verdict_is_never_merged(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 6 (a pull request with no clearing verdict never merges)."""
    note = comment(f"Verdict: fix list {sha_of(5)}\n\n1. A finding.\n")
    world = World(monkeypatch, [a_pull(5), a_pull(6, day=2)], {5: [note]})
    routed = Routed(monkeypatch)
    lines = sweep(tmp_path, capsys)
    assert world.ran == []
    assert routed.numbers == []
    assert not any(line.startswith("LABEL") for line in lines)


def test_a_verdict_for_an_older_head_is_not_cleared(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 2 (the verdict must clear the current head)."""
    world = World(monkeypatch, [a_pull(5, labels=("agk:fix",))], {5: clearing(6)})
    routed = Routed(monkeypatch)
    sweep(tmp_path, capsys)
    assert world.ran == [] and routed.numbers == []


def test_a_draft_is_never_swept(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 2 (non-draft)."""
    world = World(monkeypatch, [a_pull(5, draft=True)], {5: clearing(5)})
    sweep(tmp_path, capsys)
    assert world.ran == []


def test_oldest_first_and_at_most_five_whatever_the_label(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 2 (oldest first, at most 5 a run)."""
    pulls = [a_pull(n, day=8 - n, labels=("agk:review",)) for n in range(1, 8)]
    world = World(monkeypatch, pulls, {n: clearing(n) for n in range(1, 8)})
    Routed(monkeypatch)
    sweep(tmp_path, capsys)
    assert [n for n, _ in world.ran] == [7, 6, 5, 4, 3]


def test_the_router_is_re_run_for_a_stale_label_left_unmerged(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 2 (`LABEL #<n> <label> but cleared`, and the router re-run)."""
    World(monkeypatch, [a_pull(5, labels=("agk:review",))], {5: clearing(5)}, merged=False)
    routed = Routed(monkeypatch)
    lines = sweep(tmp_path, capsys)
    assert "LABEL #5 agk:review but cleared" in lines
    assert routed.numbers == [5]


def test_a_merged_pull_request_needs_no_router_run(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 2 (a merge starts the router by its own `closed` event)."""
    World(monkeypatch, [a_pull(5, labels=("agk:fix",))], {5: clearing(5)})
    routed = Routed(monkeypatch)
    sweep(tmp_path, capsys)
    assert routed.numbers == []


def test_a_label_that_agrees_prints_no_line(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 2 (a state the router may give a cleared head is no conflict)."""
    pulls = [a_pull(5), a_pull(6, day=2, labels=("agk:ci-running",))]
    World(monkeypatch, pulls, {5: clearing(5), 6: clearing(6)}, merged=False)
    routed = Routed(monkeypatch)
    lines = sweep(tmp_path, capsys)
    assert not any(line.startswith("LABEL") for line in lines)
    assert routed.numbers == []


def test_a_router_that_cannot_run_ends_nothing(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 2 (the sweep goes on; every step of the job ends green)."""
    pulls = [a_pull(5, labels=("agk:fix",)), a_pull(6, day=2, labels=("agk:fix",))]
    world = World(monkeypatch, pulls, {5: clearing(5), 6: clearing(6)}, merged=False)

    def broken(repo, number, root, labels, dry):
        raise merge_cleared.CheckError("the facts cannot be read")

    import route

    monkeypatch.setattr(route, "route_one", broken)
    monkeypatch.setattr(route, "Labels", lambda repo: object())
    lines = sweep(tmp_path, capsys)
    assert [n for n, _ in world.ran] == [5, 6]
    assert "LABEL #5 router not re-run" in lines


def test_the_sweep_prints_minutes_from_cleared_to_merged(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 `Measured:` (the minutes for each pull request it merges)."""
    World(monkeypatch, [a_pull(5)], {5: clearing(5, 12)})
    assert "MERGED #5 12 min after cleared" in sweep(tmp_path, capsys)


def test_an_edited_verdict_counts_from_its_edit(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 1 and `Measured:` (an edit is the moment it cleared)."""
    note = clearing(5, 40)[0]
    edit = NOW - datetime.timedelta(minutes=3)
    note["updated_at"] = edit.strftime("%Y-%m-%dT%H:%M:%SZ")
    World(monkeypatch, [a_pull(5)], {5: [note]})
    assert "MERGED #5 3 min after cleared" in sweep(tmp_path, capsys)


def test_no_merged_line_for_a_held_head(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 `Measured:` (only for a pull request it merged)."""
    World(monkeypatch, [a_pull(5)], {5: clearing(5)}, merged=False)
    assert not any(line.startswith("MERGED") for line in sweep(tmp_path, capsys))
