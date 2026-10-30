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
on a draft`, whatever its head, label or checks (brief 350). Required checks that
have not reported skip it under `agk:ci-running` and add the reason `checks not reported` under
any other label. `--all` adds a line `#N <head7> skip: <why>`
for each other open pull request; `--fingerprint` prints only `fingerprint <sha256>` of the heads,
labels, draft flags, comment times (a draft's too) and check states, which changes only when the
queue does, so a loop wakes the conductor only then.
A wait never goes silent (brief #210): when GitHub cannot be read for 5 polls in a row it prints
`error: <what> cannot be read` and exits 4, and `--assign` prints `waiting on #<issue> since
<id>` when it starts. `--assign` also takes at once the newest `Assign:` for the session posted
between its previous `Request:` and its current one, unless the session has a `taken:` on any
brief after it (brief #252). When `gh` says it could not connect, the line is
`github-unreachable: <what> cannot be read; local head <sha> not pushed; next: push, then post the
Report:/Question:`; a rate limit is waited out to the reset time that GitHub reports and does
not end a wait (answer 6).
`next` prints the first free `agk-brief` issue and takes it with the one comment `taken: <ID>
<YYYY-MM-DD>`, the only POST of this script; with none left it prints `no brief` and exits 1. This
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
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    CheckError,
    covered_fix_list,
    git,
    load_config,
    next_free_ids,
    repo_root,
    required_checks,
    show,
)
from facts import ORIGIN
from metrics import author_of, counted_authors, latest_verdict_body
from reviewers import verdict_authors

NAME = "session"
USAGE = (
    "usage: session.py watch (--pr N [--since ID] [--session ID] | --merged N | --assign ID)\n"
    "                        [--interval S] [--timeout S]\n"
    "       session.py next --session ID\n"
    "       session.py claim --session ID --brief N [--build X]\n"
    "       session.py after --session ID\n"
    "       session.py queue --role conductor|builder|person [--author LOGIN]\n"
    "       session.py review-queue [--all | --fingerprint]\n"
    "       session.py resume --pr N\n"
    "       session.py ids [--exclude-pr N]\n"
    "       session.py demand\n"
    "       session.py plan [--json]\n"
    "       session.py push-check\n"
    "       session.py tell --session ID --text MESSAGE\n"
    "       session.py inbox --session ID"
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
    "tell",
    "inbox",
)
PAGE = 100
LABEL = "agk-brief"
STALE_LABEL = "agk-stale"
STALE_LINE = "Status: stale"
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
ASSIGN = re.compile(r"Assign: (\S+) (none|#(\d+)(?: build \(([A-Za-z0-9._-]+)\))?)")
ASSIGN_LABEL = "agk-conductor"
TELL = re.compile(r"Tell: (\S+) (.+)")
TELL_LIMIT = 300
TELL_REFUSED = re.compile(r"\s*(?:Approve|Confirmed|Verdict):", re.IGNORECASE)
ZERO_WIDTH = re.compile("[\u200b-\u200f\u2060\ufeff]")  # read as nothing before the start check
ASSIGN_MODES = ("conductor", "next")
BRIEF_LINE = re.compile(r"Brief: #(\d+)")
TOUCHES = re.compile(r"Touches: (.+)")
SENTENCE = re.compile(r'Sentence: "(.*)"')
DEPENDS = re.compile(r"Depends-on: #(\d+)")
SIZE = re.compile(r"Size: [SML]")
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
PROGRESS = re.compile(r"Progress: ([0-9a-f]{7,40}) done (\d+)/(\d+); next: (\S.*)")


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


def judge(repo: str, brief: dict, me: str, prs: list, hours: int) -> tuple[str | None, list]:
    """Why the brief is not for this session (or None when it is free), and its comments."""
    if is_stale(brief):
        return "stale", []
    problems = brief_problems(brief.get("body"))
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
    takes = live_takes(comments, brief["number"], prs, hours)
    if takes and not any(t[2] == me for t in takes):
        return f"taken by {takes[0][2]}", comments
    return None, comments


def touches_of(body: str) -> list[str]:
    for line in body.splitlines():
        if found := TOUCHES.fullmatch(line.rstrip()):
            return [g.strip() for g in found.group(1).split(",")]
    return []


def priority_of(body: str) -> int:
    for line in body.splitlines():
        if found := PRIORITY.fullmatch(line.rstrip()):
            return int(found.group(1))
    return 2


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
    for brief in sorted((i for i in issues if "pull_request" not in i), key=lambda i: i["number"]):
        why, comments = judge(repo, brief, me, prs, hours)
        found.comments[brief["number"]] = comments
        if why is None:
            found.free.append(brief)
            continue
        found.skipped.append((brief["number"], why))
        if why.startswith("taken by") and brief["number"] not in named:
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


def take(s: Survey, brief: dict, reserve, build: str | None = None) -> str | None:
    """Post the take unless this session already holds one; the reason it was lost, or None.
    A take of a build conflicts with a take of the same build and with a take of the whole brief."""
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


def claim(root, me: str, number: int, build: str | None) -> int:
    repo = repo_name(root)
    comments = pages(f"repos/{repo}/issues/{number}/comments")
    prs = pages(f"repos/{repo}/pulls?state=all")
    if comments is None or prs is None:
        raise CheckError("rule 5: the brief and the pull requests cannot be read")
    hours = flow_int(root, "claim_hours", CLAIM_HOURS, 1)
    s = Survey(repo, me, 0, hours, prs, [], {number: comments})
    if any(t[2] != me for t in live_takes(comments, number, prs, hours)):
        stale_view(root, s, number)
    if why := take(s, {"number": number}, list, build):
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
    """End on the first `Assign: <me> ...` by a listed author after this session's `Request:`, or on
    the newest one posted between its previous `Request:` and that one and not yet taken (brief
    #252: the conductor may assign while the session is finishing, and need not post it twice)."""
    repo = repo_name(root)
    issue = conductor_issue(repo)
    path = f"repos/{repo}/issues/{issue}/comments"
    interval = float(args.get("--interval", 60))
    limit = float(args.get("--timeout", flow_int(root, "claim_hours", CLAIM_HOURS, 1) * 3600))
    started = time.monotonic()
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
            print("assign-timeout")
            return 0
        time.sleep(interval)
        found = pages(path)


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


def next_brief(root, me: str) -> int:
    repo = repo_name(root)
    issues = pages(f"repos/{repo}/issues?state=open&labels={LABEL}")
    red = [i for i in issues or [] if is_red(i)]
    if not red and (found := offer_stalled(root, repo, me)) is not None:
        return found
    if issues is None:
        raise CheckError("rule 3: the open briefs cannot be read")
    s = survey(root, repo, me, issues)
    if len(s.builders) >= s.max_builders:
        print(f"full {len(s.builders)}/{s.max_builders}")
        return 1
    # The plan's rules decide (brief #345, ADR-0195): a stale claim holds nothing, overlap is
    # judged by files, and a skip names the plan's reason.
    from session_plan import read_gone, running_conflict, settle_takes, wait_text

    read_gone(root, s)
    freed, s.skipped = settle_takes(s)
    s.held = [h for h in s.held if h[0] not in freed]
    for number, why in s.skipped:
        print(f"skip #{number}: {why}")
    shared = [glob_regex(p) for p in shared_patterns(root)]
    ready = [*s.free, *(s.briefs[n] for n in sorted(freed))]
    for brief in sorted(ready, key=lambda b: (priority_of(b["body"]), b["number"])):
        found = running_conflict(root, s, brief, shared)
        why = wait_text(found) if found else None
        why = why or take(s, brief, lambda b=brief: reservation(root, s, b))
        if why:
            print(f"skip #{brief['number']}: {why}")
            continue
        print(f"brief #{brief['number']}\ntitle: {brief.get('title')}")
        print(f"address: {brief.get('html_url')}\n")
        print(brief["body"])
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
        return next_brief(root, me)
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


def review_line(repo: str, root, pr: dict, authors: list[str]) -> tuple[str, list, list]:
    """(`review` or `skip`, the reasons, the facts for the fingerprint) of one open pull request."""
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
    for pr in sorted(
        (p for p in found if isinstance(p.get("number"), int)), key=lambda p: p["number"]
    ):
        head = str((pr.get("head") or {}).get("sha") or "")
        verb, reasons, facts = review_line(repo, root, pr, authors)
        line = f"#{pr['number']} {head[:7]} {verb}: {'; '.join(reasons)}"
        (review if verb == "review" else skip).append(line)
        prints.append([pr["number"], head, label_of(pr), bool(pr.get("draft")), facts])
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


def offer_stalled(root, repo: str, me: str) -> int | None:
    """Offer the first stalled pull request and take it over; None when there is none."""
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
        if waits_for_a_person(root, pr, comments):
            continue
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
        if args[1:] not in ([], ["--json"]):
            print(USAGE)
            return 2
        try:
            from session_plan import plan  # the plan builds on this module

            return plan(repo_root(), args[1:] == ["--json"])
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
        "tell": {"--session", "--text"},
        "inbox": {"--session"},
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
    elif cmd == "tell":
        ok = bool(SESSION_ID.fullmatch(opts.get("--session", ""))) and "--text" in opts
    else:
        ok = bool(SESSION_ID.fullmatch(opts.get("--session", "")))
    if not ok:
        print(USAGE)
        return 2
    try:
        root = repo_root()
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
        if cmd == "tell":
            return tell(root, opts["--session"], opts["--text"])
        if cmd == "inbox":
            return inbox(root, opts["--session"])
        return next_brief(root, opts["--session"])
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
