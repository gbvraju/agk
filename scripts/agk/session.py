"""What a builder session reads from GitHub: its verdicts and its next brief (SPEC-0030).

    python3 session.py watch --pr N [--interval S] [--timeout S]
    python3 session.py watch --merged N [--interval S] [--timeout S]
    python3 session.py next --session ID
    python3 session.py queue --role conductor|builder|person [--author LOGIN]
    python3 session.py review-queue [--all | --fingerprint]
    python3 session.py resume --pr N
    python3 session.py ids [--exclude-pr N]
    python3 session.py demand
    python3 session.py push-check
    python3 session.py slot (--take | --renew | --release | --next) SLOT

`watch` polls with `gh api --method GET` and exits 0 with one line: `verdict <kind> <sha> (comment
<id>)` for a verdict by a listed author that names a prefix of the current head and is newer than
the newest comment seen at the start, `merged #N` or `closed #N`; with `--timeout` and no event it
prints `timeout` and exits 3. `--pr` also ends with `conflict #N` when the pull request
conflicts with its base (`mergeable_state` dirty), since CI does not start on it.
`--merged N` waits on that pull request alone and ignores comments. `--pr` also ends with
`correction #n (comment id): <first line>` on a `Correction:` comment by a listed author, newer
than the start, on the pull request or on the brief named by its `Brief: #n` line (SPEC-0032 rule
10), and with `label <name>` (or `label none`) when the `agk:` label that the router sets
(SPEC-0032) changes from the one it read at its first poll; it prints its event and exits (no
loop): each event is one wake. `queue` prints `#N <label>` for each open pull request whose router
label belongs to the role (conductor: `agk:review`, `agk:ci-red`, not drafts; builder: `agk:fix`,
`agk:conflict`, `agk:ci-red`, of `--author` when given; person: `agk:approve`, `agk:ready`), or
`empty`, so a session that starts or restarts resumes from GitHub with one GET.
`review-queue` (brief 306) prints, read-only, the open pull requests that need a conductor's verdict
and why, one line `#N <head7> review: <reason>; ...` each, or `empty`: a pull request labelled
`agk:review`; one with a `Question:`, `Report:`, `Correction:` or `Maintainer answer:` comment
created or edited after the last verdict; one whose head differs from the last verdict's (or with
none yet); one whose checks are green under a stale `agk:ci-running` label. Never twice on one head:
a verdict that names the head, with no such comment after it, skips the pull request whatever its
label; a draft and checks still running (whatever the label) skip it too, except that a draft with a
`Question:` comment created or edited after the last verdict is listed with the reason `question
on a draft`, whatever its head, label or checks (brief 350). Brief 408: after the pull requests
it lists each `Request: <session> ...` on the one open `agk-conductor` issue with no
`Assign: <session> ...` by a listed author after it, as `request <session> (comment <id>)
waiting <minutes>m`, and each open `agk-brief` issue with a live `taken:`, no open pull request
with its `Brief: #n` line and a `Question:` comment created or edited after the brief's last
comment by a listed author (a session's own `Question:`, `taken:`, `released:` and `taken over:`
lines are no answer), as `#<brief> question on a brief`. Required checks that
have not reported skip it under `agk:ci-running` and add the reason `checks not reported` under
any other label. `--all` adds a line `#N <head7> skip: <why>`
for each other open pull request; `--fingerprint` prints only `fingerprint <sha256>` of the heads,
labels, draft flags, comment times (a draft's too), check states, and the waiting requests and
brief questions (their ids and times, never the minutes waited), which changes only when the
queue does, so a loop wakes the conductor only then. With `[flow] auto_merge = true` on the
default branch (brief #531, SPEC-0039 rule 9), a pull request that would be skipped for a verdict
on its head, whose latest `Verdict:` comment is exactly `Verdict: cleared <its full head>`, is
listed as `#N <head7> cleared, not merged`, and the conductor runs `merge_cleared.py` for it again.
A wait never goes silent (brief #210): when GitHub cannot be read for 5 polls in a row it prints
`error: <what> cannot be read` and exits 4, and `--assign` prints `waiting on #<issue> since
<id>` when it starts. `--assign` also takes at once the newest `Assign:` for the session posted
between its previous `Request:` and its current one, unless the session has a `taken:` on any
brief after it (brief #252). When `gh` says it could not connect, the line is
`github-unreachable: <what> cannot be read; local head <sha> not pushed; next: push, then post the
Report:/Question:`; a rate limit is waited out to the reset time that GitHub reports and does
not end a wait (answer 6).
`next` prints the first free `agk-brief` issue and the line `take it with: session.py claim
--session ID --brief N`, and posts nothing (brief #440, ADR-0236); `claim`, `next --take` and
`after` take it with the one comment `taken: <ID> <YYYY-MM-DD>`, the only POST of this script
besides `taken over:` and `tell`; with none left `next` prints `no brief` and exits 1. This
is the only script that calls GitHub; no check does. Messages name the rule, never a value.
SPEC-0034: `next` takes nothing and prints `full <open>/<max>` when `max_builders` builder pull
requests are open (rule 1), skips a brief whose `Touches:` overlaps an open builder pull request or
a taken brief and orders the rest by `Priority:` (rule 3), writes the numbers it reserves into its
take (`reserves ADR-0124`, rule 4) and frees a take after `claim_hours` or a `released:` comment
(rule 5). `ids` prints the next free numbers as one JSON line (rule 4), `demand` how many sessions
a launcher may start (rule 6) and `push-check` the files in which the head conflicts with the
default branch (rule 7b, exit 1).
Brief #327: `tell --session ID --text MESSAGE` posts one comment `Tell: <ID> <message>` on the one
open `agk-conductor` issue (one line of at most 300 characters, never starting with `Approve:`,
`Confirmed:` or `Verdict:`; a refusal names the rule, never the text); `inbox --session ID` (GET
only) prints the `Tell:` lines for the session by a listed verdict author since its last
`Request:` or since the inbox last printed one, and keeps that mark in the git directory;
`watch --assign` prints each new `Tell:` line for the session while it waits.
Brief #348 build (c) (Q-348-2, ADR-0218): while `agk.toml` of the default branch sets
`paused = true`, `claim`, `next`, `queue`, `watch` (all three forms) and `after` (which may take a
brief) print one line that starts `agk paused` and names the setting, read and write nothing on
GitHub and exit 5. The default branch is the ref `origin/<default_branch>`, which session rule 33's
fetch keeps current, never the session's own branch; without that ref the checkout's `agk.toml` is
read.
Brief #424 (ADR-0229): `mine --session ID (--pr N | --brief N)` (GET only) prints `mine` and exits 0
when the session holds a live take of the brief (any build of it), for a pull request the brief
that its `Brief: #n` line names; otherwise it prints `not mine: #<brief> belongs to <session>` (the
oldest live take of another session), `not mine: #<brief> has no live take`, or, for a pull request
without that line, `not mine: #<pr> names no brief`, and exits 1. A read that fails exits 2.
Brief #548 (ADR-0272): `tidy [--apply] [--json]` lists each linked worktree and local branch as
`remove <path> <branch> #<pr> merged|closed` or `kept: <reason> (<path> <branch>)`, and with
`--apply` removes the candidates: a builder branch (`[tidy] branch_prefix` and a number) whose pull
requests (one GET each) are all merged or closed, whose tip is the newest one's head, with a clean,
unlocked worktree holding no ignored file outside the `[tidy] caches` and unchanged for
`[tidy] min_idle_minutes` (60), that is neither the current one nor the main clone, and that no
live lock or queue record names. A read failure keeps
the item; never `--force`, never a remote branch; refused while paused.
Brief #623 (SPEC-0045 rule 4, ADR-0289): `kind --brief N` (GET only, posts nothing) prints one line
`kind: <kind>` from the brief's `Size:` and `Touches:` lines alone: `design` for a missing, repeated
or unreadable line, a brief that cannot be read, or a glob that may match a design path (`**`, the
requirements, specs, ADRs, constitution, `.github/`, the reviewers file, the hooks, the merge path
or a guard file, Q-S0045-4); `small` for `Size: S` whose every glob may match no protected class of
`config/protected-paths.txt` but the test folders; `build` otherwise. Never `review` or
`mechanical`.
Brief #700 (ADR-0330): `prompt --brief N [--session ID] [--follow-up TEXT]` (GET only, two reads:
the brief and its comments) prints the builder's standing prompt from the kit's files, so that a
project's scheduled builder and the conductor's re-fire use one text and nothing is kept by hand:
the item line with the brief's reserved numbers (its `Reserved:` lines and the `reserves` of its
takes; `none` without any) and the session name when given, the files to read first, the
secret-scan deferral line of `prepush.py`, the session rules that bind a builder quoted from
`config/session-rules.md` (`BUILDER_RULES`; a number the project's file lacks is a note on stderr),
and the body lines of CLAUDE.md item 7 read from `config/core-rules.md` (a file without the item
fails). `--follow-up TEXT` (one line, never a verdict) replaces the stop on an existing pull
request with the follow-up for it. The title of a brief never goes into the prompt.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from check_specs import CONTEXTS, CONTEXTS_PREFIX, CONTEXTS_RULE, contexts_problems
from common import (
    PAUSED_LINE,
    CheckError,
    _verify,
    config_source,
    covered_fix_list,
    git,
    load_config,
    next_free_ids,
    paused,
    repo_root,
    required_checks,
    show,
)
from facts import ORIGIN
from metrics import author_of, counted_authors, latest_verdict_body
from reviewers import spec_approvers, verdict_authors

from config import caps_settings

NAME = "session"
USAGE = (
    "usage: session.py watch (--pr N [--since ID] [--session ID] | --merged N | --assign ID)\n"
    "                        [--interval S] [--timeout S]\n"
    "       session.py next --session ID [--take]\n"
    "       session.py claim --session ID --brief N [--build X]\n"
    "       session.py after --session ID\n"
    "       session.py queue --role conductor|builder|person [--author LOGIN]\n"
    "       session.py review-queue [--all | --fingerprint]\n"
    "       session.py resume --pr N\n"
    "       session.py ids [--exclude-pr N]\n"
    "       session.py demand\n"
    "       session.py plan [--json] [--record] | plan --what-if DIR\n"
    "       session.py push-check\n"
    "       session.py slot (--take | --renew | --release | --next) SLOT\n"
    "       session.py tell --session ID --text MESSAGE\n"
    "       session.py inbox --session ID\n"
    "       session.py mine --session ID (--pr N | --brief N)\n"
    "       session.py kind --brief N\n"
    "       session.py prompt --brief N [--session ID] [--follow-up TEXT]\n"
    "       session.py tidy [--apply] [--json]"
)
COMMANDS = (
    "watch",
    "next",
    "claim",
    "after",
    "queue",
    "review-queue",
    "resume",
    "ids",
    "demand",
    "plan",
    "push-check",
    "slot",
    "tell",
    "inbox",
    "mine",
    "kind",
    "prompt",
    "tidy",
)
PAGE = 100
PAUSED_EXIT = 5
PAUSED_COMMANDS = frozenset({"claim", "next", "queue", "watch", "after", "slot"})
PAUSED_REFUSAL = (
    f"{PAUSED_LINE} (setting: paused in agk.toml of the default branch): session.py claims, takes,"
    " lists and waits on nothing; remove the line `paused = true` to resume"
)
LABEL = "agk-brief"
HOLD = re.compile(r"Hold: #(\d+) +(\S.*)")  # amendment 142: the owner's hold of a brief
RELEASE = re.compile(r"Release: #(\d+)(?: .*)?")
HELD_PREFIX = "held by the owner: "
STALE_LABEL = "agk-stale"
STALE_LINE = "Status: stale"
PARKED_LABEL = "agk:parked"
PARKED_PREFIX = "Parked:"
MAX_BUILDERS = 3
CLAIM_HOURS = 4
VERDICT = re.compile(r"Verdict: (cleared|fix list|rejected) ([0-9a-f]{7,40})")
NUMBER = r"(?:REQ-\d{3}|SPEC-\d{4}|ADR-\d{4})"
BUILD = r"(?: build \(([A-Za-z0-9._-]+)\))?"
TAKE = re.compile(
    rf"taken: (\S+) (\d{{4}}-\d{{2}}-\d{{2}}){BUILD}(?: retakes)?"
    rf"(?: reserves ({NUMBER}(?:, {NUMBER})*))?"
)
FOOTER = re.compile(r"\n+---\n_Generated by \[Claude Code\]\([^)\n]*\)_\s*$")
RULES_FILE = "config/session-rules.md"
RELEASED = re.compile(rf"released: (\S+){BUILD}")
ASSIGN = re.compile(
    r"Assign: (\S+) (none|#(\d+)(?: build \(([A-Za-z0-9._-]+)\))?"
    r"(?: pr #(\d+) (fix list|merge of main))?)"
)
ASSIGN_LABEL = "agk-conductor"
TELL = re.compile(r"Tell: (\S+) (.+)")
TELL_LIMIT = 300
TELL_REFUSED = re.compile(r"\s*(?:Approve|Confirmed|Verdict):", re.IGNORECASE)
ZERO_WIDTH = re.compile("[\u200b-\u200f\u2060\ufeff]")  # read as nothing before the start check
ASSIGN_MODES = ("conductor", "next")
BRIEF_LINE = re.compile(r"Brief: #(\d+)")
TOUCHES = re.compile(r"Touches: (.+)")
ADDS = re.compile(r"Adds: (.+)")
BROAD = re.compile(r"Broad: \S.*")
SENTENCE = re.compile(r'Sentence: "(.*)"')
DEPENDS = re.compile(r"Depends-on: #(\d+)")
SIZE = re.compile(r"Size: [SML]")
WAVE = re.compile(r"Wave: ([1-9]\d*)")
MILESTONE_WAVE = re.compile(r"Wave ([1-9]\d*)\b")
NUMBERED = re.compile(r"(\d+)\.\s+\S")
ADVANCES = re.compile(r"Advances: (new|REQ-\d{3}(?:, REQ-\d{3})*)")
PRIORITY = re.compile(r"Priority: ([0123])")  # 0 is valid in a brief only with `Measured:`
MEASURED = re.compile(r"Measured: (?=.*\bbefore\b)(?=.*\bafter\b)\S.*")
CORRECTION = re.compile(r"Correction:.*")
RED_TITLE = "The default branch is red"
ROUTER_LOGIN = "github-actions[bot]"  # the author of an issue opened with the job's token
ROUTER_PAIR = ("Advances: none", "Priority: 0")  # written only by the router (SPEC-0032 rule 7)
SESSION_ID = re.compile(r"[A-Za-z0-9._-]+")
STATE_PREFIX = "agk:"
UNSET = object()
ROLES = {
    "conductor": ("agk:review", "agk:ci-red"),
    "builder": ("agk:fix", "agk:conflict", "agk:ci-red"),
    "person": ("agk:approve", "agk:ready"),
}
TAKEOVER = re.compile(r"taken over: (\S+) (\d{4}-\d{2}-\d{2})")
HEAD_VERDICT = re.compile(r"Verdict: (cleared|fix list|rejected)(?: ([0-9a-f]{7,40}))?")
BUILDER_LABELS = frozenset({"agk:fix", "agk:conflict", "agk:ci-red"})
WAITING_LABELS = frozenset({"agk:ready", "agk:approve"})
STALL_HOURS = 4
SAFE_REF = re.compile(r"[A-Za-z0-9._/-]+")
PROGRESS = re.compile(  # the step, then the usage ending of session rule 8 (SPEC-0049 rule 4)
    r"Progress: ([0-9a-f]{7,40}) done (\d+)/(\d+); next: (\S.*?)"
    r"(?:; Usage: (?:\d+ tokens|not shown))?"
)
OVER_CAP = re.compile(r"Report: \S+ over cap (\d+(?:\.\d+)?)/\d+ (tokens|hours)\b.*")


LAST_ERROR = ""  # what `gh` said about the last failed call (empty after a good one)
RATE_LIMIT = re.compile(r"rate limit|HTTP 429", re.IGNORECASE)
RATE_WAITS = 5  # rate limits waited out for one call before it counts as failed
RESET_SLACK = 1.0  # seconds after the reset time that GitHub reports
UNREACHABLE = re.compile(
    r"error connecting|dial tcp|no such host|could not resolve|connection (?:refused|reset)"
    r"|network is unreachable|i/o timeout|tls handshake|timed out|temporary failure in name",
    re.IGNORECASE,
)


def rate_reset() -> float | None:
    """The reset time of the core rate limit that GitHub reports (`GET rate_limit` is free)."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["gh", "api", "--method", "GET", "rate_limit"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    try:
        return float(json.loads(proc.stdout)["resources"]["core"]["reset"])
    except (ValueError, KeyError, TypeError):
        return None


def gh(endpoint: str, *extra: str, method: str = "GET") -> Any:
    """One `gh api` call; a failed or unreadable call is None. A rate limit is not a failure
    (brief #210 answer 6): the call waits until the reset time that GitHub reports and retries."""
    global LAST_ERROR
    for attempt in range(RATE_WAITS + 1):
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["gh", "api", "--method", method, endpoint, *extra],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        LAST_ERROR = proc.stderr if proc.returncode != 0 else ""
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout) if proc.stdout.strip() else {}
            except ValueError:
                return None
        reset = rate_reset() if RATE_LIMIT.search(proc.stderr) else None
        if reset is None or attempt == RATE_WAITS:
            return None
        time.sleep(max(0.0, reset - time.time()) + RESET_SLACK)
    return None


def pages(endpoint: str) -> list | None:
    sep = "&" if "?" in endpoint else "?"
    found: list = []
    page = 1
    while True:
        chunk = gh(f"{endpoint}{sep}per_page={PAGE}&page={page}")
        if not isinstance(chunk, list):
            return None
        found += chunk
        if len(chunk) < PAGE:
            return found
        page += 1


def repo_name(root) -> str:
    match = ORIGIN.search(git(root, "remote", "get-url", "origin", check=False).strip())
    if shutil.which("gh") is None:
        raise CheckError("rule 5: gh is not installed")
    if not match:
        raise CheckError("rule 2: the remote origin is not a GitHub repository")
    return match.group(1)


def moment(text: Any) -> datetime:
    try:
        return datetime.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return datetime.now(UTC)


# --- watch (rule 2) ---------------------------------------------------------------------------


def newest(comments: list | None) -> int | None:
    if comments is None:
        return None
    return max((c["id"] for c in comments if isinstance(c.get("id"), int)), default=0)


def verdict_line(comments: list, seen: int, head: str, authors: list[str] | None) -> str | None:
    allowed = {a.lstrip("@").lower() for a in authors or []}
    for comment in sorted(comments, key=lambda c: c.get("id", 0)):
        body = comment.get("body")
        if not isinstance(body, str) or comment.get("id", 0) <= seen:
            continue
        match = VERDICT.fullmatch(body.splitlines()[0].strip()) if body.strip() else None
        if match and author_of(comment) in allowed and head.startswith(match.group(2)):
            return f"verdict {match.group(1)} {match.group(2)} (comment {comment['id']})"
    return None


def report_floor(comments: list, author: str | None) -> int:
    """The id of the newest comment whose first line starts `Report:` by the pull request's author:
    what the session had said when it last pushed (0 without one)."""
    me = (author or "").lstrip("@").lower()
    found = [
        c.get("id", 0)
        for c in comments
        if isinstance(c.get("body"), str)
        and c["body"].startswith("Report:")
        and author_of(c) == me
        and isinstance(c.get("id"), int)
    ]
    return max(found, default=0)


def missed_verdict(comments: list, floor: int, head: str, authors: list[str] | None) -> str | None:
    """The latest verdict by a listed author, when it is newer than `floor` and names `head`: the
    event a watch started after it would never see (brief #210 (b)). A verdict that names a
    previous head, or that comes before the floor, is not one."""
    allowed = {a.lstrip("@").lower() for a in authors or []}
    latest = None
    for comment in sorted(comments, key=lambda c: c.get("id", 0)):
        body = comment.get("body")
        match = (
            VERDICT.fullmatch(body.splitlines()[0].strip())
            if isinstance(body, str) and body.strip()
            else None
        )
        if match and author_of(comment) in allowed:
            latest = (comment.get("id", 0), match)
    if latest and latest[0] > floor and head.startswith(latest[1].group(2)):
        return f"verdict {latest[1].group(1)} {latest[1].group(2)} (comment {latest[0]})"
    return None


def label_of(pr: dict) -> str:
    """The router's label of a pull request (SPEC-0032 rule 2), `none` without one."""
    names = sorted(
        str(x.get("name"))
        for x in pr.get("labels") or []
        if isinstance(x, dict) and str(x.get("name")).startswith(STATE_PREFIX)
    )
    return ",".join(names) or "none"


def correction_line(
    comments: list, seen: int, authors: list[str] | None, number: int
) -> str | None:
    """`correction #n (comment id): <first line>` for the first `Correction:` comment by a listed
    author newer than `seen` (SPEC-0032 rule 10); the first line is cut at 200 characters."""
    allowed = {a.lstrip("@").lower() for a in authors or []}
    for comment in sorted(comments, key=lambda c: c.get("id", 0)):
        body = comment.get("body")
        if not isinstance(body, str) or comment.get("id", 0) <= seen or not body.strip():
            continue
        first = body.splitlines()[0].strip()
        if CORRECTION.fullmatch(first) and author_of(comment) in allowed:
            return f"correction #{number} (comment {comment['id']}): {first[:200]}"
    return None


FAILED_POLLS = 5  # polls in a row that cannot read GitHub before a wait ends with an error
EXIT_UNREADABLE = 4


def local_head(root) -> str:
    """`local head <sha> not pushed` (or `pushed`; `none` without a commit): what is true."""
    head = git(root, "rev-parse", "--short=7", "HEAD", check=False).strip()
    if not head:
        return "local head none"
    ahead = git(root, "rev-list", "--count", "@{upstream}..HEAD", check=False).strip()
    return f"local head {head} {'pushed' if ahead == '0' else 'not pushed'}"


class Reads:
    """Polls in a row in which GitHub could not be read (brief #210): the fifth ends the wait, so
    a wait never goes silent; one failure is retried. When `gh` says it could not connect, the one
    line is `github-unreachable: ...` (answer 6: the only channel left is the session's output);
    otherwise `error: <what> cannot be read`."""

    def __init__(self, root=None) -> None:
        self.bad = 0
        self.root = root

    def good(self) -> None:
        self.bad = 0

    def failed(self, what: str) -> bool:
        self.bad += 1
        if self.bad < FAILED_POLLS:
            return False
        if UNREACHABLE.search(LAST_ERROR):
            print(
                f"github-unreachable: {what} cannot be read; {local_head(self.root)}; "
                "next: push, then post the Report:/Question:",
                flush=True,
            )
        else:
            print(f"error: {what} cannot be read", flush=True)
        return True


def watch(root, args: dict[str, str]) -> int:
    repo = repo_name(root)
    number = args.get("--pr") or args["--merged"]
    only_merge = "--merged" in args
    interval, limit = float(args.get("--interval", 60)), args.get("--timeout")
    started = time.monotonic()

    def late() -> bool:
        return limit is not None and time.monotonic() - started >= float(limit)

    seen = 0
    label: Any = UNSET
    brief_seen: Any = UNSET
    reads = Reads(root)
    since = int(args.get("--since", 0))
    first = True
    floor = 0
    told = Told(root, repo, args["--session"], interval) if "--session" in args else None
    if told is not None and told.start() is not None:
        return EXIT_UNREADABLE
    if not only_merge:
        while (found := newest(pages(f"repos/{repo}/issues/{number}/comments"))) is None:
            if reads.failed(f"the comments of #{number}"):
                return EXIT_UNREADABLE
            if late():
                print("timeout")
                return 3
            time.sleep(interval)
        reads.good()
        seen = found
    while True:
        pr = gh(f"repos/{repo}/pulls/{number}")
        if not isinstance(pr, dict):
            if reads.failed(f"pull request #{number}"):
                return EXIT_UNREADABLE
        else:
            if pr.get("merged_at"):
                print(f"merged #{number}")
                return 0
            if pr.get("state") == "closed":
                print(f"closed #{number}")
                return 0
            if pr.get("mergeable_state") == "dirty" and not only_merge:
                print(f"conflict #{number}")
                return 0
            comments = None if only_merge else pages(f"repos/{repo}/issues/{number}/comments")
            if comments is None and not only_merge:
                if reads.failed(f"the comments of #{number}"):
                    return EXIT_UNREADABLE
            else:
                reads.good()
            if comments is not None:
                own = (pr.get("user") or {}).get("login")
                authors = counted_authors(verdict_authors(root), own)
                head = str((pr.get("head") or {}).get("sha") or "")
                if first:  # what landed after the last Report: and before this watch started
                    first = False
                    floor = max(report_floor(comments, own), since)
                    line = missed_verdict(comments, floor, head, authors)
                    line = line or correction_line(comments, floor, authors, int(number))
                    if line:
                        print(line)
                        return 0
                line = verdict_line(comments, seen, head, authors)
                if line:
                    print(line)
                    return 0
                line = correction_line(comments, seen, authors, int(number))
                if line:
                    print(line)
                    return 0
                brief = brief_number(pr)
                if brief is not None:
                    found = pages(f"repos/{repo}/issues/{brief}/comments")
                    if found is not None and brief_seen is UNSET:
                        brief_seen = newest(found)
                        line = correction_line(found, floor, authors, brief)
                        if line:
                            print(line)
                            return 0
                    elif found is not None:
                        line = correction_line(found, brief_seen, authors, brief)
                        if line:
                            print(line)
                            return 0
            if not only_merge:
                now = label_of(pr)
                if label is UNSET:
                    label = now
                elif now != label:
                    print(f"label {now}")
                    return 0
        if told is not None and (code := told.poll()) is not None:
            return code
        if late():
            print("timeout")
            return 3
        time.sleep(interval)


class Told:
    """The `Tell:` lines of `watch --pr N --session ID` (brief #368 answer 1): the watch also ends,
    with `tell <message>`, on a `Tell: <ID> ...` by a listed author on the one open `agk-conductor`
    issue that is newer than the start. Its own count of unread polls (session rule 21)."""

    def __init__(self, root, repo: str, me: str, interval: float) -> None:
        self.me, self.interval, self.repo = me, interval, repo
        self.issue: int | None = None
        self.path = ""
        self.allowed = {a.lstrip("@").lower() for a in counted_authors(verdict_authors(root), None)}
        self.reads = Reads(root)
        self.seen = 0

    def start(self) -> int | None:
        """Find the one open `agk-conductor` issue and read its baseline: an unread baseline would
        make an old line look new. A failed read is retried and the fifth in a row ends the watch
        (session rule 21); without exactly one such issue the watch says so in one line and goes
        on watching the pull request (the verdict on e90f60b, item 1)."""
        listing = f"repos/{self.repo}/issues?state=open&labels={ASSIGN_LABEL}"
        while (found := pages(listing)) is None:
            if self.reads.failed(f"the open issues labelled {ASSIGN_LABEL}"):
                return EXIT_UNREADABLE
            time.sleep(self.interval)
        self.reads.good()
        issues = [i for i in found if "pull_request" not in i and isinstance(i.get("number"), int)]
        if len(issues) != 1:
            why = "no open issue" if not issues else "more than one open issue"
            print(f"messages: not read ({why} labelled {ASSIGN_LABEL})", flush=True)
            return None
        self.issue = issues[0]["number"]
        self.path = f"repos/{self.repo}/issues/{self.issue}/comments"
        while (comments := pages(self.path)) is None:
            if self.reads.failed(f"the comments of #{self.issue}"):
                return EXIT_UNREADABLE
            time.sleep(self.interval)
        self.reads.good()
        self.seen = newest(comments) or 0
        return None

    def poll(self) -> int | None:
        """0 after printing a new `tell` line, EXIT_UNREADABLE on five unread polls, or None."""
        if self.issue is None:
            return None
        comments = pages(self.path)
        if comments is None:
            return EXIT_UNREADABLE if self.reads.failed(f"the comments of #{self.issue}") else None
        self.reads.good()
        for comment in sorted(comments, key=lambda c: c.get("id", 0)):
            line = tell_line(comment, self.me, self.allowed)
            match = TELL.fullmatch(line) if line and comment.get("id", 0) > self.seen else None
            if match:
                print(f"tell {match.group(2)}", flush=True)
                return 0
        return None


# --- the shape of a brief (rule 4) ------------------------------------------------------------


def brief_problems(body: str | None) -> list[str]:
    """What rule 4 finds wrong with an issue body; it never repeats the sentence."""
    lines = (body or "").splitlines()
    problems: list[str] = []
    sentences = [m for m in (SENTENCE.fullmatch(x.rstrip()) for x in lines) if m]
    if len(sentences) != 1:
        problems.append("rule 4: exactly one line Sentence: with the sentence in quotation marks")
    elif not 1 <= len(sentences[0].group(1)) <= 300:
        problems.append("rule 4: the Sentence is not 1 to 300 characters")
    heads = [i for i, x in enumerate(lines) if x.startswith("Answers") and x.rstrip().endswith(":")]
    if len(heads) != 1:
        problems.append("rule 4: exactly one line that starts Answers and ends with a colon")
    else:
        numbers = [int(m.group(1)) for m in map(NUMBERED.match, lines[heads[0] + 1 :]) if m]
        if numbers != list(range(1, len(numbers) + 1)) or not numbers:
            problems.append("rule 4: the Answers items are not numbered 1, 2, ... without a gap")
    for line in lines:
        if line.startswith("Depends-on") and not DEPENDS.fullmatch(line.rstrip()):
            problems.append("rule 4: a Depends-on line is not Depends-on: #n")
    if sum(1 for x in lines if SIZE.fullmatch(x.rstrip())) != 1:
        problems.append("rule 4: exactly one line Size: S, Size: M or Size: L")
    return problems + line_problems(lines)


def contexts_line_problems(body: str | None) -> list[str]:
    """Amendment 142: the one `Contexts:` line of a brief; the router's red-branch brief, a fixed
    repair of the default branch and no design, needs none (SPEC-0032 rule 7)."""
    text = (body or "").splitlines()
    if all(any(x.rstrip() == pair for x in text) for pair in ROUTER_PAIR):
        return []
    lines = [x for x in text if x.startswith(CONTEXTS_PREFIX)]
    if len(lines) != 1:
        return [f"{CONTEXTS_RULE}: exactly one line Contexts: listing {', '.join(CONTEXTS)}"]
    return contexts_problems(lines[0][len(CONTEXTS_PREFIX) :])


def line_problems(lines: list[str]) -> list[str]:
    """SPEC-0034 rule 2: the Advances, Touches and Priority lines (never the sentence)."""
    problems: list[str] = []
    advances = [x.rstrip() for x in lines if x.startswith("Advances")]
    priority = [x.rstrip() for x in lines if x.startswith("Priority")]
    pair = advances == [ROUTER_PAIR[0]] and priority == [ROUTER_PAIR[1]]
    if not pair and (len(advances) != 1 or not ADVANCES.fullmatch(advances[0])):
        problems.append(
            "rule 2: exactly one line Advances: REQ-n (comma-separated) or Advances: new"
        )
    touches = [x.rstrip() for x in lines if x.startswith("Touches")]
    globs = touches[0][len("Touches:") :].split(",") if touches[:1] else []
    if (
        len(touches) != 1
        or not touches[0].startswith("Touches:")
        or not all(g.strip() for g in globs)
    ):
        problems.append("rule 2: exactly one line Touches: with path globs separated by commas")
    adds = [x for x in lines if x.startswith("Adds:")]
    if (
        len(adds) > 1
        or not all(ADDS.fullmatch(x.rstrip()) for x in adds)
        or not all(g.strip() for x in adds for g in x[len("Adds:") :].split(","))
    ):
        problems.append("rule 4: at most one line Adds: with paths separated by commas")
    broad = [x for x in lines if x.startswith("Broad:")]
    if len(broad) > 1 or not all(BROAD.fullmatch(x.rstrip()) for x in broad):
        problems.append("rule 4: at most one line Broad: with its reason")
    if not pair and (len(priority) > 1 or any(not PRIORITY.fullmatch(x) for x in priority)):
        problems.append("rule 2: at most one line Priority: 0, 1, 2 or 3")
    return problems + measured_problems(lines, pair, priority)


def measured_problems(lines: list[str], pair: bool, priority: list[str]) -> list[str]:
    """SPEC-0032 rule 9: a cause is measured, not reasoned. A `Measured:` line holds the command run
    and the output before and after a change that turns it green; a `Priority: 0` brief needs
    exactly one, except the brief the router writes for a red default branch (it names no cause)."""
    measured = [x.rstrip() for x in lines if x.startswith("Measured")]
    problems: list[str] = []
    if len(measured) > 1 or any(not MEASURED.fullmatch(x) for x in measured):
        problems.append(
            "rule 9: at most one line Measured: with the command and the output before and after"
        )
    elif not measured and not pair and priority == ["Priority: 0"]:
        problems.append(
            "rule 9: a Priority: 0 brief needs one line Measured: with the command and the output"
            " before and after a change that turns it green"
        )
    return problems


def wave_problems(body: str | None, known: set[int] | None = None) -> list[str]:
    """Amendment 140 of SPEC-0030 rule 4: the `Wave:` line of a brief of a repository with a plan
    issue; `known` is the plan's waves, None when they cannot be read (the shape is then enough)."""
    wave = wave_of(body)
    if wave is None:
        return ["rule 4: exactly one line Wave: n (setting: plan_issue)"]
    if known and wave not in known:
        return ["rule 4: the Wave line names a wave the plan does not have"]
    return []


def wave_of(body: str | None) -> int | None:
    """The wave a brief's one good `Wave:` line names, None without one."""
    lines = [x.rstrip() for x in (body or "").splitlines() if x.startswith("Wave:")]
    found = WAVE.fullmatch(lines[0]) if len(lines) == 1 else None
    return int(found.group(1)) if found else None


def plan_issue_set(root) -> bool:
    """`plan_issue` of the `[flow]` table is set, so every brief needs a wave of that plan."""
    table = config_source(root).get("flow")
    return isinstance(table, dict) and table.get("plan_issue") is not None


def plan_waves(repo: str) -> set[int] | None:
    """The waves of the plan: the milestones titled `Wave <n>`; None when they cannot be read."""
    found = pages(f"repos/{repo}/milestones?state=all")
    if found is None:
        return None
    titles = (MILESTONE_WAVE.match(str(m.get("title"))) for m in found if isinstance(m, dict))
    return {int(t.group(1)) for t in titles if t} or None


def advances_ids(body: str) -> list[str]:
    """The requirement ids a brief that passed `brief_problems` advances (empty for `new`)."""
    for line in body.splitlines():
        found = ADVANCES.fullmatch(line.rstrip())
        if found:
            return [] if found.group(1) == "new" else found.group(1).split(", ")
    return []


def depends_on(body: str) -> list[int]:
    found = (DEPENDS.fullmatch(x.rstrip()) for x in body.splitlines())
    return [int(m.group(1)) for m in found if m]


# --- the flow table (SPEC-0034 rules 1 and 5) ------------------------------------------------


def flow_value(root, key: str, default: Any, rule: int) -> Any:
    """A value of the `[flow]` table of agk.toml, `default` when it is not set."""
    try:
        data = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise CheckError(f"rule {rule}: agk.toml cannot be read") from exc
    table = data.get("flow", {})
    return table.get(key, default) if isinstance(table, dict) else default


def flow_int(root, key: str, default: int, rule: int) -> int:
    """A whole number, 1 or more, of the `[flow]` table of agk.toml; names the setting only."""
    value = flow_value(root, key, default, rule)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CheckError(f"rule {rule}: {key} of the flow table must be a whole number, 1 or more")
    return value


# --- the claims (SPEC-0034 rule 5) ------------------------------------------------------------


def brief_number(pr: dict) -> int | None:
    """The `n` of the line `Brief: #n` of a pull request body (a builder one), else None."""
    for line in str(pr.get("body") or "").splitlines():
        if found := BRIEF_LINE.fullmatch(line.rstrip()):
            return int(found.group(1))
    return None


def plain(body: str) -> str:
    """The body of a comment without the attribution footer that the server adds (`---` and a
    `Generated by` line), so that a take or a release written alone on its lines is still read."""
    return FOOTER.sub("", body).strip()


def all_takes(comments: list) -> list[tuple]:
    """(when, id, session, login, reserves, released, build) of every take comment, oldest first.

    A `released:` frees a take only when the same account posted it, for the build it names or
    for every build when it names none."""
    takes, releases = [], []
    for c in comments:
        text = plain(c["body"]) if isinstance(c.get("body"), str) else ""
        when, cid = moment(c.get("created_at")), c.get("id", 0)
        if found := TAKE.fullmatch(text):
            reserves = tuple(found.group(4).split(", ")) if found.group(4) else ()
            takes.append((when, cid, found.group(1), author_of(c), reserves, found.group(3)))
        elif found := RELEASED.fullmatch(text):
            releases.append((when, cid, found.group(1), author_of(c), found.group(2)))

    def freed(t: tuple) -> bool:
        return any(
            (w, i) > t[:2] and (s, a) == (t[2], t[3]) and b in (None, t[5])
            for w, i, s, a, b in releases
        )

    return sorted((*t[:5], freed(t), t[5]) for t in takes)


def live_takes(comments: list, number: int, prs: list, hours: int) -> list[tuple]:
    """(when, id, session, login, reserves, build) of every live take, oldest first.

    A take is live until a `released:` comment of its session, and for `hours` hours or while an
    open pull request has the line `Brief: #<number>` (or a merged one for `hours` hours after its
    merge, the next build of the brief; SPEC-0034 rule 5)."""
    now = datetime.now(UTC)
    named = any(
        brief_number(pr) == number
        and (
            pr.get("state") == "open"
            or (pr.get("merged_at") and now - moment(pr["merged_at"]) < timedelta(hours=hours))
        )
        for pr in prs
    )
    return [
        (*t[:5], t[6])
        for t in all_takes(comments)
        if not t[5] and (named or now - t[0] < timedelta(hours=hours))
    ]


# --- next (SPEC-0030 rule 3; SPEC-0034 rules 1, 3 and 4) -------------------------------------


@dataclass
class Survey:
    repo: str
    me: str
    max_builders: int
    hours: int
    prs: list  # every pull request, any state
    builders: list  # the open ones with a line `Brief: #n`
    comments: dict = field(default_factory=dict)  # brief number -> its comments
    skipped: list = field(default_factory=list)  # (brief number, why)
    held: list = field(
        default_factory=list
    )  # (brief number, globs) of taken briefs, no pull request
    free: list = field(default_factory=list)  # the briefs left, in the order of rule 3
    files: dict = field(default_factory=dict)  # pull request number -> its changed files
    briefs: dict = field(default_factory=dict)  # brief number -> its issue
    gone: dict = field(default_factory=dict)  # session -> hours since its last post (plan only)
    posts: dict = field(default_factory=dict)  # pull request number -> its comments (plan only)


def is_stale(brief: dict) -> bool:
    """A brief the conductor marked stale: the line `Status: stale` or the label `agk-stale`."""
    lines = (x.rstrip() for x in str(brief.get("body") or "").splitlines())
    labels = {str(x.get("name")) for x in brief.get("labels") or [] if isinstance(x, dict)}
    return STALE_LABEL in labels or STALE_LINE in lines


def is_parked(brief: dict) -> bool:
    """A parked brief (#615, ADR-0301): the label `agk:parked` or a `Parked:` line in its body."""
    lines = (x.strip() for x in str(brief.get("body") or "").splitlines())
    labels = {str(x.get("name")) for x in brief.get("labels") or [] if isinstance(x, dict)}
    return PARKED_LABEL in labels or any(x.startswith(PARKED_PREFIX) for x in lines)


def hold_state(root, comments: list, number: int) -> tuple[str | None, list[str]]:
    """Amendment 142: (the reason of the brief's live hold or None, the logins of a `Hold:` by
    someone not in `spec_approvers`). The latest `Hold:` or `Release:` by an approver decides."""
    lines = [
        (moment(c.get("created_at")), c.get("id", 0), author_of(c), m)
        for c in comments
        if (m := HOLD.fullmatch(first_line(c)) or RELEASE.fullmatch(first_line(c)))
        and int(m.group(1)) == number
    ]
    if not lines:
        return None, []
    approvers = set(spec_approvers(root))
    latest: re.Match | None = None
    ignored: list[str] = []
    for _, _, login, found in sorted(lines, key=lambda x: x[:2]):
        if login in approvers:
            latest = found
        elif found.re is HOLD and login not in ignored:
            ignored.append(login)
    return (latest.group(2) if latest is not None and latest.re is HOLD else None), ignored


def judge(
    repo: str,
    brief: dict,
    me: str,
    prs: list,
    hours: int,
    shape: Callable = brief_problems,
    root=None,
) -> tuple[str | None, list]:
    """Why the brief is not for this session (or None when it is free), and its comments."""
    if is_stale(brief):
        return "stale", []
    if is_parked(brief):
        return "parked", []
    problems = shape(brief.get("body"))
    if problems:
        return problems[0], []
    for dep in depends_on(brief["body"]):
        issue = gh(f"repos/{repo}/issues/{dep}")
        if not isinstance(issue, dict) or "state" not in issue:
            return f"depends on #{dep}, which cannot be read", []
        if issue["state"] != "closed":
            return f"depends on #{dep}, which is open", []
    comments = pages(f"repos/{repo}/issues/{brief['number']}/comments")
    if comments is None:
        return "its comments cannot be read", []
    if root is not None and (reason := hold_state(root, comments, brief["number"])[0]):
        return HELD_PREFIX + reason, comments
    takes = live_takes(comments, brief["number"], prs, hours)
    if takes and not any(t[2] == me for t in takes):
        return f"taken by {takes[0][2]}", comments
    return None, comments


def line_entries(body: str, line: re.Pattern) -> list[str]:
    """The comma-separated entries of the first line of a brief that LINE matches."""
    for text in body.splitlines():
        if found := line.fullmatch(text.rstrip()):
            return [g.strip() for g in found.group(1).split(",")]
    return []


def touches_of(body: str) -> list[str]:
    """What a brief works on: its `Touches:` and `Adds:` lines as one list (amendment 141 item 1).
    Only the two refusals of `session_plan.touch_problems` read the lines apart."""
    return line_entries(body, TOUCHES) + line_entries(body, ADDS)


def priority_of(body: str) -> int:
    for line in body.splitlines():
        if found := PRIORITY.fullmatch(line.rstrip()):
            return int(found.group(1))
    return 2


def brief_shape(root, repo: str) -> Callable:
    """What this repository refuses in a brief body: rule 4, and the wave with a plan issue."""
    from session_plan import touch_problems, touch_rules  # the plan builds on this module

    rules = touch_rules(root)
    known = plan_waves(repo) if plan_issue_set(root) else None
    waves = plan_issue_set(root)

    def shape(body: str | None) -> list[str]:
        found = brief_problems(body) + (wave_problems(body, known) if waves else [])
        return found or touch_problems(str(body), rules)

    return shape


def survey(root, repo: str, me: str, issues: list | None = None) -> Survey:
    """Everything `next`, `demand` and `ids` read: the pull requests, the briefs and their takes.

    While the default branch is red only its brief is left (SPEC-0032 rule 7)."""
    limit = flow_int(root, "max_builders", MAX_BUILDERS, 1)
    hours = flow_int(root, "claim_hours", CLAIM_HOURS, 5)
    issues = pages(f"repos/{repo}/issues?state=open&labels={LABEL}") if issues is None else issues
    if issues is None:
        raise CheckError("rule 3: the open briefs cannot be read")
    red = {i["number"] for i in issues if is_red(i)}
    issues = [i for i in issues if i["number"] in red] if red else issues
    # The red-branch brief goes before the capacity and the overlap, and no pull request is read.
    prs = [] if red else pages(f"repos/{repo}/pulls?state=all")
    if prs is None:
        raise CheckError("rule 1: the pull requests cannot be read")
    builders = [p for p in prs if p.get("state") == "open" and brief_number(p) is not None]
    found = Survey(repo, me, limit, hours, prs, builders)
    found.briefs = {i["number"]: i for i in issues if "pull_request" not in i}
    named = {brief_number(p) for p in prs if p.get("state") == "open"}
    shape = brief_shape(root, repo)
    for brief in sorted((i for i in issues if "pull_request" not in i), key=lambda i: i["number"]):
        why, comments = judge(repo, brief, me, prs, hours, shape, root)
        found.comments[brief["number"]] = comments
        if why is None:
            found.free.append(brief)
            continue
        found.skipped.append((brief["number"], why))
        running = why.startswith("taken by") or (
            why.startswith(HELD_PREFIX)
            and any(t[2] != me for t in live_takes(comments, brief["number"], prs, hours))
        )
        if running and brief["number"] not in named:
            found.held.append((brief["number"], touches_of(brief["body"])))
    found.free.sort(key=lambda b: (priority_of(b["body"]), b["number"]))
    return found


def glob_regex(glob: str) -> re.Pattern:
    """A path glob: `*` and `?` stay in one directory, `**` crosses them, `dir/` is `dir/**`."""
    glob = glob + "**" if glob.endswith("/") else glob
    out, i = "", 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif glob.startswith("**", i):
            out, i = out + ".*", i + 2
        else:
            out += {"*": "[^/]*", "?": "[^/]"}.get(glob[i]) or re.escape(glob[i])
            i += 1
    return re.compile(out)


def literal(glob: str) -> str:
    return re.split(r"[*?]", glob, maxsplit=1)[0]


def shared_patterns(root) -> list[str]:
    """Shared-mechanical paths (SPEC-0034 rule 7a): changelog.d/ and the `merge=union` files."""
    found = ["changelog.d/**"]
    try:
        text = (root / ".gitattributes").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return found
    for line in text.splitlines():
        parts = line.split()
        if len(parts) > 1 and "merge=union" in parts[1:]:
            found.append(parts[0])
    return found


def pull_files(s: Survey, pr: dict) -> list:
    if pr["number"] not in s.files:
        listed = pages(f"repos/{s.repo}/pulls/{pr['number']}/files")
        if listed is None:
            raise CheckError("rule 3: the files of an open pull request cannot be read")
        s.files[pr["number"]] = listed
    return s.files[pr["number"]]


def overlap(root, s: Survey, brief: dict) -> str | None:
    """Why the `Touches:` of the brief overlap open work (rule 3), or None."""
    shared = [glob_regex(p) for p in shared_patterns(root)]
    mine = [
        g for g in touches_of(brief["body"]) if not any(r.fullmatch(literal(g)) for r in shared)
    ]
    for number, theirs in s.held:
        if any(literal(a).startswith(literal(b)) or literal(b).startswith(literal(a))
               for a in mine for b in theirs):  # fmt: skip
            return f"overlaps the taken brief #{number}"
    for pr in s.builders:
        paths = [str(f.get("filename")) for f in pull_files(s, pr)]
        paths = [p for p in paths if not any(r.fullmatch(p) for r in shared)]
        if any(glob_regex(g).fullmatch(p) for g in mine for p in paths):
            return f"overlaps open pull request #{pr['number']}"
    return None


RULE_LINE = re.compile(r"(?m)^\+?(\d+)\. ")


def numbers_in_use(root, s: Survey, exclude: int | None = None) -> dict[str, int]:
    """The highest requirement, spec, ADR and session-rule number taken on the default branch, by
    the files an open builder pull request adds (all but `exclude`, the caller's own, whose numbers
    the caller already holds) and by the reservations of live takes (rule 4)."""
    ref = f"origin/{load_config(root)['default_branch']}"
    base = next_free_ids(root, ref)
    rules = [int(n) for n in RULE_LINE.findall(show(root, ref, RULES_FILE) or "")]
    top = {
        "req": int(base["req"][4:]) - 1,
        "spec": int(base["spec"]) - 1,
        "adr": int(base["adr"]) - 1,
        "rule": max(rules, default=0),
    }
    for pr in s.builders:
        if pr.get("number") == exclude:
            continue
        for entry in pull_files(s, pr):
            if entry.get("filename") == RULES_FILE:
                added = [ln for ln in str(entry.get("patch") or "").splitlines() if ln[:1] == "+"]
                for n in RULE_LINE.findall("\n".join(added)):
                    top["rule"] = max(top["rule"], int(n))
            found = re.fullmatch(r"docs/(adr|specs)/(\d{4})-[^/]+\.md", str(entry.get("filename")))
            if found and entry.get("status") == "added":
                key = "adr" if found.group(1) == "adr" else "spec"
                top[key] = max(top[key], int(found.group(2)))
            if entry.get("filename") == "docs/requirements.md":
                for n in re.findall(r"(?m)^\+### REQ-(\d{3})\b", entry.get("patch") or ""):
                    top["req"] = max(top["req"], int(n))
    kinds = {"REQ": "req", "SPEC": "spec", "ADR": "adr"}
    for number, comments in s.comments.items():
        for live in live_takes(comments, number, s.prs, s.hours):
            for reserved in live[4]:
                kind, _, digits = reserved.partition("-")
                top[kinds[kind]] = max(top[kinds[kind]], int(digits))
    return top


def reservation(root, s: Survey, brief: dict) -> list[str]:
    """The numbers a brief needs: REQ, SPEC and ADR for `Advances: new`, else an ADR."""
    try:
        top = numbers_in_use(root, s)
    except CheckError:
        print("note: the numbers cannot be counted, none is reserved (rule 4)", file=sys.stderr)
        return []
    ids = [f"ADR-{top['adr'] + 1:04d}"]
    if "Advances: new" in [x.rstrip() for x in brief["body"].splitlines()]:
        ids = [f"REQ-{top['req'] + 1:03d}", f"SPEC-{top['spec'] + 1:04d}", *ids]
    return ids


def take(s: Survey, brief: dict, reserve, build: str | None = None, gate=None) -> str | None:
    """Post the take unless this session already holds one; the reason it was lost, or None.
    A take of a build conflicts with a take of the same build and with a take of the whole brief.
    `gate`, when given (`claim`), is asked just before the post and refuses it with its reason."""
    from session_plan import holding  # the plan's reading of a take (brief #345, ADR-0195)

    number, me, comments = brief["number"], s.me, s.comments[brief["number"]]

    def rivals(found: list) -> list:
        found = holding(s, number, found)
        return [t for t in found if build is None or t[5] in (None, build)]

    if not any(t[2] == me and t[5] == build for t in live_takes(comments, number, s.prs, s.hours)):
        if build is not None and (
            other := [t for t in rivals(live_takes(comments, number, s.prs, s.hours)) if t[2] != me]
        ):
            return f"taken by {other[0][2]}"
        if gate is not None and (why := gate()):
            return why
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        body = f"body=taken: {me} {day}" + (f" build ({build})" if build else "")
        if any(not t[5] for t in all_takes(comments)):
            body += " retakes"
        if numbers := reserve():
            body += " reserves " + ", ".join(numbers)
        if gh(f"repos/{s.repo}/issues/{number}/comments", "-f", body, method="POST") is None:
            return "the take cannot be posted"
        comments = pages(f"repos/{s.repo}/issues/{number}/comments") or []
    oldest = rivals(live_takes(comments, number, s.prs, s.hours))
    if oldest and oldest[0][2] != me:
        return f"lost the take to {oldest[0][2]}"
    return None


def mine(root, me: str, pr_number: int | None, brief: int | None) -> int:
    """Brief #424: whether this session holds the work a message names (GET only)."""
    repo = repo_name(root)
    if pr_number is not None:
        pull = gh(f"repos/{repo}/pulls/{pr_number}")
        if not isinstance(pull, dict) or "number" not in pull:
            raise CheckError("rule 5: the pull request cannot be read")
        brief = brief_number(pull)
        if brief is None:
            print(f"not mine: #{pr_number} names no brief")
            return 1
    comments = pages(f"repos/{repo}/issues/{brief}/comments")
    prs = pages(f"repos/{repo}/pulls?state=all")
    if comments is None or prs is None:
        raise CheckError("rule 5: the brief and the pull requests cannot be read")
    takes = live_takes(
        comments, int(brief or 0), prs, flow_int(root, "claim_hours", CLAIM_HOURS, 1)
    )
    if any(t[2] == me for t in takes):
        print("mine")
        return 0
    print(
        f"not mine: #{brief} belongs to {takes[0][2]}"
        if takes
        else f"not mine: #{brief} has no live take"
    )
    return 1


# --- the kind of a brief (SPEC-0045 rule 4, brief #623) ---------------------------------------

# Rule 4's design paths: a directory ends with "/"; `scripts/agk/guard` is the prefix of the guard
# files there (the hooks' guards are under `.claude/hooks/`).
DESIGN_DIRS = ("docs/specs/", "docs/adr/", "constitution/", ".github/", ".claude/hooks/")
DESIGN_FILES = (
    "docs/requirements.md",
    "config/reviewers.yaml",
    "scripts/agk/merge_cleared.py",
    "scripts/agk/route.py",
)
GUARD_PREFIX = "scripts/agk/guard"
# The kit's own test folders, joined so that an installed copy names no kit test path.
TEST_CLASSES = tuple(f"{Path('tests', name).as_posix()}/" for name in ("kit", "kit_dev"))
PROTECTED_LIST = "config/protected-paths.txt"


def may_touch(glob: str, entry: str) -> bool:
    """Whether a `Touches:` glob may match a path of ENTRY (a directory ending with "/", a prefix
    or one file); counting a doubtful glob as matching never lowers a kind (Q-S0045-4)."""
    if entry.endswith("/") or entry == GUARD_PREFIX:
        start = literal(glob)
        return start.startswith(entry) or entry.startswith(start)
    return bool(glob_regex(glob).fullmatch(entry))


def kind_of(body: str, protected: list[str] | None) -> str:
    """Rule 4, in order: an unreadable line or a design path gives `design`, `Size: S` touching
    only unprotected paths and the test folders gives `small`, anything else `build`."""
    lines = [x.rstrip() for x in body.splitlines()]
    sizes = [x for x in lines if x.startswith("Size")]
    touches = [x for x in lines if x.startswith("Touches")]
    found = TOUCHES.fullmatch(touches[0]) if len(touches) == 1 else None
    globs = [g.strip() for g in found.group(1).split(",")] if found else []
    adds = [x for x in lines if x.startswith("Adds:")]
    added = ADDS.fullmatch(adds[0]) if len(adds) == 1 else None
    if adds and not added:
        return "design"
    globs += [g.strip() for g in added.group(1).split(",")] if added else []
    if len(sizes) != 1 or not SIZE.fullmatch(sizes[0]) or not globs or not all(globs):
        return "design"
    design = (*DESIGN_DIRS, *DESIGN_FILES, GUARD_PREFIX)
    if any("guard" in g or any(may_touch(g, e) for e in design) for g in globs):
        return "design"
    if protected is None:
        return "design"  # without the list nothing shows that the brief is small
    others = [e for e in protected if e not in TEST_CLASSES]
    if sizes[0] == "Size: S" and not any(may_touch(g, e) for g in globs for e in others):
        return "small"
    return "build"


def protected_entries(root) -> list[str] | None:
    try:
        text = (root / PROTECTED_LIST).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return [x.strip() for x in text.splitlines() if x.strip() and not x.startswith("#")]


def brief_kind(root, number: int) -> int:
    """`kind --brief N`: one GET; a brief that cannot be read gives `design`, never lower."""
    brief = gh(f"repos/{repo_name(root)}/issues/{number}")
    body = brief.get("body") if isinstance(brief, dict) else None
    print(f"kind: {kind_of(body, protected_entries(root)) if isinstance(body, str) else 'design'}")
    return 0


# --- a build claim, the answer of the conductor and `after` (SPEC-0034 rules 1, 5 and 12) -----


def assign_mode(root) -> str:
    """`assign` of the flow table: `conductor` or `next` (the default); another value is refused."""
    value = flow_value(root, "assign", "next", 1)
    if value not in ASSIGN_MODES:
        raise CheckError("rule 1: assign of the [flow] table must be conductor or next")
    return value


def stale_view(root, s: Survey, number: int) -> None:
    """Read the open briefs and their takes, and judge which sessions are gone, as the plan does
    (brief #345, ADR-0195). A brief or its comments that cannot be read leave nobody gone: an
    old take then still holds, as before."""
    from session_plan import read_gone

    issues = pages(f"repos/{s.repo}/issues?state=open&labels={LABEL}")
    if issues is None:
        return
    for item in issues:
        if "pull_request" in item:
            continue
        s.briefs[item["number"]] = item
        if item["number"] != number:
            found = pages(f"repos/{s.repo}/issues/{item['number']}/comments")
            if found is None:
                return
            s.comments[item["number"]] = found
    read_gone(root, s)


def claim_reservation(root, s: Survey, number: int) -> list[str]:
    """The numbers a `claim` of a whole brief reserves, as `next --take` does (rule 4; the verdict
    on c26b62e of brief #440): read from a survey that sees the open builder pull requests and the
    reservations of every live take. A read that fails reserves nothing, with a note."""
    try:
        seen = survey(root, s.repo, s.me)
        brief = seen.briefs.get(number) or gh(f"repos/{s.repo}/issues/{number}")
        if not isinstance(brief, dict) or not isinstance(brief.get("body"), str):
            raise CheckError("rule 4: the brief cannot be read")
    except CheckError:
        print("note: the numbers cannot be counted, none is reserved (rule 4)", file=sys.stderr)
        return []
    seen.comments[number] = s.comments[number]
    return reservation(root, seen, brief)


def claim_overlap(root, s: Survey, number: int, seen: dict) -> str | None:
    """Why the brief waits for running work, by the judgement `next` and `plan` share (SPEC-0050
    rules 2 to 4), or None. It reads the open briefs and pull requests as `next` does; a read that
    fails stops the claim (CheckError) and never passes as no overlap. The survey is kept in `seen`
    for the reservation, so that the briefs are read once."""
    from session_plan import exempt, read_gone, running_conflict, settle_takes, wait_text

    shared = exempt(root)
    issues = pages(f"repos/{s.repo}/issues?state=open&labels={LABEL}")
    if issues is None:
        raise CheckError("rule 3: the open briefs cannot be read")
    briefs = [i for i in issues if "pull_request" not in i]
    brief = next((i for i in briefs if i.get("number") == number), None)
    brief = brief or gh(f"repos/{s.repo}/issues/{number}")
    if not isinstance(brief, dict) or not isinstance(brief.get("body"), str):
        raise CheckError("rule 3: the brief cannot be read")
    view = survey(root, s.repo, s.me, [i for i in briefs if i.get("number") != number])
    view.prs = s.prs  # the red-branch survey reads none; the overlap needs every open one
    view.builders = [p for p in s.prs if p.get("state") == "open" and brief_number(p) is not None]
    view.briefs[number], view.comments[number] = brief, s.comments[number]
    read_gone(root, view)
    freed, _ = settle_takes(view)
    view.held = [h for h in view.held if h[0] not in freed]
    seen["survey"], seen["brief"] = view, brief
    found = running_conflict(root, view, {**brief, "number": number}, shared)
    return wait_text(found) if found else None


def claim(root, me: str, number: int, build: str | None) -> int:
    repo = repo_name(root)
    comments = pages(f"repos/{repo}/issues/{number}/comments")
    prs = pages(f"repos/{repo}/pulls?state=all")
    if comments is None or prs is None:
        raise CheckError("rule 5: the brief and the pull requests cannot be read")
    if reason := hold_state(root, comments, number)[0]:
        print(f"skip #{number}: {HELD_PREFIX}{reason}")
        return 1
    hours = flow_int(root, "claim_hours", CLAIM_HOURS, 1)
    s = Survey(repo, me, 0, hours, prs, [], {number: comments})
    if any(t[2] != me for t in live_takes(comments, number, prs, hours)):
        stale_view(root, s, number)
    seen: dict = {}

    def reserve() -> list[str]:
        if build is not None:
            return []
        if "survey" in seen:  # the survey of the overlap judgement, read once
            return reservation(root, seen["survey"], seen["brief"])
        return claim_reservation(root, s, number)

    def gate() -> str | None:
        return claim_overlap(root, s, number, seen)

    if why := take(s, {"number": number}, reserve, build, gate):
        print(f"skip #{number}: {why}")
        return 1
    print(f"claimed #{number}" + (f" build ({build})" if build else ""))
    return 0


def conductor_issue(repo: str) -> int:
    found = pages(f"repos/{repo}/issues?state=open&labels={ASSIGN_LABEL}")
    issues = [
        i for i in found or [] if "pull_request" not in i and isinstance(i.get("number"), int)
    ]
    if len(issues) != 1:
        raise CheckError(f"rule 12: exactly one open issue labelled {ASSIGN_LABEL} is needed")
    return issues[0]["number"]


def assign_line(comment: dict, me: str, allowed: set[str]) -> re.Match | None:
    """The `Assign: <me> ...` first line of a comment by a listed author, else None."""
    body = comment.get("body")
    first = body.splitlines()[0].strip() if isinstance(body, str) and body.strip() else ""
    match = ASSIGN.fullmatch(first)
    if match and match.group(1) == me and author_of(comment) in allowed:
        return match
    return None


def spent(repo: str, me: str, line: dict) -> bool | None:
    """Brief #252 answer 2: an early `Assign:` (a brief or `none`) is spent when this session has a
    `taken:` on any brief after it, since a session takes what it was assigned; a stale `none` of
    an earlier session of the same name is then never read as an answer. None when unreadable."""
    since = f"?since={line['created_at']}" if isinstance(line.get("created_at"), str) else ""
    found = pages(f"repos/{repo}/issues/comments{since}")
    if found is None:
        return None
    for comment in found:
        body = str(comment.get("body") or "")
        take_ = TAKE.match(body.splitlines()[0].strip() if body.strip() else "")
        if take_ and take_.group(1) == me and comment.get("id", 0) > line.get("id", 0):
            return True
    return False


def watch_assign(root, me: str, args: dict[str, str]) -> int:
    """`wait_assign`; a slot's run that ends because GitHub cannot be read releases its lease."""
    code = wait_assign(root, me, args)
    if code == EXIT_UNREADABLE and is_slot(root, me) and slot_run(root, me):
        release_slot(root, me)
    return code


def wait_assign(root, me: str, args: dict[str, str]) -> int:
    """End on the first `Assign: <me> ...` by a listed author after this session's `Request:`, or on
    the newest one posted between its previous `Request:` and that one and not yet taken (brief
    #252: the conductor may assign while the session is finishing, and need not post it twice)."""
    repo = repo_name(root)
    issue = conductor_issue(repo)
    path = f"repos/{repo}/issues/{issue}/comments"
    interval = float(args.get("--interval", 60))
    limit = float(args.get("--timeout", flow_int(root, "claim_hours", CLAIM_HOURS, 1) * 3600))
    slotted = is_slot(root, me)  # a slot returns within the bound, so that it renews in time
    limit = min(limit, WATCH_BOUND - interval) if slotted else limit
    held = slotted and bool(slot_run(root, me))
    started = time.monotonic()
    renewed: float | None = None
    renew_reads = Reads(root)  # its own count, as `take_reads` below
    reads = Reads(root)
    while (comments := pages(path)) is None:  # an unread baseline would make an old line look new
        if reads.failed(f"the comments of #{issue}"):
            return EXIT_UNREADABLE
        time.sleep(interval)
    reads.good()
    asked = sorted(
        c["id"] for c in comments if str(c.get("body") or "").startswith(f"Request: {me} ")
    )
    seen = max(asked, default=newest(comments) or 0)
    allowed = {a.lstrip("@").lower() for a in counted_authors(verdict_authors(root), None)}
    print(f"waiting on #{issue} since {seen}", flush=True)
    early = None
    if asked:  # the newest Assign between the previous Request (if any) and the current one
        floor = asked[-2] if len(asked) > 1 else 0
        window = [c for c in comments if floor < c.get("id", 0) < seen]
        lines = [(c, m) for c in window if (m := assign_line(c, me, allowed))]
        early = max(lines, key=lambda x: x[0].get("id", 0), default=None)
    found: list | None = comments
    take_reads = Reads(root)  # its own count: a readable conductor issue never resets it
    told: set[int] = set()  # the `Tell:` lines already printed (brief #327 answer 2)
    while True:
        if held and (renewed is None or time.monotonic() - renewed >= RENEW_EVERY):
            try:
                code, said = quietly(slot_lease, root, "--renew", me)
            except CheckError:
                if renew_reads.failed("the slot's lease"):
                    return EXIT_UNREADABLE
            else:
                renew_reads.good()
                if code:
                    print(said, flush=True)
                    return code
                renewed = time.monotonic()
        if found is None:
            if reads.failed(f"the comments of #{issue}"):
                return EXIT_UNREADABLE
        else:
            reads.good()
        for comment in sorted(found or [], key=lambda c: c.get("id", 0)):
            cid = comment.get("id", 0)
            if cid > seen and cid not in told and (line := tell_line(comment, me, allowed)):
                told.add(cid)
                print(line, flush=True)
        for comment in sorted(found or [], key=lambda c: c.get("id", 0)):
            match = assign_line(comment, me, allowed)
            if comment.get("id", 0) > seen and match:
                print(f"assign {match.group(2)}")
                return 0
        if early is not None:
            used = spent(repo, me, early[0])
            if used is None:
                if take_reads.failed("the comments of the briefs"):
                    return EXIT_UNREADABLE
            elif used:
                take_reads.good()
                early = None
            else:
                print(f"assign {early[1].group(2)}")
                return 0
        if time.monotonic() - started >= limit:
            print("no event" if slotted else "assign-timeout")
            return 0
        time.sleep(interval)
        found = pages(path)


# --- builder slots: the setting, the lease and the next step (brief #776, ADR-0362) ---------------

BUILDER_STARTS = ("start", "assign")
SLOT_SETTING = "(setting: builder_start in the flow table of agk.toml)"
SLOT_NAME = re.compile(r"s([1-9]\d*)")
SLOT_LINE = re.compile(
    r"Slot: (active|released) (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (\S+) (\S+)"
)
POOL_STOP = re.compile(r"Pool: stop(?: .*)?")
SLOT_MINUTES = 10  # ADR-0368: a dead holder is replaced by the next staggered start
WATCH_BOUND = 300  # seconds: a slot's `watch --assign` returns by then with no event (ADR-0368)
RENEW_EVERY = 240  # seconds between renewals during one watch
SLOT_IDLE_MINUTES = 10
SLOT_ENDS = 3  # the exit of a run that must end: no slots, or its slot is another run's


def builder_start(root) -> str:
    """`builder_start` of the flow table: `start` (the default) or `assign`."""
    value = flow_value(root, "builder_start", "start", 1)
    if value not in BUILDER_STARTS:
        raise CheckError("rule 1: builder_start of the [flow] table must be start or assign")
    return value


def builder_slots(root) -> int:
    """`builder_slots` of the flow table, by default `max_builders`."""
    return flow_int(root, "builder_slots", flow_int(root, "max_builders", MAX_BUILDERS, 1), 1)


def slot_marker(comments: list, name: str, allowed: set[str]) -> tuple[dict, re.Match] | None:
    """The oldest `Slot:` marker of a slot by a listed author: two first takes at once post two
    markers, and the oldest decides."""
    for comment in sorted(comments, key=lambda c: c.get("id", 0)):
        match = SLOT_LINE.fullmatch(first_line(comment))
        if match and match.group(3) == name and author_of(comment) in allowed:
            return comment, match
    return None


def slot_holder(found: tuple[dict, re.Match] | None, now: datetime) -> tuple[str, str] | None:
    """(run, end time) of a valid active marker, else None (none, released or expired)."""
    if found is None or found[1].group(1) != "active":
        return None
    end = moment(found[1].group(2)) + timedelta(minutes=SLOT_MINUTES)
    return (found[1].group(4), end.strftime("%Y-%m-%dT%H:%M:%SZ")) if now < end else None


def slot_mark(root, name: str) -> Path:
    """The file in the git directory that holds this checkout's run name for a slot."""
    return inbox_mark(root, name).with_name(f"slot-{name}")


def slot_run(root, name: str) -> str:
    """This checkout's run name for the slot, empty when it has taken none."""
    mark = slot_mark(root, name)
    return mark.read_text(encoding="utf-8").strip() if mark.exists() else ""


def slot_lease(root, mode: str, name: str) -> int:
    """Take, renew or release a slot's lease: one marker comment per slot on the one open
    `agk-conductor` issue, edited in place, valid 10 minutes; this checkout's run name is kept in
    the git directory. A run that finds the slot another's exits 3 and writes nothing."""
    repo = repo_name(root)
    issue = conductor_issue(repo)
    path = f"repos/{repo}/issues/{issue}/comments"
    comments = pages(path)
    if comments is None:
        raise CheckError(f"slot: the comments of #{issue} cannot be read")
    allowed = {a.lstrip("@").lower() for a in counted_authors(verdict_authors(root), None) or []}
    now = datetime.now(UTC)
    found = slot_marker(comments, name, allowed)
    holder = slot_holder(found, now)
    mark = slot_mark(root, name)
    run = slot_run(root, name)
    if holder and holder[0] != run:
        print(f"slot: {name} held by {holder[0]} until {holder[1]} {SLOT_SETTING}")
        return SLOT_ENDS
    state, stamp = "active", now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if mode == "--release":
        state = "released"
        if holder is None:
            mark.unlink(missing_ok=True)
            print(f"slot: {name} free")
            return 0
    elif mode == "--renew" and not (
        run and found and found[1].group(1) == "active" and found[1].group(4) == run
    ):
        print(f"slot: {name} is not held by this run {SLOT_SETTING}")
        return SLOT_ENDS
    run = run or secrets.token_hex(4)
    text = f"body=Slot: {state} {stamp} {name} {run}"
    done = (
        gh(f"repos/{repo}/issues/comments/{found[0].get('id')}", "-f", text, method="PATCH")
        if found
        else gh(path, "-f", text, method="POST")
    )
    if done is None:
        raise CheckError(f"slot: the marker on #{issue} cannot be written")
    if mode == "--release":
        mark.unlink(missing_ok=True)
        print(f"slot: {name} released")
        return 0
    mark.parent.mkdir(parents=True, exist_ok=True)
    mark.write_text(f"{run}\n", encoding="utf-8")
    if mode == "--take":
        again = pages(path)  # two runs at the same moment: the marker read back decides
        if again is None:
            raise CheckError(f"slot: the comments of #{issue} cannot be read")
        won = slot_marker(again, name, allowed)
        if won is None or won[1].group(4) != run:
            mark.unlink(missing_ok=True)
            print(f"slot: {name} held by another run {SLOT_SETTING}")
            return SLOT_ENDS
    print(f"slot: {name} {'taken' if mode == '--take' else 'renewed'} by {run}")
    return 0


def owned_pulls(root, repo: str, name: str) -> list:
    """The open builder pull requests whose brief this slot has a live take of (session rule 3)."""
    prs = pages(f"repos/{repo}/pulls?state=all")
    if prs is None:
        raise CheckError("slot: the pull requests cannot be read")
    hours = flow_int(root, "claim_hours", CLAIM_HOURS, 1)
    owned = []
    for pull in sorted(prs, key=lambda p: p.get("number", 0)):
        brief = brief_number(pull)
        if brief is None or pull.get("state") != "open":
            continue
        comments = pages(f"repos/{repo}/issues/{brief}/comments")
        if comments is None:
            raise CheckError(f"slot: the comments of #{brief} cannot be read")
        if any(t[2] == name for t in live_takes(comments, brief, prs, hours)):
            owned.append(pull)
    return owned


def reports_after(repo: str, number: int, floor: int) -> bool:
    """Whether pull request `number` has a `Report:` comment newer than the comment id `floor`."""
    comments = pages(f"repos/{repo}/issues/{number}/comments")
    if comments is None:
        raise CheckError(f"slot: the comments of #{number} cannot be read")
    return any(first_line(c).startswith("Report:") and c.get("id", 0) > floor for c in comments)


def follow_up_owed(repo: str, pull: dict, allowed: set[str]) -> str | None:
    """`conflict`, `fix list` (the newest verdict, with no `Report:` after it) or None."""
    number = pull.get("number")
    full = gh(f"repos/{repo}/pulls/{number}")
    if not isinstance(full, dict):
        raise CheckError(f"slot: #{number} cannot be read")
    if full.get("mergeable_state") == "dirty":
        return "conflict"
    comments = pages(f"repos/{repo}/issues/{number}/comments")
    if comments is None:
        raise CheckError(f"slot: the comments of #{number} cannot be read")
    verdicts = [
        (c.get("id", 0), m.group(1))
        for c in comments
        if author_of(c) in allowed and (m := VERDICT.match(first_line(c)))
    ]
    if not verdicts or max(verdicts)[1] != "fix list":
        return None
    return None if reports_after(repo, int(number or 0), max(verdicts)[0]) else "fix list"


def slot_next(root, name: str) -> int:
    """One pass of a slot's loop: renew the lease, then print its one next step as the last line:
    `stop`, `follow-up pr #n <why>`, `assign #b [build (x)]`, `wait pr #n`, `take` (`next --take`,
    after 10 minutes with no `Assign:`), `wait`, or `request` (no `Request:` or `Assign:` yet)."""
    if code := slot_lease(root, "--renew", name):
        return code
    repo = repo_name(root)
    issue = conductor_issue(repo)
    comments = pages(f"repos/{repo}/issues/{issue}/comments")
    if comments is None:
        raise CheckError(f"slot: the comments of #{issue} cannot be read")
    allowed = {a.lstrip("@").lower() for a in counted_authors(verdict_authors(root), None) or []}
    approvers = {a.lstrip("@").lower() for a in spec_approvers(root)}
    if any(POOL_STOP.fullmatch(first_line(c)) and author_of(c) in approvers for c in comments):
        release_slot(root, name)  # every exit of a run releases its lease (ADR-0368)
        print("stop")
        return 0
    owned = owned_pulls(root, repo, name)
    for pull in owned:
        if why := follow_up_owed(repo, pull, allowed):
            print(f"follow-up pr #{pull.get('number')} {why}")
            return 0
    lines = [(c, m) for c in comments if (m := assign_line(c, name, allowed))]
    if lines:
        line, match = max(lines, key=lambda x: x[0].get("id", 0))
        if match.group(5):
            if not reports_after(repo, int(match.group(5)), line.get("id", 0)):
                print(f"follow-up pr #{match.group(5)} {match.group(6)}")
                return 0
        elif match.group(2) != "none" and not owned:
            used = spent(repo, name, line)
            if used is None:
                raise CheckError("slot: the comments of the briefs cannot be read")
            if not used:
                print(f"assign {match.group(2)}")
                return 0
    if owned:
        print(f"wait pr #{owned[0].get('number')}")
        return 0
    asked = [c for c in comments if str(c.get("body") or "").startswith(f"Request: {name} ")]
    times = [moment(c["created_at"]) for c in [*asked, *(x[0] for x in lines)]]
    if not times:
        print("request")
    elif datetime.now(UTC) - max(times) >= timedelta(minutes=SLOT_IDLE_MINUTES):
        print("take")
    else:
        print("wait")
    return 0


def quietly(act, *args) -> tuple[int, str]:
    """The exit of a lease action and what it printed, kept off a watch's own output."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = act(*args)
    return code, out.getvalue().strip()


def release_slot(root, name: str) -> None:
    """Release the slot on a run's way out; a release that cannot be written is left to expire."""
    with contextlib.suppress(CheckError):
        quietly(slot_lease, root, "--release", name)


def is_slot(root, me: str) -> bool:
    """Whether this session is a slot of the pool (`builder_start = "assign"`, the name `s<n>`)."""
    return bool(SLOT_NAME.fullmatch(me)) and builder_start(root) == "assign"


def slot(root, mode: str, name: str) -> int:
    """`slot --take|--renew|--release|--next <slot>`; with `builder_start = "start"` there are no
    slots: it says so, calls nothing and exits 3, so that a slot run ends at once."""
    if builder_start(root) != "assign":
        print(f"slot: off {SLOT_SETTING}")
        return SLOT_ENDS
    number = SLOT_NAME.fullmatch(name)
    if number is None or int(number.group(1)) > builder_slots(root):
        raise CheckError(
            "slot: the name is not one of the slots (setting: builder_slots in the flow table)"
        )
    return slot_next(root, name) if mode == "--next" else slot_lease(root, mode, name)


# --- messages to a session (brief #327) ----------------------------------------------------------


def tell_problem(text: str) -> str | None:
    """Why a message cannot be sent (brief #327 answer 1), naming the rule and never the text: it
    is one line (no line break that `str.splitlines` knows), and zero-width characters do not hide a
    refused start (the verdict on 0e12557)."""
    if not text.strip() or text.splitlines() != [text] or len(text) > TELL_LIMIT:
        return f"tell: the message is one line of 1 to {TELL_LIMIT} characters"
    if TELL_REFUSED.match(ZERO_WIDTH.sub("", text)):
        return "tell: a message never starts with Approve:, Confirmed: or Verdict:"
    return None


def tell(root, me: str, text: str) -> int:
    """Post one comment `Tell: <session> <message>` on the one open `agk-conductor` issue."""
    if problem := tell_problem(text):
        raise CheckError(problem)
    repo = repo_name(root)
    issue = conductor_issue(repo)
    body = f"body=Tell: {me} {text}"
    if gh(f"repos/{repo}/issues/{issue}/comments", "-f", body, method="POST") is None:
        raise CheckError(f"tell: the comment on #{issue} could not be posted")
    print(f"told {me} on #{issue}")
    return 0


def tell_line(comment: dict, me: str, allowed: set[str]) -> str | None:
    """The `Tell: <me> <message>` first line of a comment by a listed author, else None."""
    body = comment.get("body")
    text = plain(body) if isinstance(body, str) else ""
    first = text.splitlines()[0].strip() if text.strip() else ""
    match = TELL.fullmatch(first)
    if match and match.group(1) == me and author_of(comment) in allowed:
        return first
    return None


def last_request(comments: list, me: str) -> int:
    """The id of this session's newest `Request:` comment, 0 without one."""
    return max(
        (
            c.get("id", 0)
            for c in comments
            if str(c.get("body") or "").startswith(f"Request: {me} ")
        ),
        default=0,
    )


def inbox_mark(root, me: str) -> Path:
    """The file in the git directory that holds the id of the last message the inbox printed
    (never tracked, never pushed)."""
    found = git(root, "rev-parse", "--git-dir").strip()
    base = Path(found) if Path(found).is_absolute() else Path(root) / found
    return base / "agk" / f"inbox-{me}"


def inbox(root, me: str) -> int:
    """Print the `Tell:` lines for this session posted since its last `Request:` or since the
    inbox last printed one, oldest first, or `no message` (GET only; brief #327 answer 2)."""
    lines = unread(root, me)
    for line in lines:
        print(line)
    if not lines:
        print("no message")
    return 0


def unread(root, me: str) -> list[str]:
    """The unread `Tell:` lines of `inbox`, oldest first; the mark moves past the newest."""
    repo = repo_name(root)
    issue = conductor_issue(repo)
    comments = pages(f"repos/{repo}/issues/{issue}/comments")
    if comments is None:
        raise CheckError(f"tell: the comments of #{issue} cannot be read")
    mark = inbox_mark(root, me)
    try:
        read = int(mark.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        read = 0
    floor = max(read, last_request(comments, me))
    allowed = {a.lstrip("@").lower() for a in counted_authors(verdict_authors(root), None)}
    lines = [
        (c.get("id", 0), line)
        for c in sorted(comments, key=lambda c: c.get("id", 0))
        if c.get("id", 0) > floor and (line := tell_line(c, me, allowed))
    ]
    if lines:
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.write_text(f"{lines[-1][0]}\n", encoding="utf-8")
    return [line for _, line in lines]


def is_red(item: dict) -> bool:
    """The brief the router writes while the default branch is red (SPEC-0032 rule 7): the title,
    the `Priority: 0` line and the router's token as the author, so that nobody can stop all other
    work by writing an issue of the same shape by hand."""
    lines = (x.rstrip() for x in str(item.get("body") or "").splitlines())
    author = (item.get("user") or {}).get("login")
    return (
        "pull_request" not in item
        and item.get("title") == RED_TITLE
        and author == ROUTER_LOGIN
        and ROUTER_PAIR[1] in lines
    )


def next_brief(root, me: str, taking: bool = False) -> int:
    """The work `next` would hand this session, with the same choice and reasons either way.
    Without `taking` it only shows it and posts nothing, with the command that takes it; with
    `taking` (`next --take`, and `after`) it takes it as before (brief #440, ADR-0236)."""
    repo = repo_name(root)
    issues = pages(f"repos/{repo}/issues?state=open&labels={LABEL}")
    red = [i for i in issues or [] if is_red(i)]
    if not red and (found := offer_stalled(root, repo, me, taking)) is not None:
        return found
    if issues is None:
        raise CheckError("rule 3: the open briefs cannot be read")
    s = survey(root, repo, me, issues)
    if len(s.builders) >= s.max_builders:
        print(f"full {len(s.builders)}/{s.max_builders}")
        return 1
    # The plan's rules decide (brief #345, ADR-0195): a stale claim holds nothing, overlap is
    # judged by files, and a skip names the plan's reason.
    from session_plan import exempt, read_gone, running_conflict, settle_takes, wait_text

    shared = exempt(root)  # SPEC-0050 rules 2 and 3: the one list `plan` and `claim` judge with
    read_gone(root, s)
    freed, s.skipped = settle_takes(s)
    s.held = [h for h in s.held if h[0] not in freed]
    for number, why in s.skipped:
        print(f"skip #{number}: {why}")
    ready = [*s.free, *(s.briefs[n] for n in sorted(freed))]
    for brief in sorted(ready, key=lambda b: (priority_of(b["body"]), b["number"])):
        found = running_conflict(root, s, brief, shared)
        why = wait_text(found) if found else None
        if taking:
            why = why or take(s, brief, lambda b=brief: reservation(root, s, b))
        if why:
            print(f"skip #{brief['number']}: {why}")
            continue
        print(f"brief #{brief['number']}\ntitle: {brief.get('title')}")
        print(f"address: {brief.get('html_url')}\n")
        print(brief["body"])
        if not taking:
            print(f"\ntake it with: session.py claim --session {me} --brief {brief['number']}")
        return 0
    print("default branch red" if red else "no brief")
    return 1


def after(root, me: str) -> int:
    """Where a builder goes when its work is done, by `[flow] assign` (rule 12), after the unread
    `Tell:` lines of the inbox, with its mark (brief #368 answer 2). An inbox that cannot be read
    is said in one line and never shown as an empty one; `after` then goes on."""
    mode = assign_mode(root)
    try:
        for line in unread(root, me):
            print(line)
    except CheckError as exc:
        print(exc)
    if mode == "next":
        return next_brief(root, me, True)  # a finished builder starts its next brief (answer 3)
    print(f"ask the conductor on #{conductor_issue(repo_name(root))}")
    return 0


def demand(root) -> int:
    """How many sessions a launcher may start (rule 6): min(ready, max - open), 0 when negative."""
    s = survey(root, repo_name(root), "")
    ready = sum(1 for brief in s.free if overlap(root, s, brief) is None)
    start = max(0, min(ready, s.max_builders - len(s.builders)))
    figures = {"ready": ready, "open": len(s.builders), "max": s.max_builders, "start": start}
    print(json.dumps(figures))
    return 0


def ids(root, exclude: int | None = None) -> int:
    """The next free requirement, spec, ADR and session-rule numbers as one JSON line."""
    top = numbers_in_use(root, survey(root, repo_name(root), ""), exclude)
    print(
        json.dumps(
            {
                "req": f"REQ-{top['req'] + 1:03d}",
                "spec": f"{top['spec'] + 1:04d}",
                "adr": f"{top['adr'] + 1:04d}",
                "rule": top["rule"] + 1,
            }
        )
    )
    return 0


def push_check(root) -> int:
    """Try the merge of the head with the default branch (rule 7b); exit 1 naming the files."""
    ref = f"origin/{load_config(root)['default_branch']}"
    fetched = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "fetch", "-q", "origin", ref.split("/", 1)[1]], cwd=root, capture_output=True
    )
    tried = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "merge-tree", "--write-tree", "--name-only", "HEAD", ref],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if fetched.returncode != 0 or tried.returncode not in (0, 1):
        raise CheckError("rule 7: the merge with the default branch cannot be tried")
    if tried.returncode == 0:
        return 0
    names = (tried.stdout.split("\n\n")[0].splitlines())[1:]
    print("conflict: " + ", ".join(names))
    return 1


# --- tidy (brief #548, ADR-0272) -------------------------------------------------------------


@dataclass
class TidyItem:
    """A linked worktree with its branch, or a local branch alone (`path` None); `kept` is the
    reason it stays, None for a candidate."""

    path: str | None
    branch: str
    pr: int | None = None
    state: str = ""
    head: str = ""
    kept: str | None = None
    main: bool = False
    locked: bool = False


def run_git(cwd, *args: str) -> tuple[int, str]:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )
    return proc.returncode, proc.stdout


def same_place(a: str | Path, b: str | Path) -> bool:
    """Long and 8.3 Windows forms of one folder are the same place (#508)."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def worktrees_of(root) -> list[TidyItem]:
    """`git worktree list --porcelain`: the first entry is the main clone."""
    code, out = run_git(root, "worktree", "list", "--porcelain")
    if code != 0:
        raise CheckError("answer 1: the worktrees cannot be read (path class: git worktree list)")
    found: list[TidyItem] = []
    for block in out.strip().split("\n\n"):
        fields = dict((line + " ").split(" ", 1) for line in block.splitlines())
        if "worktree" not in fields:
            continue
        branch = fields.get("branch", "").strip().removeprefix("refs/heads/")
        found.append(TidyItem(fields["worktree"].strip(), branch, locked="locked" in fields))
    if found:
        found[0].main = True
    return found


def running_records(base: Path, limit: int) -> list[dict]:
    """Live lock owner records (`lock.py`) and queue jobs (`heavy_queue.py`) beside the heavy
    lock; an owner file that cannot be read counts as a live record of an unknown session."""
    import heavy_queue
    import lock

    found: list[dict] = []
    for held in sorted(base.glob("agk-lock-*")):
        owner = lock.read_owner(held)
        if lock.stale_reason(owner, held, limit) is None:
            found.append(owner or {"session": ""})
    for folder in sorted(base.glob(".agk-lock-*.queue")):
        found += heavy_queue.jobs(folder)
    return found


def names_item(record: dict, item: TidyItem) -> bool:
    """A record names an item by its session (ADR-0272 decision 3, Q-548-1), a job also by its
    branch or folder; a record with no session names every item."""
    session = str(record.get("session") or "")
    if not session or record.get("branch") == item.branch:
        return True
    folder = record.get("folder")
    if folder and item.path and (same_place(folder, item.path) or item.path in str(folder)):
        return True
    names = {item.branch, item.branch.rsplit("/", 1)[-1]}
    if item.path:
        names.add(Path(item.path).name)
    digits = set(re.findall(r"\d+", session)) & set(re.findall(r"\d+", item.branch))
    return session in names or bool(item.path and session in item.path) or bool(digits)


def pull_verdict(item: TidyItem, pulls: Any, tip: str | None) -> str | None:
    """Answer 2 against the branch's pull requests; the reason kept, or None for a candidate."""
    if not isinstance(pulls, list) or not all(isinstance(p, dict) for p in pulls):
        return "could not read GitHub"
    mine = [p for p in pulls if (p.get("head") or {}).get("ref") == item.branch]
    if any(p.get("state") != "closed" for p in mine):
        return "open pull request"
    if not mine:
        return "no pull request"
    last = max(mine, key=lambda p: p.get("number") or 0)
    item.pr, item.head = last.get("number"), str((last.get("head") or {}).get("sha") or "")
    item.state = "merged" if last.get("merged_at") else "closed"
    if tip is None:
        return "could not read the branch"
    return None if tip == item.head and len(tip) == 40 else "commits after the pull request's head"


def branch_tip(root, branch: str) -> str | None:
    code, out = run_git(root, "rev-parse", "--verify", "-q", f"refs/heads/{branch}^{{commit}}")
    return out.strip() if code == 0 else None


TIDY_DEFAULTS: dict[str, Any] = {
    "branch_prefix": "claude/brief-",
    "min_idle_minutes": 60,
    "caches": ["__pycache__/", ".pytest_cache/", ".ruff_cache/", ".mypy_cache/", ".venv/",
               "node_modules/"],
}  # fmt: skip


def tidy_settings(root) -> dict:
    """The `[tidy]` table of agk.toml (the fix list of 0085062): the builders' branch prefix
    (a branch is a builder's when the prefix is followed by a number), the idle minutes, and the
    ignored folders that are caches (the list replaces the default one). A wrong value or key is
    a refusal naming the setting."""
    table = config_source(root).get("tidy")
    found = {k: list(v) if isinstance(v, list) else v for k, v in TIDY_DEFAULTS.items()}
    if table is None:
        return found
    if not isinstance(table, dict):
        raise CheckError("tidy must be a table of tidy's settings (setting: [tidy])")
    for key, value in table.items():
        if key == "branch_prefix":
            ok = isinstance(value, str) and bool(value.strip())
        elif key == "min_idle_minutes":
            ok = isinstance(value, int) and not isinstance(value, bool) and value >= 1
        elif key == "caches":
            ok = isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)
        else:
            raise CheckError(f"[tidy] holds only tidy's settings (setting: [tidy] {key})")
        if not ok:
            raise CheckError(f"{key} has the wrong kind of value (setting: [tidy] {key})")
        found[key] = value
    return found


def is_builder(branch: str, prefix: str) -> bool:
    return branch.startswith(prefix) and branch[len(prefix) :].isdigit()


def worktree_state(path: str, caches: list[str]) -> str | None:
    """`git status --porcelain --ignored`: anything not ignored is unsaved work, and an ignored path
    with no cache folder in it would be lost by `git worktree remove` (fix list item 1)."""
    args = ("status", "--porcelain", "-z", "--ignored=matching", "--untracked-files=all")
    code, out = run_git(path, *args)
    if code != 0:
        return "could not read the worktree"
    entries = [e for e in out.split("\0") if e]
    if any(not e.startswith("!! ") for e in entries):
        return "uncommitted files"
    names = {c.strip().strip("/") for c in caches}
    if any(not names & set(e[3:].rstrip("/").split("/")) for e in entries):
        return "ignored files"
    return None


def newest_change(path: str) -> float | None:
    """The newest of the worktree's last commit time and the change time of every file and folder
    in it (`.git` aside); None when any of it cannot be read (fix list item 3)."""
    code, out = run_git(path, "log", "-1", "--format=%ct", "HEAD")
    if code != 0 or not out.strip().isdigit():
        return None
    newest = float(out.strip())
    try:
        newest = max(newest, os.lstat(path).st_mtime)
        for folder, dirs, names in os.walk(path, onerror=raise_error):
            if Path(folder) == Path(path) and ".git" in dirs + names:
                dirs[:] = [d for d in dirs if d != ".git"]
                names = [n for n in names if n != ".git"]
            for entry in dirs + names:
                newest = max(newest, os.lstat(Path(folder) / entry).st_mtime)
    except OSError:
        return None
    return newest


def raise_error(error: OSError) -> None:
    raise error


def tidy_items(root, read_pulls, records: list[dict], here, now=None) -> list[TidyItem]:
    """Every linked worktree and local branch with its reason kept (answer 3) or none."""
    settings = tidy_settings(root)
    now = time.time() if now is None else now
    items = worktrees_of(root)
    code, out = run_git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    if code != 0:
        raise CheckError("answer 1: the branches cannot be read (path class: git for-each-ref)")
    held = {i.branch for i in items}
    default = load_config(root)["default_branch"]
    items += [TidyItem(None, b) for b in out.split() if b not in held]
    for item in items:
        if item.main:
            item.kept = "main clone"
        elif item.path and same_place(item.path, here):
            item.kept = "current worktree"
        elif item.locked:
            item.kept = "locked"
        elif not item.branch:
            item.kept = "no branch"
        elif item.branch == default:
            item.kept = "default branch"
        elif not is_builder(item.branch, settings["branch_prefix"]):
            item.kept = "not a builder branch"
        elif item.path and (state := worktree_state(item.path, settings["caches"])):
            item.kept = state
        elif item.path and (changed := newest_change(item.path)) is None:
            item.kept = "could not read the worktree"
        elif item.path and now - changed < settings["min_idle_minutes"] * 60:
            item.kept = "recently active"
        elif any(names_item(r, item) for r in records):
            item.kept = "running"
        else:
            item.kept = pull_verdict(item, read_pulls(item.branch), branch_tip(root, item.branch))
    return items


def removal_commands(root: str, item: TidyItem) -> list[list[str]]:
    """Answer 4: argument lists, never a shell string, the path as git listed it; never --force."""
    base = ["git", "-C", root]
    worktree = [[*base, "worktree", "remove", item.path], [*base, "worktree", "prune"]]
    return (worktree if item.path else []) + [[*base, "branch", "-D", item.branch]]


def tidy_apply(root, items: list[TidyItem]) -> list[str]:
    """Remove the candidates; a failed step keeps the item, and the tip is read again before -D."""
    lines = []
    for item in (i for i in items if i.kept is None):
        where = f"{item.path or '-'} {item.branch}"
        *trees, drop = removal_commands(str(root), item)
        if branch_tip(root, item.branch) != item.head:
            lines.append(f"kept: commits after the pull request's head ({where})")
            continue
        failed = any(run_git(None, *c[1:])[0] != 0 for c in trees)  # stops at the first failure
        if failed or branch_tip(root, item.branch) != item.head or run_git(None, *drop[1:])[0]:
            lines.append(f"kept: removal failed ({where})")
            continue
        lines.append(f"removed {where} #{item.pr} {item.state}")
    return lines


def github_pulls(repo: str):
    owner = repo.split("/", 1)[0]
    return lambda branch: gh(f"repos/{repo}/pulls?head={owner}:{quote(branch)}&state=all")


def live_records(root) -> list[dict]:
    """The records beside the heavy lock; when they cannot be read every item counts as running."""
    import lock

    try:
        return running_records(lock.lock_folder(root, "heavy").parent, lock.stale_minutes(root))
    except (lock.Usage, OSError, ValueError):
        return [{"session": ""}]


def tidy(root, apply: bool, as_json: bool) -> int:
    items = tidy_items(root, github_pulls(repo_name(root)), live_records(root), repo_root())
    done = tidy_apply(root, items) if apply else []
    planned = [
        f"remove {i.path or '-'} {i.branch} #{i.pr} {i.state}" for i in items if i.kept is None
    ]
    kept = [f"kept: {i.kept} ({i.path or '-'} {i.branch})" for i in items if i.kept]
    if as_json:
        keys = ("path", "branch", "pr", "state", "kept")
        rows = [{**{k: getattr(i, k) for k in keys}, "action": "kept" if i.kept else "remove"}
                for i in items]  # fmt: skip
        print(json.dumps({"apply": apply, "items": rows, "done": done}, indent=2))
        return 0
    print(
        "\n".join((done or planned) + kept + [f"tidy: {len(planned)} finished, {len(kept)} kept"])
    )
    return 0


# --- paused (brief #348 build (c), ADR-0218) -------------------------------------------------


def paused_default(root) -> bool:
    """True when agk.toml of the default branch sets `paused = true` (Q-348-2): read at
    `origin/<default_branch>` (rule 33 fetches it), or in the checkout when that ref is absent."""
    ref = f"origin/{load_config(root)['default_branch']}"
    return paused(root, ref) if _verify(root, ref) is not None else paused(root)


# --- queue (SPEC-0032 rule 3) -----------------------------------------------------------------


def queue(root, role: str, author: str | None) -> int:
    repo = repo_name(root)
    found = pages(f"repos/{repo}/pulls?state=open")
    if found is None:
        raise CheckError("rule 3: the open pull requests cannot be read")
    me = (author or "").lstrip("@").lower()
    lines = []
    for pr in sorted(
        (p for p in found if isinstance(p.get("number"), int)), key=lambda p: p["number"]
    ):
        label = label_of(pr)
        if label not in ROLES[role] or (role == "conductor" and pr.get("draft")):
            continue
        if me and author_of(pr) != me:
            continue
        lines.append(f"#{pr['number']} {label}")
    print("\n".join(lines) if lines else "empty")
    return 0


# --- review-queue (brief 306) -----------------------------------------------------------------

TRIGGERS = ("Question:", "Report:", "Correction:", "Maintainer answer:")
RUNNING_LABEL = "agk:ci-running"


def stamp(comment: dict) -> str:
    """When a comment last changed: its edit time, else its creation time (ISO, sortable)."""
    return str(comment.get("updated_at") or comment.get("created_at") or "")


def last_verdict(comments: list, authors: list[str] | None) -> dict | None:
    """The latest verdict comment by a counted author, by creation time then id."""
    allowed = {a.lstrip("@").lower() for a in authors or []}
    found = [
        c
        for c in comments
        if author_of(c) in allowed
        and isinstance(c.get("body"), str)
        and c["body"].strip()
        and HEAD_VERDICT.fullmatch(c["body"].splitlines()[0].strip())
    ]
    found.sort(key=lambda c: (str(c.get("created_at") or ""), c.get("id") or 0))
    return found[-1] if found else None


def since_verdict(comments: list, mark: dict) -> list[str]:
    """`<Kind>: comment <id> since the last verdict` for each trigger comment created or edited
    after the verdict `mark`."""
    floor = (str(mark.get("created_at") or ""), mark.get("id") or 0)
    out = []
    for c in sorted(comments, key=lambda c: c.get("id") or 0):
        body = c.get("body")
        if not isinstance(body, str) or not body.strip() or c is mark:
            continue
        first = body.splitlines()[0].strip()
        kind = next((t for t in TRIGGERS if first.startswith(t)), None)
        if kind and (stamp(c), c.get("id") or 0) > floor:
            out.append(f"{kind} comment {c.get('id')} since the last verdict")
    return out


def draft_question(comments: list, mark: dict | None) -> bool:
    """A `Question:` comment created or edited after the verdict `mark`, or any one when there is
    no verdict (brief 350)."""
    floor = (str(mark.get("created_at") or ""), mark.get("id") or 0) if mark else ("", 0)
    for c in comments:
        body = c.get("body")
        if c is mark or not isinstance(body, str) or not body.strip():
            continue
        if body.splitlines()[0].strip().startswith("Question:"):
            if not mark or (stamp(c), c.get("id") or 0) > floor:
                return True
    return False


def check_state(repo: str, root, head: str) -> tuple[str, list]:
    """(`green`, `red`, `running` or `missing`, the facts of the checks) of a head, as the router
    judges it: the latest run of each check and status of each context named in `required_checks`.
    `running` is a required run queued or in progress or a required status pending; `missing` is a
    required check that has not reported at all (a project whose workflows are off)."""
    from route import FAILED_RUN, FAILED_STATUS, judged, listing  # route imports this module

    checks = listing(f"repos/{repo}/commits/{head}/check-runs", "check_runs")
    status = gh(f"repos/{repo}/commits/{head}/status")
    if checks is None or not isinstance(status, dict):
        raise CheckError("rule 3: the checks of an open pull request cannot be read")
    runs, statuses, missing = judged(checks, status.get("statuses") or [], required_checks(root))
    seen = sorted(
        [[str(r.get("name")), str(r.get("status")), str(r.get("conclusion"))] for r in runs]
        + [[str(s.get("context")), str(s.get("state")), ""] for s in statuses]
    )
    if any(r.get("conclusion") in FAILED_RUN for r in runs) or any(
        s.get("state") in FAILED_STATUS for s in statuses
    ):
        return "red", seen
    done = all(r.get("status") == "completed" for r in runs) and all(
        s.get("state") != "pending" for s in statuses
    )
    if not done:
        return "running", seen
    return ("missing" if missing or not (runs or statuses) else "green"), seen


def auto_merge_on(root) -> bool:
    """`[flow] auto_merge` is on at the default branch of the remote as last fetched, read as
    `merge_cleared.py` reads it (SPEC-0039 rule 9); a setting that cannot be read is off."""
    import merge_cleared  # the one reading of the setting (brief #531)

    try:
        _, data = merge_cleared.default_ref(Path(root))
        return merge_cleared.auto_merge_setting(data) == "on"
    except CheckError:
        return False


def cleared_unmerged(comments: list, head: str) -> bool:
    """The latest `Verdict:` comment clears exactly this head, as `merge_cleared.py` reads it."""
    import merge_cleared

    latest = merge_cleared.latest_verdict(comments)
    return latest is not None and merge_cleared.first_line(latest) == f"Verdict: cleared {head}"


def review_line(
    repo: str, root, pr: dict, authors: list[str], auto: bool = False
) -> tuple[str, list, list]:
    """(`review`, `skip` or, with AUTO (`auto_merge` on, brief #531), `cleared`, the reasons, the
    facts for the fingerprint) of one open pull request."""
    number, head = pr["number"], str((pr.get("head") or {}).get("sha") or "")
    label = label_of(pr)
    comments = pages(f"repos/{repo}/issues/{number}/comments")
    if comments is None:
        raise CheckError("rule 3: the comments of an open pull request cannot be read")
    times = [[c.get("id"), stamp(c)] for c in sorted(comments, key=lambda c: c.get("id") or 0)]
    if pr.get("draft"):  # brief 350: only a new question lists a draft; its checks are not read
        counted = counted_authors(authors, (pr.get("user") or {}).get("login"))
        if draft_question(comments, last_verdict(comments, counted)):
            return "review", ["question on a draft"], [times]
        return "skip", ["draft"], [times]
    state, seen = check_state(repo, root, head)
    facts = [times, seen]
    if state == "running" or (label == RUNNING_LABEL and state == "missing"):
        return "skip", ["checks running"], facts
    mark = last_verdict(comments, counted_authors(authors, (pr.get("user") or {}).get("login")))
    match = HEAD_VERDICT.fullmatch(mark["body"].splitlines()[0].strip()) if mark else None
    sha = (match.group(2) or "") if match else ""
    asked = since_verdict(comments, mark) if mark else []
    if sha and head.startswith(sha) and not asked:
        if auto and cleared_unmerged(comments, head):
            return "cleared", ["not merged"], facts
        return "skip", [f"verdict on this head (comment {mark['id']})"], facts
    reasons = ["labelled agk:review"] if label == "agk:review" else []
    reasons += asked
    if not mark:
        reasons.append("no verdict yet")
    elif not (sha and head.startswith(sha)):
        reasons.append(f"head differs from the last verdict ({sha[:7] or 'no sha'})")
    if label == RUNNING_LABEL and state == "green":
        reasons.append("checks green under a stale agk:ci-running")
    if state == "missing":
        reasons.append("checks not reported")
    return "review", reasons, facts


REQUEST = re.compile(r"Request: (\S+) \S.*")
NOT_ANSWERS = ("Question:", "taken:", "released:", "taken over:")  # a session's own lines


def first_line(comment: dict) -> str:
    body = comment.get("body")
    return body.splitlines()[0].strip() if isinstance(body, str) and body.strip() else ""


def labelled(issues: list, label: str) -> list:
    """The issues (not pull requests) of a list that carry the label."""
    return [
        i
        for i in issues
        if isinstance(i.get("number"), int)
        and "pull_request" not in i
        and label in {str(x.get("name")) for x in i.get("labels") or [] if isinstance(x, dict)}
    ]


def waiting_requests(repo: str, authors: list[str]) -> tuple[list[str], list]:
    """Brief 408 answer 1: each `Request: <session> ...` on the one open `agk-conductor` issue with
    no `Assign: <session> ...` by a listed author after it, as a line and as a fact. No such
    issue means no request (a project with `assign = "next"`); two or more fail, as
    `watch --assign` does (Q-408-2)."""
    found = pages(f"repos/{repo}/issues?state=open&labels={ASSIGN_LABEL}")
    if found is None:
        raise CheckError(f"rule 3: the open issues labelled {ASSIGN_LABEL} cannot be read")
    open_ = labelled(found, ASSIGN_LABEL)
    if not open_:
        return [], []
    if len(open_) > 1:
        raise CheckError(f"rule 12: exactly one open issue labelled {ASSIGN_LABEL} is needed")
    comments = pages(f"repos/{repo}/issues/{open_[0]['number']}/comments")
    if comments is None:
        raise CheckError(
            f"rule 3: the comments of the issue labelled {ASSIGN_LABEL} cannot be read"
        )
    allowed = {a.lstrip("@").lower() for a in authors}
    ordered = sorted((c for c in comments if isinstance(c.get("id"), int)), key=lambda c: c["id"])
    lines, facts = [], []
    now = datetime.now(UTC)
    for c in ordered:
        if not (match := REQUEST.fullmatch(first_line(c))):
            continue
        me = match.group(1)
        if any(o["id"] > c["id"] and assign_line(o, me, allowed) for o in ordered):
            continue
        minutes = max(0, int((now - moment(c.get("created_at"))).total_seconds() // 60))
        lines.append(f"request {me} (comment {c['id']}) waiting {minutes}m")
        facts.append(["request", me, c["id"], stamp(c)])  # never the minutes: they change alone
    return lines, facts


def brief_question(comments: list, allowed: set[str]) -> dict | None:
    """The newest `Question:` comment created or edited after the brief's last comment by a listed
    author, else None. A session's own lines (`Question:`, `taken:`, `released:`, `taken over:`)
    are never an answer, since a session may post as a listed author (Q-408-1)."""
    marks = [
        (str(c.get("created_at") or ""), c.get("id") or 0)
        for c in comments
        if author_of(c) in allowed and not first_line(c).startswith(NOT_ANSWERS)
    ]
    floor = max(marks, default=("", 0))
    asked = [
        c
        for c in comments
        if first_line(c).startswith("Question:") and (stamp(c), c.get("id") or 0) > floor
    ]
    return max(asked, key=lambda c: (stamp(c), c.get("id") or 0), default=None)


def brief_questions(root, repo: str, authors: list[str], prs: list) -> tuple[list[str], list]:
    """Brief 408 answer 1: each open `agk-brief` issue with a live `taken:`, no open pull request
    with its `Brief: #n` line and an unanswered `Question:`, as a line and as a fact. A brief with
    an open pull request is left to that pull request's own rules (a draft's question is listed
    there)."""
    found = pages(f"repos/{repo}/issues?state=open&labels={LABEL}")
    if found is None:
        raise CheckError(f"rule 3: the open issues labelled {LABEL} cannot be read")
    named = {brief_number(p) for p in prs}
    allowed = {a.lstrip("@").lower() for a in authors}
    asked = []
    for issue in sorted(labelled(found, LABEL), key=lambda i: i["number"]):
        if issue["number"] in named:
            continue
        comments = pages(f"repos/{repo}/issues/{issue['number']}/comments")
        if comments is None:
            raise CheckError("rule 3: the comments of an open brief cannot be read")
        if (question := brief_question(comments, allowed)) is not None:
            asked.append((issue["number"], comments, question))
    if not asked:
        return [], []
    every = pages(f"repos/{repo}/pulls?state=all")  # a merged pull request keeps a take live
    if every is None:
        raise CheckError("rule 3: the pull requests cannot be read")
    hours = flow_int(root, "claim_hours", CLAIM_HOURS, 5)
    lines, facts = [], []
    for number, comments, question in asked:
        if live_takes(comments, number, every, hours):
            lines.append(f"#{number} question on a brief")
            facts.append(["question", number, question.get("id"), stamp(question)])
    return lines, facts


def review_queue(root, mode: str) -> int:
    """Print the pull requests that qualify for a conductor's review, and why (read-only)."""
    repo = repo_name(root)
    authors = verdict_authors(root)
    if not authors:
        raise CheckError(
            "brief 306: no verdict author is listed"
            " (setting: verdict_authors in config/reviewers.yaml)"
        )
    found = pages(f"repos/{repo}/pulls?state=open")
    if found is None:
        raise CheckError("rule 3: the open pull requests cannot be read")
    review, skip, prints = [], [], []
    auto = auto_merge_on(root)
    for pr in sorted(
        (p for p in found if isinstance(p.get("number"), int)), key=lambda p: p["number"]
    ):
        head = str((pr.get("head") or {}).get("sha") or "")
        verb, reasons, facts = review_line(repo, root, pr, authors, auto)
        line = f"#{pr['number']} {head[:7]} {verb}: {'; '.join(reasons)}"
        if verb == "cleared":  # SPEC-0039 rule 9: the conductor runs merge_cleared.py again
            line = f"#{pr['number']} {head[:7]} cleared, not merged"
        (skip if verb == "skip" else review).append(line)
        prints.append([pr["number"], head, label_of(pr), bool(pr.get("draft")), facts])
    requests, asked = waiting_requests(repo, authors)
    questions, open_questions = brief_questions(root, repo, authors, found)
    review += requests + questions
    prints += asked + open_questions
    if mode == "--fingerprint":
        text = json.dumps(prints, sort_keys=True, separators=(",", ":"))
        print("fingerprint " + hashlib.sha256(text.encode("utf-8")).hexdigest())
        return 0
    print("\n".join(review) if review else "empty")
    if mode == "--all" and skip:
        print("\n".join(skip))
    return 0


# --- a stalled pull request (SPEC-0033 rule 5) ------------------------------------------------


def stall_hours(root) -> int:
    """`stall_hours` of the flow table of agk.toml: a whole number of hours, 4 by default."""
    return flow_int(root, "stall_hours", STALL_HOURS, 5)


def waits_for_a_person(root, pr: dict, comments: list) -> bool:
    """A verdict by a listed author that clears or covers the head: the work waits for a person."""
    authors = counted_authors(verdict_authors(root), (pr.get("user") or {}).get("login"))
    body = latest_verdict_body(comments, authors)
    if covered_fix_list(body) is not None:
        return True
    match = HEAD_VERDICT.fullmatch(body.splitlines()[0].strip()) if body else None
    head = str((pr.get("head") or {}).get("sha") or "")
    return bool(
        match and match.group(1) == "cleared" and match.group(2) and head.startswith(match.group(2))
    )


def last_change(repo: str, pr: dict, comments: list) -> datetime | None:
    """The latest of the head commit and every comment (created or edited); None if unreadable."""
    sha = (pr.get("head") or {}).get("sha")
    commit = gh(f"repos/{repo}/commits/{sha}") if sha else None
    stamp = ((commit or {}).get("commit") or {}).get("committer", {}).get("date")
    if not stamp:
        return None
    moments = [moment(stamp)]
    for c in comments:
        moments += [moment(c.get(k)) for k in ("created_at", "updated_at") if c.get(k)]
    return max(moments)


def takeover_lost(comments: list, since: datetime, me: str) -> str | None:
    """The session whose `taken over:` comment since `since` is older than this session's."""
    found = sorted(
        (moment(c.get("created_at")), c.get("id", 0), m.group(1))
        for c in comments
        if isinstance(c.get("body"), str)
        and (m := TAKEOVER.fullmatch(plain(c["body"])))
        and moment(c.get("created_at")) >= since
    )
    return found[0][2] if found and found[0][2] != me else None


def parked(root, repo: str, pr: dict, comments: list | None) -> bool:
    """SPEC-0049 rule 10: the newest `Report:` of the author is an `over cap` report, and no ruling
    since puts the build under its cap: the cap of the brief's `Size:` now (a person raised it) is
    at or above the figure the report gives. Without the `[caps]` table, or when the brief or the
    table cannot be read, the pull request stays parked. GET only."""
    me = str((pr.get("user") or {}).get("login") or "").lower()
    mine = [c for c in comments or [] if author_of(c) == me]
    reports = [c for c in mine if first_line(c).startswith("Report:")]
    newest = max(reports, key=lambda c: (moment(c.get("created_at")), c.get("id", 0)), default=None)
    found = OVER_CAP.fullmatch(first_line(newest)) if newest else None
    if not found:
        return False
    import caps  # here, not at the top: caps imports this module

    brief = brief_number(pr)
    issue = gh(f"repos/{repo}/issues/{brief}") if brief is not None else None
    try:
        table = caps_settings(root)
    except CheckError:
        table = None
    if table is None or not isinstance(issue, dict) or "body" not in issue:
        return True
    _, cap = caps.cap_of(table, issue.get("body"))
    return float(found.group(1)) > cap[found.group(2)]


def offer_stalled(root, repo: str, me: str, taking: bool = True) -> int | None:
    """Offer the first stalled pull request and, with `taking`, take it over; None when there is
    none. Without `taking` it posts nothing and prints the command that takes it over (Q-440-1)."""
    hours = stall_hours(root)
    prs = pages(f"repos/{repo}/pulls?state=open")
    if prs is None:
        print("note: the open pull requests cannot be read", file=sys.stderr)
        return None
    for pr in sorted(prs, key=lambda p: p.get("number", 0)):
        names = {lab.get("name") for lab in pr.get("labels") or []}
        if names & WAITING_LABELS or not (pr.get("draft") or names & BUILDER_LABELS):
            continue
        number = pr["number"]
        comments = pages(f"repos/{repo}/issues/{number}/comments")
        changed = last_change(repo, pr, comments) if comments is not None else None
        if changed is None or datetime.now(UTC) - changed < timedelta(hours=hours):
            continue
        if waits_for_a_person(root, pr, comments) or parked(root, repo, pr, comments):
            continue
        if not taking:
            print(f"stalled #{number}\ntitle: {pr.get('title')}\naddress: {pr.get('html_url')}\n")
            print(f"take it over with: session.py next --session {me} --take")
            return 0
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        body = f"body=taken over: {me} {day}"
        if gh(f"repos/{repo}/issues/{number}/comments", "-f", body, method="POST") is None:
            print(f"skip #{number}: the takeover cannot be posted")
            continue
        lost = takeover_lost(pages(f"repos/{repo}/issues/{number}/comments") or [], changed, me)
        if lost:
            print(f"skip #{number}: lost the takeover to {lost}")
            continue
        print(f"stalled #{number}\ntitle: {pr.get('title')}\naddress: {pr.get('html_url')}\n")
        print(f"run: python3 scripts/agk/session.py resume --pr {number}")
        return 0
    return None


# --- resume (SPEC-0033 rule 4) ----------------------------------------------------------------


def brief_of(repo: str, number: int, body: str) -> dict | None:
    """The first `#n` of the body that is an issue labelled agk-brief."""
    seen: set[int] = set()
    for match in re.finditer(r"#(\d+)", body or ""):
        ref = int(match.group(1))
        if ref in seen or ref == number:
            continue
        seen.add(ref)
        found = gh(f"repos/{repo}/issues/{ref}")
        names = {lab.get("name") for lab in (found or {}).get("labels") or []} if found else set()
        if LABEL in names:
            return found
    return None


def resume(root, number: int) -> int:
    repo = repo_name(root)
    pr = gh(f"repos/{repo}/pulls/{number}")
    comments = pages(f"repos/{repo}/issues/{number}/comments")
    if not isinstance(pr, dict) or "head" not in pr or comments is None:
        raise CheckError("rule 4: the pull request and its comments cannot be read")
    head, ref = str(pr["head"].get("sha")), str(pr["head"].get("ref"))
    author = (pr.get("user") or {}).get("login") or ""
    kind = "draft" if pr.get("draft") else pr.get("state", "open")
    print(f'pull request #{number} "{pr.get("title")}" ({kind}) head {head} branch {ref}')
    names = [
        lab["name"] for lab in pr.get("labels") or [] if str(lab.get("name")).startswith("agk:")
    ]
    print("state: " + (", ".join(names) or "none"))
    brief = brief_of(repo, number, pr.get("body") or "")
    if brief:
        print(f'brief #{brief["number"]} "{brief.get("title")}"\n{brief.get("body")}\n')
    else:
        print("brief: none (the body of the pull request names no agk-brief issue)")
    found, problems = progress_of(comments, author)
    if problems:
        print(f"progress: unreadable ({problems[0]})")
    elif found:
        line = f"{found['head']} done {found['done']}/{found['total']}; next: {found['next']}"
        print(f"progress: {line}\ncontinue from: {found['next']}")
    else:
        print("progress: none")
    authors = counted_authors(verdict_authors(root), author)
    allowed = {a.lstrip("@").lower() for a in authors or []}
    listed = sorted(
        (c for c in comments if author_of(c) in allowed and isinstance(c.get("body"), str)),
        key=lambda c: (str(c.get("created_at") or ""), c.get("id", 0)),
    )
    last = [
        (c, m)
        for c in listed
        if (m := HEAD_VERDICT.fullmatch(c["body"].splitlines()[0].strip() if c["body"] else ""))
    ]
    if last:
        c, m = last[-1]
        names_head = bool(m.group(2) and head.startswith(m.group(2)))
        text = m.group(0).removeprefix("Verdict: ")
        print(
            f"verdict: {text} (comment {c.get('id')}) "
            + ("names" if names_head else "does not name")
            + " the head"
        )
    else:
        print("verdict: none")
    print("commands:")
    if SAFE_REF.fullmatch(ref):
        print(f"  git fetch origin {ref}\n  git checkout -B {ref} {head}")
    print(f"  python3 scripts/agk/session.py watch --pr {number}")
    return 0


# --- the progress comment (SPEC-0033 rule 3) --------------------------------------------------


def progress_of(comments: list, login: str) -> tuple[dict | None, list[str]]:
    """The one `Progress:` comment of a pull request by `login`, and what is wrong with it.

    A comment counts when its first line starts `Progress:`. None with no problem when there is
    none; more than one, or one that is not `Progress: <head> done <n>/<m>; next: <step>` with
    1 <= m and n <= m, is a problem that names the rule and never the line."""
    me = login.lstrip("@").lower()
    found = [
        c
        for c in comments
        if author_of(c) == me
        and isinstance(c.get("body"), str)
        and c["body"].splitlines()[:1]
        and c["body"].splitlines()[0].startswith("Progress:")
    ]
    if not found:
        return None, []
    if len(found) > 1:
        return None, ["rule 3: the pull request holds more than one Progress comment"]
    match = PROGRESS.fullmatch(found[0]["body"].splitlines()[0].strip())
    done, total = (int(match.group(2)), int(match.group(3))) if match else (0, 0)
    if not match or total < 1 or done > total:
        return None, ["rule 3: the Progress comment is not of the form head, done n/m, next step"]
    return {"head": match.group(1), "done": done, "total": total, "next": match.group(4)}, []


# --- the command line -------------------------------------------------------------------------


# --- the builder's standing prompt (brief #700, ADR-0330) -------------------------------------

BUILDER_RULES = (2, 3, 7, 8, 17, 21, 27, 28, 31, 33, 34, 36)  # the session rules a builder works by
CORE_RULES_FILE = "config/core-rules.md"
RESERVED_LINE = re.compile(r"Reserved: (.+)")
NUMBER_RE = re.compile(NUMBER)
RESERVATION = re.compile(r"\b(?:ADR-\d{4}|SPEC-\d{4}|REQ-\d{3}|amendment \d+)\b")
RULE_START = re.compile(r"(\d+)\. (\S.*)")
BODY_LINE = re.compile(r"`[A-Z][A-Za-z -]*:[^`]*`")
PROMPT_HEAD = (
    "You are an AGK builder session. Repository: {repo} (clone it if it is not present).\n"
    "\n"
    "{item}\n"
    "\n"
    "Before acting, read in this order: CLAUDE.md, constitution/principles.md, "
    "config/core-rules.md, config/session-rules.md, the brief with every comment "
    "(`gh api repos/{repo}/issues/{brief}` and `/comments`), the spec and ADRs it names, "
    "docs/runs/decisions/ (one file per entry), and every file it names. Verify every name the "
    "brief cites; where it is wrong, follow the code and say so under `Decisions taken:`.\n"
    "\n"
    "The secret scan (ADR-0306, ADR-0327): when your session cannot install the scanner, every "
    "pull request body you write carries, as its own line, exactly `{defer}`, and you run "
    "`python3 scripts/agk/prepush.py --body <body file>` so the scan is deferred to the "
    "governance run, which scans your commits before any merge. Keep the line through every "
    "edit.\n"
    "\n"
    "Branch from origin/<default branch>: `claude/brief-{brief}`; one pull request for this brief "
    "only. Tests first: write the brief's tests, record the failing count, then implement. "
    "Decisions are the reviewers': a build of an Approved spec that changes no decision writes no "
    "ADR and puts `Covered-by: ADR-nnnn` in the body; otherwise write the reserved ADR with status "
    "Proposed and never mark it Accepted yourself. The pull request body carries "
    "`Brief: #{brief}`, "
    "{lines} and `Summary:` (one plain sentence of at most 120 characters), and the last pull "
    "request of the brief `Finishes: #{brief}` and `Closes #{brief}`.\n"
    "\n"
    "The session rules that bind every step, quoted from config/session-rules.md:\n"
    "\n"
)
PROMPT_TAIL = (
    "\n"
    "When the pull request is ready, post `Report: <head> ready for review` on it and end your "
    "session; a blocked session posts `Question: Q-{brief}-n ...` and waits there.\n"
)
STOP_LINE = (
    "Your item, your session name and any reserved numbers are in the line above. If an open "
    "pull request from branch `claude/brief-{brief}` already exists and this is not a follow-up "
    "for it, stop and say so."
)
FOLLOW_UP_LINE = "Follow-up for the open pull request of branch `claude/brief-{brief}`: {text}"


def reservations(body: str) -> list[str]:
    """The numbers of a brief's `Reserved:` lines, each once in the line's order: `ADR-nnnn`,
    `SPEC-nnnn`, `REQ-nnn` or `amendment n`, read only before the first `(` (Q-772-9)."""
    found: list[str] = []
    for line in body.splitlines():
        if match := RESERVED_LINE.fullmatch(line.strip()):
            found += RESERVATION.findall(match.group(1).split("(", 1)[0])
    return list(dict.fromkeys(found))


def reserved_numbers(body: str, comments: list) -> list[str]:
    """The numbers the brief reserved: its `Reserved:` lines and the `reserves` of its takes, in
    the order REQ, SPEC, ADR, each once."""
    found: list[str] = []
    for line in body.splitlines():
        if match := RESERVED_LINE.fullmatch(line.strip()):
            found += NUMBER_RE.findall(match.group(1).split("(", 1)[0])
    for take_row in all_takes(comments):
        found += list(take_row[4])
    order = {"REQ": 0, "SPEC": 1, "ADR": 2}
    return sorted(set(found), key=lambda x: (order[x.split("-")[0]], x))


def rule_texts(root, numbers: tuple[int, ...]) -> list[str]:
    """The numbered rules of config/session-rules.md, each as one line `<n>. <text>` with its
    continuation lines joined; a number the file lacks is a note on stderr."""
    try:
        text = (root / RULES_FILE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"{RULES_FILE} cannot be read") from exc
    rules: dict[int, str] = {}
    current: int | None = None
    for line in text.splitlines():
        if match := RULE_START.fullmatch(line):
            current = int(match.group(1))
            rules[current] = match.group(2).strip()
        elif current is not None and line.startswith(" ") and line.strip():
            rules[current] += " " + line.strip()
        else:
            current = None
    for n in numbers:
        if n not in rules:
            print(f"note: session rule {n} is not in {RULES_FILE}", file=sys.stderr)
    return [f"{n}. {rules[n]}" for n in numbers if n in rules]


def body_lines(root) -> list[str]:
    """The body lines of CLAUDE.md item 7 (`Advances:`, `Build-state row:`, ...), read from
    config/core-rules.md as they are written there, in backticks."""
    try:
        text = (root / CORE_RULES_FILE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"{CORE_RULES_FILE} cannot be read") from exc
    item, inside = "", False
    for line in text.splitlines():
        if match := RULE_START.fullmatch(line):
            inside = match.group(1) == "7" and not item
            item += match.group(2) if inside else ""
        elif inside and line.startswith(" "):
            item += " " + line.strip()
        else:
            inside = False
    found = BODY_LINE.findall(item)
    if not found:
        raise CheckError(f"CLAUDE.md item 7 (the body lines) cannot be read from {CORE_RULES_FILE}")
    return found


def follow_up_problem(text: str) -> str | None:
    if not text.strip() or text.splitlines() != [text]:
        return "prompt: the follow-up is one line"
    if TELL_REFUSED.match(ZERO_WIDTH.sub("", text)):
        return "prompt: a follow-up never starts with Approve:, Confirmed: or Verdict:"
    return None


def prompt(root, number: int, me: str | None, follow_up: str | None) -> int:
    """`prompt --brief N`: the builder's standing prompt from the kit's files (GET only)."""
    from prepush import DEFER_LINE  # the one secret-scan deferral line (ADR-0327)

    if follow_up is not None and (problem := follow_up_problem(follow_up)):
        raise CheckError(problem)
    repo = repo_name(root)
    brief = gh(f"repos/{repo}/issues/{number}")
    if not isinstance(brief, dict) or not isinstance(brief.get("body"), str):
        raise CheckError(f"the brief #{number} cannot be read")
    comments = pages(f"repos/{repo}/issues/{number}/comments")
    if comments is None:
        raise CheckError(f"the comments of #{number} cannot be read")
    rules = rule_texts(root, BUILDER_RULES)
    lines = ", ".join(body_lines(root))
    reserved = ", ".join(reserved_numbers(brief["body"], comments)) or "none"
    item = (f"Session name: {me}. " if me else "") + f"Item: brief #{number}. Reserved: {reserved}."
    item += "\n" + (
        FOLLOW_UP_LINE.format(brief=number, text=follow_up)
        if follow_up is not None
        else STOP_LINE.format(brief=number)
    )
    text = PROMPT_HEAD.format(repo=repo, item=item, brief=number, defer=DEFER_LINE, lines=lines)
    text += "\n".join(rules) + "\n" + PROMPT_TAIL.format(brief=number)
    print(text, end="")
    return 0


def number_of(text: str | None) -> bool:
    return bool(text) and text.isdigit() and int(text) > 0


def number_ok(text: str) -> bool:
    try:
        return float(text) >= 0
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["plan"]:
        flags = args[1:]
        what_if_dir = flags[1] if len(flags) == 2 and flags[0] == "--what-if" else None
        if what_if_dir is None and (
            set(flags) - {"--json", "--record"} or len(set(flags)) != len(flags)
        ):
            print(USAGE)
            return 2
        try:
            from session_plan import plan, what_if  # the plan builds on this module

            if what_if_dir is not None:
                return what_if(repo_root(), what_if_dir)
            return plan(repo_root(), "--json" in flags, "--record" in flags)
        except CheckError as exc:
            print(f"FAIL {NAME}: {exc}")
            return 2
    if args[:1] == ["tidy"]:
        flags = args[1:]
        if len(set(flags)) != len(flags) or not set(flags) <= {"--apply", "--json"}:
            print(USAGE)
            return 2
        try:
            root = repo_root()
            if paused_default(root):
                print(PAUSED_REFUSAL)
                return PAUSED_EXIT
            return tidy(root, "--apply" in flags, "--json" in flags)
        except CheckError as exc:
            print(f"FAIL {NAME}: {exc}")
            return 2
    if args[:1] == ["review-queue"]:
        if args[1:] not in ([], ["--all"], ["--fingerprint"]):
            print(USAGE)
            return 2
        try:
            return review_queue(repo_root(), args[1] if args[1:] else "")
        except CheckError as exc:
            print(f"FAIL {NAME}: {exc}")
            return 2
    # `--take` is the one flag without a value, of `next` only (brief #440, ADR-0236).
    take_flag = args[:1] == ["next"] and args.count("--take") == 1
    if take_flag:
        args = [a for a in args if a != "--take"]
    if not args or args[0] not in COMMANDS or len(args[1:]) % 2:
        print(USAGE)
        return 2
    cmd, opts = args[0], dict(zip(args[1::2], args[2::2], strict=False))
    allowed = {
        "watch": {
            "--pr",
            "--merged",
            "--assign",
            "--interval",
            "--timeout",
            "--since",
            "--session",
        },
        "next": {"--session"},
        "claim": {"--session", "--brief", "--build"},
        "after": {"--session"},
        "queue": {"--role", "--author"},
        "resume": {"--pr"},
        "ids": {"--exclude-pr"},
        "demand": set(),
        "plan": set(),
        "push-check": set(),
        "slot": {"--take", "--renew", "--release", "--next"},
        "tell": {"--session", "--text"},
        "inbox": {"--session"},
        "mine": {"--session", "--pr", "--brief"},
        "kind": {"--brief"},
        "prompt": {"--brief", "--session", "--follow-up"},
    }
    if not set(opts) <= allowed[cmd] or len(opts) != len(args[1::2]):
        print(USAGE)
        return 2
    if cmd == "watch":
        modes = [k for k in ("--pr", "--merged", "--assign") if k in opts]
        ok = len(modes) == 1 and (
            bool(SESSION_ID.fullmatch(opts["--assign"]))
            if "--assign" in opts
            else number_of(opts.get("--pr") or opts.get("--merged"))
        )
        ok = ok and all(number_ok(opts[k]) for k in ("--interval", "--timeout") if k in opts)
        ok = ok and ("--since" not in opts or ("--pr" in opts and opts["--since"].isdigit()))
        ok = ok and (
            "--session" not in opts
            or ("--pr" in opts and bool(SESSION_ID.fullmatch(opts["--session"])))
        )
    elif cmd == "queue":
        ok = opts.get("--role") in ROLES and (
            "--author" not in opts or bool(SESSION_ID.fullmatch(opts["--author"].lstrip("@")))
        )
    elif cmd == "resume":
        ok = number_of(opts.get("--pr"))
    elif cmd == "claim":
        ok = bool(SESSION_ID.fullmatch(opts.get("--session", ""))) and number_of(
            opts.get("--brief")
        )
        ok = ok and bool(SESSION_ID.fullmatch(opts.get("--build", "x")))
    elif cmd == "ids":
        ok = number_of(opts.get("--exclude-pr", "1"))
    elif cmd in ("demand", "push-check"):
        ok = True
    elif cmd == "slot":
        ok = len(opts) == 1 and all(SESSION_ID.fullmatch(v) for v in opts.values())
    elif cmd == "tell":
        ok = bool(SESSION_ID.fullmatch(opts.get("--session", ""))) and "--text" in opts
    elif cmd == "kind":
        ok = number_of(opts.get("--brief"))
    elif cmd == "prompt":
        ok = number_of(opts.get("--brief")) and bool(
            SESSION_ID.fullmatch(opts.get("--session", "x"))
        )
    elif cmd == "mine":
        targets = [k for k in ("--pr", "--brief") if k in opts]
        ok = bool(SESSION_ID.fullmatch(opts.get("--session", ""))) and len(targets) == 1
        ok = ok and number_of(opts[targets[0]])
    else:
        ok = bool(SESSION_ID.fullmatch(opts.get("--session", "")))
    if not ok:
        print(USAGE)
        return 2
    try:
        root = repo_root()
        if cmd in PAUSED_COMMANDS and paused_default(root):
            print(PAUSED_REFUSAL)
            return PAUSED_EXIT
        if cmd == "queue":
            return queue(root, opts["--role"], opts.get("--author"))
        if cmd == "watch":
            return (
                watch_assign(root, opts["--assign"], opts)
                if "--assign" in opts
                else watch(root, opts)
            )
        if cmd == "claim":
            return claim(root, opts["--session"], int(opts["--brief"]), opts.get("--build"))
        if cmd == "after":
            return after(root, opts["--session"])
        if cmd == "resume":
            return resume(root, int(opts["--pr"]))
        if cmd == "ids":
            return ids(root, int(opts["--exclude-pr"]) if "--exclude-pr" in opts else None)
        if cmd in ("demand", "push-check"):
            return {"demand": demand, "push-check": push_check}[cmd](root)
        if cmd == "slot":
            return slot(root, *next(iter(opts.items())))
        if cmd == "tell":
            return tell(root, opts["--session"], opts["--text"])
        if cmd == "inbox":
            return inbox(root, opts["--session"])
        if cmd == "kind":
            return brief_kind(root, int(opts["--brief"]))
        if cmd == "prompt":
            return prompt(
                root, int(opts["--brief"]), opts.get("--session"), opts.get("--follow-up")
            )
        if cmd == "mine":
            number = {k: int(v) for k, v in opts.items() if k in ("--pr", "--brief")}
            return mine(root, opts["--session"], number.get("--pr"), number.get("--brief"))
        return next_brief(root, opts["--session"], take_flag)
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
