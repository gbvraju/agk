"""The decision inbox and the weekly product report, from a facts document (SPEC-0011).

Standard library only, and a pure function of one file: it reads the facts document named by
`--facts` and nothing else: no other file, no environment, no clock, no `git`, no `gh`, no network.
Every number and every status it prints is computed from that document. The imports below are the
whole list a test allows (SPEC-0011 rule 13).
"""

import argparse
import json
import re
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

SCHEMA = 1
UNKNOWN = "unknown"
OLD_PULL_REQUEST_DAYS = 7
RESIDUAL_CHARACTERS = 120
USAGE = (
    "usage: product_report.py --facts FILE [--today YYYY-MM-DD] [--week YYYY-Www] "
    "[--json FILE | --inbox | --print-action]"
)
DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
STAMP = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|\+00:00)$")
WEEK = re.compile(r"^(\d{4})-W(\d{2})$")
KINDS = (
    ("ready", "Ready to merge"),
    ("spec", "Draft specs"),
    ("adr", "Proposed ADRs"),
    ("question", "Questions waiting"),
    ("pull-request", "Pull requests without a verdict"),
    ("residual", "Overdue residuals"),
    ("requirement", "Planned requirements with no spec"),
)
REQUIRED = (
    "config requirements markers specs adrs residuals questions pull_requests issues drift"
).split()
SECTIONS = ("Delivered", "Proven", "Needs you", "At risk", "Cost")
# A week is busy when more than this many pull requests merged in it (SPEC-0015 rule 1).
BUSY_WEEK = 10
NOTHING = "nothing this week"


class Refusal(Exception):
    """A refusal that names a field or a path class, never a value (exit 1)."""


# --- reading the document -----------------------------------------------------------------------


def load(path: str) -> dict:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Refusal("the facts file cannot be read (path class: facts file)") from exc
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise Refusal("the facts file is not JSON (path class: facts file)") from exc
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise Refusal("the field schema is not the version this renderer knows (field: schema)")
    repo = doc.get("repo")
    if not isinstance(repo, str) or repo == UNKNOWN or "/" not in repo:
        raise Refusal("the field repo is unknown, so no link can be made (field: repo)")
    if not isinstance(doc.get("commit"), str) or not isinstance(doc.get("today"), str):
        raise Refusal("the fields commit and today are required (fields: commit, today)")
    missing = [key for key in REQUIRED if key not in doc]
    if missing:
        raise Refusal(f"the document lacks the field {missing[0]} (field: {missing[0]})")
    return doc


def day_of(stamp) -> date | None:
    match = DATE.match(stamp) if isinstance(stamp, str) else None
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def seconds_of(stamp) -> int | None:
    match = STAMP.match(stamp) if isinstance(stamp, str) else None
    if not match:
        return None
    y, mo, d, h, mi, s = (int(g) for g in match.groups())
    try:
        return date(y, mo, d).toordinal() * 86400 + h * 3600 + mi * 60 + s
    except ValueError:
        return None


def hours_between(opened, closed) -> Decimal | None:
    a, b = seconds_of(opened), seconds_of(closed)
    if a is None or b is None:
        return None
    return (Decimal(b - a) / Decimal(3600)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def week_window(today: date, week: str | None) -> tuple[date, date, str]:
    """(Monday, next Monday, label): the week asked for, else the full ISO week before today's."""
    if week:
        match = WEEK.match(week)
        if not match:
            raise Refusal("--week must look like 2026-W41 (option: --week)")
        try:
            start = date.fromisocalendar(int(match.group(1)), int(match.group(2)), 1)
        except ValueError as exc:
            raise Refusal("--week is not an ISO week (option: --week)") from exc
    else:
        start = today - timedelta(days=today.weekday()) - timedelta(days=7)
    year, number, _ = start.isocalendar()
    return start, start + timedelta(days=7), f"{year}-W{number:02d}"


# --- small formatting helpers -------------------------------------------------------------------


def is_list(value) -> bool:
    return isinstance(value, list)


def plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def short(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= RESIDUAL_CHARACTERS else text[:RESIDUAL_CHARACTERS]


class Links:
    def __init__(self, doc: dict) -> None:
        self.repo = "https://github.com/" + doc["repo"]
        self.commit = doc["commit"]

    def pull(self, number) -> str:
        return f"{self.repo}/pull/{number}"

    def issue(self, number) -> str:
        return f"{self.repo}/issues/{number}"

    def file(self, path: str, line=None) -> str:
        return f"{self.repo}/blob/{self.commit}/{path}" + (f"#L{line}" if line else "")

    def tree(self, path: str) -> str:
        return f"{self.repo}/tree/{self.commit}/{path}"

    def merged_in(self, start: date, end: date) -> str:
        """A search of the merged pull requests of the week, `end` being the day after the last."""
        days = f"{start.isoformat()}..{(end - timedelta(days=1)).isoformat()}"
        return f"{self.repo}/pulls?q=is%3Apr+is%3Amerged+merged%3A{days}"


def bullet(text: str, link: str | None) -> str:
    return f"- {text} — {link}" if link else f"- {text}"


def unknown_line(what: str, link: str) -> str:
    return bullet(f"unknown: {what} could not be read", link)


# --- the structure of the report (SPEC-0022 rules 2 to 6) ---------------------------------------
# An item is `{"kind", <its fields>, "links"}`. The fields of a kind are fixed here; a kind or a
# field that is not in the table does not exist (a new one is a new schema number).

REPORT_SCHEMA = 5
ITEM_KINDS = {
    "requirement-done": ("id", "title", "criteria", "became_done"),
    "pull-request-merged": ("number", "title", "merged_on"),
    "pull-requests-merged": ("count",),
    "requirement-proven": ("id", "last_change"),
    "requirement-not-proven": ("id", "reasons"),
    "planned-not-counted": ("count",),
    "pull-request-cost": ("number", "title", "hours", "fix_verdicts", "usage"),
    "week-totals": (
        "merged",
        "hours",
        "hours_unknown",
        "fix_verdicts",
        "fix_verdicts_unknown",
        "behaviour_unchanged",
        "estimate",
        "busy",
        "usage",
        "usage_reported",
    ),
    "unknown": ("what",),
    "facts-commit": ("commit",),
    "working-tree-modified": ("dirty",),
    "kit-version": ("version",),
    "metrics-issue": ("state",),
    "drift-audit-issue": ("state",),
    "draft-spec": ("id", "title"),
    "proposed-adr": ("id", "title"),
    "question": ("id", "asked_in"),
    "pull-request-ready": ("number", "title"),
    "pull-request-no-verdict": ("number", "title", "days"),
    "overdue-residual": ("due", "text"),
    "unspecced-requirement": ("id", "title"),
    "residual-overdue": ("due", "days", "text"),
    "pull-requests-open-long": ("entries", "count"),
    "pull-requests-sent-back": ("entries", "count"),
    "pull-requests-merged-no-verdict": ("entries", "count"),
    "pull-requests-merged-not-cleared": ("entries", "count"),
    "drift-audit": ("total", "counts", "open_issue"),
}
OPTIONAL_FIELDS = {"metrics-issue": ("number", "title"), "drift-audit-issue": ("number", "title")}
SECTION_KEYS = ("delivered", "proven", "needs_you", "at_risk", "cost")


def link(to: str, url: str) -> dict:
    return {"to": to, "url": url}


def item(kind: str, links: list[dict], **fields) -> dict:
    return {"kind": kind, **fields, "links": links}


def unknown_item(what: str, to: str, url: str) -> dict:
    return item("unknown", [link(to, url)], what=what)


def unreadable_pull_requests(pulls: list[dict], links: Links) -> list[dict]:
    """One `unknown` item naming how many open pull requests have verdicts the facts could not
    read, with a link to each (SPEC-0026 rule 5); none when every open one is read."""
    numbers = sorted(
        p["number"] for p in pulls if p.get("state") == "open" and p.get("verdicts") == UNKNOWN
    )
    if not numbers:
        return []
    what = "the verdicts of " + plural(len(numbers), "open pull request", "open pull requests")
    return [item("unknown", [link("pull-request", links.pull(n)) for n in numbers], what=what)]


# --- the inbox (rules 3 to 6) -------------------------------------------------------------------


def age_days(item: dict, today: date) -> int | None:
    opened = day_of(item.get("created_at"))
    return None if opened is None else (today - opened).days


def document_link(entry: dict, links: Links, directory: str) -> list[dict]:
    """The file at the facts commit when the facts carry its path, else the directory."""
    path = entry.get("path")
    if isinstance(path, str) and path:
        return link("file", links.file(path))
    return link("directory", links.tree(directory))


def spec_items(doc: dict, links: Links) -> list[dict]:
    rows = sorted((s for s in doc["specs"] if s.get("status") == "Draft"), key=lambda s: s["id"])
    return [
        item("draft-spec", [document_link(s, links, "docs/specs")], id=s["id"], title=s["title"])
        for s in rows
    ]


def adr_items(doc: dict, links: Links) -> list[dict]:
    rows = sorted((a for a in doc["adrs"] if a.get("status") == "Proposed"), key=lambda a: a["id"])
    return [
        item("proposed-adr", [document_link(a, links, "docs/adr")], id=a["id"], title=a["title"])
        for a in rows
    ]


def question_items(doc: dict, links: Links) -> list[dict]:
    if not is_list(doc["questions"]):
        return [unknown_item("questions", "directory", links.tree("docs"))]
    rows = sorted(
        (q for q in doc["questions"] if q.get("open_in") and q.get("ruled") is False),
        key=lambda q: q["id"],
    )
    return [
        item(
            "question",
            [link("file", links.file(q["open_in"][0]))],
            id=q["id"],
            asked_in=q["open_in"][0],
        )
        for q in rows
    ]


def pull_request_items(doc: dict, links: Links, today: date) -> list[dict]:
    pulls, config = doc["pull_requests"], doc["config"]
    if not is_list(pulls):
        return [unknown_item("pull requests", "search", f"{links.repo}/pulls")]
    hours = config.get("inbox_hours") if isinstance(config, dict) else None
    if isinstance(hours, bool) or not isinstance(hours, int):
        what = "the age limit for pull requests (inbox_hours)"
        return [unknown_item(what, "file", links.file("agk.toml"))]
    found = []
    for p in sorted(pulls, key=lambda p: p["number"]):
        days = age_days(p, today)
        if p.get("state") != "open" or p.get("verdicts") != [] or days is None:
            continue
        if days * 24 >= hours:
            where = [link("pull-request", links.pull(p["number"]))]
            found.append(
                item(
                    "pull-request-no-verdict",
                    where,
                    number=p["number"],
                    title=p["title"],
                    days=days,
                )
            )
    return found + unreadable_pull_requests(pulls, links)


def overdue(doc: dict, today: date) -> list[tuple[dict, date]]:
    rows = []
    for r in doc["residuals"]:
        due = day_of(r.get("due")) if r.get("due") not in (None, UNKNOWN) else None
        if r.get("state") == "open" and due is not None and due < today:
            rows.append((r, due))
    return sorted(rows, key=lambda row: (row[0]["source"], row[1]))


def residual_items(doc: dict, links: Links, today: date) -> list[dict]:
    if not is_list(doc["residuals"]):
        return [unknown_item("residuals", "file", links.file("docs/runs/residuals.md"))]
    return [
        item(
            "overdue-residual",
            [link("file", links.file(r["source"]))],
            due=due.isoformat(),
            text=short(r["text"]),
        )
        for r, due in overdue(doc, today)
    ]


def ready_items(doc: dict, links: Links) -> list[dict]:
    """One item for each open pull request whose head is cleared (SPEC-0030 rule 8); an open one
    whose clearance cannot be read is not listed and adds one `unknown` item (SPEC-0026 rule 5)."""
    pulls = doc["pull_requests"]
    if not is_list(pulls):
        return []  # the pull-request group already says that the pull requests are unknown
    opened = sorted((p for p in pulls if p.get("state") == "open"), key=lambda p: p["number"])
    found = [
        item(
            "pull-request-ready",
            [link("pull-request", links.pull(p["number"]))],
            number=p["number"],
            title=p["title"],
        )
        for p in opened
        if p.get("head_cleared") == "yes"
    ]
    numbers = [p["number"] for p in opened if p.get("verdicts") == UNKNOWN]
    if numbers:
        what = "the clearance of " + plural(len(numbers), "open pull request", "open pull requests")
        found.append(
            item("unknown", [link("pull-request", links.pull(n)) for n in numbers], what=what)
        )
    return found


def requirement_items(doc: dict, links: Links) -> list[dict]:
    if not is_list(doc["requirements"]):
        return [unknown_item("requirements", "file", links.file("docs/requirements.md"))]
    named = {req for s in doc["specs"] for req in s.get("requirements", [])}
    rows = sorted(
        (r for r in doc["requirements"] if r.get("status") == "planned" and r["id"] not in named),
        key=lambda r: r["id"],
    )
    return [
        item(
            "unspecced-requirement",
            [link("file", links.file("docs/requirements.md", r.get("line")))],
            id=r["id"],
            title=r["title"],
        )
        for r in rows
    ]


def inbox(doc: dict, links: Links, today: date) -> list[dict]:
    """The groups of what waits for a person, for the kinds that have an item, in the order of
    the table: `{"group", "count", "items"}` (the count is `unknown` for an unknown item)."""
    by_kind = {
        "ready": ready_items(doc, links),
        "spec": spec_items(doc, links),
        "adr": adr_items(doc, links),
        "question": question_items(doc, links),
        "pull-request": pull_request_items(doc, links, today),
        "residual": residual_items(doc, links, today),
        "requirement": requirement_items(doc, links),
    }
    groups = []
    for kind, _ in KINDS:
        entries = by_kind[kind]
        if entries:
            count = UNKNOWN if any(e["kind"] == "unknown" for e in entries) else len(entries)
            groups.append({"group": kind, "count": count, "items": entries})
    return groups


def group_lines(groups: list[dict]) -> list[str]:
    out: list[str] = []
    for group in groups:
        heading = f"### {dict(KINDS)[group['group']]} ({group['count']})"
        out += [heading, *(RENDER[entry["kind"]](entry) for entry in group["items"]), ""]
    return out[:-1] if out else out


# --- the sections (rules 9 and 10) --------------------------------------------------------------


def in_week(stamp, start: date, end: date) -> bool:
    d = day_of(stamp)
    return d is not None and start <= d < end


def merged_in_week(doc: dict, start: date, end: date) -> list[dict]:
    rows = [
        p
        for p in doc["pull_requests"]
        if p.get("state") == "merged" and in_week(p.get("merged_at"), start, end)
    ]
    return sorted(rows, key=lambda p: p["number"])


def criteria_text(criteria) -> str:
    """The criteria of a requirement: a list of ids, or anything else when they are unknown."""
    if not is_list(criteria):
        return "its acceptance criteria are unknown"
    count = plural(len(criteria), "acceptance criterion", "acceptance criteria")
    return f"{count} ({', '.join(criteria)})" if criteria else "no acceptance criteria listed"


def delivered(doc: dict, links: Links, start: date, end: date) -> list[dict]:
    items: list[dict] = []
    if is_list(doc["requirements"]):
        for r in sorted(doc["requirements"], key=lambda r: r["id"]):
            if r.get("status") == "done":
                became = day_of(r.get("done_on"))  # SPEC-0017: the week it became done
                if became is not None and not start <= became < end:
                    continue
                criteria = r.get("criteria")
                items.append(
                    item(
                        "requirement-done",
                        [link("file", links.file("docs/requirements.md", r.get("line")))],
                        id=r["id"],
                        title=r["title"],
                        criteria=[c["id"] for c in criteria] if is_list(criteria) else UNKNOWN,
                        became_done=UNKNOWN if became is None else "this-week",
                    )
                )
    else:
        items.append(unknown_item("requirements", "file", links.file("docs/requirements.md")))
    if is_list(doc["pull_requests"]):
        merged = merged_in_week(doc, start, end)
        if len(merged) > BUSY_WEEK:
            items.append(
                item(
                    "pull-requests-merged",
                    [link("search", links.merged_in(start, end))],
                    count=len(merged),
                )
            )
            return items
        for p in merged:
            items.append(
                item(
                    "pull-request-merged",
                    [link("pull-request", links.pull(p["number"]))],
                    number=p["number"],
                    title=p["title"],
                    merged_on=day_of(p["merged_at"]).isoformat(),
                )
            )
    else:
        items.append(unknown_item("pull requests", "search", f"{links.repo}/pulls"))
    return items


def last_change(doc: dict, req_id: str) -> dict | None:
    files = {m["file"] for m in doc["markers"] if m.get("req") == req_id}
    related = [
        p
        for p in doc["pull_requests"]
        if p.get("state") == "merged" and is_list(p.get("files")) and files & set(p["files"])
    ]
    return max(related, key=lambda p: (p.get("merged_at") or "", p["number"]), default=None)


REASON_WORDS = {
    "green-on-base": "the new tests already pass without the change",
    "red-on-head": "the tests fail on the change itself",
    "timeout": "the test run took too long",
    "no-project-tests": "no test command is configured",
    "no-test-files": "the change adds no test file",
}


def why_code(change: dict) -> str:
    """The reason word of a proof, or `unknown`."""
    reason = change.get("proof_reason")
    return reason if isinstance(reason, str) and reason != UNKNOWN else UNKNOWN


def why_text(proof: str, code: str) -> str:
    """The outcome and its reason, as `not-proven: red-on-head, the tests fail on the change`."""
    if code == UNKNOWN:
        return f"{proof}: reason unknown"
    words = REASON_WORDS.get(code)
    return f"{proof}: {code}, {words}" if words else f"{proof}: {code}"


def proof_words(proof) -> str:
    return "skipped (declared unchanged)" if proof == "skipped" else str(proof)


def proven(doc: dict, links: Links) -> list[dict]:
    if not is_list(doc["requirements"]):
        return [unknown_item("requirements", "file", links.file("docs/requirements.md"))]
    if not is_list(doc["markers"]):
        return [unknown_item("test markers", "directory", links.tree("tests"))]
    if not is_list(doc["pull_requests"]):
        return [unknown_item("pull requests", "search", f"{links.repo}/pulls")]
    items: list[dict] = []
    planned = 0
    for r in sorted(doc["requirements"], key=lambda r: r["id"]):
        status = r.get("status")
        planned += status == "planned"
        if status not in ("done", "in-progress"):
            continue
        where = [link("file", links.file("docs/requirements.md", r.get("line")))]
        criteria = r.get("criteria")
        if not is_list(criteria):
            reasons = [{"reason": "criteria-unknown"}]
            items.append(item("requirement-not-proven", where, id=r["id"], reasons=reasons))
            continue
        tested = {m["ac"] for m in doc["markers"] if m.get("req") == r["id"] and m.get("ac")}
        change = last_change(doc, r["id"])
        reasons = []
        if not criteria:
            reasons.append({"reason": "no-criteria"})
        reasons += [{"reason": "no-test", "ac": c["id"]} for c in criteria if c["id"] not in tested]
        if change is None:
            reasons.append({"reason": "no-merged-change"})
        elif change.get("proof") not in ("proven", "skipped"):
            kind = "not-shown" if change.get("proof") == "not-proven" else "unknown-proof"
            reasons.append(
                {
                    "reason": kind,
                    "number": change["number"],
                    "proof": str(change.get("proof")),
                    "why": why_code(change),
                }
            )
        if reasons:
            items.append(item("requirement-not-proven", where, id=r["id"], reasons=reasons))
        else:
            seen = {"number": change["number"], "proof": str(change["proof"])}
            items.append(item("requirement-proven", where, id=r["id"], last_change=seen))
    if planned:
        where = [link("file", links.file("docs/requirements.md"))]
        items.append(item("planned-not-counted", where, count=planned))
    return items


def verdict_count(p: dict, kind: str) -> int | None:
    verdicts = p.get("verdicts")
    return sum(1 for v in verdicts if v.get("kind") == kind) if is_list(verdicts) else None


def cleared_state(p: dict) -> str | None:
    """`no-verdict` or `not-cleared` for a merged pull request whose head was not cleared, or None.

    The last `cleared` verdict must name the merged head (a prefix of it); with no verdict at all
    the state says so. Verdicts or a head the facts could not read say nothing (unknown is no miss).
    """
    verdicts, head = p.get("verdicts"), p.get("head")
    if p.get("head_cleared") == "yes":
        return None
    if not is_list(verdicts) or not isinstance(head, str) or head == UNKNOWN or not head:
        return None
    if not verdicts:
        return "no-verdict"
    cleared = [v for v in verdicts if v.get("kind") == "cleared"]
    sha = cleared[-1].get("sha") if cleared else None
    if isinstance(sha, str) and sha and head.lower().startswith(sha.lower()):
        return None
    return "not-cleared"


def drift_item(doc: dict, links: Links) -> dict:
    drift = doc["drift"]
    if not isinstance(drift, dict):
        return unknown_item("the drift counts", "search", f"{links.repo}/issues")
    issues = doc["issues"]
    opened = (
        sorted(
            i["number"]
            for i in issues
            if i.get("label") == "agk-drift-audit" and i.get("state") == "open"
        )
        if is_list(issues)
        else []
    )
    return item(
        "drift-audit",
        [link("issue", links.issue(opened[0]))] if opened else [],
        total=drift["total"],
        counts=dict(sorted(drift["counts"].items())),
        open_issue=opened[0] if opened else ("none" if is_list(issues) else UNKNOWN),
    )


def grouped(rows: list[tuple[str, int, str, dict]], links: Links) -> list[dict]:
    """One item for a kind with two or more pull requests, at the place of its lowest number.

    `rows` are (kind, number, title, extra) in today's order. A kind with one pull request keeps
    one entry and, for the two kinds that print it, its title (SPEC-0016, SPEC-0022 rule 5).
    """
    members: dict[str, list[tuple[int, str, dict]]] = {}
    for kind, number, title, extra in rows:
        members.setdefault(kind, []).append((number, title, extra))
    items = []
    for kind, number, title, extra in rows:
        group = members[kind]
        if len(group) == 1:
            named = {"title": title} if kind in TITLED else {}
            entries = [{"number": number, **extra, **named}]
        elif number == min(n for n, _, _ in group):
            entries = [{"number": n, **x} for n, _, x in sorted(group, key=lambda g: g[0])]
        else:
            continue
        where = [link("pull-request", links.pull(entry["number"])) for entry in entries]
        items.append(item(kind, where, entries=entries, count=len(entries)))
    return items


TITLED = ("pull-requests-open-long", "pull-requests-sent-back")
GROUPED = {
    "pull-requests-open-long": "have been open",
    "pull-requests-sent-back": "were sent back",
    "pull-requests-merged-no-verdict": "were merged with no verdict",
    "pull-requests-merged-not-cleared": "were merged before their last commit was cleared",
}


def at_risk(doc: dict, links: Links, today: date, start: date, end: date) -> list[dict]:
    items: list[dict] = []
    if is_list(doc["residuals"]):
        for r, due in overdue(doc, today):
            items.append(
                item(
                    "residual-overdue",
                    [link("file", links.file(r["source"]))],
                    due=due.isoformat(),
                    days=(today - due).days,
                    text=short(r["text"]),
                )
            )
    else:
        items.append(unknown_item("residuals", "file", links.file("docs/runs/residuals.md")))
    if is_list(doc["pull_requests"]):
        pulls = sorted(doc["pull_requests"], key=lambda p: p["number"])
        old = []
        for p in pulls:
            days = age_days(p, today)
            if p.get("state") == "open" and days is not None and days > OLD_PULL_REQUEST_DAYS:
                old.append(("pull-requests-open-long", p["number"], p["title"], {"days": days}))
        items += grouped(old, links)
        back = []
        for p in pulls:
            ended = in_week(p.get("closed_at"), start, end)
            fixes, rejected = verdict_count(p, "fix"), verdict_count(p, "rejected")
            if ended and fixes is not None and (fixes >= 2 or rejected):
                row = (
                    "pull-requests-sent-back",
                    p["number"],
                    p["title"],
                    {"times": fixes + rejected},
                )
                back.append(row)
        items += grouped(back, links)
        items += unreadable_pull_requests(pulls, links)
    else:
        items.append(unknown_item("pull requests", "search", f"{links.repo}/pulls"))
    drift = drift_item(doc, links)
    if not (
        drift["kind"] == "drift-audit" and drift["total"] == 0 and drift["open_issue"] == "none"
    ):
        items.append(drift)
    if is_list(doc["pull_requests"]):
        late = []
        for p in merged_in_week(doc, start, end):
            state = cleared_state(p)
            if state:
                late.append((f"pull-requests-merged-{state}", p["number"], p["title"], {}))
        items += grouped(late, links)
    return items


RANGE = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)")
HOURS = re.compile(r"\d+(?:\.\d+)?")


def estimate_value(merged: list[dict]):
    """`{"within", "counted"}`: M have a readable estimate and actual, N lie in the range."""
    counted = within = 0
    for p in merged:
        window, actual = p.get("estimated_hours"), p.get("actual_hours")
        if not (isinstance(window, str) and isinstance(actual, str) and HOURS.fullmatch(actual)):
            continue
        match = RANGE.fullmatch(window)
        if match:
            counted += 1
            within += Decimal(match.group(1)) <= Decimal(actual) <= Decimal(match.group(2))
    return {"within": within, "counted": counted} if counted else "none-declared"


def usage_of(p: dict) -> int | str:
    """The usage figure of a pull request: a whole number of tokens, `not-reported`, or `unknown`
    (facts without the field cannot say that nothing was reported)."""
    value = p.get("usage", UNKNOWN)
    if isinstance(value, bool) or not (
        isinstance(value, int) or value in ("not-reported", UNKNOWN)
    ):
        return UNKNOWN
    return value


def cost(doc: dict, links: Links, start: date, end: date) -> list[dict]:
    if not is_list(doc["pull_requests"]):
        return [unknown_item("pull requests", "search", f"{links.repo}/pulls")]
    merged = merged_in_week(doc, start, end)
    if not merged:
        return []
    busy = len(merged) > BUSY_WEEK
    items: list[dict] = []
    hours: list[Decimal | None] = []
    fixes: list[int | None] = []
    usages = [usage_of(p) for p in merged]
    for p in merged:
        h, f = hours_between(p.get("created_at"), p.get("merged_at")), verdict_count(p, "fix")
        hours.append(h)
        fixes.append(f)
        if busy:
            continue
        items.append(
            item(
                "pull-request-cost",
                [link("pull-request", links.pull(p["number"]))],
                number=p["number"],
                title=p["title"],
                hours=UNKNOWN if h is None else str(h),
                fix_verdicts=UNKNOWN if f is None else f,
                usage=usage_of(p),
            )
        )
    reported = [u for u in usages if isinstance(u, int)]
    searched = links.merged_in(start, end) if busy else f"{links.repo}/pulls?q=is%3Apr+is%3Amerged"
    items.append(
        item(
            "week-totals",
            [link("search", searched)],
            merged=len(merged),
            hours=UNKNOWN if None in hours else str(sum(hours, Decimal("0.0"))),
            hours_unknown=hours.count(None),
            fix_verdicts=UNKNOWN if None in fixes else sum(fixes),
            fix_verdicts_unknown=fixes.count(None),
            behaviour_unchanged=sum(1 for p in merged if p.get("behaviour") == "unchanged"),
            estimate=estimate_value(merged),
            busy=busy,
            usage=UNKNOWN if UNKNOWN in usages else (sum(reported) if reported else "not-reported"),
            usage_reported=len(reported),
        )
    )
    return items


# --- the footer and the whole report ------------------------------------------------------------


def newest(issues: list, label: str, ends: str = "", open_only: bool = False) -> dict | None:
    """The lowest-numbered issue with the label, a title ending with `ends`, and (if asked) open."""
    rows = [
        i
        for i in sorted(issues, key=lambda i: i["number"])
        if i.get("label") == label
        and str(i.get("title", "")).endswith(ends)
        and (not open_only or i.get("state") == "open")
    ]
    return rows[0] if rows else None


def dirty_notice(doc: dict) -> list[dict]:
    if doc.get("dirty") is False:
        return []
    value = "true" if doc.get("dirty") is True else str(doc.get("dirty"))
    return [item("working-tree-modified", [], dirty=value)]


def notices(doc: dict, label: str) -> list[dict]:
    """The footer lines, in the order printed: facts, kit version, the dirty tree, the issues."""
    found = [item("facts-commit", [], commit=doc["commit"])]
    version = doc.get("kit_version")
    found.append(
        item(
            "kit-version", [], version=version if isinstance(version, str) and version else UNKNOWN
        )
    )
    found += dirty_notice(doc)
    issues = doc["issues"]
    for kind, found_issue in (
        ("metrics-issue", newest(issues, "agk-metrics", label) if is_list(issues) else None),
        (
            "drift-audit-issue",
            newest(issues, "agk-drift-audit", open_only=True) if is_list(issues) else None,
        ),
    ):
        if found_issue:
            fields = {
                "state": "found",
                "number": found_issue["number"],
                "title": found_issue["title"],
            }
        else:
            fields = {"state": "none-found" if is_list(issues) else UNKNOWN}
        found.append(item(kind, [], **fields))
    return found


COUNTED = {
    "delivered": "requirement-done",
    "proven": "requirement-proven",
}


def section_counts(sections: dict) -> dict:
    """The number of the items of each section, counted by meaning (SPEC-0026 rule 1).

    `delivered` and `proven` count the items of one kind, `needs_you` the items of all its groups
    and `at_risk` all its items, each without its `unknown` items; a section that holds an `unknown`
    item is `unknown`, never a number."""
    counts: dict = {}
    for key in ("delivered", "proven", "needs_you", "at_risk"):
        entries = sections[key]
        if key == "needs_you":
            entries = [i for group in entries for i in group["items"]]
        if any(i["kind"] == "unknown" for i in entries):
            counts[key] = UNKNOWN
        elif key in COUNTED:
            counts[key] = sum(1 for i in entries if i["kind"] == COUNTED[key])
        else:
            counts[key] = len(entries)
    return counts


def build_report(doc: dict, today: date, week: str | None) -> dict:
    """The whole report as data: the opening, the five sections and the notices."""
    links = Links(doc)
    start, end, label = week_window(today, week)

    sections = {
        "delivered": delivered(doc, links, start, end),
        "proven": proven(doc, links),
        "needs_you": inbox(doc, links, today),
        "at_risk": at_risk(doc, links, today, start, end),
        "cost": cost(doc, links, start, end),
    }
    return {
        "schema": REPORT_SCHEMA,
        "week": label,
        "opening": {
            "first": start.isoformat(),
            "last": (end - timedelta(days=1)).isoformat(),
            "as_of": today.isoformat(),
        },
        "sections": sections,
        "counts": section_counts(sections),
        "notices": notices(doc, label),
    }


# --- the markdown, rendered from the structure alone --------------------------------------------


def bullet_of(entry: dict, text: str) -> str:
    return bullet(text, entry["links"][0]["url"] if entry["links"] else None)


def reason_text(reason: dict) -> str:
    kind = reason["reason"]
    if kind == "criteria-unknown":
        return "its acceptance criteria are unknown"
    if kind == "no-criteria":
        return "it lists no acceptance criteria"
    if kind == "no-test":
        return f"{reason['ac']} has no test"
    if kind == "no-merged-change":
        return "no merged change was found"
    shown = why_text(reason["proof"], reason["why"])
    if kind == "not-shown":
        return f"the last change (PR #{reason['number']}) was not shown to need its test ({shown})"
    return f"the last change (PR #{reason['number']}) has an unknown proof ({shown})"


def issue_text(label: str, entry: dict) -> str:
    if entry["state"] == "found":
        return f'{label}: #{entry["number"]} "{entry["title"]}"'
    return f"{label}: none found" if entry["state"] == "none-found" else f"{label}: unknown"


def estimate_text(estimate) -> str:
    if isinstance(estimate, dict):
        return f"{estimate['within']} of {estimate['counted']} within range"
    return "none declared this week"


def cost_text(entry: dict) -> str:
    hours = "unknown hours" if entry["hours"] == UNKNOWN else f"{entry['hours']} hours"
    fixes = entry["fix_verdicts"]
    shown = (
        "unknown fix verdicts" if fixes == UNKNOWN else plural(fixes, "fix verdict", "fix verdicts")
    )
    return (
        f'PR #{entry["number"]} "{entry["title"]}": {hours} from opening to merge, {shown}, '
        f"{usage_text(entry['usage'])}"
    )


def usage_text(value) -> str:
    if value == UNKNOWN:
        return "usage unknown"
    return "usage not reported" if value == "not-reported" else f"usage {value} tokens"


def totals_text(entry: dict) -> str:
    total = entry["usage"]
    if total in ("not-reported", UNKNOWN):
        shown = "not reported" if total == "not-reported" else UNKNOWN
    else:
        count = entry["usage_reported"]
        shown = f"{total} tokens ({count} of {entry['merged']} pull requests reported)"
    return (
        f"This week: {plural(entry['merged'], 'pull request', 'pull requests')} merged; "
        f"hours in total: {entry['hours']}; fix verdicts in total: {entry['fix_verdicts']}; "
        f'declared "Behaviour: unchanged": {entry["behaviour_unchanged"]}; '
        f"usage in total: {shown}; estimate: {estimate_text(entry['estimate'])}"
    )


def pull_requests_text(entry: dict) -> str:
    """A pull-request item: one line for one pull request, one line with links for several."""
    kind, entries = entry["kind"], entry["entries"]
    if len(entries) == 1:
        one = entries[0]
        number = one["number"]
        if kind == "pull-requests-open-long":
            span = plural(one["days"], "day", "days")
            text = f'PR #{number} "{one["title"]}" has been open for {span}'
        elif kind == "pull-requests-sent-back":
            times = plural(one["times"], "time", "times")
            text = f'PR #{number} "{one["title"]}" was sent back {times}'
        elif kind == "pull-requests-merged-no-verdict":
            text = f"PR #{number} was merged with no verdict"
        else:
            text = f"PR #{number} was merged before its last commit was cleared"
        return bullet_of(entry, text)
    parts = []
    for one, where in zip(entries, entry["links"], strict=True):
        value = ""
        if kind == "pull-requests-open-long":
            value = f" ({plural(one['days'], 'day', 'days')})"
        elif kind == "pull-requests-sent-back":
            value = f" ({plural(one['times'], 'time', 'times')})"
        parts.append(f"[#{one['number']}]({where['url']})" + value)
    joined = ", ".join(parts[:-1]) + " and " + parts[-1]
    return bullet(f"PRs {joined} {GROUPED[kind]}", None)


def unknown_text(entry: dict) -> str:
    """An unknown item; one that links several pull requests names each (SPEC-0026 rule 5)."""
    text = f"unknown: {entry['what']} could not be read"
    where = entry["links"]
    if len(where) > 1 and all(w["to"] == "pull-request" for w in where):
        parts = [f"[#{w['url'].rsplit('/', 1)[1]}]({w['url']})" for w in where]
        return bullet(f"{text}: " + ", ".join(parts), None)
    return bullet_of(entry, text)


def drift_text(entry: dict) -> str:
    total = entry["total"]
    shown = total if total == UNKNOWN else plural(total, "finding", "findings")
    counts = entry["counts"]
    text = f"drift audit: {shown} ({', '.join(f'{k} {counts[k]}' for k in sorted(counts))})"
    if entry["links"]:
        return bullet_of(entry, text)
    return bullet(
        text + ("; no open drift issue" if entry["open_issue"] == "none" else "; issues unknown"),
        None,
    )


RENDER = {
    "draft-spec": lambda i: bullet_of(i, f'Draft spec {i["id"]} "{i["title"]}" waits for approval'),
    "proposed-adr": lambda i: bullet_of(
        i, f'Proposed {i["id"]} "{i["title"]}" waits for a decision'
    ),
    "question": lambda i: bullet_of(i, f"Question {i['id']} is waiting, asked in {i['asked_in']}"),
    "pull-request-ready": lambda i: bullet_of(
        i, f'PR #{i["number"]} "{i["title"]}" is ready to merge'
    ),
    "pull-request-no-verdict": lambda i: bullet_of(
        i,
        f'PR #{i["number"]} "{i["title"]}" has had no verdict for '
        f"{plural(i['days'], 'day', 'days')}",
    ),
    "overdue-residual": lambda i: bullet_of(i, f"Overdue since {i['due']}: {i['text']}"),
    "unspecced-requirement": lambda i: bullet_of(
        i, f'{i["id"]} "{i["title"]}" is planned and no spec names it'
    ),
    "residual-overdue": lambda i: bullet_of(
        i,
        f"Residual overdue since {i['due']} ({plural(i['days'], 'day', 'days')}): {i['text']}",
    ),
    "pull-requests-open-long": pull_requests_text,
    "pull-requests-sent-back": pull_requests_text,
    "pull-requests-merged-no-verdict": pull_requests_text,
    "pull-requests-merged-not-cleared": pull_requests_text,
    "drift-audit": drift_text,
    "unknown": unknown_text,
    "requirement-done": lambda i: bullet_of(
        i,
        f'{i["id"]} "{i["title"]}" is done: {criteria_text(i["criteria"])}'
        + (" (week it became done: unknown)" if i["became_done"] == UNKNOWN else ""),
    ),
    "pull-request-merged": lambda i: bullet_of(
        i, f'PR #{i["number"]} "{i["title"]}" was merged on {i["merged_on"]}'
    ),
    "pull-requests-merged": lambda i: bullet_of(
        i, f"{i['count']} pull requests were merged this week"
    ),
    "requirement-proven": lambda i: bullet_of(
        i,
        f"{i['id']} is proven (last change PR #{i['last_change']['number']}: "
        f"{proof_words(i['last_change']['proof'])})",
    ),
    "requirement-not-proven": lambda i: bullet_of(
        i, f"{i['id']} is not proven: " + "; ".join(reason_text(r) for r in i["reasons"])
    ),
    "planned-not-counted": lambda i: bullet_of(
        i,
        f"{plural(i['count'], 'requirement is', 'requirements are')} planned and not counted here",
    ),
    "pull-request-cost": lambda i: bullet_of(i, cost_text(i)),
    "week-totals": lambda i: bullet_of(i, totals_text(i)),
    "facts-commit": lambda i: f"facts: {i['commit']}",
    "kit-version": lambda i: f"kit version: {i['version']}",
    "working-tree-modified": lambda i: f"the working tree was modified (dirty: {i['dirty']})",
    "metrics-issue": lambda i: issue_text("metrics", i),
    "drift-audit-issue": lambda i: issue_text("drift audit", i),
}


def render_markdown(structure: dict) -> str:
    """The report as markdown, from the structure and nothing else (SPEC-0022 rule 2)."""
    label, opening = structure["week"], structure["opening"]
    out = [
        f"<!-- agk-product-report: {label} -->",
        f"The week {label}, Monday {opening['first']} to Sunday {opening['last']} (UTC); "
        f"the lists of what waits for you are as of {opening['as_of']}.",
        "",
    ]
    for key, name in zip(SECTION_KEYS, SECTIONS, strict=True):
        entries = structure["sections"][key]
        if key == "needs_you":
            body = group_lines(entries)
        else:
            body = [RENDER[entry["kind"]](entry) for entry in entries]
        out += [f"## {name}", "", *(body or [NOTHING]), ""]
    out += ["---", *(RENDER[entry["kind"]](entry) for entry in structure["notices"])]
    return "\n".join(out) + "\n"


def write_json(structure: dict, path: str) -> None:
    """`report.json`: the structure, two-space indent, UTF-8, a final newline (SPEC-0022 rule 8)."""
    text = json.dumps(structure, indent=2, ensure_ascii=False) + "\n"
    try:
        Path(path).write_text(text, encoding="utf-8")
    except OSError as exc:
        raise Refusal("the report file cannot be written (option: --json)") from exc


def render_report(doc: dict, today: date, week: str | None) -> str:
    return render_markdown(build_report(doc, today, week))


def render_inbox(doc: dict, today: date) -> str:
    groups = inbox(doc, Links(doc), today)
    lines = group_lines(groups) or ["nothing waits for you"]
    notes = [item("facts-commit", [], commit=doc["commit"]), *dirty_notice(doc)]
    footer = ["---", *(RENDER[note["kind"]](note) for note in notes)]
    out = [f"The inbox as of {today.isoformat()}.", "", *lines, "", *footer]
    return "\n".join(out) + "\n"


def print_action(doc: dict, week: str) -> str:
    issues = doc["issues"]
    if not is_list(issues):
        raise Refusal("the field issues is unknown, so no action can be chosen (field: issues)")
    title = f"agk product report {week}"
    found = sorted(
        i["number"]
        for i in issues
        if i.get("label") == "agk-product-report" and i.get("title") == title
    )
    if not found:
        return "create\n"
    text = f"update {found[0]}\n"
    if len(found) > 1:
        ordered = ",".join(f"#{n}" for n in found)
        text += f"duplicate product report issues: {ordered}; #{found[0]} is the one updated\n"
    return text


# --- command line -------------------------------------------------------------------------------


class Parser(argparse.ArgumentParser):
    def error(self, message: str):
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)


def parse(argv: list[str]) -> argparse.Namespace:
    parser = Parser(prog="product_report.py", add_help=False)
    parser.add_argument("--facts", required=True)
    parser.add_argument("--today")
    parser.add_argument("--week")
    parser.add_argument("--json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--inbox", action="store_true")
    mode.add_argument("--print-action", action="store_true")
    args = parser.parse_args(argv)
    if args.json is not None and (args.inbox or args.print_action):
        parser.error("--json takes the report only")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse(sys.argv[1:] if argv is None else argv)
    try:
        doc = load(args.facts)
        stamp = doc["today"] if args.today is None else args.today
        today = day_of(stamp) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp) else None
        if today is None:
            raise Refusal("--today must look like YYYY-MM-DD (option: --today)")
        if args.inbox:
            sys.stdout.write(render_inbox(doc, today))
        elif args.print_action:
            sys.stdout.write(print_action(doc, week_window(today, args.week)[2]))
        else:
            structure = build_report(doc, today, args.week)
            if args.json is not None:
                write_json(structure, args.json)
            sys.stdout.write(render_markdown(structure))
    except Refusal as exc:
        print(f"FAIL product-report: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
