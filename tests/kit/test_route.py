"""route.py and the router workflow (SPEC-0032 rules 1, 2 and 8; REQ-039 AC1, AC2).

The label of a pull request from saved GitHub responses (a `gh` stub), one label at a time, a push
to the default branch routing every open pull request, and the router writing nothing but labels.
No network, no model.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "agk-route.yml"
sys.path.insert(0, str(SCRIPTS))

import route  # noqa: E402

REPO = "acme/widgets"
HEAD = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
OLD = "0123456789abcdef0123456789abcdef01234567"
SPEC = "docs/specs/0032-the-spec.md"


def ok(name: str) -> dict:
    return {"name": name, "status": "completed", "conclusion": "success"}


def said(cid: int, login: str, body: str) -> dict:
    return {
        "id": cid,
        "user": {"login": login},
        "body": body,
        "created_at": f"2026-10-25T10:{cid:02d}:00Z",
    }


def facts(**kw) -> dict:
    base = {
        "head": HEAD,
        "mergeable_state": "clean",
        "checks": [ok("governance"), ok("proof")],
        "statuses": [],
        "comments": [],
        "reviews": [],
        "authors": ["boss"],
        "approvers": ["maintainer"],
        "author": "builder",
        "files": [],
        "commit": {},
    }
    base.update(kw)
    return base


def approved_spec() -> list[dict]:
    patch = "@@ -1,3 +1,3 @@\n-- Status: Draft\n+- Status: Approved\n"
    return [{"filename": SPEC, "status": "modified", "patch": patch}]


# --- the label from the facts (rule 2; AC1) ----------------------------------------------------


def test_ac1_a_pull_request_with_green_checks_and_no_verdict_is_in_review():
    """REQ-039 AC1: rule 2 (agk:review)."""
    assert route.decide(facts()) == "agk:review"


def test_ac1_a_required_check_not_completed_is_ci_running():
    """REQ-039 AC1: rule 2 (agk:ci-running), also with no check run yet and a pending status."""
    running = {"name": "proof", "status": "in_progress", "conclusion": None}
    assert route.decide(facts(checks=[ok("governance"), running])) == "agk:ci-running"
    assert route.decide(facts(checks=[])) == "agk:ci-running"
    pending = [{"context": "ci/other", "state": "pending"}]
    assert route.decide(facts(statuses=pending)) == "agk:ci-running"


def test_ac1_a_failed_check_is_ci_red_and_a_skipped_one_is_not():
    """REQ-039 AC1: rule 2 (agk:ci-red)."""
    for conclusion in ("failure", "timed_out", "cancelled", "action_required"):
        bad = {"name": "proof", "status": "completed", "conclusion": conclusion}
        assert route.decide(facts(checks=[ok("governance"), bad])) == "agk:ci-red", conclusion
    for conclusion in ("skipped", "neutral", "success"):
        fine = {"name": "proof", "status": "completed", "conclusion": conclusion}
        assert route.decide(facts(checks=[ok("governance"), fine])) == "agk:review", conclusion
    assert route.decide(facts(statuses=[{"context": "x", "state": "failure"}])) == "agk:ci-red"


def test_ac1_a_dirty_pull_request_is_a_conflict_before_anything_else():
    """REQ-039 AC1: rule 2 (agk:conflict first: GitHub starts no workflow on it)."""
    bad = {"name": "proof", "status": "completed", "conclusion": "failure"}
    assert route.decide(facts(mergeable_state="dirty", checks=[bad])) == "agk:conflict"
    assert route.decide(facts(mergeable_state="dirty", checks=[])) == "agk:conflict"


def test_ac1_running_comes_before_red():
    """REQ-039 AC1: rule 2 (the order: conflict, ci-running, ci-red, ...)."""
    bad = {"name": "governance", "status": "completed", "conclusion": "failure"}
    running = {"name": "proof", "status": "queued", "conclusion": None}
    assert route.decide(facts(checks=[bad, running])) == "agk:ci-running"


def test_ac1_the_routers_own_check_run_is_not_counted():
    """REQ-039 AC1: rule 2 (the job that routes is itself a check run of the head)."""
    own = {"name": route.ROUTER_JOB, "status": "in_progress", "conclusion": None}
    assert route.decide(facts(checks=[ok("governance"), own])) == "agk:review"


def test_ac1_a_fix_list_or_a_rejection_naming_the_head_is_fix():
    """REQ-039 AC1: rule 2 (agk:fix); a verdict naming an older head does not count."""
    fix = said(1, "boss", f"Verdict: fix list {HEAD[:7]}\n\n1. do this")
    assert route.decide(facts(comments=[fix])) == "agk:fix"
    no = said(1, "boss", f"Verdict: rejected {HEAD[:7]}")
    assert route.decide(facts(comments=[no])) == "agk:fix"
    older = said(1, "boss", f"Verdict: fix list {OLD[:7]}")
    assert route.decide(facts(comments=[older])) == "agk:review"


def test_ac1_a_verdict_by_an_unlisted_author_is_ignored():
    """REQ-039 AC1: rule 2 (only a listed verdict author counts)."""
    cleared = said(1, "stranger", f"Verdict: cleared {HEAD[:7]}")
    assert route.decide(facts(comments=[cleared])) == "agk:review"


def test_ac1_a_cleared_head_with_green_checks_is_ready():
    """REQ-039 AC1: rule 2 (agk:ready)."""
    cleared = said(1, "boss", f"Verdict: cleared {HEAD[:7]}")
    assert route.decide(facts(comments=[cleared])) == "agk:ready"


def test_ac1_a_covered_head_is_ready():
    """REQ-039 AC1: rule 2 (cleared in advance by a fix list that names only the final commit)."""
    path = "docs/adr/0001-x.md"
    body = f"Verdict: fix list {OLD[:7]}\n\nFinal: {path} Proposed -> Accepted\n"
    commit = {
        "parents": [{"sha": OLD}],
        "files": [
            {
                "filename": path,
                "status": "modified",
                "patch": "@@ -1 +1 @@\n-- Status: Proposed\n+- Status: Accepted\n",
            }
        ],
    }
    assert route.decide(facts(comments=[said(1, "boss", body)], commit=commit)) == "agk:ready"
    commit["files"][0]["patch"] = "@@ -1 +1 @@\n-- Status: Proposed\n+- Status: Rejected\n"
    assert route.decide(facts(comments=[said(1, "boss", body)], commit=commit)) != "agk:ready"


def test_ac1_a_cleared_head_that_approves_a_spec_waits_for_a_person():
    """REQ-039 AC1: rule 2 (agk:approve) until an approver's Approve: names the spec."""
    cleared = said(1, "boss", f"Verdict: cleared {HEAD[:7]}")
    assert route.decide(facts(comments=[cleared], files=approved_spec())) == "agk:approve"
    by_person = said(2, "maintainer", f"Approve: {OLD[:7]} SPEC-0032")
    both = facts(comments=[cleared, by_person], files=approved_spec())
    assert route.decide(both) == "agk:ready"


def test_ac1_an_approve_review_body_by_an_approver_counts_and_other_accounts_do_not():
    """REQ-039 AC1: rule 2 (Approve: in a review body counts; an unlisted account never does)."""
    cleared = said(1, "boss", f"Verdict: cleared {HEAD[:7]}")
    review = {"user": {"login": "maintainer"}, "body": f"Approve: {HEAD[:7]} SPEC-0032"}
    assert route.decide(facts(comments=[cleared], reviews=[review], files=approved_spec())) == (
        "agk:ready"
    )
    stranger = said(2, "stranger", f"Approve: {HEAD[:7]} SPEC-0032")
    other = facts(comments=[cleared, stranger], files=approved_spec())
    assert route.decide(other) == "agk:approve"
    elsewhere = said(2, "maintainer", f"Approve: {HEAD[:7]} SPEC-0099")
    assert route.decide(facts(comments=[cleared, elsewhere], files=approved_spec())) == (
        "agk:approve"
    )
    assert route.decide(facts(comments=[cleared], files=approved_spec(), approvers=[])) == (
        "agk:approve"
    )


def test_ac1_a_fix_list_comes_before_approve_and_red_before_a_verdict():
    """REQ-039 AC1: rule 2 (the order: ..., ci-red, fix, approve, ready, review)."""
    fix = said(1, "boss", f"Verdict: fix list {HEAD[:7]}\n\n1. x")
    assert route.decide(facts(comments=[fix], files=approved_spec())) == "agk:fix"
    bad = {"name": "proof", "status": "completed", "conclusion": "failure"}
    cleared = said(1, "boss", f"Verdict: cleared {HEAD[:7]}")
    assert route.decide(facts(comments=[cleared], checks=[bad])) == "agk:ci-red"


def test_ac1_the_result_is_always_exactly_one_of_the_seven():
    """REQ-039 AC1: rule 2 (one label at a time)."""
    cleared = said(1, "boss", f"Verdict: cleared {HEAD[:7]}")
    bad = {"name": "proof", "status": "completed", "conclusion": "failure"}
    for state in ("clean", "dirty", "blocked", "unknown"):
        for checks in ([], [ok("a")], [bad]):
            for comments in ([], [cleared]):
                label = route.decide(facts(mergeable_state=state, checks=checks, comments=comments))
                assert label in route.LABELS


# --- the router against a gh stub (rules 1 and 8; AC1, AC2) ----------------------------------

STUB = '''#!/usr/bin/env python3
"""A gh stub: serves GET fixtures from fixtures.json, logs every call, answers writes with {}."""
import json, os, sys
args = sys.argv[1:]
root = os.environ["GH_STUB_DIR"]
method = args[args.index("--method") + 1]
endpoint = args[args.index("--method") + 2]
with open(os.path.join(root, "calls.log"), "a") as log:
    log.write(json.dumps([method, endpoint, args[args.index("--method") + 3:]]) + "\\n")
if method != "GET":
    if os.environ.get("GH_STUB_FORBID"):
        sys.stderr.write("gh: Resource not accessible by integration (HTTP 403)\\n")
        sys.exit(1)
    print("{}")
    sys.exit(0)
fixtures = json.load(open(os.path.join(root, "fixtures.json")))
value = fixtures.get(endpoint.split("?")[0])
if value is None or value == "FAIL":
    sys.exit(1)
print(json.dumps(value))
'''


class Stub:
    def __init__(self, tmp: Path) -> None:
        self.dir = tmp / "stub"
        self.dir.mkdir()
        self.bin = tmp / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(STUB, encoding="utf-8")
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        self.fixtures: dict = {f"repos/{REPO}/labels": []}
        # a green default branch with no red-branch issue (SPEC-0032 rule 7)
        self.fixtures[f"repos/{REPO}/branches/main"] = {"commit": {"sha": HEAD}}
        self.fixtures[f"repos/{REPO}/commits/{HEAD}/check-runs"] = {
            "total_count": 2,
            "check_runs": [ok("governance"), ok("proof")],
        }
        self.fixtures[f"repos/{REPO}/commits/{HEAD}/status"] = {"statuses": []}
        self.fixtures[f"repos/{REPO}/issues"] = []

    def pull(self, n: int, labels=(), state="open", mergeable="clean", merged=None) -> None:
        self.fixtures[f"repos/{REPO}/pulls/{n}"] = {
            "number": n,
            "state": state,
            "merged_at": merged,
            "mergeable_state": mergeable,
            "user": {"login": "builder"},
            "head": {"sha": HEAD},
            "labels": [{"name": name} for name in labels],
        }
        self.fixtures[f"repos/{REPO}/commits/{HEAD}/check-runs"] = {
            "total_count": 2,
            "check_runs": [ok("governance"), ok("proof")],
        }
        self.fixtures[f"repos/{REPO}/commits/{HEAD}/status"] = {"statuses": []}
        for kind in ("issues/%d/comments", "pulls/%d/reviews", "pulls/%d/files"):
            self.fixtures.setdefault(f"repos/{REPO}/{kind % n}", [])

    def open_list(self, numbers: list[int]) -> None:
        self.fixtures[f"repos/{REPO}/pulls"] = [
            {"number": n, "head": {"sha": HEAD}, "state": "open"} for n in numbers
        ]

    def serve(self, endpoint: str, value) -> None:
        self.fixtures[f"repos/{REPO}/{endpoint}"] = value

    def calls(self) -> list[list]:
        log = self.dir / "calls.log"
        return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []

    def writes(self) -> list[list]:
        return [c for c in self.calls() if c[0] != "GET"]


@pytest.fixture
def stub(tmp_path: Path) -> Stub:
    return Stub(tmp_path)


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "config").mkdir(parents=True)
    (root / "config" / "reviewers.yaml").write_text(
        "version: 1\nverdict_authors: [boss]\nspec_approvers: [maintainer]\n", encoding="utf-8"
    )
    git = ["git", "init", "-q", "-b", "main"]
    subprocess.run(git, cwd=root, check=True)  # nosec B603 - fixed argument list, no shell
    return root


def run_router(
    proj: Path, stub: Stub, tmp: Path, event: str, payload: dict, *args: str, **extra: str
):
    (stub.dir / "fixtures.json").write_text(json.dumps(stub.fixtures), encoding="utf-8")
    path = tmp / f"event-{event}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env.update(
        PATH=f"{stub.bin}{os.pathsep}{os.environ['PATH']}",
        GH_STUB_DIR=str(stub.dir),
        GITHUB_EVENT_NAME=event,
        GITHUB_EVENT_PATH=str(path),
        GITHUB_REPOSITORY=REPO,
        **extra,
    )
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "route.py"), *args],
        cwd=proj,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


REPO_INFO = {"full_name": REPO, "default_branch": "main"}


def test_ac1_a_pull_request_event_sets_the_one_label_and_removes_the_others(proj, stub, tmp_path):
    """REQ-039 AC1: rules 1 and 2 (only agk: labels change; a person's label is left alone)."""
    stub.pull(7, labels=["bug", "agk:ci-running", "agk:fix"])
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    proc = run_router(proj, stub, tmp_path, "pull_request", event)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    writes = stub.writes()
    adds = [w for w in writes if w[0] == "POST" and w[1].endswith("/issues/7/labels")]
    assert len(adds) == 1 and "labels[]=agk:review" in adds[0][2]
    removed = sorted(w[1].rsplit("/", 1)[1] for w in writes if w[0] == "DELETE")
    assert removed == ["agk%3Aci-running", "agk%3Afix"] or removed == ["agk:ci-running", "agk:fix"]
    assert not any("bug" in w[1] for w in writes)


def test_ac1_a_pull_request_that_already_has_its_label_is_not_written(proj, stub, tmp_path):
    """REQ-039 AC1: rule 2 (idempotent: the same facts change nothing)."""
    stub.pull(7, labels=["agk:review"])
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    proc = run_router(proj, stub, tmp_path, "pull_request", event)
    assert proc.returncode == 0 and stub.writes() == []


def test_ac1_a_label_that_does_not_exist_yet_is_created_first(proj, stub, tmp_path):
    """REQ-039 AC1: rule 2 (the repository may not have the seven labels)."""
    stub.pull(7)
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "pull_request", event)
    writes = stub.writes()
    assert writes[0][0] == "POST" and writes[0][1] == f"repos/{REPO}/labels"
    assert "name=agk:review" in writes[0][2]


def test_ac1_a_push_to_the_default_branch_routes_every_open_pull_request(proj, stub, tmp_path):
    """REQ-039 AC1: rule 1 (a new conflict is seen at once)."""
    stub.pull(7)
    stub.pull(8, mergeable="dirty")
    stub.open_list([7, 8])
    event = {"ref": "refs/heads/main", "repository": REPO_INFO}
    proc = run_router(proj, stub, tmp_path, "push", event)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    posted = {
        w[1].split("/")[-2]: w[2] for w in stub.writes() if w[0] == "POST" and "/issues/" in w[1]
    }
    assert "labels[]=agk:review" in posted["7"] and "labels[]=agk:conflict" in posted["8"]


def test_ac1_a_push_to_another_branch_routes_nothing(proj, stub, tmp_path):
    """REQ-039 AC1: rule 1 (only the default branch)."""
    stub.pull(7)
    stub.open_list([7])
    event = {"ref": "refs/heads/feature", "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "push", event)
    assert stub.writes() == [] and not any("pulls/7" in c[1] for c in stub.calls())


def test_ac1_a_comment_on_a_pull_request_routes_it_and_one_on_an_issue_does_not(
    proj, stub, tmp_path
):
    """REQ-039 AC1: rule 1 (issue_comment)."""
    stub.pull(7)
    on_issue = {"issue": {"number": 7}, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "issue_comment", on_issue)
    # the only call: the read of the open pull requests for the pipeline document (SPEC-0036)
    assert [c[1].split("?")[0] for c in stub.calls()] == [f"repos/{REPO}/pulls"]
    assert stub.writes() == []
    on_pull = {"issue": {"number": 7, "pull_request": {}}, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "issue_comment", on_pull)
    assert any(w[0] == "POST" for w in stub.writes())


def test_ac1_a_finished_workflow_routes_its_pull_requests_or_all_on_the_default_branch(
    proj, stub, tmp_path
):
    """REQ-039 AC1: rule 1 (workflow_run completed)."""
    stub.pull(7)
    stub.pull(8)
    stub.open_list([7, 8])
    run = {"head_branch": "feature", "head_sha": HEAD, "pull_requests": [{"number": 7}]}
    payload = {"workflow_run": run, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "workflow_run", payload)
    touched = {w[1].split("/")[-2] for w in stub.writes() if "/issues/" in w[1]}
    assert touched == {"7"}
    again = {"head_branch": "main", "head_sha": HEAD, "pull_requests": []}
    payload = {"workflow_run": again, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "workflow_run", payload)
    touched = {w[1].split("/")[-2] for w in stub.writes() if "/issues/" in w[1]}
    assert touched == {"7", "8"}


def test_ac1_a_merged_or_closed_pull_request_keeps_its_last_label(proj, stub, tmp_path):
    """REQ-039 AC1: rule 2 (nothing to route once it is over)."""
    stub.pull(7, state="closed", merged="2026-10-25T10:00:00Z", labels=["agk:ready"])
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    run_router(proj, stub, tmp_path, "pull_request", event)
    assert stub.writes() == []


def test_ac2_the_router_writes_labels_and_nothing_else(proj, stub, tmp_path):
    """REQ-039 AC2: rule 8 (no comment, no review, no merge, no issue)."""
    stub.pull(7, labels=["agk:fix"])
    stub.pull(8, mergeable="dirty")
    stub.open_list([7, 8])
    run_router(proj, stub, tmp_path, "push", {"ref": "refs/heads/main", "repository": REPO_INFO})
    for method, endpoint, _ in stub.writes():
        assert re.search(r"/(issues/\d+/labels(/.+)?|labels)$", endpoint), (method, endpoint)
    assert not any("merge" in c[1] or "reviews" in c[1] and c[0] != "GET" for c in stub.calls())


def test_ac2_a_failed_read_writes_nothing_and_fails_naming_the_rule(proj, stub, tmp_path):
    """REQ-039 AC2: rule 1 (a pull request that cannot be read is reported, never guessed)."""
    stub.pull(7)
    stub.fixtures[f"repos/{REPO}/pulls/7"] = "FAIL"
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    proc = run_router(proj, stub, tmp_path, "pull_request", event)
    assert proc.returncode == 1 and "FAIL route" in proc.stdout and "rule" in proc.stdout
    assert stub.writes() == []


def test_ac1_the_command_line_prints_the_label_and_writes_nothing_with_dry_run(
    proj, stub, tmp_path
):
    """REQ-039 AC1: rule 2 (route.py --pr N --dry-run)."""
    stub.pull(7)
    proc = run_router(proj, stub, tmp_path, "workflow_dispatch", {}, "--pr", "7", "--dry-run")
    assert proc.returncode == 0 and proc.stdout.strip().endswith("agk:review"), proc.stdout
    assert stub.writes() == []


# --- the workflow (rules 1 and 8; AC2) ---------------------------------------------------------


def workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_ac2_the_workflow_is_triggered_by_the_four_events_and_not_by_a_label_change():
    """REQ-039 AC2: rule 1 (a label set with GITHUB_TOKEN starts nothing; none is listened to)."""
    text = workflow()
    on = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert re.search(
        r"pull_request:\n\s+types: \[opened, synchronize, reopened, edited, closed\]", on
    )
    assert re.search(r"issue_comment:\n\s+types: \[created\]", on)
    assert re.search(
        r"workflow_run:\n(?:\s+#[^\n]*\n)*\s+workflows: \[[^\]]+\]\n\s+types: \[completed\]", on
    )
    assert re.search(r"\n  push:", on)
    assert "labeled" not in on and "pull_request_target" not in text


def test_ac2_the_workflow_holds_only_the_five_permissions():
    """REQ-039 AC2: rule 1 (read checks and statuses, write labels, nothing else)."""
    text = workflow()
    block = text.split("\npermissions:\n", 1)[1].split("\n\n", 1)[0].split("\njobs:", 1)[0]
    held = dict(re.findall(r"^\s{2}([a-z-]+): (read|write)$", block, re.MULTILINE))
    assert held == {
        "contents": "read",
        "pull-requests": "write",
        "issues": "write",
        "checks": "read",
        "statuses": "read",
    }
    assert "write-all" not in text and "actions: write" not in text


def test_ac2_the_workflow_runs_no_code_of_the_pull_request_and_no_agent():
    """REQ-039 AC2: rule 1 and 8 (the checkout is the default branch; route.py is the only step)."""
    text = workflow()
    assert "ref: ${{ github.event.repository.default_branch }}" in text
    assert "github.event.pull_request.head" not in text and "head_ref" not in text
    assert text.count("python3 scripts/agk/route.py") == 1
    for word in ("claude", "anthropic", "openai", "model"):
        assert word not in text.lower().replace("pull_request_target", ""), word
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in text
    assert re.search(r"uses: actions/checkout@[0-9a-f]{40}", text)
    assert route.ROUTER_JOB in re.findall(r"^  ([a-z-]+):$", text, re.MULTILINE)


def test_ac2_the_router_is_installed_and_names_no_project():
    """REQ-039 AC2: rules 1 and 12 (a verbatim kit file, no project or runtime named)."""
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert ".github/workflows/agk-route.yml" in manifest["verbatim"]
    assert "scripts/agk/route.py" in manifest["verbatim"]


def test_ac2_a_read_only_token_skips_the_label_write_and_exits_zero(proj, stub, tmp_path):
    """REQ-039 AC2: rule 1 (a fork's pull request gets a read-only token: 403 on every write)."""
    stub.pull(7)
    stub.pull(8)
    stub.open_list([7, 8])
    event = {"ref": "refs/heads/main", "repository": REPO_INFO}
    proc = run_router(proj, stub, tmp_path, "push", event, GH_STUB_FORBID="1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "skipped (read-only token)" in proc.stdout
    assert "FAIL" not in proc.stdout


def test_ac2_any_other_failed_write_still_fails_naming_the_rule(proj, stub, tmp_path):
    """REQ-039 AC2: rule 1 (only a 403 is a skip)."""
    stub.pull(7)
    (stub.bin / "gh").write_text(STUB.replace("(HTTP 403)", "(HTTP 500)"), encoding="utf-8")
    event = {"pull_request": {"number": 7}, "repository": REPO_INFO}
    proc = run_router(proj, stub, tmp_path, "pull_request", event, GH_STUB_FORBID="1")
    assert proc.returncode == 1 and "FAIL route" in proc.stdout and "rule 2" in proc.stdout


def test_ac2_the_step_skips_cleanly_when_route_py_is_not_on_the_default_branch():
    """REQ-039 AC2: rule 1 (the workflow lands before its script in a project that installs it)."""
    text = workflow()
    step = text.split("      - name: Route\n", 1)[1]
    assert "if [ -f scripts/agk/route.py ]; then" in step
    assert "python3 scripts/agk/route.py" in step.split("then", 1)[1].split("else", 1)[0]
    assert "nothing to route" in step.split("else", 1)[1]
