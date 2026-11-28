# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The steward's memory (SPEC-0059 rules 2, 8, 14 and 18; brief #1320, ADR-0557).

Usage: python3 scripts/agk/steward.py start --session ID
       python3 scripts/agk/steward.py record --kind KIND (--text TEXT | --file FILE)
                                      [--repeat ID | --prevent-of ID]
       python3 scripts/agk/steward.py show ID
       python3 scripts/agk/steward.py find WORD
       python3 scripts/agk/steward.py refresh --session ID [--since UTC-TIME]
       python3 scripts/agk/steward.py end --session ID [--calls N] [--tokens N]
       python3 scripts/agk/steward.py onboard [--again]
       python3 scripts/agk/steward.py setup [--adopted] [--detect FILE] [--answer TEXT]
       python3 scripts/agk/steward.py first-run [--folder DIR]

The memory is one open issue labelled `agk-steward`, created when none is open: one comment per
entry, whose first word is one of KINDS, each ending `Who: AGK steward`. `start` reads it before any
other step: the open listing, then the comments with `since=` from the last one seen (kept in a file
of the clone's git folder, or AGK_STEWARD_CACHE; never a tracked file), so a quiet start is at most
3 counted calls. It prints the newest entry of each kind first and names an entry of another first
word. A `Started: steward <session> <UTC time> [beat <UTC time>]` whose newer time is within 60
minutes, with no `Ended: steward <session>` after it, of any name, the starting one included, makes
a start say so and write nothing (exit 1); `refresh` and `record` beat on the run's own marker (one
PATCH), and `record` and `end` refuse with no start in this clone (brief #1741, ADR-0726). At 500
comments a start opens a new memory issue whose first comment links the old one and carries every
open `Owner question:` (no `Decision:` or `Maintainer answer:` names its Q id), then closes the old
one; the start lists only those open ones, at most three, and counts the answered (brief #1765).
`record` refuses an unknown kind and a text that the data guard's detectors match, naming the
class, never the value (exit 2). `end` writes the pass's counted calls and tokens on its marker,
`not shown` when not given, never 0 (rule 13's daily list reads them). `start` keeps a checkpoint
in the cache;
`refresh` posts nothing and prints only what changed since it, in three GET calls: the new or
edited memory comments (a `Decision:` or `Maintainer answer:` first), the open pull requests whose
head or labels changed and the ones closed or merged, then moves it (brief #1702, ADR-0708).
`onboard` is `steward_onboard.py onboard`
(SPEC-0059 rule 20, Q-S0059-14, brief #1325, ADR-0562). In solo mode a start with no `Person:` entry
prints the one question of SPEC-0062 rule 4, and `record --kind Person` takes `<business|technical>:
<their words>` and ends `Who: ProductOwner` (rule 15; brief #1598, ADR-0678). `setup` prints one
`Setup: <matter>: <choice> because <reason>` line per AGK matter, the plain questions and, with the
person's `--answer`, the install command; after the install it refuses `--answer` (SPEC-0062 rules
2, 9 and 11; brief #1599, ADR-0679). In personal mode
(a `[personal]` table) the memory is `docs/runs/steward/memory.md` of the sidecar and nothing is
posted. A failed GitHub call exits 4. Outside a git repository every command but `first-run`
prints `outside: no project here`, exit 3, and writes nothing; `first-run` prints `first-run:
<step>`, one of `kit`, `project`, `adopt`, `greet` and `greeted`, and writes only the greeting mark
of a `greet` to the person's Claude folder (SPEC-0066 rule 8; brief #1583, ADR-0663).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (  # noqa: E402
    OUTSIDE_PROJECT,
    CheckError,
    branch_check,
    personal_table,
    repo_root,
    review_mode,
    utf8_output,
)  # noqa: E402
from usage import tokens_figure  # noqa: E402  (brief #2020 answer 5)

KINDS = (
    "Decision",
    "Ranking",
    "Term",
    "Persona",
    "Person",
    "Pattern",
    "Gap",
    "Risk",
    "Lesson",
    "Owner question",
    "Triage",
    "Override",
    "Onboarded",
    "Setup",
    "Note",  # brief #1741 (ADR-0726): the kinds the runs write are memory
    "Owner list",
    "Morning list for the owner",
    "Draft brief",
    "Filed",
)
MARKERS = ("Started", "Ended", "Daily", "Shortened")
LABEL = "agk-steward"
TITLE = "AGK steward memory"
WHO = "Who: AGK steward"
OWNER_WHO = "Who: ProductOwner"
PERSON = re.compile(r"(?:business|technical): \S.*", re.S)
QUESTION = (
    "Tell me in your own words what you want to build and who it is for; are you coming at this"
    " from the business side or the technical side?"
)
SETUP = re.compile(r"[^:\n]+: \S.* because \S.*", re.S)
# SPEC-0062 rules 2, 9 and 11 (brief #1599, ADR-0679): the only setup questions are plain ones.
ALONE_QUESTION = (
    "Will you run this alone, or with a team? Alone (recommended for one person) · with a team"
)
REST_QUESTION = "When do you rest?"
STACK_TESTS = {
    "python-pyproject": "python3 -m pytest -q",
    "python-pip": "python3 -m pytest -q",
    "node": "npm test",
    "go-modules": "go test ./...",
    "rust-cargo": "cargo test",
    "java-maven": "mvn -q test",
    "java-gradle": "./gradlew test",
    "dart-pub": "dart test",
}
LOGIN_ENV = "AGK_SETUP_LOGIN"  # init.py's; the login is read by `gh api user` and never printed
ROLL_OVER = 500
LIVE = timedelta(minutes=60)
PAGE = 100
LISTING = f"repos/{{owner}}/{{repo}}/issues?labels={LABEL}&state=open&per_page=10"
ISSUES = "repos/{owner}/{repo}/issues"
PULLS = "repos/{owner}/{repo}/pulls"
URGENT = ("Decision:", "Maintainer answer:")
NO_CHECKPOINT = (
    "refresh: no checkpoint (setting: AGK_STEWARD_CACHE); run start, or pass --since <UTC time>"
)
PERSONAL_PULLS = "pull requests: not read in personal mode"
PERSONAL_FILE = Path("docs") / "runs" / "steward" / "memory.md"
SEPARATOR = "\n---\n"
MULTI = sorted((k for k in KINDS if " " in k), key=len, reverse=True)
FIRST = re.compile(r"^(" + "|".join(map(re.escape, MULTI)) + r"|[A-Z][a-z]+):")
STARTED = re.compile(r"^Started: steward (\S+) (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})Z")
BEAT = re.compile(r"^Started: steward \S+ \S+ beat (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})Z")
DRAFT_ID = re.compile(r"F-[\w.-]+")
DRAFT_FOR_OWNER = re.compile(r"draft for the owner", re.I)
ONLY_NEWEST = ("Owner list", "Morning list for the owner")
NO_START = "refused: no live start in this clone; run steward.py start --session <session> first"
ENDED = re.compile(r"^Ended: steward (\S+)")
QID = re.compile(r"\bQ-[\w-]+\b")

Gh = Callable[..., object]


class Unreadable(Exception):
    """A GitHub call failed: the memory cannot be read or written."""


def entry_kind(body: str) -> str | None:
    found = FIRST.match(body.lstrip())
    return found[1] if found and found[1] in (*KINDS, *MARKERS) else None


def read_memory(comments: list[dict]) -> dict:
    """{"newest": {kind: [entries newest first]}, "unknown": [ids of other first words],
    "comments": [every comment, newest first]}."""
    newest: dict[str, list[dict]] = {}
    unknown = []
    ordered = sorted(
        comments, key=lambda c: (c.get("created_at", ""), c.get("id", 0)), reverse=True
    )
    for item in ordered:
        kind = entry_kind(item.get("body", ""))
        if kind is None:
            unknown.append(item.get("id"))
        elif kind in KINDS:
            newest.setdefault(kind, []).append(item)
    unknown.sort(key=lambda i: (i is None, i))
    return {"newest": newest, "unknown": unknown, "comments": ordered}


def body_lines(item: dict) -> list[str]:
    """Every line of an entry, without its closing `Who:` line and blank lines."""
    lines = [line.rstrip() for line in (item.get("body") or "").strip().splitlines()]
    return [line[:200] for line in lines if line.strip() and not line.startswith("Who: ")]


def unfiled_drafts(comments: list[dict]) -> list[dict]:
    """Each `Draft brief:` that no later `Filed:` names by its id, oldest first."""
    ordered = sorted(comments, key=lambda c: (c.get("created_at") or "", c.get("id") or 0))
    drafts: dict[str, dict] = {}
    for item in ordered:
        kind, body = entry_kind(item.get("body", "")), item.get("body", "")
        if kind == "Draft brief" and (found := DRAFT_ID.search(body.split("\n", 1)[0])):
            drafts[found[0]] = item
        elif kind == "Filed":
            for name in DRAFT_ID.findall(body):
                drafts.pop(name, None)
    return list(drafts.values())


def draft_ids(comments: list[dict]) -> set[str]:
    return {
        found[0]
        for c in comments
        if entry_kind(c.get("body", "")) == "Draft brief"
        and (found := DRAFT_ID.search(c.get("body", "").split("\n", 1)[0]))
    }


def summary(memory: dict) -> list[str]:
    lines = []
    for kind in KINDS:
        entries = memory["newest"].get(kind, [])
        if kind == "Note" and entries:  # brief #1741 answer 4: every line of the newest note
            lines += body_lines(entries[0])
            if len(entries) > 1:
                lines.append(f"Note: {len(entries) - 1} older entries")
            continue
        if kind == "Draft brief":
            for item in reversed(unfiled_drafts(entries + memory["newest"].get("Filed", []))):
                lines += body_lines(item)
            continue
        if kind == "Owner question":  # brief #1765 answers 1 and 2: open first, answered counted
            still = open_questions(memory.get("comments", entries))
            lines += [line[:200] for line in still[:3]]
            if len(still) > 3:
                lines.append(f"Owner question: {len(still) - 3} more open")
            if len(entries) > len(still):
                lines.append(f"Owner question: {len(entries) - len(still)} answered")
            continue
        if kind in ONLY_NEWEST:
            lines += [item["body"].strip().splitlines()[0][:200] for item in entries[:1]]
            continue
        for item in entries[:3]:
            lines.append(item["body"].strip().splitlines()[0][:200])
        if len(entries) > 3:
            lines.append(f"{kind}: {len(entries) - 3} older entries")
    if memory["unknown"]:
        ids = ", ".join(str(i) for i in memory["unknown"])
        lines.append(f"unknown first word, read as text: comment {ids}")
    return lines


def minute(text: str) -> datetime | None:
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)
    except ValueError:
        return None


def runs(comments: list[dict]) -> dict[str, dict]:
    """The runs not ended: {session: {"start", "last" (the newer of start and beat), "id"}}.
    A later `Started:` closes every earlier run, since a start is written only when none is live
    (brief #1741, ADR-0726); a malformed beat is read as the start time alone."""
    ordered = sorted(comments, key=lambda c: (c.get("created_at") or "", c.get("id") or 0))
    open_runs: dict[str, dict] = {}
    for item in ordered:
        body = (item.get("body") or "").lstrip()
        if (found := STARTED.match(body)) and (begun := minute(found[2])):
            beat = BEAT.match(body)
            beaten = minute(beat[1]) if beat else None
            open_runs = {
                found[1]: {
                    "start": begun,
                    "last": max(begun, beaten or begun),
                    "id": item.get("id"),
                }
            }
        elif found := ENDED.match(body):
            open_runs.pop(found[1], None)
    return open_runs


def live_run(comments: list[dict], now: datetime) -> tuple[str, datetime] | None:
    """The run, of any name, whose newest start or beat is within 60 minutes and not ended."""
    return next(
        ((s, r["start"]) for s, r in runs(comments).items() if now - r["last"] < LIVE), None
    )


def live_start(comments: list[dict], session: str, now: datetime) -> str | None:
    """The session of a live run, whatever its name, the starting one included (brief #1741)."""
    del session
    found = live_run(comments, now)
    return found[0] if found else None


def stale_lines(comments: list[dict], now: datetime) -> list[str]:
    return [
        f"previous run {s} ended without Ended (last beat {stamp(r['last'])})"
        for s, r in runs(comments).items()
        if now - r["last"] >= LIVE
    ]


def refused_start(session: str, other: tuple[str, datetime]) -> list[str]:
    lines = [
        f"steward already running: {other[0]} since {stamp(other[1])}; this start writes nothing"
    ]
    if os.environ.get("AGK_STEWARD_START") == "conductor":  # SPEC-0059 rule 2: never silent
        lines.insert(
            0, f"stuck: steward {session} not started (steward already running: {other[0]})"
        )
    return lines


def open_questions(comments: list[dict]) -> list[str]:
    answers = [c["body"] for c in comments if entry_kind(c["body"]) == "Decision"]
    answers += [c["body"] for c in comments if c["body"].lstrip().startswith("Maintainer answer:")]
    decided = {q for body in answers for q in QID.findall(body)}  # brief #1765 answer 2
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


# --- the digest: the memory in force (brief #2098, ADR-0873) -----------------------------------

SCHEMA = 1
DIGEST_LIMIT = 30_000  # Q-S4-2: fixed constants, no setting
WIDTH = 200
SHOWN = 80
WINDOW = timedelta(days=14)  # rule 13's window for `Gap:`, `Risk:` and `Override:`
OVERLAP = timedelta(seconds=120)
CAPS = {"Decision": 40, "Lesson": 40, "Owner question": 20}
CAPS |= dict.fromkeys(("Ranking", "Term", "Persona", "Pattern", "Gap", "Risk", "Override"), 20)
ONE = ("Person", "Onboarded", "Note", "Owner list", "Morning list for the owner", "Daily")
WINDOWED = ("Gap", "Risk", "Override")
NOT_KEPT = ("Triage", "Filed")
HEAD = re.compile(
    r"^Memory in force \(schema (\d+), through (\d+) (\S+), checked (\d{4}-\d{2}-\d{2})\)$"
)
NOTE_LINE = re.compile(r"^(\d+) #(\d+) (\S+) (.+)$")
COUNT_LINE = re.compile(r"^([A-Z][A-Za-z ]*): (\d+) (older|answered|filed|not kept), on (.+)$")
PREVENT = re.compile(
    r"^Prevent: (done (?:check|tool|skill) \S+ (?:[0-9a-f]{7}|#\d+)|brief #(\d+)|draft (F-[\w.-]+)"
    r"|kit-defect #\d+)[ \t]*$",
    re.M,
)
PREVENT_ANY = re.compile(r"^Prevent:", re.M)
REPEAT = re.compile(r"^Lesson: repeat of (\d+):")
PREVENT_OF = re.compile(r"^Lesson: prevention of (\d+)\b")
KIT_PATHS = ("scripts/agk/", ".claude/", "skills/")
DIGEST_FILE = Path("docs") / "runs" / "steward" / "memory-digest.md"
NO_PREVENT = "the Prevent: line of a Lesson"


def first_line(item: dict) -> str:
    return ((item.get("body") or "").strip().splitlines() or [""])[0].strip()


def order(item: dict) -> tuple:
    return (item.get("created_at") or "", item.get("id") or 0)


def form_of(item: dict) -> str | None:
    found = PREVENT.search(item.get("body") or "")
    return found[1] if found else None


def lessons_in(notes: list[dict]) -> dict[int, dict]:
    """Each first `Lesson:` by id with `seen`, `last` and `prevent`; a repeat counts once by id."""
    held: dict[int, dict] = {}
    for item in sorted(notes, key=order):
        body = (item.get("body") or "").lstrip()
        if entry_kind(body) != "Lesson":
            continue
        ref = REPEAT.match(body) or PREVENT_OF.match(body)
        if ref is None:
            seen, last = item.get("seen", 1), item.get("last", item["id"])
            lesson = {"item": item, "seen": seen, "last": last, "state": item.get("state")}
            held[item["id"]] = lesson | {"prevent": item.get("prevent") or form_of(item)}
            continue
        if (target := held.get(int(ref[1]))) is None:
            continue
        if REPEAT.match(body) and item["id"] > target["last"]:
            target["seen"], target["last"] = target["seen"] + 1, item["id"]
        if (found := form_of(item)) and item["id"] >= target.get("formed", 0):
            target.update({"prevent": found, "formed": item["id"], "state": None})
    return held


def brief_state(cache: dict, form: str | None) -> str | None:
    """Answer 9 (Q-2098-2): a `brief #<n>` prevention's state, from the issues the daily read."""
    found = re.fullmatch(r"brief #(\d+)", form or "")
    return (cache.get("issues_read") or {}).get(found[1]) if found else None


def recent(item: dict, now: datetime) -> bool:
    try:
        made = datetime.fromisoformat((item.get("created_at") or "").replace("Z", "+00:00"))
    except ValueError:
        return True  # a sidecar entry has no time: kept
    return now - made <= WINDOW


def in_force(cache: dict, now: datetime) -> tuple[list[dict], dict]:
    """Brief #2098 answer 3: the notes kept, and the rest counted by kind, reason and issue."""
    current = cache.get("issue") or 0
    counts = {k: dict(v) for k, v in (cache.get("base") or {}).items()}

    def drop(item: dict, kind: str, why: str = "older") -> None:
        slot = counts.setdefault(f"{kind}|{why}", {})
        key = str(item.get("issue") or current)
        slot[key] = slot.get(key, 0) + 1

    notes = sorted(cache.get("comments") or [], key=order, reverse=True)  # newest first
    live = {run["id"] for run in runs(notes).values()}
    lessons = lessons_in(notes)
    bodies = [n.get("body") or "" for n in notes]
    decided = {
        q
        for b in bodies
        if entry_kind(b) == "Decision" or b.lstrip().startswith("Maintainer answer:")
        for q in QID.findall(b)
    }
    filed = {d for b in bodies if entry_kind(b) == "Filed" for d in DRAFT_ID.findall(b)}
    kept: list[dict] = []
    taken: dict[str, int] = {}
    seen_q: set[str] = set()
    matters: set[str] = set()
    for item in notes:
        kind = entry_kind(item.get("body") or "")
        if kind in ("Started", "Ended", "Shortened"):
            if item.get("id") in live:
                kept.append(item)
            continue
        if kind is None or kind in NOT_KEPT:
            drop(item, kind or "Other", "not kept")
            continue
        if kind == "Lesson":
            if item.get("id") not in lessons:
                continue  # a repeat or a prevention: folded into its first note
            item = {**item, **{k: lessons[item["id"]][k] for k in ("seen", "last", "prevent")}}
            item["state"] = brief_state(cache, item.get("prevent")) or lessons[item["id"]]["state"]
        why = "older"
        if kind == "Decision":
            ids = set(QID.findall(first_line(item)))
            if ids & seen_q:
                drop(item, kind)
                continue
            seen_q |= ids
        if kind == "Owner question" and set(QID.findall(first_line(item))) & decided:
            drop(item, kind, "answered")
            continue
        if kind == "Draft brief":
            draft = DRAFT_ID.search(first_line(item))
            if draft and draft[0] in filed:
                drop(item, kind, "filed")
            else:
                kept.append(item)
            continue
        if kind == "Setup":
            matter = first_line(item).split(":", 2)[1].strip()
            if matter in matters:
                drop(item, kind)
                continue
            matters.add(matter)
            kept.append(item)
            continue
        limit = 1 if kind in ONE else CAPS.get(kind, 20)
        if taken.get(kind, 0) >= limit or (kind in WINDOWED and not recent(item, now)):
            drop(item, kind, why)
            continue
        taken[kind] = taken.get(kind, 0) + 1
        kept.append(item)
    while kept and sum(len(note_line(i, current)) + 1 for i in kept) > DIGEST_LIMIT - 2000:
        capped = [i for i in kept if entry_kind(i.get("body") or "") in CAPS]
        if not capped:
            break
        oldest = min(capped, key=order)  # answer 9: the oldest capped line becomes a count
        kept.remove(oldest)
        drop(oldest, entry_kind(oldest["body"]) or "Other")
    return kept, counts


def note_line(item: dict, current: int) -> str:
    head = f"{item.get('id')} #{item.get('issue') or current} {item.get('created_at') or '-'}"
    text = first_line(item).replace(" | ", " / ")
    if entry_kind(text) == "Lesson":
        tail = f" | seen {item.get('seen', 1)} last {item.get('last', item.get('id'))}"
        tail += f" | prevention {item.get('prevent') or 'none'}"
        tail += f" ({item['state']})" if item.get("state") else ""
        return f"{head} {text[: WIDTH - len(head) - len(tail) - 1]}{tail}"[:WIDTH]
    return f"{head} {text}"[:WIDTH]


def digest_text(cache: dict, now: datetime) -> tuple[str, list[dict]]:
    """The body: the first line, a hash of the rest, the chain, the counts and one line a note."""
    current = cache.get("issue") or 0
    kept, counts = in_force(cache, now)
    mine = [c for c in cache.get("comments") or [] if (c.get("issue") or current) == current]
    through = max((c.get("id") or 0 for c in mine), default=0)
    at = max([cache.get("through_at") or "", *(c.get("updated_at") or "" for c in mine)])
    chain = " ".join(f"#{n}" for n in cache.get("chain") or [])
    rest = [f"Chain: {chain + ' and ' if chain else ''}this issue"]
    for key in sorted(counts):
        kind, why = key.split("|")
        spread = counts[key]
        where = ", ".join(f"#{n} ({spread[n]})" for n in sorted(spread, key=int))
        rest.append(f"{kind}: {sum(spread.values())} {why}, on {where}")
    rest += [note_line(i, current) for i in sorted(kept, key=order, reverse=True)]
    checked = cache.get("checked") or now.date().isoformat()
    first = f"Memory in force (schema {SCHEMA}, through {through} {at or seconds(now)}"
    first += f", checked {checked})"
    digest = hashlib.sha256("\n".join(rest).encode("utf-8")).hexdigest()[:16]
    return "\n".join([first, f"Hash: {digest}", *rest]) + "\n", kept


def parse_digest(text: str | None) -> dict | str:
    """The digest's state, or why it is rebuilt: missing, unparsable, schema or edited."""
    lines = [line.rstrip() for line in (text or "").strip().splitlines()]
    if not lines or not lines[0].startswith("Memory in force ("):
        return "missing"
    head = HEAD.match(lines[0])
    if head is None or len(lines) < 3 or not lines[2].startswith("Chain: "):
        return "unparsable"
    if int(head[1]) != SCHEMA:
        return "schema"
    if lines[1] != "Hash: " + hashlib.sha256("\n".join(lines[2:]).encode()).hexdigest()[:16]:
        return "edited"
    chain = [int(n) for n in re.findall(r"#(\d+)", lines[2])]
    state: dict = {"through": int(head[2]), "through_at": head[3], "checked": head[4]}
    state |= {"chain": chain, "counts": {}, "notes": []}
    for line in lines[3:]:
        if count := COUNT_LINE.match(line):
            state["counts"][f"{count[1]}|{count[3]}"] = {
                n: int(k) for n, k in re.findall(r"#(\d+) \((\d+)\)", count[4])
            }
        elif note := NOTE_LINE.match(line):
            parts = note[4].split(" | ")
            item = {"id": int(note[1]), "issue": int(note[2]), "created_at": note[3]}
            item |= {"updated_at": note[3], "body": parts[0]}
            if len(parts) == 3 and entry_kind(parts[0]) == "Lesson":
                seen = re.match(r"seen (\d+) last (\d+)", parts[1])
                form = parts[2].removeprefix("prevention ")
                if said := re.search(r" \((open|closed|not an issue)\)$", form):
                    item["state"], form = said[1], form[: said.start()]
                item |= {"seen": int(seen[1]), "last": int(seen[2])} if seen else {}
                if form != "none":
                    item |= {"prevent": form, "body": f"{parts[0]}\nPrevent: {form}"}
            state["notes"].append(item)
        else:
            return "unparsable"
    return state


def seed(cache: dict, state: dict) -> None:
    cache.update({"comments": state["notes"], "base": state["counts"], "chain": state["chain"]})
    cache.update({"through_at": state["through_at"], "checked": state["checked"], "read": True})
    cache["through"] = state["through"]


def full_read(gh: Gh, cache: dict, state: dict | str, issue: dict, today: str) -> None:
    """Answer 5: every page of the open issue; the older issues' notes as the digest held them."""
    number = issue["number"]
    pages = comments_of(gh, number, None) if issue.get("comments", 0) else []
    old = state if isinstance(state, dict) else {"notes": [], "counts": {}, "chain": []}
    carried = [n for n in old["notes"] if n.get("issue") != number]
    base = {k: {i: n for i, n in v.items() if i != str(number)} for k, v in old["counts"].items()}
    counted = {n["id"]: n for n in old["notes"]}
    for item in pages:  # a lesson keeps what the digest counted for it
        was = counted.get(item["id"], {})
        item.update({k: was[k] for k in ("seen", "last") if k in was})
    cache.update({"comments": carried + pages, "base": base, "chain": old["chain"], "read": True})
    cache.update({"checked": today, "seen": issue.get("comments", 0), "dirty": True})
    cache["through_at"] = max((c.get("updated_at") or "" for c in pages), default="")
    cache["through"] = max((c["id"] for c in pages), default=0)
    if isinstance(state, str):
        cache["notice"] = [f"digest: rebuilt ({state})"]
        return
    held = {n["id"]: n for n in state["notes"] if n.get("issue") == number}
    now_is = {c["id"]: c for c in pages}
    drift: dict[str, int] = {}
    for cid, note in held.items():
        found = now_is.get(cid)
        if found is None or not same(note, found):
            kind = entry_kind(note["body"]) or "Other"
            drift[kind] = drift.get(kind, 0) + 1
    cache["notice"] = [f"digest: drift {k} {n}" for k, n in sorted(drift.items())]


def since_read(gh: Gh, cache: dict, issue: dict) -> bool:
    """Answer 4: the comments since the digest's `through` time less 120 seconds, folded by id."""
    try:
        since = datetime.fromisoformat((cache.get("through_at") or "").replace("Z", "+00:00"))
        query = seconds(since - OVERLAP)
    except ValueError:
        query = None
    known = {c["id"]: c for c in cache.get("comments") or []}
    changed = False
    for item in comments_of(gh, issue["number"], query):
        was = known.get(item["id"])
        folded = item["id"] <= (cache.get("through") or 0)  # by id: a note read twice folds once
        edited = (item.get("updated_at") or "") > (cache.get("through_at") or "")
        changed = (
            changed or (was is None and not folded) or (was is not None and not same(was, item))
        )
        changed = changed or (folded and edited and was is None)
        if was is not None:  # a lesson keeps its count; a carried prevention stays
            item.update({k: was[k] for k in ("seen", "last", "prevent") if k in was})
        known[item["id"]] = item
        cache["through_at"] = max(cache.get("through_at") or "", item.get("updated_at") or "")
    cache["comments"] = sorted(known.values(), key=order)
    cache["seen"] = issue.get("comments", 0)
    cache["dirty"] = cache.get("dirty") or changed
    return changed


def same(was: dict, item: dict) -> bool:
    """A note read again is folded once: its first line is the one the digest holds."""
    return first_line(item).replace(" | ", " / ").startswith(first_line(was))


def write_digest(gh: Gh, root: Path, cache: dict, now: datetime, ending: bool = False) -> None:
    """One PATCH of the memory issue's body; at `end` in team mode the body is read and its notes
    folded by id first (answer 9)."""
    number = cache["issue"]
    if (
        ending and review_mode(root) == "team"
    ):  # SPEC-0063 rule 9: several stewards share one digest
        theirs = parse_digest(call(gh, "GET", f"{ISSUES}/{number}").get("body"))
        if isinstance(theirs, dict):
            known = {c["id"] for c in cache["comments"]}
            cache["comments"] += [n for n in theirs["notes"] if n["id"] not in known]
    text, _ = digest_text(cache, now)
    call(gh, "PATCH", f"{ISSUES}/{number}", {"body": text})
    cache["digest"], cache["dirty"] = text, False


def digest_notes(text: str) -> list[dict]:
    state = parse_digest(text)
    return state["notes"] if isinstance(state, dict) else []


def owner_lines(root: Path, notes: list[dict]) -> list[str]:
    """Answer 2 and Q-S4-6: a lesson seen twice or more, and the lessons with no prevention."""
    kit = (root / "kit" / "manifest.json").is_file()
    lines, bare = [], 0
    for note in notes:
        if entry_kind(note["body"]) != "Lesson":
            continue
        form = note.get("prevent")
        if not kit and form and form.startswith("kit-defect"):
            continue  # answer 7: a project's owner lines leave the kit's lessons out
        bare += form is None
        if note.get("seen", 1) >= 2:
            where = "; impact: the kit and every project" if kit else ""
            lines.append(
                f"owner: lesson {note['id']} seen {note['seen']} times; "
                f"prevention {form or 'none'}"
                f"{' (' + note['state'] + ')' if note.get('state') else ''}{where}"[:WIDTH]
            )
    if bare:
        lines.append(
            f"owner: {bare} lessons name no prevention; record --kind Lesson --prevent-of <id>"
        )
    return lines


def shown(root: Path, text: str, head: list[str]) -> list[str]:
    """The start's memory lines: the summary of the digest only, at most 80 lines of 200."""
    notes = digest_notes(text)
    lines = [*head, *summary(read_memory(notes)), *owner_lines(root, notes)]
    lines = [line[:WIDTH] for line in lines]
    if len(lines) > SHOWN:
        more = len(lines) - SHOWN + 1
        lines = [*lines[: SHOWN - 1], f"{more} more lines: steward.py find <word>"]
    return lines


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


def memory_issue(gh: Gh, root: Path, cache: dict, now: datetime | None = None) -> dict:
    """The open memory issue with its notes current in the cache; created when none is open.
    Brief #2098 answers 4 and 5 (ADR-0873): a cold clone takes the digest of the issue's body and
    reads one `since` page; a missing, unparsable or hand-edited digest, or the first read of a
    UTC day, reads every page and rebuilds it."""
    today = (now or datetime.now(UTC)).date().isoformat()
    listed = [i for i in call(gh, "GET", LISTING) if "pull_request" not in i]
    if not listed:
        body = digest_text({"comments": [], "chain": []}, now or datetime.now(UTC))[0]
        listed = [call(gh, "POST", ISSUES, {"title": TITLE, "body": body, "labels": [LABEL]})]
    issue = max(listed, key=lambda i: i["number"])
    if cache.get("issue") != issue["number"]:
        cache.clear()
        cache.update({"issue": issue["number"], "comments": []})
    state = parse_digest(issue.get("body"))
    fresh = isinstance(state, dict) and state["checked"] >= today
    if not cache.get("read") and isinstance(state, dict) and fresh:
        seed(cache, state)
    elif not fresh and cache.get("checked") != today:
        full_read(gh, cache, state, issue, today)
        return issue
    if issue.get("comments", 0) and issue.get("comments") != cache.get("seen"):
        since_read(gh, cache, issue)
    return issue


def post(gh: Gh, cache: dict, text: str, who: str = WHO) -> None:
    item = call(gh, "POST", f"{ISSUES}/{cache['issue']}/comments", {"body": f"{text}\n\n{who}\n"})
    cache["comments"].append({k: item.get(k) for k in ("id", "body", "created_at", "updated_at")})


def roll_over(gh: Gh, cache: dict, now: datetime) -> None:
    """Rule 8 at 500 comments (brief #2098 answer 6): the new issue's body is the digest, so what
    is in force carries over; the old issue says where the memory continues, then is closed."""
    old, carried = cache["issue"], open_questions(cache["comments"])
    for item in cache["comments"]:
        item.setdefault("issue", old)
    cache["chain"] = [*(cache.get("chain") or []), old]
    cache["issue"] = 0  # the new issue: its number is not known before it is opened
    body, _ = digest_text(cache, now)
    new = call(gh, "POST", ISSUES, {"title": TITLE, "body": body, "labels": [LABEL]})
    cache.update({"issue": new["number"], "seen": 0, "digest": body, "read": True})
    lines = [
        f"Memory continued from #{old}; open owner questions carried forward:",
        *(carried or ["none"]),
    ]
    post(gh, cache, "\n".join(lines))
    note = {"body": f"Memory continued in #{new['number']}.\n\n{WHO}\n"}
    call(gh, "POST", f"{ISSUES}/{old}/comments", note)
    call(gh, "PATCH", f"{ISSUES}/{old}", {"state": "closed"})
    cache["dirty"] = True  # the body names the new issue's own notes from the next pass


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


def first_question(root: Path, memory: dict) -> list[str]:
    """SPEC-0062 rule 4: in solo mode, with no `Person:` entry yet, the one question to ask."""
    if review_mode(root) != "solo" or memory["newest"].get("Person"):
        return []
    return [
        "first start with this person: ask, then record the answer as --kind Person",
        f"ask: {QUESTION}",
    ]


def proposed_tests(stack: dict | None) -> str:
    """Rule 11: the test command for the stacks `front_door.py detect` read, or empty."""
    parts = []
    for row in (stack or {}).get("rows", []):
        command = STACK_TESTS.get(row.get("name", ""))
        folder = row.get("folder", ".")
        if command and folder in (".", ""):
            parts.append(command)
        elif command:
            parts.append(f"(cd {folder} && {command})")
    return " && ".join(dict.fromkeys(parts))


def test_outcome(code: int, output: str) -> str:
    """Q-1599-2: the one run of a proposed command, said plainly."""
    if code == 5 or "no tests ran" in output:
        return "no tests"
    return "passed" if code == 0 else "failed"


def review_choice(answer: str) -> str | None:
    """Rule 2 as amendment 208 proposes: the person's answer, `solo`, `team` or None (ask again)."""
    words = answer.strip().lower().rstrip(".!")
    if words in ("alone", "alone, by myself", "by myself", "just me", "solo"):
        return "solo"
    return "team" if words in ("with a team", "a team", "team") else None


def setup_plan(root: Path, adopted: bool, stack: dict | None) -> dict:
    """Rule 9: each AGK matter of a start, settled from the kit's defaults; plain questions only."""
    from session import MAX_BUILDERS

    entries = [
        "models: one route for every session because the kit's default has no [models.routes]",
        "builders: one builder per brief because the kit runs one pull request per item",
        f"max_builders: {MAX_BUILDERS} because it is the kit's cost-effective default",
        "pr_mode: strict because it is the kit's default (one open pull request at a time)",
        "reviewers: the signed-in login on both lines because the person is the one reviewer",
    ]
    if adopted:
        command = proposed_tests(stack)
        names = ", ".join(row.get("name", "") for row in (stack or {}).get("rows", []))
        entries.append(
            f"project_tests: {command} because the detected stack is {names}"
            if command
            else "project_tests: empty because no stack was detected"
        )
    return {"entries": [f"Setup: {e}" for e in entries], "ask": [ALONE_QUESTION, REST_QUESTION]}


def setup_lines(
    root: Path, adopted: bool, stack: dict | None, answer: str | None
) -> tuple[int, list[str]]:
    """The entries to record, the questions left, and the install command to run."""
    stamp = root / "agk.toml"
    text = stamp.read_text(encoding="utf-8") if stamp.is_file() else ""
    if answer is not None and re.search(r'(?m)^mode\s*=\s*"(init|adopt)"', text):
        return 2, [
            "refused: review_mode is set only at setup (setting: review_mode; SPEC-0062 rule 2)"
        ]
    plan = setup_plan(root, adopted, stack)
    lines = list(plan["entries"])
    tool = "adopt" if adopted else "init"
    login = f'{LOGIN_ENV}="$(gh api user --jq .login)"'
    run = f"run: {login} python3 scripts/agk/{tool}.py . --login-from-env"
    command = proposed_tests(stack) if adopted else ""
    if command:
        run += " --project-tests " + json.dumps(command)
    choice = review_choice(answer) if answer is not None else None
    if choice is None:
        return 0, [*lines, *(f"ask: {q}" for q in plan["ask"])]
    said = (answer or "").strip()
    lines.append(f'Setup: review_mode: {choice} because the person said "{said}"')
    lines.append(f"ask: {REST_QUESTION}")
    return 0, [*lines, run + (" --solo" if choice == "solo" else "")]


def start(root: Path, session: str, gh: Gh, now: datetime) -> tuple[int, list[str]]:
    if line := branch_check(root):  # SPEC-0066 rule 3 (ADR-0663): stop before any write
        return 1, [line]
    if personal_table(root) is not None:
        comments = personal_entries(root)
        if other := live_run(comments, now):
            return 1, refused_start(session, other)
        stale = stale_lines(comments, now)
        personal_append(root, f"Started: steward {session} {stamp(now)}")
        run = {"session": session, "id": len(comments) + 1, "at": stamp(now)}
        held = {"at": seconds(now)}
        save_cache(root, {"personal": len(comments) + 1, "checkpoint": held, "running": run})
        text = personal_digest(root, comments, now)
        memory = read_memory(digest_notes(text))
        lines = shown(root, text, [*stale, f"memory: {PERSONAL_FILE.as_posix()}"])
        return 0, [*lines, *first_question(root, memory)]
    cache = load_cache(root)
    issue = memory_issue(gh, root, cache, now)
    if other := live_run(cache["comments"], now):
        save_cache(root, cache)
        return 1, refused_start(session, other)
    stale = stale_lines(cache["comments"], now)
    if issue.get("comments", 0) >= ROLL_OVER:
        roll_over(gh, cache, now)
    post(gh, cache, f"Started: steward {session} {stamp(now)}")
    mark = cache["comments"][-1]
    cache["running"] = {"session": session, "id": mark["id"], "issue": cache["issue"]}
    cache["running"]["at"] = stamp(now)
    checkpoint(cache, now)
    cache.pop("pulls", None)
    if cache.get("dirty"):  # answer 4: written by start only when its read folded anything
        write_digest(gh, root, cache, now)
    text = cache["digest"] = digest_text(cache, now)[0]
    memory = read_memory(digest_notes(text))
    head = [*stale, f"memory: #{cache['issue']}", *cache.pop("notice", [])]
    save_cache(root, cache)
    return 0, [*shown(root, text, head), *first_question(root, memory)]


def personal_digest(root: Path, entries: list[dict], now: datetime) -> str:
    """Rule 14: the sidecar's digest file beside `memory.md`; nothing is posted."""
    text, _ = digest_text({"issue": 0, "comments": entries, "chain": []}, now)
    path = root / DIGEST_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def seconds(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def checkpoint(cache: dict, now: datetime) -> None:
    newest = max((c.get("updated_at") or "" for c in cache.get("comments", [])), default="")
    cache["checkpoint"] = {"memory": newest or seconds(now), "at": seconds(now)}


def entry_line(item: dict, edited: bool = False) -> str:
    first = (item.get("body") or "").strip().splitlines() or [""]
    word = (first[0].split() or ["-"])[0].rstrip(":")
    return f"{item.get('id')} {'edited ' if edited else ''}{word} {first[0][:120]}"


def urgent(line: str) -> bool:
    return line.split(" edited ", 1)[-1].split(" ", 2)[-1].startswith(URGENT)


def refresh(
    root: Path, session: str, gh: Gh, now: datetime, since: str | None = None
) -> tuple[int, list[str]]:
    """Brief #1702: what changed since the checkpoint, in three GET calls; nothing is posted."""
    del session  # one checkpoint per clone; the session names the pass only
    if since is not None:
        try:
            since = seconds(datetime.fromisoformat(since.replace("Z", "+00:00")).astimezone(UTC))
        except ValueError:
            return 2, ["refused: --since takes a UTC time, as 2026-11-22T05:20Z (setting: --since)"]
    cache = load_cache(root)
    held = cache.get("checkpoint", {})
    after = since or held.get("at")
    if not after:
        return 2, [NO_CHECKPOINT]
    if personal_table(root) is not None:
        entries = personal_entries(root)
        seen = 0 if since else cache.get("personal", 0)
        lines = [entry_line(e) for e in entries[seen:]]
        lines = [*sorted(lines, key=lambda line: not urgent(line))]
        kept = {"personal": len(entries), "checkpoint": {"at": seconds(now)}}
        if cache.get("running"):
            kept["running"] = cache["running"]
            beat(root, gh, now, kept)
        save_cache(root, kept)
        return 0, [*(lines or [f"refresh: nothing new since {after}"]), PERSONAL_PULLS]
    if "issue" not in cache:  # only with --since and a lost cache: find the memory issue
        memory_issue(gh, root, cache)
    known = {c["id"]: c for c in cache["comments"]}
    lines, mine = [], (cache.get("running") or {}).get("id")
    for item in comments_of(gh, cache["issue"], since or held.get("memory")):
        was = known.get(item["id"])
        if item["id"] == mine and was is not None:  # its own beat is not a change
            known[item["id"]] = item
            continue
        if was is None or was.get("updated_at") != item.get("updated_at") or since:
            lines.append(entry_line(item, edited=was is not None and not since))
        known[item["id"]] = item
    current = [c for c in known.values() if c.get("issue") in (None, cache["issue"])]
    if len(current) >= ROLL_OVER:  # another start may have rolled the memory over: find it
        issue = max(call(gh, "GET", LISTING), key=lambda i: i["number"], default=None)
        if issue and issue["number"] != cache["issue"]:
            known = {c["id"]: c for c in comments_of(gh, issue["number"], None)}
            lines += [entry_line(c) for c in known.values()]
            cache["issue"] = issue["number"]
    cache["comments"] = sorted(known.values(), key=lambda c: (c.get("created_at") or "", c["id"]))
    lines.sort(key=lambda line: not urgent(line))
    pulls, shown = {}, cache.get("pulls")
    for pr in call(gh, "GET", f"{PULLS}?state=open&per_page={PAGE}"):
        now_is = [pr["head"]["sha"][:12], ",".join(sorted(x["name"] for x in pr["labels"])) or "-"]
        pulls[str(pr["number"])] = now_is
        moved = (shown or {}).get(str(pr["number"])) != now_is
        if moved if shown is not None else pr.get("updated_at", "") > after:
            lines.append(f"#{pr['number']} {' '.join(now_is)}")
    closed = call(gh, "GET", f"{PULLS}?state=closed&sort=updated&direction=desc&per_page={PAGE}")
    for pr in closed:
        done = pr.get("merged_at") or pr.get("closed_at") or ""
        if pr.get("updated_at", "") > after and done > after:
            lines.append(f"#{pr['number']} {'merged' if pr.get('merged_at') else 'closed'} {done}")
    if len(closed) >= PAGE and closed[-1].get("updated_at", "") > after:
        lines.append(f"more closed since {after}: not listed")
    cache["pulls"] = pulls
    beat(root, gh, now, cache)
    checkpoint(cache, now)
    save_cache(root, cache)
    return 0, lines or [f"refresh: nothing new since {after}"]


def end(
    root: Path, session: str, gh: Gh, now: datetime, calls: int | None = None, tokens=None
) -> tuple[int, list[str]]:
    figures = f" calls {calls or 'not shown'}; tokens {tokens or 'not shown'}"
    code, lines = write(root, f"Ended: steward {session}{figures}", gh)
    cache = load_cache(root)
    if code == 0 and personal_table(root) is not None:
        personal_digest(root, personal_entries(root), now)
    elif code == 0 and cache.get("issue"):
        write_digest(gh, root, cache, now, ending=True)  # answer 4: once per pass
    if code == 0 and (cache.get("running") or {}).get("session") == session:
        cache.pop("running")
    save_cache(root, cache)
    return code, lines


def lesson(
    root: Path, text: str, gh: Gh, repeat: int | None, prevent_of: int | None
) -> tuple[str | None, list[str], Callable[[], None] | None]:
    """Brief #2098 answers 1, 2 and 7: the note's text, its refusal or warnings, what follows."""
    text = re.sub(r"^(?:\s*Lesson:\s*)+", "", text.strip())
    entries = memory_entries(root)
    held = lessons_in(entries)
    form = PREVENT.search(text)
    if PREVENT_ANY.search(text) and not form or (not form and not repeat):
        return None, [f"refused: a Lesson names its prevention (setting: {NO_PREVENT})"], None
    if form and form[3] and form[3] not in draft_ids(entries):
        return (
            None,
            [f"refused: the draft is not a recorded Draft brief id (setting: {NO_PREVENT})"],
            None,
        )
    kit = (root / "kit" / "manifest.json").is_file()
    if form and kit == form[1].startswith("kit-defect"):
        need = (
            "a kit-defect is a project's form" if kit else "a kit prevention is `kit-defect #<n>`"
        )
        if kit or any(path in form[1] for path in KIT_PATHS):
            return None, [f"refused: {need} (setting: {NO_PREVENT})"], None
    target = repeat or prevent_of
    flag = "--repeat" if repeat else "--prevent-of"
    if target is not None and target not in held:
        return None, [f"refused: {flag} names a Lesson the digest holds (setting: {flag})"], None
    after, said = None, []
    if repeat:
        was, seen = held[repeat]["prevent"] or "", held[repeat]["seen"] + 1
        brief = re.match(r"brief #(\d+)$", was)
        state = brief_state(load_cache(root), was) if brief else None
        if brief and state is None:  # outside the daily's read: one GET (Q-2098-2)
            state = call(gh, "GET", f"{ISSUES}/{brief[1]}").get("state")
        if not form and (was.startswith("done") or state == "closed"):
            return (
                None,
                [
                    f"refused: the prevention of {repeat} did not hold; a repeat names a new"
                    f" one (setting: {NO_PREVENT})"
                ],
                None,
            )
        text = f"repeat of {repeat}: {text}"
        if state == "open" and personal_table(root) is None:
            body = {"body": f"Lesson repeat: {repeat} seen {seen} times\n\n{WHO}\n"}

            def after():  # noqa: E306 - answer 2 and Q-S4-3: one comment on the open brief
                call(gh, "POST", f"{ISSUES}/{brief[1]}/comments", body)
    elif prevent_of:
        text = f"prevention of {prevent_of}\n{text}"
    if form and not repeat:
        said = [
            f"warning: lesson {i} names the same prevention; --repeat {i} if it repeats"
            for i, h in held.items()
            if h["prevent"] == form[1] and i != prevent_of
        ]
    return text, said, after


def record(
    root: Path,
    kind: str,
    text: str,
    gh: Gh,
    repeat: int | None = None,
    prevent_of: int | None = None,
) -> tuple[int, list[str]]:
    warnings: list[str] = []
    after = None
    if kind == "Lesson":
        said, warnings, after = lesson(root, text, gh, repeat, prevent_of)
        if said is None:
            return 2, warnings
        text = said
    elif repeat or prevent_of:
        return 2, ["refused: --repeat and --prevent-of take a Lesson (setting: --kind)"]
    if kind not in KINDS:
        return 2, ["refused: not a memory kind (setting: the first word of rule 8)"]
    if kind == "Person" and not PERSON.fullmatch(text.strip()):
        return 2, [
            "refused: a Person entry is `<business|technical>: <their words>` (SPEC-0062 rule 4)"
        ]
    if kind == "Setup" and not SETUP.fullmatch(text.strip()):
        return 2, [
            "refused: a Setup entry is `<setting or matter>: <choice> because <reason>`"
            " (SPEC-0062 rule 9)"
        ]
    if kind == "Draft brief" and not re.match(r"F-[\w.-]+\s", text.strip() + " "):
        return 2, ["refused: a Draft brief entry starts with its id, F-<session>-<n> (brief #1741)"]
    if kind == "Triage" and DRAFT_FOR_OWNER.search(text):
        if not set(DRAFT_ID.findall(text)) & draft_ids(memory_entries(root)):
            return 2, [
                "refused: a Triage draft for the owner names a recorded Draft brief id"
                " (setting: the kind Draft brief)"
            ]
    from guard import scan_text

    from config import guard_patterns

    findings = scan_text(f"{kind}: {text}", guard_patterns(root))
    if findings:
        classes = ", ".join(sorted({f.kind for f in findings}))
        return 2, [f"refused: the text holds {classes} (setting: [guard]; data guard, SPEC-0042)"]
    who = OWNER_WHO if kind == "Person" else WHO
    code, lines = write(root, f"{kind}: {text.strip()}", gh, who)
    if code == 0 and after is not None:
        after()
    return code, [*warnings, *lines]


def show(root: Path, cid: int, gh: Gh) -> tuple[int, list[str]]:
    """Answer 4: one note in full, one GET; only a comment of a memory issue the digest names."""
    refused = "refused: not a note of a memory issue the digest names (setting: show)"
    if personal_table(root) is not None:
        found = [e for e in personal_entries(root) if e["id"] == cid]
        return (0, found[0]["body"].splitlines()) if found else (2, [refused])
    cache = load_cache(root)
    if not cache.get("issue"):
        return 2, ["refused: no memory read in this clone; run steward.py start (setting: show)"]
    item = call(gh, "GET", f"{ISSUES}/comments/{cid}")
    number = re.search(r"/issues/(\d+)$", item.get("issue_url") or "")
    if not number or int(number[1]) not in [*(cache.get("chain") or []), cache["issue"]]:
        return 2, [refused]
    return 0, (item.get("body") or "").strip().splitlines()


def find(root: Path, word: str) -> tuple[int, list[str]]:
    """Answer 4: the digest's lines that hold WORD; no call."""
    if personal_table(root) is not None:
        path = root / DIGEST_FILE
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
    else:
        text = load_cache(root).get("digest") or ""
    found = [line for line in text.splitlines()[3:] if word.casefold() in line.casefold()]
    return 0, found or [f"find: nothing in the digest for {word}"]


def memory_entries(root: Path) -> list[dict]:
    """The memory this clone holds: the sidecar file, or the start's cache (no call)."""
    if personal_table(root) is not None:
        return personal_entries(root)
    return load_cache(root).get("comments") or []


def ended(run: dict, entries: list[dict]) -> bool:
    """An `Ended: steward <session>` of the run after its own `Started:`."""
    return any(
        (found := ENDED.match((c.get("body") or "").lstrip())) and found[1] == run.get("session")
        for c in entries
        if (c.get("id") or 0) > (run.get("id") or 0)
    )


def no_start(root: Path) -> str | None:
    """Brief #1741 answer 3: the refusal when this clone holds no start of a run not ended."""
    run = load_cache(root).get("running") or {}
    return NO_START if not run.get("session") or ended(run, memory_entries(root)) else None


def beat(root: Path, gh: Gh, now: datetime, cache: dict) -> None:
    """Brief #1741 answer 2: edit the run's own `Started:` in place, one PATCH, no new comment."""
    run = cache.get("running") or {}
    personal = personal_table(root) is not None
    entries = personal_entries(root) if personal else cache.get("comments", [])
    if not run.get("session") or ended(run, entries):
        return
    text = f"Started: steward {run['session']} {run['at']} beat {stamp(now)}"
    if personal:
        path = root / PERSONAL_FILE
        parts = path.read_text(encoding="utf-8").split(SEPARATOR) if path.is_file() else []
        kept = [p for p in parts if p.strip()]
        index = run["id"] - 1
        if 0 <= index < len(kept) and STARTED.match(kept[index].strip()):
            kept[index] = text
            path.write_text("".join(f"{p.strip()}{SEPARATOR}" for p in kept), encoding="utf-8")
        return
    if run.get("issue") != cache.get("issue"):
        return  # the memory rolled over: the marker is on a closed issue
    item = call(gh, "PATCH", f"{ISSUES}/comments/{run['id']}", {"body": f"{text}\n\n{WHO}\n"})
    for held in cache.get("comments", []):
        if held.get("id") == run["id"]:
            held["body"] = item.get("body", held["body"])
            held["updated_at"] = item.get("updated_at") or held.get("updated_at")


def write(root: Path, text: str, gh: Gh, who: str = WHO) -> tuple[int, list[str]]:
    if personal_table(root) is not None:
        personal_append(root, text if who == WHO else f"{text}\n\n{who}")
        return 0, [f"recorded in {PERSONAL_FILE.as_posix()}"]
    cache = load_cache(root)
    if "issue" not in cache:
        memory_issue(gh, root, cache)
    post(gh, cache, text, who)
    save_cache(root, cache)
    return 0, [f"recorded on #{cache['issue']}"]


# SPEC-0066 rule 8 (brief #1583, ADR-0663): the greeting mark, one line per folder greeted, a hash
# of the folder's path and the date and nothing else, in the person's own Claude folder.
GREETED = "agk-greeted.txt"


def now_day() -> str:
    return datetime.now(UTC).date().isoformat()


def claude_folder() -> Path:
    """The person's Claude folder: CLAUDE_CONFIG_DIR, else `~/.claude` (verify: per platform)."""
    found = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(found) if found else Path.home() / ".claude"


def folder_key(folder: Path) -> str:
    """Rule 8's hash of the folder's path, shared by the greeting mark and the day-zero notes."""
    text = str(folder.resolve())
    return hashlib.sha256(
        (text.casefold() if sys.platform in ("win32", "darwin") else text).encode("utf-8")
    ).hexdigest()


def first_run(folder: Path, today: str) -> str:
    """The first step for FOLDER (SPEC-0066 rule 8): `kit`, `project`, `adopt`, `greet` or
    `greeted`. Only `greet` writes, and only its mark in the person's Claude folder."""
    folder = folder.resolve()
    top = next((p for p in (folder, *folder.parents) if (p / ".git").exists()), None)
    if top is not None:
        if (top / "kit" / "manifest.json").is_file() and (top / ".claude-plugin").is_dir():
            return "kit"
        return "project" if (top / "agk.toml").is_file() else "adopt"
    key = folder_key(folder)
    mark = claude_folder() / GREETED
    try:
        seen = mark.read_text(encoding="utf-8").split()
    except OSError:
        seen = []
    if key in seen:
        return "greeted"
    mark.parent.mkdir(parents=True, exist_ok=True)
    with mark.open("a", encoding="utf-8") as out:
        out.write(f"{key} {today}\n")
    return "greet"


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
    ref = sub.add_parser("refresh")
    ref.add_argument("--session", required=True)
    ref.add_argument("--since", help="a UTC time, as 2026-11-22T05:20Z, when no checkpoint is held")
    end_p = sub.add_parser("end")
    end_p.add_argument("--session", required=True)
    end_p.add_argument("--calls", type=int)
    end_p.add_argument("--tokens", type=int)
    sub.add_parser("onboard").add_argument("--again", action="store_true")
    sub.add_parser("first-run").add_argument("--folder", type=Path)
    sub.add_parser("branch")
    set_p = sub.add_parser("setup")
    set_p.add_argument("--adopted", action="store_true")
    set_p.add_argument("--detect", type=Path, help="the output of `front_door.py detect --json`")
    set_p.add_argument("--answer", help="the person's answer to the alone-or-team question")
    rec = sub.add_parser("record")
    rec.add_argument("--kind", required=True)
    group = rec.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--file", type=Path)
    rec.add_argument("--repeat", type=int, help="a Lesson's comment id: count it seen again")
    rec.add_argument("--prevent-of", type=int, help="a Lesson's comment id: name its prevention")
    sub.add_parser("show").add_argument("id", type=int)
    sub.add_parser("find").add_argument("word")
    opts = parser.parse_args(argv)
    if opts.command == "first-run":
        print(f"first-run: {first_run(opts.folder or Path.cwd(), now_day())}")
        return 0
    try:
        root = repo_root()
    except CheckError:
        print(OUTSIDE_PROJECT)
        return 3
    now = datetime.now(UTC)
    if opts.command == "branch":  # rule 3 again, when the person asks the steward to act
        line = branch_check(root)
        print(line or "branch: ok")
        return 1 if line else 0
    if opts.command == "onboard":
        import steward_onboard

        return steward_onboard.run(root, opts.again)
    if opts.command == "setup":
        try:
            facts = json.loads(opts.detect.read_text(encoding="utf-8")) if opts.detect else {}
        except (OSError, ValueError):
            print("refused: --detect cannot be read (setting: --detect)", file=sys.stderr)
            return 2
        code, lines = setup_lines(root, opts.adopted, facts.get("stack"), opts.answer)
        print("\n".join(lines))
        return code
    try:
        if opts.command in ("record", "end") and (refused := no_start(root)):
            print(refused, file=sys.stderr)  # brief #1741 answer 3: no write without a start
            return 2
        if opts.command == "record":
            text = opts.text if opts.text is not None else opts.file.read_text(encoding="utf-8")
            code, lines = record(root, opts.kind, text, gh_api, opts.repeat, opts.prevent_of)
            if code == 0:
                cache = load_cache(root)
                beat(root, gh_api, now, cache)
                save_cache(root, cache)
        elif opts.command == "start":
            code, lines = start(root, opts.session, gh_api, now)
        elif opts.command == "show":
            code, lines = show(root, opts.id, gh_api)
        elif opts.command == "find":
            code, lines = find(root, opts.word)
        elif opts.command == "refresh":
            code, lines = refresh(root, opts.session, gh_api, now, opts.since)
        else:
            tokens = opts.tokens if opts.tokens is not None else tokens_figure(dict(os.environ))
            code, lines = end(root, opts.session, gh_api, now, opts.calls, tokens)
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
