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
    "[--inbox | --print-action]"
)
DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
STAMP = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|\+00:00)$")
WEEK = re.compile(r"^(\d{4})-W(\d{2})$")
KINDS = (
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


def bullet(text: str, link: str | None) -> str:
    return f"- {text} — {link}" if link else f"- {text}"


def unknown_line(what: str, link: str) -> str:
    return bullet(f"unknown: {what} could not be read", link)


# --- the inbox (rules 3 to 6) -------------------------------------------------------------------


def age_days(item: dict, today: date) -> int | None:
    opened = day_of(item.get("created_at"))
    return None if opened is None else (today - opened).days


def spec_items(doc: dict, links: Links) -> list[str]:
    rows = sorted((s for s in doc["specs"] if s.get("status") == "Draft"), key=lambda s: s["id"])
    return [
        bullet(
            f'Draft spec {s["id"]} "{s["title"]}" waits for approval',
            links.tree("docs/specs"),
        )
        for s in rows
    ]


def adr_items(doc: dict, links: Links) -> list[str]:
    rows = sorted((a for a in doc["adrs"] if a.get("status") == "Proposed"), key=lambda a: a["id"])
    return [
        bullet(
            f'Proposed {a["id"]} "{a["title"]}" waits for a decision',
            links.tree("docs/adr"),
        )
        for a in rows
    ]


def question_items(doc: dict, links: Links) -> list[str]:
    if not is_list(doc["questions"]):
        return [unknown_line("questions", links.tree("docs"))]
    rows = sorted(
        (q for q in doc["questions"] if q.get("open_in") and q.get("ruled") is False),
        key=lambda q: q["id"],
    )
    return [
        bullet(
            f"Question {q['id']} is waiting, asked in {q['open_in'][0]}",
            links.file(q["open_in"][0]),
        )
        for q in rows
    ]


def pull_request_items(doc: dict, links: Links, today: date) -> list[str]:
    pulls, config = doc["pull_requests"], doc["config"]
    if not is_list(pulls):
        return [unknown_line("pull requests", f"{links.repo}/pulls")]
    hours = config.get("inbox_hours") if isinstance(config, dict) else None
    if isinstance(hours, bool) or not isinstance(hours, int):
        return [
            unknown_line("the age limit for pull requests (inbox_hours)", links.file("agk.toml"))
        ]
    found = []
    for p in sorted(pulls, key=lambda p: p["number"]):
        days = age_days(p, today)
        if p.get("state") != "open" or p.get("verdicts") != [] or days is None:
            continue
        if days * 24 >= hours:
            span = plural(days, "day", "days")
            text = f'PR #{p["number"]} "{p["title"]}" has had no verdict for {span}'
            found.append(bullet(text, links.pull(p["number"])))
    return found


def overdue(doc: dict, today: date) -> list[tuple[dict, date]]:
    rows = []
    for r in doc["residuals"]:
        due = day_of(r.get("due")) if r.get("due") not in (None, UNKNOWN) else None
        if r.get("state") == "open" and due is not None and due < today:
            rows.append((r, due))
    return sorted(rows, key=lambda row: (row[0]["source"], row[1]))


def residual_items(doc: dict, links: Links, today: date) -> list[str]:
    if not is_list(doc["residuals"]):
        return [unknown_line("residuals", links.file("docs/runs/residuals.md"))]
    return [
        bullet(f"Overdue since {due.isoformat()}: {short(r['text'])}", links.file(r["source"]))
        for r, due in overdue(doc, today)
    ]


def requirement_items(doc: dict, links: Links) -> list[str]:
    if not is_list(doc["requirements"]):
        return [unknown_line("requirements", links.file("docs/requirements.md"))]
    named = {req for s in doc["specs"] for req in s.get("requirements", [])}
    rows = sorted(
        (r for r in doc["requirements"] if r.get("status") == "planned" and r["id"] not in named),
        key=lambda r: r["id"],
    )
    return [
        bullet(
            f'{r["id"]} "{r["title"]}" is planned and no spec names it',
            links.file("docs/requirements.md", r.get("line")),
        )
        for r in rows
    ]


def inbox(doc: dict, links: Links, today: date) -> list[tuple[str, list[str]]]:
    """[(heading, lines)] for the kinds that have a line, in the order of the table."""
    by_kind = {
        "spec": spec_items(doc, links),
        "adr": adr_items(doc, links),
        "question": question_items(doc, links),
        "pull-request": pull_request_items(doc, links, today),
        "residual": residual_items(doc, links, today),
        "requirement": requirement_items(doc, links),
    }
    groups = []
    for kind, title in KINDS:
        lines = by_kind[kind]
        if not lines:
            continue
        count = "unknown" if lines[0].startswith("- unknown:") else str(len(lines))
        groups.append((f"### {title} ({count})", lines))
    return groups


def group_lines(groups: list[tuple[str, list[str]]]) -> list[str]:
    out: list[str] = []
    for heading, lines in groups:
        out += [heading, *lines, ""]
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


def criteria_text(req: dict) -> str:
    criteria = req.get("criteria")
    if not is_list(criteria):
        return "its acceptance criteria are unknown"
    ids = ", ".join(c["id"] for c in criteria)
    count = plural(len(criteria), "acceptance criterion", "acceptance criteria")
    return f"{count} ({ids})" if criteria else "no acceptance criteria listed"


def delivered(doc: dict, links: Links, start: date, end: date) -> list[str]:
    lines: list[str] = []
    if is_list(doc["requirements"]):
        for r in sorted(doc["requirements"], key=lambda r: r["id"]):
            if r.get("status") == "done":
                text = f'{r["id"]} "{r["title"]}" is done: {criteria_text(r)}'
                lines.append(bullet(text, links.file("docs/requirements.md", r.get("line"))))
    else:
        lines.append(unknown_line("requirements", links.file("docs/requirements.md")))
    if is_list(doc["pull_requests"]):
        for p in merged_in_week(doc, start, end):
            day = day_of(p["merged_at"]).isoformat()
            text = f'PR #{p["number"]} "{p["title"]}" was merged on {day}'
            lines.append(bullet(text, links.pull(p["number"])))
    else:
        lines.append(unknown_line("pull requests", f"{links.repo}/pulls"))
    return lines


def last_change(doc: dict, req_id: str) -> dict | None:
    files = {m["file"] for m in doc["markers"] if m.get("req") == req_id}
    related = [
        p
        for p in doc["pull_requests"]
        if p.get("state") == "merged" and is_list(p.get("files")) and files & set(p["files"])
    ]
    return max(related, key=lambda p: (p.get("merged_at") or "", p["number"]), default=None)


def proof_words(proof) -> str:
    return "skipped (declared unchanged)" if proof == "skipped" else str(proof)


def proven(doc: dict, links: Links) -> list[str]:
    if not is_list(doc["requirements"]):
        return [unknown_line("requirements", links.file("docs/requirements.md"))]
    if not is_list(doc["markers"]):
        return [unknown_line("test markers", links.tree("tests"))]
    if not is_list(doc["pull_requests"]):
        return [unknown_line("pull requests", f"{links.repo}/pulls")]
    lines: list[str] = []
    planned = 0
    for r in sorted(doc["requirements"], key=lambda r: r["id"]):
        status = r.get("status")
        planned += status == "planned"
        if status not in ("done", "in-progress"):
            continue
        link = links.file("docs/requirements.md", r.get("line"))
        criteria = r.get("criteria")
        if not is_list(criteria):
            lines.append(
                bullet(f"{r['id']} is not proven: its acceptance criteria are unknown", link)
            )
            continue
        tested = {m["ac"] for m in doc["markers"] if m.get("req") == r["id"] and m.get("ac")}
        change = last_change(doc, r["id"])
        reasons = []
        if not criteria:
            reasons.append("it lists no acceptance criteria")
        reasons += [f"{c['id']} has no test" for c in criteria if c["id"] not in tested]
        if change is None:
            reasons.append("no merged change was found")
        elif change.get("proof") == "not-proven":
            reasons.append(
                f"the last change (PR #{change['number']}) was not shown to need its test"
            )
        elif change.get("proof") not in ("proven", "skipped"):
            reasons.append(f"the last change (PR #{change['number']}) has an unknown proof")
        if reasons:
            lines.append(bullet(f"{r['id']} is not proven: " + "; ".join(reasons), link))
        else:
            seen = f"last change PR #{change['number']}: {proof_words(change['proof'])}"
            lines.append(bullet(f"{r['id']} is proven ({seen})", link))
    if planned:
        text = (
            f"{plural(planned, 'requirement is', 'requirements are')} planned and not counted here"
        )
        lines.append(bullet(text, links.file("docs/requirements.md")))
    return lines


def verdict_count(p: dict, kind: str) -> int | None:
    verdicts = p.get("verdicts")
    return sum(1 for v in verdicts if v.get("kind") == kind) if is_list(verdicts) else None


def drift_line(doc: dict, links: Links) -> str:
    drift = doc["drift"]
    if not isinstance(drift, dict):
        return unknown_line("the drift counts", f"{links.repo}/issues")
    counts = drift["counts"]
    parts = ", ".join(f"{kind} {counts[kind]}" for kind in sorted(counts))
    total = drift["total"]
    text = f"drift audit: {total if total == UNKNOWN else plural(total, 'finding', 'findings')}"
    text += f" ({parts})"
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
    if opened:
        return bullet(text, links.issue(opened[0]))
    return bullet(text + ("; no open drift issue" if is_list(issues) else "; issues unknown"), None)


def at_risk(doc: dict, links: Links, today: date, start: date, end: date) -> list[str]:
    lines: list[str] = []
    if is_list(doc["residuals"]):
        for r, due in overdue(doc, today):
            days = (today - due).days
            span = plural(days, "day", "days")
            text = f"Residual overdue since {due.isoformat()} ({span}): {short(r['text'])}"
            lines.append(bullet(text, links.file(r["source"])))
    else:
        lines.append(unknown_line("residuals", links.file("docs/runs/residuals.md")))
    if is_list(doc["pull_requests"]):
        for p in sorted(doc["pull_requests"], key=lambda p: p["number"]):
            days = age_days(p, today)
            if p.get("state") == "open" and days is not None and days > OLD_PULL_REQUEST_DAYS:
                span = plural(days, "day", "days")
                text = f'PR #{p["number"]} "{p["title"]}" has been open for {span}'
                lines.append(bullet(text, links.pull(p["number"])))
        for p in sorted(doc["pull_requests"], key=lambda p: p["number"]):
            ended = in_week(p.get("closed_at"), start, end)
            fixes, rejected = verdict_count(p, "fix"), verdict_count(p, "rejected")
            if ended and fixes is not None and (fixes >= 2 or rejected):
                times = plural(fixes + rejected, "time", "times")
                text = f'PR #{p["number"]} "{p["title"]}" was sent back {times}'
                lines.append(bullet(text, links.pull(p["number"])))
    else:
        lines.append(unknown_line("pull requests", f"{links.repo}/pulls"))
    lines.append(drift_line(doc, links))
    return lines


def cost(doc: dict, links: Links, start: date, end: date) -> list[str]:
    if not is_list(doc["pull_requests"]):
        return [unknown_line("pull requests", f"{links.repo}/pulls")]
    merged = merged_in_week(doc, start, end)
    if not merged:
        return []
    lines: list[str] = []
    hours: list[Decimal | None] = []
    fixes: list[int | None] = []
    for p in merged:
        h, f = hours_between(p.get("created_at"), p.get("merged_at")), verdict_count(p, "fix")
        hours.append(h)
        fixes.append(f)
        shown_h = "unknown hours" if h is None else f"{h} hours"
        shown_f = "unknown fix verdicts" if f is None else plural(f, "fix verdict", "fix verdicts")
        text = f'PR #{p["number"]} "{p["title"]}": {shown_h} from opening to merge, {shown_f}'
        lines.append(bullet(text, links.pull(p["number"])))
    total_h = "unknown" if None in hours else str(sum(hours, Decimal("0.0")))
    total_f = "unknown" if None in fixes else str(sum(fixes))
    declared = sum(1 for p in merged if p.get("behaviour") == "unchanged")
    totals = (
        f"This week: {plural(len(merged), 'pull request', 'pull requests')} merged; "
        f"hours in total: {total_h}; fix verdicts in total: {total_f}; "
        f'declared "Behaviour: unchanged": {declared}'
    )
    lines.append(bullet(totals, f"{links.repo}/pulls?q=is%3Apr+is%3Amerged"))
    return lines


# --- the footer and the whole report ------------------------------------------------------------


def footer_head(doc: dict) -> list[str]:
    lines = ["---", f"facts: {doc['commit']}"]
    if doc.get("dirty") is not False:
        value = "true" if doc.get("dirty") is True else str(doc.get("dirty"))
        lines.append(f"the working tree was modified (dirty: {value})")
    return lines


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


def footer(doc: dict, label: str) -> list[str]:
    lines = footer_head(doc)
    issues = doc["issues"]
    for name, issue in (
        ("metrics", newest(issues, "agk-metrics", label) if is_list(issues) else None),
        (
            "drift audit",
            newest(issues, "agk-drift-audit", open_only=True) if is_list(issues) else None,
        ),
    ):
        if issue:
            lines.append(f'{name}: #{issue["number"]} "{issue["title"]}"')
        else:
            lines.append(f"{name}: none found" if is_list(issues) else f"{name}: unknown")
    return lines


def render_report(doc: dict, today: date, week: str | None) -> str:
    links = Links(doc)
    start, end, label = week_window(today, week)
    last = end - timedelta(days=1)
    bodies = {
        "Delivered": delivered(doc, links, start, end),
        "Proven": proven(doc, links),
        "Needs you": group_lines(inbox(doc, links, today)),
        "At risk": at_risk(doc, links, today, start, end),
        "Cost": cost(doc, links, start, end),
    }
    out = [
        f"<!-- agk-product-report: {label} -->",
        f"The week {label}, Monday {start.isoformat()} to Sunday {last.isoformat()} (UTC); "
        f"the lists of what waits for you are as of {today.isoformat()}.",
        "",
    ]
    for name in SECTIONS:
        out += [f"## {name}", "", *(bodies[name] or [NOTHING]), ""]
    out += footer(doc, label)
    return "\n".join(out) + "\n"


def render_inbox(doc: dict, today: date) -> str:
    groups = inbox(doc, Links(doc), today)
    lines = group_lines(groups) or ["nothing waits for you"]
    out = [f"The inbox as of {today.isoformat()}.", "", *lines, "", *footer_head(doc)]
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--inbox", action="store_true")
    mode.add_argument("--print-action", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse(sys.argv[1:] if argv is None else argv)
    try:
        doc = load(args.facts)
        stamp = doc["today"] if args.today is None else args.today
        today = day_of(stamp) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp) else None
        if today is None:
            raise Refusal("--today must look like 2026-10-14 (option: --today)")
        if args.inbox:
            sys.stdout.write(render_inbox(doc, today))
        elif args.print_action:
            sys.stdout.write(print_action(doc, week_window(today, args.week)[2]))
        else:
            sys.stdout.write(render_report(doc, today, args.week))
    except Refusal as exc:
        print(f"FAIL product-report: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
