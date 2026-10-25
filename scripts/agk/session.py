"""What a builder session reads from GitHub: its verdicts and its next brief (SPEC-0030).

    python3 session.py watch --pr N [--interval S] [--timeout S]
    python3 session.py watch --merged N [--interval S] [--timeout S]
    python3 session.py next --session ID

`watch` polls with `gh api --method GET` and exits 0 with one line: `verdict <kind> <sha> (comment
<id>)` for a verdict by a listed author that names a prefix of the current head and is newer than
the newest comment seen at the start, `merged #N` or `closed #N`; with `--timeout` and no event it
prints `timeout` and exits 3. `--pr` also ends with `conflict #N` when the pull request
conflicts with its base (`mergeable_state` dirty), since CI does not start on it.
`--merged N` waits on that pull request alone and ignores comments.
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
from datetime import UTC, datetime, timedelta
from typing import Any

from common import CheckError, git, repo_root
from facts import ORIGIN
from metrics import author_of, counted_authors
from reviewers import verdict_authors

NAME = "session"
USAGE = (
    "usage: session.py watch (--pr N | --merged N) [--interval S] [--timeout S]\n"
    "       session.py next --session ID"
)
PAGE = 100
LABEL = "agk-brief"
LIVE = timedelta(hours=24)
VERDICT = re.compile(r"Verdict: (cleared|fix list|rejected) ([0-9a-f]{7,40})")
TAKE = re.compile(r"taken: (\S+) (\d{4}-\d{2}-\d{2})")
SENTENCE = re.compile(r'Sentence: "(.*)"')
DEPENDS = re.compile(r"Depends-on: #(\d+)")
SIZE = re.compile(r"Size: [SML]")
NUMBERED = re.compile(r"(\d+)\.\s+\S")
SESSION_ID = re.compile(r"[A-Za-z0-9._-]+")
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


def watch(root, args: dict[str, str]) -> int:
    repo = repo_name(root)
    number = args.get("--pr") or args["--merged"]
    only_merge = "--merged" in args
    interval, limit = float(args.get("--interval", 60)), args.get("--timeout")
    started = time.monotonic()

    def late() -> bool:
        return limit is not None and time.monotonic() - started >= float(limit)

    seen = 0
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
    return problems


def depends_on(body: str) -> list[int]:
    found = (DEPENDS.fullmatch(x.rstrip()) for x in body.splitlines())
    return [int(m.group(1)) for m in found if m]


# --- next (rule 3) ----------------------------------------------------------------------------


def live_takes(comments: list, repo: str, number: int) -> list[tuple[datetime, int, str, str]]:
    """(when, id, session, login) of every live take, oldest first; the pull requests are read
    only when a take is older than 24 hours."""
    now = datetime.now(UTC)
    found, prs = [], None
    for comment in comments:
        body = comment.get("body")
        match = TAKE.fullmatch(body.strip()) if isinstance(body, str) else None
        if not match:
            continue
        when, login = moment(comment.get("created_at")), author_of(comment)
        live = now - when < LIVE
        if not live:
            prs = mentioning(repo, number) if prs is None else prs
            live = any(author_of(pr) == login and moment(pr.get("created_at")) > when for pr in prs)
        if live:
            found.append((when, comment.get("id", 0), match.group(1), login))
    return sorted(found)


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


def take(repo: str, number: int, me: str, comments: list) -> str | None:
    """Post the take unless this session already holds one; the reason it was lost, or None."""
    if not any(t[2] == me for t in live_takes(comments, repo, number)):
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        body = f"body=taken: {me} {day}"
        if gh(f"repos/{repo}/issues/{number}/comments", "-f", body, method="POST") is None:
            return "the take cannot be posted"
        comments = pages(f"repos/{repo}/issues/{number}/comments") or []
    oldest = live_takes(comments, repo, number)
    if oldest and oldest[0][2] != me:
        return f"lost the take to {oldest[0][2]}"
    return None


def next_brief(root, me: str) -> int:
    repo = repo_name(root)
    issues = pages(f"repos/{repo}/issues?state=open&labels={LABEL}")
    if issues is None:
        raise CheckError("rule 3: the open briefs cannot be read")
    for brief in sorted((i for i in issues if "pull_request" not in i), key=lambda i: i["number"]):
        why, comments = judge(repo, brief, me)
        why = why or take(repo, brief["number"], me, comments)
        if why:
            print(f"skip #{brief['number']}: {why}")
            continue
        print(f"brief #{brief['number']}\ntitle: {brief.get('title')}")
        print(f"address: {brief.get('html_url')}\n")
        print(brief["body"])
        return 0
    print("no brief")
    return 1


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
    if not args or args[0] not in ("watch", "next") or len(args[1:]) % 2:
        print(USAGE)
        return 2
    cmd, opts = args[0], dict(zip(args[1::2], args[2::2], strict=False))
    allowed = {"watch": {"--pr", "--merged", "--interval", "--timeout"}, "next": {"--session"}}
    if not set(opts) <= allowed[cmd] or len(opts) != len(args[1::2]):
        print(USAGE)
        return 2
    if cmd == "watch":
        ok = ("--pr" in opts) != ("--merged" in opts) and number_of(
            opts.get("--pr") or opts.get("--merged")
        )
        ok = ok and all(number_ok(opts[k]) for k in ("--interval", "--timeout") if k in opts)
    else:
        ok = bool(SESSION_ID.fullmatch(opts.get("--session", "")))
    if not ok:
        print(USAGE)
        return 2
    try:
        root = repo_root()
        return watch(root, opts) if cmd == "watch" else next_brief(root, opts["--session"])
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
