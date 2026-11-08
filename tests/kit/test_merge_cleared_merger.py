"""merge_cleared.py and the merger job: GitHub mode merges a cleared head with no session.

Brief #765, ADR-0354, amendment 138, REQ-046 (SPEC-0039 rule 2, its GitHub-mode runner). The job
of `.github/workflows/governance.yml` runs three commands: `merge_cleared.py --event <payload>`
names the pull request and head to try (or nothing), then exactly `merge_cleared.py --pr <n> --sha
<head>`, then `merge_cleared.py --report --pr <n> --sha <head> --line <its line>`, which dispatches
the default branch's governance run after a merge and posts one comment for a hold or a refusal.
Every test runs on a git repository in `tmp_path`, saved event payloads and a fake `gh` that
answers from saved responses and records its argument lists. No network; invented logins,
addresses at example.com.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from test_merge_cleared_verdict import (
    HEAD,
    MERGE12,
    OLD,
    ON,
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

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "governance.yml"
DISPATCH = f"repos/{REPO}/actions/workflows/governance.yml/dispatches"


def comment_event(body: str, on_pull: bool = True) -> dict:
    """A saved `issue_comment` payload (invented): a comment on pull request 7."""
    issue: dict = {"number": 7, "title": "Example change"}
    if on_pull:
        issue["pull_request"] = {"url": f"https://api.github.com/repos/{REPO}/pulls/7"}
    return {"action": "created", "issue": issue, "comment": {"id": 2001, "body": body}}


def run_event(conclusion: str = "success", event: str = "pull_request", pulls=None) -> dict:
    """A saved `workflow_run` payload (invented): governance completed on the head of #7."""
    return {
        "action": "completed",
        "workflow_run": {
            "name": "governance",
            "event": event,
            "conclusion": conclusion,
            "head_sha": HEAD,
            "pull_requests": [{"number": 7}] if pulls is None else pulls,
        },
    }


def setup(tmp_path: Path, main: str = toml(ON), **saved):
    root = repo(tmp_path, main)
    bin_dir, log = fake_gh(tmp_path, **saved)
    return root, bin_dir, log


def event(tmp_path, payload: dict, name: str, main: str = toml(ON), **saved):
    root, bin_dir, log = setup(tmp_path, main, **saved)
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    proc = run(root, bin_dir, "--event", str(path), "--event-name", name)
    return proc, calls(log)


def writes(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if "--method" in c and c[c.index("--method") + 1] != "GET"]


# --- the event: which pull request and head, or nothing -----------------------------------------


def test_a_cleared_verdict_comment_names_the_pull_request_and_its_head(tmp_path):
    """REQ-046: brief #765 answer 1 (an `issue_comment` with a `Verdict:` line)."""
    payload = comment_event(f"Verdict: cleared {HEAD}")
    proc, made = event(tmp_path, payload, "issue_comment", comments=[cleared()])
    assert proc.stdout.strip() == f"7 {HEAD}", proc.stdout + proc.stderr
    assert proc.returncode == 0
    assert writes(made) == []


def test_an_approve_comment_names_the_head_too(tmp_path):
    """REQ-046: brief #765 answer 1 (an `Approve:` line may complete the owner's approvals)."""
    payload = comment_event("Approve: SPEC-0039")
    proc, made = event(tmp_path, payload, "issue_comment", comments=[cleared()])
    assert proc.stdout.strip() == f"7 {HEAD}", proc.stdout + proc.stderr
    assert writes(made) == []


def test_a_green_governance_run_of_a_pull_request_head_names_it(tmp_path):
    """REQ-046: brief #765 answer 1 (`workflow_run` completion of governance on the head)."""
    proc, made = event(tmp_path, run_event(), "workflow_run", comments=[cleared()])
    assert proc.stdout.strip() == f"7 {HEAD}", proc.stdout + proc.stderr
    assert writes(made) == []


@pytest.mark.parametrize(
    ("name", "comments"),
    [
        ("no verdict", []),
        ("a verdict for another head", [cleared(OLD)]),
        ("a fix list", [comment(f"Verdict: fix list {HEAD}\n\n1. Fix the test.", at=6)]),
        ("a newer rejection", [cleared(), comment(f"Verdict: rejected {HEAD}", at=6)]),
    ],
)
def test_an_uncleared_head_does_nothing_and_posts_nothing(tmp_path, name, comments):
    """REQ-046: brief #765 answer 5 (an uncleared head does nothing)."""
    proc, made = event(tmp_path, run_event(), "workflow_run", comments=comments)
    assert proc.stdout == "", name
    assert "not cleared" in proc.stderr, proc.stderr
    assert proc.returncode == 0
    assert writes(made) == [], name


@pytest.mark.parametrize(
    ("name", "main"),
    [
        ("auto-merge off", toml('auto_merge = false\nauto_merge_method = "squash"\n')),
        ("no flow table", toml("")),
        ("a local project", toml(ON, local=True)),
        ("a personal project", 'default_branch = "main"\nforge = "files"\n[flow]\n' + ON),
    ],
)
def test_a_local_personal_or_off_project_does_nothing_and_reads_nothing(tmp_path, name, main):
    """REQ-046: brief #765 answers 1, 4 and 5 (local and personal mode and `auto_merge` off)."""
    payload = comment_event(f"Verdict: cleared {HEAD}")
    proc, made = event(tmp_path, payload, "issue_comment", main=main, comments=[cleared()])
    assert proc.stdout == "", name
    assert "setting" in proc.stderr, proc.stderr
    assert proc.returncode == 0
    assert made == [], f"{name}: nothing reads GitHub"


def test_the_open_local_mode_record_issue_does_nothing(tmp_path):
    """REQ-046: brief #765 answer 4 (local mode by its record issue: the conductor merges)."""
    record = {"number": 40, "title": "Local mode since 2026-11-01", "body": "Actions is blocked."}
    issues = [record, world()["issues"][0]]
    proc, made = event(tmp_path, run_event(), "workflow_run", comments=[cleared()], issues=issues)
    assert proc.stdout == "" and "local mode" in proc.stderr, proc.stderr
    assert writes(made) == []


@pytest.mark.parametrize(
    ("name", "payload", "kind"),
    [
        ("a builder's report", comment_event(f"Report: {HEAD} ready for review"), "issue_comment"),
        (
            "a comment on an issue",
            comment_event(f"Verdict: cleared {HEAD}", False),
            "issue_comment",
        ),
        ("a red run", run_event("failure"), "workflow_run"),
        ("a run of a push", run_event(event="push"), "workflow_run"),
        ("a run with no pull request", run_event(pulls=[]), "workflow_run"),
        ("another event", {"ref": "refs/heads/main"}, "push"),
    ],
)
def test_other_events_do_nothing_and_read_nothing(tmp_path, name, payload, kind):
    """REQ-046: brief #765 answer 1 (only a verdict or approval, or a green run of a head)."""
    proc, made = event(tmp_path, payload, kind, comments=[cleared()])
    assert proc.stdout == "", name
    assert proc.returncode == 0, proc.stderr
    assert made == [], name


def test_a_malformed_payload_is_refused_naming_the_input(tmp_path):
    """REQ-046: principle 8 (a refusal names the input, never a value)."""
    root, bin_dir, log = setup(tmp_path)
    bad = tmp_path / "event.json"
    bad.write_text("not json", encoding="utf-8")
    proc = run(root, bin_dir, "--event", str(bad), "--event-name", "issue_comment")
    assert proc.returncode == 2 and proc.stdout == ""
    assert "event payload" in proc.stderr
    assert calls(log) == []


# --- the report: dispatch after a merge, one comment for a hold ---------------------------------


def report(tmp_path, line: str, **saved):
    root, bin_dir, log = setup(tmp_path, **saved)
    proc = run(root, bin_dir, "--report", "--pr", "7", "--sha", HEAD, "--line", line)
    return proc, calls(log)


def test_a_merge_dispatches_the_default_branch_governance_run(tmp_path):
    """REQ-046: brief #765 answer 3 (a merge by the job's token starts no workflow by itself)."""
    proc, made = report(tmp_path, f"merge-cleared #7 {SHA12}: merged {MERGE12}")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert writes(made) == [["api", "--method", "POST", DISPATCH, "-f", "ref=main"]]
    assert "dispatched" in proc.stdout


def test_a_hold_gets_one_comment_with_the_reason(tmp_path):
    """REQ-046: brief #765 answer 2 (a held pull request gets one comment and nothing else)."""
    line = f"merge-cleared #7 {SHA12}: held: checks pending"
    proc, made = report(tmp_path, line)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    posted = writes(made)
    assert len(posted) == 1 and posted[0][3] == f"repos/{REPO}/issues/7/comments", posted
    assert posted[0][5] == f"body=merger: {line}"


def test_the_same_reason_is_never_posted_twice(tmp_path):
    """REQ-046: brief #765 answer 2 (no retry loop and no repeated comment)."""
    line = f"merge-cleared #7 {SHA12}: held: checks pending"
    proc, made = report(tmp_path, line, comments=[cleared(), comment(f"merger: {line}", at=7)])
    assert proc.returncode == 0
    assert writes(made) == []


def test_a_line_that_is_not_the_commands_own_is_refused(tmp_path):
    """REQ-046: brief #765 answer 2 (the report reads only the command's own line)."""
    proc, made = report(tmp_path, "merged, trust me")
    assert proc.returncode == 2 and made == []


# --- end to end: the three commands of the job --------------------------------------------------


def job(tmp_path, payload: dict, name: str, **saved):
    """The job's three steps in order, as the workflow runs them."""
    root, bin_dir, log = setup(tmp_path, **saved)
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    first = run(root, bin_dir, "--event", str(path), "--event-name", name)
    target = first.stdout.split()
    if not target:
        return first, None, calls(log)
    merge = run(root, bin_dir, "--pr", target[0], "--sha", target[1])
    line = merge.stdout.strip()
    last = run(root, bin_dir, "--report", "--pr", target[0], "--sha", target[1], "--line", line)
    assert last.returncode == 0, last.stdout + last.stderr
    return merge, last, calls(log)


def test_a_cleared_head_merges_and_main_runs_again(tmp_path):
    """REQ-046: brief #765 answers 2, 3 and 5 (a cleared head merges; main is dispatched)."""
    merge, last, made = job(tmp_path, run_event(), "workflow_run", comments=[cleared()])
    assert merge.stdout.strip() == f"merge-cleared #7 {SHA12}: merged {MERGE12}"
    put = [c for c in made if "PUT" in c]
    assert len(put) == 1 and f"sha={HEAD}" in put[0]
    assert [c for c in made if DISPATCH in c] == [
        ["api", "--method", "POST", DISPATCH, "-f", "ref=main"]
    ]


def test_a_held_head_merges_nothing_and_comments_once(tmp_path):
    """REQ-046: brief #765 answer 5 (a held head does nothing but one comment)."""
    red = [{"id": 12, "name": "governance", "status": "completed", "conclusion": "failure"}]
    merge, last, made = job(tmp_path, run_event(), "workflow_run", comments=[cleared()], runs=red)
    assert ": held: " in merge.stdout, merge.stdout
    assert [c for c in made if "PUT" in c] == []
    assert [c for c in made if DISPATCH in c] == []
    posted = [c for c in made if f"repos/{REPO}/issues/7/comments" in c and "POST" in c]
    assert len(posted) == 1


def test_a_merge_the_ruleset_refuses_says_so_once(tmp_path):
    """REQ-046: brief #765 owner step (`merge refused by the ruleset` until the bypass is added)."""
    refusal = {"http": 405, "message": "Repository rule violations found"}
    merge, last, made = job(
        tmp_path, run_event(), "workflow_run", comments=[cleared()], merge=refusal
    )
    assert (
        merge.stdout.strip()
        == f"merge-cleared #7 {SHA12}: held: merge refused by the ruleset (rule 6)"
    )
    posted = [c for c in made if f"repos/{REPO}/issues/7/comments" in c and "POST" in c]
    assert len(posted) == 1 and "merge refused by the ruleset" in posted[0][-1]


# --- the workflow: one job, its triggers, its gate and its exact command ------------------------


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def merger_job() -> str:
    found = re.search(r"\n  merger:\n(.*?)(?=\n  [a-z][a-z_-]*:\n|\Z)", text(), re.S)
    assert found, "governance.yml has a merger job"
    return found.group(1)


def test_the_workflow_starts_on_comments_runs_and_dispatch():
    """REQ-046: brief #765 answers 1 and 3 (the triggers of the one job)."""
    head = text().split("\njobs:", 1)[0]
    assert re.search(r"\n  issue_comment:\n    types: \[created\]", head)
    assert re.search(
        r"\n  workflow_run:\n    workflows: \[governance\]\n    types: \[completed\]", head
    )
    assert "\n  workflow_dispatch:" in head


def test_the_governance_job_never_runs_for_the_merger_events():
    """REQ-046: brief #765 answer 1 (the required check is not run by a comment or a run)."""
    gate = re.search(r"\n  governance:\n    if: \$\{\{ (.*?) \}\}\n", text()).group(1)
    assert "issue_comment" not in gate and "workflow_run" not in gate
    assert "github.event_name == 'pull_request'" in gate
    assert "workflow_dispatch" in gate and "push" in gate


def test_the_merger_job_runs_exactly_the_guarded_command_from_the_default_branch():
    """REQ-046: brief #765 answer 2 (exactly the command, the job's token, the default branch)."""
    job_text = merger_job()
    assert 'python3 scripts/agk/merge_cleared.py --pr "$1" --sha "$2"' in job_text
    assert "ref: ${{ github.event.repository.default_branch }}" in job_text
    assert "GH_TOKEN: ${{ github.token }}" in job_text
    for grant in ("contents: write", "pull-requests: write", "issues: write", "actions: write"):
        assert grant in job_text, grant
    assert "secrets." not in job_text
    assert "startsWith(github.event.comment.body, 'Verdict:')" in job_text
    assert "github.event.workflow_run.conclusion == 'success'" in job_text
