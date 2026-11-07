"""The conductor guard allows the routines of `conductor.py` (brief #643, builds (a) and (b)).

REQ-037. Exactly `python3 scripts/agk/conductor.py sweep` and `... watch [--since <ISO>] [--once]`,
the project's own regular file, so that the role's operating lessons name a command it can run;
every other form stays denied. Build (b), ADR-0329: `... merge-queue [--dry-run] [--max-batch N]`
too, the dry run always and a run that merges only with `auto_merge` on in the checkout and on the
default branch, as `merge_cleared.py` itself; builders are asked first. No test uses the network."""

from __future__ import annotations

import json

import pytest
from test_conductor_guard import (
    FLOW_OFF,
    FLOW_ON,
    REPO_ROOT,
    allows_merge,
    merge_decision,
    merge_project,
)
from test_conductor_guard_queue import RULE, reason, run_hook

SCRIPT = "scripts/agk/conductor.py"
WHEN = "2026-11-06T10:00:00Z"


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    (root / "scripts" / "agk").mkdir(parents=True)
    (root / SCRIPT).write_text("print('the project script')\n", encoding="utf-8")
    (root / ".git").mkdir()
    return root


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {SCRIPT} sweep",
        f"python3 {SCRIPT} watch",
        f"python3 {SCRIPT} watch --once",
        f"python3 {SCRIPT} watch --since {WHEN}",
        f"python3 {SCRIPT} watch --since {WHEN} --once",
    ],
)
def test_the_read_only_routines_are_allowed(project, command):
    result = run_hook(command, project)
    assert result.returncode == 0 and result.stdout == "", result.stdout


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {SCRIPT}",
        f"python3 {SCRIPT} merge-queue",
        f"python3 {SCRIPT} sweep --all",
        f"python3 {SCRIPT} watch --since yesterday",
        f"python3 {SCRIPT} watch --once --since {WHEN}",
        f"python3 {SCRIPT} watch --since {WHEN} --once x",
        f"python3 {SCRIPT} sweep; gh pr merge 7",
        f"python3 -I {SCRIPT} sweep",
        "python3 /elsewhere/scripts/agk/conductor.py sweep",
    ],
)
def test_every_other_form_is_denied(project, command):
    assert reason(run_hook(command, project).stdout) is not None


def test_a_linked_script_is_denied(project, tmp_path):
    (project / SCRIPT).unlink()
    other = tmp_path / "other.py"
    other.write_text("print(1)\n", encoding="utf-8")
    (project / SCRIPT).symlink_to(other)
    assert reason(run_hook(f"python3 {SCRIPT} sweep", project).stdout) == RULE


# --- merge-queue (build (b), ADR-0329) --------------------------------------------------------

QUEUE = f"python3 {SCRIPT} merge-queue"
DRY = [f"{QUEUE} --dry-run", f"{QUEUE} --dry-run --max-batch 3"]
RUNS = [QUEUE, f"{QUEUE} --max-batch 3", f"{QUEUE} --max-batch 12"]


def queue_project(tmp_path, here: str, there: str | None):
    root = merge_project(tmp_path, here, there)
    (root / SCRIPT).write_text("print('the project script')\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("command", DRY + RUNS)
def test_the_merge_queue_is_allowed_with_auto_merge_on_in_both_places(tmp_path, command):
    """The explicit allow lifts the builders' ask entry, as for `merge_cleared.py`."""
    root = queue_project(tmp_path, FLOW_ON, FLOW_ON)
    assert allows_merge(merge_decision(root, command)), command


OFF_SOMEWHERE = [(FLOW_OFF, FLOW_ON), (FLOW_ON, FLOW_OFF), (FLOW_ON, None)]


@pytest.mark.parametrize(("here", "there"), OFF_SOMEWHERE)
@pytest.mark.parametrize("command", RUNS)
def test_a_queue_that_merges_is_denied_with_auto_merge_off_in_either_place(
    tmp_path, here, there, command
):
    found = merge_decision(queue_project(tmp_path, here, there), command)
    assert found is not None and found["permissionDecision"] == "deny"


@pytest.mark.parametrize("command", DRY)
def test_the_dry_run_merges_nothing_and_is_allowed_with_auto_merge_off(tmp_path, command):
    root = queue_project(tmp_path, FLOW_OFF, FLOW_OFF)
    assert allows_merge(merge_decision(root, command)), command


@pytest.mark.parametrize(
    "command",
    [
        f"{QUEUE} --max-batch 0",
        f"{QUEUE} --max-batch",
        f"{QUEUE} --max-batch 3 --dry-run",
        f"{QUEUE} --dry-run --dry-run",
        f"{QUEUE} --force",
        f"{QUEUE} --max-batch 3; gh pr merge 7",
        f"python {SCRIPT} merge-queue",
        f"python3 -I {SCRIPT} merge-queue",
        "python3 /elsewhere/scripts/agk/conductor.py merge-queue",
    ],
)
def test_every_other_form_of_the_merge_queue_is_denied(tmp_path, command):
    found = merge_decision(queue_project(tmp_path, FLOW_ON, FLOW_ON), command)
    assert found is not None and found["permissionDecision"] == "deny", command


def test_the_shadow_reviewer_never_runs_the_merge_queue(tmp_path):
    root = queue_project(tmp_path, FLOW_ON, FLOW_ON)
    for command in DRY + RUNS:
        found = merge_decision(root, command, shadow=True)
        assert found is not None and found["permissionDecision"] == "deny", command


def test_builders_are_asked_before_the_merge_queue_and_no_deny_or_allow_is_added():
    """Q-S0039-15: the builders' settings ask, as for `merge_cleared.py`, never a deny."""
    data = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "Bash(*conductor.py*merge-queue*)" in data["permissions"]["ask"]
    for kind in ("deny", "allow"):
        assert not any("merge-queue" in e for e in data["permissions"][kind])


# --- rerun, check-verdict and lease (brief #700, ADR-0330) -------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {SCRIPT} rerun --pr 7",
        f"python3 {SCRIPT} rerun --pr 7 --apply",
        f"python3 {SCRIPT} check-verdict /tmp/scratch/verdict.md",
        f"python3 {SCRIPT} check-verdict verdict.md",
        f"python3 {SCRIPT} lease --show",
        f"python3 {SCRIPT} lease --take c1",
        f"python3 {SCRIPT} lease --release c1",
    ],
)
def test_the_routines_of_brief_700_are_allowed(project, command):
    result = run_hook(command, project)
    assert result.returncode == 0 and result.stdout == "", result.stdout


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {SCRIPT} rerun",
        f"python3 {SCRIPT} rerun --pr x",
        f"python3 {SCRIPT} rerun --pr 7 --force",
        f"python3 {SCRIPT} rerun --apply --pr 7",
        f"python3 {SCRIPT} check-verdict",
        f"python3 {SCRIPT} check-verdict --all",
        f"python3 {SCRIPT} check-verdict a b",
        f"python3 {SCRIPT} lease",
        f"python3 {SCRIPT} lease --take",
        f"python3 {SCRIPT} lease --take c1 --show",
        f"python3 {SCRIPT} lease --hold c1",
        f"python3 {SCRIPT} lease --show; gh pr merge 7",
        f"python {SCRIPT} lease --show",
        "python3 /elsewhere/scripts/agk/conductor.py lease --show",
    ],
)
def test_every_other_form_of_the_new_routines_is_denied(project, command):
    assert reason(run_hook(command, project).stdout) is not None


def test_the_shadow_reviewer_runs_none_of_the_new_routines(project):
    for command in (f"python3 {SCRIPT} lease --show", f"python3 {SCRIPT} rerun --pr 7"):
        result = run_hook(command, project, shadow=True)
        assert reason(result.stdout) is not None, command
