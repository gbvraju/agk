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
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import re
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
import merge_cleared
import session
import session_plan
from common import (
    FINAL_LINE,
    NOT_FIX_LIST,
    CheckError,
    fix_items,
    repo_root,
    verdict_problem,
)
from full_run import contained_in, covered
from reviewers import approval_shas, authors_of, spec_approvers, verdict_authors

USAGE = (
    "usage: conductor.py watch [--since ISO] [--once] | conductor.py sweep | "
    "conductor.py merge-queue [--dry-run] [--max-batch N] | "
    "conductor.py rerun --pr N [--apply] | conductor.py check-verdict FILE [--pr N] | "
    "conductor.py lease (--show | --take NAME | --release NAME) | conductor.py over --pr N | "
    "conductor.py reprove --pr N [--apply]"
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


def new_lines(repo: str, since: datetime, approvers: AbstractSet[str] = frozenset()) -> list[str]:
    briefs = session.labelled(
        read(f"repos/{repo}/issues?state=open&labels={session.LABEL}", "the open briefs"),
        session.LABEL,
    )
    pulls = read(f"repos/{repo}/pulls?state=open", "the open pull requests")
    numbers = sorted({i["number"] for i in briefs} | {p["number"] for p in pulls}, reverse=True)
    lines = []
    for number in numbers:
        comments = read(f"repos/{repo}/issues/{number}/comments", f"the comments of #{number}")
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
            lines = lines or start_lines(root, repo)
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


def write_held(mark: Path, marks: dict) -> None:
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
    read at most once per START_EVERY; one brief is returned again only after START_AGAIN."""
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


def sweep(root) -> int:
    repo = session.repo_name(root)
    authors, approvers = verdict_authors(root), spec_approvers(root)
    late = session.flow_int(root, LATE[0], LATE[1], 0)
    now = datetime.now(UTC)
    pulls = read(f"repos/{repo}/pulls?state=open", "the open pull requests")
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
    issues = read(f"repos/{repo}/issues?state=open", "the open issues")
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
    if session.gh(endpoint, *extra, method=method) is None:
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


def full_problem(repo: str, number: int, body: str) -> str | None:
    """`line_problem`, then for a verdict the reads of pull request NUMBER: the check that
    `check-verdict --pr` and the guard run before a post. A read that fails is a CheckError."""
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
    return head_problem(repo, number, body, head)


def check_verdict(path: str, root=None, number: int | None = None) -> int:
    try:
        body = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the verdict file cannot be read") from exc
    problem = (
        line_problem(body)
        if number is None
        else full_problem(session.repo_name(root), number, body)
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
    if queue is None and routine is None and not plain:
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
