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
    comment,
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
        entry = {'state': 'QUEUED', 'position': 1}
        out = {'data': {'enqueuePullRequest': {'mergeQueueEntry': entry}}}
    else:
        out = {'data': {'repository': {'pullRequest': {
            'id': data['pull'].get('node_id'), 'headRefOid': data['pull']['head']['sha'],
            'isInMergeQueue': bool(queue.get('in_queue'))}}}}
    print(json.dumps(out)); sys.exit(0)
"""


PULL = {
    "number": 7,
    "node_id": NODE,
    "head": {"sha": HEAD},
    "state": "open",
    "draft": False,
    "labels": [],
    "mergeable_state": "clean",
    "body": "Brief: #500\nAdvances: REQ-046\n",
}


def queue_gh(tmp_path: Path, **saved):
    """The fake `gh` of test_merge_cleared_verdict with a GraphQL answer in front of it."""
    pull = saved.pop("pull", None) or dict(PULL)
    bin_dir, log = fake_gh(tmp_path, pull=pull, **saved)
    script = bin_dir / "gh"
    text = script.read_text(encoding="utf-8")
    first, _, rest = text.partition("\n")
    header, _, body = rest.partition("\n")
    script.write_text(f"{first}\n{header}\n{GRAPHQL}\n{body}", encoding="utf-8")
    return bin_dir, log


def run(root: Path, bin_dir: Path, *args: str, actions: bool = True, token: bool = True):
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
    if actions and token:
        env["AGK_MERGE_TOKEN"] = "example-merge-token"  # nosec B105 - an invented placeholder
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True, env=env
    )


def queued_run(
    tmp_path: Path,
    main: str = toml(QUEUE_ON),
    actions: bool = True,
    token: bool = True,
    **saved,
):
    saved.setdefault("comments", [cleared()])
    root = repo(tmp_path, main)
    bin_dir, log = queue_gh(tmp_path, **saved)
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD, actions=actions, token=token)
    return proc, calls(log)


def graphql(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if c[:2] == ["api", "graphql"]]


def enqueues(made: list[list[str]]) -> list[list[str]]:
    return [c for c in graphql(made) if any("enqueuePullRequest" in a for a in c)]


def merges(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if "PUT" in c]


# --- (a) a cleared head is queued with its exact sha, not merged ---


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
    assert re.fullmatch(
        rf"merge-cleared #7 {SHA12}: refused: head moved \(.+\)", proc.stdout.strip()
    )
    assert proc.returncode == 3
    assert merges(made) == []


def test_a_queue_call_that_fails_otherwise_is_refused_naming_the_rule(tmp_path):
    """REQ-046: amendment 158 item 2 (a reason names the rule, never a value)."""
    proc, made = queued_run(tmp_path, queue={"error": "Something went wrong (HTTP 502)"})
    assert proc.stdout.strip().startswith(f"merge-cleared #7 {SHA12}: refused: ")
    assert "rule 2a" in proc.stdout and "Something" not in proc.stdout
    assert proc.returncode != 0 and merges(made) == []


# --- (b) every hold of today still holds first ---

HOLDS = [
    ("no verdict", {"comments": []}, ": held: "),
    (
        "a red check",
        {"runs": [{**GREEN_RUNS[0], "conclusion": "failure"}, GREEN_RUNS[1]]},
        ": held: ",
    ),
    ("no record issue", {"issues": []}, ": held: no record issue (rule 7)"),
    ("governance of the would-be merge", {"premerge_exit": 2}, ": held: the merge with"),
    # the hold list of SPEC-0039 rule 5 (verdict item 5 on #993)
    ("a draft", {"pull": {**PULL, "draft": True}}, ": held: draft (rule 5)"),
    (
        "the hold label",
        {"pull": {**PULL, "labels": [{"name": "agk:hold"}]}},
        ": held: hold label (rule 5)",
    ),
    (
        "the approve label",
        {"pull": {**PULL, "labels": [{"name": "agk:approve"}]}},
        ": held: spec approval (rule 5)",
    ),
    (
        "an unmerged dependence",
        {
            "pull": {**PULL, "body": "Brief: #500\nDepends-on: #12\n"},
            "items": {"12": {"number": 12, "state": "open", "pull_request": {}, "pull": {}}},
        },
        ": held: depends-on (rule 5)",
    ),
    ("a conflict", {"pull": {**PULL, "mergeable_state": "dirty"}}, ": held: conflict (rule 5)"),
]

# The REST reads of the holds, each of which must come before any GraphQL call.
HOLD_READS = (
    f"repos/{REPO}/pulls/7",
    f"repos/{REPO}/issues/7/comments",
    f"repos/{REPO}/pulls/7/files",
    f"repos/{REPO}/pulls/7/commits",
)


@pytest.mark.parametrize(("name", "saved", "expected"), HOLDS, ids=[h[0] for h in HOLDS])
def test_every_hold_of_today_holds_before_the_queue(tmp_path, name, saved, expected):
    """REQ-046: brief #972 answer 7b (amendment 158 item 2: the holds, in the same order)."""
    proc, made = queued_run(tmp_path, **saved)
    assert expected in proc.stdout, proc.stdout + proc.stderr
    assert proc.returncode == 3
    assert enqueues(made) == [] and merges(made) == []
    if "premerge_exit" not in saved:  # the queue state is read after the REST holds alone
        assert graphql(made) == []


def test_no_queue_call_comes_before_the_rest_holds(tmp_path):
    """REQ-046: brief #972 answer 7b (the holds first; verdict item 5 on #993)."""
    proc, made = queued_run(tmp_path)
    assert proc.stdout.strip() == f"merge-cleared #7 {SHA12}: queued", proc.stdout + proc.stderr
    first = next(i for i, c in enumerate(made) if c[:2] == ["api", "graphql"])
    for path in HOLD_READS:
        reads = [i for i, c in enumerate(made) if any(a.split("?")[0] == path for a in c)]
        assert reads and max(reads) < first, path


# --- a head the queue removed is held until a new head or verdict (verdict item 3 on #993) ---

REMOVED = f"Removed from the merge queue: governance failed on {QUEUE_SHA[:12]}"


def test_a_head_removed_from_the_queue_is_not_queued_again(tmp_path):
    """REQ-046: amendment 158 item 4 (a removed head needs a new head and a new verdict)."""
    removal = comment(REMOVED, "github-actions[bot]", 8)
    proc, made = queued_run(tmp_path, comments=[cleared(at=5), removal])
    assert proc.stdout.strip() == (
        f"merge-cleared #7 {SHA12}: held: removed from the merge queue since the verdict (rule 2c)"
    ), proc.stdout + proc.stderr
    assert proc.returncode == 3
    assert graphql(made) == [] and merges(made) == []


def test_a_new_verdict_after_the_removal_queues_the_head_again(tmp_path):
    """REQ-046: amendment 158 item 4 (a new verdict lifts the hold)."""
    removal = comment(REMOVED, "github-actions[bot]", 3)
    proc, made = queued_run(tmp_path, comments=[removal, cleared(at=9)])
    assert proc.stdout.strip() == f"merge-cleared #7 {SHA12}: queued", proc.stdout + proc.stderr
    assert len(enqueues(made)) == 1


# --- (c) with the queue off, or in local mode, it merges as today ---


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


# --- (d) the queue call outside Actions is refused ---


def test_the_queue_call_outside_actions_is_refused_naming_the_rule(tmp_path):
    """REQ-046: brief #972 answers 2 and 7d (sessions stay REST-only)."""
    proc, made = queued_run(tmp_path, actions=False)
    out = proc.stdout.strip()
    assert out.startswith(f"merge-cleared #7 {SHA12}: refused: "), proc.stdout + proc.stderr
    assert "rule 2a" in out and "GitHub Actions" in out
    assert proc.returncode == 1
    assert graphql(made) == [] and merges(made) == []


def test_the_queue_call_without_the_merger_token_is_refused(tmp_path):
    """REQ-046: session rule 2 (verdict item 6 on #993: never a session's own login)."""
    proc, made = queued_run(tmp_path, token=False)
    out = proc.stdout.strip()
    assert out.startswith(f"merge-cleared #7 {SHA12}: refused: "), proc.stdout + proc.stderr
    assert "rule 2a" in out and "AGK_MERGE_TOKEN" in out
    assert proc.returncode == 1
    assert graphql(made) == [] and merges(made) == []


def test_the_merger_event_no_longer_stops_at_the_queue_setting(tmp_path):
    """REQ-046: brief #972 answer 3 (the event job calls the command; the command decides)."""
    root = repo(tmp_path, toml(QUEUE_ON))
    bin_dir, _ = queue_gh(tmp_path, comments=[cleared()])
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "issue": {"number": 7, "pull_request": {"url": "https://example.com/7"}},
                "comment": cleared(),
            }
        ),
        encoding="utf-8",
    )
    proc = run(root, bin_dir, "--event", str(event), "--event-name", "issue_comment")
    assert proc.stdout.strip() == f"7 {HEAD}", proc.stdout + proc.stderr


# --- answer 4: a pull request removed from the queue ---


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


def removed_run(tmp_path: Path, payload: dict, token: bool = True, **saved):
    root = repo(tmp_path, toml(QUEUE_ON))
    bin_dir, log = queue_gh(tmp_path, **saved)
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    proc = run(root, bin_dir, "--queue-removed", "--event", str(path), token=token)
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
    assert [b.splitlines()[0] for b in posted_comments(made)] == [expected], (
        proc.stdout + proc.stderr
    )
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
    ("name", "saved", "token"),
    [
        ("still in the queue", {"queue": {"in_queue": True}}, True),
        ("merged", {"pull": {**PULL, "state": "closed", "merged": True}}, True),
        ("closed", {"pull": {**PULL, "state": "closed"}}, True),
        ("no merger token", {}, False),
    ],
)
def test_the_removal_line_is_posted_only_when_github_removed_the_pull_request(
    tmp_path, name, saved, token
):
    """REQ-046: amendment 158 item 4 (only a pull request GitHub removed; verdict item 4 on #993)."""
    proc, made = removed_run(tmp_path, removal_event(), token=token, **saved)
    assert posted_comments(made) == [], name + proc.stdout + proc.stderr
    assert proc.returncode == 0
    if not token:
        assert graphql(made) == []


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


# --- answer 1 and 3: the workflows ---


def on_block(name: str) -> str:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    found = re.search(r"^on:\n((?:[ #].*\n|\n)*)", text, re.MULTILINE)
    assert found, name
    return found.group(1)


@pytest.mark.parametrize("name", ["governance.yml", "proof.yml"])
def test_governance_and_proof_run_on_the_merge_queue(name):
    """REQ-057: brief #972 answers 1 and 7 (the `merge_group` trigger)."""
    block = on_block(name)
    assert re.search(r"^  merge_group:\n    types: \[checks_requested\]$", block, re.MULTILINE), (
        block
    )
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    job_if = re.search(r"^jobs:\n  \w+:\n    if: (.+)$", text, re.MULTILINE)
    assert job_if, name  # the job is not skipped on the queue's ref
    allowed = ("github.event_name == 'merge_group'", "github.event_name != 'pull_request' ||")
    assert any(words in job_if.group(1) for words in allowed), job_if.group(1)


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


@pytest.mark.parametrize("step", ["check_protected_changes", "check_specs", "check_final_clearance"])
def test_the_body_reading_checks_are_skipped_on_the_merge_queue(step):
    """REQ-057: brief #972 answer 1 (verdict item 1 on #993). On `merge_group` no step sets
    AGK_BASE, so these checks would diff the whole batch, a `Covered-by:` pull request's protected
    change included, against an empty body and fail the batch; each passed on its own head."""
    text = (WORKFLOWS / "governance.yml").read_text(encoding="utf-8")
    found = re.search(rf"- name: {step}\n(?:\s+#.*\n)*\s+if: \$\{{\{{ (.+) \}}\}}", text)
    assert found, step
    assert "github.event_name != 'merge_group'" in found.group(1), found.group(1)


def paused_step() -> str:
    text = (WORKFLOWS / "governance.yml").read_text(encoding="utf-8")
    step = text.split("      - name: Paused\n", 1)[1].split("\n      - name: ", 1)[0]
    return step


@pytest.mark.parametrize(
    ("env", "ref"),
    [
        ({"QUEUE_BASE": "b" * 40}, "b" * 40),
        ({"AGK_BASE": "a" * 40}, "a" * 40),
        ({}, None),
    ],
    ids=["merge-group", "pull-request", "push"],
)
def test_the_paused_step_judges_a_queue_run_by_its_base(tmp_path, env, ref):
    """REQ-057: ADR-0196 (verdict item 2 on #993): a batch member that adds `paused = true`
    never turns the queue's checks green unchecked; the queue's run reads its base sha."""
    step = paused_step()
    assert "QUEUE_BASE: ${{ github.event.merge_group.base_sha }}" in step
    script = step.split("        run: |\n", 1)[1]
    script = "\n".join(line[10:] for line in script.splitlines())
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "python3.log"
    fake = bin_dir / "python3"
    fake.write_text(
        f"#!/bin/sh\necho \"$@\" >> {log}\necho 'agk not paused'\n", encoding="utf-8"
    )
    fake.chmod(0o755)
    out = tmp_path / "out"
    base = {k: v for k, v in os.environ.items() if k not in ("AGK_BASE", "QUEUE_BASE")}
    base.update(env, PATH=f"{bin_dir}{os.pathsep}{base['PATH']}")
    base.update(GITHUB_OUTPUT=str(out), GITHUB_STEP_SUMMARY=str(tmp_path / "summary"))
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell input
        ["bash", "-e", "-c", script], cwd=tmp_path, capture_output=True, text=True, env=base
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    called = log.read_text(encoding="utf-8").split()
    if ref is None:
        assert "--ref" not in called
    else:
        assert called[called.index("--ref") + 1] == ref
    assert out.read_text(encoding="utf-8").strip() == "paused=false"


def test_the_merger_job_has_a_timeout():
    """REQ-046: brief #972 answer 3 (a waiting run can never block the queue for hours)."""
    text = (WORKFLOWS / "merger.yml").read_text(encoding="utf-8")
    job = text.split("\n  merger:\n", 1)[1].split("\n  sweep-gate:\n", 1)[0]
    assert re.search(r"^    timeout-minutes: 30$", job, re.MULTILINE), job[:400]
    assert "--queue-removed" in text


def test_the_guide_names_governance_and_proof_the_queue_checks_never_agk_verdict():
    """REQ-046: amendment 158 items 3 and 9."""
    guide = (ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    section = guide.split("## The merge queue", 1)[1].split("\n## ", 1)[0]
    named = section.split("the required checks are", 1)[1].split(".", 1)[0]
    assert "`governance` and `proof`" in named and "agk/verdict" not in named
    assert "Do not add `agk/verdict`" in section
    assert "holds that head and never queues it again" in section  # verdict item 3 on #993


# --- answers 5 and 6: the setting, the doctor line and the guide ---


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
        "Maximum group size: 5",
        "Require branches to be up to date before merging",
        "organization",
        "merge_queue = true",
    ):
        assert words in section, words
    order = [section.index(f"({n})") for n in ("i", "ii", "iii")]
    assert order == sorted(order)
