"""The steward's memory (SPEC-0059 rules 2, 8, 14 and 18; brief #1320, ADR-0557).

Usage: python3 scripts/agk/steward.py start --session ID
       python3 scripts/agk/steward.py record --kind KIND (--text TEXT | --file FILE)
       python3 scripts/agk/steward.py end --session ID [--calls N] [--tokens N]
       python3 scripts/agk/steward.py onboard [--again]

The memory is one open issue labelled `agk-steward`, created when none is open: one comment per
entry, whose first word is one of KINDS, each ending `Who: AGK steward`. `start` reads it before any
other step: the open listing, then the comments with `since=` from the last one seen (kept in a file
of the clone's git folder, or AGK_STEWARD_CACHE; never a tracked file), so a quiet start is at most
3 counted calls. It prints the newest entry of each kind first and names an entry of another first
word. A `Started: steward <session> <UTC time>` newer than 60 minutes with no `Ended: steward
<session>` after it, by another session, makes a start say so and write nothing (exit 1). At 500
comments a start opens a new memory issue whose first comment links the old one and carries every
open `Owner question:` (no later `Decision:` names its Q id), then closes the old one. `record`
refuses an unknown kind and a text that the data guard's detectors match, naming the class, never
the value (exit 2). `end` writes the pass's counted calls and tokens on its marker, `not shown` when
not given, never 0 (rule 13's daily list reads them). `onboard` is `steward_onboard.py onboard`
(SPEC-0059 rule 20, Q-S0059-14, brief #1325, ADR-0562). In personal mode (a `[personal]` table) the
memory is `docs/runs/steward/memory.md` of the sidecar and nothing is posted. A failed GitHub call
exits 4.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, personal_table, repo_root, utf8_output  # noqa: E402

KINDS = (
    "Decision",
    "Ranking",
    "Term",
    "Persona",
    "Pattern",
    "Gap",
    "Risk",
    "Lesson",
    "Owner question",
    "Triage",
    "Override",
    "Onboarded",
)
MARKERS = ("Started", "Ended", "Daily", "Shortened")
LABEL = "agk-steward"
TITLE = "AGK steward memory"
WHO = "Who: AGK steward"
ROLL_OVER = 500
LIVE = timedelta(minutes=60)
PAGE = 100
LISTING = f"repos/{{owner}}/{{repo}}/issues?labels={LABEL}&state=open&per_page=10"
ISSUES = "repos/{owner}/{repo}/issues"
PERSONAL_FILE = Path("docs") / "runs" / "steward" / "memory.md"
SEPARATOR = "\n---\n"
FIRST = re.compile(r"^(Owner question|[A-Z][a-z]+):")
STARTED = re.compile(r"^Started: steward (\S+) (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})Z")
ENDED = re.compile(r"^Ended: steward (\S+)")
QID = re.compile(r"\bQ-[\w-]+\b")

Gh = Callable[..., object]


class Unreadable(Exception):
    """A GitHub call failed: the memory cannot be read or written."""


def entry_kind(body: str) -> str | None:
    found = FIRST.match(body.lstrip())
    return found[1] if found and found[1] in (*KINDS, *MARKERS) else None


def read_memory(comments: list[dict]) -> dict:
    """{"newest": {kind: [entries newest first]}, "unknown": [ids of other first words]}."""
    newest: dict[str, list[dict]] = {}
    unknown = []
    for item in sorted(
        comments, key=lambda c: (c.get("created_at", ""), c.get("id", 0)), reverse=True
    ):
        kind = entry_kind(item.get("body", ""))
        if kind is None:
            unknown.append(item.get("id"))
        elif kind in KINDS:
            newest.setdefault(kind, []).append(item)
    return {"newest": newest, "unknown": sorted(unknown, key=lambda i: (i is None, i))}


def summary(memory: dict) -> list[str]:
    lines = []
    for kind in KINDS:
        entries = memory["newest"].get(kind, [])
        for item in entries[:3]:
            lines.append(item["body"].strip().splitlines()[0][:200])
        if len(entries) > 3:
            lines.append(f"{kind}: {len(entries) - 3} older entries")
    if memory["unknown"]:
        ids = ", ".join(str(i) for i in memory["unknown"])
        lines.append(f"unknown first word, read as text: comment {ids}")
    return lines


def live_start(comments: list[dict], session: str, now: datetime) -> str | None:
    """The other session whose `Started: steward` is newer than 60 minutes and not ended."""
    ordered = sorted(comments, key=lambda c: (c.get("created_at", ""), c.get("id", 0)))
    live: dict[str, datetime] = {}
    for item in ordered:
        body = item.get("body", "").lstrip()
        if found := STARTED.match(body):
            live[found[1]] = datetime.strptime(found[2], "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)
        elif found := ENDED.match(body):
            live.pop(found[1], None)
    return next((s for s, t in live.items() if s != session and now - t < LIVE), None)


def open_questions(comments: list[dict]) -> list[str]:
    decided = {
        q for c in comments if entry_kind(c["body"]) == "Decision" for q in QID.findall(c["body"])
    }
    asked = [
        c["body"].strip().splitlines()[0]
        for c in comments
        if entry_kind(c["body"]) == "Owner question"
    ]
    return [line for line in asked if not set(QID.findall(line)) & decided]


def stamp(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%MZ")


# --- the cache of what was read (never a tracked file) ------------------------------------------


def cache_file(root: Path) -> Path:
    if os.environ.get("AGK_STEWARD_CACHE"):
        return Path(os.environ["AGK_STEWARD_CACHE"])
    found = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    folder = Path(found.stdout.strip() or ".git")
    return (folder if folder.is_absolute() else root / folder) / "agk-steward-memory.json"


def load_cache(root: Path) -> dict:
    try:
        return json.loads(cache_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(root: Path, cache: dict) -> None:
    path = cache_file(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass  # a lost cache costs reads, never an entry


# --- GitHub mode ---------------------------------------------------------------------------------


def call(gh: Gh, method: str, endpoint: str, fields: dict | None = None):
    found = gh(method, endpoint, fields)
    if found is None:
        raise Unreadable(endpoint.split("?", 1)[0])
    return found


def comments_of(gh: Gh, number: int, since: str | None) -> list[dict]:
    out, page = [], 1
    while True:
        query = f"per_page={PAGE}" + (f"&since={since}" if since else "") + f"&page={page}"
        items = call(gh, "GET", f"{ISSUES}/{number}/comments?{query}")
        out += [{k: c.get(k) for k in ("id", "body", "created_at", "updated_at")} for c in items]
        if len(items) < PAGE:
            return out
        page += 1


def memory_issue(gh: Gh, root: Path, cache: dict) -> dict:
    """The open memory issue with its comments current in the cache; created when none is open."""
    listed = [i for i in call(gh, "GET", LISTING) if "pull_request" not in i]
    if not listed:
        listed = [
            call(
                gh,
                "POST",
                ISSUES,
                {"title": TITLE, "body": "The steward's notes.", "labels": [LABEL]},
            )
        ]
    issue = max(listed, key=lambda i: i["number"])
    if cache.get("issue") != issue["number"]:
        cache.clear()
        cache.update({"issue": issue["number"], "comments": []})
    if issue.get("comments", 0) != len(cache["comments"]):
        known = {c["id"]: c for c in cache["comments"]}
        since = max((c.get("updated_at") or "" for c in known.values()), default="") or None
        for item in comments_of(gh, issue["number"], since):
            known[item["id"]] = item
        if len(known) != issue.get("comments", 0) and since:
            known = {c["id"]: c for c in comments_of(gh, issue["number"], None)}  # a deleted one
        cache["comments"] = sorted(
            known.values(), key=lambda c: (c.get("created_at") or "", c["id"])
        )
    return issue


def post(gh: Gh, cache: dict, text: str) -> None:
    item = call(gh, "POST", f"{ISSUES}/{cache['issue']}/comments", {"body": f"{text}\n\n{WHO}\n"})
    cache["comments"].append({k: item.get(k) for k in ("id", "body", "created_at", "updated_at")})


def roll_over(gh: Gh, cache: dict) -> None:
    old, carried = cache["issue"], open_questions(cache["comments"])
    new = call(
        gh, "POST", ISSUES, {"title": TITLE, "body": f"Continues #{old}.", "labels": [LABEL]}
    )
    cache.clear()
    cache.update({"issue": new["number"], "comments": []})
    lines = [
        f"Memory continued from #{old}; open owner questions carried forward:",
        *(carried or ["none"]),
    ]
    post(gh, cache, "\n".join(lines))
    call(gh, "PATCH", f"{ISSUES}/{old}", {"state": "closed"})


# --- personal mode (rule 14): a sidecar file, nothing posted -------------------------------------


def personal_entries(root: Path) -> list[dict]:
    path = root / PERSONAL_FILE
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    parts = [p.strip() for p in text.split(SEPARATOR) if p.strip()]
    return [{"id": n, "body": p, "created_at": f"{n:08d}"} for n, p in enumerate(parts, 1)]


def personal_append(root: Path, text: str) -> None:
    path = root / PERSONAL_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as out:
        out.write(f"{text.strip()}{SEPARATOR}")


# --- the commands ---------------------------------------------------------------------------------


def start(root: Path, session: str, gh: Gh, now: datetime) -> tuple[int, list[str]]:
    if personal_table(root) is not None:
        comments = personal_entries(root)
        if other := live_start(comments, session, now):
            return 1, [f"steward already running: {other}; this start writes nothing"]
        personal_append(root, f"Started: steward {session} {stamp(now)}")
        return 0, [f"memory: {PERSONAL_FILE.as_posix()}", *summary(read_memory(comments))]
    cache = load_cache(root)
    issue = memory_issue(gh, root, cache)
    if other := live_start(cache["comments"], session, now):
        save_cache(root, cache)
        return 1, [f"steward already running: {other}; this start writes nothing"]
    if issue.get("comments", 0) >= ROLL_OVER:
        if len(cache["comments"]) < issue["comments"]:
            cache["comments"] = comments_of(gh, issue["number"], None)
        roll_over(gh, cache)
    memory = read_memory(cache["comments"])
    post(gh, cache, f"Started: steward {session} {stamp(now)}")
    save_cache(root, cache)
    return 0, [f"memory: #{cache['issue']}", *summary(memory)]


def end(
    root: Path, session: str, gh: Gh, now: datetime, calls: int | None = None, tokens=None
) -> tuple[int, list[str]]:
    del now  # the marker names the session; its time is the comment's own
    figures = f" calls {calls or 'not shown'}; tokens {tokens or 'not shown'}"
    return write(root, f"Ended: steward {session}{figures}", gh)


def record(root: Path, kind: str, text: str, gh: Gh) -> tuple[int, list[str]]:
    if kind not in KINDS:
        return 2, ["refused: not a memory kind (setting: the first word of rule 8)"]
    from guard import scan_text

    from config import guard_patterns

    findings = scan_text(f"{kind}: {text}", guard_patterns(root))
    if findings:
        classes = ", ".join(sorted({f.kind for f in findings}))
        return 2, [f"refused: the text holds {classes} (setting: [guard]; data guard, SPEC-0042)"]
    return write(root, f"{kind}: {text.strip()}", gh)


def write(root: Path, text: str, gh: Gh) -> tuple[int, list[str]]:
    if personal_table(root) is not None:
        personal_append(root, text)
        return 0, [f"recorded in {PERSONAL_FILE.as_posix()}"]
    cache = load_cache(root)
    if "issue" not in cache:
        memory_issue(gh, root, cache)
    post(gh, cache, text)
    save_cache(root, cache)
    return 0, [f"recorded on #{cache['issue']}"]


def gh_api(method: str, endpoint: str, fields: dict | None = None):
    """One `gh api` call; None when it fails or answers no JSON."""
    args = ["gh", "api", "-X", method, endpoint]
    if fields is not None:
        args += ["--input", "-"]
    found = subprocess.run(  # nosec B603 - fixed argument list, no shell
        args,
        input=json.dumps(fields) if fields is not None else None,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    try:
        return json.loads(found.stdout) if found.returncode == 0 else None
    except ValueError:
        return None


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(prog="steward.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("start").add_argument("--session", required=True)
    end_p = sub.add_parser("end")
    end_p.add_argument("--session", required=True)
    end_p.add_argument("--calls", type=int)
    end_p.add_argument("--tokens", type=int)
    sub.add_parser("onboard").add_argument("--again", action="store_true")
    rec = sub.add_parser("record")
    rec.add_argument("--kind", required=True)
    group = rec.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--file", type=Path)
    opts = parser.parse_args(argv)
    root, now = repo_root(), datetime.now(UTC)
    if opts.command == "onboard":
        import steward_onboard

        return steward_onboard.run(root, opts.again)
    try:
        if opts.command == "record":
            text = opts.text if opts.text is not None else opts.file.read_text(encoding="utf-8")
            code, lines = record(root, opts.kind, text, gh_api)
        elif opts.command == "start":
            code, lines = start(root, opts.session, gh_api, now)
        else:
            code, lines = end(root, opts.session, gh_api, now, opts.calls, opts.tokens)
    except Unreadable as exc:
        print(f"error: {exc} cannot be read", file=sys.stderr)
        return 4
    except (CheckError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
