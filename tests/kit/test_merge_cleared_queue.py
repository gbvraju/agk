"""merge_cleared.py with GitHub's merge queue (brief #972, ADR-0417, amendment 158 of SPEC-0039).

With `[flow] merge_queue = true` in GitHub mode the guarded command applies every hold of today
and then adds the cleared head to GitHub's merge queue, pinned to its sha, instead of merging it;
it does so only inside GitHub Actions (the merger job), since the one call is GraphQL and a session
stays REST-only. `governance` and `proof` run on `merge_group`; the merger job has a timeout; a
batch that fails posts one line on the pull request GitHub removed; `doctor.py` prints
`merge queue: on|off`. Every test runs on a git repository in `tmp_path`, saved responses and a
fake `gh` that also answers GraphQL. No network; invented logins, addresses at example.com.
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_merge_cleared_verdict import (
    GREEN_RUNS,
    HEAD,
    ON,
    REPO,
    SCRIPT,
    SHA12,
    calls,
    cleared,
    fake_gh,
    repo,
    toml,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import doctor as doctor_module  # noqa: E402

WORKFLOWS = ROOT / ".github" / "workflows"
QUEUE_ON = ON + "merge_queue = true\n"
NODE = "PR_kwExampleNode7"  # the pull request's GraphQL id, as REST answers it (`node_id`)
QUEUE_SHA = "1a2b3c4d5e" * 4  # the queue's commit
QUEUE_BRANCH = f"gh-readonly-queue/main/pr-7-{HEAD}"

GRAPHQL = """
import json, sys
args = sys.argv[1:]
if args[:2] == ['api', 'graphql']:
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(args) + '\\n')
    data = json.load(open(SAVED, encoding='utf-8'))
    queue = data.get('queue', {})
    query = next((a.split('=', 1)[1] for a in args if a.startswith('query=')), '')
    if 'enqueuePullRequest' in query:
        if queue.get('error'):
            sys.stderr.write('gh: %s\\n' % queue['error']); sys.exit(1)
        out = {'data': {'enqueuePullRequest': {'mergeQueueEntry': {'state': 'QUEUED', 'position': 1}}}}
    else:
        out = {'data': {'repository': {'pullRequest': {
            'id': data['pull'].get('node_id'), 'headRefOid': data['pull']['head']['sha'],
            'isInMergeQueue': bool(queue.get('in_queue'))}}}}
    print(json.dumps(out)); sys.exit(0)
"""


def queue_gh(tmp_path: Path, **saved):
    """The fake `gh` of test_merge_cleared_verdict with a GraphQL answer in front of it."""
    pull = saved.pop("pull", None) or {
        "number": 7,
        "node_id": NODE,
        "head": {"sha": HEAD},
        "state": "open",
        "draft": False,
        "labels": [],
        "mergeable_state": "clean",
        "body": "Brief: #500\nAdvances: REQ-046\n",
    }
    bin_dir, log = fake_gh(tmp_path, pull=pull, **saved)
    script = bin_dir / "gh"
    text = script.read_text(encoding="utf-8")
    first, _, rest = text.partition("\n")
    header, _, body = rest.partition("\n")
    script.write_text(f"{first}\n{header}\n{GRAPHQL}\n{body}", encoding="utf-8")
    return bin_dir, log


def run(root: Path, bin_dir: Path, *args: str, actions: bool = True):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI", "GITHUB_ACTIONS", "AGK_MERGE_TOKEN")
    }
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    temp = bin_dir.parent / "temp"
    temp.mkdir(exist_ok=True)
    env["TMPDIR"] = env["TEMP"] = env["TMP"] = str(temp)
    if actions:
        env["GITHUB_ACTIONS"] = "true"
        env["AGK_MERGE_TOKEN"] = "example-merge-token"  # nosec B105 - an invented placeholder
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True, env=env
    )


def queued_run(tmp_path: Path, main: str = toml(QUEUE_ON), actions: bool = True, **saved):
    saved.setdefault("comments", [cleared()])
    root = repo(tmp_path, main)
    bin_dir, log = queue_gh(tmp_path, **saved)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD, actions=actions)
    return proc, calls(log)


def graphql(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if c[:2] == ["api", "graphql"]]


def enqueues(made: list[list[str]]) -> list[list[str]]:
    return [c for c in graphql(made) if any("enqueuePullRequest" in a for a in c)]


def merges(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if "PUT" in c]


# --- (a) a cleared head is queued with its exact sha, not merged ----------------------------------


def test_a_cleared_head_is_queued_pinned_to_its_sha_and_not_merged(tmp_path):
    """REQ-046: brief #972 answers 2 and 7a (amendment 158 item 2)."""
    proc, made = queued_run(tmp_path)
    assert proc.stdout.strip() == f"merge-cleared #7 {SHA12}: queued", proc.stdout + proc.stderr
    assert proc.returncode == 0
    assert merges(made) == []
    [call] = enqueues(made)
    assert f"pullRequestId={NODE}" in call
    assert f"expectedHeadOid={HEAD}" in call


def test_a_head_already_in_the_queue_is_not_queued_twice(tmp_path):
    """REQ-046: brief #972 answer 2 (`already queued`, nothing done)."""
    proc, made = queued_run(tmp_path, queue={"in_queue": True})
    assert proc.stdout.strip() == f"merge-cleared #7 {SHA12}: already queued"
    assert proc.returncode == 0
    assert enqueues(made) == [] and merges(made) == []


def test_a_head_that_moved_is_refused_by_the_queue(tmp_path):
    """REQ-046: amendment 158 item 2 (`refused: head moved`, exit 3)."""
    error = "Expected head oid does not match the pull request's head (HTTP 200)"
    proc, made = queued_run(tmp_path, queue={"error": error})
    assert re.fullmatch(rf"merge-cleared #7 {SHA12}: refused: head moved \(.+\)", proc.stdout.strip())
    assert proc.returncode == 3
    assert merges(made) == []


def test_a_queue_call_that_fails_otherwise_is_refused_naming_the_rule(tmp_path):
    """REQ-046: amendment 158 item 2 (a reason names the rule, never a value)."""
    proc, made = queued_run(tmp_path, queue={"error": "Something went wrong (HTTP 502)"})
    assert proc.stdout.strip().startswith(f"merge-cleared #7 {SHA12}: refused: ")
    assert "rule 2a" in proc.stdout and "Something" not in proc.stdout
    assert proc.returncode != 0 and merges(made) == []


# --- (b) every hold of today still holds first -----------------------------------------------------

HOLDS = [
    ("no verdict", {"comments": []}, ": held: "),
    (
        "a red check",
        {"runs": [{**GREEN_RUNS[0], "conclusion": "failure"}, GREEN_RUNS[1]]},
        ": held: ",
    ),
    ("no record issue", {"issues": []}, ": held: no record issue (rule 7)"),
    ("governance of the would-be merge", {"premerge_exit": 2}, ": held: the merge with"),
]


@pytest.mark.parametrize(("name", "saved", "expected"), HOLDS, ids=[h[0] for h in HOLDS])
def test_every_hold_of_today_holds_before_the_queue(tmp_path, name, saved, expected):
    """REQ-046: brief #972 answer 7b (amendment 158 item 2: the holds, in the same order)."""
    proc, made = queued_run(tmp_path, **saved)
    assert expected in proc.stdout, proc.stdout + proc.stderr
    assert proc.returncode == 3
    assert graphql(made) == [] and merges(made) == []


# --- (c) with the queue off, or in local mode, it merges as today ----------------------------------


def test_with_the_queue_off_it_merges_as_today(tmp_path):
    """REQ-046: brief #972 answer 7c."""
    proc, made = queued_run(tmp_path, main=toml(ON))
    assert f"merge-cleared #7 {SHA12}: merged " in proc.stdout, proc.stdout + proc.stderr
    assert len(merges(made)) == 1 and graphql(made) == []


def test_in_local_mode_the_queue_setting_is_not_read_and_it_merges_as_today(tmp_path):
    """REQ-046: brief #972 contexts (local: `merge_queue` is read only in GitHub mode)."""
    record = {"number": 42, "title": "Local mode since 2026-11-01", "body": "", "labels": []}
    proc, made = queued_run(tmp_path, issues=[record], actions=False)
    assert graphql(made) == []
    assert ": queued" not in proc.stdout
    assert "rule 2a" not in proc.stdout, proc.stdout


# --- (d) the queue call outside Actions is refused --------------------------------------------------


def test_the_queue_call_outside_actions_is_refused_naming_the_rule(tmp_path):
    """REQ-046: brief #972 answers 2 and 7d (sessions stay REST-only)."""
    proc, made = queued_run(tmp_path, actions=False)
    out = proc.stdout.strip()
    assert out.startswith(f"merge-cleared #7 {SHA12}: refused: "), proc.stdout + proc.stderr
    assert "rule 2a" in out and "GitHub Actions" in out
    assert proc.returncode == 1
    assert graphql(made) == [] and merges(made) == []


def test_the_merger_event_no_longer_stops_at_the_queue_setting(tmp_path):
    """REQ-046: brief #972 answer 3 (the event job calls the command; the command decides)."""
    root = repo(tmp_path, toml(QUEUE_ON))
    bin_dir, _ = queue_gh(tmp_path, comments=[cleared()])
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps({"issue": {"number": 7, "pull_request": {}}, "comment": cleared()}),
        encoding="utf-8",
    )
    proc = run(root, bin_dir, "--event", str(event), "--event-name", "issue_comment")
    assert proc.stdout.strip() == f"7 {HEAD}", proc.stdout + proc.stderr


# --- answer 4: a pull request removed from the queue ------------------------------------------------


def removal_event(conclusion: str = "failure", event: str = "merge_group") -> dict:
    return {
        "workflow_run": {
            "name": "governance",
            "event": event,
            "conclusion": conclusion,
            "head_sha": QUEUE_SHA,
            "head_branch": QUEUE_BRANCH,
        }
    }


def removed_run(tmp_path: Path, payload: dict, **saved):
    root = repo(tmp_path, toml(QUEUE_ON))
    bin_dir, log = queue_gh(tmp_path, **saved)
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    proc = run(root, bin_dir, "--queue-removed", "--event", str(path))
    return proc, calls(log)


def posted_comments(made: list[list[str]]) -> list[str]:
    found = []
    for call in made:
        if "POST" in call and any(a.endswith("/comments") for a in call):
            found += [a.split("=", 1)[1] for a in call if a.startswith("body=")]
    return found


def test_a_failed_queue_run_posts_one_removal_line(tmp_path):
    """REQ-046: brief #972 answer 4 (amendment 158 item 4)."""
    proc, made = removed_run(tmp_path, removal_event())
    expected = f"Removed from the merge queue: governance failed on {QUEUE_SHA[:12]}"
    assert [b.splitlines()[0] for b in posted_comments(made)] == [expected], proc.stdout + proc.stderr
    assert f"repos/{REPO}/issues/7/comments" in [a for c in made for a in c]
    assert proc.returncode == 0


def test_the_same_removal_is_never_posted_twice(tmp_path):
    """REQ-046: amendment 158 item 4 (never the same line twice for one queue sha)."""
    line = f"Removed from the merge queue: governance failed on {QUEUE_SHA[:12]}"
    seen = [{"id": 3, "body": line, "user": {"login": "example-bot"}}]
    proc, made = removed_run(tmp_path, removal_event(), comments=seen)
    assert posted_comments(made) == [], proc.stdout + proc.stderr
    assert proc.returncode == 0


@pytest.mark.parametrize(
    "payload",
    [
        removal_event(conclusion="success"),
        removal_event(event="pull_request"),
        {"workflow_run": {**removal_event()["workflow_run"], "head_branch": "feature"}},
        {},
    ],
    ids=["green", "not-a-queue-run", "not-a-queue-branch", "empty"],
)
def test_anything_but_a_failed_queue_run_posts_nothing(tmp_path, payload):
    """REQ-046: brief #972 answer 4 (nothing else is written)."""
    proc, made = removed_run(tmp_path, payload)
    assert posted_comments(made) == [], proc.stdout + proc.stderr
    assert proc.returncode == 0


# --- answer 1 and 3: the workflows -----------------------------------------------------------------


def on_block(name: str) -> str:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    found = re.search(r"^on:\n((?:[ #].*\n|\n)*)", text, re.MULTILINE)
    assert found, name
    return found.group(1)


@pytest.mark.parametrize("name", ["governance.yml", "proof.yml"])
def test_governance_and_proof_run_on_the_merge_queue(name):
    """REQ-057: brief #972 answers 1 and 7 (the `merge_group` trigger)."""
    block = on_block(name)
    assert re.search(r"^  merge_group:\n    types: \[checks_requested\]$", block, re.MULTILINE), block
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    assert "github.event_name == 'merge_group'" in text  # the job is not skipped on the queue's ref


def test_no_other_workflow_runs_on_the_merge_queue():
    """REQ-057: amendment 158 item 9 (`merge_group` for governance and proof only)."""
    for path in sorted(WORKFLOWS.glob("*.yml")):
        if path.name in ("governance.yml", "proof.yml"):
            continue
        assert "merge_group:" not in on_block(path.name), path.name


def test_the_job_and_check_names_do_not_change():
    """REQ-057: brief #972 answer 1 (the required checks keep their names)."""
    for name, job in (("governance.yml", "governance"), ("proof.yml", "proof")):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert re.search(rf"^name: {job}$", text, re.MULTILINE)
        assert re.search(rf"^jobs:\n  {job}:$", text, re.MULTILINE)


def test_the_pull_request_body_checks_run_only_on_a_pull_request():
    """REQ-057: brief #972 answer 1 (skipped on `merge_group`; they passed on the head)."""
    text = (WORKFLOWS / "governance.yml").read_text(encoding="utf-8")
    for step in ("PR body shape", "Open briefs"):
        found = re.search(rf"- name: {step}\n\s+if: \$\{{\{{ (.+) \}}\}}", text)
        assert found and "github.event_name == 'pull_request'" in found.group(1), step


def test_the_merger_job_has_a_timeout():
    """REQ-046: brief #972 answer 3 (a waiting run can never block the queue for hours)."""
    text = (WORKFLOWS / "merger.yml").read_text(encoding="utf-8")
    job = text.split("\n  merger:\n", 1)[1].split("\n  sweep-gate:\n", 1)[0]
    assert re.search(r"^    timeout-minutes: 30$", job, re.MULTILINE), job[:400]
    assert "--queue-removed" in text


def test_no_workflow_or_guide_names_agk_verdict_a_required_check_of_the_queue():
    """REQ-046: amendment 158 items 3 and 9."""
    guide = (ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    section = guide.split("## The merge queue", 1)[1]
    assert "`governance` and `proof`" in section
    assert "agk/verdict" not in section.split("required", 1)[1].split("\n\n", 1)[0]


# --- answers 5 and 6: the setting, the doctor line and the guide ------------------------------------


def test_the_setting_is_committed_off_with_its_adr():
    """REQ-046: brief #972 answer 5 (`merge_queue = false`, commented with ADR-0417)."""
    text = (ROOT / "agk.toml").read_text(encoding="utf-8")
    flow = text.split("\n[flow]\n", 1)[1].split("\n[", 1)[0]
    found = re.search(r"^merge_queue = false\s*#.*ADR-0417", flow, re.MULTILINE)
    assert found, "merge_queue = false with ADR-0417 in [flow]"


@pytest.mark.parametrize(
    ("flow", "status", "message"),
    [
        ({}, "ok", "off"),
        ({"merge_queue": False}, "ok", "off"),
        ({"merge_queue": True}, "ok", "on"),
        ({"merge_queue": "not-for-output"}, "fail", None),
    ],
)
def test_doctor_prints_merge_queue_on_or_off(flow, status, message):
    """REQ-046: brief #972 answer 5 (from the setting alone, no ruleset call)."""
    result = doctor_module.merge_queue_result({"flow": flow})
    assert result.status == status
    if message is not None:
        assert result.message == message
    else:
        assert "merge_queue" in result.message and "not-for-output" not in result.message
    severity, ok_text, _fail, _fix = doctor_module.CHECKS["merge-queue-setting"]
    assert ok_text == "merge queue: " and severity == "warn"


def test_the_guide_gives_the_ruleset_settings_and_the_switch_over_order():
    """REQ-046: brief #972 answer 6 and the narrowing on #972 (organization-owned only)."""
    guide = (ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    section = guide.split("## The merge queue", 1)[1].split("\n## ", 1)[0]
    for words in (
        "Require merge queue",
        "Squash",
        "Maximum pull requests to build: 5",
        "Require branches to be up to date before merging",
        "organization",
        "merge_queue = true",
    ):
        assert words in section, words
    order = [section.index(f"({n})") for n in ("i", "ii", "iii")]
    assert order == sorted(order)
