"""merge_cleared.py and the merger job: GitHub mode merges a cleared head with no session.

Brief #765, ADR-0354, amendment 139, REQ-046 (SPEC-0039 rule 2, its GitHub-mode runner). The job
of `.github/workflows/merger.yml`, started only from the default branch, runs three commands:
`merge_cleared.py --event <payload>` names the pull request and head to try (or nothing), then
exactly `merge_cleared.py --pr <n> --sha <head>`, its one merge call under the secret
`AGK_MERGE_TOKEN` of the `merge` environment, then `merge_cleared.py --report --pr <n> --sha <head>
--line <its line>`, which posts one comment for a hold or a refusal. With no secret the job posts
`merge needs AGK_MERGE_TOKEN or the owner's tap` once and does nothing else.
Every test runs on a git repository in `tmp_path`, saved event payloads and a fake `gh` that
answers from saved responses and records its argument lists. No network; invented logins,
addresses at example.com.
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - the workflow step's own text, on a saved world
import textwrap
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

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "merger.yml"
MERGE_ENV = "AGK_MERGE_TOKEN"
MERGE_VALUE = "example-merge-value"
JOB_VALUE = "example-job-value"
NEEDS_KEY = "merge needs AGK_MERGE_TOKEN or the owner's tap"


def comment_event(body: str, on_pull: bool = True) -> dict:
    """A saved `issue_comment` payload (invented): a comment on pull request 7."""
    issue: dict = {"number": 7, "title": "Example change"}
    if on_pull:
        issue["pull_request"] = {"url": f"https://api.github.com/repos/{REPO}/pulls/7"}
    return {"action": "created", "issue": issue, "comment": {"id": 2001, "body": body}}


def run_event(
    conclusion: str = "success", event: str = "pull_request", pulls=None, name: str = "proof"
) -> dict:
    """A saved `workflow_run` payload (invented): a required run completed on the head of #7."""
    return {
        "action": "completed",
        "workflow_run": {
            "name": name,
            "event": event,
            "conclusion": conclusion,
            "head_sha": HEAD,
            "pull_requests": [{"number": 7}] if pulls is None else pulls,
        },
    }


def pull_event() -> dict:
    """A saved `pull_request` payload (invented): an event that never starts the job."""
    return {"action": "synchronize", "pull_request": {"number": 7, "head": {"sha": HEAD}}}


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


@pytest.mark.parametrize("workflow", ["governance", "proof"])
def test_a_green_required_run_of_a_pull_request_head_names_it(tmp_path, workflow):
    """REQ-046: brief #765 answer 1 (`workflow_run` completion of either required run)."""
    payload = run_event(name=workflow)
    proc, made = event(tmp_path, payload, "workflow_run", comments=[cleared()])
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
        ("a pull request's own run", pull_event(), "pull_request"),
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


# --- the report: one comment for a hold, nothing after a merge ----------------------------------


def report(tmp_path, line: str, **saved):
    root, bin_dir, log = setup(tmp_path, **saved)
    proc = run(root, bin_dir, "--report", "--pr", "7", "--sha", HEAD, "--line", line)
    return proc, calls(log)


@pytest.mark.parametrize("secret", [True, False])
def test_a_merge_posts_nothing_and_starts_no_run(tmp_path, monkeypatch, secret):
    """REQ-046: verdict on f3acd19 item 2 (the merge's own push starts the default branch's run)."""
    if secret:
        monkeypatch.setenv(MERGE_ENV, MERGE_VALUE)
    else:
        monkeypatch.delenv(MERGE_ENV, raising=False)
    proc, made = report(tmp_path, f"merge-cleared #7 {SHA12}: merged {MERGE12}")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert writes(made) == []


def test_a_hold_gets_one_comment_with_the_reason(tmp_path):
    """REQ-046: brief #765 answer 2 (a held pull request gets one comment and nothing else)."""
    line = f"merge-cleared #7 {SHA12}: held: the default branch is red (rule 5)"
    proc, made = report(tmp_path, line)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    posted = writes(made)
    assert len(posted) == 1 and posted[0][3] == f"repos/{REPO}/issues/7/comments", posted
    assert posted[0][5] == f"body=merger: {line}"


def test_checks_pending_posts_nothing(tmp_path):
    """REQ-046: brief #765 answer 2 (the other required run's end is the next try)."""
    proc, made = report(tmp_path, f"merge-cleared #7 {SHA12}: held: checks pending")
    assert proc.returncode == 0 and writes(made) == []


def test_the_same_reason_is_never_posted_twice(tmp_path):
    """REQ-046: brief #765 answer 2 (no retry loop and no repeated comment)."""
    line = f"merge-cleared #7 {SHA12}: held: the default branch is red (rule 5)"
    proc, made = report(tmp_path, line, comments=[cleared(), comment(f"merger: {line}", at=7)])
    assert proc.returncode == 0
    assert writes(made) == []


def test_no_secret_posts_the_one_line_once(tmp_path):
    """REQ-046: the `Correction:` on brief #765 (the test for a missing secret, answer 5)."""
    root, bin_dir, log = setup(tmp_path)
    proc = run(root, bin_dir, "--report", "--pr", "7", "--no-secret")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert writes(calls(log)) == [
        ["api", "--method", "POST", f"repos/{REPO}/issues/7/comments", "-f", f"body={NEEDS_KEY}"]
    ]


def test_no_secret_says_it_never_twice(tmp_path):
    """REQ-046: the `Correction:` on brief #765 (one line, and nothing else)."""
    root, bin_dir, log = setup(tmp_path, comments=[cleared(), comment(NEEDS_KEY, at=7)])
    proc = run(root, bin_dir, "--report", "--pr", "7", "--no-secret")
    assert proc.returncode == 0
    assert writes(calls(log)) == []


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


def test_a_held_head_merges_nothing_and_comments_once(tmp_path):
    """REQ-046: brief #765 answer 5 (a held head does nothing but one comment)."""
    red = [{"id": 12, "name": "governance", "status": "completed", "conclusion": "failure"}]
    merge, last, made = job(tmp_path, run_event(), "workflow_run", comments=[cleared()], runs=red)
    assert ": held: " in merge.stdout, merge.stdout
    assert [c for c in made if "PUT" in c] == []
    posted = [c for c in made if f"repos/{REPO}/issues/7/comments" in c and "POST" in c]
    assert len(posted) == 1


def tokens(tmp_path: Path) -> list[list]:
    """Each `gh` call of the stub as [method, path, the GH_TOKEN it ran with]."""
    lines = (tmp_path / "gh-calls.jsonl.token").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_the_merge_call_alone_runs_under_the_merge_secret(tmp_path, monkeypatch):
    """REQ-046: the `Correction:` on brief #765 (the job merges with `AGK_MERGE_TOKEN`)."""
    monkeypatch.setenv(MERGE_ENV, MERGE_VALUE)
    monkeypatch.setenv("GH_TOKEN", JOB_VALUE)
    merge, last, made = job(tmp_path, run_event(), "workflow_run", comments=[cleared()])
    assert merge.stdout.strip() == f"merge-cleared #7 {SHA12}: merged {MERGE12}"
    seen = tokens(tmp_path)
    merges = [c for c in seen if c[0] == "PUT"]
    assert merges == [["PUT", f"repos/{REPO}/pulls/7/merge", MERGE_VALUE]]
    assert all(c[2] == JOB_VALUE for c in seen if c[0] != "PUT"), seen
    assert [c for c in writes(made) if c[3].startswith(f"repos/{REPO}/actions/")] == []


def test_without_the_merge_secret_the_command_keeps_the_callers_login(tmp_path, monkeypatch):
    """REQ-046: brief #765 answer 4 (the conductor's own run is unchanged)."""
    monkeypatch.delenv(MERGE_ENV, raising=False)
    monkeypatch.setenv("GH_TOKEN", JOB_VALUE)
    job(tmp_path, run_event(), "workflow_run", comments=[cleared()])
    assert [c[2] for c in tokens(tmp_path) if c[0] == "PUT"] == [JOB_VALUE]


def test_the_pre_merge_tests_never_receive_the_merge_secret(tmp_path, monkeypatch):
    """REQ-046: the `Correction:` on brief #765 (no merged code sees the secret)."""
    monkeypatch.setenv(MERGE_ENV, MERGE_VALUE)
    job(tmp_path, run_event(), "workflow_run", comments=[cleared()])
    made = (tmp_path / "make-calls.jsonl").read_text(encoding="utf-8").splitlines()
    assert made, "the governance runs were recorded"
    assert all(MERGE_ENV not in json.loads(line)["env"] for line in made)


def test_a_merge_the_ruleset_refuses_says_so_once(tmp_path):
    """REQ-046: rule 6 (`merge refused by the ruleset`, when the merge secret cannot pass it)."""
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


def test_the_workflow_starts_only_on_comments_and_on_the_two_required_runs():
    """REQ-046: verdict on f3acd19 item 1 (no pull request's run can start this file)."""
    head = text().split("\njobs:", 1)[0]
    block = re.search(r"\non:\n(.*?)\n(?=[a-z])", head, re.S).group(1)
    # brief #797 answer 3 (ADR-0373): the sweep's two starts, neither from a pull request's run
    assert re.findall(r"^  ([a-z_]+):", block, re.M) == [
        "issue_comment",
        "workflow_run",
        "status",  # brief #853 (ADR-0387): the verdict status, also never from a pull request's run
        "schedule",
        "workflow_dispatch",
    ]
    assert re.search(r"\n  issue_comment:\n    types: \[created, edited\]", head)  # brief #836
    assert re.search(
        r"\n  workflow_run:\n    workflows: \[governance, proof\]\n    types: \[completed\]", head
    )
    assert "needs:" not in merger_job()


def test_the_secret_comes_from_the_merge_environment():
    """REQ-046: verdict on f3acd19 item 1 (an environment limited to the default branch)."""
    assert re.search(r"^    environment: merge$", merger_job(), re.M)


def test_the_governance_workflow_knows_nothing_of_the_merger():
    """REQ-046: verdict on f3acd19 items 1 and 2 (no start or secret in a governance run)."""
    governance = (WORKFLOWS / "governance.yml").read_text(encoding="utf-8")
    for word in ("merger", MERGE_ENV, "issue_comment:", "workflow_run:", "workflow_dispatch:"):
        assert word not in governance, word


def test_the_merger_is_the_only_workflow_that_names_the_secret():
    """REQ-046: the `Correction:` on brief #765 (the job reads it, nothing else)."""
    named = [p.name for p in sorted(WORKFLOWS.glob("*.yml")) if MERGE_ENV in p.read_text("utf-8")]
    assert named == ["merger.yml"]


def test_the_job_token_may_write_only_comments_and_statuses():
    """REQ-046: verdict on f3acd19 item 2 (every merge is the secret's), and brief #853 answer 1
    (ADR-0387: `statuses: write` for the verdict status)."""
    head = text().split("\njobs:", 1)[0]
    block = re.search(r"\npermissions:\n((?:  [a-z-]+: [a-z]+\n)+)", head).group(1)
    assert sorted(block.split("\n")[:-1]) == [
        "  actions: read",
        "  checks: read",
        "  contents: read",
        "  issues: write",
        "  pull-requests: read",
        "  statuses: write",
    ]
    assert "permissions:" not in merger_job()


def test_the_merger_job_runs_exactly_the_guarded_command_from_the_default_branch():
    """REQ-046: brief #765 answer 2 (exactly the command, the default branch)."""
    job_text = merger_job()
    assert 'python3 scripts/agk/merge_cleared.py --pr "$1" --sha "$2"' in job_text
    assert '|| { echo "merger: no target could be read"; exit 0; }' in job_text
    assert "ref: ${{ github.event.repository.default_branch }}" in job_text
    assert "GH_TOKEN: ${{ github.token }}" in job_text
    assert set(re.findall(r"secrets\.\w+", job_text)) == {"secrets.AGK_MERGE_TOKEN"}
    # with the one above, every command ends green; brief #972 adds the removal line's step
    assert job_text.count(' || echo "merger: ') == 5
    assert "startsWith(github.event.comment.body, 'Verdict:')" in job_text
    # brief #1116 (ADR-0476): a green run starts the job through the router's dispatch with `pr`
    assert "github.event.workflow_run.event == 'pull_request'" not in job_text
    assert "(github.event_name == 'workflow_dispatch' && github.event.inputs.pr != '')" in job_text


def step_block(name: str) -> str:
    """The text of the merger job's step NAME."""
    found = re.search(rf"\n      - name: {name}\n(.*?)(?=\n      - |\Z)", merger_job(), re.S)
    assert found, name
    return found.group(1)


def test_only_the_merge_step_holds_the_secret_and_pip_runs_without_it():
    """REQ-046: the `Correction:` on brief #765 (the secret reaches one step, no install)."""
    find, merge = step_block("Find a cleared pull request"), step_block(
        "Merge a cleared pull request"
    )
    assert "secrets." not in find
    assert "pip install" in find and "pip install" not in merge
    assert f"{MERGE_ENV}: ${{{{ secrets.{MERGE_ENV} }}}}" in merge
    assert "if: ${{ steps.find.outputs.target != '' }}" in merge


def merge_step(tmp_path: Path, secret: str, **saved):
    """The merge step's own `run:` text under bash, on the saved world, as the job runs it."""
    root, bin_dir, log = setup(tmp_path, **saved)
    (root / "scripts").symlink_to(WORKFLOW.parents[2] / "scripts")
    script = textwrap.dedent(step_block("Merge a cleared pull request").split("run: |\n", 1)[1])
    temp = tmp_path / "temp"
    temp.mkdir()
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}",
        TMPDIR=str(temp),
        GH_TOKEN=JOB_VALUE,
        TARGET=f"7 {HEAD}",
    )
    env[MERGE_ENV] = secret
    proc = subprocess.run(  # nosec B603 B607 - the workflow's fixed step text, no network
        ["bash", "-e", "-c", script], cwd=root, capture_output=True, text=True, env=env
    )
    return proc, calls(log)


def test_the_step_with_no_secret_posts_the_one_line_and_never_merges(tmp_path):
    """REQ-046: the `Correction:` on brief #765 (the workflow's own step, answer 5)."""
    proc, made = merge_step(tmp_path, "", comments=[cleared()])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert writes(made) == [
        ["api", "--method", "POST", f"repos/{REPO}/issues/7/comments", "-f", f"body={NEEDS_KEY}"]
    ]


def test_the_step_with_the_secret_merges_the_named_head(tmp_path):
    """REQ-046: the `Correction:` on brief #765 (one merge, under the secret)."""
    proc, made = merge_step(tmp_path, MERGE_VALUE, comments=[cleared()])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"merge-cleared #7 {SHA12}: merged {MERGE12}" in proc.stdout, proc.stdout + proc.stderr
    assert len([c for c in made if "PUT" in c]) == 1
    assert [c[2] for c in tokens(tmp_path) if c[0] == "PUT"] == [MERGE_VALUE]
