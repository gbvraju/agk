"""Main checks run in batches (brief #621, ADR-0302): the workflow's concurrency and the readers.

REQ-016: a push to the default branch never cancels a running full check; pushes that arrive
meanwhile wait as one run for the newest commit. A commit whose own run was replaced while it
waited, or that has no run of its own, is covered by the next completed `governance full` run on a
later default-branch commit that contains it, and never counts as green before that run ends.
The workflow is read as text; the readers get invented, saved responses. No network.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
from datetime import UTC, datetime
from pathlib import Path

import full_run
import local_mode
import metrics
import route

ROOT = Path(__file__).resolve().parents[2]
C1, C2, C3, C4 = ("a1" * 20, "b2" * 20, "c3" * 20, "d4" * 20)
ORDER = [C1, C2, C3, C4]  # the default branch, oldest first: each commit contains the ones before


def contains(older: str, newer: str) -> bool:
    """`git merge-base --is-ancestor older newer` on the invented line C1..C4."""
    return older in ORDER and newer in ORDER and ORDER.index(older) <= ORDER.index(newer)


def push_run(rid: int, sha: str, conclusion: str | None, status: str = "completed", **kw) -> dict:
    run_ = {
        "id": rid,
        "head_sha": sha,
        "event": "push",
        "display_title": "governance full",
        "name": "governance",
        "status": status,
        "conclusion": conclusion if status == "completed" else None,
        "created_at": f"2026-11-06T10:{rid:02d}:00Z",
    }
    run_.update(kw)
    return run_


# --- answer 1 and 5: the workflow's concurrency ----------------------------------------------


def concurrency() -> str:
    """Read when a test runs: a copy of the kit tests in a project has no `.github/workflows`."""
    text = (ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    return text.split("\nconcurrency:\n", 1)[1].split("\njobs:", 1)[0]


def test_a_push_to_the_default_branch_shares_one_fixed_group():
    """REQ-016: brief #621 answer 1 (every push to the default branch shares one group, so
    GitHub keeps one running and at most one waiting run, the newest)."""
    block = concurrency()
    group = re.search(r"(?m)^  group: (.+)$", block)
    assert group
    expr = group.group(1)
    assert (
        "github.event_name == 'push' && github.ref_name == github.event.repository.default_branch"
        " && format('governance-{0}-code', github.ref_name)"
    ) in expr
    fixed = expr.split("||", 1)[0]
    assert "github.sha" not in fixed and "pull_request" not in fixed


def test_a_running_push_run_is_never_cancelled():
    """REQ-016: brief #621 answer 1 (a run 80% done finishes; only pull request runs cancel, and
    since brief #1122 an edited run cancels none, ADR-0480)."""
    assert re.search(
        r"(?m)^  cancel-in-progress: \$\{\{ github\.event_name == 'pull_request'"
        r" && github\.event\.action != 'edited' \}\}$",
        concurrency(),
    )


def test_pull_request_and_edited_groups_are_unchanged():
    """REQ-016: brief #621 answer 1 (a pull request's group as brief #216 made it), with the
    `edited` run in that same group since brief #1122 answer 1 (ADR-0480), where it waits for
    the full run instead of polling it."""
    expr = re.search(r"(?m)^  group: (.+)$", concurrency()).group(1)
    pull = expr.split("||", 1)[1]
    assert "format('governance-{0}-code', github.event.pull_request.number || github.sha)" in pull
    assert "'edited'" not in expr


def test_the_header_says_waiting_pushes_collapse():
    """REQ-016: brief #621 answer 1 (the header comment says what happens to a waiting push)."""
    text = (ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    head = text.split("\nconcurrency:\n", 1)[0]
    assert "brief #621" in head
    assert "never cancelled" in head and "newest commit" in head


# --- answer 2: the rule every reader uses (full_run.covered) ----------------------------------


def test_a_commit_with_its_own_green_run_is_green():
    """REQ-016: brief #621 answer 2 (a run of its own decides)."""
    state, used = full_run.covered(C2, [push_run(1, C2, "success")], contains)
    assert (state, used["id"]) == ("green", 1)


def test_a_replaced_run_is_covered_by_the_next_completed_run_that_contains_it():
    """REQ-016: brief #621 answer 2 (runs 2 and 3 replaced while waiting; run 4 covers them)."""
    runs = [
        push_run(1, C1, "success"),
        push_run(2, C2, "cancelled"),
        push_run(3, C3, "cancelled"),
        push_run(4, C4, "success"),
    ]
    assert full_run.covered(C2, runs, contains)[0] == "green"
    assert full_run.covered(C3, runs, contains)[1]["id"] == 4


def test_a_red_covering_run_is_red_for_every_commit_it_covers():
    """REQ-016: brief #621 answer 2 (its result is the result of every commit in between)."""
    runs = [push_run(2, C2, "cancelled"), push_run(4, C4, "failure")]
    assert full_run.covered(C2, runs, contains)[0] == "red"


def test_a_commit_with_no_run_of_its_own_is_covered_too():
    """REQ-016: brief #621 answer 2 (a commit with no run of its own)."""
    assert full_run.covered(C3, [push_run(4, C4, "success")], contains)[0] == "green"


def test_a_replaced_run_is_never_green_while_the_covering_run_has_not_ended():
    """REQ-016: brief #621 answer 2 (never green while no later run has completed)."""
    runs = [push_run(2, C2, "cancelled"), push_run(4, C4, None, status="in_progress")]
    assert full_run.covered(C2, runs, contains) == ("pending", None)
    assert full_run.covered(C2, [push_run(2, C2, "cancelled")], contains) == ("pending", None)
    assert full_run.covered(C2, [], contains) == ("pending", None)


def test_a_cancelled_run_never_counts_as_green_on_its_own():
    """REQ-016: brief #621 answer 2 (a cancelled run, own or later, is never a result)."""
    runs = [push_run(2, C2, "cancelled"), push_run(4, C4, "cancelled")]
    assert full_run.covered(C2, runs, contains) == ("pending", None)


def test_a_later_run_that_does_not_contain_the_commit_covers_nothing():
    """REQ-016: brief #621 answer 2 (`git merge-base --is-ancestor` must hold)."""
    stray = "e5" * 20
    runs = [push_run(2, C2, "cancelled"), push_run(4, stray, "success")]
    assert full_run.covered(C2, runs, contains) == ("pending", None)


def test_the_first_covering_run_decides_not_a_newer_green_one():
    """REQ-016: brief #621 answer 2 (the next completed run, not the newest)."""
    runs = [push_run(2, C2, "cancelled"), push_run(3, C3, "failure"), push_run(4, C4, "success")]
    state, used = full_run.covered(C2, runs, contains)
    assert (state, used["id"]) == ("red", 3)


def test_its_own_running_run_is_pending():
    """REQ-016: brief #621 answer 2 (a run of its own still running is waited for)."""
    runs = [push_run(2, C2, None, status="in_progress"), push_run(4, C4, "success")]
    assert full_run.covered(C2, runs, contains) == ("pending", None)


def test_only_full_push_runs_count():
    """REQ-016: brief #621 answer 2 (a pull request run or an `edited` run covers nothing)."""
    runs = [
        push_run(2, C2, "cancelled"),
        push_run(4, C4, "success", event="pull_request"),
        push_run(5, C4, "success", display_title="governance edited"),
    ]
    assert full_run.covered(C2, runs, contains) == ("pending", None)


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_containment_is_read_with_git_and_an_unknown_commit_is_not_contained(tmp_path):
    """REQ-016: brief #621 answer 2 (git decides; a commit git does not know fails closed)."""
    git(tmp_path, "init", "-q")
    for n in ("1", "2"):
        (tmp_path / "f").write_text(n, encoding="utf-8")
        git(tmp_path, "add", "f")
        git(tmp_path, "-c", "user.name=a", "-c", "user.email=a@example.com", "commit", "-qm", n)
    old, new = git(tmp_path, "rev-parse", "HEAD~1"), git(tmp_path, "rev-parse", "HEAD")
    inside = full_run.contained_in(tmp_path)
    assert inside(old, new) is True
    assert inside(new, old) is False
    assert inside("f" * 40, new) is False


# --- answer 2: the readers ---------------------------------------------------------------------


class Saved:
    """Saved responses by name, as metrics' `ApiDir` reads them."""

    def __init__(self, data: dict) -> None:
        self.data = data
        self.asked: list[str] = []

    def get(self, name: str, endpoint: str, until=None):
        self.asked.append(endpoint)
        return self.data.get(name)


HEAD = "f0" * 20


def detail(merge: str) -> dict:
    return {
        "number": 7,
        "merged_at": "2026-11-06T10:00:00Z",
        "merge_commit_sha": merge,
        "head": {"sha": HEAD},
        "base": {"ref": "main"},
    }


def proof_saved(outcome: str) -> dict:
    return {
        f"runs-{HEAD}": {"workflow_runs": [{"id": 90, "name": "proof", "created_at": "x"}]},
        "run-jobs-90": {
            "jobs": [
                {
                    "name": "proof",
                    "conclusion": "success",
                    "started_at": "2026-11-06T09:00:00Z",
                    "steps": [{"name": f"outcome: {outcome} (x)", "conclusion": "success"}],
                }
            ]
        },
    }


def test_metrics_never_reads_a_replaced_push_run_as_green():
    """REQ-016: brief #621 answer 2 (the backstop-escape reader: a merge commit whose push run was
    replaced, with no later run done, is unknown, never green)."""
    src = Saved(
        {
            f"runs-{C2}": {"workflow_runs": [push_run(2, C2, "cancelled", head_branch="main")]},
            "branch-runs-main": {"workflow_runs": [push_run(2, C2, "cancelled")]},
        }
    )
    assert metrics.escape_of(src, detail(C2), contains) == metrics.UNKNOWN


def test_metrics_reads_the_covering_run_of_a_replaced_push_run():
    """REQ-016: brief #621 answer 2 (green when the covering run is green)."""
    branch = {"workflow_runs": [push_run(2, C2, "cancelled"), push_run(4, C4, "success")]}
    src = Saved({f"runs-{C2}": {"workflow_runs": []}, "branch-runs-main": branch})
    assert metrics.escape_of(src, detail(C2), contains) == "green"
    assert any("workflows/governance.yml/runs?branch=main&event=push" in e for e in src.asked)


def test_metrics_reads_a_red_covering_run_as_a_red_push():
    """REQ-016: brief #621 answer 2 (a red covering run is red for the merge, then the proof
    decides escape or red as before)."""
    branch = {"workflow_runs": [push_run(2, C2, "cancelled"), push_run(4, C4, "failure")]}
    saved = {f"runs-{C2}": {"workflow_runs": []}, "branch-runs-main": branch}
    saved.update(proof_saved("not-proven"))
    assert metrics.escape_of(Saved(saved), detail(C2), contains) == "red"


def test_metrics_keeps_reading_a_push_run_of_its_own():
    """REQ-016: brief #621 answer 2 (a run of its own decides; the branch list is not read)."""
    own = push_run(2, C2, "success", head_branch="main")
    src = Saved({f"runs-{C2}": {"workflow_runs": [own]}})
    assert metrics.escape_of(src, detail(C2), contains) == "green"
    assert not any("branch=" in e for e in src.asked)


def test_the_router_never_reads_the_tip_waiting_for_its_run_as_green():
    """REQ-016: brief #621 answer 2 (the red-branch reader reads only the tip, whose run is never
    replaced: a tip whose run waits has no check yet and is pending; a cancelled one is red)."""
    required = ["proof", "governance"]
    assert route.branch_state([], [], required) == "pending"
    cancelled = [{"id": 1, "name": "governance", "status": "completed", "conclusion": "cancelled"}]
    assert route.branch_state(cancelled, [], required) == "red"


class Local:
    def __init__(self, data: dict) -> None:
        self.data = data

    def get(self, name: str, endpoint: str):
        return 200, self.data[name]


def test_local_mode_catch_up_never_reads_a_cancelled_tip_as_green():
    """REQ-016: brief #621 answer 2 (the catch-up reader reads only the tip; cancelled is red)."""
    run_ = {
        "id": 1,
        "name": "governance",
        "head_sha": C4,
        "status": "completed",
        "conclusion": "cancelled",
        "started_at": "2026-11-06T10:00:00Z",
    }
    src = Local({"commit": {"sha": C4}, "check-runs": {"check_runs": [run_]}})
    since = datetime(2026, 11, 6, tzinfo=UTC)
    found = local_mode.catch_up(src, "main", since, ["governance"])
    assert found.red and "catch-up: green" not in found.lines
