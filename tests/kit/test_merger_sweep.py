"""merge_cleared.py --sweep and the schedule of the merger workflow.

Brief #797 answers 3, 5 and 6, ADR-0373, amendment 144, REQ-046 (SPEC-0039 rule 2): a cleared pull
request whose own event was lost is still merged, because a scheduled run lists the open pull
requests labelled `agk:ready`, oldest first, and runs the one guarded merge on at most five
cleared heads. Saved answers and a recorded merge only; no network, invented logins.
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

import pytest
from test_merge_cleared_verdict import ON, comment, repo, toml

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import merge_cleared  # noqa: E402

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "merger.yml"
NOW = datetime.datetime(2026, 11, 4, 11, 0, tzinfo=datetime.UTC)
RECORD = {"number": 41, "title": "Auto merge record", "labels": [{"name": "agk-auto-merge"}]}
LOCAL_RECORD = {"number": 42, "title": "Local mode since 2026-11-04", "labels": []}


def sha_of(number: int) -> str:
    return f"{number:040x}"


def a_pull(number: int, day: int = 1, labels=("agk:ready",), draft=False, state="open") -> dict:
    return {
        "number": number,
        "state": state,
        "draft": draft,
        "created_at": f"2026-11-{day:02d}T10:00:00Z",
        "head": {"sha": sha_of(number)},
        "labels": [{"name": name} for name in labels],
    }


def clearing(number: int, minutes_ago: int = 5) -> list[dict]:
    at = NOW - datetime.timedelta(minutes=minutes_ago)
    note = comment(f"Verdict: cleared {sha_of(number)}\n")
    return [{**note, "created_at": at.strftime("%Y-%m-%dT%H:%M:%SZ")}]


class World:
    """The saved answers of one sweep and the guarded runs it made."""

    def __init__(self, monkeypatch, pulls, comments, issues=None, merged=True, line=None):
        self.ran: list[tuple[int, str]] = []
        self.reads: list[str] = []
        self.answer = line

        def pages(endpoint, what, key=None):
            self.reads.append(endpoint)
            return pulls if "/pulls" in endpoint else ([RECORD] if issues is None else issues)

        def guarded(root, number, sha):
            self.ran.append((number, sha))
            prefix = f"merge-cleared #{number} {sha[:12]}:"
            if self.answer is not None:
                return self.answer.format(prefix=prefix), merge_cleared.EXIT_HELD
            word = f"merged {'ab' * 6}" if merged else "held: hold label (rule 5)"
            return f"{prefix} {word}", merge_cleared.EXIT_CLEARED

        monkeypatch.setattr(merge_cleared, "read_pages", pages)
        monkeypatch.setattr(merge_cleared, "read_comments", lambda r, n: comments.get(n, []))
        monkeypatch.setattr(merge_cleared, "guarded", guarded)
        monkeypatch.setattr(merge_cleared, "clock", lambda: NOW)
        monkeypatch.setattr(merge_cleared, "repo_of", lambda root: "example-owner/example-repo")


def sweep(tmp_path, capsys, main: str = toml(ON)) -> list[str]:
    root = repo(tmp_path, main, origin="")
    assert merge_cleared.main(["--sweep"], root) == 0
    return capsys.readouterr().out.splitlines()


def test_the_sweep_takes_open_ready_pull_requests_oldest_first(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #797 answer 3 (open, not a draft, labelled `agk:ready`, oldest first)."""
    pulls = [
        a_pull(5, day=3),
        a_pull(6, day=1),
        a_pull(7, day=2, draft=True),
        a_pull(8, day=2, labels=("agk:fix",)),
    ]
    world = World(monkeypatch, pulls, {5: clearing(5), 6: clearing(6), 7: clearing(7)})
    lines = sweep(tmp_path, capsys)
    assert world.ran == [(6, sha_of(6)), (5, sha_of(5))]
    assert len(lines) == 2  # one line per pull request


def test_a_head_that_is_not_cleared_gets_a_line_and_no_merge(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #797 answer 3 (only a cleared head runs the guarded merge)."""
    note = comment(f"Verdict: fix list {sha_of(5)}\n\n1. a finding (rule: none)\n")
    world = World(monkeypatch, [a_pull(5)], {5: [note]})
    lines = sweep(tmp_path, capsys)
    assert world.ran == []
    assert len(lines) == 1 and "not cleared" in lines[0]
    assert "UNMERGED" not in lines[0]


def test_at_most_five_guarded_merges_a_run(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #797 answer 3 (at most 5 a run; the rest wait for the next run)."""
    pulls = [a_pull(n, day=n) for n in range(1, 8)]
    world = World(monkeypatch, pulls, {n: clearing(n) for n in range(1, 8)})
    lines = sweep(tmp_path, capsys)
    assert [n for n, _ in world.ran] == [1, 2, 3, 4, 5]
    assert len(lines) == 7


def test_a_cleared_head_past_the_limit_is_reported_when_old(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #797 answers 3 and 5 (a head the limit left out is not silent)."""
    pulls = [a_pull(n, day=n) for n in range(1, 7)]
    world = World(monkeypatch, pulls, {n: clearing(n, 30) for n in range(1, 7)})
    lines = sweep(tmp_path, capsys)
    assert len(world.ran) == 5
    assert lines[-1].startswith("UNMERGED #6 cleared 30 min ")


@pytest.mark.parametrize(("minutes", "reported"), [(20, False), (21, True)])
def test_unmerged_is_printed_only_after_twenty_minutes(
    tmp_path, monkeypatch, capsys, minutes, reported
):
    """REQ-046: brief #797 answer 5 (older than 20 minutes, the reason, never a value)."""
    World(monkeypatch, [a_pull(5)], {5: clearing(5, minutes)}, merged=False)
    lines = sweep(tmp_path, capsys)
    found = [line for line in lines if line.startswith("UNMERGED")]
    assert found == ([f"UNMERGED #5 cleared {minutes} min held: hold label (rule 5)"] * reported)


def test_a_merged_head_is_never_reported_unmerged(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #797 answer 5 (only one it could not merge)."""
    World(monkeypatch, [a_pull(5)], {5: clearing(5, 90)})
    assert not any(line.startswith("UNMERGED") for line in sweep(tmp_path, capsys))


def test_a_red_default_branch_ends_the_sweep(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #797 answer 3 (the guarded merge's stop stops the sweep too)."""
    line = "merge-cleared: stopped: default branch red after #1"
    pulls = [a_pull(1, day=1), a_pull(2, day=2)]
    world = World(monkeypatch, pulls, {1: clearing(1), 2: clearing(2)}, line=line)
    assert sweep(tmp_path, capsys) == [line]
    assert [n for n, _ in world.ran] == [1]


@pytest.mark.parametrize(
    "main",
    [
        toml(""),
        'forge = "files"\n' + toml(ON),
    ],
    ids=["auto-merge-off", "personal"],
)
def test_no_auto_merge_or_personal_mode_reads_and_merges_nothing(
    tmp_path, monkeypatch, capsys, main
):
    """REQ-046: brief #797 answer 6 (no sweep without `[flow] auto_merge = true`)."""
    world = World(monkeypatch, [a_pull(5)], {5: clearing(5, 90)})
    root = repo(tmp_path, main, origin="")
    assert merge_cleared.main(["--sweep"], root) == 0
    assert world.ran == [] and world.reads == []
    assert "nothing to do" in capsys.readouterr().err


def test_paused_reads_and_merges_nothing(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #797 answer 3 (a pause holds the sweep; session rule 33)."""
    world = World(monkeypatch, [a_pull(5)], {5: clearing(5, 90)})
    root = repo(tmp_path, "paused = true\n" + toml(ON), origin="")
    assert merge_cleared.main(["--sweep"], root) == 0
    assert world.ran == [] and world.reads == []


@pytest.mark.parametrize("how", ["setting", "record issue"])
def test_local_mode_reports_and_merges_nothing(tmp_path, monkeypatch, capsys, how):
    """REQ-046: brief #797 answers 5 and 6 (the report holds in local mode, the merge does not)."""
    issues = [RECORD, LOCAL_RECORD] if how == "record issue" else [RECORD]
    world = World(monkeypatch, [a_pull(5)], {5: clearing(5, 90)}, issues=issues)
    main = toml(ON, local=how == "setting")
    lines = sweep(tmp_path, capsys, main)
    assert world.ran == []
    assert lines[-1].startswith("UNMERGED #5 cleared 90 min local mode")


@pytest.mark.parametrize(
    ("main", "word"),
    [
        (toml(ON), "on"),
        (toml(""), "off"),
        (toml(ON, local=True), "off"),
        ('forge = "files"\n' + toml(ON), "off"),
    ],
    ids=["github", "auto-merge-off", "local", "personal"],
)
def test_the_gate_says_whether_this_project_sweeps(tmp_path, capsys, main, word):
    """REQ-046: brief #797 answer 6 (GitHub mode with auto-merge alone gets the sweep job)."""
    root = repo(tmp_path, main, origin="")
    assert merge_cleared.main(["--sweep-gate"], root) == 0
    assert capsys.readouterr().out.strip() == word


# --- the workflow ----------------------------------------------------------------------------


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def job(name: str) -> str:
    found = re.search(rf"\n  {name}:\n(.*?)(?=\n  [a-z][a-z_-]*:\n|\Z)", text(), re.S)
    assert found, name
    return found.group(1)


def test_the_schedule_runs_every_fifteen_minutes_and_by_hand():
    """REQ-046: brief #797 answer 3 (`schedule` every 15 minutes and `workflow_dispatch`)."""
    head = text().split("\njobs:", 1)[0]
    assert re.search(r"\n  schedule:\n    - cron: \"\*/15 \* \* \* \*\"\n", head)
    assert re.search(r"\n  workflow_dispatch:\n", head)


def test_the_event_job_is_unchanged_by_the_sweep():
    """REQ-046: brief #797 answer 3 (event runs are unchanged)."""
    event = job("merger")
    assert "schedule" not in event and "workflow_dispatch" not in event
    assert "--sweep" not in event and "needs:" not in event


def test_the_gate_holds_no_secret_and_starts_only_on_the_schedule():
    """REQ-046: brief #797 answer 6 (a project without auto-merge opens no `merge` environment)."""
    gate = job("sweep-gate")
    assert "secrets." not in gate and "environment:" not in gate
    assert "github.event_name == 'schedule'" in gate
    assert "github.event_name == 'workflow_dispatch'" in gate
    assert "scripts/agk/merge_cleared.py --sweep-gate" in gate


def test_the_sweep_job_runs_only_the_guarded_sweep_from_the_default_branch():
    """REQ-046: brief #797 answer 3 (the one command, under the secret of `merge`)."""
    body = job("sweep")
    assert re.search(r"^    needs: sweep-gate$", body, re.M)
    assert "needs.sweep-gate.outputs.sweep == 'on'" in body
    assert re.search(r"^    environment: merge$", body, re.M)
    assert "ref: ${{ github.event.repository.default_branch }}" in body
    assert set(re.findall(r"secrets\.\w+", body)) == {"secrets.AGK_MERGE_TOKEN"}
    assert 'python3 scripts/agk/merge_cleared.py --sweep || echo "merger: ' in body


def test_a_sweep_never_cancels_and_never_shares_a_group_with_a_pull_request():
    """REQ-046: brief #797 answer 3 (one sweep at a time; a run that may be merging is kept)."""
    assert "'sweep'" in text().split("\njobs:", 1)[0]
    assert "cancel-in-progress: false" in text()
