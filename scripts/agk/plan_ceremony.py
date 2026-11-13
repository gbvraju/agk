"""The iteration and its four ceremonies, printed from measured facts (SPEC-0043 rules 23, 24 and
26, amendment 164 item 4; REQ-050). Installed: `kit/manifest.json` lists it in `verbatim`. Build
(h) of SPEC-0043 rule 27 (brief #1096, ADR-0468).

`python3 scripts/agk/plan_ceremony.py planning|daily|review|retro --facts FILE [--plan DIR]
[--today D] [--weeks N] [--stalls FILE] [--matches FILE]` prints one ceremony's text for the person
to paste or post. AGK runs no meeting, posts nothing, files nothing and runs no other program.

- The iteration (rule 23): `[plan] iteration_days` working days (Monday to Friday, 10 by default),
  numbered from 1 from the `date` of `DIR/baseline.json`; today's is the one holding today, or on a
  weekend the next working day.
- planning: the open briefs in milestone order, then `Depends-on` order, then priority, up to the
  capacity (the nearest-rank P50 of the briefs closed as completed per full past iteration inside
  rule 12's throughput; `capacity unknown` while uncalibrated, and then no cut), then the forecast
  lines of `plan_estimate.py` and the limits line of rule 26.
- daily: at most ten lines: what finished since the previous working day, what is in progress and
  what is blocked, with the cause of a saved `stalls.py --json` output (`--stalls FILE`).
- review: per milestone touched in the iteration, its `Exit:` criterion with its evidence (merged
  pull requests with their proof, requirements done) or `no evidence yet`, the signed-off design
  version and its link, and each `Demo:` screen and state with the `Design match:` line of a merged
  pull request (`--matches FILE`, a JSON object from pull request number to its lines) and the
  persona whose story it completes.
- retro: measured facts of the iteration's merged pull requests and at most three candidate briefs,
  printed for the person and never filed.

An input that cannot be read exits 2 naming the option or the setting, never its value. Files only:
no network, no model, nothing written.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_signoff  # noqa: E402
import plan_estimate as pe  # noqa: E402
from common import CheckError, plan_settings  # noqa: E402
from facts import window_start  # noqa: E402
from metrics import stamp, start_of  # noqa: E402

UNKNOWN = "unknown"
COMMANDS = ("planning", "daily", "review", "retro")
USAGE = (
    "usage: plan_ceremony.py planning|daily|review|retro --facts FILE [--plan DIR] "
    "[--today YYYY-MM-DD] [--weeks N] [--stalls FILE] [--matches FILE]"
)
PROPOSED = "Proposed for the person to accept or change"
DAILY_MOST = 10
MOST_IMPROVEMENTS = 3
REPO = re.compile(r"[^/ ]+/[^/ ]+")
FIELD = re.compile(
    r"^(Exit|Demo|Size|Expected|Priority|Depends-on|Screens|Advances|Persona): (.+?)\s*$"
)
MATCH = re.compile(r"^Design match: (\S+/\S+) (.+?)\s*$")
REQUIREMENT = re.compile(r"^### (\S+) ")
WAIT_NAMES = {
    "to_first_verdict": "to first verdict",
    "verdict_to_cleared": "verdict to cleared",
    "cleared_to_merge": "cleared to merge",
}


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        raise pe.Refusal(USAGE)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = Parser(prog="plan_ceremony.py", add_help=False)
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--facts", required=True)
    parser.add_argument("--plan", default="docs/plan")
    parser.add_argument("--today")
    parser.add_argument("--weeks", default="12")
    parser.add_argument("--stalls")
    parser.add_argument("--matches")
    args = parser.parse_args(argv)
    if not (args.weeks.isdigit() and 4 <= int(args.weeks) <= 52):
        raise pe.Refusal("--weeks must be a whole number from 4 to 52 (option: --weeks)")
    args.weeks = int(args.weeks)
    return args


def read_json(path: str, option: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        raise pe.Refusal(f"the file cannot be read as JSON (option: {option})") from None


# --- rule 23: working days and the iteration ---------------------------------------------------


def working(day: date) -> date:
    """DAY, or the first working day (Monday to Friday) after it."""
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def add_working(day: date, count: int) -> date:
    """The working day COUNT working days after the working day DAY (negative: before it)."""
    step = 1 if count >= 0 else -1
    for _ in range(abs(count)):
        day += timedelta(days=step)
        while day.weekday() >= 5:
            day += timedelta(days=step)
    return day


def iteration_of(baseline: date, today: date, days: int) -> tuple[int, date, date] | None:
    """(number, first day, last day) of the iteration that holds TODAY, or on a weekend the next
    working day; None before the baseline's first working day (rule 23)."""
    first, target = working(baseline), working(today)
    if target < first:
        return None
    index, day = 0, first
    while day < target:
        day = add_working(day, 1)
        index += 1
    number = index // days + 1
    start = add_working(first, (number - 1) * days)
    return number, start, add_working(start, days - 1)


def baseline_date(plan: Path) -> date | None:
    path = plan / "baseline.json"
    if not path.is_file():
        return None
    doc = read_json(str(path), "--plan")
    try:
        return date.fromisoformat(doc["date"])
    except (TypeError, KeyError, ValueError):
        raise pe.Refusal("the baseline has no readable date (option: --plan)") from None


def iteration_text(found: tuple | None, baseline: date | None) -> str:
    if baseline is None:
        return "iteration unknown (no baseline)"
    if found is None:
        return f"no iteration yet (the baseline starts {working(baseline)})"
    return f"iteration {found[0]} ({found[1]} to {found[2]})"


# --- the plan's files ---------------------------------------------------------------------------


def fields_of(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        if found := FIELD.match(line):
            out.setdefault(found[1], []).append(found[2])
    return out


def milestones_of(plan: Path) -> list[dict]:
    """`### M<n> <title>` blocks with their `Exit:` and `Demo:` lines (rule 7, amendment 164)."""
    try:
        text = (plan / "milestones.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise pe.Refusal("the plan has no readable milestones.md (option: --plan)") from None
    out: list[dict] = []
    for line in text.splitlines():
        if heading := pe.HEADING.fullmatch(line):
            out.append({"id": heading[1], "title": heading[2], "exit": None, "demo": []})
        elif out and (found := FIELD.match(line)) and found[1] in ("Exit", "Demo"):
            if found[1] == "Exit":
                out[-1]["exit"] = found[2]
            elif found[2] != "none (foundation)":
                out[-1]["demo"] = [p.strip() for p in found[2].split(",") if p.strip()]
    return out


def brief_files(plan: Path, milestone: str) -> list[dict]:
    """The brief files of a milestone (before publish) with their key and fields."""
    out = []
    for path in sorted((plan / "briefs" / milestone).glob("*.md"), key=lambda f: f.stem):
        text = path.read_text(encoding="utf-8")
        size, expected = pe.estimate_parts(text)
        found = fields_of(text)
        priority = (found.get("Priority") or [""])[0]
        out.append(
            {
                "key": path.stem,
                "size": size,
                "expected": expected,
                "depends": [d.strip() for d in found.get("Depends-on", [])],
                "priority": int(priority) if priority.isdigit() else None,
                "screens": [
                    pair.strip(",") for x in found.get("Screens", []) for pair in x.split()[1:]
                ],
                "advances": [
                    a.strip() for x in found.get("Advances", []) for a in x.split(",") if a.strip()
                ],
            }
        )
    return out


def in_order(files: list[dict]) -> list[dict]:
    """`Depends-on` order, then priority (lower first, none last), then key (`Q-1096-2`)."""
    left = {f["key"]: f for f in files}
    done: list[dict] = []
    while left:
        ready = [f for f in left.values() if not any(d in left for d in f["depends"])]
        if not ready:  # a cycle is check_plan's to refuse; keep the rest in key order
            ready = list(left.values())
        ready.sort(key=lambda f: (f["priority"] is None, f["priority"] or 0, f["key"]))
        done.append(left.pop(ready[0]["key"]))
    return done


def personas(plan: Path) -> dict[str, str]:
    """Requirement key to its `Persona:` text in `requirements-proposed.md` (amendment 164)."""
    try:
        text = (plan / "requirements-proposed.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    out: dict[str, str] = {}
    key = None
    for line in text.splitlines():
        if found := REQUIREMENT.match(line):
            key = found[1]
        elif key and line.startswith("Persona: "):
            out[key] = line.removeprefix("Persona: ").strip()
    return out


# --- the facts ----------------------------------------------------------------------------------


def completed_closes(briefs: Any) -> list[tuple[date, dict]]:
    if not isinstance(briefs, list):
        return []
    out = []
    for b in briefs:
        when = stamp(b.get("closed_at")) if isinstance(b, dict) else None
        if when is not None and b.get("state_reason") == "completed":
            out.append((when.date(), b))
    return out


def merged(pulls: Any, start: datetime, end: datetime) -> list[dict]:
    if not isinstance(pulls, list):
        return []
    found = [
        p
        for p in pulls
        if isinstance(p, dict)
        and p.get("state") == "merged"
        and (when := stamp(p.get("merged_at"))) is not None
        and start <= when < end
    ]
    return sorted(found, key=lambda p: (p["merged_at"], p.get("number", 0)))


def named(p: dict) -> str:
    title = str(p.get("title") or "").strip()
    return f"#{p.get('number')} {title}".rstrip()


# --- planning -----------------------------------------------------------------------------------


def capacity(ctx: dict) -> tuple[int | None, str]:
    """(capacity, its line): the P50 of briefs closed as completed per full past iteration."""
    weeks = pe.throughput_of(ctx["briefs"], ctx["start"], ctx["end"], ctx["today"])
    if weeks is None:
        return None, "capacity unknown (throughput unknown)"
    if len(weeks) < pe.WEEKS_MINIMUM:
        return None, f"capacity unknown (throughput {len(weeks)} of {pe.WEEKS_MINIMUM} weeks)"
    closes = [d for d, _ in completed_closes(ctx["briefs"]) if ctx["start"].date() <= d]
    first = min(closes)
    first -= timedelta(days=first.weekday())
    days, counts = ctx["days"], []
    end = add_working(ctx["current"], -1)
    while (start := add_working(end, -(days - 1))) >= first:
        counts.append(sum(1 for d in closes if start <= d <= end))
        end = add_working(start, -1)
    if not counts:
        return None, "capacity unknown (no full past iteration in the throughput)"
    p50 = sorted(counts)[math.ceil(len(counts) / 2) - 1]
    text = f"capacity {p50} briefs (P50 of {len(counts)} past iterations of {days} working days)"
    return p50, text


def open_items(ctx: dict, plan: Path) -> list[str] | None:
    """The open briefs as lines, in milestone, `Depends-on` and priority order; None unreadable."""
    briefs = ctx["briefs"]
    if not isinstance(briefs, list):
        return None
    out = []
    for m in ctx["milestones"]:
        mine = [b for b in briefs if isinstance(b, dict) and b.get("milestone") == m["id"]]
        if mine:
            for b in sorted(
                (b for b in mine if b.get("state") == "open"), key=lambda b: b["number"]
            ):
                size, expected = b.get("size", UNKNOWN), b.get("expected", UNKNOWN)
                title = str(b.get("title") or "").strip()
                out.append(f"#{b['number']} {m['id']} {title} (size {size}, expected {expected})")
        else:
            for f in in_order(brief_files(plan, m["id"])):
                out.append(f"{m['id']}/{f['key']} (size {f['size']}, expected {f['expected']})")
    return out


def planning(args: argparse.Namespace, ctx: dict, plan: Path) -> list[str]:
    head = f"Planning: {iteration_text(ctx['iteration'], ctx['baseline'])}"
    lines = [f"{head}, {ctx['days']} working days"]
    cap, text = capacity(ctx)
    lines += [text, PROPOSED]
    items = open_items(ctx, plan)
    if items is None:
        lines.append(f"  {UNKNOWN} (the facts' briefs cannot be read)")
    else:
        chosen = items if cap is None else items[:cap]
        lines += [f"  {n}. {item}" for n, item in enumerate(chosen, start=1)] or ["  none"]
        if cap is not None and len(items) > cap:
            rest = len(items) - cap
            lines.append(f"not proposed (over capacity): {rest} brief{'s' * (rest != 1)}")
    lines.append("Forecast (plan_estimate.py):")
    forecast = argparse.Namespace(facts=args.facts, plan=args.plan, today=args.today)
    forecast.weeks, forecast.change = args.weeks, None
    return [*lines, *pe.report(forecast)]


# --- daily status -------------------------------------------------------------------------------


def stalls_of(args: argparse.Namespace) -> list[dict] | None:
    if args.stalls is None:
        return None
    doc = read_json(args.stalls, "--stalls")
    found = doc.get("stalls") if isinstance(doc, dict) else None
    if not isinstance(found, list) or not all(
        isinstance(s, dict) and isinstance(s.get("number"), int) for s in found
    ):
        raise pe.Refusal("the stalls are not a saved stalls.py --json output (option: --stalls)")
    return found


def daily(args: argparse.Namespace, ctx: dict) -> list[str]:
    today = ctx["today"]
    previous = add_working(working(today), -1) if today.weekday() < 5 else add_working(today, -1)
    since = start_of(previous)
    found = ctx["iteration"]
    head = f"Daily status {today} (since {previous}), "
    head += f"iteration {found[0]}" if found else iteration_text(found, ctx["baseline"])
    pulls = ctx["pulls"]
    if isinstance(pulls, list):
        done = [named(p) for p in merged(pulls, since, ctx["end"])]
        running = sorted(
            (p for p in pulls if isinstance(p, dict) and p.get("state") == "open"),
            key=lambda p: p.get("number", 0),
        )
    else:
        done, running = [UNKNOWN], []
    done += [
        f"brief #{b['number']}"
        for d, b in sorted(completed_closes(ctx["briefs"]), key=lambda x: (x[0], x[1]["number"]))
        if since.date() <= d <= today
    ]
    progress = "; ".join(named(p) for p in running) if isinstance(pulls, list) else UNKNOWN
    lines = [head, f"finished: {'; '.join(done) or 'none'}", f"in progress: {progress or 'none'}"]
    stalls = stalls_of(args) or []
    blocked = [
        f"#{s['number']} {s.get('kind', UNKNOWN)}: {s.get('cause', UNKNOWN)}" for s in stalls
    ]
    saved = {s["number"] for s in stalls}
    blocked += [
        f"#{p.get('number')} stalled (facts)"
        for p in running
        if p.get("stalled") is True and p.get("number") not in saved
    ]
    room = DAILY_MOST - len(lines)
    if len(blocked) > room:
        blocked = [*blocked[: room - 1], f"and {len(blocked) - room + 1} more"]
    return lines + [f"blocked: {b}" for b in blocked]


# --- review -------------------------------------------------------------------------------------


def matches_of(args: argparse.Namespace) -> dict[int, list[str]]:
    if args.matches is None:
        return {}
    doc = read_json(args.matches, "--matches")
    ok = isinstance(doc, dict) and all(
        k.isdigit() and isinstance(v, list) and all(isinstance(x, str) for x in v)
        for k, v in doc.items()
    )
    if not ok:
        raise pe.Refusal("the matches are not pull request numbers to lines (option: --matches)")
    return {int(k): v for k, v in doc.items()}


def demo_line(pair: str, merged_pulls: list[dict], matches: dict, files: list, names: dict) -> str:
    result = "no evidence yet"
    for p in merged_pulls:  # in merge order: the newest line wins
        for line in matches.get(p.get("number"), []):
            if (found := MATCH.match(line)) and found[1] == pair:
                result = f"{found[2]} (#{p['number']})"
    who = sorted(
        {names[k] for f in files if pair in f["screens"] for k in f["advances"] if k in names}
    )
    return f"  demo {pair}: {result}; persona {', '.join(who) or UNKNOWN}"


def review(args: argparse.Namespace, ctx: dict, plan: Path) -> list[str]:
    start, end = ctx["window"]
    matches = matches_of(args)
    try:
        rows = design_signoff.rows(Path("."))
    except CheckError as error:
        raise pe.Refusal(str(error)) from None
    designs = [r for r in rows if r["kind"] == "design"]
    design = (
        f"  design: {designs[-1]['version']} {designs[-1]['comment']}"
        if designs
        else "  design: no design sign-off"
    )
    repo = ctx["repo"] if isinstance(ctx["repo"], str) and REPO.fullmatch(ctx["repo"]) else None
    briefs = ctx["briefs"] if isinstance(ctx["briefs"], list) else []
    done_reqs = {
        r.get("id")
        for r in (ctx["requirements"] if isinstance(ctx["requirements"], list) else [])
        if isinstance(r, dict) and r.get("status") == "done"
    }
    every = merged(ctx["pulls"], datetime.min.replace(tzinfo=start.tzinfo), ctx["end"])
    names = personas(plan)
    lines = [f"Review: {iteration_text(ctx['iteration'], ctx['baseline'])}"]
    for m in ctx["milestones"]:
        mine = [b for b in briefs if isinstance(b, dict) and b.get("milestone") == m["id"]]
        numbers = {b["number"] for b in mine}
        closed = [d for d, b in completed_closes(mine) if start.date() <= d < end.date()]
        pulls = [p for p in every if p.get("brief") in numbers]
        if not closed and not [p for p in pulls if start <= stamp(p["merged_at"]) < end]:
            continue
        lines += [f"{m['id']} {m['title']}", f"  exit: {m['exit'] or 'none'}"]
        evidence = []
        for p in pulls:
            link = f"https://github.com/{repo}/pull/{p['number']}" if repo else "(link unknown)"
            when = p["merged_at"][:10]
            evidence.append(f"#{p['number']} {link} merged {when} proof {p.get('proof', UNKNOWN)}")
        advanced = sorted(
            {a for b in mine if isinstance(b.get("advances"), list) for a in b["advances"]}
        )
        evidence += [f"requirement {r} done" for r in advanced if r in done_reqs]
        lines += [f"    evidence: {e}" for e in evidence] or ["    no evidence yet"]
        lines.append(design)
        files = brief_files(plan, m["id"])
        lines += [demo_line(pair, every, matches, files, names) for pair in m["demo"]]
    if len(lines) == 1:
        lines.append("no milestone touched in this iteration")
    return lines


# --- retrospective -------------------------------------------------------------------------------


def retro(args: argparse.Namespace, ctx: dict) -> list[str]:
    start, end = ctx["window"]
    number = ctx["iteration"][0]
    lines = [f"Retrospective: {iteration_text(ctx['iteration'], ctx['baseline'])}"]
    pulls = merged(ctx["pulls"], start, end)
    sized = {}
    for size in pe.SIZES:
        judged = within = 0
        for p in pulls:
            found = pe.RANGE.fullmatch(str(p.get("estimated_hours")))
            hours = pe.number(p.get("actual_hours"))
            if p.get("estimated_size") == size and found and hours is not None:
                judged += 1
                within += Decimal(found[1]) <= hours <= Decimal(found[2])
        sized[size] = (within, judged)
    lines.append(
        "estimates within range: " + ", ".join(f"{s} {w} of {j}" for s, (w, j) in sized.items())
    )
    waits = {k: pe.median_of(pulls, k) for k in pe.WAITS}
    lines.append(
        "median waits: "
        + ", ".join(f"{WAIT_NAMES[k]} {pe.hours_text(v)}" for k, v in waits.items())
    )
    fixes = sum(
        1
        for p in pulls
        if isinstance(p.get("verdicts"), list)
        for v in p["verdicts"]
        if isinstance(v, dict) and v.get("kind") == "fix"
    )
    lines.append(f"rework: {fixes} fix verdicts over {len(pulls)} merged pull requests")
    stalls = stalls_of(args)
    if stalls is None:
        open_pulls = ctx["pulls"] if isinstance(ctx["pulls"], list) else []
        kinds = Counter(
            "builder"
            for p in open_pulls
            if isinstance(p, dict) and p.get("state") == "open" and p.get("stalled") is True
        )
    else:
        kinds = Counter(str(s.get("kind", UNKNOWN)) for s in stalls)
    found = ", ".join(f"{k} {n}" for k, n in kinds.most_common())
    lines.append(f"stalls by kind: {found or 'none'}")
    ideas = []
    missed = [(w / j, s, w, j) for s, (w, j) in sized.items() if j and w < j]
    if missed:
        _, size, w, j = min(missed)
        ideas.append(
            (
                f"Re-size the {size} briefs: {w} of {j} estimates were within range in "
                f"iteration {number}",
                f"estimates within range {size} {w} of {j}",
            )
        )
    if fixes:
        ideas.append(
            (
                f"Cut the rework: {fixes} fix verdicts over {len(pulls)} merged pull requests "
                f"in iteration {number}",
                f"rework {fixes} fix verdicts over {len(pulls)} merged pull requests",
            )
        )
    known = [(Decimal(v), k) for k, v in waits.items() if v != UNKNOWN and Decimal(v) > 0]
    if known:
        value, key = max(known)
        ideas.append(
            (
                f"Shorten the wait {WAIT_NAMES[key]}: median {pe.tenth(value)} h in iteration "
                f"{number}",
                f"median wait {WAIT_NAMES[key]} {pe.tenth(value)} h",
            )
        )
    if kinds:
        kind, count = kinds.most_common(1)[0]
        ideas.append(
            (
                f"Remove the cause of the {kind} stalls: {count} in iteration {number}",
                f"stalls of kind {kind} {count}",
            )
        )
    lines.append("Proposed improvements (candidate briefs for the person; AGK files none):")
    if not ideas:
        return [*lines, "none proposed (nothing measured to improve)"]
    for n, (sentence, measured) in enumerate(ideas[:MOST_IMPROVEMENTS], start=1):
        lines.append(f"Candidate brief {n} (printed for the person; not filed)")
        lines += [
            f'  Sentence: "{sentence}"',
            f"  Measured: before: {measured}; after: the person sets it",
        ]
    return lines


# --- the command --------------------------------------------------------------------------------


def ceremony(args: argparse.Namespace) -> list[str]:
    try:
        settings = plan_settings(Path("."))
    except (CheckError, ValueError) as error:
        raise pe.Refusal(
            str(error) if isinstance(error, CheckError) else "(setting: [plan])"
        ) from None
    doc = read_json(args.facts, "--facts")
    if not isinstance(doc, dict):
        raise pe.Refusal("the facts cannot be read as a facts document (option: --facts)")
    today = pe.day_of(args.today if args.today is not None else doc.get("today"), "--today")
    plan = Path(args.plan)
    days = settings["iteration_days"]
    baseline = baseline_date(plan)
    found = iteration_of(baseline, today, days) if baseline is not None else None
    if args.command in ("review", "retro") and found is None:
        raise pe.Refusal(
            "the plan has no iteration: no baseline.json, or today is before its date "
            "(option: --plan)"
        )
    flow = doc.get("flow")
    ctx = {"today": today, "days": days, "baseline": baseline, "iteration": found}
    ctx |= {"briefs": flow.get("briefs") if isinstance(flow, dict) else None}
    ctx |= {"pulls": doc.get("pull_requests"), "repo": doc.get("repo")}
    ctx |= {"requirements": doc.get("requirements"), "milestones": milestones_of(plan)}
    ctx |= {"start": window_start(today, args.weeks), "end": start_of(today + timedelta(days=1))}
    ctx["current"] = found[1] if found is not None else working(today)
    if found is not None:
        ctx["window"] = (start_of(found[1]), start_of(min(found[2], today) + timedelta(days=1)))
    if args.command == "planning":
        return planning(args, ctx, plan)
    if args.command == "daily":
        return daily(args, ctx)
    if args.command == "review":
        return review(args, ctx, plan)
    return retro(args, ctx)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(list(sys.argv[1:] if argv is None else argv))
        lines = ceremony(args)
    except pe.Refusal as refusal:
        print(f"plan_ceremony: {refusal}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
