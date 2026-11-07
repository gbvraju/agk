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
from datetime import datetime, timedelta

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


# --- rerun, check-verdict and lease (brief #700, ADR-0330) -------------------------------------

SHA12 = SHA[:12]
RUNS = f"repos/{REPO}/actions/runs"


def run_of(rid: int, conclusion: str | None, name: str = "proof") -> dict:
    return {
        "id": rid, "name": name, "event": "pull_request", "head_sha": SHA,
        "status": "completed" if conclusion else "in_progress", "conclusion": conclusion,
    }  # fmt: skip


def serve_runs(stub, item: dict, runs: list) -> None:
    stub.serve(f"repos/{REPO}/pulls/{item['number']}", item)
    stub.serve(RUNS, {"workflow_runs": runs})


def posts(stub) -> list[list]:
    return [c for c in stub.calls() if c[0] != "GET"]


def test_rerun_lists_each_cancelled_run_and_reruns_nothing_without_apply(proj, stub):
    serve_runs(stub, pr(7), [run_of(1, "cancelled"), run_of(2, "success", "governance")])
    out = run(proj, stub, "rerun", "--pr", "7")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == [
        f"rerun: #7 {SHA12}: run 1 (proof) cancelled; add --apply to rerun it",
    ]
    assert posts(stub) == []


def test_rerun_with_apply_reruns_each_cancelled_run(proj, stub):
    serve_runs(stub, pr(7), [run_of(1, "cancelled"), run_of(3, "cancelled", "governance")])
    out = run(proj, stub, "rerun", "--pr", "7", "--apply")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == [
        f"rerun: #7 {SHA12}: run 1 (proof) cancelled; rerun",
        f"rerun: #7 {SHA12}: run 3 (governance) cancelled; rerun",
    ]
    assert [c[:2] for c in posts(stub)] == [
        ["POST", f"{RUNS}/1/rerun"],
        ["POST", f"{RUNS}/3/rerun"],
    ]


def test_rerun_reads_the_runs_of_the_head_by_pull_request_event(proj, stub):
    serve_runs(stub, pr(7), [])
    run(proj, stub, "rerun", "--pr", "7")
    asked = [c[1] for c in stub.calls() if c[1].startswith(RUNS)]
    assert asked == [f"{RUNS}?event=pull_request&head_sha={SHA}&per_page=100"]


def test_rerun_with_only_skipped_runs_prints_the_step_and_does_it_only_with_apply(proj, stub):
    serve_runs(stub, pr(7), [run_of(1, "skipped"), run_of(2, "skipped", "governance")])
    out = run(proj, stub, "rerun", "--pr", "7")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == [
        f"rerun: #7 {SHA12}: every run of the head skipped (a push to a ready pull request); "
        f"the step: POST repos/{REPO}/pulls/7/ccr/convert_to_draft, then "
        f"POST repos/{REPO}/pulls/7/ccr/ready_for_review; add --apply to do it",
    ]
    assert posts(stub) == []
    out = run(proj, stub, "rerun", "--pr", "7", "--apply")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines()[-1] == (
        f"rerun: #7 {SHA12}: converted to draft and back; its runs start"
    )
    assert [c[:2] for c in posts(stub)] == [
        ["POST", f"repos/{REPO}/pulls/7/ccr/convert_to_draft"],
        ["POST", f"repos/{REPO}/pulls/7/ccr/ready_for_review"],
    ]


def test_rerun_leaves_a_draft_alone_whose_runs_skip_by_design(proj, stub):
    serve_runs(stub, pr(7, draft=True), [run_of(1, "skipped")])
    out = run(proj, stub, "rerun", "--pr", "7", "--apply")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == [
        f"rerun: #7 {SHA12}: every run of the head skipped; the pull request is a draft, "
        "whose runs skip until it is marked ready",
    ]
    assert posts(stub) == []


@pytest.mark.parametrize(
    ("runs", "line"),
    [
        ([], "no run of the head"),
        ([run_of(1, "success"), run_of(2, "skipped", "governance")], "nothing to rerun"),
        ([run_of(1, "failure")], "nothing to rerun"),
        ([run_of(1, None)], "nothing to rerun"),
    ],
)
def test_rerun_with_nothing_cancelled_says_so(proj, stub, runs, line):
    serve_runs(stub, pr(7), runs)
    out = run(proj, stub, "rerun", "--pr", "7", "--apply")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == [f"rerun: #7 {SHA12}: {line}"]
    assert posts(stub) == []


def test_rerun_a_run_of_another_event_is_not_a_run_of_the_head(proj, stub):
    other = {**run_of(1, "cancelled"), "event": "push"}
    serve_runs(stub, pr(7), [other])
    out = run(proj, stub, "rerun", "--pr", "7", "--apply")
    assert out.stdout.splitlines() == [f"rerun: #7 {SHA12}: no run of the head"]
    assert posts(stub) == []


def test_rerun_fails_when_the_pull_request_or_its_runs_cannot_be_read(proj, stub):
    stub.serve(f"repos/{REPO}/pulls/7", "FAIL")
    out = run(proj, stub, "rerun", "--pr", "7")
    assert out.returncode == 1 and "cannot be read" in out.stderr
    serve_runs(stub, pr(7), [])
    stub.serve(RUNS, "FAIL")
    out = run(proj, stub, "rerun", "--pr", "7")
    assert out.returncode == 1 and "cannot be read" in out.stderr


def test_rerun_fails_when_a_rerun_is_refused(proj, stub):
    serve_runs(stub, pr(7), [run_of(1, "cancelled")])
    stub.serve(f"{RUNS}/1/rerun", "FAIL", method="POST")
    out = run(proj, stub, "rerun", "--pr", "7", "--apply")
    assert out.returncode == 1
    assert "cannot be rerun" in out.stderr


@pytest.mark.parametrize(
    "args",
    [
        ["rerun"],
        ["rerun", "--pr"],
        ["rerun", "--pr", "x"],
        ["rerun", "--pr", "0"],
        ["rerun", "--apply", "--pr", "7"],
        ["rerun", "--pr", "7", "--apply", "--apply"],
        ["rerun", "--pr", "7", "--force"],
    ],
)
def test_rerun_any_other_form_is_a_usage_error(proj, stub, args):
    out = run(proj, stub, *args)
    assert out.returncode == 2
    assert "rerun --pr N [--apply]" in out.stderr
    assert stub.calls() == []


# --- check-verdict ----------------------------------------------------------------------------

GOOD = f"Verdict: fix list {SHA}\n\nFinal: docs/adr/0001-the-adr.md Proposed -> Accepted\n"


def check(proj, stub, text: str):
    path = proj.root / "verdict.md"
    path.write_text(text, encoding="utf-8")
    return run(proj, stub, "check-verdict", str(path))


def test_check_verdict_prints_ok_for_a_well_formed_verdict(proj, stub):
    for text in (GOOD, f"Verdict: cleared {SHA}\n\nAll fine.\n", f"Verdict: rejected {SHA[:7]}\nwhy\n"):
        out = check(proj, stub, text)
        assert out.returncode == 0 and out.stdout.strip() == "ok", text
    assert stub.calls() == []


def test_check_verdict_prints_the_problem_of_a_final_line_and_exits_1(proj, stub):
    out = check(proj, stub, f"Verdict: cleared {SHA}\nFinal: flip ADR-0146 to Accepted\n")
    assert out.returncode == 1
    assert out.stdout.strip().startswith("SPEC-0021 rule 1:")
    assert "ADR-0146" not in out.stdout  # the rule and the shape, never the body


def test_check_verdict_a_first_line_that_names_no_head_is_a_problem(proj, stub):
    for text in ("Verdict: cleared\n", "Report: done\n", "", "Verdict: fix list main\n"):
        out = check(proj, stub, text)
        assert out.returncode == 1, text
        assert out.stdout.strip() == (
            "the first line is not `Verdict: cleared|fix list|rejected <sha>` (session rule 1)"
        )


def test_check_verdict_fails_when_the_file_cannot_be_read(proj, stub):
    out = run(proj, stub, "check-verdict", str(proj.root / "missing.md"))
    assert out.returncode == 1
    assert "cannot be read" in out.stderr
    assert run(proj, stub, "check-verdict").returncode == 2
    assert run(proj, stub, "check-verdict", "a", "b").returncode == 2


# --- lease ------------------------------------------------------------------------------------

PLAN = f"repos/{REPO}/issues/61/comments"
OFF = "lease: off (setting: plan_issue in the flow table of agk.toml)"


def with_plan(proj, stub, comments: list) -> None:
    proj.write("agk.toml", "[flow]\nconductor_poll_seconds = 1\nplan_issue = 61\n")
    stub.serve(PLAN, comments)


def active(minutes: int, who: str = "c1", cid: int = 5, kind: str = "active") -> dict:
    return comment(cid, "boss", f"Conductor: {kind} {ago(minutes)} {who}", ago(minutes))


def until(marker: dict) -> str:
    """The end of the lease the marker holds: its time plus 50 minutes."""
    start = datetime.strptime(marker["body"].split()[2], "%Y-%m-%dT%H:%M:%SZ")
    return (start + timedelta(minutes=50)).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_lease_is_off_without_the_setting(proj, stub):
    out = run(proj, stub, "lease", "--show")
    assert out.returncode == 0 and out.stdout.strip() == OFF
    for args in (["--take", "c1"], ["--release", "c1"]):
        out = run(proj, stub, "lease", *args)
        assert out.returncode == 1 and out.stdout.strip() == OFF
    assert stub.calls() == []


def test_lease_show_prints_free_without_a_marker(proj, stub):
    with_plan(proj, stub, [comment(1, "builder", "Request: b1 new")])
    out = run(proj, stub, "lease", "--show")
    assert out.returncode == 0 and out.stdout.strip() == "lease: free"
    assert all(c[0] == "GET" for c in stub.calls())


def test_lease_show_names_a_valid_holder_and_its_end(proj, stub):
    marker = active(10)
    with_plan(proj, stub, [marker])
    out = run(proj, stub, "lease", "--show")
    assert out.returncode == 0
    assert out.stdout.strip() == f"lease: held by c1 until {until(marker)}"


@pytest.mark.parametrize("marker", [active(55), active(10, kind="released")])
def test_lease_show_an_expired_or_released_marker_is_free(proj, stub, marker):
    with_plan(proj, stub, [marker])
    out = run(proj, stub, "lease", "--show")
    assert out.stdout.strip() == "lease: free"


def test_lease_take_posts_the_marker_when_there_is_none(proj, stub):
    with_plan(proj, stub, [])
    out = run(proj, stub, "lease", "--take", "c2")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().startswith("lease: taken by c2 until ")
    made = posts(stub)
    assert len(made) == 1 and made[0][:2] == ["POST", PLAN]
    body = made[0][2][made[0][2].index("-f") + 1]
    assert body.startswith("body=Conductor: active 20") and body.endswith(" c2")
    assert body.split()[2].endswith("Z")


def test_lease_take_edits_the_marker_in_place_when_it_is_free(proj, stub):
    with_plan(proj, stub, [active(55), comment(6, "builder", "Request: b1 new")])
    stub.serve(f"repos/{REPO}/issues/comments/5", {}, method="PATCH")
    out = run(proj, stub, "lease", "--take", "c2")
    assert out.returncode == 0, out.stderr
    made = posts(stub)
    assert len(made) == 1 and made[0][:2] == ["PATCH", f"repos/{REPO}/issues/comments/5"]
    assert "Conductor: active" in made[0][2][made[0][2].index("-f") + 1]


def test_lease_take_by_the_holder_renews_it(proj, stub):
    with_plan(proj, stub, [active(30)])
    stub.serve(f"repos/{REPO}/issues/comments/5", {}, method="PATCH")
    out = run(proj, stub, "lease", "--take", "c1")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().startswith("lease: taken by c1 until ")
    assert [c[:2] for c in posts(stub)] == [["PATCH", f"repos/{REPO}/issues/comments/5"]]


def test_lease_take_is_refused_while_another_name_holds_a_valid_lease(proj, stub):
    marker = active(10)
    with_plan(proj, stub, [marker])
    out = run(proj, stub, "lease", "--take", "c2")
    assert out.returncode == 3
    assert out.stdout.strip() == (
        f"lease: held by c1 until {until(marker)} "
        "(setting: plan_issue in the flow table of agk.toml)"
    )
    assert posts(stub) == []


def test_lease_release_by_the_holder_marks_the_comment_released(proj, stub):
    with_plan(proj, stub, [active(10)])
    stub.serve(f"repos/{REPO}/issues/comments/5", {}, method="PATCH")
    out = run(proj, stub, "lease", "--release", "c1")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "lease: released by c1"
    made = posts(stub)
    assert made[0][:2] == ["PATCH", f"repos/{REPO}/issues/comments/5"]
    body = made[0][2][made[0][2].index("-f") + 1]
    assert body.startswith("body=Conductor: released 20") and body.endswith(" c1")


def test_lease_release_by_another_name_is_refused_and_a_free_lease_needs_no_write(proj, stub):
    with_plan(proj, stub, [active(10)])
    out = run(proj, stub, "lease", "--release", "c2")
    assert out.returncode == 3 and posts(stub) == []
    with_plan(proj, stub, [active(55)])
    out = run(proj, stub, "lease", "--release", "c2")
    assert out.returncode == 0 and out.stdout.strip() == "lease: free" and posts(stub) == []


def test_lease_fails_when_the_plan_issue_cannot_be_read_or_written(proj, stub):
    with_plan(proj, stub, [])
    stub.serve(PLAN, "FAIL")
    out = run(proj, stub, "lease", "--show")
    assert out.returncode == 1 and "cannot be read" in out.stderr
    with_plan(proj, stub, [])
    stub.serve(PLAN, "FAIL", method="POST")
    out = run(proj, stub, "lease", "--take", "c2")
    assert out.returncode == 1 and "cannot be written" in out.stderr


def test_lease_a_plan_issue_that_is_no_number_names_the_setting(proj, stub):
    proj.write("agk.toml", '[flow]\nplan_issue = "sixty-one"\n')
    out = run(proj, stub, "lease", "--show")
    assert out.returncode == 1 and "plan_issue" in out.stderr and "sixty" not in out.stderr


@pytest.mark.parametrize(
    "args",
    [
        ["lease"],
        ["lease", "--take"],
        ["lease", "--take", "--show"],
        ["lease", "--show", "c1"],
        ["lease", "--take", "c1", "--release", "c1"],
        ["lease", "--hold", "c1"],
        ["lease", "--take", "a b"],
    ],
)
def test_lease_any_other_form_is_a_usage_error(proj, stub, args):
    out = run(proj, stub, *args)
    assert out.returncode == 2
    assert "lease (--show | --take NAME | --release NAME)" in out.stderr
    assert stub.calls() == []


def test_the_lease_take_leaves_a_local_mark_that_release_removes(proj, stub):
    with_plan(proj, stub, [])
    assert run(proj, stub, "lease", "--take", "c2").returncode == 0
    mark = proj.root / ".git" / "agk" / "lease"
    assert mark.read_text(encoding="utf-8").strip() == "c2"
    with_plan(proj, stub, [active(1, who="c2")])
    stub.serve(f"repos/{REPO}/issues/comments/5", {}, method="PATCH")
    assert run(proj, stub, "lease", "--release", "c2").returncode == 0
    assert not mark.exists()
