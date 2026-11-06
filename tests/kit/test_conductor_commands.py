"""conductor.py watch and sweep: the conductor's routines as kit commands (brief #643 build (a)).

REQ-037. `watch` ends on any builder `Question:` or `Report:` on an open brief or an open pull
request (conductor catch log row 1); `sweep` prints every open pull request by what it waits for,
an unanswered question or report older than `conductor_late_minutes` marked `LATE` (row 13). A
`gh` stub serves saved copies of the GitHub responses; no network, GET only, nothing written.
REQ-041 (brief #669, ADR-0322): `sweep` lists a taken brief with no branch, no pull request and
no post after its take, older than `silent_minutes`, as `SILENT`."""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import timedelta

import pytest
from test_session import REPO, SCRIPTS, SHA, Stub, clean_env, comment, iso

OTHER = "b" * 40
SHORT = SHA[:7]
GREEN = [{"id": 1, "name": "proof", "status": "completed", "conclusion": "success"}]
RUNNING = [{"id": 1, "name": "proof", "status": "in_progress", "conclusion": None}]
RED = [{"id": 1, "name": "proof", "status": "completed", "conclusion": "failure"}]


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write(
        "config/reviewers.yaml",
        "version: 1\nverdict_authors: [boss]\nspec_approvers: [owner]\n",
    )
    repo.write("agk.toml", "[flow]\nconductor_poll_seconds = 1\n")
    stub.serve(f"repos/{REPO}", {"default_branch": "main"})
    stub.serve(f"repos/{REPO}/actions/runs", {"workflow_runs": []})
    stub.serve(f"repos/{REPO}/issues", [])
    stub.serve(f"repos/{REPO}/pulls", [])
    return repo


def run(proj, stub, *args: str):
    env = clean_env()
    env.update(PATH=f"{stub.bin}:{env['PATH']}", GH_STUB_DIR=str(stub.dir))
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "conductor.py"), *args],
        cwd=proj.root,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def ago(minutes: int) -> str:
    return iso(timedelta(minutes=-minutes))


def pr(n: int, head: str = SHA, draft: bool = False, body: str = "Brief: #9\n") -> dict:
    return {
        "number": n, "draft": draft, "user": {"login": "builder"}, "head": {"sha": head},
        "labels": [], "body": body, "created_at": ago(90), "mergeable_state": "clean",
    }  # fmt: skip


def serve_pr(stub, item: dict, comments: list, checks: list | None = None) -> None:
    stub.serve(f"repos/{REPO}/pulls", [item])
    stub.serve(f"repos/{REPO}/issues/{item['number']}/comments", comments)
    head = item["head"]["sha"]
    runs = GREEN if checks is None else checks
    stub.serve(f"repos/{REPO}/commits/{head}/check-runs", {"check_runs": runs})
    stub.serve(f"repos/{REPO}/commits/{head}/status", {"state": "success", "statuses": []})


def sweep(proj, stub) -> list[str]:
    out = run(proj, stub, "sweep")
    assert out.returncode == 0, out.stdout + out.stderr
    assert all(c[0] == "GET" for c in stub.calls())
    return out.stdout.splitlines()


def verdict(kind: str, sha: str = SHA, minutes: int = 20) -> dict:
    return comment(5, "boss", f"Verdict: {kind} {sha}\n\n1. A finding.", ago(minutes))


# --- sweep: one fixture per state -------------------------------------------------------------


@pytest.mark.parametrize(
    ("item", "comments", "checks", "state"),
    [
        (pr(7, draft=True), [], None, "draft"),
        (pr(7), [], None, "ready: no verdict"),
        (pr(7), [verdict("fix list")], None, f"fix list on {SHORT}"),
        (pr(7), [verdict("cleared")], None, f"cleared on {SHORT}"),
        (pr(7, head=OTHER), [verdict("cleared")], None, "cleared, head moved"),
        (pr(7, head=OTHER), [verdict("fix list")], None, "ready: no verdict"),
        (pr(7), [], RUNNING, "checks pending"),
        (pr(7), [verdict("cleared")], RED, "red"),
        (
            pr(7, body="Brief: #9\nApproval: SPEC-0042\n"),
            [verdict("cleared")],
            None,
            f"waiting: Approve SPEC-0042 at {SHORT}",
        ),
    ],
)
def test_sweep_names_each_state(proj, stub, item, comments, checks, state):
    serve_pr(stub, item, comments, checks)
    lines = sweep(proj, stub)
    assert lines[0] == f"#7 {item['head']['sha'][:7]} {state} 1h"


def test_sweep_counts_an_approval_of_the_head(proj, stub):
    item = pr(7, body="Brief: #9\nApproval: SPEC-0042\n")
    approve = comment(6, "owner", f"Approve: {SHA} SPEC-0042", ago(10))
    serve_pr(stub, item, [verdict("cleared"), approve])
    assert sweep(proj, stub)[0] == f"#7 {SHORT} cleared on {SHORT} 1h"


def test_sweep_marks_an_unanswered_question_and_late(proj, stub):
    asked = comment(6, "builder", "Question: Q-9-2 which file?", ago(45))
    serve_pr(stub, pr(7), [verdict("fix list", minutes=60), asked])
    assert sweep(proj, stub)[0] == f"#7 {SHORT} blocked: Question Q-9-2 unanswered 45m LATE"


def test_sweep_a_fresh_question_is_not_late(proj, stub):
    asked = comment(6, "builder", "Question: Q-9-2 which file?", ago(5))
    serve_pr(stub, pr(7), [asked])
    assert sweep(proj, stub)[0] == f"#7 {SHORT} blocked: Question Q-9-2 unanswered 5m"


def test_sweep_an_answered_question_does_not_block(proj, stub):
    asked = comment(6, "builder", "Question: Q-9-2 which file?", ago(45))
    serve_pr(stub, pr(7), [asked, verdict("fix list", minutes=30)])
    assert sweep(proj, stub)[0] == f"#7 {SHORT} fix list on {SHORT} 1h"


def test_sweep_marks_an_old_unanswered_report_late(proj, stub):
    report = comment(6, "builder", f"Report: {SHORT} ready for review", ago(40))
    serve_pr(stub, pr(7), [report])
    assert sweep(proj, stub)[0] == f"#7 {SHORT} ready: no verdict 1h LATE"


def test_sweep_the_late_threshold_is_a_setting(proj, stub):
    proj.write("agk.toml", "[flow]\nconductor_late_minutes = 60\n")
    report = comment(6, "builder", f"Report: {SHORT} ready for review", ago(40))
    serve_pr(stub, pr(7), [report])
    assert sweep(proj, stub)[0] == f"#7 {SHORT} ready: no verdict 1h"


def test_sweep_reports_the_default_branch_and_a_red_issue(proj, stub):
    stub.serve(
        f"repos/{REPO}/actions/runs",
        {"workflow_runs": [{"head_sha": OTHER, "status": "completed", "conclusion": "failure"}]},
    )
    red = {
        "number": 50, "title": "The default branch is red",
        "user": {"login": "github-actions[bot]"}, "body": "Advances: none\nPriority: 0\n",
    }  # fmt: skip
    stub.serve(f"repos/{REPO}/issues", [red])
    lines = sweep(proj, stub)
    assert lines == ["no open pull request", "main: failure at bbbbbbb", "red-branch issue: #50"]


def test_sweep_fails_when_github_cannot_be_read(proj, stub):
    stub.serve(f"repos/{REPO}/pulls", "FAIL")
    out = run(proj, stub, "sweep")
    assert out.returncode == 1
    assert "cannot be read" in out.stderr


# --- watch ------------------------------------------------------------------------------------


def brief(n: int) -> dict:
    return {"number": n, "labels": [{"name": "agk-brief"}], "title": "a brief"}


def test_watch_once_lists_questions_and_reports_on_briefs_and_pull_requests(proj, stub):
    stub.serve(f"repos/{REPO}/issues", [brief(9)])
    stub.serve(
        f"repos/{REPO}/issues/9/comments",
        [comment(1, "builder", "Question: Q-9-1 which spec?\n\nmore", ago(5))],
    )
    serve_pr(
        stub,
        pr(7),
        [
            comment(2, "builder", f"Report: {SHORT} ready for review", ago(4)),
            comment(3, "builder", f"Progress: {SHORT} done 1/3; next: tests", ago(3)),
            comment(4, "builder", "Report: an old one", ago(120)),
        ],
    )
    out = run(proj, stub, "watch", "--since", ago(60), "--once")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == [
        "9 Question: Q-9-1 which spec?",
        f"7 Report: {SHORT} ready for review",
    ]
    assert all(c[0] == "GET" for c in stub.calls())


def test_watch_once_with_nothing_new_prints_nothing_new(proj, stub):
    out = run(proj, stub, "watch", "--once")
    assert out.returncode == 0
    assert out.stdout.strip() == "nothing new"


def test_watch_prints_a_network_error_and_retries(proj, stub):
    stub.serve(f"repos/{REPO}/issues", "FAIL", nth=1)
    stub.serve(f"repos/{REPO}/issues", [brief(9)], nth=2)
    stub.serve(
        f"repos/{REPO}/issues/9/comments", [comment(1, "builder", "Report: done", ago(0))]
    )
    out = run(proj, stub, "watch", "--since", ago(10))
    assert out.returncode == 0, out.stderr
    assert "cannot be read; retrying" in out.stderr
    assert out.stdout.splitlines() == ["9 Report: done"]


def test_watch_refuses_a_bad_since(proj, stub):
    out = run(proj, stub, "watch", "--since", "yesterday")
    assert out.returncode == 2
    assert "--since" in out.stderr


# --- sweep: a silent builder (brief #669, ADR-0322) -------------------------------------------


def taken_brief(stub, comments: list, branch: bool = False, number: int = 9) -> None:
    stub.serve(f"repos/{REPO}/issues", [brief(number)])
    stub.serve(f"repos/{REPO}/issues/{number}/comments", comments)
    refs = [{"ref": f"refs/heads/claude/brief-{number}"}] if branch else []
    stub.serve(f"repos/{REPO}/git/matching-refs/heads/claude/brief-{number}", refs)


def take(minutes: int, who: str = "b9", cid: int = 1) -> dict:
    return comment(cid, "builder", f"taken: {who} 2026-11-06", ago(minutes))


SILENT = "SILENT 9 b9 45; re-fire: Session name: b9. Item: brief #9."


def test_sweep_marks_a_silent_builder(proj, stub):
    taken_brief(stub, [take(45)])
    assert sweep(proj, stub)[-1] == SILENT


def test_sweep_a_fresh_take_is_not_silent(proj, stub):
    taken_brief(stub, [take(10)])
    assert not [x for x in sweep(proj, stub) if x.startswith("SILENT")]


def test_sweep_the_silent_threshold_is_a_setting(proj, stub):
    proj.write("agk.toml", "[flow]\nsilent_minutes = 60\n")
    taken_brief(stub, [take(45)])
    assert not [x for x in sweep(proj, stub) if x.startswith("SILENT")]


@pytest.mark.parametrize(
    "later",
    [
        f"Progress: {SHORT} done 1/3; next: tests",
        f"Report: {SHORT} pushed the tests",
        "Question: Q-9-1 which spec?",
    ],
)
def test_sweep_a_post_after_the_take_is_not_silent(proj, stub, later):
    taken_brief(stub, [take(45), comment(2, "builder", later, ago(30))])
    assert not [x for x in sweep(proj, stub) if x.startswith("SILENT")]


def test_sweep_a_post_before_the_take_does_not_count(proj, stub):
    taken_brief(stub, [comment(1, "builder", "Report: an older run", ago(90)), take(45, cid=2)])
    assert sweep(proj, stub)[-1] == SILENT


def test_sweep_an_escalated_brief_is_never_silent(proj, stub):
    escalate = comment(1, "builder", f"Report: {SHORT} escalate: a conflict", ago(90))
    taken_brief(stub, [escalate, take(45, cid=2)])
    assert not [x for x in sweep(proj, stub) if x.startswith("SILENT")]


def test_sweep_a_pushed_branch_is_not_silent(proj, stub):
    taken_brief(stub, [take(45)], branch=True)
    assert not [x for x in sweep(proj, stub) if x.startswith("SILENT")]


def test_sweep_an_open_pull_request_is_not_silent(proj, stub):
    taken_brief(stub, [take(45)])
    serve_pr(stub, pr(7, draft=True), [])
    lines = sweep(proj, stub)
    assert lines[0] == f"#7 {SHORT} draft 1h"
    assert not [x for x in lines if x.startswith("SILENT")]


def test_sweep_a_pull_request_merged_after_the_take_is_not_silent(proj, stub):
    taken_brief(stub, [take(45)])
    merged = {**pr(8), "state": "closed", "created_at": ago(40), "merged_at": ago(5)}
    stub.serve(f"repos/{REPO}/pulls", [merged], nth=2)  # the second read is state=all
    assert not [x for x in sweep(proj, stub) if x.startswith("SILENT")]


def test_sweep_a_released_take_is_not_silent(proj, stub):
    taken_brief(stub, [take(45), comment(2, "builder", "released: b9", ago(40))])
    assert not [x for x in sweep(proj, stub) if x.startswith("SILENT")]


def test_sweep_names_the_newest_take(proj, stub):
    old = comment(1, "builder", "taken: b8 2026-11-06", ago(200))
    late = comment(2, "builder", "released: b8", ago(100))
    taken_brief(stub, [old, late, take(45, cid=3)])
    assert sweep(proj, stub)[-1] == SILENT


def test_sweep_fails_when_a_branch_cannot_be_read(proj, stub):
    taken_brief(stub, [take(45)])
    stub.serve(f"repos/{REPO}/git/matching-refs/heads/claude/brief-9", "FAIL")
    out = run(proj, stub, "sweep")
    assert out.returncode == 1
    assert "cannot be read" in out.stderr
    assert "SILENT" not in out.stdout
