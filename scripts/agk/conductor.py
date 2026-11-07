"""The conductor's routines as kit commands (brief #643, ADR-0308). Read-only: GET only, posts
nothing and writes no file.

    python3 conductor.py watch [--since ISO] [--once]
    python3 conductor.py sweep

`watch` polls the comments of every open issue labelled `agk-brief` and every open pull request,
and exits 0 printing one line `<number> <first line>` for each comment created after `--since`
(default: the start) whose first line starts `Question:` or `Report:` (conductor catch log row 1);
`--once` reads once, printing `nothing new` when there is none. The poll interval is
`conductor_poll_seconds` of the `[flow]` table of agk.toml (60 by default); a read that fails is
printed and retried. `sweep` prints one line `#<n> <head7> <state> <age>` per open pull request,
then the latest run of the default branch and any open red-branch issue. A `Question:` or
`Report:` with no comment by a listed verdict author after it, older than
`conductor_late_minutes` (30 by default), is marked `LATE` (row 13). The rules it reads are
`session.py`'s and `merge_cleared.py`'s own functions, never a copy.

Brief #669 (ADR-0322): after those lines `sweep` prints `SILENT <brief> <session> <minutes>;
re-fire: Session name: <session>. Item: brief #<brief>.` for each open `agk-brief` issue whose
newest live take (`session.live_takes`) is older than `silent_minutes` of `[flow]` (30 by
default), measured from the take comment's creation time, with no branch `claude/brief-<n>`, no
open pull request naming the brief, no pull request naming it created after the take, and no
`Progress:`, `Report:` or `Question:` comment after the take. A brief with any `Report: ...
escalate` comment is never SILENT. The sweep fires nothing; the conductor re-fires the session
with the printed line.

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
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import merge_cleared
import session
from common import CheckError, repo_root
from full_run import contained_in, covered
from reviewers import approval_shas, authors_of, spec_approvers, verdict_authors

USAGE = (
    "usage: conductor.py watch [--since ISO] [--once] | conductor.py sweep | "
    "conductor.py merge-queue [--dry-run] [--max-batch N]"
)
TRIGGERS = ("Question:", "Report:")
QUESTION_ID = re.compile(r"Question: (Q-\S+)")
POLL = ("conductor_poll_seconds", 60)
LATE = ("conductor_late_minutes", 30)
SILENT = ("silent_minutes", 30)
ALIVE = ("Progress:", "Report:", "Question:")
ESCALATE = re.compile(r"Report: .*\bescalate\b")


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


def new_lines(repo: str, since: datetime) -> list[str]:
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
            if first.startswith(TRIGGERS) and session.moment(c.get("created_at")) > since:
                lines.append(f"{number} {first}")
    return lines


def watch(root, since: datetime, once: bool) -> int:
    repo = session.repo_name(root)
    interval = session.flow_int(root, POLL[0], POLL[1], 0)
    while True:
        try:
            lines = new_lines(repo, since)
        except CheckError as exc:
            if once:
                raise
            print(f"error: {exc}; retrying", file=sys.stderr, flush=True)
            time.sleep(interval)
            continue
        if lines or once:
            print("\n".join(lines) if lines else "nothing new")
            return 0
        time.sleep(interval)


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
    runs = session.gh(f"repos/{repo}/actions/runs?branch={branch}&per_page=1") if branch else None
    if not isinstance(runs, dict):
        raise CheckError("the runs of the default branch cannot be read")
    latest = (runs.get("workflow_runs") or [None])[0]
    if latest:
        state = latest.get("conclusion") or latest.get("status")
        lines.append(f"{branch}: {state} at {str(latest.get('head_sha'))[:7]}")
    else:
        lines.append(f"{branch}: no run")
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
    print("\n".join(lines))
    return 0


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
    if queue is None and args not in (["sweep"], ["watch"], ["watch", "--once"]):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        root = repo_root() if root is None else root
        if queue is not None:
            return merge_queue(root, *queue)
        if args == ["sweep"]:
            return sweep(root)
        return watch(root, since, args[1:] == ["--once"])
    except merge_cleared.Held as exc:
        print(f"merge-queue: held: {exc}")
        return merge_cleared.EXIT_HELD
    except merge_cleared.Unreadable as exc:
        print(f"FAIL conductor: GitHub cannot be read ({exc})", file=sys.stderr)
        return merge_cleared.EXIT_UNREADABLE
    except CheckError as exc:
        print(f"FAIL conductor: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
