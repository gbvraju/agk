"""Every finished check sweeps; the conductor reports a late sweep (brief #836 answers 3 to 5).

REQ-046, ADR-0383, amendment 148 (SPEC-0039 rule 2): GitHub drops scheduled runs under load, so the
schedule cannot be the only sweep. The workflow file as text and saved GitHub answers; no network.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from test_conductor_commands import (  # noqa: F401
    REPO,
    SHA,
    ago,
    comment,
    pr,
    proj,
    run,
    serve_pr,
    stub,
)
from test_merge_cleared_merger import run_event
from test_merger_sweep import World, a_pull, clearing, sha_of, sweep

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "merger.yml"
RUNS = f"repos/{REPO}/actions/workflows/merger.yml/runs"
ON = '[flow]\nconductor_poll_seconds = 1\nauto_merge = true\nauto_merge_method = "squash"\n'


def job(name: str) -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    found = re.search(rf"\n  {name}:\n(.*?)(?=\n  [a-z][a-z_-]*:\n|\Z)", text, re.S)
    assert found, name
    return found.group(1)


def a_run(event: str, minutes: int, conclusion: str = "success") -> dict:
    return {"event": event, "conclusion": conclusion, "updated_at": ago(minutes)}


def serve_runs(stub, *runs) -> None:  # noqa: F811
    stub.serve(RUNS, {"workflow_runs": list(runs)})


def turn_on(proj) -> None:  # noqa: F811
    """`auto_merge` on, committed so that origin/main reads it."""
    proj.write("agk.toml", ON)
    proj.git("add", "agk.toml")
    proj.git("commit", "-q", "-m", "auto merge on")
    proj.git("update-ref", "refs/remotes/origin/main", "HEAD")


def watch_lines(proj, stub) -> list[str]:  # noqa: F811
    out = run(proj, stub, "watch", "--once")
    assert out.returncode == 0, out.stdout + out.stderr
    assert all(c[0] == "GET" for c in stub.calls())
    return out.stdout.splitlines()


def cleared(minutes: int = 50) -> dict:
    return comment(5, "boss", f"Verdict: cleared {SHA}", ago(minutes))


# --- answer 3: the workflow -----------------------------------------------------------------------


def test_the_gate_also_starts_on_a_finished_check():
    """REQ-046: brief #836 answer 3 (`workflow_run` of `governance` or `proof`)."""
    gate = job("sweep-gate")
    assert "github.event_name == 'workflow_run'" in gate
    assert "github.event_name == 'schedule'" in gate
    assert "github.event_name == 'workflow_dispatch'" in gate


def test_the_sweep_runs_after_the_event_job_whatever_it_did():
    """REQ-046: brief #836 answer 3 (after the event job, which is often skipped or may fail)."""
    gate = job("sweep-gate")
    assert re.search(r"^    needs: merger$", gate, re.M)
    assert "!cancelled()" in gate


def test_the_sweep_job_is_not_skipped_with_the_event_job():
    """REQ-046: brief #836 answer 3 (a skipped ancestor skips a job unless its `if` overrides)."""
    line = next(ln for ln in job("sweep").splitlines() if ln.strip().startswith("if:"))
    assert "!cancelled()" in line
    assert "needs.sweep-gate.outputs.sweep == 'on'" in line


def test_one_sweep_at_a_time_across_pull_requests():
    """REQ-046: brief #836 answer 3 (each finished run has its own group; the sweep job has one).

    Brief #1066 (ADR-0452): the group is `agk-merger-sweep-job-2`, so the run of 2026-11-09 that waits for the
    `merge` environment under the old group no longer holds every later sweep.
    """
    body = job("sweep")
    assert re.search(r"^    concurrency:\n      group: agk-merger-sweep-job-2\n", body, re.M)
    assert "cancel-in-progress: false" in body


def test_the_schedule_and_the_dispatch_stay():
    """REQ-046: brief #836 answer 3 (the schedule and `workflow_dispatch` stay as a fallback)."""
    head = WORKFLOW.read_text(encoding="utf-8").split("\njobs:", 1)[0]
    assert '- cron: "*/15 * * * *"' in head and "\n  workflow_dispatch:\n" in head
    assert "\n  workflow_run:\n    workflows: [governance, proof]\n    types: [completed]\n" in head


def test_a_sweep_after_a_finished_check_merges_a_stale_label(tmp_path, monkeypatch, capsys):
    """REQ-046: brief #836 answer 6 (a `workflow_run` event sweeps; the command is the same)."""
    assert run_event(conclusion="failure")["action"] == "completed"
    world = World(monkeypatch, [a_pull(5, labels=("agk:fix",))], {5: clearing(5)})
    monkeypatch.setattr("merge_cleared.reroute", lambda root, repo, n: None)
    sweep(tmp_path, capsys)
    assert world.ran == [(5, sha_of(5))]


# --- answers 4 and 5: the conductor ---------------------------------------------------------------


@pytest.mark.parametrize("event", ["schedule", "workflow_dispatch", "workflow_run"])
def test_a_recent_sweep_prints_nothing(proj, stub, event):  # noqa: F811
    """REQ-046: brief #836 answer 4 (a sweep finished in the last 30 minutes)."""
    turn_on(proj)
    serve_runs(stub, a_run(event, 5))
    serve_pr(stub, pr(7), [cleared()])
    assert watch_lines(proj, stub) == ["nothing new"]


def test_a_late_sweep_with_a_cleared_pull_request_is_printed(proj, stub):  # noqa: F811
    """REQ-046: brief #836 answer 4 (`SWEEP late <m> min`)."""
    turn_on(proj)
    serve_runs(stub, a_run("schedule", 47), a_run("workflow_run", 95))
    serve_pr(stub, pr(7), [cleared()])
    lines = watch_lines(proj, stub)
    assert lines[0] == "nothing new"
    assert re.fullmatch(r"SWEEP late 4[78] min", lines[1])


def test_a_late_sweep_with_nothing_cleared_is_silent(proj, stub):  # noqa: F811
    """REQ-046: brief #836 answer 4 (only when a cleared pull request is open)."""
    turn_on(proj)
    serve_runs(stub, a_run("schedule", 47))
    serve_pr(stub, pr(7), [comment(5, "boss", f"Verdict: fix list {SHA}", ago(9))])
    assert watch_lines(proj, stub) == ["nothing new"]


def test_a_draft_cleared_is_not_counted(proj, stub):  # noqa: F811
    """REQ-046: brief #836 answers 2 and 4 (the sweep never takes a draft)."""
    turn_on(proj)
    serve_runs(stub, a_run("schedule", 47))
    serve_pr(stub, pr(7, draft=True), [cleared()])
    assert watch_lines(proj, stub) == ["nothing new"]


@pytest.mark.parametrize(
    "other", [a_run("issue_comment", 1), a_run("schedule", 1, conclusion="cancelled")]
)
def test_a_run_that_did_not_sweep_does_not_count(proj, stub, other):  # noqa: F811
    """REQ-046: brief #836 answer 4 (a comment's run and a cancelled run are not sweeps)."""
    turn_on(proj)
    serve_runs(stub, other, a_run("schedule", 47))
    serve_pr(stub, pr(7), [cleared()])
    assert any(line.startswith("SWEEP late 4") for line in watch_lines(proj, stub))


def test_no_sweep_run_at_all_is_late_too(proj, stub):  # noqa: F811
    """REQ-046: brief #836 answer 4 (none finished in the last 30 minutes)."""
    turn_on(proj)
    serve_runs(stub)
    serve_pr(stub, pr(7), [cleared()])
    assert "SWEEP late 30 min" in watch_lines(proj, stub)


def test_without_auto_merge_the_watch_reads_no_sweep_run(proj, stub):  # noqa: F811
    """REQ-046: brief #836 answer 5 (the same gate as the sweep: no sweep, no late sweep)."""
    serve_runs(stub, a_run("schedule", 300))
    serve_pr(stub, pr(7), [cleared()])
    assert watch_lines(proj, stub) == ["nothing new"]
    assert not any("actions/workflows" in str(c) for c in stub.calls())


def test_a_late_sweep_never_ends_the_watch_early(proj, stub):  # noqa: F811
    """REQ-046: brief #836 answer 4 (the line goes with what the pass prints)."""
    turn_on(proj)
    serve_runs(stub, a_run("schedule", 47))
    serve_pr(stub, pr(7), [cleared(), comment(6, "builder", "Report: done", ago(0))])
    out = run(proj, stub, "watch", "--since", ago(10), "--once")
    assert out.stdout.splitlines()[0] == "7 Report: done"
    assert out.stdout.splitlines()[1].startswith("SWEEP late 4")


def test_runs_that_cannot_be_read_end_nothing(proj, stub):  # noqa: F811
    """REQ-046: brief #836 answer 4 (a fallback that fails is silent; the watch is not hurt)."""
    turn_on(proj)
    stub.serve(RUNS, "FAIL")
    serve_pr(stub, pr(7), [cleared()])
    assert watch_lines(proj, stub) == ["nothing new"]
