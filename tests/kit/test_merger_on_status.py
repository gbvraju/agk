"""The merger starts on the verdict status `agk/verdict` (brief #853).

ADR-0387, amendment 151, REQ-046 (SPEC-0039 rule 2). `merger.yml` also starts on the `status` event
for `agk/verdict` with `success`, as a step of its existing job, and `merge_cleared.py --event`
names the open pull request whose head is that sha, then the guarded command runs as for any
other start. A verdict comment refreshes the status first. Saved payloads, a git repository in
`tmp_path` and a fake `gh`; no network, invented data.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from test_merge_cleared_merger import comment_event, run_event, writes
from test_merge_cleared_verdict import (
    HEAD,
    MERGE12,
    OLD,
    ON,
    SHA12,
    calls,
    cleared,
    comment,
    fake_gh,
    repo,
    run,
    toml,
)
from test_verdict_status import posted

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "merger.yml"
OPEN_PULL = {"number": 7, "state": "open", "head": {"sha": HEAD}, "base": {"ref": "main"}}
FIX_LIST = f"Verdict: fix list {HEAD}\n\n1. Fix the test.\n"


def status_event(state: str = "success", context: str = "agk/verdict", sha: str = HEAD) -> dict:
    """A saved `status` payload (invented)."""
    return {"sha": sha, "state": state, "context": context, "description": "cleared", "id": 91}


def fire(tmp_path, payload: dict, name: str = "status", main: str = toml(ON), **saved):
    root = repo(tmp_path, main)
    bin_dir, log = fake_gh(tmp_path, **saved)
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    proc = run(root, bin_dir, "--event", str(path), "--event-name", name)
    return proc, calls(log), root, bin_dir


# --- the event ------------------------------------------------------------------------------------


def test_the_success_status_names_the_open_pull_request_of_that_head(tmp_path):
    """REQ-046: brief #853 answer 2."""
    proc, made, _, _ = fire(tmp_path, status_event(), comments=[cleared()], head_pulls=[OPEN_PULL])
    assert proc.stdout.strip() == f"7 {HEAD}", proc.stdout + proc.stderr
    assert writes(made) == []


def test_a_cleared_head_gets_success_and_merges(tmp_path):
    """REQ-046: brief #853 answer 6 (the status event starts the guarded merge)."""
    proc, _, root, bin_dir = fire(
        tmp_path, status_event(), comments=[cleared()], head_pulls=[OPEN_PULL]
    )
    number, sha = proc.stdout.split()
    merged = run(root, bin_dir, "--pr", number, "--sha", sha)
    assert merged.stdout.strip() == f"merge-cleared #7 {SHA12}: merged {MERGE12}", merged.stdout


@pytest.mark.parametrize(
    "payload",
    [
        status_event(state="pending"),
        status_event(state="failure"),
        status_event(context="governance"),
        status_event(sha="abc"),
        {"state": "success", "context": "agk/verdict"},
    ],
)
def test_any_other_status_does_nothing(tmp_path, payload):
    """REQ-046: brief #853 answer 2 (`agk/verdict` with `success` alone)."""
    proc, made, _, _ = fire(tmp_path, payload, comments=[cleared()], head_pulls=[OPEN_PULL])
    assert proc.stdout == "", proc.stdout
    assert proc.returncode == 0
    assert writes(made) == []


@pytest.mark.parametrize(
    "pulls",
    [
        [],
        [{**OPEN_PULL, "state": "closed"}],
        [{**OPEN_PULL, "head": {"sha": OLD}}],
        [{**OPEN_PULL, "base": {"ref": "release"}}],
        [OPEN_PULL, {**OPEN_PULL, "number": 8}],
    ],
)
def test_a_head_that_is_not_one_open_pull_request_does_nothing(tmp_path, pulls):
    """REQ-046: brief #853 answer 2 (the conservative reading: exactly one open pull request)."""
    proc, _, _, _ = fire(tmp_path, status_event(), comments=[cleared()], head_pulls=pulls)
    assert proc.stdout == "", proc.stdout


def test_a_status_alone_clears_nothing(tmp_path):
    """REQ-046: AC2 (the status starts the job; the verdict is read again)."""
    fixes = [comment(FIX_LIST, at=6)]
    proc, _, _, _ = fire(tmp_path, status_event(), comments=fixes, head_pulls=[OPEN_PULL])
    assert proc.stdout == "", proc.stdout
    assert "not cleared" in proc.stderr


def test_with_the_merge_queue_the_status_starts_no_merge(tmp_path):
    """REQ-046: brief #853 answer 4."""
    main = toml(ON + "merge_queue = true\n")
    proc, _, _, _ = fire(
        tmp_path, status_event(), main=main, comments=[cleared()], head_pulls=[OPEN_PULL]
    )
    assert proc.stdout == "", proc.stdout
    assert "flow.merge_queue" in proc.stderr


# --- the status step of the job -------------------------------------------------------------------


def set_from(tmp_path, payload: dict, name: str, **saved):
    root = repo(tmp_path, toml(ON))
    bin_dir, log = fake_gh(tmp_path, **saved)
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    proc = run(root, bin_dir, "--status", "--event", str(path), "--event-name", name)
    return proc, calls(log)


def test_a_fix_list_comment_refreshes_the_status(tmp_path):
    """REQ-046: brief #853 answer 1 (an old `success` never outlives a newer verdict)."""
    proc, made = set_from(
        tmp_path, comment_event(FIX_LIST), "issue_comment", comments=[comment(FIX_LIST, at=6)]
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert [p["description"] for p in posted(made)] == ["fix list"]


def test_an_unrelated_comment_sets_no_status(tmp_path):
    """REQ-046: only a verdict or an approval reads the head."""
    _, made = set_from(tmp_path, comment_event("Report: done"), "issue_comment", comments=[])
    assert posted(made) == []


@pytest.mark.parametrize(
    ("payload", "name"),
    [(status_event(), "status"), (run_event(), "workflow_run")],
)
def test_the_status_step_acts_only_on_a_comment(tmp_path, payload, name):
    """REQ-046: no status write answers a status event, so nothing can loop."""
    _, made = set_from(tmp_path, payload, name, comments=[cleared()], head_pulls=[OPEN_PULL])
    assert posted(made) == []


def test_the_status_step_with_auto_merge_off_sets_nothing(tmp_path):
    """REQ-046: AC1."""
    root = repo(tmp_path, toml(""))
    bin_dir, log = fake_gh(tmp_path, comments=[cleared()])
    path = tmp_path / "event.json"
    path.write_text(json.dumps(comment_event(f"Verdict: cleared {HEAD}")), encoding="utf-8")
    proc = run(root, bin_dir, "--status", "--event", str(path), "--event-name", "issue_comment")
    assert proc.returncode == 0
    assert posted(calls(log)) == []


# --- the workflow ---------------------------------------------------------------------------------


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def job(name: str) -> str:
    return re.search(rf"\n  {name}:\n(.*?)(?=\n  [a-z-]+:\n    |\Z)", text(), re.S).group(1)


def test_the_workflow_starts_on_the_status_event():
    """REQ-046: brief #853 answer 2 (the one new trigger)."""
    head = text().split("\njobs:", 1)[0]
    block = re.search(r"\non:\n(.*?)\n(?=[a-z])", head, re.S).group(1)
    assert re.findall(r"^  ([a-z_]+):", block, re.M) == [
        "issue_comment",
        "workflow_run",
        "status",
        "schedule",
        "workflow_dispatch",
    ]


def test_no_new_job():
    """REQ-046: brief #853 (the cost rule of #846: a step of the existing job)."""
    body = text().split("\njobs:\n", 1)[1]
    assert re.findall(r"^  ([a-z-]+):$", body, re.M) == ["merger", "sweep-gate", "sweep"]


def test_the_job_starts_only_for_a_success_of_the_verdict_status():
    """REQ-046: brief #853 answer 2."""
    condition = re.search(r"^    if: (.*)$", job("merger"), re.M).group(1)
    assert (
        "(github.event_name == 'status' && github.event.context == 'agk/verdict' "
        "&& github.event.state == 'success')"
    ) in condition


def test_a_status_event_never_starts_the_sweep():
    """REQ-046: brief #853 (each status of any check must cost no sweep)."""
    assert "'status'" not in re.search(r"^    if: (.*)$", job("sweep-gate"), re.M).group(1)


def test_runs_of_one_head_share_a_group():
    """REQ-046: two statuses of one head never run the job side by side."""
    assert "github.event.sha" in re.search(r"group: (agk-merger-.*)", text()).group(1)


def test_the_job_refreshes_the_status_after_a_comment():
    """REQ-046: brief #853 answer 1 (a step of the job, with the job's token, ending green)."""
    steps = job("merger")
    assert (
        'python3 scripts/agk/merge_cleared.py --status --event "$GITHUB_EVENT_PATH" '
        '--event-name "$EVENT_NAME" || echo "merger: no status"'
    ) in steps
    assert steps.index("--status --event") < steps.index('--event-name "$EVENT_NAME")')


def test_the_pull_request_copy_of_the_body_is_never_read():
    """REQ-046: the `status` event runs this file from the default branch, as the job checks out."""
    assert "ref: ${{ github.event.repository.default_branch }}" in job("merger")
