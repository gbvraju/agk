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
    """REQ-039 AC1: rule 2 (agk:merge-ready, ADR-0385)."""
    cleared = said(1, "boss", f"Verdict: cleared {HEAD[:7]}")
    assert route.decide(facts(comments=[cleared])) == "agk:merge-ready"


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
    assert route.decide(facts(comments=[said(1, "boss", body)], commit=commit)) == "agk:merge-ready"
    commit["files"][0]["patch"] = "@@ -1 +1 @@\n-- Status: Proposed\n+- Status: Rejected\n"
    assert route.decide(facts(comments=[said(1, "boss", body)], commit=commit)) != "agk:merge-ready"


def test_ac1_a_cleared_head_that_approves_a_spec_waits_for_a_person():
    """REQ-039 AC1: rule 2 (agk:approve) until an approver's Approve: names the spec."""
    cleared = said(1, "boss", f"Verdict: cleared {HEAD[:7]}")
    assert route.decide(facts(comments=[cleared], files=approved_spec())) == "agk:approve"
    by_person = said(2, "maintainer", f"Approve: {OLD[:7]} SPEC-0032")
    both = facts(comments=[cleared, by_person], files=approved_spec())
    assert route.decide(both) == "agk:merge-ready"


def test_ac1_an_approve_review_body_by_an_approver_counts_and_other_accounts_do_not():
    """REQ-039 AC1: rule 2 (Approve: in a review body counts; an unlisted account never does)."""
    cleared = said(1, "boss", f"Verdict: cleared {HEAD[:7]}")
    review = {"user": {"login": "maintainer"}, "body": f"Approve: {HEAD[:7]} SPEC-0032"}
    assert route.decide(facts(comments=[cleared], reviews=[review], files=approved_spec())) == (
        "agk:merge-ready"
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
        r"pull_request:\n\s+types: \[opened, synchronize, reopened, closed\]",
        on,  # brief #369
    )
    assert re.search(r"issue_comment:\n\s+types: \[created, edited\]", on)  # brief #836
    assert re.search(
        r"workflow_run:\n(?:\s+#[^\n]*\n)*\s+workflows: \[[^\]]+\]\n\s+types: \[completed\]", on
    )
    assert re.search(r"\n  push:", on)
    assert "labeled" not in on and "pull_request_target" not in text


def test_ac2_the_workflow_holds_only_the_six_permissions():
    """REQ-039 AC2: rule 1 (read checks and statuses, write labels, nothing else), and brief
    #1116 (ADR-0476): `actions: write`, to start the merger once for a pull request."""
    text = workflow()
    block = text.split("\npermissions:\n", 1)[1].split("\n\n", 1)[0].split("\njobs:", 1)[0]
    held = dict(re.findall(r"^\s{2}([a-z-]+): (read|write)$", block, re.MULTILINE))
    assert held == {
        "contents": "read",
        "pull-requests": "write",
        "issues": "write",
        "checks": "read",
        "statuses": "read",
        "actions": "write",
    }
    assert "write-all" not in text


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


# --- one red default branch, one alarm: green closes every copy (brief #916) -----------------

RED_TIP = "9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"
RED_URL = "https://github.com/acme/widgets/actions/runs/42"
RED_TITLE = "The default branch is red"
ON_MAIN = {"ref": "refs/heads/main", "repository": REPO_INFO}
PERSON = "person-example"


def red_tip(stub: Stub, checks: list[dict]) -> None:
    stub.fixtures[f"repos/{REPO}/branches/main"] = {"commit": {"sha": RED_TIP}}
    stub.fixtures[f"repos/{REPO}/commits/{RED_TIP}/check-runs"] = {
        "total_count": len(checks),
        "check_runs": checks,
    }
    stub.fixtures[f"repos/{REPO}/commits/{RED_TIP}/status"] = {"statuses": []}


def failed(name: str = "proof") -> dict:
    return {"name": name, "status": "completed", "conclusion": "failure", "html_url": RED_URL}


def alarm(number: int, login: str, sha: str = RED_TIP) -> dict:
    return {
        "number": number,
        "title": RED_TITLE,
        "body": route.red_body("proof", sha, RED_URL) + "\n---\n_a session footer_\n",
        "user": {"login": login},
    }


def issue_calls(stub: Stub) -> list[list]:
    return [w for w in stub.writes() if "/labels" not in w[1]]


def closes(stub: Stub) -> list[str]:
    return [w[1] for w in issue_calls(stub) if w[0] == "PATCH" and "state=closed" in w[2]]


def test_ac5_916c_a_red_head_with_no_copy_opens_exactly_one_alarm(proj, stub, tmp_path):
    """REQ-039 AC5: brief #916 test 5(c) (no copy open: the router opens exactly one)."""
    red_tip(stub, [ok("governance"), failed()])
    proc = run_router(proj, stub, tmp_path, "push", ON_MAIN)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    writes = issue_calls(stub)
    assert [(w[0], w[1]) for w in writes] == [("POST", f"repos/{REPO}/issues")]
    assert f"title={RED_TITLE}" in writes[0][2]


def test_ac5_916d_green_closes_a_copy_by_another_login_and_the_routers_own(proj, stub, tmp_path):
    """REQ-039 AC5: brief #916 answer 3 and test 5(d) (every same-shape copy, whoever wrote it,
    closed as completed; the 9 Nov history: a person's copy, then the router's, for one head)."""
    red_tip(stub, [ok("governance"), ok("proof")])
    stub.fixtures[f"repos/{REPO}/issues"] = [alarm(909, PERSON), alarm(911, "github-actions[bot]")]
    proc = run_router(proj, stub, tmp_path, "push", ON_MAIN)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    writes = issue_calls(stub)
    assert sorted(w[1] for w in writes) == [f"repos/{REPO}/issues/909", f"repos/{REPO}/issues/911"]
    for w in writes:
        assert w[0] == "PATCH" and "state=closed" in w[2] and "state_reason=completed" in w[2]
    assert not any(w[1].endswith("/comments") for w in stub.writes())


def test_ac5_916d_green_closes_only_the_shape_title_priority_0_and_advances_none(
    proj, stub, tmp_path
):
    """REQ-039 AC5: brief #916 answer 3 (the shape is the title and the two lines; a pull request,
    another title or a body without the two lines is left open)."""
    red_tip(stub, [ok("governance"), ok("proof")])
    no_pair = {**alarm(5, PERSON), "body": "The default branch looked red to me.\n"}
    renamed = {**alarm(6, PERSON), "title": "The default branch is not red"}
    pull = {**alarm(7, PERSON), "pull_request": {}}
    half = {**alarm(8, PERSON), "body": "Priority: 0\nTouches: **\n"}
    stub.fixtures[f"repos/{REPO}/issues"] = [no_pair, renamed, pull, half, alarm(9, PERSON)]
    run_router(proj, stub, tmp_path, "push", ON_MAIN)
    assert closes(stub) == [f"repos/{REPO}/issues/9"]


def test_ac5_916e_red_or_pending_closes_no_copy(proj, stub, tmp_path):
    """REQ-039 AC5: brief #916 answer 3 and test 5(e) (never closed while red or pending; the red
    run still opens the router's own alarm, as today, and updates no person's copy)."""
    copies = [alarm(909, PERSON), alarm(911, "github-actions[bot]", sha=OLD)]
    stub.fixtures[f"repos/{REPO}/issues"] = copies
    red_tip(stub, [ok("governance"), failed()])
    proc = run_router(proj, stub, tmp_path, "push", ON_MAIN)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert closes(stub) == []
    assert [(w[0], w[1]) for w in issue_calls(stub)] == [("PATCH", f"repos/{REPO}/issues/911")]
    running = {"name": "proof", "status": "in_progress", "conclusion": None}
    for checks in ([ok("governance"), running], []):
        (stub.dir / "calls.log").unlink(missing_ok=True)
        red_tip(stub, checks)
        run_router(proj, stub, tmp_path, "push", ON_MAIN)
        assert issue_calls(stub) == [], checks


def test_a_conductor_fallback_cleared_verdict_is_ready_like_today():
    """REQ-046: brief #1013 answer 4 (ADR-0431 decision 3): the router reads the fallback ending
    as the same verdict."""
    cleared = said(1, "boss", f"Verdict: cleared {HEAD} (conductor fallback)")
    assert route.decide(facts(comments=[cleared])) == "agk:merge-ready"


# --- a draft that waits on the owner (brief #1043, ADR-0442) -----------------------------------

EARLY = {"commit": {"committer": {"date": "2026-10-25T09:00:00Z"}}}
LATER = {"commit": {"committer": {"date": "2026-10-25T11:00:00Z"}}}
ASKED = "Question: Q-9-1 for the maintainers: may the builder edit a file the cloud refuses?"


def test_a_draft_with_an_open_question_for_the_maintainers_is_question():
    """REQ-037: brief #1043 answers 1, 2 and test 3(a) (any author; a draft shows agk:question)."""
    asked = said(4, "builder", ASKED)
    assert route.pr_state(facts(draft=True, comments=[asked], commit=EARLY)) == (
        "agk:question",
        "owner",
    )
    stranger = said(4, "stranger", ASKED)
    assert route.decide(facts(draft=True, comments=[stranger], commit=EARLY)) == "agk:question"


def test_a_maintainer_answer_closes_the_question_for_the_maintainers():
    """REQ-037: brief #1043 answer 1 and test 3(b) (an approver's answer or Approve: closes it)."""
    asked = said(4, "builder", ASKED)
    for line in ("Maintainer answer: yes", "Approve: yes"):
        answer = said(5, "maintainer", line)
        got = route.decide(facts(draft=True, comments=[asked, answer], commit=EARLY))
        assert got == "agk:build", line
    other = said(5, "stranger", "Maintainer answer: yes")
    got = route.decide(facts(draft=True, comments=[asked, other], commit=EARLY))
    assert got == "agk:question"


def test_a_later_push_closes_the_question_for_the_maintainers():
    """REQ-037: brief #1043 answer 1 and test 3(c) (a head pushed after the question)."""
    asked = said(4, "builder", ASKED)
    assert route.decide(facts(draft=True, comments=[asked], commit=LATER)) == "agk:build"


def test_a_plain_question_on_a_draft_stays_build():
    """REQ-037: brief #1043 answer 1 and test 3(d) (only `for the maintainers` asks the owner)."""
    plain = said(4, "builder", "Question: Q-9-1 may the builder rename a test?")
    assert route.decide(facts(draft=True, comments=[plain], commit=EARLY)) == "agk:build"
    later_line = said(4, "builder", "Question: Q-9-1 a line\n\nfor the maintainers: in the body")
    assert route.decide(facts(draft=True, comments=[later_line], commit=EARLY)) == "agk:build"
    report = said(4, "builder", "Report: abc for the maintainers")
    assert route.decide(facts(draft=True, comments=[report], commit=EARLY)) == "agk:build"


def test_an_owner_needed_line_on_a_draft_is_question():
    """REQ-037: brief #1043 answer 2 and test 3(e) (`Owner needed:` by a verdict author)."""
    asked = said(4, "boss", "Owner needed: may this change the workflow?")
    assert route.decide(facts(draft=True, comments=[asked], commit=EARLY)) == "agk:question"
    unlisted = said(4, "stranger", "Owner needed: anything")
    assert route.decide(facts(draft=True, comments=[unlisted], commit=EARLY)) == "agk:build"


# --- a stopped builder hands over (brief #1071, amendment 162, ADR-0453) -----------------------

FIX = said(1, "boss", f"Verdict: fix list {HEAD[:7]}\n\n1. do this")
BRIEF_BODY = "Brief: #9\nSummary: A person sees who acts next.\n"


def handing(cid: int, reason: str | None, login: str = "builder") -> dict:
    tail = f": {reason}" if reason is not None else ""
    return said(cid, login, f"Report: {HEAD[:12]} handing over{tail}\n\nUsage: not shown")


def test_1071a_a_handing_over_report_on_a_fix_list_is_handover():
    """REQ-039: brief #1071 test (a) (`handing over: six hours` in `agk:fix`)."""
    f = facts(comments=[FIX, handing(4, "six hours")], commit=EARLY)
    assert route.pr_state(f) == ("agk:handover", "launcher")
    blocked = facts(comments=[FIX, handing(4, "blocked: the cloud refuses a file")], commit=EARLY)
    assert route.decide(blocked) == "agk:handover"


def test_1071b_the_old_form_with_no_reason_reads_as_six_hours():
    """REQ-039: brief #1071 test (b) and answer 2 (no reason is `six hours`)."""
    assert route.handover_reason(f"Report: {HEAD[:12]} handing over") == "six hours"
    f = facts(comments=[FIX, handing(4, None)], commit=EARLY)
    assert route.decide(f) == "agk:handover"
    draft = facts(draft=True, body=BRIEF_BODY, comments=[handing(4, None)], commit=EARLY)
    assert route.decide(draft) == "agk:handover"


def test_1071c_a_hand_over_to_a_session_or_done_is_not_handover():
    """REQ-039: brief #1071 test (c) (`to <session>` and `done` need no restart)."""
    for reason in ("to cb1048r", "done"):
        f = facts(comments=[FIX, handing(4, reason)], commit=EARLY)
        assert route.decide(f) == "agk:fix", reason
    old = said(4, "builder", f"Report: {HEAD[:7]} handing over to cb1030r (started 11:13Z)")
    assert route.decide(facts(comments=[FIX, old], commit=EARLY)) == "agk:fix"


def test_1071d_a_later_builder_comment_or_a_push_clears_it():
    """REQ-039: brief #1071 test (d) (the next builder's comment or push)."""
    progress = said(5, "builder", f"Progress: {HEAD[:7]} done 1/3; next: 2; Usage: not shown")
    assert route.decide(facts(comments=[FIX, handing(4, None), progress], commit=EARLY)) == (
        "agk:fix"
    )
    assert route.decide(facts(comments=[FIX, handing(4, None)], commit=LATER)) == "agk:fix"


def test_1071e_the_owners_states_keep_their_label():
    """REQ-039: brief #1071 test (e) (`agk:question` and `agk:parked` never become handover)."""
    asked = said(3, "builder", ASKED)
    draft = facts(draft=True, comments=[asked, handing(4, None)], commit=EARLY)
    assert route.decide(draft) == "agk:question"
    parked = facts(labels=["agk:parked"], comments=[FIX, handing(4, None)], commit=EARLY)
    assert route.decide(parked) == "agk:parked"


def test_1071f_a_later_verdict_answer_or_correction_does_not_clear_it():
    """REQ-039: brief #1071 test (f) (the conductor's lines are not a builder's)."""
    for line in (f"Verdict: fix list {HEAD[:7]}\n\n1. again", "Answer: Q-9-1 yes", "Correction: x"):
        f = facts(comments=[FIX, handing(4, None), said(5, "boss", line)], commit=EARLY)
        assert route.decide(f) == "agk:handover", line
    stranger = said(5, "stranger", "Progress: abc done 1/2; next: 2")
    assert route.decide(facts(comments=[FIX, handing(4, None), stranger], commit=EARLY)) == (
        "agk:handover"
    )


def test_1071_only_a_builders_state_becomes_handover_and_the_label_is_known():
    """REQ-039: brief #1071 answers 1 and 3 (a cleared head stays merge-ready; a colour)."""
    cleared = said(5, "boss", f"Verdict: cleared {HEAD[:7]}")
    f = facts(comments=[handing(4, None), cleared], commit=EARLY)
    assert route.decide(f) == "agk:merge-ready"
    stranger = facts(comments=[FIX, handing(4, None, login="stranger")], commit=EARLY)
    assert route.decide(stranger) == "agk:fix"
    assert "agk:handover" in route.LABELS and route.COLORS["agk:handover"]
    assert route.description_of("agk:handover").startswith("AGK: launcher acts next: ")


# --- brief #1101 (ADR-0471): the owner's turn wins over the builder's --------------------------


def fix_list() -> dict:
    return said(1, "boss", f"Verdict: fix list {HEAD[:7]}\n\n1. change nothing until the ruling")


def owner_needed(cid: int = 4) -> dict:
    return said(cid, "boss", "Owner needed: a size ruling on this pull request")


def test_1101a_a_fix_list_and_a_later_open_owner_ask_is_question():
    """REQ-039: brief #1101 answer 4(a) (an open owner ask is decided before `agk:fix`)."""
    assert route.pr_state(facts(comments=[fix_list(), owner_needed()])) == ("agk:question", "owner")
    asked = said(4, "builder", "Question: Q-1101-9 for the maintainers: a ruling, please")
    assert route.decide(facts(comments=[fix_list(), asked])) == "agk:question"


def test_1101a_an_open_owner_ask_wins_over_every_builder_state_but_parked():
    """REQ-039: brief #1101 answer 1 (before `agk:fix` and every other builder state)."""
    red = {"name": "proof", "status": "completed", "conclusion": "failure"}
    asks = [owner_needed()]
    assert route.decide(facts(comments=asks, checks=[ok("governance"), red])) == "agk:question"
    assert route.decide(facts(comments=asks, mergeable_state="dirty")) == "agk:question"
    assert route.decide(facts(comments=asks, body="Brief: #5\n")) == "agk:question"
    assert route.decide(facts(comments=asks, labels=["agk:parked"])) == "agk:parked"


def test_1101b_a_maintainer_answer_by_an_approver_returns_the_state_the_facts_give():
    """REQ-039: brief #1101 answer 4(b) (the answer closes the ask; `agk:fix` returns); a later head
    no longer closes it (brief #1168, ADR-0497)."""
    answer = said(5, "maintainer", "Maintainer answer: keep the size")
    assert route.decide(facts(comments=[fix_list(), owner_needed(), answer])) == "agk:fix"
    stranger = said(5, "stranger", "Maintainer answer: keep the size")
    comments = [fix_list(), owner_needed(), stranger]
    assert route.decide(facts(comments=comments)) == "agk:question"
    later = {"commit": {"committer": {"date": "2026-10-25T11:00:00Z"}}}
    assert route.decide(facts(comments=[fix_list(), owner_needed()], commit=later)) == (
        "agk:question"
    )


def handing_over(cid: int = 6, reason: str = "six hours") -> dict:
    return said(cid, "builder", f"Report: {HEAD[:12]} handing over: {reason}")


def test_1101c_a_hand_over_while_an_owner_ask_is_open_keeps_question():
    """REQ-039: brief #1101 answer 4(c) (an owner state is never replaced by `agk:handover`)."""
    comments = [fix_list(), owner_needed(), handing_over()]
    assert route.pr_state(facts(comments=comments)) == ("agk:question", "owner")
    blocked = [fix_list(), owner_needed(), handing_over(reason="blocked: the owner's ruling")]
    assert route.decide(facts(comments=blocked)) == "agk:question"


def test_1101d_a_hand_over_with_no_owner_ask_still_gives_handover():
    """REQ-039: brief #1101 answer 4(d) (amendment 162 unchanged for a builder's state)."""
    assert route.pr_state(facts(comments=[fix_list(), handing_over()])) == (
        "agk:handover",
        "launcher",
    )
    answered = said(5, "maintainer", "Maintainer answer: keep the size")
    comments = [fix_list(), owner_needed(), answered, handing_over()]
    assert route.decide(facts(comments=comments)) == "agk:handover"


def test_1101_an_owner_state_is_never_replaced_by_handover():
    """REQ-039: brief #1101 answer 1 (`OWNER_STATES` and `state_of`)."""
    assert set(route.OWNER_STATES) == {
        "agk:question",
        "agk:approve",
        "agk:owner-merge",
        "agk:parked",
    }
    assert all(route.ACTOR[label] == "owner" for label in route.OWNER_STATES)
    assert not set(route.OWNER_STATES) & set(route.BUILDER_STATES)
    parked = facts(comments=[fix_list(), handing_over()], labels=["agk:parked"])
    assert route.decide(parked) == "agk:parked"
