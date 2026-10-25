"""What a builder session reads from GitHub: its verdicts and its next brief (SPEC-0030).

    python3 session.py watch --pr N [--interval S] [--timeout S]
    python3 session.py watch --merged N [--interval S] [--timeout S]
    python3 session.py next --session ID
    python3 session.py queue --role conductor|builder|person [--author LOGIN]
    python3 session.py resume --pr N
    python3 session.py ids
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
A wait never goes silent (brief #210): when GitHub cannot be read for 5 polls in a row it prints
`error: <what> cannot be read` and exits 4, and `--assign` prints `waiting on #<issue> since
<id>` when it starts. When `gh` says it could not connect, the line is `github-unreachable:
<what> cannot be read; local head <sha> not pushed; next: push, then post the
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
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from common import CheckError, covered_fix_list, git, load_config, next_free_ids, repo_root
from facts import ORIGIN
from metrics import author_of, counted_authors, latest_verdict_body
from reviewers import verdict_authors

NAME = "session"
USAGE = (
    "usage: session.py watch (--pr N [--since ID] | --merged N | --assign ID)\n"
    "                        [--interval S] [--timeout S]\n"
    "       session.py next --session ID\n"
    "       session.py claim --session ID --brief N [--build X]\n"
    "       session.py after --session ID\n"
    "       session.py queue --role conductor|builder|person [--author LOGIN]\n"
    "       session.py resume --pr N\n"
    "       session.py ids\n"
    "       session.py demand\n"
    "       session.py push-check"
)
COMMANDS = ("watch", "next", "claim", "after", "queue", "resume", "ids", "demand", "push-check")
PAGE = 100
LABEL = "agk-brief"
MAX_BUILDERS = 3
CLAIM_HOURS = 4
VERDICT = re.compile(r"Verdict: (cleared|fix list|rejected) ([0-9a-f]{7,40})")
NUMBER = r"(?:REQ-\d{3}|SPEC-\d{4}|ADR-\d{4})"
BUILD = r"(?: build \(([A-Za-z0-9._-]+)\))?"
TAKE = re.compile(
    rf"taken: (\S+) (\d{{4}}-\d{{2}}-\d{{2}}){BUILD}(?: retakes)?"
    rf"(?: reserves ({NUMBER}(?:, {NUMBER})*))?"
)
RELEASED = re.compile(rf"released: (\S+){BUILD}")
ASSIGN = re.compile(r"Assign: (\S+) (none|#(\d+)(?: build \(([A-Za-z0-9._-]+)\))?)")
ASSIGN_LABEL = "agk-conductor"
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
        ["gh", "api", "--method", "GET", "rate_limit"], capture_output=True, text=True
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
            ["gh", "api", "--method", method, endpoint, *extra], capture_output=True, text=True
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
        if late():
            print("timeout")
            return 3
        time.sleep(interval)


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


def all_takes(comments: list) -> list[tuple]:
    """(when, id, session, login, reserves, released, build) of every take comment, oldest first.

    A `released:` frees a take only when the same account posted it, for the build it names or
    for every build when it names none."""
    takes, releases = [], []
    for c in comments:
        text = c["body"].strip() if isinstance(c.get("body"), str) else ""
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


def judge(repo: str, brief: dict, me: str, prs: list, hours: int) -> tuple[str | None, list]:
    """Why the brief is not for this session (or None when it is free), and its comments."""
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


def numbers_in_use(root, s: Survey) -> dict[str, int]:
    """The highest requirement, spec and ADR number taken on the default branch, by the files an
    open builder pull request adds and by the reservations of live takes (rule 4)."""
    base = next_free_ids(root, f"origin/{load_config(root)['default_branch']}")
    top = {
        "req": int(base["req"][4:]) - 1,
        "spec": int(base["spec"]) - 1,
        "adr": int(base["adr"]) - 1,
    }
    for pr in s.builders:
        for entry in pull_files(s, pr):
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
    number, me, comments = brief["number"], s.me, s.comments[brief["number"]]

    def rivals(found: list) -> list:
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


def claim(root, me: str, number: int, build: str | None) -> int:
    repo = repo_name(root)
    comments = pages(f"repos/{repo}/issues/{number}/comments")
    prs = pages(f"repos/{repo}/pulls?state=all")
    if comments is None or prs is None:
        raise CheckError("rule 5: the brief and the pull requests cannot be read")
    hours = flow_int(root, "claim_hours", CLAIM_HOURS, 1)
    s = Survey(repo, me, 0, hours, prs, [], {number: comments})
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


def watch_assign(root, me: str, args: dict[str, str]) -> int:
    """End on the first `Assign: <me> ...` by a listed author after this session's `Request:`."""
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
    asked = [c["id"] for c in comments if str(c.get("body") or "").startswith(f"Request: {me} ")]
    seen = max(asked, default=newest(comments) or 0)
    allowed = {a.lstrip("@").lower() for a in counted_authors(verdict_authors(root), None)}
    print(f"waiting on #{issue} since {seen}", flush=True)
    while True:
        found = pages(path)
        if found is None:
            if reads.failed(f"the comments of #{issue}"):
                return EXIT_UNREADABLE
        else:
            reads.good()
        for comment in sorted(found or [], key=lambda c: c.get("id", 0)):
            body = comment.get("body")
            first = body.splitlines()[0].strip() if isinstance(body, str) and body.strip() else ""
            match = ASSIGN.fullmatch(first)
            if comment.get("id", 0) > seen and match and match.group(1) == me:
                if author_of(comment) in allowed:
                    print(f"assign {match.group(2)}")
                    return 0
        if time.monotonic() - started >= limit:
            print("assign-timeout")
            return 0
        time.sleep(interval)


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
    for number, why in s.skipped:
        print(f"skip #{number}: {why}")
    for brief in s.free:
        why = overlap(root, s, brief) or take(s, brief, lambda b=brief: reservation(root, s, b))
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
    """Where a builder goes when its work is done, by `[flow] assign` (rule 12)."""
    if assign_mode(root) == "next":
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


def ids(root) -> int:
    top = numbers_in_use(root, survey(root, repo_name(root), ""))
    print(
        json.dumps(
            {
                "req": f"REQ-{top['req'] + 1:03d}",
                "spec": f"{top['spec'] + 1:04d}",
                "adr": f"{top['adr'] + 1:04d}",
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
        and (m := TAKEOVER.fullmatch(c["body"].strip()))
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
    if not args or args[0] not in COMMANDS or len(args[1:]) % 2:
        print(USAGE)
        return 2
    cmd, opts = args[0], dict(zip(args[1::2], args[2::2], strict=False))
    allowed = {
        "watch": {"--pr", "--merged", "--assign", "--interval", "--timeout", "--since"},
        "next": {"--session"},
        "claim": {"--session", "--brief", "--build"},
        "after": {"--session"},
        "queue": {"--role", "--author"},
        "resume": {"--pr"},
        "ids": set(),
        "demand": set(),
        "push-check": set(),
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
    elif cmd in ("ids", "demand", "push-check"):
        ok = True
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
        if cmd in ("ids", "demand", "push-check"):
            return {"ids": ids, "demand": demand, "push-check": push_check}[cmd](root)
        return next_brief(root, opts["--session"])
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
