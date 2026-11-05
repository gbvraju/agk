"""merge_cleared.py build (d): the CI path holds a cleared head whose checks are still running.

Brief #569, REQ-046 (SPEC-0039 rule 10, `Q-S0039-12`): GitHub's own auto-merge is offered only
through GraphQL, which the kit never calls, so with a required check of the cleared head still
queued or in progress the command merges nothing, turns nothing on and exits 3 with exactly
`merge-cleared #<n> <sha12>: held: checks pending`; the next review pass merges once they are
green. It reads the head's check runs and its commit status over REST only. Saved responses and a
fake `gh` only; no network; invented logins, addresses at example.com.
"""

from __future__ import annotations

import pytest
from test_merge_cleared_verdict import (
    GREEN_RUNS,
    HEAD,
    MERGE12,
    ON,
    REPO,
    SHA12,
    merge_cleared_run,
    one_line,
    toml,
)
from test_merge_cleared_verdict import cleared as verdict

MERGED = f"merge-cleared #7 {SHA12}: merged {MERGE12}"
PENDING = f"merge-cleared #7 {SHA12}: held: checks pending"
RED = f"merge-cleared #7 {SHA12}: held: a required check is red (rule 4)"
STATUS_READ = f"repos/{REPO}/commits/{HEAD}/status?per_page=100&page=1"


def run(name: str, conclusion: str | None, status: str = "completed", rid: int = 20) -> dict:
    return {"id": rid, "name": name, "status": status, "conclusion": conclusion}


def status(context: str, state: str, sid: int = 30) -> dict:
    return {"id": sid, "context": context, "state": state}


def ci(tmp_path, runs=None, statuses=None, status_state=None):
    """One run of the command in CI mode on a cleared head with the saved checks of the head."""
    saved = {"runs": runs, "statuses": statuses, "status_state": status_state}
    return merge_cleared_run(tmp_path, toml(ON), [verdict()], **saved)


def writes(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if "--method" in c and c[c.index("--method") + 1] != "GET"]


def held_pending(proc, made) -> None:
    assert one_line(proc) == PENDING, proc.stdout + proc.stderr
    assert proc.returncode == 3
    assert writes(made) == [], "nothing is merged, turned on or posted"
    flat = [a for c in made for a in c]
    assert not any("graphql" in a for a in flat), "the command never calls GraphQL"
    assert not any("auto-merge" in a or "auto_merge" in a for a in flat)


# --- pending: held, nothing merged, nothing turned on ------------------------------------------


@pytest.mark.parametrize("state", ["queued", "in_progress", "waiting", "requested", "pending"])
def test_a_required_check_run_not_ended_holds_with_checks_pending(tmp_path, state):
    """REQ-046 AC7: SPEC-0039 rule 10, brief #569 answer 1 (exactly `held: checks pending`)."""
    runs = [GREEN_RUNS[0], run("governance", None, state)]
    proc, made = ci(tmp_path, runs=runs)
    held_pending(proc, made)


def test_every_required_check_pending_holds(tmp_path):
    """REQ-046 AC7: brief #569 answer 3 (pending)."""
    runs = [run("proof", None, "queued", 11), run("governance", None, "in_progress", 12)]
    proc, made = ci(tmp_path, runs=runs)
    held_pending(proc, made)


def test_a_mix_of_pending_and_green_holds(tmp_path):
    """REQ-046 AC7: brief #569 answer 3 (a mix of pending and green)."""
    runs = [*GREEN_RUNS, run("governance", None, "in_progress", rid=30)]  # a re-run, still going
    proc, made = ci(tmp_path, runs=runs)
    held_pending(proc, made)


def test_a_required_commit_status_pending_holds(tmp_path):
    """REQ-046 AC7: brief #569 answer 2 (the commit status of the head is read too)."""
    proc, made = ci(tmp_path, runs=[GREEN_RUNS[1]], statuses=[status("proof", "pending")])
    held_pending(proc, made)


def test_a_status_pending_beside_a_green_run_of_the_same_name_holds(tmp_path):
    """REQ-046 AC7: brief #569 answer 2 (a name is ended only when all its reports ended)."""
    proc, made = ci(tmp_path, runs=GREEN_RUNS, statuses=[status("governance", "pending")])
    held_pending(proc, made)


def test_a_later_pass_merges_the_same_head_once_its_checks_are_green(tmp_path):
    """REQ-046 AC7: SPEC-0039 rule 10 (rule 9's retry merges once they are green)."""
    proc, made = ci(tmp_path / "a", runs=[GREEN_RUNS[0], run("governance", None, "in_progress")])
    held_pending(proc, made)
    proc, made = ci(tmp_path / "b", runs=GREEN_RUNS)
    assert one_line(proc) == MERGED and proc.returncode == 0


# --- green: merges, as today --------------------------------------------------------------------


def test_all_green_merges_and_reads_runs_and_status_over_rest(tmp_path):
    """REQ-046 AC7: brief #569 answers 2 and 3 (all green merges; REST GETs only)."""
    proc, made = ci(tmp_path, runs=GREEN_RUNS, statuses=[status("proof", "success")])
    assert one_line(proc) == MERGED and proc.returncode == 0
    reads = [c for c in made if any("/commits/" in a for a in c)]
    assert reads == [
        ["api", "--method", "GET", f"repos/{REPO}/commits/{HEAD}/check-runs?per_page=100&page=1"],
        ["api", "--method", "GET", STATUS_READ],
    ]
    assert not any("graphql" in a for c in made for a in c)


def test_a_required_check_reported_only_as_a_green_status_merges(tmp_path):
    """REQ-046 AC7: brief #569 answer 2 (a required name may be a status context)."""
    proc, _ = ci(tmp_path, runs=[GREEN_RUNS[1]], statuses=[status("proof", "success")])
    assert one_line(proc) == MERGED


def test_the_combined_state_with_no_statuses_never_holds(tmp_path):
    """REQ-046 AC7: GitHub answers a combined `pending` when a head has no status at all."""
    proc, _ = ci(tmp_path, runs=GREEN_RUNS, statuses=[], status_state="pending")
    assert one_line(proc) == MERGED


def test_the_latest_status_of_a_context_decides(tmp_path):
    """REQ-046 AC7: brief #569 answer 2 (an older pending status of a context is replaced)."""
    statuses = [status("proof", "pending", 1), status("proof", "success", 2)]
    proc, _ = ci(tmp_path, runs=GREEN_RUNS, statuses=statuses)
    assert one_line(proc) == MERGED


# --- a pending check that is not required ------------------------------------------------------


def test_a_pending_check_that_is_not_required_never_holds(tmp_path):
    """REQ-046 AC7: brief #569 answer 3 (a pending check that is not required)."""
    runs = [*GREEN_RUNS, run("lint-extra", None, "in_progress", rid=40)]
    statuses = [status("deploy-preview", "pending")]
    proc, _ = ci(tmp_path, runs=runs, statuses=statuses)
    assert one_line(proc) == MERGED and proc.returncode == 0


# --- red stays held under the existing rule -----------------------------------------------------


@pytest.mark.parametrize("state", ["failure", "error"])
def test_a_red_required_status_holds_as_red(tmp_path, state):
    """REQ-046 AC3: brief #569 answer 2 (a failed required check stays held, unchanged)."""
    proc, made = ci(tmp_path, runs=GREEN_RUNS, statuses=[status("proof", state)])
    assert one_line(proc) == RED and proc.returncode == 3
    assert writes(made) == []


@pytest.mark.parametrize("conclusion", ["failure", "cancelled"])
def test_red_wins_over_pending(tmp_path, conclusion):
    """REQ-046 AC3: brief #569 answer 2 (failed or cancelled holds as red, not as pending)."""
    runs = [run("proof", conclusion, rid=11), run("governance", None, "in_progress", 12)]
    proc, made = ci(tmp_path, runs=runs)
    assert one_line(proc) == RED and proc.returncode == 3
    assert writes(made) == []


def test_local_mode_reads_no_commit_status(tmp_path):
    """REQ-046 AC7: the CI path only; local mode keeps its own evidence (rule 4)."""
    proc, made = merge_cleared_run(tmp_path, toml(ON, local=True), [verdict()])
    assert proc.stdout.startswith(f"merge-cleared #7 {SHA12}: "), proc.stdout + proc.stderr
    assert not any("/status" in a for c in made for a in c)
