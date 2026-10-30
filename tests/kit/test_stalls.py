"""stalls.py: one read-only list of every stall, each with its cause and its fix (brief #367).

REQ-040; ADR-0205. A `gh` stub serves saved JSON copies of the GitHub responses; no network. One
fixture per kind reports it, one just under each limit does not; `no stall`, `--json`, and a
repository that cannot be read (exit 1, the rule named, never a value)."""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import timedelta

import pytest
from test_session import ISSUES, REPO, SHA, Stub, clean_env, comment, iso, issue, posts
from test_session_flow import DAY, PULLS, brief

SCRIPTS = __import__("pathlib").Path(__file__).resolve().parents[2] / "scripts" / "agk"
MIN = timedelta(minutes=1)


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    stub.serve(ISSUES, [])
    stub.serve(PULLS, [])
    return repo


def stalls(proj, stub, *args: str):
    env = clean_env()
    env.update(PATH=f"{stub.bin}{os.pathsep}{os.environ['PATH']}", GH_STUB_DIR=str(stub.dir))
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "stalls.py"), *args],
        cwd=proj.root,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def lines(proj, stub) -> list[str]:
    out = stalls(proj, stub)
    assert out.returncode in (0, 3), out.stdout + out.stderr
    assert all(c[0] == "GET" for c in stub.calls()) and posts(stub) == []
    return out.stdout.splitlines()


def kinds(proj, stub) -> list[tuple[str, int]]:
    found = []
    for line in lines(proj, stub):
        if line.startswith("stall "):
            kind, number = line.split(":")[0].split()[1:3]
            found.append((kind, int(number.lstrip("#"))))
    return found


# --- saved responses ----------------------------------------------------------------------------


def run(name: str, status: str = "completed", conclusion: str | None = "success", **kw) -> dict:
    """One check run; `ago` is how long ago it started and `done` how long ago it finished."""
    started = kw.get("ago", timedelta(minutes=90))
    done = kw.get("done", timedelta(minutes=80))
    return {
        "id": kw.get("id", 100),
        "name": name,
        "status": status,
        "conclusion": conclusion if status == "completed" else None,
        "started_at": iso(-started),
        "completed_at": iso(-done) if status == "completed" else None,
        "html_url": f"https://github.com/{REPO}/actions/runs/1",
    }


def green(done: timedelta = timedelta(minutes=80)) -> list[dict]:
    return [run("governance", id=1, done=done), run("proof", id=2, done=done)]


def open_pr(stub: Stub, n: int, label: str, checks: list[dict], **kw) -> dict:
    """An open pull request at LABEL with its facts: the checks of its head, comments, files and
    the issue events (when the label was set)."""
    pr = {
        "number": n,
        "state": "open",
        "title": f"pull request {n}",
        "body": "Advances: REQ-001\n",
        "labels": [{"name": label}],
        "user": {"login": "builder"},
        "created_at": iso(-timedelta(days=1)),
        "head": {"sha": SHA},
        "mergeable_state": "clean",
    }
    stub.serve(f"{PULLS}/{n}", pr)
    stub.serve(f"repos/{REPO}/commits/{SHA}/check-runs", {"total_count": len(checks),
               "check_runs": checks})  # fmt: skip
    stub.serve(f"{ISSUES}/{n}/comments", kw.get("comments", []))
    stub.serve(f"{PULLS}/{n}/files", [])
    stub.serve(f"repos/{REPO}/commits/{SHA}/status", {"statuses": kw.get("statuses", [])})
    labelled = kw.get("labelled", timedelta(minutes=120))
    event = {"event": "labeled", "label": {"name": label}, "created_at": iso(-labelled)}
    stub.serve(f"{ISSUES}/{n}/events", [event])
    return pr


def pulls(stub: Stub, *prs: dict) -> None:
    stub.serve(PULLS, list(prs))


# --- no stall, the table, the exit codes (answers 1 and 2) --------------------------------------


def test_nothing_stalled_prints_no_stall_and_exits_0_reading_only(proj, stub):
    out = stalls(proj, stub)
    assert (out.returncode, out.stdout) == (0, "no stall\n"), out.stdout + out.stderr
    assert stub.calls() and all(c[0] == "GET" for c in stub.calls())


def test_the_kinds_are_one_table_row_each_in_order():
    sys.path.insert(0, str(SCRIPTS))
    import stalls as module

    names = [k.name for k in module.KINDS]
    assert names == [
        "stale-label",
        "no-verdict",
        "stuck-run",
        "red-default",
        "idle-capacity",
        "claim-no-pr",
    ]
    for k in module.KINDS:
        assert k.detected and k.cause and k.fix, k.name


def test_a_stall_line_has_the_kind_the_number_the_cause_and_the_fix_and_exits_3(proj, stub):
    pulls(stub, open_pr(stub, 20, "agk:ci-running", green()))
    out = stalls(proj, stub)
    assert out.returncode == 3, out.stdout + out.stderr
    line = out.stdout.splitlines()[0]
    assert line.startswith("stall stale-label #20: ")
    cause, _, fix = line.partition(": ")[2].partition("; fix: ")
    assert cause and fix and "\n" not in line


def test_json_gives_the_same_stalls(proj, stub):
    pulls(stub, open_pr(stub, 20, "agk:ci-running", green()))
    words = stalls(proj, stub).stdout.splitlines()
    out = stalls(proj, stub, "--json")
    assert out.returncode == 3, out.stdout + out.stderr
    data = json.loads(out.stdout)
    assert [s["kind"] for s in data["stalls"]] == ["stale-label"]
    item = data["stalls"][0]
    assert item["number"] == 20
    assert (
        f"stall {item['kind']} #{item['number']}: {item['cause']}; fix: {item['fix']}" == words[0]
    )


def test_json_with_no_stall_is_an_empty_list_and_exit_0(proj, stub):
    out = stalls(proj, stub, "--json")
    assert out.returncode == 0 and json.loads(out.stdout) == {"stalls": []}


@pytest.mark.parametrize("args", [["--write"], ["--json", "x"], ["-h"]])
def test_an_unknown_argument_is_usage_exit_2(proj, stub, args):
    out = stalls(proj, stub, *args)
    assert out.returncode == 2 and out.stdout.startswith("usage: stalls.py")
    assert stub.calls() == []


# --- a repository that cannot be read (answer 4) ------------------------------------------------


@pytest.mark.parametrize("endpoint", [ISSUES, PULLS])
def test_a_repository_that_cannot_be_read_exits_1_naming_the_rule_not_a_value(proj, stub, endpoint):
    stub.serve(endpoint, "FAIL")
    out = stalls(proj, stub)
    assert out.returncode == 1, out.stdout + out.stderr
    text = out.stdout + out.stderr
    assert "cannot be read" in text and "rule " in text
    assert REPO not in text and "acme" not in text
    assert all(c[0] == "GET" for c in stub.calls())


def test_the_facts_of_a_pull_request_that_cannot_be_read_exit_1(proj, stub):
    pulls(stub, open_pr(stub, 20, "agk:ci-running", green()))
    stub.serve(f"{ISSUES}/20/events", "FAIL")
    out = stalls(proj, stub)
    assert out.returncode == 1 and "cannot be read" in out.stdout + out.stderr
    assert "#20" not in out.stdout + out.stderr


# --- stale-label --------------------------------------------------------------------------------


def test_stale_label_green_checks_and_ci_running_for_more_than_10_minutes(proj, stub):
    pulls(stub, open_pr(stub, 20, "agk:ci-running", green(11 * MIN), labelled=30 * MIN))
    assert kinds(proj, stub) == [("stale-label", 20)]
    line = lines(proj, stub)[0]
    assert "route.py --pr 20" in line


@pytest.mark.parametrize(
    ("done", "labelled"), [(9 * MIN, 30 * MIN), (30 * MIN, 9 * MIN)], ids=["checks", "label"]
)
def test_stale_label_just_under_10_minutes_is_no_stall(proj, stub, done, labelled):
    pulls(stub, open_pr(stub, 20, "agk:ci-running", green(done), labelled=labelled))
    assert kinds(proj, stub) == []


def test_stale_label_not_while_a_required_check_is_red_or_missing(proj, stub):
    red = [run("governance", id=1), run("proof", id=2, conclusion="failure")]
    pulls(stub, open_pr(stub, 20, "agk:ci-running", red))
    assert ("stale-label", 20) not in kinds(proj, stub)
    pulls(stub, open_pr(stub, 20, "agk:ci-running", [run("governance", id=1)]))
    assert kinds(proj, stub) == []


def test_stale_label_a_status_that_cannot_be_read_exits_1(proj, stub):
    """The verdict on b0b3ef3, item 3: a failed status read is never `no stall`."""
    pulls(stub, open_pr(stub, 20, "agk:ci-running", green()))
    stub.serve(f"repos/{REPO}/commits/{SHA}/status", "FAIL")
    out = stalls(proj, stub)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "rule 2 (stale-label, no-verdict)" in out.stdout and "cannot be read" in out.stdout


def test_stale_label_a_required_status_context_counts(proj, stub):
    proj.write("agk.toml", 'required_checks = ["governance", "proof", "ext"]\n')
    ext = {"context": "ext", "state": "success", "id": 7, "updated_at": iso(-80 * MIN)}
    pulls(stub, open_pr(stub, 20, "agk:ci-running", green(), statuses=[ext]))
    assert kinds(proj, stub) == [("stale-label", 20)]
    pending = {**ext, "state": "pending"}
    pulls(stub, open_pr(stub, 20, "agk:ci-running", green(), statuses=[pending]))
    assert kinds(proj, stub) == []


# --- no-verdict ---------------------------------------------------------------------------------


def test_no_verdict_at_review_for_more_than_30_minutes(proj, stub):
    old = comment(5, "boss", "Verdict: cleared 0123456")
    pulls(stub, open_pr(stub, 21, "agk:review", green(), comments=[old], labelled=31 * MIN))
    assert kinds(proj, stub) == [("no-verdict", 21)]


def test_no_verdict_just_under_30_minutes_is_no_stall(proj, stub):
    pulls(stub, open_pr(stub, 21, "agk:review", green(), labelled=29 * MIN))
    assert kinds(proj, stub) == []


def test_no_verdict_not_when_a_verdict_names_the_head(proj, stub):
    named = comment(5, "boss", f"Verdict: fix list {SHA[:7]}\n\n1. a thing")
    pulls(stub, open_pr(stub, 21, "agk:review", green(), comments=[named], labelled=3 * 60 * MIN))
    assert kinds(proj, stub) == []


# --- stuck-run ----------------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["queued", "in_progress"])
def test_stuck_run_a_required_run_waiting_for_more_than_60_minutes(proj, stub, status):
    checks = [run("governance", id=1), run("proof", status, id=2, ago=61 * MIN)]
    pulls(stub, open_pr(stub, 22, "agk:ci-running", checks))
    assert kinds(proj, stub) == [("stuck-run", 22)]
    assert "proof" in lines(proj, stub)[0]


def test_stuck_run_just_under_60_minutes_is_no_stall(proj, stub):
    checks = [run("governance", id=1), run("proof", "in_progress", id=2, ago=59 * MIN)]
    pulls(stub, open_pr(stub, 22, "agk:ci-running", checks))
    assert kinds(proj, stub) == []


def test_stuck_run_the_latest_required_run_cancelled_with_no_newer_run(proj, stub):
    checks = [run("governance", id=1), run("proof", id=2, conclusion="cancelled", done=MIN)]
    pulls(stub, open_pr(stub, 22, "agk:ci-red", checks))
    assert kinds(proj, stub) == [("stuck-run", 22)]
    assert "cancelled" in lines(proj, stub)[0]


def test_stuck_run_not_when_a_newer_run_follows_the_cancelled_one(proj, stub):
    checks = [
        run("governance", id=1),
        run("proof", id=2, conclusion="cancelled"),
        run("proof", id=3, done=MIN),
    ]
    pulls(stub, open_pr(stub, 22, "agk:ready", checks))
    assert kinds(proj, stub) == []


def test_stuck_run_ignores_a_check_that_is_not_required(proj, stub):
    checks = [*green(), run("lint", id=4, conclusion="cancelled")]
    pulls(stub, open_pr(stub, 22, "agk:ready", checks))
    assert kinds(proj, stub) == []


# --- red-default --------------------------------------------------------------------------------


def red_issue(author: str = "github-actions[bot]") -> dict:
    body = brief().replace("Advances: REQ-001", "Advances: none") + "Priority: 0\n"
    return {**issue(9, body), "title": "The default branch is red", "user": {"login": author}}


def test_red_default_the_red_branch_issue_is_open(proj, stub):
    stub.serve(ISSUES, [red_issue()])
    stub.serve(f"{ISSUES}/9/comments", [comment(1, "x", f"taken: builder-r {DAY}")])
    assert kinds(proj, stub) == [("red-default", 9)]


def test_red_default_not_for_an_issue_of_that_title_by_a_person(proj, stub):
    stub.serve(ISSUES, [red_issue(author="someone")])
    stub.serve(f"{ISSUES}/9/comments", [comment(1, "x", f"taken: builder-r {DAY}")])
    assert ("red-default", 9) not in kinds(proj, stub)


# --- idle-capacity ------------------------------------------------------------------------------


def test_idle_capacity_the_plan_starts_a_session_and_nobody_took_a_brief_in_15_minutes(proj, stub):
    take = comment(1, "x", f"taken: builder-z {DAY}", when=iso(-16 * MIN))
    stub.serve(ISSUES, [issue(5, brief("a/")), issue(6, brief("b/"))])
    stub.serve(f"{ISSUES}/5/comments", [])
    stub.serve(f"{ISSUES}/6/comments", [take])
    assert kinds(proj, stub) == [("idle-capacity", 5)]
    line = lines(proj, stub)[0]
    assert "session.py claim --session builder-a --brief 5" in line


def test_idle_capacity_just_under_15_minutes_is_no_stall(proj, stub):
    take = comment(1, "x", f"taken: builder-z {DAY}", when=iso(-14 * MIN))
    stub.serve(ISSUES, [issue(5, brief("a/")), issue(6, brief("b/"))])
    stub.serve(f"{ISSUES}/5/comments", [])
    stub.serve(f"{ISSUES}/6/comments", [take])
    assert kinds(proj, stub) == []


def test_idle_capacity_not_when_the_plan_starts_nobody(proj, stub):
    stub.serve(ISSUES, [issue(5, brief("a/"))])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-z {DAY}", iso(-60 * MIN))])
    assert kinds(proj, stub) == []


def test_idle_capacity_a_dependence_that_cannot_be_read_exits_1(proj, stub):
    """The verdict on b0b3ef3, item 1: `GOOD` depends on #3, whose read fails."""
    stub.serve(ISSUES, [issue(5)])
    stub.serve(f"{ISSUES}/5/comments", [])
    stub.serve(f"{ISSUES}/3", "FAIL")
    out = stalls(proj, stub)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "rule 2 (idle-capacity): the plan cannot be read" in out.stdout


def test_idle_capacity_comments_the_plan_cannot_read_exit_1(proj, stub):
    """The verdict on b0b3ef3, item 2: only the plan's own read of the comments fails."""
    stub.serve(ISSUES, [issue(5, brief("a/"))])
    stub.serve(f"{ISSUES}/5/comments", [], nth=1)
    stub.serve(f"{ISSUES}/5/comments", "FAIL", nth=2)
    out = stalls(proj, stub)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "rule 2 (idle-capacity): the plan cannot be read" in out.stdout


# --- claim-no-pr --------------------------------------------------------------------------------


def taken(stub: Stub, ago: timedelta, *more: dict) -> None:
    stub.serve(ISSUES, [issue(6, brief("b/"))])
    take = comment(1, "x", f"taken: builder-x {DAY}", when=iso(-ago))
    stub.serve(f"{ISSUES}/6/comments", [take, *more])


def test_claim_no_pr_a_live_take_with_no_pull_request_and_no_post_for_2_hours(proj, stub):
    taken(stub, 121 * MIN)
    assert kinds(proj, stub) == [("claim-no-pr", 6)]
    line = lines(proj, stub)[0]
    assert "builder-x" in line and "released: builder-x" in line
    assert "posted nothing for 2 hours" in line


def test_claim_no_pr_the_age_counts_from_the_sessions_last_post(proj, stub):
    """The verdict on b0b3ef3 (optional): a post after the take moves the age, not the take."""
    note = comment(2, "x", "Progress: builder-x done 0/4; next: 1", when=iso(-121 * MIN))
    taken(stub, 230 * MIN, note)
    line = lines(proj, stub)[0]
    assert line.startswith("stall claim-no-pr #6: ") and "posted nothing for 2 hours" in line
    assert "3 hours" not in line


def test_claim_no_pr_just_under_2_hours_is_no_stall(proj, stub):
    taken(stub, 119 * MIN)
    assert kinds(proj, stub) == []


def test_claim_no_pr_not_when_the_session_posted_since(proj, stub):
    note = comment(2, "x", "Request: builder-x blocked on a question", when=iso(-60 * MIN))
    taken(stub, 150 * MIN, note)
    assert kinds(proj, stub) == []


def test_claim_no_pr_not_when_a_pull_request_names_the_brief(proj, stub):
    taken(stub, 150 * MIN)
    work = open_pr(stub, 30, "agk:review", green(), labelled=MIN)
    pulls(stub, {**work, "body": "Advances: REQ-001\nBrief: #6\n"})
    stub.serve(f"{PULLS}/30", {**work, "body": "Advances: REQ-001\nBrief: #6\n"})
    assert ("claim-no-pr", 6) not in kinds(proj, stub)


def test_claim_no_pr_not_for_a_released_take(proj, stub):
    gone = comment(2, "x", "released: builder-x", when=iso(-130 * MIN))
    taken(stub, 150 * MIN, gone)
    assert ("claim-no-pr", 6) not in kinds(proj, stub)
