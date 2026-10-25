"""What a builder session reads from GitHub: its verdicts and its next brief (SPEC-0030).

    python3 session.py watch --pr N [--interval S] [--timeout S]
    python3 session.py watch --merged N [--interval S] [--timeout S]
    python3 session.py next --session ID
    python3 session.py queue --role conductor|builder|person [--author LOGIN]
    python3 session.py resume --pr N

`watch` polls with `gh api --method GET` and exits 0 with one line: `verdict <kind> <sha> (comment
<id>)` for a verdict by a listed author that names a prefix of the current head and is newer than
the newest comment seen at the start, `merged #N` or `closed #N`; with `--timeout` and no event it
prints `timeout` and exits 3. `--pr` also ends with `conflict #N` when the pull request
conflicts with its base (`mergeable_state` dirty), since CI does not start on it.
`--merged N` waits on that pull request alone and ignores comments. `--pr` also ends with `label
<name>` (or `label none`) when the `agk:` label that the router sets (SPEC-0032) changes from
the one it read at its first poll; it prints its event and exits (no loop): each event is one
wake. `queue` prints `#N <label>` for each open pull request whose router label belongs to the
role (conductor: `agk:review`, `agk:ci-red`, not drafts; builder: `agk:fix`, `agk:conflict`,
`agk:ci-red`, of `--author` when given; person: `agk:approve`, `agk:ready`), or `empty`, so a
session that starts or restarts resumes from GitHub with one GET.
`next` prints the first free `agk-brief` issue and takes it with the one comment `taken: <ID>
<YYYY-MM-DD>`, the only POST of this script; with none left it prints `no brief` and exits 1. This
is the only script that calls GitHub; no check does. Messages name the rule, never a value.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import tomllib
from datetime import UTC, datetime, timedelta
from typing import Any

from common import CheckError, covered_fix_list, git, repo_root
from facts import ORIGIN
from metrics import author_of, counted_authors, latest_verdict_body
from reviewers import verdict_authors

NAME = "session"
USAGE = (
    "usage: session.py watch (--pr N | --merged N) [--interval S] [--timeout S]\n"
    "       session.py watch --assign ID [--interval S] [--timeout S]\n"
    "       session.py next --session ID\n"
    "       session.py claim --session ID --brief N [--build X]\n"
    "       session.py after --session ID\n"
    "       session.py queue --role conductor|builder|person [--author LOGIN]\n"
    "       session.py resume --pr N"
)
PAGE = 100
LABEL = "agk-brief"
LIVE = timedelta(hours=24)
VERDICT = re.compile(r"Verdict: (cleared|fix list|rejected) ([0-9a-f]{7,40})")
BUILD = r"(?: build \(([A-Za-z0-9._-]+)\))?"
TAKE = re.compile(rf"taken: (\S+) (\d{{4}}-\d{{2}}-\d{{2}}){BUILD}")
RELEASE = re.compile(rf"released: (\S+){BUILD}")
ASSIGN = re.compile(r"Assign: (\S+) (none|#(\d+)(?: build \(([A-Za-z0-9._-]+)\))?)")
ASSIGN_LABEL = "agk-conductor"
ASSIGN_MODES = ("conductor", "next")
SENTENCE = re.compile(r'Sentence: "(.*)"')
DEPENDS = re.compile(r"Depends-on: #(\d+)")
SIZE = re.compile(r"Size: [SML]")
NUMBERED = re.compile(r"(\d+)\.\s+\S")
ADVANCES = re.compile(r"Advances: (new|REQ-\d{3}(?:, REQ-\d{3})*)")
PRIORITY = re.compile(r"Priority: [123]")
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
CLAIM_HOURS = 4
SAFE_REF = re.compile(r"[A-Za-z0-9._/-]+")
PROGRESS = re.compile(r"Progress: ([0-9a-f]{7,40}) done (\d+)/(\d+); next: (\S.*)")


def gh(endpoint: str, *extra: str, method: str = "GET") -> Any:
    """One `gh api` call; a failed or unreadable call is None."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["gh", "api", "--method", method, endpoint, *extra], capture_output=True, text=True
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout) if proc.stdout.strip() else {}
    except ValueError:
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


def label_of(pr: dict) -> str:
    """The router's label of a pull request (SPEC-0032 rule 2), `none` without one."""
    names = sorted(
        str(x.get("name"))
        for x in pr.get("labels") or []
        if isinstance(x, dict) and str(x.get("name")).startswith(STATE_PREFIX)
    )
    return ",".join(names) or "none"


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
    if not only_merge:
        while (found := newest(pages(f"repos/{repo}/issues/{number}/comments"))) is None:
            if late():
                print("timeout")
                return 3
            time.sleep(interval)
        seen = found
    while True:
        pr = gh(f"repos/{repo}/pulls/{number}")
        if isinstance(pr, dict):
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
            if comments is not None:
                own = (pr.get("user") or {}).get("login")
                authors = counted_authors(verdict_authors(root), own)
                head = str((pr.get("head") or {}).get("sha") or "")
                line = verdict_line(comments, seen, head, authors)
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
        problems.append("rule 2: at most one line Priority: 1, Priority: 2 or Priority: 3")
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


# --- next (rule 3) ----------------------------------------------------------------------------


def live_takes(
    comments: list, repo: str, number: int
) -> list[tuple[datetime, int, str, str, str | None]]:
    """(when, id, session, login, build) of every live take, oldest first; the pull requests are
    read only when a take is older than 24 hours. A later `released:` of the session frees its take
    of that build (or of every build when it names none)."""
    now = datetime.now(UTC)
    found, prs, freed = [], None, []
    for comment in comments:
        body = comment.get("body")
        text = body.strip() if isinstance(body, str) else ""
        if (gone := RELEASE.fullmatch(text)) is not None:
            freed.append((comment.get("id", 0), gone.group(1), gone.group(2)))
        match = TAKE.fullmatch(text)
        if not match:
            continue
        when, login = moment(comment.get("created_at")), author_of(comment)
        live = now - when < LIVE
        if not live:
            prs = mentioning(repo, number) if prs is None else prs
            live = any(author_of(pr) == login and moment(pr.get("created_at")) > when for pr in prs)
        if live:
            found.append((when, comment.get("id", 0), match.group(1), login, match.group(3)))
    return sorted(
        t
        for t in found
        if not any(f[0] > t[1] and f[1] == t[2] and f[2] in (None, t[4]) for f in freed)
    )


def mentioning(repo: str, number: int) -> list:
    """The pull requests that mention the issue as `#n` (none when they cannot be read)."""
    pattern = re.compile(rf"#{number}(?!\d)")
    prs = pages(f"repos/{repo}/pulls?state=all") or []
    return [p for p in prs if pattern.search(f"{p.get('title') or ''} {p.get('body') or ''}")]


def judge(repo: str, brief: dict, me: str) -> tuple[str | None, list]:
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
    takes = live_takes(comments, repo, brief["number"])
    if takes and not any(t[2] == me for t in takes):
        return f"taken by {takes[0][2]}", comments
    return None, comments


def take(repo: str, number: int, me: str, comments: list, build: str | None = None) -> str | None:
    """Post the take unless this session already holds one; the reason it was lost, or None.
    A take of a build conflicts with a take of the same build and with a take of the whole brief."""

    def rivals() -> list:
        found = live_takes(comments, repo, number)
        return [t for t in found if build is None or t[4] in (None, build)]

    if not any(t[2] == me and t[4] == build for t in rivals()):
        if other := [t for t in rivals() if t[2] != me]:
            return f"taken by {other[0][2]}"
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        part = f" build ({build})" if build else ""
        body = f"body=taken: {me} {day}{part}"
        if gh(f"repos/{repo}/issues/{number}/comments", "-f", body, method="POST") is None:
            return "the take cannot be posted"
        comments = pages(f"repos/{repo}/issues/{number}/comments") or []
    oldest = rivals()
    if oldest and oldest[0][2] != me:
        return f"lost the take to {oldest[0][2]}"
    return None


# --- a build claim, the answer of the conductor and `after` (SPEC-0034 rules 5 and 12) ----------


def flow_table(root) -> dict:
    try:
        data = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise CheckError("rule 12: agk.toml cannot be read") from exc
    flow = data.get("flow", {})
    return flow if isinstance(flow, dict) else {}


def assign_mode(root) -> str:
    """`assign` of the flow table: `conductor` or `next` (the default); another value is refused."""
    value = flow_table(root).get("assign", "next")
    if value not in ASSIGN_MODES:
        raise CheckError("rule 12: assign of the [flow] table must be conductor or next")
    return value


def claim_hours(root) -> int:
    value = flow_table(root).get("claim_hours", CLAIM_HOURS)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CheckError("rule 12: claim_hours of the flow table must be a whole number, 1 or more")
    return value


def claim(root, me: str, number: int, build: str | None) -> int:
    repo = repo_name(root)
    comments = pages(f"repos/{repo}/issues/{number}/comments")
    if comments is None:
        raise CheckError("rule 5: the comments of the brief cannot be read")
    if why := take(repo, number, me, comments, build):
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
    path = f"repos/{repo}/issues/{conductor_issue(repo)}/comments"
    interval = float(args.get("--interval", 60))
    limit = float(args.get("--timeout", claim_hours(root) * 3600))
    started = time.monotonic()
    comments = pages(path) or []
    asked = [c["id"] for c in comments if str(c.get("body") or "").startswith(f"Request: {me} ")]
    seen = max(asked, default=newest(comments) or 0)
    allowed = {a.lstrip("@").lower() for a in counted_authors(verdict_authors(root), None)}
    while True:
        for comment in sorted(pages(path) or [], key=lambda c: c.get("id", 0)):
            body = comment.get("body")
            first = body.splitlines()[0].strip() if isinstance(body, str) and body.strip() else ""
            match = ASSIGN.fullmatch(first)
            if comment.get("id", 0) > seen and match and match.group(1) == me:
                if author_of(comment) in allowed:
                    what = match.group(2)
                    print("assign " + (what if what == "none" else what))
                    return 0
        if time.monotonic() - started >= limit:
            print("assign-timeout")
            return 0
        time.sleep(interval)


def after(root, me: str) -> int:
    """Where a builder goes when its work is done, by `[flow] assign` (rule 12)."""
    if assign_mode(root) == "next":
        return next_brief(root, me)
    print(f"ask the conductor on #{conductor_issue(repo_name(root))}")
    return 0


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
    # While the default branch is red only its brief is handed out (SPEC-0032 rule 7).
    handed = sorted(
        red or (i for i in issues if "pull_request" not in i), key=lambda i: i["number"]
    )
    for brief in handed:
        why, comments = judge(repo, brief, me)
        why = why or take(repo, brief["number"], me, comments)
        if why:
            print(f"skip #{brief['number']}: {why}")
            continue
        print(f"brief #{brief['number']}\ntitle: {brief.get('title')}")
        print(f"address: {brief.get('html_url')}\n")
        print(brief["body"])
        return 0
    print("default branch red" if red else "no brief")
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
    try:
        data = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return STALL_HOURS
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise CheckError("rule 5: agk.toml cannot be read") from exc
    flow = data.get("flow", {})
    value = flow.get("stall_hours", STALL_HOURS) if isinstance(flow, dict) else STALL_HOURS
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CheckError("rule 5: stall_hours of the flow table must be a whole number, 1 or more")
    return value


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
    if (
        not args
        or args[0] not in ("watch", "next", "queue", "resume", "claim", "after")
        or len(args[1:]) % 2
    ):
        print(USAGE)
        return 2
    cmd, opts = args[0], dict(zip(args[1::2], args[2::2], strict=False))
    allowed = {
        "watch": {"--pr", "--merged", "--assign", "--interval", "--timeout"},
        "next": {"--session"},
        "claim": {"--session", "--brief", "--build"},
        "after": {"--session"},
        "queue": {"--role", "--author"},
        "resume": {"--pr"},
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
        return next_brief(root, opts["--session"])
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
