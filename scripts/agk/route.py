"""The router: one label for the state of every pull request (SPEC-0032 rules 1, 2 and 8).

    python3 route.py                         route what the GitHub event of the job names
    python3 route.py --pr N [--dry-run]      route one pull request (a person or a test)
    python3 route.py --all [--dry-run]       route every open pull request
    python3 route.py --branch [--dry-run]    route the default branch: its red-branch brief
    python3 route.py --health [--dry-run]    the health issues alone (local mode has no job)

It runs in the workflow `agk-route.yml` on `pull_request`, `issue_comment`, `workflow_run` and
`push` to the default branch, with the job's `GITHUB_TOKEN`, from a checkout of the default
branch: it runs no code of a pull request. For each pull request to route it reads the facts with
GET (the head, the latest run of each check and the latest status of each context of the head,
`mergeable_state`, the comments, the reviews, the changed files) and sets exactly one of the
states of `STATES`, each naming its actor in its description, removing the others and the old
`agk:ready` (amendment 150, ADR-0385); `pr_state` gives the label and its actor, the first of
`STATES` that holds, except that `agk:conflict` comes before the checks, and `agk:parked`, a
person's hold, is never set or removed. A label set with the job's
token starts no workflow, so the router cannot loop. It writes labels and, for the default branch
(SPEC-0032 rule 7), the one issue `The default branch is red`: on a `push` to the default branch
or a finished workflow on it, it reads the checks of the branch's head and, when they fail, opens
or updates that issue as a brief (`Priority: 0`, `Advances: none`) that names the failing check,
the sha and the run and no cause, and closes it when the branch is green, with every open copy of
the same shape whoever wrote it (brief #916); while checks still run it does nothing.
A run woken by a finished workflow (`workflow_run`) also sweeps (brief #309): it re-reads every
open pull request labelled `agk:ci-running` that the event did not name and relabels each one whose
required checks have all finished, by the same rules, writing the label only, so a wake lost to
another event does not leave a green pull request at `agk:ci-running`.
No review, no merge, and one comment only: the reply `Correction needed:` to a verdict whose
`Final:` line it cannot read (brief 238), and one comment `Unreadable: <rule>` for another
conductor line it cannot read, which sets `agk:review` while it is the newest (brief #854). When a
pull request merges (`pull_request` closed, the job runs only for a merge), the brief its body
names with `Finishes: #n` or `Closes #n` beside `Brief: #n` is closed as completed, with one
comment that names the merge commit (brief 302, ADR-0178); apart
from the health issues below, that is the only other issue it closes. Messages name the rule,
never a value.
A covered fix list on the full head whose every `Final:` line accepts an ADR the pull request
changes (SPEC-0021 rule 3a) clears the head for the label, as `merge_cleared.py` clears it, so a
pull request merged on it ends with `agk:merge-ready` (brief #601, ADR-0293).
With `builder_start = "assign"` every run of the job also reads the conductor lease and the slot
leases and opens, updates or closes the plain issues `No live conductor` and `Builder pool down`,
labelled `agk-health` (brief #776 answer 5, ADR-0368); with `start` it reads none of them.
Brief #1116 (ADR-0476): a run of the event job that labels a pull request `agk:merge-ready`, the
state it did not have before (nor the old `agk:ready`), starts the merger workflow once for it with
`workflow_dispatch` and the input `pr`, only while `[flow] auto_merge = true` in GitHub mode (the
setting the merger reads), and not for a `Verdict:` or `Approve:` comment or an edited `Final:`,
on which the merger starts by itself. `--pr`, `--all` and `--dry-run` start nothing, and a start
that GitHub refuses prints one line and fails no routing: the merger's schedule still sweeps.
Brief #1143 (ADR-0485): a run of the event job for the default branch that reads its required
checks green when the branch turns green (this run closes the red-branch issue, or the checks
were pending or red before the run of the finished workflow that woke it) starts the merger the
same way once for every open pull request labelled `agk:merge-ready`, under the same setting, and
not twice for one that entered that state in the same run. A branch that stays green, stays red
or still runs starts nothing, and `--branch` starts nothing.
Brief #1212 (ADR-0513): while the one open local-mode record issue exists (`Local mode since ...`,
the issue `merge_cleared.py` finds, read once per run), a required check of the head that never
reported is satisfied when the newest `Report:` of the pull request's author on that head carries
the `Evidence:` line of `prepush.py` naming the head, and failed when that report records a failed
step (`prepush: stopped at ...` or `failed: step ...`); without such evidence the head is the
builder's (`agk:build`), never `agk:ci-running`. A check that reported is judged as before.
`agk:merge-ready` then also needs the verdict's `Local evidence:` and `Evidence check: agrees` for
the head, read by `merge_cleared.local_evidence`; without them a cleared head is `agk:review`.
While the checkout's agk.toml sets `paused = true` (brief #348, ADR-0196) it prints `agk paused`
and reads and writes nothing, whatever it was asked to route.
"""

from __future__ import annotations

import base64
import datetime
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    BRIEF_NUMBER,
    PAUSED_LINE,
    CheckError,
    agent_apps,
    config_source,
    covered_fix_list,
    final_accepts,
    finished_brief,
    finishes_problem,
    load_config,
    paused,
    repo_root,
    required_checks,
    verdict_problem,
)
from merge_cleared import (
    PROTECTED,
    RECORD_TITLE,
    Held as EvidenceHeld,
    Nothing,
    github_mode,
    local_evidence,
    titled,
)
from metrics import counted_authors, covered_head, latest_verdict_body, verdicts
from reviewers import (
    APPROVE,
    APPROVE_SHORT,
    approval_shas,
    confirmed_comments,
    first_line,
    login_of,
    person_approvals,
    solo_person,
    spec_approvers,
    specs_named_approved,
    verdict_authors,
    via_agent,
)
from session import RED_TITLE, ROUTER_PAIR, gh, is_red, pages, repo_name

NAME = "route"
USAGE = "usage: route.py [--pr N | --all | --branch | --health] [--dry-run]"
ROUTER_JOB = "agk-route"
MERGER_WORKFLOW = "merger.yml"  # brief #1116 (ADR-0476): started once per pull request entering
MERGE_READY = "agk:merge-ready"
MERGER_STARTS = ("Verdict:", "Approve:")  # comments on which merger.yml starts by itself
STATES = (  # (label, actor, what), amendment 150 item 1; pr_state's precedence (ADR-0385)
    ("agk:parked", "owner", "a person holds it"),
    ("agk:build", "builder", "a draft, or no ready Report: on the head"),
    ("agk:ci-running", "checks", "the required checks of the head run"),
    ("agk:ci-red", "builder", "a required check of the head failed"),
    ("agk:conflict", "builder", "a conflict with the default branch"),
    ("agk:review", "conductor", "a verdict on the reported head"),
    ("agk:fix", "builder", "the fix list on the head"),
    ("agk:question", "owner", "an answer to Owner needed:"),
    ("agk:approve", "owner", "a spec approval the head needs"),
    ("agk:owner-merge", "owner", "the merge of a path only a person merges"),
    ("agk:merge-ready", "merger", "the guarded merge"),
    # amendment 162 (ADR-0453): not in the order; it replaces a builder's state, see `state_of`
    ("agk:handover", "launcher", "a new builder for a pull request whose builder stopped"),
)
ACTOR = {label: actor for label, actor, _ in STATES}
PARKED = "agk:parked"
OLD_READY = "agk:ready"  # read as agk:merge-ready until the next release (amendment 150 item 2)
LABELS = (*(label for label, _, _ in STATES if label != PARKED), OLD_READY)  # set or removed
OWNER_PATHS = PROTECTED  # the one list merge_cleared.py refuses (SPEC-0039 rule 5)
BRIEF_LINE = re.compile(r"^Brief: #\d+", re.MULTILINE)
HANDOVER = "agk:handover"
BUILDER_STATES = ("agk:build", "agk:ci-red", "agk:conflict", "agk:fix")  # amendment 162 item 3
# brief #1101 answer 1 (ADR-0471): the owner's turn; never replaced by agk:handover
OWNER_STATES = ("agk:question", "agk:approve", "agk:owner-merge", "agk:parked")
HANDING_OVER = re.compile(r"Report: ([0-9a-f]{7,40}) handing over\b:?\s*(.*)$")  # item 2
NO_RESTART = re.compile(r"(?:to \S|done\b)")  # a successor named, or nothing left
NOT_A_BUILDER = ("Verdict:", "Answer:", "Correction:")  # lines that never clear a hand-over
BUILT = re.compile(
    r"Report: ([0-9a-f]{7,40}) (?:ready for review|fix list applied|merge of main)\b"
)
COLORS = {
    "agk:build": "c2e0c6",
    "agk:ci-running": "fbca04",
    "agk:ci-red": "d93f0b",
    "agk:conflict": "b60205",
    "agk:review": "0e8a16",
    "agk:fix": "d4c5f9",
    "agk:question": "5319e7",
    "agk:approve": "5319e7",
    "agk:owner-merge": "5319e7",
    "agk:merge-ready": "0e8a16",
    "agk:handover": "f9d0c4",
    "agk-brief": "1d76db",
    "agk-health": "b60205",
    "agk:parked": "c5def5",
}
DESCRIPTIONS = {
    "agk-brief": "AGK: a brief a builder session can take",
    "agk-health": "AGK: the conductor or the builder pool has no valid lease",
    **{label: f"AGK: {actor} acts next: {what}" for label, actor, what in STATES},
}
FAILED_RUN = {"failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale"}
FAILED_STATUS = {"failure", "error"}
ASKED = re.compile(
    r"Approval: (SPEC-\d{4}) (\S+) Draft -> Approved, waiting for a person"
    r"(?:: post \"Approve: (SPEC-\d{4})\")?"
)
REPORT_HEAD = re.compile(r"Report: ([0-9a-f]{7,40})(?![0-9A-Za-z])")  # brief #1212
EVIDENCE_LINE = re.compile(  # the line `prepush.py --record` prints (docs/guides/local-mode.md)
    r"Evidence: prepush schema \d+, head ([0-9a-f]{12}), \d+ steps ok, record [0-9a-f]{12}\b"
)
FAILED_STEP = ("prepush: stopped at ", "failed: step ")  # a failed step of prepush or evidence.py
RECORD_OPEN: dict[str, bool] = {}  # repo -> the local-mode record issue is open, once per run
SUMMARY = re.compile(r"Summary: (\S.{0,118}\S|\S)")
PIPELINE_COUNTS = ("review", "fix", "ci-red", "conflict", "approve", "ready")
SPEC_TITLE = re.compile(r"# SPEC-\d{4}: (\S.*)")
SPEC_FILE = re.compile(r"docs/specs/(\d{4})-[^/]+\.md")


class ReadOnly(Exception):
    """The job's token cannot write (a fork's pull request gets a read-only token): skip."""


def write(endpoint: str, *extra: str, method: str, what: str = "rule 2: a label") -> None:
    """One write with `gh api`; a 403 is `ReadOnly`, any other failure a CheckError."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["gh", "api", "--method", method, endpoint, *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode == 0 or (method == "DELETE" and "404" in proc.stderr):
        return
    if "403" in proc.stderr:
        raise ReadOnly
    raise CheckError(f"{what} cannot be written")


class Held:
    """The one commit record that `metrics.covered_head` asks its source for."""

    def __init__(self, commit: dict) -> None:
        self.commit = commit

    def get(self, key: str, endpoint: str) -> dict:
        return self.commit


# --- the decision (rule 2) --------------------------------------------------------------------


def specs_approved_by(files: list[dict]) -> set[str]:
    """The specs the pull request sets to `Approved`, from the patches of its changed files."""
    found = set()
    for item in files:
        match = SPEC_FILE.fullmatch(str(item.get("filename") or ""))
        patch = str(item.get("patch") or "")
        if match and "+- Status: Approved" in patch.splitlines():
            found.add(f"SPEC-{match.group(1)}")
    return found


approved_by_a_person = person_approvals


def asked_for(body: str) -> set[str]:
    """The specs the conductor's `Approval:` lines of a verdict ask a person to approve."""
    found = map(ASKED.fullmatch, (x.strip() for x in body.splitlines()))
    return {m.group(1) for m in found if m and m.group(3) in (None, m.group(1))}


def record_open(repo: str) -> bool:
    """Whether a local-mode record issue is open, as `merge_cleared.local_mode` finds it (brief
    #1212 answer 1); read once per run. Open issues that cannot be read count as no record issue:
    the router then labels as it does in CI mode."""
    if repo not in RECORD_OPEN:
        issues = pages(f"repos/{repo}/issues?state=open")
        RECORD_OPEN[repo] = isinstance(issues, list) and titled(issues, RECORD_TITLE)
    return RECORD_OPEN[repo]


def local_proof(f: dict, head: str) -> str:
    """`failed`, `ok` or `none`: the local evidence of the newest `Report:` that the pull request's
    author posted on HEAD (brief #1212 answer 1)."""
    me = str(f.get("author") or "").lstrip("@").lower()
    newest = None
    for c in f.get("comments") or []:
        match = REPORT_HEAD.match(first_line(c))
        if match and me and login_of(c) == me and head.startswith(match.group(1)):
            newest = c
    if newest is None:
        return "none"
    lines = [x.strip() for x in str(newest.get("body") or "").splitlines()]
    if any(x.startswith(FAILED_STEP) for x in lines):
        return "failed"
    named = any((m := EVIDENCE_LINE.match(x)) and m.group(1) == head[:12] for x in lines)
    return "ok" if named and len(head) >= 12 else "none"


def local_cleared(f: dict, comments: list[dict], authors: list[str] | None, head: str) -> bool:
    """Whether the latest verdict carries the local evidence `merge_cleared.py` needs for HEAD
    (`Local evidence:` and `Evidence check: agrees`, or `differs` with the accept answer)."""
    allowed = {str(a).lstrip("@").lower() for a in authors or []}
    body = latest_verdict_body(comments, authors)
    found = [c for c in comments if login_of(c) in allowed and c.get("body") == body]
    if not body or not found:
        return False
    approvers = [str(a).lstrip("@").lower() for a in f.get("approvers") or []]
    try:
        local_evidence(found[-1], comments, head, approvers)
    except EvidenceHeld:
        return False
    return True


def latest_runs(checks: list[dict]) -> list[dict]:
    """The latest run of each check name: the highest `id`, the later `started_at` on a tie.

    An older run of a name (a cancelled one, one a newer run replaced) is ignored, as GitHub's
    required checks ignore it; a latest run that failed or was cancelled still counts. A skipped
    run (the `push` workflows start jobs of the same names that `if:` skips) is never the latest
    while the name has a run that was not skipped; a name with only skipped runs keeps its
    newest."""
    ran = {str(r.get("name") or "") for r in checks if r.get("conclusion") != "skipped"}
    kept = [
        r for r in checks if r.get("conclusion") != "skipped" or str(r.get("name") or "") not in ran
    ]
    newest: dict[str, dict] = {}
    for run in kept:
        key = str(run.get("name") or "")
        rank = (run.get("id") or 0, str(run.get("started_at") or ""))
        held = newest.get(key)
        if held is None or rank > (held.get("id") or 0, str(held.get("started_at") or "")):
            newest[key] = run
    return list(newest.values())


def latest_statuses(statuses: list[dict]) -> list[dict]:
    """The latest status of each context (the highest `id`), as GitHub reads them."""
    newest: dict[str, dict] = {}
    for item in statuses:
        key = str(item.get("context") or "")
        held = newest.get(key)
        if held is None or (item.get("id") or 0) > (held.get("id") or 0):
            newest[key] = item
    return list(newest.values())


def judged(
    checks: list[dict], statuses: list[dict], required: list[str] | None, wait: bool = True
) -> tuple[list[dict], list[dict], bool]:
    """(the latest runs, the latest statuses, whether a required name has not reported).

    With `required` (the `required_checks` of agk.toml) only a run named in it and a status whose
    context is named in it are judged; a check that is not listed never decides a label. Without
    it every run and status counts. The router's own job is never judged. With `wait` false (the
    default branch, where a workflow such as `proof` may never run) a listed name that has not
    reported is not waited for: the head waits only for the names that have a run or a status."""
    runs = [c for c in latest_runs(checks) if c.get("name") != ROUTER_JOB]
    latest = latest_statuses(statuses)
    if required is None:
        return runs, latest, False
    names = {x for x in required if x != ROUTER_JOB}
    runs = [c for c in runs if c.get("name") in names]
    latest = [s for s in latest if s.get("context") in names]
    seen = {c.get("name") for c in runs} | {s.get("context") for s in latest}
    return runs, latest, wait and bool(names - seen)


def final_accept_clears(body: str, head: str, files: list[dict]) -> bool:
    """Whether the latest verdict BODY is a covered fix list on the full HEAD whose every `Final:`
    line accepts an ADR that the pull request adds or modifies (SPEC-0021 rule 3a): the cases that
    `merge_cleared.py` clears (`accepted_adrs`, and the file test of `hold_list`), which the label
    reads as cleared (brief #601, ADR-0293)."""
    covered = covered_fix_list(body)
    if covered is None or not head or covered[0] != head:
        return False
    accepts = final_accepts(covered[1])
    if not accepts:
        return False
    touched = {f.get("filename") for f in files if f.get("status") in ("added", "modified")}
    return all(path in touched for path in accepts)


def description_of(label: str) -> str:
    """The GitHub description of a label the router creates (amendment 150 item 1)."""
    return DESCRIPTIONS.get(label, "AGK: the state of a pull request")


def decide(f: dict) -> str:
    """The one label of a pull request from its facts (the label of `pr_state`)."""
    return pr_state(f)[0]


def pr_state(f: dict) -> tuple[str, str]:
    """(the one state label, its actor): the first state that holds, in order (ADR-0385)."""
    label = state_of(f)
    return label, ACTOR[label]


def reported(f: dict, head: str) -> bool:
    """Whether the author's `Report:` names HEAD as ready, fixed or merged (amendment 150)."""
    me = str(f.get("author") or "").lower()
    for c in f.get("comments") or []:
        match = BUILT.match(first_line(c))
        if match and login_of(c) == me and head.startswith(match.group(1)):
            return True
    return False


def for_maintainers(line: str) -> bool:
    """A builder's question only the owner can answer: a first line that starts `Question: Q-` and
    contains `for the maintainers`, by any author (brief #1043 answer 1, ADR-0442)."""
    return line.startswith("Question: Q-") and "for the maintainers" in line


def asks_owner(f: dict, comments: list[dict], authors: list[str] | None) -> bool:
    """An `Owner needed:` by a listed verdict author with no later answer by a spec approver, which
    a new head does not close (amendment 172, ADR-0497), or a `for_maintainers` question with no
    later such answer and no later head (amendment 150 item 1, Q-846-4, ADR-0442); the two are
    kept apart, so a question never closes an `Owner needed:`; comments are in the order GitHub
    lists them."""
    approvers = {str(a).lower() for a in f.get("approvers") or []}
    listed = {str(a).lstrip("@").lower() for a in authors or []}
    pushed = str(
        (((f.get("commit") or {}).get("commit") or {}).get("committer") or {}).get("date") or ""
    )
    owner_open = False  # an `Owner needed:`: only the owner's answer closes it (brief #1168)
    question_open = False  # a maintainers question: that answer or a newer head closes it
    for c in comments:
        line = first_line(c)
        if line.startswith("Owner needed:") and login_of(c) in listed:
            owner_open = True
        elif for_maintainers(line):
            question_open = not pushed or str(c.get("created_at") or "") >= pushed
        elif line.startswith(("Maintainer answer:", "Approve:")) and login_of(c) in approvers:
            owner_open = question_open = False
    return owner_open or question_open


def handover_reason(line: str) -> str | None:
    """The reason of a `Report: <head> handing over: <reason>` first line, `six hours` for the
    older form with none, or None for any other line (amendment 162 item 2, ADR-0453)."""
    match = HANDING_OVER.match(line)
    if not match:
        return None
    return match.group(2).strip() or "six hours"


def handed_over(f: dict) -> dict | None:
    """The newest `Report:` by the pull request's author or a listed verdict author when it hands
    over with a reason that needs a new builder (not `to <session>` or `done`), with no later
    comment by those authors but a `Verdict:`, `Answer:` or `Correction:`, and no later push;
    else None (amendment 162 item 3). Comments are in the order GitHub lists them."""
    speakers = {str(a).lstrip("@").lower() for a in f.get("authors") or []}
    speakers.add(str(f.get("author") or "").lstrip("@").lower())
    speakers.discard("")
    newest = None
    for c in f.get("comments") or []:
        if login_of(c) not in speakers:
            continue
        line = first_line(c)
        if line.startswith("Report:"):
            newest = c
        elif newest is not None and not line.startswith(NOT_A_BUILDER):
            newest = None  # a builder spoke again after the hand-over
    reason = handover_reason(first_line(newest)) if newest is not None else None
    # reason is None whenever newest is; the first test only narrows newest for the type check
    if newest is None or reason is None or NO_RESTART.match(reason):
        return None
    pushed = str(
        (((f.get("commit") or {}).get("commit") or {}).get("committer") or {}).get("date") or ""
    )
    if pushed and pushed > str(newest.get("created_at") or ""):
        return None
    return newest


def state_of(f: dict) -> str:
    """The state of `pr_state`; a builder's state becomes `agk:handover` while its builder has
    handed over with no successor (amendment 162 item 3, ADR-0453), and an owner's state never
    does (brief #1101 answer 1, ADR-0471)."""
    label = base_state(f)
    if label in OWNER_STATES or label not in BUILDER_STATES:
        return label
    return HANDOVER if handed_over(f) is not None else label


def base_state(f: dict) -> str:
    """The first state of `STATES` that holds, before a hand-over is read; an open owner ask comes
    right after `agk:parked`, before every builder state (brief #1101 answer 1, ADR-0471)."""
    if PARKED in (f.get("labels") or ()):  # a person's hold; never set or removed (Q-846-1)
        return PARKED
    head = str(f.get("head") or "")
    comments = f.get("comments") or []
    if f.get("solo_person"):  # brief 277: the person's confirmation is the verdict and approval
        parents = (f.get("commit") or {}).get("parents") or []
        heads = {head} | ({str(parents[0].get("sha"))} if len(parents) == 1 else set())
        comments = confirmed_comments(
            comments, f.get("agent_apps") or (), f["solo_person"], heads=heads
        )
    authors = counted_authors(f.get("authors"), f.get("author"))
    if asks_owner(f, comments, authors):  # on a draft too (brief #1043 answer 2, ADR-0442)
        return "agk:question"
    if f.get("draft"):
        return "agk:build"
    if f.get("mergeable_state") == "dirty":  # before the checks: none start on it (Q-846-8)
        return "agk:conflict"
    listed = verdicts(comments, authors) or []
    kind, sha = listed[-1] if listed else ("", "")
    names_head = bool(sha) and head.startswith(sha)
    covered = covered_head(Held(f.get("commit") or {}), head, comments, authors) == "yes"
    brief = BRIEF_LINE.search(str(f.get("body") or ""))
    if brief and not (names_head or covered or reported(f, head)):  # Q-846-3, Q-846-7
        return "agk:build"
    checks, statuses, missing = judged(
        f.get("checks") or [], f.get("statuses") or [], f.get("required")
    )
    unreported = missing or (not checks and not statuses)
    local = bool(f.get("local"))  # brief #1212: the local-mode record issue is open
    if unreported and not local:
        return "agk:ci-running"
    if any(c.get("status") != "completed" for c in checks) or any(
        s.get("state") == "pending" for s in statuses
    ):
        return "agk:ci-running"
    if any(c.get("conclusion") in FAILED_RUN for c in checks) or any(
        s.get("state") in FAILED_STATUS for s in statuses
    ):
        return "agk:ci-red"
    if unreported:  # local mode: the builder's evidence stands in for the checks never reported
        proof = local_proof(f, head)
        if proof == "failed":
            return "agk:ci-red"
        if proof != "ok":
            return "agk:build"
    if f.get("unreadable"):  # brief #854 answer 2: the conductor sees it at its next pass
        return "agk:review"
    flipped = specs_approved_by(f.get("files") or [])
    people = approved_by_a_person(
        comments,
        f.get("reviews") or [],
        f.get("approvers") or [],
        flipped,
        f.get("agent_apps") or (),
    )
    latest = latest_verdict_body(comments, authors)
    accepted = names_head and final_accept_clears(latest, head, f.get("files") or [])
    if names_head and kind in ("fix", "rejected") and not accepted:
        return "agk:fix"
    if names_head and asked_for(latest) - people:
        return "agk:approve"
    if (names_head and kind == "cleared") or accepted or covered:
        # brief #797 answer 4: an approval given while the spec on the head still reads Draft
        drafts = set(f.get("draft_specs") or ()) & specs_named_approved(
            comments, f.get("approvers") or []
        )
        if (flipped - people) | drafts:
            return "agk:approve"
        files = {str(x.get("filename") or "") for x in f.get("files") or []}
        owner = any(p.startswith(OWNER_PATHS) for p in files)
        if owner:
            return "agk:owner-merge"
        if local and not local_cleared(f, comments, authors, head):
            return "agk:review"  # brief #1212: the merger needs the verdict's local evidence
        return "agk:merge-ready"
    return "agk:review"


# --- reading the facts and writing the label (rules 1 and 8) ----------------------------------


def listing(endpoint: str, key: str | None = None) -> list | None:
    """A paged GET; `key` names the list inside an object (the check runs)."""
    if key is None:
        return pages(endpoint)
    found: list = []
    page = 1
    sep = "&" if "?" in endpoint else "?"
    while True:
        chunk = gh(f"{endpoint}{sep}per_page=100&page={page}")
        if not isinstance(chunk, dict) or not isinstance(chunk.get(key), list):
            return None
        found += chunk[key]
        if len(chunk[key]) < 100 or len(found) >= int(chunk.get("total_count") or 0):
            return found
        page += 1


def spec_reads_draft(repo: str, path: str, head: str) -> bool:
    """Whether the spec file at the head reads `Draft`; False when it cannot be read: the label
    only, the merge guard fails closed (brief #797 answer 4)."""
    record = gh(f"repos/{repo}/contents/{quote(path)}?ref={head}")
    try:
        text = base64.b64decode(record["content"]).decode("utf-8")
    except (KeyError, TypeError, ValueError):
        return False
    return "- Status: Draft" in text.splitlines()


def draft_specs_of(repo: str, files: list[dict], head: str) -> set[str]:
    """The specs the pull request adds or changes that still read `Draft` on the head."""
    found = set()
    for item in files:
        name = str(item.get("filename") or "")
        match = SPEC_FILE.fullmatch(name)
        if match and item.get("status") in ("added", "modified") and head:
            if spec_reads_draft(repo, name, head):
                found.add(f"SPEC-{match.group(1)}")
    return found


def read_facts(repo: str, n: int, root: Path) -> tuple[dict, dict] | None:
    """(the pull request, its facts); None when a fact that must be known cannot be read."""
    pr = gh(f"repos/{repo}/pulls/{n}")
    if not isinstance(pr, dict) or not isinstance(pr.get("head"), dict):
        return None
    head = str(pr["head"].get("sha") or "")
    checks = listing(f"repos/{repo}/commits/{head}/check-runs", "check_runs")
    comments = listing(f"repos/{repo}/issues/{n}/comments")
    files = listing(f"repos/{repo}/pulls/{n}/files")
    if checks is None or comments is None or files is None:
        return None
    status = gh(f"repos/{repo}/commits/{head}/status")
    reviews = listing(f"repos/{repo}/pulls/{n}/reviews")
    commit = gh(f"repos/{repo}/commits/{head}")
    facts = {
        "head": head,
        "mergeable_state": pr.get("mergeable_state"),
        "checks": checks,
        "statuses": status.get("statuses", []) if isinstance(status, dict) else [],
        "comments": comments,
        "reviews": reviews or [],
        "authors": verdict_authors(root),
        "approvers": spec_approvers(root),
        "required": required_checks(root),
        "agent_apps": agent_apps(root),
        "solo_person": solo_person(root),
        "author": (pr.get("user") or {}).get("login"),
        "draft": pr.get("draft") is True,
        "body": str(pr.get("body") or ""),
        "labels": [str(x.get("name")) for x in pr.get("labels") or []],
        "files": files,
        "draft_specs": draft_specs_of(repo, files, head),
        "commit": commit if isinstance(commit, dict) else {},
        "local": record_open(repo),
    }
    facts["found"] = unreadable_lines(repo, n, facts)
    facts["unreadable"] = newest_is_unreadable(comments, facts["authors"], facts["found"])
    return pr, facts


class Labels:
    """The labels of the repository, read once, created when a label to set is missing."""

    def __init__(self, repo: str) -> None:
        self.repo = repo
        self.known: set[str] | None = None

    def ensure(self, name: str) -> None:
        if self.known is None:
            found = listing(f"repos/{self.repo}/labels")
            self.known = {str(x.get("name")) for x in found or []}
        if name not in self.known:
            write(
                f"repos/{self.repo}/labels",
                "-f",
                f"name={name}",
                "-f",
                f"color={COLORS[name]}",
                "-f",
                "description=" + description_of(name),
                method="POST",
            )
            self.known.add(name)


def apply(repo: str, n: int, current: list[str], wanted: str, labels: Labels) -> None:
    if wanted not in current:
        labels.ensure(wanted)
        write(f"repos/{repo}/issues/{n}/labels", "-f", f"labels[]={wanted}", method="POST")
    for name in current:
        if name in LABELS and name != wanted:
            write(f"repos/{repo}/issues/{n}/labels/{quote(name, safe='')}", method="DELETE")


CORRECTION = "Correction needed:"
ANSWERED = re.compile(r"\(verdict comment (\d+)\)")


def correct_verdicts(repo: str, n: int, comments: list[dict], authors: list[str] | None) -> None:
    """Tell the reviewer, once for each verdict comment, that a `Final:` line cannot be read.

    A `Verdict:` comment of a listed author with a problem (`verdict_problem`, brief 238) gets one
    reply that begins `Correction needed:`, gives the message and names the comment; a reply already
    there for that comment (found by its marker) means nothing new is posted. The reply is the last
    write of a routing; the label comes from `unreadable_lines` (brief #854)."""
    allowed = {a.lstrip("@").lower() for a in authors or []}
    answered = {
        m.group(1)
        for c in comments
        if str(c.get("body") or "").startswith(CORRECTION)
        for m in [ANSWERED.search(str(c.get("body")))]
        if m
    }
    for c in sorted(comments, key=lambda c: c.get("id") or 0):
        login = str((c.get("user") or {}).get("login") or "").lower()
        problem = verdict_problem(str(c.get("body") or "")) if login in allowed else None
        if problem and str(c.get("id")) not in answered:
            body = f"{CORRECTION} {problem} (verdict comment {c.get('id')})"
            write(
                f"repos/{repo}/issues/{n}/comments",
                "-f",
                f"body={body}",
                method="POST",
                what="rule 2: a correction",
            )


REFUSED = "an approval posted through an agent's app does not count; the person posts it themselves"
REFUSED_REVIEW = (
    "a review does not count as an approval while agent apps are listed, because a review cannot "
    "show which app posted it; the person posts `Approve: SPEC-<n>` as a comment from their own "
    "account"
)
ANSWERED_APPROVAL = re.compile(r"\(approval (comment|review) (\d+)\)")


def correct_approvals(
    repo: str,
    n: int,
    comments: list[dict],
    reviews: list[dict],
    approvers: list[str] | None,
    apps: list[str] | None,
    flipped: set[str] | None = None,
) -> None:
    """Tell the person, once for each comment or review, that their approval does not count
    (brief 242). A comment of a listed approver whose first line is an `Approve:` line and that
    GitHub records as posted through an app of `agent_apps` gets one reply that begins
    `Correction needed:` and names the comment. While `agent_apps` is not empty a review never
    counts, since it cannot show which app posted it (Q-242-1); a review of a listed approver that
    would have counted gets one reply that asks for the `Approve: SPEC-<n>` comment. A reply already
    there for that comment or review (found by its marker) means nothing new is posted. No label
    depends on it."""
    if not apps:
        return
    allowed = {a.lstrip("@").lower() for a in approvers or []}
    answered = {
        (m.group(1), m.group(2))
        for c in comments
        if str(c.get("body") or "").startswith(CORRECTION)
        for m in [ANSWERED_APPROVAL.search(str(c.get("body")))]
        if m
    }
    asked: list[tuple[str, dict, str]] = []
    for c in comments:
        line = first_line(c)
        if (
            (APPROVE.fullmatch(line) or APPROVE_SHORT.fullmatch(line))
            and login_of(c) in allowed
            and via_agent(c, apps)
        ):
            asked.append(("comment", c, REFUSED))
    for r in reviews:
        if login_of(r) in allowed and approval_shas(
            [], [r], list(allowed), [], flipped or set(), ()
        ):
            asked.append(("review", r, REFUSED_REVIEW))
    for kind, item, message in sorted(asked, key=lambda a: (a[0], a[1].get("id") or 0)):
        ident = str(item.get("id") or "")
        if ident and (kind, ident) not in answered:
            body = f"{CORRECTION} {message} (approval {kind} {ident})"
            write(
                f"repos/{repo}/issues/{n}/comments",
                "-f",
                f"body={body}",
                method="POST",
                what="rule 2: a correction",
            )


FORM_LINES = ("Verdict:", "Final:", "Correction:")
UNREADABLE = "Unreadable:"


def head_check(repo: str, n: int, body: str, head: str, files: list) -> str | None:
    """`conductor.head_problem`, the guard's check; a function so that a test can replace it."""
    import conductor  # conductor imports merge_cleared, which imports this file

    return conductor.head_problem(repo, n, body, head, files)


def form_lines(comments: list[dict], authors: list[str] | None) -> list[dict]:
    """The comments of a listed author whose first line is a conductor line, oldest first."""
    allowed = {a.lstrip("@").lower() for a in authors or []}
    return [
        c
        for c in sorted(comments, key=lambda c: c.get("id") or 0)
        if login_of(c) in allowed and first_line(c).startswith(FORM_LINES)
    ]


def unreadable_lines(repo: str, n: int, f: dict) -> list[tuple[dict, str]]:
    """(comment, rule) for each conductor line AGK cannot read (brief #854 answer 2), by the check
    the guard runs. A line is read as it stands now, so an edit counts. Only the newest line, when
    it is a verdict on the current head, is read against the pull request; a read that fails flags
    nothing, for the label alone depends on it and the merge guard fails closed."""
    import conductor  # conductor imports merge_cleared, which imports this file

    lines = form_lines(f.get("comments") or [], f.get("authors"))
    head = str(f.get("head") or "")
    found = []
    for comment in lines:
        body = str(comment.get("body") or "")
        problem = conductor.line_problem(body)
        if problem is None and comment is lines[-1] and first_line(comment).startswith("Verdict:"):
            named = first_line(comment).split()[-1]
            if head and head.startswith(named):
                try:
                    problem = head_check(repo, n, body, head, f.get("files") or [])
                except CheckError:
                    problem = None
        if problem:
            found.append((comment, problem))
    return found


def newest_is_unreadable(
    comments: list[dict], authors: list[str] | None, found: list[tuple[dict, str]]
) -> bool:
    """Whether the newest conductor line is one AGK cannot read; a later good line replaces it."""
    lines = form_lines(comments, authors)
    return bool(lines) and any(c.get("id") == lines[-1].get("id") for c, _ in found)


def report_unreadable(
    repo: str, n: int, comments: list[dict], found: list[tuple[dict, str]]
) -> None:
    """One comment `Unreadable: <rule>` for each line and rule, found again by its text. A line
    `correct_verdicts` already answers with `Correction needed:` gets no second comment."""
    said = {str(c.get("body") or "") for c in comments}
    for comment, problem in found:
        body = f"{UNREADABLE} {problem} (comment {comment.get('id')})"
        if body in said or verdict_problem(str(comment.get("body") or "").strip()):
            continue
        write(
            f"repos/{repo}/issues/{n}/comments",
            "-f",
            f"body={body}",
            method="POST",
            what="rule 2: a correction",
        )


def route_one(
    repo: str, n: int, root: Path, labels: Labels, dry: bool, entered: Any = None
) -> str | None:
    """Route pull request `n`; its label, or None when it is over; CheckError if unreadable."""
    got = read_facts(repo, n, root)
    if got is None:
        raise CheckError(f"rule 2: the facts of pull request #{n} cannot be read")
    pr, facts = got
    if pr.get("state") != "open" or pr.get("merged_at"):
        return None
    wanted = decide(facts)
    current = [str(x.get("name")) for x in pr.get("labels") or []]
    if not dry:
        apply(repo, n, current, wanted, labels)
        correct_verdicts(repo, n, facts.get("comments") or [], facts.get("authors"))
        report_unreadable(repo, n, facts.get("comments") or [], facts.get("found") or [])
        correct_approvals(
            repo,
            n,
            facts.get("comments") or [],
            facts.get("reviews") or [],
            facts.get("approvers"),
            facts.get("agent_apps"),
            specs_approved_by(facts.get("files") or []),
        )
    changed = [name for name in current if name in LABELS] != [wanted]
    print(f"#{n} {wanted}" + (" (changed)" if changed and not dry else ""))
    if entered is not None and not dry and entering_merge_ready(current, wanted):
        entered(n)
    return wanted


# --- the brief a merged pull request finishes (brief #302, ADR-0178) ---------------------------

FINISHED = "Finished by #{pr} (merge commit {sha})."
FINISHED_MARK = "Finished by #{pr} (merge commit "


CLOSES = re.compile(r"Closes (#\d+)")


def closing_brief(body: str | None) -> int | None:
    """The brief a body closes: its valid `Finishes: #n`, else a line `Closes #n` beside `Brief: #n`
    of the same number (brief #854 answer 3); a malformed `Finishes:` line closes nothing."""
    if finishes_problem(body) is not None:
        return None
    if (found := finished_brief(body)) is not None:
        return found
    lines = [x.strip() for x in str(body or "").splitlines()]
    brief = next((x[len("Brief:") :].strip() for x in lines if x.startswith("Brief:")), "")
    named = BRIEF_NUMBER.fullmatch(brief)
    if named and any((m := CLOSES.fullmatch(x)) and m.group(1) == brief for x in lines):
        return int(named.group(1))
    return None


def finish_brief(repo: str, n: int, dry: bool) -> int | None:
    """Close the brief that merged pull request `n` finishes; its number, or None.

    The pull request is read again with GET: only one GitHub reports as merged, whose body has a
    line `Finishes: #b` or `Closes #b` beside `Brief: #b` (the same number, `closing_brief`),
    closes issue #b,
    and only while #b is an open issue (not a pull request) labelled `agk-brief`. The router posts
    one comment on it that names the pull request and the merge commit, unless one for this pull
    request is there already, then closes it as completed. It touches no other issue."""
    pr = gh(f"repos/{repo}/pulls/{n}")
    if not isinstance(pr, dict):
        raise CheckError(f"rule 8: pull request #{n} cannot be read")
    if not (pr.get("merged") is True or pr.get("merged_at")):
        return None
    brief = closing_brief(pr.get("body"))
    if brief is None:
        return None
    issue = gh(f"repos/{repo}/issues/{brief}")
    if not isinstance(issue, dict):
        raise CheckError("rule 8: the brief a merged pull request finishes cannot be read")
    labels = {str((x or {}).get("name")) for x in issue.get("labels") or []}
    if "pull_request" in issue or issue.get("state") != "open" or "agk-brief" not in labels:
        return None
    if dry:
        print(f"#{brief} would be closed (finished by #{n})")
        return brief
    comments = listing(f"repos/{repo}/issues/{brief}/comments")
    if comments is None:
        raise CheckError("rule 8: the comments of the brief a pull request finishes cannot be read")
    mark = FINISHED_MARK.format(pr=n)
    if not any(str(c.get("body") or "").startswith(mark) for c in comments):
        sha = str(pr.get("merge_commit_sha") or "unknown")
        body = FINISHED.format(pr=n, sha=sha)
        where = f"repos/{repo}/issues/{brief}"
        write(f"{where}/comments", "-f", f"body={body}", method="POST", what="rule 8: the brief")
    args = ("-f", "state=closed", "-f", "state_reason=completed")
    write(f"repos/{repo}/issues/{brief}", *args, method="PATCH", what="rule 8: the brief")
    print(f"#{brief} closed (finished by #{n})")
    return brief


def stale_running(repo: str, done: set[int]) -> list[int]:
    """The open pull requests labelled `agk:ci-running`, other than DONE (brief #309 answer 2)."""
    found = pages(f"repos/{repo}/pulls?state=open")
    if found is None:
        raise CheckError("rule 1: the open pull requests cannot be read for the sweep")
    return [
        int(p["number"])
        for p in found
        if isinstance(p.get("number"), int)
        and p["number"] not in done
        and "agk:ci-running" in {str(x.get("name")) for x in p.get("labels") or []}
    ]


def sweep_one(
    repo: str, n: int, root: Path, labels: Labels, dry: bool, entered: Any = None
) -> str | None:
    """Relabel one pull request left at `agk:ci-running` once its required checks have finished,
    by the same rules as `route_one`; it writes the label only, and nothing while checks run."""
    got = read_facts(repo, n, root)
    if got is None:
        raise CheckError(f"rule 2: the facts of pull request #{n} cannot be read")
    pr, facts = got
    if pr.get("state") != "open" or pr.get("merged_at"):
        return None
    wanted = decide(facts)
    if wanted == "agk:ci-running":
        return wanted
    current = [str(x.get("name")) for x in pr.get("labels") or []]
    if not dry:
        apply(repo, n, current, wanted, labels)
    print(f"#{n} {wanted} (swept)")
    if entered is not None and not dry and entering_merge_ready(current, wanted):
        entered(n)
    return wanted


# --- the start of the merger (brief #1116, ADR-0476) -------------------------------------------


def entering_merge_ready(current: list[str], wanted: str) -> bool:
    """WANTED is `agk:merge-ready` and the pull request had neither it nor the old `agk:ready`."""
    return wanted == MERGE_READY and not {MERGE_READY, OLD_READY} & set(current)


def merger_on(root: Path) -> bool:
    """The merger merges here: `[flow] auto_merge = true` in GitHub mode, as merge_cleared.py
    reads it (`github_mode`); a setting it refuses starts nothing."""
    try:
        github_mode(config_source(root))
    except (Nothing, CheckError, ValueError):
        return False
    return True


def merger_starts_itself(name: str, event: dict) -> bool:
    """The comment of this event already starts merger.yml (its `issue_comment` condition)."""
    if name != "issue_comment":
        return False
    body = str((event.get("comment") or {}).get("body") or "")
    if body.startswith(MERGER_STARTS):
        return True
    return event.get("action") == "edited" and body.startswith("Final:")


def start_merger(repo: str, default: str, n: int) -> None:
    """One `workflow_dispatch` of merger.yml on the default branch with the input `pr`; a refusal
    prints one line and is not a failure of the routing."""
    endpoint = f"repos/{repo}/actions/workflows/{MERGER_WORKFLOW}/dispatches"
    try:
        write(
            endpoint,
            "-f",
            f"ref={default}",
            "-f",
            f"inputs[pr]={n}",
            method="POST",
            what="brief #1116: the start of the merger",
        )
    except (ReadOnly, CheckError):
        print(f"merger: not started for #{n} (permission actions: write on the router's job)")
        return
    print(f"#{n} merger started")


# --- the default branch (rule 7) ---------------------------------------------------------------


def branch_state(
    checks: list[dict], statuses: list[dict], required: list[str] | None = None
) -> str:
    """`pending`, `red` or `green` for the checks of the default branch's head, judged by the
    required checks of the project that have a run or a status on that head (brief 231): a listed
    check that never runs on the default branch is not waited for, and a head none of them has
    reported is `pending`."""
    checks, statuses, missing = judged(checks, statuses, required, wait=False)
    if missing or (not checks and not statuses):
        return "pending"
    if any(c.get("status") != "completed" for c in checks) or any(
        s.get("state") == "pending" for s in statuses
    ):
        return "pending"
    failed = any(c.get("conclusion") in FAILED_RUN for c in checks)
    return "red" if failed or any(s.get("state") in FAILED_STATUS for s in statuses) else "green"


def failing(
    checks: list[dict],
    statuses: list[dict],
    repo: str,
    sha: str,
    required: list[str] | None = None,
) -> tuple[str, str]:
    """(name, link) of the first failing check by name, or status, among the judged ones."""
    runs, latest, _ = judged(checks, statuses, required, wait=False)
    bad = sorted(
        (str(c.get("name") or ""), str(c.get("html_url") or c.get("details_url") or ""))
        for c in runs
        if c.get("conclusion") in FAILED_RUN
    ) + sorted(
        (str(s.get("context") or ""), str(s.get("target_url") or ""))
        for s in latest
        if s.get("state") in FAILED_STATUS
    )
    name, url = bad[0] if bad else ("", "")
    return name, url or f"https://github.com/{repo}/commit/{sha}/checks"


def one_line(text: str) -> str:
    return " ".join(str(text).split()) or "unnamed"


RED_RUNBOOK = "docs/runbooks/red-default-branch.md"  # SPEC-0056 rule 13: a path, never a value


def red_body(name: str, sha: str, url: str) -> str:
    """The red-branch brief in the shape of a brief; it names the check, the sha, the run and the
    page of steps."""
    return (
        'Sentence: "The default branch is red: the required checks of its head fail."\n'
        f"Answers:\n1. Failing check: {one_line(name)}\n2. Head: {one_line(sha)}\n"
        f"3. Run: {one_line(url)}\n"
        f"Runbook: {RED_RUNBOOK}\n"
        "Priority: 0\nAdvances: none\nTouches: **\nSize: S\n"
        "Broad: a red default branch can start in any file\n"
    )


def red_copies(found: list[dict]) -> list[dict]:
    """Every open issue in the shape of the red-branch brief, whoever wrote it (brief #916 answer
    3): the title `RED_TITLE` and the lines `Priority: 0` and `Advances: none`, oldest first. A
    green branch closes them all, so no stale copy holds every merge; `is_red` still counts only
    the router's own (answer 4)."""

    def shaped(item: dict) -> bool:
        lines = {x.rstrip() for x in str(item.get("body") or "").splitlines()}
        return (
            "pull_request" not in item
            and item.get("title") == RED_TITLE
            and (set(ROUTER_PAIR) <= lines)
        )

    return sorted((i for i in found if shaped(i)), key=lambda i: i["number"])


def turned_green(
    state: str,
    checks: list[dict],
    statuses: list[dict],
    required: list[str] | None,
    closed: bool,
    suite: Any = None,
) -> bool:
    """The default branch turns green in this run (brief #1143 answer 1): its head is green and
    either this run closes the red-branch issue, or the head was pending or red without the
    check runs of SUITE, the check suite of the finished workflow that woke the run."""
    if state != "green":
        return False
    if closed:
        return True
    if suite is None:
        return False
    before = [
        {**c, "status": "in_progress", "conclusion": None}
        if (c.get("check_suite") or {}).get("id") == suite
        else c
        for c in checks
    ]
    return branch_state(before, statuses, required) != "green"


def route_branch(
    repo: str,
    default: str,
    labels: Labels,
    dry: bool,
    required: list[str] | None = None,
    suite: Any = None,
) -> tuple[str, bool]:
    """Open, update or close the red-branch brief from the checks of the default branch's head;
    the state and whether the branch turned green in this run (`turned_green`)."""
    tip = gh(f"repos/{repo}/branches/{default}")
    sha = str(((tip or {}).get("commit") or {}).get("sha") or "") if isinstance(tip, dict) else ""
    checks = listing(f"repos/{repo}/commits/{sha}/check-runs", "check_runs") if sha else None
    status = gh(f"repos/{repo}/commits/{sha}/status") if sha else None
    found = pages(f"repos/{repo}/issues?state=open&labels=agk-brief")
    if checks is None or found is None:
        raise CheckError("rule 7: the checks of the default branch cannot be read")
    statuses = status.get("statuses", []) if isinstance(status, dict) else []
    state = branch_state(checks, statuses, required)
    open_red = sorted((i for i in found if is_red(i)), key=lambda i: i["number"])
    print(f"default branch {state}")
    if state == "pending" or dry:
        return state, False
    issues = f"repos/{repo}/issues"
    if state == "green":
        closing = red_copies(found)
        for item in closing:
            args = ("-f", "state=closed", "-f", "state_reason=completed")
            write(f"{issues}/{item['number']}", *args, method="PATCH", what="rule 7: the issue")
        return state, turned_green(state, checks, statuses, required, bool(closing), suite)
    name, url = failing(checks, statuses, repo, sha, required)
    body = red_body(name, sha, url)
    write_red(repo, open_red, body, labels)
    return state, False


def merge_ready(repo: str) -> list[int]:
    """The open pull requests labelled `agk:merge-ready` (brief #1143 answer 1)."""
    found = pages(f"repos/{repo}/pulls?state=open")
    if found is None:
        raise CheckError("rule 7: the open pull requests cannot be read for the merger")
    return [
        int(p["number"])
        for p in found
        if isinstance(p.get("number"), int)
        and MERGE_READY in {str((x or {}).get("name")) for x in p.get("labels") or []}
    ]


def branch_suite(name: str, event: dict) -> Any:
    """The check suite of the finished workflow on the default branch that woke this run."""
    if name != "workflow_run":
        return None
    return (event.get("workflow_run") or {}).get("check_suite_id")


def write_red(repo: str, open_red: list[dict], body: str, labels: Labels) -> None:
    """Open the red-branch brief with BODY, or update the oldest of OPEN_RED (the router's own
    open ones, oldest first) when its body differs (SPEC-0032 rule 7). `merge_cleared.py` calls
    it after a red governance run (SPEC-0039 rule 6, brief #551), so there is one issue."""
    issues = f"repos/{repo}/issues"
    if open_red:
        if str(open_red[0].get("body") or "") != body:
            write(
                f"{issues}/{open_red[0]['number']}",
                "-f",
                f"body={body}",
                method="PATCH",
                what="rule 7: the issue",
            )
    else:
        labels.ensure("agk-brief")
        args = ("-f", f"title={RED_TITLE}", "-f", f"body={body}", "-f", "labels[]=agk-brief")
        write(issues, *args, method="POST", what="rule 7: the issue")


def route_health(root: Path, repo: str, labels: Labels, dry: bool) -> None:
    """Open, update or close the issues `No live conductor` and `Builder pool down` from the
    leases (brief #776 answer 5, ADR-0368). A lease that cannot be read says so and writes
    nothing: unknown is never dead, and it fails no routing."""
    import conductor  # conductor imports merge_cleared, which imports this file

    try:
        rows = conductor.pool_state(root, repo)
        found = pages(f"repos/{repo}/issues?state=open&labels=agk-health") if rows else []
    except CheckError as exc:
        print(f"health: skipped: {exc}")
        return
    if found is None:
        print("health: skipped: the open health issues cannot be read")
        return
    issues = f"repos/{repo}/issues"
    for title, down, waits, text in rows:
        same = sorted(
            (i for i in found if i.get("title") == title and "pull_request" not in i),
            key=lambda i: i["number"],
        )
        print(f"health: {title}: {'down' if down else 'ok'}{', work waits' if waits else ''}")
        if dry:
            continue
        if not down:
            for item in same:
                ended = ("-f", "state=closed", "-f", "state_reason=completed")
                target = f"{issues}/{item['number']}"
                write(target, *ended, method="PATCH", what="health: the issue")
        elif waits and not same:
            labels.ensure("agk-health")
            args = ("-f", f"title={title}", "-f", f"body={text}", "-f", "labels[]=agk-health")
            write(issues, *args, method="POST", what="health: the issue")
        elif waits and str(same[0].get("body") or "") != text:
            target = f"{issues}/{same[0]['number']}"
            write(target, "-f", f"body={text}", method="PATCH", what="health: the issue")


# --- which pull requests an event names (rule 1) ----------------------------------------------


def open_numbers(repo: str, head: str | None = None) -> list[int]:
    found = pages(f"repos/{repo}/pulls?state=open") or []
    return [
        int(p["number"])
        for p in found
        if isinstance(p.get("number"), int)
        and (head is None or (p.get("head") or {}).get("sha") == head)
    ]


def targets(name: str, event: dict, repo: str, default: str) -> list[int]:
    if name == "pull_request":
        number = (event.get("pull_request") or {}).get("number")
        return [number] if isinstance(number, int) else []
    if name == "issue_comment":
        issue = event.get("issue") or {}
        return [issue["number"]] if "pull_request" in issue and "number" in issue else []
    if name == "push":
        return open_numbers(repo) if event.get("ref") == f"refs/heads/{default}" else []
    if name == "workflow_run":
        run = event.get("workflow_run") or {}
        if run.get("head_branch") == default:
            return open_numbers(repo)
        listed = [p["number"] for p in run.get("pull_requests") or [] if "number" in p]
        return listed or open_numbers(repo, str(run.get("head_sha") or ""))
    return []


def on_default_branch(name: str, event: dict, default: str) -> bool:
    """A push to the default branch, or a finished workflow run on it (rule 7)."""
    if name == "push":
        return event.get("ref") == f"refs/heads/{default}"
    if name == "workflow_run":
        return (event.get("workflow_run") or {}).get("head_branch") == default
    return False


# --- the pipeline document (SPEC-0036 rules 2 to 5) --------------------------------------------


def summary_of(body: object) -> str:
    """The sentence of the first `Summary:` line of a pull request body, or `unknown`."""
    for line in str(body or "").splitlines():
        found = SUMMARY.fullmatch(line.strip())
        if found:
            return found.group(1)
    return "unknown"


def spec_title(repo: str, path: str, head: str) -> str:
    """The title of the spec file at the head of a pull request, or `unknown`."""
    if not re.fullmatch(r"docs/specs/\d{4}-[^/]+\.md", path) or not head:
        return "unknown"
    record = gh(f"repos/{repo}/contents/{quote(path)}?ref={head}")
    try:
        text = base64.b64decode(record["content"]).decode("utf-8")
    except (KeyError, TypeError, ValueError):
        return "unknown"
    found = SPEC_TITLE.match(text.splitlines()[0] if text else "")
    return found.group(1).strip() if found else "unknown"


def approve_items(repo: str, pr: dict, root: Path) -> list[dict]:
    n = int(pr["number"])
    url = str(pr.get("html_url") or "")
    unread = [{"number": n, "spec": "unknown", "spec_title": "unknown", "url": url}]
    comments = listing(f"repos/{repo}/issues/{n}/comments")
    if comments is None:
        return unread
    body = latest_verdict_body(comments, counted_authors(verdict_authors(root), None))
    head = str((pr.get("head") or {}).get("sha") or "")
    found = [ASKED.fullmatch(x.strip()) for x in body.splitlines() if ASKED.fullmatch(x.strip())]
    return [
        {
            "number": n,
            "spec": m.group(1),
            "spec_title": spec_title(repo, m.group(2), head),
            "url": url,
        }
        for m in found
    ] or unread


def pipeline_document(repo: str, root: Path) -> dict:
    """What waits for a person, from a fresh read of the open pull requests."""
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    found = pages(f"repos/{repo}/pulls?state=open")
    doc: dict = {"schema": 1, "as_of": now, "ready": [], "approve": []}
    if found is None:
        doc["counts"] = {k: "unknown" for k in PIPELINE_COUNTS}
        return doc
    held = {k: [] for k in PIPELINE_COUNTS}
    for pr in found:
        names = {(x or {}).get("name") for x in pr.get("labels") or []}
        if names & {"agk:merge-ready", "agk:owner-merge"}:  # schema 1 until build (b) of #846
            names.add(OLD_READY)
        for k in PIPELINE_COUNTS:
            if f"agk:{k}" in names and isinstance(pr.get("number"), int):
                held[k].append(pr)
    doc["counts"] = {k: len(v) for k, v in held.items()}
    doc["ready"] = [
        {
            "number": p["number"],
            "summary": summary_of(p.get("body")),
            "url": str(p.get("html_url") or ""),
        }
        for p in held["ready"]
    ]
    for pr in held["approve"]:
        doc["approve"] += approve_items(repo, pr, root)
    return doc


def write_pipeline(repo: str, root: Path) -> None:
    """Write `pipeline.json` (rule 2); a failure is reported and fails no routing (rule 4)."""
    target = Path(os.environ.get("AGK_PIPELINE_FILE") or "pipeline.json")
    try:
        doc = pipeline_document(repo, root)
        target.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    except (OSError, CheckError, ValueError, KeyError, TypeError):
        print("skipped rule 4: the pipeline document was not written")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry-run" in args
    rest = [a for a in args if a != "--dry-run"]
    by_number = len(rest) == 2 and rest[0] == "--pr" and rest[1].isdigit()
    if rest not in ([], ["--all"], ["--branch"], ["--health"]) and not by_number:
        print(USAGE, file=sys.stderr)
        return 2
    root = repo_root()
    RECORD_OPEN.clear()  # read once per run (brief #1212)
    try:
        if paused(root):  # brief #348 (ADR-0196): nothing is read and nothing is written
            print(PAUSED_LINE)
            return 0
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 1
    repo = os.environ.get("GITHUB_REPOSITORY") or repo_name(root)
    path = os.environ.get("GITHUB_EVENT_PATH")
    try:
        event = json.loads(Path(path).read_text(encoding="utf-8")) if path else {}
    except (OSError, ValueError):
        event = {}
    default = (event.get("repository") or {}).get("default_branch") or load_config(root)[
        "default_branch"
    ]
    name = os.environ.get("GITHUB_EVENT_NAME", "")
    if rest == ["--all"]:
        numbers = open_numbers(repo)
    elif rest in (["--branch"], ["--health"]):
        numbers = []
    elif rest:
        numbers = [int(rest[1])]
    else:
        numbers = targets(os.environ.get("GITHUB_EVENT_NAME", ""), event, repo, default)
    try:
        required = required_checks(root)
        agent_apps(root)
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 1
    labels = Labels(repo)
    failed = False
    starts = not rest and not dry and not merger_starts_itself(name, event) and merger_on(root)
    begun: set[int] = set()

    def enter(n: int) -> None:
        begun.add(n)
        start_merger(repo, default, n)

    entered = enter if starts else None

    try:
        for n in dict.fromkeys(numbers):
            try:
                route_one(repo, n, root, labels, dry, entered)
            except CheckError as exc:
                print(f"FAIL {NAME}: {exc}")
                failed = True
        if not rest and name == "pull_request" and event.get("action") == "closed":
            for n in dict.fromkeys(numbers):
                try:
                    finish_brief(repo, n, dry)
                except CheckError as exc:
                    print(f"FAIL {NAME}: {exc}")
                    failed = True
        if not rest and name == "workflow_run":  # the safety net of a lost wake (brief #309)
            try:
                for n in stale_running(repo, set(numbers)):
                    try:
                        sweep_one(repo, n, root, labels, dry, entered)
                    except CheckError as exc:
                        print(f"FAIL {NAME}: {exc}")
                        failed = True
            except CheckError as exc:
                print(f"FAIL {NAME}: {exc}")
                failed = True
        if rest == ["--branch"] or (not rest and on_default_branch(name, event, default)):
            try:
                _, green = route_branch(
                    repo, default, labels, dry, required, branch_suite(name, event)
                )
                if green and entered is not None:  # brief #1143 (ADR-0485)
                    for n in merge_ready(repo):
                        if n not in begun:
                            entered(n)
            except CheckError as exc:
                print(f"FAIL {NAME}: {exc}")
                failed = True
        if not rest or rest == ["--health"]:  # every event of the job (brief #776 answer 5)
            try:
                route_health(root, repo, labels, dry)
            except CheckError as exc:
                print(f"health: skipped: {exc}")
    except ReadOnly:
        print("skipped (read-only token)")
        failed = False
    if not dry:
        write_pipeline(repo, root)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
