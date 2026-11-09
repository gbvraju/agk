"""merge_cleared.py --status: the verdict as the commit status `agk/verdict` (brief #853).

ADR-0387, amendment 151, REQ-046 (SPEC-0039 rules 2 and 5). `--status --pr N --sha HEAD` reads the
head as the merge reads it and sets `success` (cleared, approvals in, not in the re-prove state, no
owner-only path) or `pending` with the reason; in local mode it prints the state and sets nothing.
Every test runs on a git repository in `tmp_path`, saved responses and a fake `gh`. No network;
invented logins, addresses at example.com.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_merge_cleared_reprove import FIRST, LAST, SHARED, reprove_world
from test_merge_cleared_verdict import (
    AUTO_ISSUE,
    HEAD,
    OLD,
    ON,
    OWNER,
    REPO,
    SHA12,
    calls,
    cleared,
    comment,
    fake_gh,
    repo,
    run,
    toml,
    world,
)

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import doctor as doctor_module  # noqa: E402

CONTEXT = "agk/verdict"
FIX_LIST = f"Verdict: fix list {HEAD}\n\n1. Fix the test.\n"


def status_run(tmp_path: Path, main: str = toml(ON), sha: str = HEAD, **saved):
    root = repo(tmp_path, main)
    bin_dir, log = fake_gh(tmp_path, **saved)
    proc = run(root, bin_dir, "--status", "--pr", "7", "--sha", sha)
    return proc, calls(log)


def posted(made: list[list[str]]) -> list[dict[str, str]]:
    """The fields of every status the command set."""
    found = []
    for call in made:
        if "POST" in call and any(a.startswith(f"repos/{REPO}/statuses/") for a in call):
            fields = [call[i + 1] for i, a in enumerate(call) if a == "-f"]
            found.append(dict(f.split("=", 1) for f in fields))
    return found


def line(state: str) -> str:
    return f"merge-cleared #7 {SHA12}: status {state}"


# --- answer 1: the state ------------------------------------------------------------------------


def test_a_cleared_head_gets_success(tmp_path):
    """REQ-046: brief #853 answer 6 (a cleared head gets `success`)."""
    proc, made = status_run(tmp_path, comments=[cleared()])
    assert proc.stdout.strip() == line("success"), proc.stdout + proc.stderr
    assert proc.returncode == 0
    assert posted(made) == [{"state": "success", "context": CONTEXT, "description": "cleared"}]
    assert f"repos/{REPO}/statuses/{HEAD}" in [a for c in made for a in c]


def test_a_fix_list_gets_pending_fix_list(tmp_path):
    """REQ-046: brief #853 answer 6."""
    proc, made = status_run(tmp_path, comments=[comment(FIX_LIST, at=6)])
    assert proc.stdout.strip() == line("pending fix list"), proc.stdout + proc.stderr
    assert posted(made) == [{"state": "pending", "context": CONTEXT, "description": "fix list"}]


@pytest.mark.parametrize(
    ("comments", "reason"),
    [
        ([], "no verdict"),
        ([cleared(OLD)], "no verdict for this head"),
        ([comment(f"Verdict: rejected {HEAD}", at=6)], "rejected"),
    ],
)
def test_a_head_without_a_clearing_verdict_is_pending_with_the_reason(tmp_path, comments, reason):
    """REQ-046: brief #853 answer 1 (`pending` with the reason otherwise)."""
    proc, made = status_run(tmp_path, comments=comments)
    assert proc.stdout.strip() == line(f"pending {reason}"), proc.stdout + proc.stderr
    assert [p["description"] for p in posted(made)] == [reason]


def test_a_missing_spec_approval_is_pending_naming_the_spec(tmp_path):
    """REQ-046: brief #853 answer 1 (`approve SPEC-nnnn`)."""
    pull = {**world()["pull"], "body": "Approval: SPEC-0039\n"}
    proc, made = status_run(tmp_path, pull=pull, comments=[cleared()])
    assert proc.stdout.strip() == line("pending approve SPEC-0039"), proc.stdout + proc.stderr
    assert posted(made)[0]["state"] == "pending"


def test_an_approval_that_is_in_gives_success(tmp_path):
    """REQ-046: brief #853 answer 1 (its `Approve:` lines are in)."""
    people = f'version: 1\nspec_approvers: ["@{OWNER}"]\n'
    root = repo(tmp_path, toml(ON), reviewers_yaml=people)
    pull = {**world()["pull"], "body": "Approval: SPEC-0039\n"}
    approval = comment(f"Approve: {HEAD} SPEC-0039", at=6)
    bin_dir, log = fake_gh(tmp_path, pull=pull, comments=[cleared(), approval])
    proc = run(root, bin_dir, "--status", "--pr", "7", "--sha", HEAD)
    assert proc.stdout.strip() == line("success"), proc.stdout + proc.stderr
    assert posted(calls(log))[0]["state"] == "success"


@pytest.mark.parametrize(
    "name", [".github/workflows/merger.yml", "constitution/principles.md", "config/reviewers.yaml"]
)
def test_an_owner_only_path_is_pending_owner_merge(tmp_path, name):
    """REQ-046: brief #853 answer 6 (a workflow change gets `pending owner merge`)."""
    files = [{"filename": name, "status": "modified", "patch": "+x"}]
    proc, made = status_run(tmp_path, comments=[cleared()], files=files)
    assert proc.stdout.strip() == line("pending owner merge"), proc.stdout + proc.stderr
    assert posted(made)[0]["description"] == "owner merge"


def test_a_release_is_pending_owner_merge(tmp_path):
    """REQ-046: brief #853 answer 1 (a person merges it, as rule 5 says)."""
    files = [{"filename": "agk.toml", "status": "modified", "patch": '+version = "9.9.9"'}]
    proc, _ = status_run(tmp_path, comments=[cleared()], files=files)
    assert proc.stdout.strip() == line("pending owner merge"), proc.stdout + proc.stderr


def test_another_hold_of_rule_five_is_pending_with_its_rule(tmp_path):
    """REQ-046: brief #853 answer 1 (the same reading as the merge)."""
    pull = {**world()["pull"], "labels": [{"name": "agk:hold"}]}
    proc, made = status_run(tmp_path, pull=pull, comments=[cleared()])
    assert proc.stdout.strip() == line("pending hold label (rule 5)"), proc.stdout + proc.stderr
    assert posted(made)[0]["state"] == "pending"


def status_on_reprove(tmp_path, head_files, main_files, flow=""):
    root, head = reprove_world(tmp_path, head_files, main_files, flow=flow)
    pull = {**world()["pull"], "head": {"sha": head}}
    commits = [{"sha": head, "commit": {"message": "Example change\n"}}]
    bin_dir, log = fake_gh(tmp_path, pull=pull, comments=[cleared(head, extra="")], commits=commits)
    proc = run(root, bin_dir, "--status", "--pr", "7", "--sha", head)
    return proc, calls(log), head


def test_a_re_prove_head_gets_pending_re_prove_naming_the_file(tmp_path):
    """REQ-046: brief #853 answer 6 (a re-prove head gets `pending re-prove`)."""
    proc, made, head = status_on_reprove(tmp_path, {SHARED: FIRST}, [{SHARED: LAST}])
    expected = f"merge-cleared #7 {head[:12]}: status pending re-prove {SHARED}"
    assert proc.stdout.strip() == expected, proc.stdout + proc.stderr
    assert posted(made)[0]["description"] == f"re-prove {SHARED}"


def test_a_head_clear_of_main_is_not_in_the_re_prove_state(tmp_path):
    """REQ-046: brief #853 answer 1 (the other file changed on main)."""
    proc, made, _ = status_on_reprove(tmp_path, {SHARED: FIRST}, [{"docs/example.md": "b\n"}])
    assert proc.stdout.strip().endswith("status success"), proc.stdout + proc.stderr
    assert posted(made)[0]["state"] == "success"


def test_the_description_fits_github_s_limit(tmp_path):
    """REQ-046: GitHub refuses a status description over 140 characters (verify)."""
    name = "docs/" + "x" * 200 + ".md"
    proc, made, _ = status_on_reprove(tmp_path, {name: "a\n"}, [{name: "b\n"}])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(posted(made)[0]["description"]) == 140


# --- answer 1: a new push, and no duplicate -------------------------------------------------------


def test_a_new_push_has_no_status(tmp_path):
    """REQ-046: brief #853 answer 6 (an old verdict never clears a new head: nothing is set)."""
    pull = {**world()["pull"], "head": {"sha": OLD}}
    proc, made = status_run(tmp_path, pull=pull, comments=[cleared()])
    assert ": refused: head moved" in proc.stdout, proc.stdout + proc.stderr
    assert proc.returncode == 3
    assert posted(made) == []


def test_the_same_status_is_not_set_twice(tmp_path):
    """REQ-046: brief #853 answer 1 (a refresh that changes nothing sets nothing)."""
    same = [{"context": CONTEXT, "state": "success", "description": "cleared"}]
    proc, made = status_run(tmp_path, comments=[cleared()], commit_statuses=same)
    assert proc.stdout.strip() == line("success"), proc.stdout + proc.stderr
    assert posted(made) == []


def test_a_changed_status_is_set_again(tmp_path):
    """REQ-046: brief #853 answer 1 (the newest status of the context is the one compared)."""
    older = [
        {"context": "other", "state": "success", "description": "cleared"},
        {"context": CONTEXT, "state": "pending", "description": "fix list"},
        {"context": CONTEXT, "state": "success", "description": "cleared"},
    ]
    _, made = status_run(tmp_path, comments=[cleared()], commit_statuses=older)
    assert posted(made)[0]["state"] == "success"


def test_a_status_that_cannot_be_set_says_so(tmp_path):
    """REQ-046: a write that fails is reported, never read as done."""
    proc, _ = status_run(tmp_path, comments=[cleared()], status_fails=True)
    assert proc.returncode == 1
    assert proc.stdout.strip() == line("success") + ": the status cannot be set"


# --- answers 4 and 5: the modes -------------------------------------------------------------------


def test_local_mode_prints_the_state_and_sets_nothing(tmp_path):
    """REQ-046: brief #853 answer 5."""
    proc, made = status_run(tmp_path, main=toml(ON, local=True), comments=[cleared()])
    assert proc.stdout.strip() == line("success") + " (local mode: not set)", proc.stdout
    assert proc.returncode == 0
    assert posted(made) == []


def test_the_local_mode_record_issue_also_sets_nothing(tmp_path):
    """REQ-046: brief #853 answer 5 (local mode as rule 4 reads it)."""
    record = {"number": 42, "title": "Local mode since 2026-11-01", "body": "", "labels": []}
    issues = [AUTO_ISSUE, record]
    proc, made = status_run(tmp_path, comments=[comment(FIX_LIST, at=6)], issues=issues)
    assert proc.stdout.strip() == line("pending fix list") + " (local mode: not set)"
    assert posted(made) == []


def test_auto_merge_off_sets_nothing_and_names_the_setting(tmp_path):
    """REQ-046: AC1 (auto-merge is off unless the owner turns it on)."""
    proc, made = status_run(tmp_path, main=toml(""), comments=[cleared()])
    assert ": refused: " in proc.stdout and "auto_merge" in proc.stdout
    assert posted(made) == []


def test_the_merge_queue_replaces_the_re_prove_state(tmp_path):
    """REQ-046: brief #853 answer 4 (the re-prove rule reads the queue's result)."""
    flow = "merge_queue = true\n"
    proc, made, _ = status_on_reprove(tmp_path, {SHARED: FIRST}, [{SHARED: LAST}], flow=flow)
    assert proc.stdout.strip().endswith("status success"), proc.stdout + proc.stderr
    assert posted(made)[0]["state"] == "success"


def test_with_the_merge_queue_the_command_does_not_merge(tmp_path):
    """REQ-046: brief #853 answer 4 (the merger does not merge)."""
    root = repo(tmp_path, toml(ON + "merge_queue = true\n"))
    bin_dir, log = fake_gh(tmp_path, comments=[cleared()])
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert proc.stdout.strip().endswith("held: merge queue (setting flow.merge_queue)")
    assert proc.returncode == 3
    assert not any("PUT" in call for call in calls(log))


@pytest.mark.parametrize("value", ['"yes"', "1"])
def test_a_malformed_merge_queue_is_refused_naming_the_setting(tmp_path, value):
    """REQ-046: brief #853 answer 4 (a setting of the wrong kind, never its value)."""
    root = repo(tmp_path, toml(ON + f"merge_queue = {value}\n"))
    bin_dir, log = fake_gh(tmp_path, comments=[cleared()])
    proc = run(root, bin_dir, "--status", "--pr", "7", "--sha", HEAD)
    assert ": refused: " in proc.stdout and "setting: merge_queue" in proc.stdout
    assert value not in proc.stdout
    assert posted(calls(log)) == []


# --- the sweep refreshes --------------------------------------------------------------------------


def test_the_sweep_refreshes_the_status_of_a_cleared_head(tmp_path):
    """REQ-046: brief #853 answer 1 (the merger job refreshes it when main moves)."""
    root = repo(tmp_path, toml(ON))
    files = [{"filename": ".github/workflows/merger.yml", "status": "modified", "patch": "+x"}]
    bin_dir, log = fake_gh(tmp_path, comments=[cleared()], files=files)
    proc = run(root, bin_dir, "--sweep")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert [p["description"] for p in posted(calls(log))] == ["owner merge"]


def test_the_sweep_sets_no_status_on_a_head_that_is_not_cleared(tmp_path):
    """REQ-046: brief #853 answer 1 (no status read or write for every open pull request)."""
    root = repo(tmp_path, toml(ON))
    bin_dir, log = fake_gh(tmp_path, comments=[comment(FIX_LIST, at=6)])
    run(root, bin_dir, "--sweep")
    assert posted(calls(log)) == []


# --- answer 3: doctor -----------------------------------------------------------------------------


def strict_rule(strict: bool) -> list[dict]:
    parameters = {
        "strict_required_status_checks_policy": strict,
        "required_status_checks": [{"context": "governance"}],
    }
    return [{"rules": [{"type": "required_status_checks", "parameters": parameters}]}]


@pytest.mark.parametrize(
    ("flow", "strict", "status"),
    [
        ({"auto_merge": True}, False, "fail"),
        ({"auto_merge": True}, True, "ok"),
        ({}, False, "ok"),
        ({"auto_merge": False}, False, "ok"),
        ({"auto_merge": True, "merge_queue": True}, False, "ok"),
    ],
)
def test_doctor_reports_strict_off_only_where_it_matters(flow, strict, status):
    """REQ-046: brief #853 answer 3."""
    result = doctor_module.up_to_date_result(strict_rule(strict), {"flow": flow})
    assert result.status == status


def test_doctor_lists_the_check_as_a_warning():
    """REQ-046: brief #853 answer 3 (a warning: the owner's step follows the merge)."""
    assert doctor_module.CHECKS["ruleset-up-to-date"][0] == "warn"
    assert doctor_module.up_to_date_result(None, {"flow": {"auto_merge": True}}).status == (
        "cannot-check"
    )
    assert doctor_module.up_to_date_result(None, {}).status == "ok"
