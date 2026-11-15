"""The conductor's routines as kit commands (brief #643, ADR-0308). Read-only: GET only, posts
nothing and writes no file, but for the `--apply` and merge forms named below.

    python3 conductor.py watch [--since ISO] [--once]
    python3 conductor.py sweep

Each `watch` also prints `SWEEP late <m> min`, after its other lines, when no sweep run finished in
the last 30 minutes and a cleared pull request is open (brief #836 answer 4, ADR-0383).

`watch` polls the comments of every open issue labelled `agk-brief` and every open pull request,
and exits 0 printing one line `<number> <first line>` for each comment created after `--since`
(default: the start) whose first line starts `Question:` or `Report:` (conductor catch log row 1),
or is an owner's answer or approval: an `Answer: Q-…` or `Maintainer answer: Q-…`, or an `Approve:`
by a listed spec approver (brief #1112, ADR-0475);
`--once` reads once, printing `nothing new` when there is none. The poll interval is
`conductor_poll_seconds` of the `[flow]` table of agk.toml (60 by default); a read that fails is
printed and retried. `sweep` prints one line `#<n> <head7> <state> <age>` per open pull request,
then the default branch line (its required checks, brief #736) and any open red-branch issue.
A `Question:` or `Report:` with no comment by a listed verdict author after it, older than
`conductor_late_minutes` (30 by default), is marked `LATE` (row 13). The rules it reads are
`session.py`'s and `merge_cleared.py`'s own functions, never a copy.

Brief #854 (ADR-0388): `sweep` prints `HELD VERDICT #<n>` for a pull request whose newest author
`Report:` says ready, with green checks, no verdict on its head, and that report and the conductor's
last comment both older than 15 minutes.

Brief #669 (ADR-0322): after those lines `sweep` prints `SILENT <brief> <session> <minutes>;
re-fire: Session name: <session>. Item: brief #<brief>.` for each open `agk-brief` issue whose
newest live take (`session.live_takes`) is older than `silent_minutes` of `[flow]` (30 by
default), measured from the take comment's creation time, with no branch `claude/brief-<n>`, no
open pull request naming the brief, no pull request naming it created after the take, and no
`Progress:`, `Report:` or `Question:` comment after the take. A brief with any `Report: ...
escalate` comment is never SILENT. The sweep fires nothing; the conductor re-fires the session
with the printed line.

Brief #714 (SPEC-0049 rule 7, ADR-0324): with a `[caps]` table, after the pull request lines and
before the default branch line, `sweep` prints `OVER #<brief> <used>/<cap> tokens|hours #<pr>`
for each cap a builder pull request is past and `UNKNOWN #<brief> tokens #<pr>` for one with no
token figure (`caps.over_lines`); it marks only, and stops or changes nothing.

Brief #755 (SPEC-0050 rule 5, ADR-0325): right after the pull request lines `sweep` prints, for the
open builder pull requests (a `Brief: #n` line), `overlap: #<a> #<b> <file>` for two of different
briefs that change one file that is not shared-mechanical (a < b, the first such file sorted),
`re-prove: #<n> <file> (changed by #<m>)` for one that changes a file the default branch changed
after its merge base (the earliest merged pull request that changed it), and `BEHIND #<pr> <n>`
with the compare's `ahead_by`. It reads `GET pulls/N/files`, one `GET compare/<head>...<default>`
and, for a re-prove, `GET commits?path=`; a read that fails prints `re-prove: #<n> unknown (cannot
be read)`. With none of them nothing more is printed.

Brief #781 (SPEC-0049 rules 11 and 12, ADR-0366), GET only:

    python3 conductor.py over --pr N

prints `over #<pr> brief #<brief>`, then one count per line, `unknown` when its evidence cannot be
read and never 0, then the cause of the first matching rule of rule 12: `loop-red-heads` (the same
check red on heads in a row), `loop-file-commits` (one file in commits with no green run between),
`wander-files` (files outside the brief's `Touches:` and `Adds:` lines), `counted-hours` and
`blocked-hours` (`caps.hours_used`, up to the `over cap` report; blocked runs from a reported tool
error or refused push to the next commit), `unreadable`, `cause`. The walk stops at `unknown` when
a rule is not met and part of its evidence cannot be read; `estimate` needs at most half the
counted hours blocked (Q-781-2).

Build (b) of brief #643 (ADR-0329, catch log rows 3 and 22):

    python3 conductor.py merge-queue [--dry-run] [--max-batch N]

`merge-queue` reads the default branch's settings as `merge_cleared.py` does (`merge_cleared.ruled`)
and judges every open pull request with `merge_cleared.holds`, the same holds that command runs;
the clearing verdict's author must be a listed verdict author. A pull request whose latest verdict
does not clear its head is left out; a cleared one that is held is printed as `not queued: #<n>
<sha12>: <reason>`. The rest are merged in the order of their verdicts, at most `--max-batch N` of
them (5 by default), each through `python3 scripts/agk/merge_cleared.py --pr <n> --sha <head>` in
its own process, its line printed in full, with no wait for the default branch's run between two
merges (the check before each merge against the latest default branch is merge_cleared.py's own).
The queue stops at the first run that does not exit 0 and lists what merged; then, when anything
merged and no `stopped:` line ended it, it waits once for the default branch's run on the last
merge commit (`full_run.covered`, the batched reading of ADR-0302), polling every
`conductor_poll_seconds` for at most `merge_queue_wait_minutes` (60 by default), and prints
`<branch> green at <sha12> after the batch #a #b` (exit as the stop's code) or `stopped: <branch>
red at <sha12> after the batch #a #b` (exit 1). In local mode there is no run to wait for.
Before the holds of each open pull request that is not a draft, and before each merge after the
first, the pull request is read again until GitHub has computed its mergeable state. `--dry-run`
prints the order and merges nothing. It posts nothing and merges only through merge_cleared.py.

Brief #700 (ADR-0330, catch log rows 18 and 19): the last private routines, as commands.

    python3 conductor.py rerun --pr N [--apply]
    python3 conductor.py check-verdict FILE
    python3 conductor.py lease (--show | --take NAME | --release NAME)

`rerun` reads the pull request and the `pull_request` runs of its head (one GET each, GET by
default) and prints one line `rerun: #<n> <sha12>: run <id> (<name>) cancelled; ...` per cancelled
run, rerun only with `--apply` (`POST actions/runs/<id>/rerun`, row 18). When every run of the
head is skipped (a push to a ready pull request, row 19) it says so and prints the one step that
starts them, converting the pull request to a draft and back (`POST
repos/{owner}/{repo}/pulls/<n>/ccr/convert_to_draft`, then `.../ccr/ready_for_review`, the routes
of the runtime that session rule 7 names `(verify: the draft route is the ready route's twin, not
read from the runtime's documentation)`), and does it only with `--apply`; a draft's runs skip by
design and are left alone. Otherwise `nothing to rerun` or `no run of the head`.
`check-verdict FILE [--pr N]` prints `ok` or the rule the line breaks, exit 1 on a problem (brief
#854, ADR-0388): a first line that is not `Verdict: cleared|fix list|rejected <sha>` or `Correction:
<text>` (a `Final:` first line is read by nothing), an `Approval:` line of another shape, and the
problem of the `Final:` lines by `common.verdict_problem` (the reading `route.py` applies). Without
`--pr` it reads nothing on GitHub. With `--pr N` it also refuses a verdict on another head, a
`Final:` path the head does not have, and a fix list with no numbered item and no `Final:` line on
a pull request with no Proposed ADR (it must be `cleared`); a read that fails is an error, never
`ok`. `conductor_guard.py` runs the same check before the comment and `route.py` after it.
`lease` is the active-conductor marker, so that the hourly run and a live conductor never merge at
once: one comment on the plan issue that `plan_issue` of the `[flow]` table names (absent: the
lease is off, said as such), whose first line is `Conductor: active <time> <name>`, valid 10
minutes from `<time>` (ADR-0368; `watch` renews this checkout's at every pass, exit 3 when another
name holds it, and returns within 5 minutes with `tick`), counted only when its author is
in `verdict_authors`; `--take NAME` posts
it, or edits the newest counted `Conductor:` comment in place, unless another name holds a valid
lease (exit 3, naming the setting), and keeps NAME in the git directory as this checkout's name;
`--release NAME` edits it to `Conductor: released <time> <name>` for the holder; `--show` prints
`held by <name> until <time>` or `free`. `merge-queue` refuses to run (`held`, exit 3) while a
name other than this checkout's holds a valid lease.

Brief #776 build (c) (ADR-0402): `watch` ends within 5 minutes with no event with the line `tick`
(`--once` keeps `nothing new`) and the stall lines, which `sweep` prints too: `STALL #<pr> <m>m:
restart <session>` for a builder's draft with no push and no builder comment for `stall_minutes`
of `[flow]` (30), `... (owner needed posted)` when the one `Owner needed:` of a refused start is
there, `STALL #<pr>: failed check <name>` for a failed required check with no `Progress:` for 15
minutes, and `STALL conductor <name> <m> min` for a lease holder with no conductor comment for
`stall_minutes` with a review or a start due, counted from its take (`since <time>`). Another
name's `lease --take` then posts that line on the plan issue and takes the lease; a renewal never
does. `MAIN GREEN after #<n>: merge of main #<pr> (<session>) ...` ends a watch when a red-branch
issue has closed, naming the pull requests whose every failed required check finished inside it;
with none, the line is `MAIN GREEN after #<n>`.

Brief #1151 (ADR-0489): with `builder_start = "assign"`, when a poll of `watch` finds no new line
and no held review, it reads the plan as `session.py plan` does, at most once per minute across
watches (the file `agk/starts` of the git directory), and ends with `START #<brief>[ build (<x>)]
<kind>` for each `Assign` row whose brief has no `Started: cb` or `taken:` comment in the last 2
hours, a brief titled `The default branch is red` first as `START #<brief> red`; one brief is
returned again only after 10 minutes. The conductor's start rule itself is unchanged.

Brief #1163 (SPEC-0050 amendment 171, ADR-0495): a `re-prove:` line whose files are all shared
indexes ends ` light`, and

    python3 conductor.py reprove --pr N [--apply]

takes the light re-prove: when every re-prove file is a shared index and the merge is clean, it
prints `PUT repos/<repo>/pulls/<n>/update-branch expected_head_sha=<head>` (a merge commit, never
a rebase or a force-push) and, with `--apply`, makes it and posts `Report: <new head> merge of
main (light re-prove, SPEC-0050 amendment 171)`; any other re-prove file or a conflict prints
`full re-prove (...)`, exit 3, and changes nothing.

Brief #1071 (amendment 162, ADR-0453): `sweep` prints `HANDOVER #<pr> <minutes>m` for each open pull
request labelled `agk:handover`, counted from its newest handing-over `Report:` (`unknown` without
one), so the launcher restarts a builder for exactly those.

Brief #1282 (ADR-0543): before its `START` lines `sweep` parks each open pull request whose
owner wait passed (`[flow] owner_wait_minutes`, or at once inside `owner_rest_hours`), with one
label write and one `Parked-by: wait <Q-id>` comment, and unparks one it parked once the owner
answered, with the label removed and one `Unparked-by: answer <Q-id>` comment; it prints
`UNPARKED #<n> <Q-id>; run: python3 scripts/agk/session.py resume --pr <n>` and, once per park,
`PARKED #<n> <Q-id>`. A person's own `agk:parked` is never removed.

Brief #1322 (SPEC-0059 rule 2, ADR-0559): from the same comments, `sweep` then prints one line
`STEWARD: #<n> <Q-id>, ... waited one pass unanswered; run: python3 scripts/agk/launch.py role
--role steward --session steward-<comment id>` (with `--adapter <launch_adapter>` when `auto_start`
is on in the checkout and on the default branch) when a `Question:` has waited one conductor pass
(25 minutes) with no `Answer:`, `Maintainer answer:` or `Correction:` by a listed author and no
steward post (ending `Who: AGK steward`) after it. It is read from the comments alone.

Brief #1237 (ADR-0525): local mode restarts the conductor unattended.

    python3 conductor.py watchdog [--session NAME] [--install] [--pass]

`watchdog` is one pass, never a loop. It reads, in order: the pause of the default branch
(`agk paused; nothing started`, exit 0); `auto_start` and `launch_adapter` of the `[flow]` table,
which must be on and set in the checkout and on `origin/<default branch>` alike, as for the review
pass's starts (else nothing starts, exit 1, naming the settings); the lease on the plan issue (off:
nothing starts, exit 1; held by a live conductor: `lease held by <name> until <time>; nothing
started`, exit 0); and the machine's free memory (`common.available_memory`) against
`builder_memory_gb`, the smaller of the `[flow]` and `[capacity]` values as the plan reads it,
printed as `watchdog: memory <n> GB available, builder_memory_gb <g>|unset`. Below one builder it
starts nothing and says so (exit 1); memory that cannot be read prints `memory unknown` and the
start goes ahead, as `launch.py`'s floor does. Otherwise it calls the adapter once, as
`launch.py` does (split into words, no shell, the prompt on standard input), with `AGK_SESSION`
NAME (`conductor-local` by default), `AGK_ROLE=conductor` and `AGK_TIER=strongest`, and no
`AGK_BRIEF`; the prompt names the conductor role and tells it to take the lease under NAME first.
It posts nothing and takes no lease: the started conductor takes its own, and the lease keeps two
from running. `--install` reads nothing and runs nothing: it prints the one scheduler line for the
platform, `schtasks /Create /SC MINUTE /MO 30 ...` on Windows and a crontab line elsewhere, each a
`git fetch` of the checkout and then this pass, for the person to run.

Brief #1310 (ADR-0554): `watchdog --pass` is the scripted conductor pass. After the same checks it
takes or renews the lease under NAME (another live holder starts nothing, exit 0), runs
`review-queue --fingerprint`, the plan and `sweep` in the script, and starts one conductor job
through the adapter only when the fingerprint or the sweep's lines (without their ages and times)
differ from those of the last job, the plan's `Start` line starts a brief, or no job ran for 24
hours; otherwise it prints `watchdog: nothing changed; no job started`. The job does one pass and
leaves the lease to the script. Under `--pass` the lease no longer keeps two jobs apart, since the
script and its job share the name: the pass starts nothing, printing `watchdog: job <name> still
running; nothing started`, within the first lease window of its last job or while the lease was
renewed since the script's own last take (the job renews it first and as it works). What the
last job saw is kept in `<git dir>/agk/watchdog.json` only after the adapter succeeded, so a failed
job is tried again. `--install --pass` prints the scheduler line every 10 minutes. The
watchdog, the reviewer starts and `launch.py` set
`CLAUDE_CODE_ENABLE_AWAY_SUMMARY=0` for the sessions they start (verify).

Brief #1359 (ADR-0571): `watchdog --pass` starts each job on the tier its queue needs, as
`AGK_TIER` and `AGK_EFFORT`, and prints `watchdog: tier <tier>[: <why>]`. It reads each pull
request that `review-queue --all` lists for review (the pull request, its files and comments):
`strongest` at `high` when one changes a protected path class, adds or changes a spec or ADR
(`docs/specs/`, `docs/adr/`), is a first review (no verdict by a counted author) of more than
`[review] large_lines` changed lines (300 by default), carries a `Question:` or `Correction:`
after its last verdict or two verdicts of different kinds on one head, or is an intake (a title
starting `Intake:`); also for a question on a brief, a queue that cannot be read and
`[models] conductor = "strongest"`, the one pin. Every other pass runs on `mid` at `medium`, and
its prompt says to post no verdict where it meets one of those or is unsure, and to end with
`escalate: #<n> <reason>` for each. Those lines, from the adapter's output or, for a background
job, from `<worktree>/.agk-session.log` once the job ended, start one strongest job at once,
printing `watchdog: escalated #<n> to strongest: <reason>`; never a step down inside a pass. The
interactive `watchdog` and the reviewer starts stay on `strongest`.

Brief #1355 (ADR-0568): after its conductor checks, `watchdog` (and `--pass`) reads each builder
session with a process record (`<parent of the checkout>/agk-<session>/.agk-session-pid`) and a
live take of its brief, and prints one line each, `watchdog: builder <name> #<brief>
ended|idle|live -> restarted|left|held (<reason>)`, posting nothing. An `ended` builder is
restarted through the adapter with `launch.py`'s resume prompt under the same name. A builder is
`idle` only when every sign of work is quiet for `[flow] idle_minutes` (60 by default, never below
`silent_minutes`): it owes the next move and posted or pushed nothing, its transcript was not
written, no local commit or file change in its worktree, no `lock.py` lock of it with a fresh
heartbeat, and two reads of its process tree 5 to 30 minutes apart (one per pass, kept in
`builders.json`) show the same processes and CPU seconds; until they agree it prints `held
(working)`, which is no NEEDS-YOU line. An idle one is stopped first, only when its worktree is
clean and pushed; a parked or handed-over one is never restarted; one restart per
session per hour, kept in `<git dir>/agk/builders.json`, and `sweep` prints `NEEDS-YOU: builder
<name> #<brief> held (<reason>)` for each held one.

Brief #1248 (ADR-0528): a fresh reviewer gives the gating verdict, in local mode too.

    python3 conductor.py review --pr N [--start]

With `[flow] reviewer_slots` 0 or unset it prints `review: off` and nothing changes. With 1 or more
it reads the pull request, its comments and the `Review: r<k> #<n> <head>` lines by a listed verdict
author on the one open `agk-conductor` issue, and prints one line: the head has its verdict; a slot
has it (`with r<k> since <time>`, the conductor gives no verdict until `review_minutes` pass); the
fallback is due (no reviewer verdict within `review_minutes`); no slot is free; or `review: ask
Review: r<k> #<n> <head>` for a head nobody was asked about. `--start` (local mode: `auto_start` and
`launch_adapter` set in the checkout and on the default branch, not paused, above `[flow]
min_free_memory_mb`) posts that line and calls the adapter once, with `AGK_SESSION=r<k>`,
`AGK_ROLE=reviewer`, `AGK_AGENT=architect-review`, `AGK_TIER=strongest`, `AGK_PR` and `AGK_SHA`,
and a prompt naming only the slot, the pull request and the head. With slots counted,
`check-verdict --pr N` refuses a verdict without the slot's marker lines (`agent:`, `tier:`,
`session:`) unless it ends `(conductor fallback)`, and a fallback while a slot has the head, after
its verdict, or with no `Review:` line for the head.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
import re
import shlex
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from collections.abc import Set as AbstractSet
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import caps
import common
import launch
import merge_cleared
import session
import session_plan
from common import (
    FINAL_LINE,
    NOT_FIX_LIST,
    CheckError,
    fix_items,
    repo_root,
    utf8_output,
    verdict_problem,
)
from full_run import contained_in, covered
from reviewers import approval_shas, authors_of, spec_approvers, verdict_authors

import config

USAGE = (
    "usage: conductor.py watch [--since ISO] [--once] | conductor.py sweep | "
    "conductor.py merge-queue [--dry-run] [--max-batch N] | "
    "conductor.py rerun --pr N [--apply] | conductor.py check-verdict FILE [--pr N] | "
    "conductor.py lease (--show | --take NAME | --release NAME) | conductor.py over --pr N | "
    "conductor.py reprove --pr N [--apply] | "
    "conductor.py watchdog [--session NAME] [--install] [--pass] | "
    "conductor.py review --pr N [--start]"
)
REPROVE_REPORT = "merge of main (light re-prove, SPEC-0050 amendment 171)"
REPROVE_WAITS = 10  # reads of the pull request for the new head after update-branch
REPROVE_PAUSE = 3  # seconds between two of those reads
TRIGGERS = ("Question:", "Report:")
# What wakes `watch` (brief #1112, ADR-0475): `TRIGGERS` and an owner's answer or approval;
# `waiting_on` keeps `TRIGGERS`.
WAKES = TRIGGERS + ("Answer:", "Maintainer answer:", "Approve:")
QUESTION_ID = re.compile(r"Question: (Q-\S+)")
HELD_MINUTES = 15  # a ready, green head with no verdict for this long (brief #854 answer 9)
HELD_EVERY = 300  # seconds between two held-review checks of `watch` (brief #1125 answer 1)
START_EVERY = 60  # seconds between two plan reads of `watch` (brief #1151 answer 1)
START_AGAIN = 10  # minutes before a returned `START` brief is returned again (brief #1151)
START_HOURS = 2  # a `Started: cb` or `taken:` this recent holds a brief (brief #1151 answer 1)
STARTED = ("Started: cb", "taken:")
SWEEP_LATE = 30  # minutes without a finished sweep run before `SWEEP late` (brief #836 answer 4)
SWEEP_RUNS = "repos/{}/actions/workflows/merger.yml/runs?status=completed&per_page=100"
SWEEP_EVENTS = ("schedule", "workflow_dispatch", "workflow_run")
POLL = ("conductor_poll_seconds", 60)
LATE = ("conductor_late_minutes", 30)
SILENT = ("silent_minutes", 30)
STALL_SETTING = "stall_minutes"
HANDOVER_LABEL = "agk:handover"  # route.HANDOVER (amendment 162); route imports session
ALIVE = ("Progress:", "Report:", "Question:")
STALL_CHECK_MINUTES = 15  # a failed required check with no `Progress:` for this long (brief #776)
SAYS = ("Verdict:", "Assign:", "Tell:", "Correction:", "Owner needed:", "STALL ", "Conductor ")
ESCALATE = re.compile(r"Report: .*\bescalate\b")
RED_RUN = ("failure", "timed_out")
GREEN_RUN = ("success", "neutral")
BLOCKED = re.compile(
    r"(?:Question|Report): .*(?:tool error|push\b.*\brefused|refused\b.*\bpush)", re.I
)
OVER_REPORT = re.compile(r"Report: \S+ over cap\b")
OVER_KEYS = (
    "loop-red-heads",
    "loop-file-commits",
    "wander-files",
    "counted-hours",
    "blocked-hours",
)
SQUASHED = re.compile(r"\(#(\d+)\)\s*$")  # the `(#m)` that ends a merged pull request's subject


def when(text: str) -> datetime | None:
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def read(endpoint: str, what: str) -> list:
    found = session.pages(endpoint)
    if found is None:
        raise CheckError(f"{what} cannot be read")
    return found


def age(since: datetime, now: datetime) -> str:
    minutes = max(0, int((now - since).total_seconds() // 60))
    return f"{minutes}m" if minutes < 60 else f"{minutes // 60}h"


# --- watch (row 1) ----------------------------------------------------------------------------


def wakes(comment: dict, approvers: AbstractSet[str]) -> bool:
    """Whether a comment's first line wakes `watch`: a `Question:` or `Report:`; an `Answer:` or
    `Maintainer answer:` that names a `Q-` id; an `Approve:` by a spec approver (brief #1112)."""
    first = session.first_line(comment)
    if not first.startswith(WAKES):
        return False
    if first.startswith(TRIGGERS):
        return True
    if first.startswith("Approve:"):
        return session.author_of(comment) in approvers
    return bool(session.ANSWER_LINE.match(first))


READS = ["full"]  # `github_reads` of this run, set once by `watch` (brief #1314, ADR-0555)


def new_lines(
    repo: str, since: datetime, approvers: AbstractSet[str] = frozenset(), reads: str = ""
) -> list[str]:
    """The waking lines of the open briefs and pull requests since `since`. With `reads` delta
    (brief #1314, ADR-0555 decision 2) one `changed_comments` read stands for every issue's pages:
    a comment created after `since` was updated after it, so the lines are the same; a delta that
    cannot be read reads every page as before."""
    briefs = session.labelled(
        read(f"repos/{repo}/issues?state=open&labels={session.LABEL}", "the open briefs"),
        session.LABEL,
    )
    pulls = read(f"repos/{repo}/pulls?state=open", "the open pull requests")
    numbers = sorted({i["number"] for i in briefs} | {p["number"] for p in pulls}, reverse=True)
    delta = None
    if (reads or READS[0]) == "delta":
        delta = session.changed_comments(repo, since.timestamp())
    by_issue: dict[int, list] = {}
    for c in delta or []:
        by_issue.setdefault(session.issue_of(c), []).append(c)
    lines = []
    for number in numbers:
        comments = (
            by_issue.get(number, [])
            if delta is not None
            else read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
        )
        for c in sorted(comments, key=lambda c: c.get("id") or 0):
            first = session.first_line(c)
            if wakes(c, approvers) and session.moment(c.get("created_at")) > since:
                lines.append(f"{number} {first}")
    return lines


def renew_lease(root) -> int:
    """Renew this checkout's lease, if it took one; nonzero when another name holds it."""
    name = own_name(root)
    if name is None or plan_issue(root) is None:
        return 0
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = lease(root, "--take", name, takeover=False)
    if code:
        print(out.getvalue().strip(), flush=True)
    return code


def cleared_open(repo: str) -> bool:
    """True when an open, non-draft pull request's latest verdict clears its current head."""
    for pull in read(f"repos/{repo}/pulls?state=open", "the open pull requests"):
        if pull.get("draft") is not False:
            continue
        comments = read(f"repos/{repo}/issues/{pull['number']}/comments", "the comments")
        if merge_cleared.judge(comments, str(pull["head"]["sha"]), [])[0] == "cleared":
            return True
    return False


def sweep_late(root, repo: str) -> list[str]:
    """`SWEEP late <m> min` when no sweep run finished in the last 30 minutes and a cleared pull
    request is open (brief #836 answer 4), by the sweep's own gate; a failed read is silent."""
    try:
        merge_cleared.github_mode(merge_cleared.default_ref(root)[1])
        found = read_one(SWEEP_RUNS.format(repo), "the sweep runs").get("workflow_runs")
        ended = [
            when(str(r.get("updated_at")))
            for r in (found if isinstance(found, list) else [])
            if r.get("event") in SWEEP_EVENTS
            and r.get("conclusion") not in ("cancelled", "skipped")
        ]
        newest = max((t for t in ended if t), default=None)
        now = datetime.now(UTC)
        minutes = SWEEP_LATE if newest is None else int((now - newest).total_seconds() // 60)
        if minutes < SWEEP_LATE or not cleared_open(repo):
            return []
    except (merge_cleared.Nothing, merge_cleared.Unreadable, CheckError, OSError):
        return []
    return [f"SWEEP late {minutes} min"]


def watch(root, since: datetime, once: bool) -> int:
    repo = session.repo_name(root)
    interval = session.flow_int(root, POLL[0], POLL[1], 0)
    READS[0] = session.github_reads(root)
    print(f"reads: {READS[0]}", file=sys.stderr, flush=True)  # once (brief #1314 answer 5)
    started = time.monotonic()
    renewed: float | None = None
    while True:
        lines: list[str] = []
        try:
            if renewed is None or time.monotonic() - renewed >= RENEW_EVERY:
                if code := renew_lease(root):
                    return code
                renewed = time.monotonic()
            approvers = {a.lstrip("@").lower() for a in spec_approvers(Path(root))}
            lines = new_lines(repo, since, approvers) + green_lines(root, repo, since)
            lines = lines or held_lines(root, repo)
            lines = lines + start_lines(root, repo)  # with every return (brief #1179, ADR-0500)
        except CheckError as exc:
            if once:
                raise
            print(f"error: {exc}; retrying", file=sys.stderr, flush=True)
        if lines or once or time.monotonic() - started + interval >= WATCH_BOUND:
            ticked = not lines and not once
            said = lines or ["tick" if ticked else "nothing new"]
            said += stall_report(root, repo) if ticked else []
            print("\n".join(said + sweep_late(root, repo)))
            return 0
        time.sleep(interval)


def held_mark(root) -> Path | None:
    """The file of the git directory that holds the held-review marks of `watch` (never tracked)."""
    try:
        found = lease_mark(root)
    except OSError:
        return None
    return found.with_name("held") if found else None


def held_lines(root, repo: str) -> list[str]:
    """The `HELD VERDICT #<n>` lines of the open, ready pull requests (brief #1125, ADR-0482), read
    at most once per HELD_EVERY; one pull request is returned again only after HELD_MINUTES."""
    mark, now = held_mark(root), datetime.now(UTC)
    if mark is None:  # no checkout to keep the marks in: no check, so reads stay few
        return []
    try:
        marks = json.loads(mark.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        marks = {}
    marks = marks if isinstance(marks, dict) else {}
    checked = when(str(marks.get("checked")))
    if checked is not None and now - checked < timedelta(seconds=HELD_EVERY):
        return []
    found = marks.get("said")
    said: dict = found if isinstance(found, dict) else {}
    keep = {"checked": stamp_of(now), "said": said}
    write_held(mark, keep)
    authors = verdict_authors(root)
    pulls = read(f"repos/{repo}/pulls?state=open", "the open pull requests")
    lines: list[str] = []
    held: dict = {}
    for pull in sorted(pulls, key=lambda p: p["number"]):
        line = None if pull.get("draft") else held_verdict_line(root, repo, pull, authors, now)
        if line is None:
            continue
        number = str(pull["number"])
        before = when(str(said.get(number)))
        if before is not None and now - before < timedelta(minutes=HELD_MINUTES):
            held[number] = said[number]
            continue
        held[number] = stamp_of(now)
        lines.append(line)
    write_held(mark, {"checked": keep["checked"], "said": held})
    return lines


def write_held(mark: Path, marks: dict | list) -> None:
    with contextlib.suppress(OSError):  # an unwritten mark only makes the next check come sooner
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.write_text(json.dumps(marks, sort_keys=True), encoding="utf-8")


def start_mark(root) -> Path | None:
    """The file of the git directory that holds the start marks of `watch` (never tracked)."""
    try:
        found = lease_mark(root)
    except OSError:
        return None
    return found.with_name("starts") if found else None


def started(repo: str, number: int, now: datetime) -> bool:
    """Whether a `Started: cb` or `taken:` comment on the brief is newer than START_HOURS."""
    comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
    edge = now - timedelta(hours=START_HOURS)
    return any(
        session.first_line(c).startswith(STARTED) and session.moment(c.get("created_at")) > edge
        for c in comments
    )


def start_lines(root, repo: str, now: datetime | None = None) -> list[str]:
    """The `START #<brief>[ build (<x>)] <kind>` lines (brief #1151, ADR-0489): one per `Assign`
    row of the plan whose brief nobody started, a red-branch brief first as `START #<brief> red`,
    read at most once per START_EVERY; one brief is returned again only after START_AGAIN. `watch`
    adds them to every return and `sweep` prints them last (brief #1179, ADR-0500)."""
    now = now or datetime.now(UTC)
    mark = start_mark(root)
    if mark is None or session.builder_start(root) != "assign":
        return []  # no checkout to keep the marks in, or a conductor that assigns nothing
    try:
        marks = json.loads(mark.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        marks = {}
    marks = marks if isinstance(marks, dict) else {}
    checked = when(str(marks.get("checked")))
    if checked is not None and now - checked < timedelta(seconds=START_EVERY):
        return []
    found = marks.get("said")
    said: dict = found if isinstance(found, dict) else {}
    keep = {"checked": stamp_of(now), "said": said}
    write_held(mark, keep)
    try:
        rows = session_plan.build(root).get("assign") or []
    except CheckError:
        return []  # tried again after START_EVERY
    red = [r for r in rows if r.get("title") == session.RED_TITLE]
    lines: list[str] = []
    kept: dict = {}
    for r in red + [r for r in rows if r not in red]:
        build = f" build ({r['build']})" if r.get("build") else ""
        key = f"{r['brief']} ({r['build']})" if build else str(r["brief"])
        before = when(str(said.get(key)))
        if before is not None and now - before < timedelta(minutes=START_AGAIN):
            kept[key] = said[key]
            continue
        if started(repo, r["brief"], now):
            continue
        kept[key] = stamp_of(now)
        lines.append(f"START #{r['brief']}{build} {'red' if r in red else r.get('kind')}")
    write_held(mark, {"checked": keep["checked"], "said": kept})
    return lines


# --- ticks and stalls (brief #776 build (c), ADR-0402) ----------------------------------------


def minutes_since(moment: datetime, now: datetime) -> int:
    return max(0, int((now - moment).total_seconds() // 60))


def failed_checks(root, repo: str, head: str) -> list[dict]:
    """The required check runs of a head that failed, by the router's own `judged`; none when
    they cannot be read, since unknown is never a stall."""
    from route import FAILED_RUN, judged  # route imports session

    found = session.gh(f"repos/{repo}/commits/{head}/check-runs?per_page=100")
    checks = found.get("check_runs") if isinstance(found, dict) else None
    if not isinstance(checks, list):
        return []
    runs, _, _ = judged(checks, [], session.required_checks(root), wait=False)
    return [r for r in runs if r.get("conclusion") in FAILED_RUN]


def taker(root, repo: str, brief: int, pulls: list) -> str:
    """The session of the newest live take of a brief, `unknown` without one."""
    comments = session.pages(f"repos/{repo}/issues/{brief}/comments") or []
    hours = session.flow_int(root, "claim_hours", session.CLAIM_HOURS, 5)
    takes = session.live_takes(comments, brief, pulls, hours)
    return max(takes, key=lambda t: t[:2])[2] if takes else "unknown"


def stall_line(root, repo: str, pull: dict, pulls: list, limit: int, now) -> str | None:
    """The `STALL` line of a builder's draft, else None: a failed required check with no
    `Progress:` for 15 minutes, or no push and no builder comment for `stall_minutes`. A draft
    whose newest comment is a `Question:` waits for its answer; a head that cannot be read is
    never a stall."""
    brief = session.brief_number(pull)
    if not pull.get("draft") or brief is None:
        return None
    number, head = pull["number"], str(pull["head"]["sha"])
    comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
    ordered = sorted(comments, key=lambda c: c.get("id") or 0)
    if ordered and session.first_line(ordered[-1]).startswith("Question:"):
        return None
    commit = session.gh(f"repos/{repo}/commits/{head}")
    detail = commit.get("commit") if isinstance(commit, dict) else None
    pushed = when(str(((detail or {}).get("committer") or {}).get("date")))
    if pushed is None:
        return None
    alive = [c for c in ordered if session.first_line(c).startswith(ALIVE)]
    moments = [session.moment(c.get("created_at")) for c in alive]
    progress = [
        session.moment(c.get("created_at"))
        for c in alive
        if session.first_line(c).startswith("Progress:")
    ]
    failed = failed_checks(root, repo, head)
    if failed and minutes_since(max([pushed, *progress]), now) >= STALL_CHECK_MINUTES:
        return f"STALL #{number}: failed check {sorted(str(r.get('name')) for r in failed)[0]}"
    last = max([pushed, *moments])
    idle = minutes_since(last, now)
    if idle < limit:
        return None
    asked = any(
        session.first_line(c).startswith("Owner needed:")
        and session.moment(c.get("created_at")) >= last
        for c in ordered
    )
    note = " (owner needed posted)" if asked else ""
    return f"STALL #{number} {idle}m: restart {taker(root, repo, brief, pulls)}{note}"


def stall_lines(root, repo: str, pulls: list, now: datetime) -> list[str]:
    limit = session.flow_int(root, STALL_SETTING, session_plan.STALL_MINUTES, 4)
    found = (stall_line(root, repo, p, pulls, limit, now) for p in pulls)
    return [x for x in found if x]


def review_or_start_due(root, repo: str, authors: list[str]) -> bool:
    """Whether a ready pull request has no verdict on its head, or the plan has work to hand
    out. A plan or a pull request that cannot be read says nothing is due."""
    try:
        for pull in read(f"repos/{repo}/pulls?state=open", "the open pull requests"):
            if pull.get("draft"):
                continue
            number, head = pull["number"], str(pull["head"]["sha"])
            comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
            me = str((pull.get("user") or {}).get("login") or "").lower()
            ready = [
                c
                for c in comments
                if session.author_of(c) == me and session.first_line(c).startswith("Report:")
            ]
            newest = max(ready, key=lambda c: c.get("id") or 0, default=None)
            counted = session.counted_authors(authors, me)
            if (
                newest is not None
                and session_plan.WAITING_REPORT.match(session.first_line(newest))
                and session.verdict_line(comments, 0, head, counted) is None
            ):
                return True
        plan = session_plan.build(root)
    except CheckError:
        return False
    return bool(plan["start"] or plan.get("assign"))


def lease_stall(root, repo: str, comments: list, authors: list[str], now) -> tuple[str, int] | None:
    """(holder, minutes) when the lease's holder has said nothing for `stall_minutes`, counted
    from the later of its take and its last conductor comment, with a review or a start due."""
    holder, found = lease_holder(comments, authors, now), lease_comment(comments, authors)
    if holder is None or found is None:
        return None
    floor = when(found[1].group(4) or found[1].group(2))
    if floor is None:
        return None
    spoken = session.pages(f"repos/{repo}/issues/comments?since={stamp_of(floor)}")
    if spoken is None:
        return None
    listed = {a.lstrip("@").lower() for a in authors}
    times = [
        session.moment(c.get("created_at"))
        for c in spoken
        if session.author_of(c) in listed and session.first_line(c).startswith(SAYS)
    ]
    minutes = minutes_since(max([floor, *times]), now)
    limit = session.flow_int(root, STALL_SETTING, session_plan.STALL_MINUTES, 4)
    if minutes < limit or not review_or_start_due(root, repo, authors):
        return None
    return holder[0], minutes


def conductor_stall(root, repo: str, now: datetime) -> list[str]:
    issue = plan_issue(root)
    if issue is None:
        return []
    found = lease_stall(root, repo, plan_comments(repo, issue), verdict_authors(root), now)
    return [f"STALL conductor {found[0]} {found[1]} min"] if found else []


def stall_report(root, repo: str) -> list[str]:
    """The `STALL` lines of a tick or a sweep; what cannot be read adds none."""
    now, lines = datetime.now(UTC), []
    try:
        pulls = read(f"repos/{repo}/pulls?state=open", "the open pull requests")
        lines += stall_lines(root, repo, sorted(pulls, key=lambda p: p["number"]), now)
    except CheckError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
    try:
        lines += conductor_stall(root, repo, now)
    except CheckError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
    return lines


def green_lines(root, repo: str, since: datetime) -> list[str]:
    """One `MAIN GREEN` line per red-branch issue closed since the watch began, naming the open
    pull requests whose every failed required check finished while it was open, and `MAIN GREEN
    after #<n>` alone when none did, which still ends the watch; a read that fails is no event."""
    closed = session.pages(f"repos/{repo}/issues?state=closed&since={stamp_of(since)}") or []
    red = [
        i
        for i in closed
        if i.get("closed_at") and session.is_red(i) and session.moment(i["closed_at"]) > since
    ]
    pulls = (session.pages(f"repos/{repo}/pulls?state=open") or []) if red else []
    lines = []
    for issue in red:
        opened, shut = session.moment(issue.get("created_at")), session.moment(issue["closed_at"])
        named_pulls = []
        for pull in sorted(pulls, key=lambda p: p["number"]):
            failed = failed_checks(root, repo, str(pull["head"]["sha"]))
            ended = [when(str(r.get("completed_at"))) for r in failed]
            if failed and all(e is not None and opened <= e <= shut for e in ended):
                brief = session.brief_number(pull)
                who = taker(root, repo, brief, pulls) if brief is not None else "unknown"
                named_pulls.append(f"#{pull['number']} ({who})")
        names = " ".join(named_pulls)
        tail = f": merge of main {names}" if named_pulls else ""
        lines.append(f"MAIN GREEN after #{issue['number']}{tail}")
    return lines


# --- sweep (row 13) ---------------------------------------------------------------------------


def waiting_on(comments: list, allowed: set[str]) -> dict | None:
    """The newest `Question:` or `Report:` after the last comment by a listed verdict author."""

    def order(c: dict) -> tuple[str, int]:
        return str(c.get("created_at") or ""), c.get("id") or 0

    floor = max((order(c) for c in comments if session.author_of(c) in allowed), default=("", 0))
    asked = [
        c
        for c in comments
        if order(c) > floor
        and session.author_of(c) not in allowed
        and session.first_line(c).startswith(TRIGGERS)
    ]
    return max(asked, key=order, default=None)


def verdict_state(pull: dict, comments: list, authors: list[str], approvers: list[str]) -> str:
    head = str(pull["head"]["sha"])
    counted = session.counted_authors(authors, (pull.get("user") or {}).get("login"))
    mark = session.last_verdict(comments, counted)
    match = session.HEAD_VERDICT.fullmatch(session.first_line(mark)) if mark else None
    if not match:
        return "ready: no verdict"
    kind, sha = match.group(1), match.group(2) or ""
    on_head = bool(sha) and head.startswith(sha)
    if kind == "cleared" and not on_head:
        return "cleared, head moved"
    if not on_head:
        return "ready: no verdict"
    if kind == "cleared" and merge_cleared.unapproved(pull, comments, head, approvers):
        asked = sorted(set(merge_cleared.APPROVAL.findall(str(pull.get("body") or ""))))
        approved = approval_shas(comments, [], approvers) if asked else {}
        missing = [s for s in asked if not any(head.startswith(x) for x in approved.get(s, []))]
        return f"waiting: Approve {', '.join(missing) or 'label'} at {head[:7]}"
    return f"{kind} on {head[:7]}"


def pull_line(root, repo: str, pull: dict, authors, approvers, late: int, now) -> str:
    number, head = pull["number"], str(pull["head"]["sha"])
    comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
    waiting = waiting_on(comments, {a.lower() for a in authors})
    question = waiting if waiting and session.first_line(waiting).startswith("Question:") else None
    if question:
        found = QUESTION_ID.match(session.first_line(question))
        since = session.moment(question.get("created_at"))
        state = f"blocked: Question {found.group(1) if found else '?'} unanswered"
        text = f"{state} {age(since, now)}"
    else:
        if pull.get("draft"):
            state = "draft"
        else:
            checks, _ = session.check_state(repo, root, head)
            state = {"red": "red", "running": "checks pending"}.get(checks) or verdict_state(
                pull, comments, authors, approvers
            )
        text = f"{state} {age(session.moment(pull.get('created_at')), now)}"
    if waiting and (now - session.moment(waiting.get("created_at"))).total_seconds() > late * 60:
        text += " LATE"
    return f"#{number} {head[:7]} {text}"


def handover_line(repo: str, pull: dict, now) -> str:
    """`HANDOVER #<pr> <minutes>m` from the newest handing-over `Report:` of the pull request's
    author, or `unknown` (amendment 162 item 4); the label is the router's, never recounted."""
    from route import handover_reason  # route imports session

    number = pull["number"]
    comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
    me = str((pull.get("user") or {}).get("login") or "").lower()
    said = [
        session.moment(c.get("created_at"))
        for c in comments
        if session.author_of(c) == me and handover_reason(session.first_line(c)) is not None
    ]
    when = max((t for t in said if t is not None), default=None)
    minutes = f"{max(0, int((now - when).total_seconds() // 60))}m" if when else "unknown"
    return f"HANDOVER #{number} {minutes}"


def held_verdict_line(root, repo: str, pull: dict, authors, now) -> str | None:
    """`HELD VERDICT #<n>` when a ready head waits with no verdict (brief #854 answer 9): the newest
    `Report:` of the pull request's author says ready, its checks are green, no verdict names the
    head, and that report and the conductor's last comment are older than HELD_MINUTES."""
    if pull.get("draft"):
        return None
    number, head = pull["number"], str(pull["head"]["sha"])
    comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
    me = str((pull.get("user") or {}).get("login") or "").lower()
    reports = [
        c
        for c in comments
        if session.author_of(c) == me and session.first_line(c).startswith("Report:")
    ]
    newest = max(reports, key=lambda c: c.get("id") or 0, default=None)
    if newest is None or not session_plan.WAITING_REPORT.match(session.first_line(newest)):
        return None
    if session.verdict_line(comments, 0, head, session.counted_authors(authors, me)) is not None:
        return None
    allowed = {a.lstrip("@").lower() for a in authors}
    spoken = [newest] + [
        c
        for c in comments
        if session.author_of(c) in allowed and not session.first_line(c).startswith(ALIVE)
    ]
    if any(
        now - session.moment(c.get("created_at")) <= timedelta(minutes=HELD_MINUTES) for c in spoken
    ):
        return None
    if session.check_state(repo, root, head)[0] != "green":
        return None
    return f"HELD VERDICT #{number}"


def named(pull: dict, number: int) -> bool:
    ref = str((pull.get("head") or {}).get("ref") or "")
    return session.brief_number(pull) == number or ref == f"claude/brief-{number}"


def silent_line(root, repo: str, issue: dict, pulls: list, every, wait: int, now) -> str | None:
    """Brief #669: the SILENT line of a taken brief whose builder left no trace, else None."""
    number = issue["number"]
    comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
    hours = session.flow_int(root, "claim_hours", session.CLAIM_HOURS, 5)
    takes = session.live_takes(comments, number, pulls, hours)
    if not takes:
        return None
    when, cid, who = max(takes, key=lambda t: t[:2])[:3]
    minutes = int((now - when).total_seconds() // 60)
    if minutes <= wait or any(ESCALATE.match(session.first_line(c)) for c in comments):
        return None
    if any(
        (session.moment(c.get("created_at")), c.get("id") or 0) > (when, cid)
        and session.first_line(c).startswith(ALIVE)
        for c in comments
    ):
        return None
    if any(named(p, number) for p in pulls):
        return None
    branch = f"claude/brief-{number}"
    refs = read(f"repos/{repo}/git/matching-refs/heads/{branch}", f"the branch of #{number}")
    if any(r.get("ref") == f"refs/heads/{branch}" for r in refs if isinstance(r, dict)):
        return None
    if any(named(p, number) and session.moment(p.get("created_at")) >= when for p in every()):
        return None
    return f"SILENT {number} {who} {minutes}; re-fire: Session name: {who}. Item: brief #{number}."


def branch_line(root, repo: str, branch: str) -> str:
    """`<branch>: <state> at <sha7>` of the default branch's head, from the newest run of each
    check of `required_checks` (brief #736): `failure` when one failed, `pending` while one has not
    finished, `success` when all that reported passed, `no run` when none reported. The runs are
    judged by the router's own `judged` with no wait for a name that never runs on the branch; a
    run of another workflow (a skipped `agk-route`) never sets it."""
    from route import FAILED_RUN, FAILED_STATUS, judged, listing  # route imports session

    info = session.gh(f"repos/{repo}/branches/{branch}")
    commit = info.get("commit") if isinstance(info, dict) else None
    head = str(commit.get("sha") or "") if isinstance(commit, dict) else ""
    if not head:
        raise CheckError("the head of the default branch cannot be read")
    checks = listing(f"repos/{repo}/commits/{head}/check-runs", "check_runs")
    status = session.gh(f"repos/{repo}/commits/{head}/status")
    if checks is None or not isinstance(status, dict):
        raise CheckError("the checks of the default branch cannot be read")
    runs, statuses, _ = judged(
        checks, status.get("statuses") or [], session.required_checks(root), wait=False
    )
    runs = [r for r in runs if r.get("conclusion") != "skipped"]  # a skipped run reported nothing
    if not runs and not statuses:
        state = "no run"
    elif any(r.get("conclusion") in FAILED_RUN for r in runs) or any(
        s.get("state") in FAILED_STATUS for s in statuses
    ):
        state = "failure"
    elif any(r.get("status") != "completed" for r in runs) or any(
        s.get("state") == "pending" for s in statuses
    ):
        state = "pending"
    else:
        state = "success"
    return f"{branch}: {state} at {head[:7]}"


def paths_of(files: list) -> set[str]:
    """The paths a list of changed files names: each file, and a renamed file's old name."""
    found: set[str] = set()
    for item in files:
        if isinstance(item, dict):
            found.add(str(item.get("filename")))
            if item.get("status") == "renamed" and item.get("previous_filename"):
                found.add(str(item["previous_filename"]))
    return found


def changed_by(repo: str, branch: str, path: str, compare: dict) -> int | None:
    """The earliest merged pull request of the default branch after the merge base that changed
    PATH: the oldest commit of the compare that `commits?path=` lists, numbered by its subject's
    `(#m)` or by `commits/<sha>/pulls`; None when it cannot be read or named."""
    since = ((compare.get("merge_base_commit") or {}).get("commit") or {}).get("committer") or {}
    query = f"sha={quote(branch)}&path={quote(path)}"
    if since.get("date"):
        query += f"&since={quote(str(since['date']))}"
    touched = session.pages(f"repos/{repo}/commits?{query}")
    if touched is None:
        return None
    shas = {str(c.get("sha")) for c in touched if isinstance(c, dict)}
    for commit in compare.get("commits") or []:
        sha = str(commit.get("sha"))
        if sha not in shas:
            continue
        subject = str((commit.get("commit") or {}).get("message") or "").partition("\n")[0]
        if found := SQUASHED.search(subject):
            return int(found.group(1))
        pulls = session.gh(f"repos/{repo}/commits/{sha}/pulls")
        merged = [p for p in pulls or [] if isinstance(p, dict) and p.get("merged_at")]
        return int(merged[0]["number"]) if merged else None
    return None


def proof_lines(root, repo: str, pulls: list, branch: str) -> list[str]:
    """SPEC-0050 rule 5 (brief #755): `overlap:`, `re-prove:` and `BEHIND` lines of the open builder
    pull requests, from `GET pulls/N/files` and one `GET compare/<head>...<branch>` each. An
    `overlap:` leaves out the files of the table of rule 3 (amendment 141 item 8)."""
    shared = session_plan.exempt(root)
    indexes = set(session_plan.shared_indexes(root))
    mine: dict[int, set[str]] = {}
    brief: dict[int, int] = {}
    reprove: list[str] = []
    behind: list[str] = []
    for pull in sorted(pulls, key=lambda p: p["number"]):
        number = session.brief_number(pull)
        if number is None:
            continue
        n, head = pull["number"], str(pull["head"]["sha"])
        files = session.pages(f"repos/{repo}/pulls/{n}/files")
        compare = session.gh(f"repos/{repo}/compare/{head}...{branch}")
        if files is None or not isinstance(compare, dict):
            reprove.append(f"re-prove: #{n} unknown (cannot be read)")
            continue
        mine[n], brief[n] = paths_of(files), number
        both = sorted(mine[n] & paths_of(compare.get("files") or []))
        if both:
            by = changed_by(repo, branch, both[0], compare)
            light = " light" if all(p in indexes for p in both) else ""  # amendment 171
            reprove.append(
                f"re-prove: #{n} {both[0]} (changed by #{by}){light}"
                if by
                else f"re-prove: #{n} unknown (cannot be read)"
            )
        ahead = compare.get("ahead_by")
        if isinstance(ahead, int) and not isinstance(ahead, bool) and ahead > 0:
            behind.append(f"BEHIND #{n} {ahead}")
    overlap = []
    for a in sorted(mine):
        for b in sorted(x for x in mine if x > a and brief[x] != brief[a]):
            both = sorted(p for p in mine[a] & mine[b] if not any(r.fullmatch(p) for r in shared))
            if both:
                overlap.append(f"overlap: #{a} #{b} {both[0]}")
    return overlap + reprove + behind


# --- the owner's waits (brief #1282, ADR-0543) --------------------------------------------------


def parked_mark(root) -> Path | None:
    """The file of the git directory that holds the parks `sweep` has listed (never tracked)."""
    try:
        found = lease_mark(root)
    except OSError:
        return None
    return found.with_name("parked") if found else None


def owner_lines(
    root, repo: str, pulls: list, settings: dict, authors, approvers, now, kept=None
) -> list:
    """The owner-wait lines of `sweep` (brief #1282 answers 3 and 4): it parks each open pull
    request whose owner wait has passed (`session.park_pull`) and unparks each one this rule parked
    once the owner answered (`session.unpark_pull`), then prints `PARKED #<n> <key>` once per park,
    by its `Parked-by:` comment, and `UNPARKED #<n> <key>; run: ... resume --pr <n>`."""
    listed = {a.lstrip("@").lower() for a in authors or []}
    answerers = listed | {a.lstrip("@").lower() for a in approvers or []}
    mark = parked_mark(root)
    try:
        said = json.loads(mark.read_text(encoding="utf-8")) if mark else []
    except (OSError, ValueError):
        said = []
    said = [x for x in said if isinstance(x, int)] if isinstance(said, list) else []
    parks: list[str] = []
    unparks: list[str] = []
    listed_now: list[int] = []
    for pull in sorted(pulls, key=lambda p: p["number"]):
        number = pull["number"]
        comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
        if kept is not None:
            kept[number] = comments  # read once: the steward's start reads them too (#1322)
        found = session.owner_step(pull, comments, settings, now, listed, answerers)
        if found and found[0] == "unpark" and session.unpark_pull(repo, number, found[1]):
            unparks.append(
                f"UNPARKED #{number} {found[1]}; run: python3 scripts/agk/session.py resume "
                f"--pr {number}"
            )
            continue
        if found and found[0] == "park" and session.park_pull(repo, number, found[1]):
            comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
            pull = {**pull, "labels": [*(pull.get("labels") or []), {"name": "agk:parked"}]}
        own = session.own_park(comments) if "agk:parked" in session.labels_of(pull) else None
        if own is not None:
            cid = int(own[1].get("id") or 0)
            listed_now.append(cid)
            if cid not in said:
                parks.append(f"PARKED #{number} {own[0]}")
    if mark is not None:
        write_held(mark, sorted(set(listed_now)))
    return unparks + parks


STEWARD_PASS = timedelta(minutes=25)  # one conductor pass: its wake-up timer is at most 25 minutes
STEWARD_WHO = "Who: AGK steward"


def waiting_questions(comments: list, answerers: set[str]) -> list[tuple[str, int]]:
    """(Q id, comment id) of each `Question: Q-...` with no `Answer:`, `Maintainer answer:` or
    `Correction:` by an answerer after it that names its Q id or names none, and no steward post
    (one ending `Who: AGK steward`) after it: the steward has taken it (SPEC-0059 rule 2)."""
    open_items: dict[str, int] = {}
    for c in session.in_order(comments):
        line, body = session.first_line(c), str(c.get("body") or "")
        if line.startswith("Question: ") and (found := session.QUESTION_ID.search(line)):
            open_items[found.group(0)] = int(c.get("id") or 0)
        elif session.author_of(c) in answerers and line.startswith(
            ("Answer:", "Maintainer answer:", "Correction:")
        ):
            for qid in session.QUESTION_ID.findall(body) or list(open_items):
                open_items.pop(qid, None)
        if STEWARD_WHO in (x.strip() for x in body.splitlines()):
            open_items.clear()
    return sorted(open_items.items(), key=lambda kv: kv[1])


def steward_lines(root, kept: dict, answerers: set[str], now) -> list[str]:
    """One `STEWARD:` line when a question has waited one conductor pass (`STEWARD_PASS`) with no
    answer and no steward post after it (SPEC-0059 rule 2, brief #1322). Read from the comments
    alone, so every sweep of the same comments prints the same line; the session is named by the
    oldest waiting question, and a second start of a running steward writes nothing (ADR-0557)."""
    due = []
    for number, comments in sorted(kept.items()):
        when = {int(c.get("id") or 0): session.moment(c.get("created_at")) for c in comments}
        for qid, cid in waiting_questions(comments, answerers):
            if when.get(cid) is not None and now - when[cid] >= STEWARD_PASS:
                due.append((number, qid, cid))
    if not due:
        return []
    asks = ", ".join(f"#{n} {q}" for n, q, _ in due)
    name = f"steward-{min(c for *_, c in due)}"
    adapter = configured_start_adapter(root)
    run = f"python3 scripts/agk/launch.py role --role steward --session {name}"
    run += f" --adapter {shlex.quote(adapter)}" if adapter else ""
    return [f"STEWARD: {asks} waited one pass unanswered; run: {run}"]


def configured_start_adapter(root) -> str | None:
    """`launch_adapter` when `auto_start` is on with it in the checkout and on the default branch
    alike, else None."""
    try:
        here = launch.launch_settings(Path(root))
        there = launch.launch_settings(Path(root), f"origin/{launch.default_branch(Path(root))}")
    except (CheckError, OSError):
        return None
    return here[1] if here == there and here[0] is True and here[1] else None


def main_folder_lines(root) -> list[str]:
    """`MAIN-FOLDER: on <branch>, <n> untracked` when the main folder of a clone that several
    sessions share is off the default branch or holds untracked files (brief #1301, ADR-0551);
    the conductor's report lists it under `Needs a fix`. Local git only, never fails the sweep."""
    line = common.main_folder_line(Path(root))
    return [f"MAIN-FOLDER: {line}"] if line else []


def sweep(root) -> int:
    repo = session.repo_name(root)
    authors, approvers = verdict_authors(root), spec_approvers(root)
    late = session.flow_int(root, LATE[0], LATE[1], 0)
    now = datetime.now(UTC)
    # Brief #1314 build (b), ADR-0555 decision 3: the store answers each unchanged brief's comments
    # for the per-brief loops below (`silent_line`, `slot_lines`, the caps' brief pages); the open
    # issues are listed first after the pull requests, so the store has their counts.
    session.STORE.begin(root, repo)
    pulls = read(f"repos/{repo}/pulls?state=open", "the open pull requests")
    issues = read(f"repos/{repo}/issues?state=open", "the open issues")
    lines = [
        pull_line(root, repo, p, authors, approvers, late, now)
        for p in sorted(pulls, key=lambda p: p["number"])
    ] or ["no open pull request"]
    info = session.gh(f"repos/{repo}")
    branch = info.get("default_branch") if isinstance(info, dict) else None
    if not branch:
        raise CheckError("the default branch cannot be read")
    lines += proof_lines(root, repo, pulls, branch)
    lines += caps.over_lines(root, repo, pulls, {a.lower() for a in authors}, now)
    lines += [x for p in pulls if (x := held_verdict_line(root, repo, p, authors, now))]
    lines += [handover_line(repo, p, now) for p in pulls if session.label_of(p) == HANDOVER_LABEL]
    lines.append(branch_line(root, repo, branch))
    lines += main_folder_lines(root)
    lines += [f"red-branch issue: #{i['number']}" for i in issues if session.is_red(i)]
    wait = session.flow_int(root, SILENT[0], SILENT[1], 0)
    cache: list = []

    def every() -> list:  # every pull request, read once and only when a brief needs it
        if not cache:
            cache.append(read(f"repos/{repo}/pulls?state=all", "the pull requests"))
        return cache[0]

    for issue in sorted(session.labelled(issues, session.LABEL), key=lambda i: i["number"]):
        if found := silent_line(root, repo, issue, pulls, every, wait, now):
            lines.append(found)
    lines += slot_lines(root, repo, issues, every, now)
    lines += stall_report(root, repo)
    lines += unacted_lines(root, repo, now, issues, pulls)
    try:  # a bad value is refused in one line naming the setting; every other line still prints
        waits = session.owner_wait_settings(Path(root))
    except CheckError as refused:
        lines.append(f"owner waits: {refused}")
    else:
        kept: dict = {}
        lines += owner_lines(root, repo, pulls, waits, authors, approvers, now, kept)
        answerers = {a.lstrip("@").lower() for a in [*(authors or []), *(approvers or [])]}
        lines += steward_lines(root, kept, answerers, now)  # SPEC-0059 rule 2 (brief #1322)
    lines += start_lines(root, repo, now)  # ready work after a review or a merge (ADR-0500)
    lines += held_builder_lines(root)  # builders the watchdog held on this machine (ADR-0568)
    print("\n".join(lines))
    return 0


# --- over: the counts of an overrun and its cause (brief #781, SPEC-0049 rule 12) ---------------


def head_runs(repo: str, commits: list) -> list | None:
    """The finished, not skipped check runs of each commit, or None when one cannot be read."""
    from route import listing  # route imports session

    found = []
    for c in commits:
        runs = listing(f"repos/{repo}/commits/{c.get('sha')}/check-runs", "check_runs")
        if not isinstance(runs, list):
            return None
        found.append([r for r in runs if r.get("conclusion") not in (None, "skipped")])
    return found


def red_heads(runs: list) -> int:
    """The longest run of heads in a row on which one check failed; no finished run, no head."""
    best = 0
    streak: dict[str, int] = {}
    for ran in filter(None, runs):
        red = {r.get("name") for r in ran if r.get("conclusion") in RED_RUN}
        streak = {name: streak.get(name, 0) + 1 for name in red}
        best = max([best, *streak.values()])
    return best


def file_commits(repo: str, commits: list, runs: list) -> int | str:
    """The most commits that changed one file with no green run between; merges change none."""
    best = 0
    seen: dict[str, int] = {}
    for c, ran in zip(commits, runs, strict=True):
        if len(c.get("parents") or []) < 2:
            detail = session.gh(f"repos/{repo}/commits/{c.get('sha')}")
            if not isinstance(detail, dict) or not isinstance(detail.get("files"), list):
                return caps.UNKNOWN
            for f in detail["files"]:
                seen[f.get("filename")] = seen.get(f.get("filename"), 0) + 1
            best = max([best, *seen.values()])
        if ran and all(r.get("conclusion") in GREEN_RUN for r in ran):
            seen = {}
    return best


def wander_files(repo: str, number: int, body: object) -> int | str:
    """The files of the pull request outside the brief's lines, or `unknown`."""
    globs = session.touches_of(body) if isinstance(body, str) else []
    files = session.pages(f"repos/{repo}/pulls/{number}/files")
    if not globs or files is None:
        return caps.UNKNOWN
    rules = [session.glob_regex(g) for g in globs]
    return sum(not any(r.fullmatch(f.get("filename", "")) for r in rules) for f in files)


def build_end(comments: list, login: str, now: datetime) -> datetime:
    """The builder's `over cap` report ends the build: a person's time is not the builder's."""
    said = [c for c in comments if session.author_of(c) == login.lower()]
    ends = [
        session.moment(c.get("created_at"))
        for c in said
        if OVER_REPORT.match(session.first_line(c))
    ]
    return max(ends, default=now)


def blocked_spans(comments: list, login: str, pushes: list[datetime], end: datetime) -> dict:
    """{the next push or the end: the earliest report of a block before it}."""
    spans: dict[datetime, datetime] = {}
    for c in comments:
        said = session.moment(c.get("created_at"))
        if (
            session.author_of(c) == login.lower()
            and said <= end
            and BLOCKED.match(session.first_line(c))
        ):
            stop = min((p for p in pushes if p > said), default=end)
            spans[stop] = min(spans.get(stop, said), said)
    return spans


def hours_of(repo_data: tuple, login: str, allowed: set[str], opened: str, commits, now) -> tuple:
    """(counted, blocked) hours, each `unknown` when its evidence cannot be read (rules 6, 12)."""
    brief, pull = repo_data
    if not isinstance(brief, list) or not isinstance(pull, list):
        return caps.UNKNOWN, caps.UNKNOWN
    end = build_end(pull, login, now)

    def upto(moment: datetime) -> Decimal | str:  # caps.hours_used on what had happened by then
        early = [
            [c for c in side if session.moment(c.get("created_at")) <= moment]
            for side in (brief, pull)
        ]
        return caps.hours_used(early[0], early[1], login, allowed, opened, moment)

    counted = upto(end)
    if commits is None or not isinstance(counted, Decimal):
        return counted, caps.UNKNOWN
    pushes = [
        when(str(((c.get("commit") or {}).get("committer") or {}).get("date"))) for c in commits
    ]
    known = [p for p in pushes if p is not None]
    if len(known) != len(pushes):
        return counted, caps.UNKNOWN
    blocked = Decimal("0.0")
    for stop, start in blocked_spans(pull, login, known, end).items():
        high, low = upto(stop), upto(start)
        if not isinstance(high, Decimal) or not isinstance(low, Decimal):
            return counted, caps.UNKNOWN
        blocked += high - low
    return counted, min(blocked, counted)


def cause_of(red, files, wander, counted, blocked) -> str:
    """Rule 12: the first rule met, in order; evidence that cannot be read stops the walk."""
    if (red != caps.UNKNOWN and red >= 2) or (files != caps.UNKNOWN and files >= 3):
        return "loop"
    if caps.UNKNOWN in (red, files, wander):
        return caps.UNKNOWN
    if wander:
        return "wander"
    if caps.UNKNOWN in (counted, blocked):
        return caps.UNKNOWN
    return "blocked" if blocked * 2 > counted else "estimate"


def over(root, number: int) -> int:
    """`over --pr N`: the counts of rule 12, one line each, and the cause; GET only."""
    repo = session.repo_name(root)
    pull = session.gh(f"repos/{repo}/pulls/{number}")
    pull = pull if isinstance(pull, dict) else {}
    brief = session.brief_number(pull) if pull else None
    commits = session.pages(f"repos/{repo}/pulls/{number}/commits") if pull else None
    runs = head_runs(repo, commits) if commits is not None else None
    red = red_heads(runs) if runs is not None else caps.UNKNOWN
    known = commits is not None and runs is not None
    files = file_commits(repo, commits or [], runs or []) if known else caps.UNKNOWN
    issue = session.gh(f"repos/{repo}/issues/{brief}") if brief else None
    body = issue.get("body") if isinstance(issue, dict) else None
    wander = wander_files(repo, number, body) if pull else caps.UNKNOWN
    login = str((pull.get("user") or {}).get("login") or "")
    said = (
        session.pages(f"repos/{repo}/issues/{brief}/comments") if brief else None,
        session.pages(f"repos/{repo}/issues/{number}/comments") if pull else None,
    )
    allowed = {a.lower() for a in verdict_authors(root)}
    opened = str(pull.get("created_at"))
    counted, blocked = hours_of(said, login, allowed, opened, commits, datetime.now(UTC))
    counts = (red, files, wander, counted, blocked)
    print(f"over #{number} brief {f'#{brief}' if brief else caps.UNKNOWN}")
    for key, value in zip(OVER_KEYS, counts, strict=True):
        print(f"{key} {value}")
    print(f"unreadable {counts.count(caps.UNKNOWN)}")
    print(f"cause {cause_of(*counts)}")
    return 0


# --- the pool: every slot in the report, the health issues (brief #776 answer 5, ADR-0368) --------


def slot_state(comments: list, name: str, allowed: set[str], now: datetime) -> tuple[bool, str]:
    """(whether the slot has a valid lease, the time it died or `no lease yet`)."""
    found = session.slot_marker(comments, name, allowed)
    if found is None:
        return False, "no lease yet"
    if session.slot_holder(found, now):
        return True, ""
    stamp = when(found[1].group(2)) or now
    if found[1].group(1) == "active":
        stamp += timedelta(minutes=session.SLOT_MINUTES)
    return False, stamp_of(stamp)


def assignments(root, repo: str) -> tuple[list, set[str], list[str]]:
    """The comments of the assignments issue, the listed authors and the names of the slots."""
    issue = session.conductor_issue(repo)
    comments = read(f"repos/{repo}/issues/{issue}/comments", f"the comments of #{issue}")
    allowed = {a.lstrip("@").lower() for a in verdict_authors(root)}
    return comments, allowed, [f"s{n + 1}" for n in range(session.builder_slots(root))]


def slot_lines(root, repo: str, issues: list, every, now: datetime) -> list[str]:
    """One line per slot: working (brief), idle, or dead since when; none with `start`."""
    if session.builder_start(root) != "assign":
        return []
    comments, allowed, names = assignments(root, repo)
    hours = session.flow_int(root, "claim_hours", session.CLAIM_HOURS, 1)
    takes: dict[str, int] = {}
    for item in sorted(session.labelled(issues, session.LABEL), key=lambda i: i["number"]):
        number = item["number"]
        said = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
        for take in session.live_takes(said, number, every(), hours):
            takes.setdefault(take[2], number)
    lines = []
    for name in names:
        alive, since = slot_state(comments, name, allowed, now)
        if not alive:
            state = "dead (no lease yet)" if since == "no lease yet" else f"dead since {since}"
        else:
            state = f"working (#{takes[name]})" if name in takes else "idle"
        lines.append(f"slot {name}: {state}{last_run(comments, name, allowed, ', ')}")
    return lines


def last_run(comments: list, name: str, allowed: set[str], lead: str) -> str:
    """`<lead>last run <hh:mm> decided <...>` from the slot's marker (brief #998, ADR-0425), or
    nothing when the marker records no run."""
    found = session.slot_marker(comments, name, allowed)
    log = session.slot_log(found[0]) if found else None
    start = when(log[0]) if log else None
    return f"{lead}last run {start:%H:%M} decided {log[2]}" if log and start else ""


UNACTED_MINUTES = 75  # brief #998 answer 2: past one hourly run of the slot and its margin


def acted(decided: str, match) -> bool:
    """Whether a run's decision is the assignment `match`: `assign #b ...` or `follow-up pr #n`."""
    if match.group(5):
        return decided.startswith(f"follow-up pr #{match.group(5)} ")
    return decided == f"assign {match.group(2)}"


def stale_brief(repo: str, line: dict, match, issues: list | None, pulls: list | None) -> bool:
    """Brief #1020 answer 2: an `Assign:` of a brief that is closed (not among the open `issues`),
    that a slot took after the line, or that an open pull request names, by
    `session_plan.assign_spent`; False when the open issues were not read. The brief's comments
    are read only while it is open; when they cannot be read, the take test finds nothing."""
    if issues is None:
        return False
    number, build = int(match.group(3)), match.group(4)
    known = {i["number"] for i in issues if isinstance(i.get("number"), int)}
    said = session.pages(f"repos/{repo}/issues/{number}/comments") if number in known else []
    takes = session.all_takes(said or [])
    cid = line.get("id", 0)
    return session_plan.assign_spent(number, build, cid, known, takes, pulls or [])


def spent_line(
    repo: str, name: str, line: dict, match, issues: list | None = None, pulls: list | None = None
) -> bool | None:
    """Whether an `Assign:` was acted on since: a later `taken:` of the slot for a brief, a later
    `Report:` on the pull request for a follow-up; None when that cannot be read. A brief's line
    that `stale_brief` finds spent by the open issues and pull requests is spent (brief #1020)."""
    if match.group(5):
        try:
            return session.reports_after(repo, int(match.group(5)), line.get("id", 0))
        except CheckError:
            return None
    if stale_brief(repo, line, match, issues, pulls):
        return True
    return session.spent(repo, name, line)


def unacted_lines(
    root, repo: str, now: datetime, issues: list | None = None, pulls: list | None = None
) -> list[str]:
    """One `UNACTED:` line per slot whose newest `Assign:` no run acted on (brief #998, ADR-0425):
    a run started after it and decided otherwise, or none started after it within 75 minutes; a
    spent assignment, `none`, or what cannot be read adds no line. None with `start`. With the
    open `issues` and open `pulls`, a line whose brief is closed, taken by a slot after it or named
    by an open pull request is spent (brief #1020)."""
    if session.builder_start(root) != "assign":
        return []
    comments, allowed, names = assignments(root, repo)
    lines = []
    for name in names:
        said = [(c, m) for c in comments if (m := session.assign_line(c, name, allowed))]
        if not said:
            continue
        line, match = max(said, key=lambda x: x[0].get("id", 0))
        posted = when(str(line.get("created_at")))
        if match.group(2) == "none" or posted is None:
            continue
        found = session.slot_marker(comments, name, allowed)
        log = session.slot_log(found[0]) if found else None
        start = when(log[0]) if log else None
        if log is not None and start is not None and start >= posted:
            if acted(log[2], match):
                continue
        elif now - posted <= timedelta(minutes=UNACTED_MINUTES):
            continue
        if spent_line(repo, name, line, match, issues, pulls) is not False:
            continue
        minutes = int((now - posted).total_seconds() // 60)
        tail = last_run(comments, name, allowed, "; ") or "; no run recorded"
        lines.append(f"UNACTED: {session.first_line(line)} ({minutes} min{tail})")
    return lines


NO_CONDUCTOR, POOL_DOWN = "No live conductor", "Builder pool down"


def pool_state(root, repo: str) -> list[tuple[str, bool, bool, str]]:
    """(title, whether the leases are down, whether work waits, the issue's text) of each health
    issue; none with `builder_start = "start"`, and no conductor row while its lease is off."""
    if session.builder_start(root) != "assign":
        return []
    days = timedelta(days=slot_active_days(root))
    now = datetime.now(UTC)
    briefs = session.labelled(
        read(f"repos/{repo}/issues?state=open&labels={session.LABEL}", "the open briefs"),
        session.LABEL,
    )
    ready = [p for p in read(f"repos/{repo}/pulls?state=open", "the open pull requests")
             if not p.get("draft")]  # fmt: skip
    rows = []
    issue = plan_issue(root)
    if issue is not None:
        down = lease_holder(plan_comments(repo, issue), verdict_authors(root), now) is None
        text = (
            f"No conductor holds a valid lease on #{issue} (setting: {PLAN_ISSUE} in the flow "
            "table of agk.toml) while work waits. This issue closes when the lease is back."
        )
        rows.append((NO_CONDUCTOR, down, bool(briefs or ready), text))
    comments, allowed, names = assignments(root, repo)
    window = timedelta(minutes=session.flow_int(root, SEEN, SLOT_SEEN_MINUTES, 1))
    dead, retired, counted = [], [], 0
    for name in names:
        seen = slot_seen(comments, name, allowed)
        said = f"{name} ({f'last seen {stamp_of(seen)}' if seen else 'never'})"
        alive = slot_state(comments, name, allowed, now)[0]
        if not alive and (seen is None or now - seen >= days):
            retired.append(said)  # never ran, or not this week: not counted (ADR-0498)
            continue
        counted += 1
        if not alive and seen is not None and now - seen >= window:
            dead.append(said)
    text = (
        f"Slots not seen within the window: {', '.join(dead) or 'none'}, of {counted} counted. "
        f"Retired (not seen within {ACTIVE} days, not counted): {', '.join(retired) or 'none'} "
        f"(settings: builder_slots, {SEEN} and {ACTIVE} in the flow table of agk.toml). This "
        "issue closes when the slots run again."
    )
    rows.append((POOL_DOWN, len(dead) * 3 > counted, bool(briefs), text))
    return rows


SEEN, SLOT_SEEN_MINUTES = "slot_seen_minutes", 90  # one hourly run plus margin (ADR-0412)
ACTIVE, SLOT_ACTIVE_DAYS = "slot_active_days", 7  # a slot that ran this week counts (ADR-0498)


def slot_active_days(root) -> int:
    """`slot_active_days` of the `[flow]` table, 7 when unset: a positive whole number of days, or
    refused naming the setting, never the value (brief #1172, ADR-0498)."""
    value = session.flow_value(root, ACTIVE, SLOT_ACTIVE_DAYS, 1)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CheckError(f"setting: flow.{ACTIVE} must be a whole number of days, 1 or more")
    return value


def slot_seen(comments: list, name: str, allowed: set[str]) -> datetime | None:
    """The time on the slot's lease marker by a listed author: it is edited in place by `taken`,
    `renewed` and `released`, so it is the newest of the three; None when it has none."""
    found = session.slot_marker(comments, name, allowed)
    return when(found[1].group(2)) if found else None


# --- merge-queue (rows 3 and 22; brief #643 build (b), ADR-0329) ------------------------------

BATCH = 5  # merges in one batch unless --max-batch says otherwise
BATCH_SIZE = re.compile(r"[1-9][0-9]?")
WAIT = ("merge_queue_wait_minutes", 60)  # the one wait for the default branch's run, at the end
SETTLE, PAUSE = 10, 3.0  # reads of a pull request until GitHub knows its mergeable state
MERGED = re.compile(r"merge-cleared #\d+ [0-9a-f]{12}: merged ([0-9a-f]{12})")
STOPPED = "merge-cleared: stopped:"  # merge_cleared.py's own red line (SPEC-0039 rule 6)
RUNS = "repos/{}/actions/workflows/governance.yml/runs?branch={}&event=push&per_page=100"
NOT_LISTED = (
    "the verdict's author is not a listed verdict author "
    "(setting: verdict_authors in config/reviewers.yaml)"
)


def settle(repo: str, number: int) -> None:
    """Read the pull request again, at most SETTLE times a PAUSE apart, while GitHub says its
    mergeable state is `unknown` (it computes the state in the background after a read; a hold
    would read `unknown` as a conflict). What it says then is merge_cleared.py's to judge."""
    for _ in range(SETTLE):
        pull = merge_cleared.read_json(f"repos/{repo}/pulls/{number}", dict, "the pull request")
        if pull.get("mergeable_state") != "unknown":
            return
        time.sleep(PAUSE)


def queued(root, repo: str, rules: merge_cleared.Rules) -> tuple[list[tuple[int, str]], list[str]]:
    """The open pull requests to merge, as (number, head) in the order of their clearing verdicts,
    and one `not queued:` line for each cleared one that a hold or an unlisted author keeps out."""
    authors = authors_of(rules.people)
    found, kept_out = [], []
    for pull in read(f"repos/{repo}/pulls?state=open", "the open pull requests"):
        number, sha = int(pull["number"]), str((pull.get("head") or {}).get("sha") or "")
        try:
            if not pull.get("draft"):
                settle(repo, number)
            _, verdict, *_ = merge_cleared.holds(root, repo, number, sha, rules)
            counted = session.counted_authors(authors, session.author_of(pull)) or []
            if merge_cleared.login(verdict) not in {a.lstrip("@").lower() for a in counted}:
                raise merge_cleared.Held(NOT_LISTED)
        except merge_cleared.NotCleared:
            continue
        except (merge_cleared.Held, merge_cleared.Refused) as exc:
            kept_out.append(f"not queued: #{number} {sha[:12]}: {exc}")
            continue
        found.append((merge_cleared.stamp(verdict), number, sha))
    return [(number, sha) for _, number, sha in sorted(found)], kept_out


def run_merge(root, number: int, sha: str) -> tuple[int, str]:
    """`python3 scripts/agk/merge_cleared.py --pr N --sha SHA`, the project's own file beside this
    one, as its own process; its line is printed in full. (Its exit code, its standard output.)"""
    script = Path(__file__).resolve().parent / "merge_cleared.py"
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(script), "--pr", str(number), "--sha", sha],
        cwd=root,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(proc.stdout, end="", flush=True)
    return proc.returncode, proc.stdout


def full_sha(root, short: str) -> str | None:
    code, found = merge_cleared.git_out(root, "rev-parse", "--verify", "-q", f"{short}^{{commit}}")
    return found if code == 0 and merge_cleared.SHA.fullmatch(found) else None


def branch_state(root, repo: str, branch: str, sha: str) -> str:
    """`green`, `red` or `pending` for the default branch's commit SHA: its last 100 push runs of
    governance.yml, read as ADR-0302 reads them (a run replaced while it waited is covered by the
    next completed run on a later commit that contains it)."""
    merge_cleared.git_out(root, "fetch", "-q", "origin", branch)
    data = session.gh(RUNS.format(repo, branch))
    listed = data.get("workflow_runs") if isinstance(data, dict) else None
    if not isinstance(listed, list):
        raise CheckError("the runs of the default branch cannot be read")
    return covered(sha, listed, contained_in(root))[0]


def batch_run(root, repo: str, branch: str, sha: str, minutes: int) -> str:
    """The one wait at the end: the state of SHA, polled until it is not `pending` or MINUTES
    have passed; a read that fails is printed and tried again."""
    interval = session.flow_int(root, POLL[0], POLL[1], 0)
    end = time.monotonic() + minutes * 60
    while True:
        try:
            state = branch_state(root, repo, branch, sha)
        except CheckError as exc:
            print(f"error: {exc}; retrying", file=sys.stderr, flush=True)
            state = "pending"
        if state != "pending" or time.monotonic() >= end:
            return state
        time.sleep(interval)


def merge_queue(root, dry: bool, limit: int) -> int:
    rules = merge_cleared.ruled(root)
    repo = merge_cleared.repo_of(root)
    if (issue := plan_issue(root)) is not None:
        comments = plan_comments(repo, issue)
        holder = lease_holder(comments, authors_of(rules.people), datetime.now(UTC))
        if holder and holder[0] != own_name(root):
            raise merge_cleared.Held(
                f"another conductor holds the lease until {stamp_of(holder[1])} {LEASE_SETTING}"
            )
    order, kept_out = queued(root, repo, rules)
    if kept_out:
        print("\n".join(kept_out))
    batch, rest = order[:limit], order[limit:]
    if dry or not batch:
        for place, (number, sha) in enumerate(batch, 1):
            print(f"merge-queue: {place}. #{number} {sha[:12]}")
        if rest:
            print(f"merge-queue: {len(rest)} more wait for the next batch")
        if not batch:
            print("merge-queue: nothing to merge")
        return 0
    merged: list[tuple[int, str]] = []
    code, red = 0, False
    for place, (number, sha) in enumerate(batch):
        if place:
            settle(repo, number)
        code, out = run_merge(root, number, sha)
        if found := MERGED.search(out):
            merged.append((number, found.group(1)))
        elif out.startswith(STOPPED):
            merged.append((number, ""))
            red = True
        if code != 0:
            break
    names = " ".join(f"#{n}" for n, _ in merged)
    if code != 0:
        print(f"merge-queue: stopped at #{number} (exit {code}); merged: {names or 'none'}")
    elif rest:
        print(f"merge-queue: {len(rest)} more wait for the next batch")
    if not merged or red:
        return code
    issues = merge_cleared.read_pages(f"repos/{repo}/issues?state=open", "the open issues")
    if merge_cleared.local_mode(rules.data, issues):
        print(f"merge-queue: local mode, no run of the default branch to wait for; batch {names}")
        return code
    branch = str(rules.data.get("default_branch", "main"))
    last = full_sha(root, merged[-1][1])
    if last is None:
        raise CheckError("the merge commit of the last merge cannot be read")
    minutes = session.flow_int(root, WAIT[0], WAIT[1], 0)
    state = batch_run(root, repo, branch, last, minutes)
    if state == "green":
        print(f"merge-queue: {branch} green at {last[:12]} after the batch {names}")
        return code
    if state == "red":
        print(f"merge-queue: stopped: {branch} red at {last[:12]} after the batch {names}")
        return 1
    print(
        f"merge-queue: the run of {branch} at {last[:12]} has not ended after {minutes} minutes; "
        f"batch {names}"
    )
    return code or 3


# --- rerun (rows 18 and 19), check-verdict and lease (brief #700, ADR-0330) --------------------

PR_NUMBER = re.compile(r"[1-9][0-9]{0,9}")
NAME = re.compile(r"[A-Za-z0-9._][A-Za-z0-9._-]*")  # a conductor's name, never an option
HEAD_RUNS = "repos/{}/actions/runs?event=pull_request&head_sha={}&per_page=100"
DRAFT_STEP = ("ccr/convert_to_draft", "ccr/ready_for_review")  # the runtime's routes (verify)
ADR_FILE = re.compile(r"docs/adr/\d{4}-[^/]+\.md")
VERDICT_SHAPE = "the first line is not `Verdict: cleared|fix list|rejected <sha>` (session rule 1)"
CORRECTION_EMPTY = (
    "a Correction: line needs its text: 'Correction: <what was wrong>; <what stands>'"
)
APPROVAL_SHAPE = (
    "SPEC-0032 rule 5: an Approval: line reads 'Approval: SPEC-<n> <path> Draft -> Approved, "
    'waiting for a person: post "Approve: SPEC-<n>"\''
)
FINAL_PATH = "SPEC-0021 rule 2: a Final: line names a path that does not exist on the head"
NO_ITEMS = (
    "brief #854 answer 1: a fix list with no numbered item and no Final: line on a pull request "
    "with no Proposed ADR gives the builder nothing to do; the verdict is `cleared`"
)
OTHER_HEAD = "session rule 1: the verdict names a head that is not the pull request's current head"
PLAN_ISSUE = "plan_issue"
LEASE_SETTING = f"(setting: {PLAN_ISSUE} in the flow table of agk.toml)"
LEASE_OFF = f"lease: off {LEASE_SETTING}"
LEASE_MINUTES = 10  # ADR-0368: a dead holder is replaced by the next staggered start
WATCH_BOUND = 300  # seconds: `watch` returns by then with `tick` (ADR-0368, ADR-0402)
RENEW_EVERY = 240  # seconds between renewals during one watch
LEASE_LINE = re.compile(
    r"Conductor: (active|released) (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (\S+)"
    r"(?: since (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z))?"
)
TIME = "%Y-%m-%dT%H:%M:%SZ"


def read_one(endpoint: str, what: str) -> dict:
    found = session.gh(endpoint)
    if not isinstance(found, dict):
        raise CheckError(f"{what} cannot be read")
    return found


def post(endpoint: str, what: str, *extra: str, method: str = "POST") -> None:
    """One write; a comment's body ends with `Who: AGK conductor` (brief #1289, ADR-0546)."""
    fields = common.who_fields(endpoint, method, extra, role="conductor")
    if session.gh(endpoint, *fields, method=method) is None:
        raise CheckError(what)


def reprove(root, number: int, apply: bool) -> int:
    """SPEC-0050 amendment 171 (brief #1163): the light re-prove of pull request NUMBER. It reads
    the pull request (GET), fetches its base branch and `refs/pull/<n>/head`, and judges with
    `session_plan.reprove_kind`; only `light` goes on: it prints the one update it would make and,
    with APPLY, makes it (`PUT pulls/<n>/update-branch` pinned by `expected_head_sha`), reads the
    new head and posts `Report: <new head> merge of main (light re-prove, ...)`. A full re-prove or
    a conflict exits 3 and writes nothing; a refused or unreadable step is an error (exit 1)."""
    repo = session.repo_name(root)
    pull = read_one(f"repos/{repo}/pulls/{number}", "the pull request")
    head = str((pull.get("head") or {}).get("sha") or "")
    branch = str((pull.get("base") or {}).get("ref") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not branch:
        raise CheckError("the pull request cannot be read")
    lead = f"reprove: #{number} {head[:12]}:"
    fetched = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "fetch", "-q", "origin", branch, f"refs/pull/{number}/head"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
    )  # fmt: skip
    if fetched.returncode != 0:
        raise CheckError("the default branch or the head cannot be fetched")
    kind, files = session_plan.reprove_kind(root, f"refs/remotes/origin/{branch}", head)
    if kind is None:
        raise CheckError("the re-prove state cannot be read")
    if kind == "none":
        print(f"{lead} not in the re-prove state; nothing to update")
        return 0
    if kind != "light":
        other = [f for f in files if f not in session_plan.shared_indexes(root)]
        why = "conflict" if kind == "conflict" else f"{other[0]} is not a shared index"
        print(f"{lead} full re-prove ({why}); the builder merges the default branch")
        return merge_cleared.EXIT_HELD
    step = f"PUT repos/{repo}/pulls/{number}/update-branch expected_head_sha={head}"
    print(
        f"{lead} light ({', '.join(files)}); the step: {step}"
        + ("" if apply else "; add --apply to do it")
    )
    if not apply:
        return 0
    endpoint = f"repos/{repo}/pulls/{number}/update-branch"
    post(endpoint, "update-branch was refused", "-f", f"expected_head_sha={head}", method="PUT")
    new = head
    for _ in range(REPROVE_WAITS):
        found = session.gh(f"repos/{repo}/pulls/{number}")
        new = (
            str(((found or {}).get("head") or {}).get("sha") or "")
            if isinstance(found, dict)
            else ""
        )
        if new and new != head:
            break
        time.sleep(REPROVE_PAUSE)
    if not re.fullmatch(r"[0-9a-f]{40}", new) or new == head:
        raise CheckError("the branch was updated but its new head cannot be read; no Report posted")
    body = f"body=Report: {new} {REPROVE_REPORT}"
    post(f"repos/{repo}/issues/{number}/comments", "the Report cannot be posted", "-f", body)
    print(f"{lead} updated to {new[:12]}; Report posted")
    return 0


def rerun(root, number: int, apply: bool) -> int:
    repo = session.repo_name(root)
    pull = read_one(f"repos/{repo}/pulls/{number}", "the pull request")
    head = str((pull.get("head") or {}).get("sha") or "")
    data = read_one(HEAD_RUNS.format(repo, head), "the runs of the head")
    listed = data.get("workflow_runs")
    if not isinstance(listed, list):
        raise CheckError("the runs of the head cannot be read")
    runs = [r for r in listed if isinstance(r, dict) and r.get("event") == "pull_request"]
    lead = f"rerun: #{number} {head[:12]}:"
    cancelled = [r for r in runs if r.get("conclusion") == "cancelled"]
    for run in cancelled:
        rid, name = run.get("id"), run.get("name")
        if apply:
            post(f"repos/{repo}/actions/runs/{rid}/rerun", f"run {rid} cannot be rerun")
        done = "rerun" if apply else "add --apply to rerun it"
        print(f"{lead} run {rid} ({name}) cancelled; {done}")
    if cancelled:
        return 0
    if runs and all(r.get("conclusion") == "skipped" for r in runs):
        if pull.get("draft"):
            print(
                f"{lead} every run of the head skipped; the pull request is a draft, whose runs "
                "skip until it is marked ready"
            )
            return 0
        steps = [f"POST repos/{repo}/pulls/{number}/{route}" for route in DRAFT_STEP]
        print(
            f"{lead} every run of the head skipped (a push to a ready pull request); the step: "
            f"{steps[0]}, then {steps[1]}" + ("" if apply else "; add --apply to do it")
        )
        if apply:
            for route in DRAFT_STEP:
                post(f"repos/{repo}/pulls/{number}/{route}", f"the step {route} was refused")
            print(f"{lead} converted to draft and back; its runs start")
        return 0
    print(f"{lead} {'nothing to rerun' if runs else 'no run of the head'}")
    return 0


def line_problem(body: str) -> str | None:
    """The rule a `Verdict:`, `Final:` or `Correction:` comment breaks, read from its text alone."""
    from route import ASKED  # route imports merge_cleared, which this module imports

    text = body.strip()
    first = text.splitlines()[0].strip() if text else ""
    if first.startswith("Final:"):
        return NOT_FIX_LIST
    if first.startswith("Correction:"):
        return None if first[len("Correction:") :].strip() else CORRECTION_EMPTY
    if not session.VERDICT.fullmatch(first):
        return VERDICT_SHAPE
    for line in text.splitlines():
        if line.strip().startswith("Approval:") and not ASKED.fullmatch(line.strip()):
            return APPROVAL_SHAPE
    return verdict_problem(text)


def adr_is_proposed(repo: str, path: str, head: str) -> bool:
    record = read_one(f"repos/{repo}/contents/{quote(path)}?ref={head}", "the ADR on the head")
    try:
        text = base64.b64decode(record["content"]).decode("utf-8")
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckError("the ADR on the head cannot be read") from exc
    return "- Status: Proposed" in text.splitlines()


def head_problem(
    repo: str, number: int, body: str, head: str, files: list | None = None
) -> str | None:
    """The rule a verdict that names HEAD breaks against the pull request (brief #854 answer 1), or
    None. It reads only what the verdict needs; a read that fails is a CheckError, never `ok`."""
    text = body.strip()
    finals = [m.group(1) for m in map(FINAL_LINE.fullmatch, text.splitlines()) if m]
    if finals:
        tree = read_one(f"repos/{repo}/git/trees/{head}?recursive=1", "the files of the head")
        listed = tree.get("tree")
        if not isinstance(listed, list) or tree.get("truncated"):
            raise CheckError("the files of the head cannot be read")
        have = {str(x.get("path")) for x in listed if isinstance(x, dict)}
        return FINAL_PATH if any(path not in have for path in finals) else None
    if not text.startswith("Verdict: fix list") or fix_items(text):
        return None
    if files is None:
        files = read(f"repos/{repo}/pulls/{number}/files", "the files of the pull request")
    adrs = [
        str(f.get("filename"))
        for f in files
        if ADR_FILE.fullmatch(str(f.get("filename"))) and f.get("status") != "removed"
    ]
    return None if any(adr_is_proposed(repo, path, head) for path in adrs) else NO_ITEMS


def full_problem(repo: str, number: int, body: str, root=None) -> str | None:
    """`line_problem`, then for a verdict the reads of pull request NUMBER: the check that
    `check-verdict --pr` and the guard run before a post, the reviewer's gate last (ADR-0528). A
    read that fails is a CheckError."""
    problem = line_problem(body)
    if problem or not body.strip().startswith("Verdict:"):
        return problem
    pull = read_one(f"repos/{repo}/pulls/{number}", "the pull request")
    head = str((pull.get("head") or {}).get("sha") or "")
    if not head:
        raise CheckError("the pull request cannot be read")
    named = session.VERDICT.fullmatch(body.strip().splitlines()[0].strip())
    if named is None or not head.startswith(named.group(2)):
        return OTHER_HEAD
    return head_problem(repo, number, body, head) or gate_problem(root, repo, number, head, body)


def check_verdict(path: str, root=None, number: int | None = None) -> int:
    try:
        body = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the verdict file cannot be read") from exc
    problem = (
        line_problem(body)
        if number is None
        else full_problem(session.repo_name(root), number, body, root)
    )
    print("ok" if problem is None else problem)
    return 0 if problem is None else 1


def plan_issue(root) -> int | None:
    """The plan issue of `[flow] plan_issue`, None when the lease is off."""
    value = session.flow_value(root, PLAN_ISSUE, None, 0)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CheckError(f"{PLAN_ISSUE} of the flow table must be an issue number, 1 or more")
    return value


def plan_comments(repo: str, issue: int) -> list:
    return read(f"repos/{repo}/issues/{issue}/comments", f"the comments of #{issue}")


def lease_comment(comments: list, authors: list[str]) -> tuple[dict, re.Match] | None:
    """The newest `Conductor:` marker by a listed verdict author and its reading, else None."""
    listed = {a.lstrip("@").lower() for a in authors}
    found = None
    for c in sorted(comments, key=lambda c: (str(c.get("created_at") or ""), c.get("id") or 0)):
        if merge_cleared.login(c) not in listed:
            continue
        if match := LEASE_LINE.fullmatch(session.first_line(c)):
            found = (c, match)
    return found


def lease_holder(comments: list, authors: list[str], now: datetime) -> tuple[str, datetime] | None:
    """(name, end) of a valid active lease, else None (no marker, released or expired)."""
    found = lease_comment(comments, authors)
    if found is None or found[1].group(1) != "active":
        return None
    start = when(found[1].group(2))
    if start is None:
        return None
    end = start + timedelta(minutes=LEASE_MINUTES)
    return (found[1].group(3), end) if now < end else None


def stamp_of(moment: datetime) -> str:
    return moment.strftime(TIME)


def lease_mark(root) -> Path | None:
    """The file of the git directory that holds this checkout's conductor name (never tracked)."""
    code, found = merge_cleared.git_out(root, "rev-parse", "--git-dir")
    if code != 0 or not found:
        return None
    base = Path(found) if Path(found).is_absolute() else Path(root) / found
    return base / "agk" / "lease"


def own_name(root) -> str | None:
    mark = lease_mark(root)
    try:
        return mark.read_text(encoding="utf-8").strip() or None if mark else None
    except OSError:
        return None


def write_marker(repo: str, issue: int, found, text: str) -> None:
    """Edit the marker comment in place, or post the first one."""
    if found is None:
        post(f"repos/{repo}/issues/{issue}/comments", "the lease cannot be written", "-f", text)
    else:
        post(
            f"repos/{repo}/issues/comments/{found[0].get('id')}",
            "the lease cannot be written",
            "-f",
            text,
            method="PATCH",
        )


def lease(root, mode: str, name: str | None, takeover: bool = True) -> int:
    issue = plan_issue(root)
    if issue is None:
        print(LEASE_OFF)
        return 0 if mode == "--show" else 1
    repo = session.repo_name(root)
    comments, authors = plan_comments(repo, issue), verdict_authors(root)
    now = datetime.now(UTC)
    holder = lease_holder(comments, authors, now)
    if mode == "--show":
        if holder:
            print(f"lease: held by {holder[0]} until {stamp_of(holder[1])}")
        else:
            print("lease: free")
        return 0
    if holder and holder[0] != name:
        relay = mode == "--take" and takeover
        stalled = lease_stall(root, repo, comments, authors, now) if relay else None
        if stalled is None:
            print(f"lease: held by {holder[0]} until {stamp_of(holder[1])} {LEASE_SETTING}")
            return merge_cleared.EXIT_HELD
        line = f"body=STALL conductor {stalled[0]} {stalled[1]} min"
        post(f"repos/{repo}/issues/{issue}/comments", "the stall line cannot be posted", "-f", line)
        holder = None
    found = lease_comment(comments, authors)
    mark = lease_mark(root)
    if mode == "--take":
        taken = found[1].group(4) or found[1].group(2) if holder and found else stamp_of(now)
        text = f"body=Conductor: active {stamp_of(now)} {name} since {taken}"
        write_marker(repo, issue, found, text)
        if mark is not None:
            mark.parent.mkdir(parents=True, exist_ok=True)
            mark.write_text(f"{name}\n", encoding="utf-8")
        print(f"lease: taken by {name} until {stamp_of(now + timedelta(minutes=LEASE_MINUTES))}")
        return 0
    if holder:  # --release by the holder
        write_marker(repo, issue, found, f"body=Conductor: released {stamp_of(now)} {name}")
        print(f"lease: released by {name}")
    else:
        print("lease: free")
    if mark is not None and mark.exists():
        mark.unlink()
    return 0


# --- watchdog (brief #1237, ADR-0525) ---------------------------------------------------------

WATCHDOG_NAME = "conductor-local"
WATCHDOG_TASK = "AGK conductor watchdog"
WATCHDOG_MINUTES = 30
WATCHDOG_SETTINGS = "(settings: auto_start and launch_adapter in the flow table of agk.toml)"
WATCHDOG_PROMPT = (
    "You are the AGK conductor {name} for repository {repo}, started by the local watchdog "
    "(`python3 scripts/agk/conductor.py watchdog`) because no conductor held the lease. Your role "
    "is `.claude/agents/conductor.md` on the default branch: read it, `CLAUDE.md`, "
    "`constitution/principles.md` and `config/session-rules.md` first and follow them exactly. "
    "Take the lease first with `python3 scripts/agk/conductor.py lease --take {name}`; when it "
    "is refused another conductor holds it, so end at once. Renew it and release it as the role "
    "says, and run `python3 scripts/agk/session.py queue --role conductor` before anything else "
    "(session rule 11).\n"
)


def watchdog_args(args: list[str]) -> tuple[str, bool, bool] | None:
    """(NAME, `--install` given, `--pass` given) for `watchdog [--session NAME] [--install]
    [--pass]`; None otherwise."""
    rest, name, install, scripted = args[1:], WATCHDOG_NAME, False, False
    while rest:
        if rest[0] == "--install" and not install:
            install, rest = True, rest[1:]
        elif rest[0] == "--pass" and not scripted:
            scripted, rest = True, rest[1:]
        elif rest[0] == "--session" and len(rest) > 1 and NAME.fullmatch(rest[1]):
            name, rest = rest[1], rest[2:]
        else:
            return None
    return name, install, scripted


def install_line(root, name: str, platform: str, scripted: bool = False) -> str:
    """The one scheduler line that runs a watchdog pass every 30 minutes (a scripted pass every
    10, ADR-0554); printed, never run."""
    named = "" if name == WATCHDOG_NAME else f" --session {name}"
    named += " --pass" if scripted else ""
    minutes = JOB_MINUTES if scripted else WATCHDOG_MINUTES
    folder = str(Path(root).resolve())
    if platform == "win32":
        run = (
            f'cmd /c cd /d \\"{folder}\\" && git fetch -q origin && '
            f"python scripts\\agk\\conductor.py watchdog{named}"
        )
        return f'schtasks /Create /SC MINUTE /MO {minutes} /TN "{WATCHDOG_TASK}" /TR "{run}" /F'
    return (
        f"*/{minutes} * * * * cd {shlex.quote(folder)} && git fetch -q origin && "
        f"python3 scripts/agk/conductor.py watchdog{named}"
    )


def builder_memory(root) -> int | None:
    """`builder_memory_gb` as the plan reads it: the smaller of `[flow]` and `[capacity]`."""
    flow_max = session.flow_int(root, "max_builders", session.MAX_BUILDERS, 1)
    return session_plan.ceilings(root, flow_max)["builder_memory_gb"]


def memory_line(root) -> tuple[str, bool]:
    """(the printed line, whether the memory allows one more session)."""
    per = builder_memory(root)
    free = common.available_memory()
    shown = "unknown" if free is None else f"{free // session_plan.GIB} GB available"
    line = f"watchdog: memory {shown}, builder_memory_gb {per if per else 'unset'}"
    return line, not (per and free is not None and free < per * session_plan.GIB)


def watchdog(root, name: str, scripted: bool = False) -> int:
    """One pass: start the conductor through the adapter when its lease is free or expired; with
    `scripted` (`--pass`), the scripted pass of ADR-0554."""
    if session.paused_default(root):
        print("watchdog: agk paused; nothing started")
        return 0
    branch = launch.default_branch(root)
    here = launch.launch_settings(root)
    main_ = launch.launch_settings(root, f"origin/{branch}")
    if not (here[0] and here[1]) or here != main_:
        print(f"watchdog: nothing started: no adapter to start a conductor {WATCHDOG_SETTINGS}")
        return 1
    issue = plan_issue(root)
    if issue is None:
        print(f"watchdog: nothing started: {LEASE_OFF}")
        return 1
    repo = session.repo_name(root)
    code = (
        watchdog_pass(root, name, repo, here[1])
        if scripted
        else watchdog_once(root, name, repo, here[1], issue)
    )
    builder_pass(root, repo, here[1])  # brief #1355 (ADR-0568): the builders after the conductor
    return code


def watchdog_once(root, name: str, repo: str, adapter: str, issue: int) -> int:
    """Start the conductor through the adapter when its lease is free or expired (ADR-0525)."""
    holder = lease_holder(plan_comments(repo, issue), verdict_authors(root), datetime.now(UTC))
    if holder is not None:
        print(f"watchdog: lease held by {holder[0]} until {stamp_of(holder[1])}; nothing started")
        return 0
    print("watchdog: lease free")
    line, allowed = memory_line(root)
    print(line)
    if not allowed:
        print(
            "watchdog: nothing started: free memory is below one builder "
            "(setting: builder_memory_gb)"
        )
        return 1
    env = {k: v for k, v in os.environ.items() if k not in ("AGK_BRIEF", "AGK_BUILD")}
    env.update(launch.QUIET)
    env.update(AGK_SESSION=name, AGK_ROLE="conductor", AGK_TIER="strongest")
    try:
        done = subprocess.run(  # nosec B603 - the person's own command, split, no shell
            shlex.split(adapter),
            input=WATCHDOG_PROMPT.format(name=name, repo=repo),
            text=True,
            encoding="utf-8",
            env=env,
            capture_output=True,
            cwd=root,
        )
    except OSError:
        print(f"FAIL conductor: the adapter cannot be run for {name}", file=sys.stderr)
        return 1
    if done.returncode != 0:
        print(f"FAIL conductor: the adapter failed for {name}", file=sys.stderr)
        return 1
    print(f"watchdog: started {name}")
    return 0


# --- the scripted pass: a model only when there is work (brief #1310 answer 3, ADR-0554) ---------

JOB_MINUTES = 10
JOB_DAY = timedelta(hours=24)  # one job a day still posts the conductor's report
JOB_STATE = "watchdog.json"  # beside the lease mark, in the git directory: never tracked
AGE = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z|\b\d+(?:s|m|h|d|min| min)\b")
JOB_PROMPT = (
    "You are the AGK conductor {name} for repository {repo}, started by the local watchdog's "
    "scripted pass (`python3 scripts/agk/conductor.py watchdog --pass`) because {why}. Your role "
    "is `.claude/agents/conductor.md` on the default branch: read it, `CLAUDE.md`, "
    "`constitution/principles.md` and `config/session-rules.md` first and follow them exactly. "
    "The watchdog holds the lease under {name} between passes: renew it first with "
    "`python3 scripts/agk/conductor.py lease --take {name}`, again before a step that may pass 10 "
    "minutes, and do not release it: while you renew it the watchdog starts no other job. "
    "Do one pass: `python3 scripts/agk/session.py queue --role conductor`, then "
    "`python3 scripts/agk/session.py review-queue --all` and the pass on its "
    "lines, then the plan's starts and the sweep's lines; schedule no wake, start no loop, and "
    "end when the pass is done.\n"
)


def pass_state_file(root) -> Path | None:
    mark = lease_mark(root)
    return None if mark is None else mark.parent / JOB_STATE


def pass_state(root) -> dict:
    """The fingerprint, sweep digest and time of the last job started (an empty dict when none)."""
    found = pass_state_file(root)
    try:
        data = json.loads(found.read_text(encoding="utf-8")) if found else {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def pass_facts(root) -> tuple[str, bool, str]:
    """(the review queue's fingerprint, whether the plan starts a brief, the digest of the sweep's
    lines without their ages and times), each run as the script it is; CheckError when one fails."""
    code, said = session.quietly(session.review_queue, root, "--fingerprint")
    if code or not said.startswith("fingerprint "):
        raise CheckError("the review queue cannot be read")
    code, planned = session.quietly(session_plan.plan, root, False, False, False)
    if code not in (0, 1):
        raise CheckError("the plan cannot be read")
    starts = any(re.match(r"Start [1-9]\d*:", line) for line in planned.splitlines())
    code, swept = session.quietly(sweep, root)
    if code:
        raise CheckError("the sweep cannot be read")
    lines = sorted(AGE.sub("", line).strip() for line in swept.splitlines() if line.strip())
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return said.split()[1], starts, digest


def keep_state(root, state: dict) -> None:
    found = pass_state_file(root)
    if found is not None:
        found.parent.mkdir(parents=True, exist_ok=True)
        found.write_text(json.dumps(state) + "\n", encoding="utf-8")


# --- the tier of a pass (brief #1359, ADR-0571) ---------------------------------------------

STRONG = ("strongest", "high")
ROUTINE = ("mid", "medium")
SPEC_OR_ADR = ("docs/specs/", "docs/adr/")
QUEUED = re.compile(r"#(\d+) [0-9a-f]{0,40} ?review: ")
BRIEF_ASKED = re.compile(r"#(\d+) question on a brief")
ESCALATION = re.compile(r"escalate: #(\d+) (\S.*)")
JOB_LOG = ".agk-session.log"  # the POSIX adapter's log of a background job, in its worktree
TIER_NOTE = (
    "You run this pass on the `{tier}` tier at `{effort}` effort: name it in the `Read:` line of "
    "each verdict you post as `tier: {tier}`.\n"
)
MID_NOTE = (
    "On the `mid` tier, post no verdict on a pull request that changes a protected path class, "
    "adds or changes a spec or ADR, is a first review of more than {large} changed lines, carries "
    "a `Question:`, a `Correction:` or a disagreement between verdicts, or is an intake, nor on "
    "one whose verdict you are unsure of: end your pass with one line `escalate: #<n> <reason>` "
    "for each, and the watchdog runs one strongest pass for them at once.\n"
)


def pass_classes(root) -> list[str]:
    """The protected path classes of `config/protected-paths.txt` (none when it cannot be read)."""
    try:
        text = (Path(root) / "config" / "protected-paths.txt").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [x.strip() for x in text.splitlines() if x.strip() and not x.startswith("#")]


def queued_items(root, repo: str) -> list[dict]:
    """The queue a job is handed: each pull request `review-queue --all` lists for review, with its
    title, author, changed paths, changed lines and comments, and each question on a brief;
    CheckError when one cannot be read."""
    code, listed = session.quietly(session.review_queue, root, "--all")
    if code:
        raise CheckError("the review queue cannot be read")
    found: list[dict] = []
    for line in (x.strip() for x in listed.splitlines()):
        if asked := BRIEF_ASKED.fullmatch(line):
            found.append({"number": int(asked.group(1)), "brief_question": True})
            continue
        if not (queued := QUEUED.match(line)):
            continue
        n = int(queued.group(1))
        pr = session.gh(f"repos/{repo}/pulls/{n}")
        files = session.pages(f"repos/{repo}/pulls/{n}/files")
        said = session.pages(f"repos/{repo}/issues/{n}/comments")
        if not isinstance(pr, dict) or files is None or said is None:
            raise CheckError(f"#{n} cannot be read")
        changed = [pr.get(k) for k in ("additions", "deletions")]
        found.append(
            {
                "number": n,
                "title": str(pr.get("title") or ""),
                "author": str((pr.get("user") or {}).get("login") or ""),
                "paths": [str(f.get("filename") or "") for f in files if isinstance(f, dict)],
                "changed": sum(x for x in changed if isinstance(x, int)),
                "comments": said,
            }
        )
    return found


def strongest_reasons(one: dict, classes: list[str], authors: list[str], large: int) -> list[str]:
    """Why one queued item needs the strongest tier (brief #1359 answer 1); [] for a routine one."""
    n = one["number"]
    if one.get("brief_question"):
        return [f"#{n} question on a brief"]
    paths, out = one.get("paths") or [], []
    if any(p == c or (c.endswith("/") and p.startswith(c)) for p in paths for c in classes):
        out.append(f"#{n} changes a protected path class")
    if any(p.startswith(SPEC_OR_ADR) for p in paths):
        out.append(f"#{n} adds or changes a spec or ADR")
    counted = session.counted_authors(authors, one.get("author")) or []
    allowed = {a.lstrip("@").lower() for a in counted}
    said = sorted(
        one.get("comments") or [], key=lambda c: (str(c.get("created_at") or ""), c.get("id") or 0)
    )
    marks = [
        (c, m)
        for c in said
        if session.author_of(c) in allowed
        and (m := session.HEAD_VERDICT.fullmatch(session.first_line(c)))
    ]
    if not marks and one.get("changed", 0) > large:
        out.append(f"#{n} first review of {one['changed']} changed lines")
    after = said[said.index(marks[-1][0]) + 1 :] if marks else said
    for kind in ("Question:", "Correction:"):
        if any(session.first_line(c).startswith(kind) for c in after):
            out.append(f"#{n} carries a {kind}")
    kinds: dict[str, set[str]] = {}
    for _, m in marks:
        if m.group(2):
            kinds.setdefault(m.group(2)[:7], set()).add(m.group(1))
    if any(len(v) > 1 for v in kinds.values()):
        out.append(f"#{n} disagreement between verdicts")
    if str(one.get("title") or "").startswith("Intake:"):
        out.append(f"#{n} is an intake")
    return out


def tier_for_pass(root, repo: str) -> tuple[str, str, list[str]]:
    """(tier, effort, why) of the next job: the pin, else `strongest` at `high` when any queued
    item needs it or the queue cannot be read, else `mid` at `medium` (brief #1359 answers 1-3)."""
    try:
        if config.conductor_pin(root):
            return (*STRONG, ["pinned by [models] conductor"])
        large = config.review_large_lines(root)
    except CheckError as exc:
        return (*STRONG, [str(exc)])
    try:
        items = queued_items(root, repo)
    except CheckError:
        return (*STRONG, ["the queue cannot be read"])
    classes, authors = pass_classes(root), verdict_authors(root)
    why = [r for one in items for r in strongest_reasons(one, classes, authors, large)]
    return (*(STRONG if why else ROUTINE), why)


def escalations(text: str) -> list[tuple[str, str]]:
    """The `escalate: #<n> <reason>` lines a mid job ended with, in order."""
    found = (ESCALATION.fullmatch(x.strip()) for x in (text or "").splitlines())
    return [(m.group(1), m.group(2).strip()) for m in found if m]


def logged_escalations(root, name: str, state: dict) -> list[tuple[str, str]]:
    """The escalations in the log of the last job when it ran on `mid` and the log is newer than
    its start (a background job of the POSIX adapter; verify: the Windows adapter keeps no log)."""
    start = when(str(state.get("job_at") or ""))
    found = launch.worktree_of(Path(root), name) / JOB_LOG
    if state.get("tier") != "mid" or start is None:
        return []
    try:
        if found.stat().st_mtime < start.timestamp():
            return []
        return escalations(found.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return []


def start_job(root, adapter: str, name: str, repo: str, why: str, tier: tuple) -> str | None:
    """Call the adapter once for one conductor job on TIER (tier, effort, large); its standard
    output, or None when it cannot be run or fails."""
    env = {k: v for k, v in os.environ.items() if k not in ("AGK_BRIEF", "AGK_BUILD")}
    env.update(launch.QUIET)
    env.update(AGK_SESSION=name, AGK_ROLE="conductor", AGK_TIER=tier[0], AGK_EFFORT=tier[1])
    prompt = JOB_PROMPT.format(name=name, repo=repo, why=why)
    prompt += TIER_NOTE.format(tier=tier[0], effort=tier[1])
    prompt += MID_NOTE.format(large=tier[2]) if tier[0] == "mid" else ""
    try:
        done = subprocess.run(  # nosec B603 - the person's own command, split, no shell
            shlex.split(adapter),
            input=prompt,
            text=True,
            encoding="utf-8",
            env=env,
            capture_output=True,
            cwd=root,
        )
    except OSError:
        print(f"FAIL conductor: the adapter cannot be run for {name}", file=sys.stderr)
        return None
    if done.returncode != 0:
        print(f"FAIL conductor: the adapter failed for {name}", file=sys.stderr)
        return None
    return done.stdout or ""


def escalate(root, adapter: str, name: str, repo: str, found: list) -> bool:
    """One strongest job for the escalations of a mid pass (brief #1359 answer 2)."""
    for n, reason in found:
        print(f"watchdog: escalated #{n} to strongest: {reason}")
    named = "; ".join(f"#{n} ({reason})" for n, reason in found)
    why = f"a mid pass escalated {named}: review these first"
    return start_job(root, adapter, name, repo, why, (*STRONG, 0)) is not None


def job_running(root, repo: str, name: str, state: dict, now: datetime) -> bool:
    """Whether the last job may still run (fix list 6889113783 item 2): within its first lease
    window, or while the lease under its name was renewed since the script's own last take (the job
    renews it as it works and never releases it; it lapses `LEASE_MINUTES` after the job ends)."""
    start = when(str(state.get("job_at") or ""))
    if start is None:
        return False
    if now < start + timedelta(minutes=LEASE_MINUTES):
        return True
    issue = plan_issue(root)
    holder = (
        None
        if issue is None
        else lease_holder(plan_comments(repo, issue), verdict_authors(root), now)
    )
    return (
        holder is not None and holder[0] == name and stamp_of(holder[1]) != state.get("own_until")
    )


def watchdog_pass(root, name: str, repo: str, adapter: str) -> int:
    """Hold the lease, run the scripts of the pass, start one conductor job only when needed and
    never a second one while the last may still run."""
    state, now = pass_state(root), datetime.now(UTC)
    if job_running(root, repo, name, state, now):
        print(f"watchdog: job {name} still running; nothing started")
        return 0
    code, said = session.quietly(lease, root, "--take", name, False)
    if code:
        print(f"watchdog: {said}; nothing started")
        return 0 if code == merge_cleared.EXIT_HELD else 1
    issue = plan_issue(root)
    holder = (
        None
        if issue is None
        else lease_holder(plan_comments(repo, issue), verdict_authors(root), now)
    )
    state["own_until"] = stamp_of(holder[1]) if holder else None  # the script's own take
    keep_state(root, state)
    try:
        fingerprint, starts, swept = pass_facts(root)
    except CheckError as exc:
        print(f"watchdog: nothing started: {exc}")
        return 1
    last = when(str(state.get("job_at") or ""))
    logged = logged_escalations(root, name, state) if not state.get("log_read") else []
    why = [
        text
        for text, yes in (
            ("the queue changed", fingerprint != state.get("fingerprint")),
            ("the plan starts a brief", starts),
            ("a sweep line changed", swept != state.get("sweep")),
            ("no job ran for 24 hours", last is None or now - last >= JOB_DAY),
        )
        if yes
    ]
    if not why and not logged:
        if state.get("tier") == "mid" and not state.get("log_read"):
            state["log_read"] = True  # the last job ended without an escalation
            keep_state(root, state)
        print("watchdog: nothing changed; no job started")
        return 0
    line, allowed = memory_line(root)
    print(line)
    if not allowed:
        print(
            "watchdog: nothing started: free memory is below one builder "
            "(setting: builder_memory_gb)"
        )
        return 1
    seen = {"fingerprint": fingerprint, "sweep": swept, "job_at": stamp_of(now), "log_read": True}
    if logged:  # brief #1359 answer 2: the escalations of the last mid job, before anything else
        if not escalate(root, adapter, name, repo, logged):
            return 1
        state.update(seen, tier=STRONG[0])
        keep_state(root, state)
        print(f"watchdog: job started {name} on strongest at high: escalated by a mid pass")
        return 0
    tier, effort, needs = tier_for_pass(root, repo)
    print(f"watchdog: tier {tier}: {'; '.join(needs)}" if needs else f"watchdog: tier {tier}")
    large = config.review_large_lines(root) if tier == "mid" else 0
    said = start_job(root, adapter, name, repo, ", ".join(why), (tier, effort, large))
    if said is None:  # the state stays, so the next pass tries again
        return 1
    print(f"watchdog: job started {name} on {tier} at {effort}: {', '.join(why)}")
    found = escalations(said) if tier == "mid" else []
    if found and not escalate(root, adapter, name, repo, found):
        return 1
    state.update(seen, tier=STRONG[0] if found else tier, log_read=tier != "mid" or bool(found))
    keep_state(root, state)
    return 0


# --- the watchdog keeps builders alive (brief #1355, ADR-0568) ------------------------------

BUILDER_STATE = "builders.json"  # beside the lease mark, in the git directory: never tracked
RESTART_GAP = timedelta(hours=1)
OWED = ("Verdict:", "Correction:", "Answer:", "Maintainer answer:")
FINAL = re.compile(r"Report: \S+ (handing over:|over cap )")
NO_ROOM = "no room: max_builders or builder_memory_gb"
IDLE = ("idle_minutes", 60)
QUIET = timedelta(minutes=5)  # a fresh lock heartbeat, and the least gap of the two reads
READ_LATE = timedelta(minutes=30)  # an earlier read older than this starts the two reads again
WORKING = "working"


def idle_minutes(root) -> int:
    """`[flow] idle_minutes` (60 by default), never below `silent_minutes` (ADR-0568 decision 2)."""
    silent = session.flow_int(root, SILENT[0], SILENT[1], 0)
    return max(session.flow_int(root, IDLE[0], IDLE[1], 0), silent)


def builder_state(alive, exited, own, owed, now, quiet: int, has_pr: bool, busy=()) -> str:
    """`ended`, `idle` or `live` (ADR-0568 decisions 1 and 2). OWN is the builder's newest move
    (its record, take, posts or push), OWED the newest line it owes an answer to, or None; BUSY
    the signs of work its machine shows (`busy_signs`): any one of them is `live`."""
    if not alive or exited:
        return "ended"
    if busy:
        return "live"
    wait = timedelta(minutes=quiet)
    if not has_pr:
        return "idle" if now - own >= wait else "live"
    return "idle" if owed is not None and owed > own and now - owed >= wait else "live"


def builder_action(
    state: str, *, final, parked, recent, room, safe, checked=True
) -> tuple[str, str | None]:
    """(`restart`, `left` or `held`, the reason) for one session (ADR-0568 decisions 2 and 3);
    CHECKED is whether two reads 5 minutes apart found the same quiet process tree."""
    if state == "live":
        return "left", None
    if parked or final:
        return "left", "parked" if parked else "final report"
    if recent:
        return "held", "restarted within the hour"
    if state == "idle" and not safe:
        return "held", "unpushed work"
    if state == "idle" and not checked:
        return "held", WORKING
    if not room:
        return "held", NO_ROOM
    return "restart", None


def worktree_safe(worktree: Path) -> bool:
    """Nothing to lose: the worktree is clean and every commit of its head is on a remote."""

    def git_out(*args: str) -> str | None:
        try:
            done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
                ["git", "-C", str(worktree), *args],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )  # fmt: skip
        except OSError:
            return None
        return done.stdout if done.returncode == 0 else None

    if not Path(worktree).is_dir():
        return False
    changes = git_out("status", "--porcelain", "--untracked-files=all")
    unpushed = git_out("rev-list", "HEAD", "--not", "--remotes")
    return changes == "" and unpushed == ""


def transcript_folder(worktree: Path) -> Path:
    """The runtime's transcript folder of a session started in WORKTREE: `projects/<the folder's
    path, every character other than a letter or digit a dash>` under `CLAUDE_CONFIG_DIR`, else
    `~/.claude` (verify: the runtime's layout on POSIX and on Windows)."""
    base = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    return Path(base) / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(Path(worktree).resolve()))


def newest_write(folder: Path, skip: AbstractSet[str] = frozenset()) -> float | None:
    """The newest modification time of a file below FOLDER, never inside `.git`; None for none."""
    newest_ = None
    for top, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            if name in skip:
                continue
            with contextlib.suppress(OSError):
                moment = (Path(top) / name).stat().st_mtime
                newest_ = moment if newest_ is None else max(newest_, moment)
    return newest_


def lock_base(root) -> Path:
    """The folder of the heavy-step locks (`lock_dir` of agk.toml, else the temp folder)."""
    import lock

    return lock.lock_folder(Path(root), "x").parent


def holds_fresh_lock(root, name: str, tree: AbstractSet[int], now) -> bool:
    """A `lock.py` lock of session NAME, or of a process of its tree, with a heartbeat younger
    than 5 minutes; a lock folder that cannot be read counts as held (ADR-0568 decision 2)."""
    import lock

    try:
        folders = sorted(lock_base(root).glob("agk-lock-*"))
    except (OSError, lock.Usage):
        return True
    for held in folders:
        owner = lock.read_owner(held) if held.is_dir() else None
        if owner is None:
            continue
        ours = owner.get("session") == name or bool(set(lock.holder_pids(owner)) & set(tree))
        beat = lock.beat_minutes(owner, now)
        if ours and beat is not None and beat < QUIET.total_seconds() / 60:
            return True
    return False


def busy_signs(root, worktree: Path, record: dict, table, now, quiet: int) -> list[str]:
    """The signs of work that one read shows within QUIET minutes (ADR-0568 decision 2): a
    transcript write, a local commit, a file change in the worktree (the adapter's record and
    exit file are not one), and a lock with a fresh heartbeat. The process tree's CPU use is
    the two reads' part (`watch_builders`)."""
    since = (now - timedelta(minutes=quiet)).timestamp()
    found = []
    written = newest_write(transcript_folder(worktree))
    if written is not None and written >= since:
        found.append("transcript")
    with contextlib.suppress(OSError):
        done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "-C", str(worktree), "log", "-1", "--format=%ct"],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )  # fmt: skip
        stamp = done.stdout.strip()
        if done.returncode == 0 and stamp.isdigit() and int(stamp) >= since:
            found.append("commit")
    changed = newest_write(Path(worktree), {launch.RECORD_FILE, launch.EXIT_FILE})
    if changed is not None and changed >= since:
        found.append("files")
    tree = launch.tree_cpu(record["pid"], table or {})
    if holds_fresh_lock(root, record["session"], set(tree), now):
        found.append("lock")
    return found


def two_reads(checks: dict, name: str, cpu: dict | None, now) -> bool:
    """Whether an earlier read, 5 to 30 minutes ago, found the same CPU seconds for the same
    processes of the tree; keeps this read for the next pass when it did not."""
    found = checks.get(name)
    before: dict = found if isinstance(found, dict) else {}
    then = when(str(before.get("at") or ""))
    same = (
        cpu is not None
        and then is not None
        and QUIET <= now - then <= READ_LATE
        and before.get("cpu") == cpu
    )
    if not same:
        checks[name] = {"at": stamp_of(now), "cpu": cpu}
    return same


def builder_file(root) -> Path | None:
    mark = lease_mark(root)
    return None if mark is None else mark.parent / BUILDER_STATE


def builder_memo(root) -> dict:
    found = builder_file(root)
    try:
        data = json.loads(found.read_text(encoding="utf-8")) if found else {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def keep_builder_memo(root, memo: dict) -> None:
    found = builder_file(root)
    if found is not None:
        found.parent.mkdir(parents=True, exist_ok=True)
        found.write_text(json.dumps(memo, sort_keys=True) + "\n", encoding="utf-8")


def held_builder_lines(root) -> list[str]:
    """The NEEDS-YOU line of each builder the watchdog held on this machine (ADR-0568); none when
    the root is not a git checkout (the sweep's tests run on a fake root)."""
    try:
        held = builder_memo(root).get("held") or {}
    except OSError:
        return []
    return [
        f"NEEDS-YOU: builder {name} #{item.get('brief')} held ({item.get('reason')})"
        for name, item in sorted(held.items())
        if isinstance(item, dict)
    ]


def local_records(root) -> list[tuple[Path, dict]]:
    """(worktree, record) of each session worktree beside the checkout that has a record."""
    parent = Path(root).resolve().parent
    found = []
    for worktree in sorted(parent.glob("agk-*")):
        record = launch.read_record(worktree)
        if record is not None and worktree.name == f"agk-{record['session']}":
            found.append((worktree, record))
    return found


def newest(comments: list, prefixes: tuple[str, ...]) -> datetime | None:
    times = [
        session.moment(c.get("created_at"))
        for c in comments
        if session.first_line(c).startswith(prefixes)
    ]
    return max(times, default=None)


def builder_facts(root, repo: str, record: dict, pulls: list, now) -> dict | None:
    """What GitHub says of one recorded session: None when it holds no live take of its brief."""
    number, name = record["brief"], record["session"]
    if number is None:
        return None
    comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
    hours = session.flow_int(root, "claim_hours", session.CLAIM_HOURS, 5)
    takes = [t for t in session.live_takes(comments, number, pulls, hours) if t[2] == name]
    if not takes:
        return None
    started = session.moment(record["started_utc"])
    own = max([started, *(t[0] for t in takes)])
    pull = next((p for p in pulls if named(p, number)), None)
    facts = {"pr": None, "own": own, "owed": None, "final": False, "parked": False}
    if pull is None:
        return {**facts, "own": max([own, newest(comments, ALIVE) or own])}
    said = read(f"repos/{repo}/issues/{pull['number']}/comments", "the pull request's comments")
    sha = str((pull.get("head") or {}).get("sha") or "")
    commit = session.gh(f"repos/{repo}/commits/{sha}") if sha else None
    pushed = ((commit or {}).get("commit") or {}).get("committer") or {}
    moves = [own, newest(said, ALIVE)]
    if pushed.get("date"):
        moves.append(session.moment(pushed["date"]))
    reports = [c for c in session.in_order(said) if session.first_line(c).startswith("Report:")]
    return {
        "pr": pull["number"],
        "own": max(x for x in moves if x is not None),
        "owed": newest(said, OWED),
        "final": bool(reports) and bool(FINAL.match(session.first_line(reports[-1]))),
        "parked": session.PARKED_LABEL in session.labels_of(pull)
        or session.own_park(said) is not None,
        "author": session.author_of(pull) if isinstance(pull.get("user"), dict) else None,
    }


def stopped(pid: int) -> bool:
    launch.stop_tree(pid)
    for _ in range(50):
        if not launch.process_alive(pid):
            return True
        time.sleep(0.2)
    return False


def watch_builders(root, repo: str, adapter: str, now=None) -> list[str]:
    """One line per recorded builder session, restarting an ended or idle one (ADR-0568)."""
    now = now or datetime.now(UTC)
    records = local_records(root)
    if not records:
        return []
    pulls = read(f"repos/{repo}/pulls?state=open", "the open pull requests")
    quiet = idle_minutes(root)
    limit = launch.max_builders(Path(root))
    memo = builder_memo(root)
    restarts, held = memo.setdefault("restarts", {}), memo.setdefault("held", {})
    checks = memo.setdefault("checks", {})
    table = launch.process_table()
    running = sum(
        1 for w, r in records if not launch.exited(w, r) and launch.process_alive(r["pid"])
    )
    lines = []
    for worktree, record in records:
        name, number = record["session"], record["brief"]
        facts = builder_facts(root, repo, record, pulls, now)
        if facts is None:
            continue
        alive = launch.process_alive(record["pid"])
        args = (alive, launch.exited(worktree, record), facts["own"], facts["owed"], now, quiet)
        state = builder_state(*args, facts["pr"] is not None)
        if state == "idle":
            busy = busy_signs(root, worktree, record, table, now, quiet)
            state = builder_state(*args, facts["pr"] is not None, busy)
        checked = False
        if state == "idle":
            cpu = None if table is None else launch.tree_cpu(record["pid"], table)
            shown = None if cpu is None else {str(p): c for p, c in sorted(cpu.items())}
            checked = two_reads(checks, name, shown, now)
        else:
            checks.pop(name, None)
        last = when(str(restarts.get(name) or ""))
        room = (running - (state == "idle") < limit) and memory_line(root)[1]
        action, why = builder_action(
            state,
            final=facts["final"],
            parked=facts["parked"],
            recent=last is not None and now - last < RESTART_GAP,
            room=room,
            safe=state != "idle" or worktree_safe(worktree),
            checked=checked,
        )
        if action == "restart" and state == "idle" and not stopped(record["pid"]):
            action, why = "held", "the process did not stop"
        if action == "restart":
            prompt = launch.resume_for(name, number, None, facts["pr"], facts.get("author"))
            code, _ = session.quietly(
                launch.start_with, adapter, [(name, number, None)], [prompt], None, Path(root)
            )
            action, why = ("restarted", None) if code == 0 else ("held", "the adapter failed")
            if code == 0:
                restarts[name] = stamp_of(now)
                running += state == "ended"
        if action == "restarted":
            checks.pop(name, None)
        if action == "held" and why != WORKING:  # a working builder needs no one
            held[name] = {"brief": number, "reason": why}
        else:
            held.pop(name, None)
        lines.append(
            f"watchdog: builder {name} #{number} {state} -> {action}" + (f" ({why})" if why else "")
        )
    keep_builder_memo(root, memo)
    return lines


def builder_pass(root, repo: str, adapter: str) -> None:
    """Print the builder lines after the conductor's checks; a read that fails is one line."""
    try:
        lines = watch_builders(root, repo, adapter)
    except CheckError as exc:
        lines = [f"watchdog: builders not read: {exc}"]
    if lines:
        print("\n".join(lines))


# --- the reviewer at the gate (brief #1248, ADR-0528) ---------------------------------------

REVIEW_AGENT = "architect-review"
FULL_HEAD = re.compile(r"[0-9a-f]{40}")
FALLBACK_END = " (conductor fallback)"
SLOTS_SETTING = "(setting: reviewer_slots in the flow table of agk.toml)"
WAIT_SETTING = "(setting: review_minutes in the flow table of agk.toml)"
REVIEW_START_SETTINGS = (
    "(settings: auto_start and launch_adapter in the flow table of agk.toml, for a reviewer start)"
)
MARKER = re.compile(r"(agent|tier|session): (\S+)")
GATE_MARKERS = (
    "with reviewer slots counted, a gating verdict carries the slot's marker lines (agent:, tier:, "
    f"session:) or ends (conductor fallback) {SLOTS_SETTING}"
)
GATE_UNASKED = f"no reviewer slot was asked for this head, so no fallback yet {SLOTS_SETTING}"
GATE_WAIT = (
    f"a reviewer slot has this head; the conductor gives no verdict meanwhile {WAIT_SETTING}"
)
GATE_ANSWERED = f"a reviewer slot gave this head's verdict; no fallback {SLOTS_SETTING}"
REVIEW_PROMPT = (
    "You are reviewer slot {slot} of repository {repo}, started by `python3 "
    "scripts/agk/conductor.py review --start` for one head: pull request #{pr} at {sha}. "
    "You are the `architect-review` agent (`.claude/agents/architect-review.md`); read it, "
    "`CLAUDE.md` and `constitution/principles.md` first and follow them. You never saw the "
    "build. Run `git fetch origin` and `git checkout --detach {sha}`, save the bundle with "
    "`python3 scripts/agk/review_bundle.py --pr {pr} --sha {sha} > <scratch>/bundle.md`, "
    "where <scratch> is the folder `agk-review-{slot}` in the system temp folder, and read "
    "only that file. Write the verdict to `<scratch>/v.md` with the marker lines "
    "`agent: architect-review`, `tier: strongest` and `session: {slot}`, check it with "
    "`python3 scripts/agk/conductor.py check-verdict <scratch>/v.md --pr {pr}`, post it on "
    "pull request #{pr}, then run `python3 scripts/agk/session.py slot --release {slot}` and "
    "end. Review nothing else.\n"
)


def review_args(args: list[str]) -> tuple[int, bool] | None:
    """(number, `--start` given) for `review --pr N [--start]`; None otherwise."""
    if args[:2] == ["review", "--pr"] and len(args) in (3, 4) and PR_NUMBER.fullmatch(args[2]):
        if args[3:] in ([], ["--start"]):
            return int(args[2]), args[3:] == ["--start"]
    return None


def listed(root) -> set[str]:
    return {
        a.lstrip("@").lower() for a in session.counted_authors(verdict_authors(root), None) or []
    }


def review_asks(repo: str, allowed: set[str]) -> list[tuple[datetime, str, int, str]]:
    """(time, slot, pull request, head) of each `Review:` line by a listed author on the one open
    `agk-conductor` issue, oldest first."""
    issue = session.conductor_issue(repo)
    found = []
    for c in read(f"repos/{repo}/issues/{issue}/comments", "the conductor issue"):
        match = session.REVIEW.fullmatch(session.first_line(c))
        if match and session.author_of(c) in allowed:
            when_ = session.moment(c.get("created_at"))
            found.append((when_, match.group(1), int(match.group(2)), match.group(3)))
    return sorted(found)


def verdicts_on(comments: list, head: str, allowed: set[str]) -> list[str]:
    """The bodies of the verdicts by a listed author that name HEAD."""
    return [
        str(c.get("body") or "")
        for c in comments
        if session.author_of(c) in allowed
        and (v := session.VERDICT.fullmatch(session.first_line(c)))
        and head.startswith(v.group(2))
    ]


def marked(body: str, count: int) -> bool:
    """Whether BODY carries the reviewer slot's marker lines once each: `agent: architect-review`,
    `tier: strongest` and `session: r<k>` with k from 1 to COUNT (ADR-0528 decision 2)."""
    lines = [m for m in map(MARKER.fullmatch, (x.strip() for x in body.splitlines())) if m]
    found: dict[str, list[str]] = {}
    for m in lines:
        found.setdefault(m.group(1), []).append(m.group(2))
    slot = found.get("session", [""])
    return (
        found.get("agent") == [REVIEW_AGENT]
        and found.get("tier") == ["strongest"]
        and len(slot) == 1
        and bool(session.REVIEWER_NAME.fullmatch(slot[0]))
        and int(slot[0][1:]) <= count
    )


def gate_problem(root, repo: str, number: int, head: str, body: str) -> str | None:
    """The reviewer's gate of ADR-0528 decision 2, or None: off while `reviewer_slots` is 0 (or no
    checkout is found, which has no agk.toml to set it)."""
    if root is None:
        try:
            root = repo_root()
        except CheckError:
            return None
    count = session.reviewer_slots(root)
    if not count:
        return None
    first = body.strip().splitlines()[0].strip()
    if not first.endswith(FALLBACK_END):
        return None if marked(body, count) else GATE_MARKERS
    allowed = listed(root)
    said = read(f"repos/{repo}/issues/{number}/comments", "the comments of the pull request")
    if any(marked(b, count) for b in verdicts_on(said, head, allowed)):
        return GATE_ANSWERED
    asks = [a for a in review_asks(repo, allowed) if a[2] == number and a[3] == head]
    if not asks:
        return GATE_UNASKED
    if datetime.now(UTC) - asks[-1][0] < timedelta(minutes=session.review_minutes(root)):
        return GATE_WAIT
    return None


def free_slot(repo: str, asks: list, count: int, minutes: int, allowed: set[str]) -> str | None:
    """The first of `r1` to `r<count>` whose newest `Review:` line is past MINUTES or names a head
    that has its verdict; None when every slot has a head."""
    now = datetime.now(UTC)
    newest = {slot: (n, sha, t) for t, slot, n, sha in asks}
    for k in range(1, count + 1):
        held = newest.get(f"r{k}")
        if held is None or now - held[2] >= timedelta(minutes=minutes):
            return f"r{k}"
        said = read(f"repos/{repo}/issues/{held[0]}/comments", "the comments of a pull request")
        if verdicts_on(said, held[1], allowed):
            return f"r{k}"
    return None


def start_reviewer(root, repo: str, slot: str, number: int, head: str) -> int:
    """Call the adapter once for one reviewer session, as `launch.py` does (no shell)."""
    env = {k: v for k, v in os.environ.items() if k not in ("AGK_BRIEF", "AGK_BUILD")}
    env.update(launch.QUIET)
    env.update(
        AGK_SESSION=slot,
        AGK_ROLE="reviewer",
        AGK_AGENT=REVIEW_AGENT,
        AGK_TIER="strongest",
        AGK_PR=str(number),
        AGK_SHA=head,
    )
    adapter = launch.launch_settings(root)[1] or ""
    try:
        done = subprocess.run(  # nosec B603 - the person's own command, split, no shell
            shlex.split(adapter),
            input=REVIEW_PROMPT.format(slot=slot, repo=repo, pr=number, sha=head),
            text=True,
            encoding="utf-8",
            env=env,
            capture_output=True,
            cwd=root,
        )
    except OSError:
        print(f"FAIL conductor: the adapter cannot be run for {slot}", file=sys.stderr)
        return 1
    if done.returncode != 0:
        print(f"FAIL conductor: the adapter failed for {slot}", file=sys.stderr)
        return 1
    print(f"review: started {slot} for #{number} {head[:12]}")
    return 0


def review(root, number: int, start: bool) -> int:
    """`review --pr N [--start]` (ADR-0528 decision 3): one line on who gives the head's verdict;
    with `--start` in local mode, the `Review:` line and one reviewer session by the adapter."""
    count = session.reviewer_slots(root)
    if not count:
        print(f"review: off {SLOTS_SETTING}; the conductor gives the verdict as before")
        return 0
    minutes = session.review_minutes(root)
    repo = session.repo_name(root)
    pull = read_one(f"repos/{repo}/pulls/{number}", "the pull request")
    head = str((pull.get("head") or {}).get("sha") or "")
    if not FULL_HEAD.fullmatch(head):
        raise CheckError("the pull request cannot be read")
    allowed = listed(root)
    said = read(f"repos/{repo}/issues/{number}/comments", "the comments of the pull request")
    lead = f"review: #{number} {head[:12]}"
    if verdicts_on(said, head, allowed):
        print(f"{lead} has its verdict")
        return 0
    asks = review_asks(repo, allowed)
    mine = [a for a in asks if a[2] == number and a[3] == head]
    if mine:
        since = mine[-1][0]
        until = since + timedelta(minutes=minutes)
        if datetime.now(UTC) < until:
            print(
                f"{lead} with {mine[-1][1]} since {stamp_of(since)}; the conductor gives no "
                f"verdict until {stamp_of(until)}"
            )
        else:
            print(
                f"{lead} fallback: no reviewer verdict within review_minutes; the conductor may "
                f"post its verdict ending (conductor fallback) {WAIT_SETTING}"
            )
        return 0
    slot = free_slot(repo, asks, count, minutes, allowed)
    if slot is None:
        print(f"{lead} waits: no reviewer slot is free {SLOTS_SETTING}")
        return 0
    line = f"Review: {slot} #{number} {head}"
    if not start:
        print(f"review: ask {line}")
        return 0
    if session.paused_default(root):
        print("review: agk paused; nothing started")
        return 0
    branch = launch.default_branch(root)
    here = launch.launch_settings(root)
    if not (here[0] and here[1]) or here != launch.launch_settings(root, f"origin/{branch}"):
        print(f"review: nothing started: no adapter to start a reviewer {REVIEW_START_SETTINGS}")
        return 1
    if not launch.memory_allows(root):
        return 1
    issue = session.conductor_issue(repo)
    post(
        f"repos/{repo}/issues/{issue}/comments",
        "the Review: line was refused",
        "-f",
        f"body={line}",
    )
    return start_reviewer(root, repo, slot, number, head)


def routine_args(args: list[str]) -> tuple | None:
    """(`rerun`, number, apply), (`check-verdict`, path) or (`lease`, mode, name) for the forms
    of brief #700; None for any other form."""
    if args[:2] == ["rerun", "--pr"] and len(args) in (3, 4) and PR_NUMBER.fullmatch(args[2]):
        if args[3:] in ([], ["--apply"]):
            return ("rerun", int(args[2]), args[3:] == ["--apply"])
    if args[:1] == ["check-verdict"] and len(args) in (2, 4) and args[1] and args[1][0] != "-":
        if len(args) == 2:
            return ("check-verdict", args[1], None)
        if args[2] == "--pr" and PR_NUMBER.fullmatch(args[3]):
            return ("check-verdict", args[1], int(args[3]))
    if args[:1] == ["lease"]:
        if args[1:] == ["--show"]:
            return ("lease", "--show", None)
        if len(args) == 3 and args[1] in ("--take", "--release") and NAME.fullmatch(args[2]):
            return ("lease", args[1], args[2])
    if args[:2] == ["over", "--pr"] and len(args) == 3 and PR_NUMBER.fullmatch(args[2]):
        return ("over", int(args[2]))
    if args[:2] == ["reprove", "--pr"] and len(args) in (3, 4) and PR_NUMBER.fullmatch(args[2]):
        if args[3:] in ([], ["--apply"]):
            return ("reprove", int(args[2]), args[3:] == ["--apply"])
    return None


def queue_args(args: list[str]) -> tuple[bool, int] | None:
    """(`--dry-run` given, the batch size) for `merge-queue [--dry-run] [--max-batch N]`; None
    for any other form."""
    rest = args[1:]
    dry = rest[:1] == ["--dry-run"]
    rest = rest[1:] if dry else rest
    if not rest:
        return dry, BATCH
    if len(rest) == 2 and rest[0] == "--max-batch" and BATCH_SIZE.fullmatch(rest[1]):
        return dry, int(rest[1])
    return None


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    utf8_output()
    args = sys.argv[1:] if argv is None else argv
    since = datetime.now(UTC)
    if args[:1] == ["watch"] and len(args) >= 3 and args[1] == "--since":
        parsed = when(args[2])
        if parsed is None:
            print(f"{USAGE}\n--since takes a time such as 2026-11-06T10:00:00Z", file=sys.stderr)
            return 2
        since, args = parsed, ["watch", *args[3:]]
    queue = queue_args(args) if args[:1] == ["merge-queue"] else None
    routine = routine_args(args)
    plain = args in (["sweep"], ["watch"], ["watch", "--once"])
    guard = watchdog_args(args) if args[:1] == ["watchdog"] else None
    gate = review_args(args)
    if guard is not None and guard[1]:
        print(install_line(root or repo_root(), guard[0], sys.platform, guard[2]))
        return 0
    if queue is None and routine is None and guard is None and gate is None and not plain:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        root = repo_root() if root is None else root
        if queue is not None:
            return merge_queue(root, *queue)
        if routine is not None:
            if routine[0] == "rerun":
                return rerun(root, routine[1], routine[2])
            if routine[0] == "check-verdict":
                return check_verdict(routine[1], root, routine[2])
            if routine[0] == "over":
                return over(root, routine[1])
            if routine[0] == "reprove":
                return reprove(root, routine[1], routine[2])
            return lease(root, routine[1], routine[2])
        if guard is not None:
            return watchdog(root, guard[0], guard[2])
        if gate is not None:
            return review(root, *gate)
        if args == ["sweep"]:
            return sweep(root)
        return watch(root, since, args[1:] == ["--once"])
    except merge_cleared.Held as exc:
        print(f"{args[0]}: held: {exc}")
        return merge_cleared.EXIT_HELD
    except merge_cleared.Unreadable as exc:
        print(f"FAIL conductor: GitHub cannot be read ({exc})", file=sys.stderr)
        return merge_cleared.EXIT_UNREADABLE
    except CheckError as exc:
        print(f"FAIL conductor: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
