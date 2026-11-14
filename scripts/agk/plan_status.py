"""The status of each milestone against its plan (SPEC-0043 rules 17 to 19 and 26; REQ-050).
Installed: `kit/manifest.json` lists it in `verbatim`. Build (f) of SPEC-0043 rule 27 (ADR-0466).

`python3 scripts/agk/plan_status.py --facts FILE [--plan DIR] [--today D] [--weeks N] [--json]`
prints one block per `### M<n> <title>` milestone of `DIR/milestones.md` (`docs/plan` by default):

- `briefs <done> done, <open> open`: a brief is the milestone's by its `Milestone:` line, done when
  its issue closed as completed; before any is published, its brief files count as open;
- `hours <spent> spent of P50 <x> P85 <y>`: `actual_hours` of the milestone's merged pull requests
  (by their `Brief: #n`), against the estimate of `plan_estimate.py` (rules 12 to 14);
- `forecast P50 <date> P85 <date>` (or `uncalibrated` with its reasons), `target`, `status`
  (`late`, `unknown`, `at risk` or `on track`, decided in that order), `trend` (the P85 finish
  against the same estimate made from the facts as they were at the start of the report's week)
  and `cause` (at most three measured phrases, or `none measured`).

`--json` prints the same as data; `--base IN --into OUT` writes a copy of the report's facts `IN`
with one more top-level key `plan` holding that data, so that the report reads one file (rule 19).
An input that cannot be read prints `unknown`, never a guess or a zero; a facts, plan, date or
setting that cannot be read exits 2 naming the option or the setting, never its value. Files
only: no network, nothing written but `--into`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import plan_estimate as pe  # noqa: E402
from common import CheckError, plan_settings, utf8_output  # noqa: E402
from facts import window_start  # noqa: E402
from metrics import stamp, start_of  # noqa: E402

UNKNOWN = "unknown"
NONE = "none"
UNCALIBRATED = "uncalibrated"
USAGE = (
    "usage: plan_status.py --facts FILE [--plan DIR] [--today YYYY-MM-DD] [--weeks N] "
    "[--json | --base IN --into OUT]"
)
MOST_CAUSES = 3
SCOPE_CHANGE = re.compile(r"^Scope change: (SC-\d+)\s*$")
APPROVED = re.compile(r"^Approved: (\d{4}-\d{2}-\d{2})\b")


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        raise pe.Refusal(USAGE)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = Parser(prog="plan_status.py", add_help=False)
    parser.add_argument("--facts", required=True)
    parser.add_argument("--plan", default="docs/plan")
    parser.add_argument("--today")
    parser.add_argument("--weeks", default="12")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--base")
    parser.add_argument("--into")
    args = parser.parse_args(argv)
    if (args.base is None) != (args.into is None) or (args.json and args.base is not None):
        raise pe.Refusal(USAGE)
    if not (args.weeks.isdigit() and 4 <= int(args.weeks) <= 52):
        raise pe.Refusal("--weeks must be a whole number from 4 to 52 (option: --weeks)")
    args.weeks = int(args.weeks)
    return args


def read_json(path: str, option: str) -> dict:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        doc = None
    if not isinstance(doc, dict):
        raise pe.Refusal(f"the facts cannot be read as a facts document (option: {option})")
    return doc


# --- the plan's files ---------------------------------------------------------------------------


def milestones_of(text: str) -> list[dict]:
    """`### M<n> <title>` blocks, each with its `Target:` date or `none` (rule 7)."""
    out: list[dict] = []
    for line in text.splitlines():
        if heading := pe.HEADING.fullmatch(line):
            out.append({"id": heading[1], "title": heading[2], "target": NONE})
        elif out and line.startswith("Target: "):
            value = line.removeprefix("Target: ").strip()
            try:
                out[-1]["target"] = date.fromisoformat(value).isoformat()
            except ValueError:
                out[-1]["target"] = NONE
    return out


def scope_changes(plan: Path) -> list[dict]:
    """The blocks of `scope-changes.md` (rule 21): id, `What:`, `Status:` and `Approved:` date."""
    try:
        text = (plan / "scope-changes.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    out: list[dict] = []
    for line in text.splitlines():
        if found := SCOPE_CHANGE.match(line):
            out.append({"id": found[1], "what": "", "status": "", "approved": None})
        elif out and line.startswith("What: "):
            out[-1]["what"] = line.removeprefix("What: ")
        elif out and line.startswith("Status: "):
            out[-1]["status"] = line.removeprefix("Status: ").strip()
        elif out and (found := APPROVED.match(line)):
            try:  # a date-shaped value that is no date leaves the block not approved (rule 17)
                out[-1]["approved"] = date.fromisoformat(found[1]).isoformat()
            except ValueError:
                pass
    return out


def waiting(plan: Path) -> dict:
    """What waits for the person (rule 19): the plan before its baseline (rules 8 and 20) and each
    scope change proposed and not approved (rule 22)."""
    changes = [
        c["id"] for c in scope_changes(plan) if c["status"] == "proposed" and not c["approved"]
    ]
    return {"plan": not (plan / "baseline.json").exists(), "scope_changes": changes}


# --- the estimate, as plan_estimate.py makes it -------------------------------------------------


def estimates(doc: dict, plan: Path, milestones: list[dict], today: date, ctx: dict) -> dict:
    """Per milestone: `kind` (`calibrated`, `uncalibrated`, `done` or `unknown`), the reasons, the
    declared text and P50 and P85 of hours and finish dates (rules 12 to 14)."""
    start, end = window_start(today, ctx["weeks"]), start_of(today + timedelta(days=1))
    flow = doc.get("flow")
    briefs = flow.get("briefs") if isinstance(flow, dict) else None
    history = pe.history_of(doc.get("pull_requests"), start, end)
    weeks = pe.throughput_of(briefs, start, end, today)
    out: dict = {}
    need = 0
    for m in milestones:
        mid = m["id"]
        entry = {"kind": UNKNOWN, "reasons": [], "hours": [UNKNOWN] * 2, "dates": [UNKNOWN] * 2}
        out[mid] = entry
        if not isinstance(briefs, list):
            continue
        found = pe.open_briefs(briefs, plan, mid)
        need += len(found)
        sizes = [size for size, _ in found]
        reasons = pe.reasons_of(history, weeks, sizes, ctx["settings"]["calibration_min"])
        if not found:
            entry |= {"kind": "done", "hours": ["done"] * 2, "dates": ["done"] * 2}
        elif reasons:
            entry |= {"kind": UNCALIBRATED, "reasons": reasons}
            entry["declared"] = pe.declared(found, ctx["settings"]["default_hours"])
        else:
            assert history is not None and weeks is not None  # nosec B101 - reasons_of says so
            entry["kind"] = "calibrated"
            entry["hours"] = pe.hours_of(history, sizes, mid)
            entry["dates"] = pe.dates_of(weeks, need, mid, today)
    return out


def as_of(doc: dict, cutoff: datetime) -> dict:
    """The facts as they were at `cutoff`: pull requests merged and briefs closed before it, and
    only the briefs created before it (rule 18, the trend)."""
    then = dict(doc)
    pulls = doc.get("pull_requests")
    if isinstance(pulls, list):
        then["pull_requests"] = [
            p
            for p in pulls
            if isinstance(p, dict) and (when := stamp(p.get("merged_at"))) and when < cutoff
        ]
    flow = doc.get("flow")
    if isinstance(flow, dict) and isinstance(flow.get("briefs"), list):
        kept = []
        for b in flow["briefs"]:
            made = stamp(b.get("created_at")) if isinstance(b, dict) else None
            if not isinstance(b, dict) or (made is not None and made >= cutoff):
                continue
            closed = stamp(b.get("closed_at"))
            if closed is not None and closed >= cutoff:
                b = {**b, "state": "open", "closed_at": None, "state_reason": None}
            kept.append(b)
        then["flow"] = {**flow, "briefs": kept}
    return then


def trend_of(now: str, then: str) -> str:
    try:
        days = (date.fromisoformat(now) - date.fromisoformat(then)).days
    except ValueError:
        return UNKNOWN
    if days == 0:
        return "same"
    return f"P85 {abs(days)} days {'later' if days > 0 else 'earlier'}"


# --- what happened ------------------------------------------------------------------------------


def numbers_of(briefs: Any, plan: Path, mid: str) -> tuple[set, Any, Any]:
    """(issue numbers, done, open) of the milestone's briefs; `unknown` when unreadable."""
    if not isinstance(briefs, list):
        return set(), UNKNOWN, UNKNOWN
    mine = [b for b in briefs if isinstance(b, dict) and b.get("milestone") == mid]
    if not mine:
        return set(), 0, len(list((plan / "briefs" / mid).glob("*.md")))
    done = sum(
        1 for b in mine if b.get("state") == "closed" and b.get("state_reason") == "completed"
    )
    opened = sum(1 for b in mine if b.get("state", "open") == "open")
    return {b["number"] for b in mine}, done, opened


def spent_of(pulls: Any, numbers: set) -> str:
    if not isinstance(pulls, list):
        return UNKNOWN
    total = Decimal(0)
    for p in pulls:
        if isinstance(p, dict) and p.get("brief") in numbers and p.get("state") == "merged":
            hours = pe.number(p.get("actual_hours"))
            if hours is None:
                return UNKNOWN
            total += hours
    return pe.tenth(total)


def first_verdict(p: dict) -> datetime | None:
    verdicts = p.get("verdicts")
    times = (
        [stamp(v.get("at")) for v in verdicts if isinstance(v, dict)]
        if isinstance(verdicts, list)
        else []
    )
    found = [t for t in times if t is not None]
    return min(found) if found else None


def causes_of(doc: dict, plan: Path, mid: str, numbers: set, week: tuple) -> list[str]:
    """The measured causes, in the order of rule 18, at most three; `unknown` when the pull
    requests cannot be read."""
    pulls = doc.get("pull_requests")
    if not isinstance(pulls, list):
        return [UNKNOWN]
    start, end = week
    mine = [p for p in pulls if isinstance(p, dict) and p.get("brief") in numbers]
    review = Decimal(0)
    for p in mine:
        when, hours = first_verdict(p), pe.number((p.get("flow") or {}).get("to_first_verdict"))
        if when is not None and start <= when < end and hours is not None:
            review += hours
    grew = sum(
        1
        for c in scope_changes(plan)
        if c["approved"]
        and start.date() <= date.fromisoformat(c["approved"]) < end.date()
        and re.search(rf"\b{mid}\b", c["what"])
    )
    stalled = sum(1 for p in mine if p.get("state") == "open" and p.get("stalled") is True)
    judged = missed = 0
    for p in mine:
        found = pe.RANGE.fullmatch(str(p.get("estimated_hours")))
        hours = pe.number(p.get("actual_hours"))
        if p.get("state") == "merged" and found and hours is not None:
            judged += 1
            missed += hours > Decimal(found.group(2))
    phrases = []
    if review > 0:
        phrases.append(f"waiting on review {pe.tenth(review)} h this week")
    if grew:
        phrases.append(f"scope grew by {grew} briefs")
    if stalled:
        phrases.append(f"{stalled} briefs stalled (builder)")
    if missed:
        phrases.append(f"{missed} of {judged} estimates missed")
    return phrases[:MOST_CAUSES] or ["none measured"]


def status_of(target: str, opened: Any, estimate: dict, today: date) -> str:
    """`late`, else `unknown`, else `at risk`, else `on track` (rule 18, in that order)."""
    if target != NONE and today > date.fromisoformat(target) and opened not in (0, UNKNOWN):
        return "late"
    if target == NONE or estimate["kind"] in (UNCALIBRATED, UNKNOWN) or opened == UNKNOWN:
        return UNKNOWN
    p85 = estimate["dates"][1]
    if p85 == UNKNOWN:
        return UNKNOWN
    if p85 != "done" and date.fromisoformat(p85) > date.fromisoformat(target):
        return "at risk"
    return "on track"


# --- the command --------------------------------------------------------------------------------


def status(args: argparse.Namespace) -> dict:
    doc = read_json(args.facts, "--facts")
    today = pe.day_of(args.today if args.today is not None else doc.get("today"), "--today")
    plan = Path(args.plan)
    try:
        milestones = milestones_of((plan / "milestones.md").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        raise pe.Refusal("the plan has no readable milestones.md (option: --plan)") from None
    try:
        settings = plan_settings(Path("."))
    except (CheckError, ValueError) as error:
        raise pe.Refusal(
            str(error) if isinstance(error, CheckError) else "(setting: [plan])"
        ) from None
    ctx = {"weeks": args.weeks, "settings": settings}
    monday = today - timedelta(days=today.weekday()) - timedelta(days=7)  # the report's week
    week = (start_of(monday), start_of(monday + timedelta(days=7)))
    now = estimates(doc, plan, milestones, today, ctx)
    then = estimates(as_of(doc, week[0]), plan, milestones, monday - timedelta(days=1), ctx)
    flow = doc.get("flow")
    briefs = flow.get("briefs") if isinstance(flow, dict) else None
    out = []
    for m in milestones:
        mid, estimate = m["id"], now[m["id"]]
        numbers, done, opened = numbers_of(briefs, plan, mid)
        entry = {"id": mid, "title": m["title"], "briefs": {"done": done, "open": opened}}
        entry["estimate"] = estimate["kind"]
        entry["reasons"] = estimate["reasons"] + (
            [estimate["declared"]] if "declared" in estimate else []
        )
        entry["hours"] = {"spent": spent_of(doc.get("pull_requests"), numbers)}
        entry["hours"] |= dict(zip(("p50", "p85"), estimate["hours"], strict=True))
        entry["forecast"] = dict(zip(("p50", "p85"), estimate["dates"], strict=True))
        entry["target"] = m["target"]
        entry["status"] = status_of(m["target"], opened, estimate, today)
        entry["trend"] = trend_of(estimate["dates"][1], then[mid]["dates"][1])
        entry["cause"] = causes_of(doc, plan, mid, numbers, week)
        out.append(entry)
    return {
        "today": today.isoformat(),
        "milestones": out,
        "waiting": waiting(plan),
        "limits": pe.LIMITS,
    }


def text_of(data: dict) -> list[str]:
    lines = []
    for m in data["milestones"]:
        hours, forecast = m["hours"], m["forecast"]
        lines.append(f"{m['id']} {m['title']}")
        lines.append(f"  briefs {m['briefs']['done']} done, {m['briefs']['open']} open")
        if m["estimate"] == UNCALIBRATED:
            reasons = "; ".join(m["reasons"])
            lines.append(f"  hours {hours['spent']} spent of {UNCALIBRATED} ({reasons})")
            lines.append(f"  forecast {UNCALIBRATED}")
        else:
            lines.append(f"  hours {hours['spent']} spent of P50 {hours['p50']} P85 {hours['p85']}")
            lines.append(f"  forecast P50 {forecast['p50']} P85 {forecast['p85']}")
        lines.append(f"  target {m['target']}")
        lines.append(f"  status {m['status']}")
        lines.append(f"  trend {m['trend']}")
        lines.append(f"  cause {'; '.join(m['cause'])}")
    wait = data["waiting"]
    if wait["plan"]:
        lines.append("waiting: the plan waits for its confirmation (Approve: plan)")
    lines += [f"waiting: scope change {sc} waits for approval" for sc in wait["scope_changes"]]
    return [*lines, data["limits"]]


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    try:
        args = parse_args(list(sys.argv[1:] if argv is None else argv))
        data = status(args)
        if args.base is not None:
            base = read_json(args.base, "--base")
            text = json.dumps({**base, "plan": data}, indent=2, ensure_ascii=False) + "\n"
            try:
                Path(args.into).write_text(text, encoding="utf-8")
            except OSError:
                raise pe.Refusal("the facts copy cannot be written (option: --into)") from None
            return 0
    except pe.Refusal as refusal:
        print(f"plan_status: {refusal}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("\n".join(text_of(data)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
