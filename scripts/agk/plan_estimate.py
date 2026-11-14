"""The milestone estimator (SPEC-0043 rules 12 to 16 and 26; REQ-050). Installed:
`kit/manifest.json` lists it in `verbatim`. Build (e) of SPEC-0043 rule 27 (ADR-0465).

`python3 scripts/agk/plan_estimate.py --facts FILE [--plan DIR] [--today D] [--weeks N]` estimates
each `### M<n> <title>` milestone of `DIR/milestones.md` (`docs/plan` by default) in order, from
the facts made with `facts.py --weeks N` for the same `N` (12 by default, 4 to 52):

- the history (rule 12): merged pull requests of the window with a size and `actual_hours`, the
  most recent 30 of each size; the throughput: briefs closed as completed per ISO week, from the
  week of the first such close in the window to today's week, empty weeks counting 0;
- a milestone's open briefs: the facts' briefs whose `milestone` is it, open, by issue number;
  before any is published (none in the facts), its brief files `DIR/briefs/M<n>/<key>.md` by key;
- the simulation (rule 13): `random.Random("hours:M<n>")` and `random.Random("weeks:M<n>")`,
  10,000 trials each, nearest-rank P50 and P85 (positions 5000 and 8500);
- `uncalibrated` with its reasons and the declared `Expected:` sums when the history or the
  throughput is below the minimum (rule 14); the waits are shown apart and never added (rule 15);
- one `inputs:` line after each estimate (rule 16), and the limits line last (rule 26).

Build (g), rule 21 (brief #1095, ADR-0467): `--with SC-<n>` prints the effect of that block of
`DIR/scope-changes.md`: `effect of SC-<n>: before`, the estimate without the change, then `effect
of SC-<n>: after`, the estimate with it, each milestone with its `inputs:` line, and the limits
line once. A `Briefs:` entry `+M<n>/<key> <size> <low>-<high> hours` adds that brief to the
milestone after the change (its brief file, when it already exists, counts only after), and
`-M<n>/<key>` leaves the brief file `M<n>/<key>.md` out after it; briefs read from the facts have no
key, so a removal changes only brief files.

The deadline fit (brief #1220, ADR-0519, amendment 177), the uncalibrated path only (rule 14):
`--deadline D --builders N[,N...] [--hours-per-day H] [--review-hours R]` reads every brief file
`DIR/briefs/M<n>/<key>.md` of the milestones in order, each costing the mid point of its
`Expected:` range (the owner default of its size, else 0 h) plus R hours of review (0.25), and
schedules them as a list in milestone then key order: a brief starts only when its `Depends-on`
briefs are done and no running brief's `Touches` or `Adds` overlap its own (the shared-mechanical
paths of `session.shared_patterns` left out, the prefix rule of `session.overlap`). With N builders
the finish is the soonest of the schedules with 1 to N lanes, so more builders never finish later;
the hours become working days Monday to Friday at H a day (6) from the first working day after
`--today`. It prints `internal estimate`, one `assumptions:` line, then per N the finish date, the
buffer in working days against D and, on a miss, the briefs to move: the latest in plan order first,
each with the briefs that depend on it, until the rest meets D. A calibrated history is refused.

The same facts, plan and `--today` print the same bytes. A facts, plan, date or `[plan]` setting
that cannot be read exits 2 naming the option or the setting, never its value. Files only: no
network, no model, nothing written.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from datetime import date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_EVEN, Decimal
from pathlib import Path
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_plan  # noqa: E402
from common import ESTIMATE_LINES, CheckError, estimate_parts, plan_settings  # noqa: F401, E402
from facts import window_start  # noqa: E402
from metrics import stamp, start_of  # noqa: E402

UNKNOWN = "unknown"
USAGE = (
    "usage: plan_estimate.py --facts FILE [--plan DIR] [--today YYYY-MM-DD] [--weeks N] "
    "[--with SC-<n> | --deadline YYYY-MM-DD --builders N[,N...] [--hours-per-day H] "
    "[--review-hours R]]"
)
MOST_BUILDERS = 50
DEPENDS = re.compile(r"^Depends-on:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
SC_ID = re.compile(r"SC-[1-9]\d*")
SIZES = ("S", "M", "L")
TRIALS = 10000
PERCENTS = (50, 85)
MOST_WEEKS = 520
RECENT = 30
SIZE_MINIMUM = 3
WEEKS_MINIMUM = 4
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
HEADING = re.compile(r"^### (M\d+) (.+?)\s*$", re.MULTILINE)
RANGE = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(?: hours)?")
WAITS = ("to_first_verdict", "verdict_to_cleared", "cleared_to_merge")
LIMITS = (
    "Estimates are ranges from this project's own history, not promises; AGK drafts from the "
    "sources and the person owns scope."
)


class Refusal(Exception):
    """An input that cannot be read: exit 2 with a message that names the option or setting."""


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        raise Refusal(USAGE)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = Parser(prog="plan_estimate.py", add_help=False)
    parser.add_argument("--facts", required=True)
    parser.add_argument("--plan", default="docs/plan")
    parser.add_argument("--today")
    parser.add_argument("--weeks", default="12")
    parser.add_argument("--with", dest="change")
    parser.add_argument("--deadline")
    parser.add_argument("--builders")
    parser.add_argument("--hours-per-day", dest="hours_per_day")
    parser.add_argument("--review-hours", dest="review_hours")
    args = parser.parse_args(argv)
    fit_options(args)
    if args.change is not None and not SC_ID.fullmatch(args.change):
        raise Refusal("--with names a scope change SC-<n> (option: --with)")
    if not (args.weeks.isdigit() and 4 <= int(args.weeks) <= 52):
        raise Refusal("--weeks must be a whole number from 4 to 52 (option: --weeks)")
    args.weeks = int(args.weeks)
    return args


def fit_options(args: argparse.Namespace) -> None:
    """The deadline fit's options: all or none, never with `--with`; each refusal names one."""
    if args.deadline is None:
        if (args.builders, args.hours_per_day, args.review_hours) != (None, None, None):
            raise Refusal("the builder options need a deadline (option: --deadline)")
        return
    if args.change is not None:
        raise Refusal("a scope change and a deadline fit are run apart (option: --with)")
    if args.builders is None:
        raise Refusal("a deadline fit needs the builder counts (option: --builders)")
    args.deadline = day_of(args.deadline, "--deadline")
    counts = args.builders.split(",")
    if not all(c.isdigit() and 1 <= int(c) <= MOST_BUILDERS for c in counts):
        raise Refusal(f"builders are whole numbers from 1 to {MOST_BUILDERS} (option: --builders)")
    args.builders = sorted({int(c) for c in counts})
    hours = number(args.hours_per_day if args.hours_per_day is not None else "6")
    if hours is None or not 0 < hours <= 24:
        raise Refusal("hours a day are a number above 0 and at most 24 (option: --hours-per-day)")
    review = number(args.review_hours if args.review_hours is not None else "0.25")
    if review is None:
        raise Refusal("review hours are a number of 0 or more (option: --review-hours)")
    args.hours_per_day, args.review_hours = hours, review


def day_of(text: Any, option: str) -> date:
    try:
        if isinstance(text, str) and DAY.fullmatch(text):
            return date.fromisoformat(text)
    except ValueError:
        pass
    raise Refusal(f"a YYYY-MM-DD date is needed (option: {option})")


def number(value: Any) -> Decimal | None:
    if isinstance(value, str) and NUMBER.fullmatch(value):
        return Decimal(value)
    return None


def plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def tenth(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN))


def ranks(values: list) -> list:
    ordered = sorted(values)
    return [ordered[math.ceil(p / 100 * TRIALS) - 1] for p in PERCENTS]


def friday_of(today: date, k: int) -> date:
    """The Friday of the `k`-th full ISO week after `today`, which is never counted (rule 13)."""
    monday = today + timedelta(days=7 - today.weekday())
    return monday + timedelta(days=7 * k - 3)


# --- the inputs ---------------------------------------------------------------------------------


def history_of(pulls: Any, start: datetime, end: datetime) -> list[dict] | None:
    """The merged pull requests of the window with a size and actual hours, the most recent 30 of
    each size, each pool in `merged_at` then number order (rules 12 and 13)."""
    if not isinstance(pulls, list):
        return None
    chosen: list[dict] = []
    for size in SIZES:
        found = [
            p
            for p in pulls
            if isinstance(p, dict)
            and p.get("estimated_size") == size
            and number(p.get("actual_hours")) is not None
            and (when := stamp(p.get("merged_at"))) is not None
            and start <= when < end
        ]
        found.sort(key=lambda p: (p["merged_at"], p.get("number", 0)))
        chosen += found[-RECENT:]
    return chosen


def throughput_of(briefs: Any, start: datetime, end: datetime, today: date) -> list[int] | None:
    """Briefs closed as completed per ISO week, from the first such week to today's (rule 12)."""
    if not isinstance(briefs, list):
        return None
    mondays = []
    for b in briefs:
        when = stamp(b.get("closed_at")) if isinstance(b, dict) else None
        if b.get("state_reason") == "completed" and when is not None and start <= when < end:
            day = when.date()
            mondays.append(day - timedelta(days=day.weekday()))
    if not mondays:
        return []
    last = today - timedelta(days=today.weekday())
    first = min(mondays)
    count = (last - first).days // 7 + 1
    return [sum(1 for m in mondays if (m - first).days // 7 == i) for i in range(count)]


def open_briefs(
    briefs: list, plan: Path, milestone: str, change: dict | None = None, after: bool = False
) -> list[tuple[str, str]]:
    """(size, expected) of the milestone's open briefs: the facts' by number, or before publish
    its brief files by key (rule 13). With a scope change (rule 21) its added keys are left out
    before it and counted from the change after it, and its removed keys are left out after it."""
    adds = [
        (k, size, hours) for m, k, size, hours in (change or {}).get("adds", []) if m == milestone
    ]
    removes = {k for m, k in (change or {}).get("removes", []) if m == milestone}
    added = [(size, hours) for _, size, hours in adds] if after else []
    mine = [b for b in briefs if isinstance(b, dict) and b.get("milestone") == milestone]
    if mine:
        listed = sorted((b for b in mine if b.get("state") == "open"), key=lambda b: b["number"])
        return [(b.get("size", UNKNOWN), b.get("expected", UNKNOWN)) for b in listed] + added
    skip = {k for k, _, _ in adds} | (removes if after else set())
    files = sorted((plan / "briefs" / milestone).glob("*.md"), key=lambda f: f.stem)
    found = [estimate_parts(f.read_text(encoding="utf-8")) for f in files if f.stem not in skip]
    return found + added


def scope_change(plan: Path, wanted: str) -> dict:
    """The block `Scope change: <wanted>` of `scope-changes.md`: its added and removed briefs."""
    try:
        text = (plan / "scope-changes.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = ""
    found: dict | None = None
    for line in text.splitlines():
        if head := check_plan.CHANGE_HEAD.match(line):
            if found is not None:
                break
            found = {"adds": [], "removes": []} if head[1] == wanted else None
        elif found is not None and line.startswith("Briefs:"):
            for entry in filter(None, (e.strip() for e in line[len("Briefs:") :].split(";"))):
                if added := check_plan.ADDED.match(entry):
                    found["adds"].append((added[1], added[2], added[3], added[4]))
                elif removed := check_plan.REMOVED.match(entry):
                    found["removes"].append((removed[1], removed[2]))
                else:
                    raise Refusal(f"{check_plan.BAD_BRIEFS} (option: --with)")
    if found is None:
        raise Refusal("the scope change is not in scope-changes.md (option: --with)")
    return found


def median_of(items: list[dict], key: str) -> str:
    values = [v for p in items if (v := number((p.get("flow") or {}).get(key))) is not None]
    return tenth(Decimal(median(values))) if values else UNKNOWN


# --- one milestone -----------------------------------------------------------------------------


def reasons_of(history: Any, weeks: Any, sizes: list[str], minimum: int) -> list[str]:
    out = []
    if history is None:
        out.append(f"history {UNKNOWN}")
    elif len(history) < minimum:
        out.append(f"history {len(history)} of {minimum}")
    for size in SIZES:
        have = sum(1 for p in history or [] if p["estimated_size"] == size)
        if history is not None and size in sizes and have < SIZE_MINIMUM:
            out.append(f"size {size} {have} of {SIZE_MINIMUM}")
    if weeks is None:
        out.append(f"throughput {UNKNOWN}")
    elif len(weeks) < WEEKS_MINIMUM:
        out.append(f"throughput {len(weeks)} of {WEEKS_MINIMUM} weeks")
    return out


def declared(briefs: list[tuple[str, str]], defaults: dict) -> str:
    low = high = Decimal(0)
    owner = missing = counted = 0
    for size, expected in briefs:
        found = RANGE.fullmatch(expected) if expected != UNKNOWN else None
        if found is None and size in defaults:
            found, owner = RANGE.fullmatch(defaults[size]), owner + 1
        if found is None:
            missing += 1
            continue
        counted += 1
        low, high = low + Decimal(found.group(1)), high + Decimal(found.group(2))
    text = f"declared {plain(low)}-{plain(high)} hours" if counted else "declared none"
    text += f" ({owner} owner default)" if owner else ""
    return text + (f"; {missing} briefs without an estimate" if missing else "")


def hours_of(history: list[dict], sizes: list[str], milestone: str) -> list[str]:
    pools: dict[str, list[Decimal]] = {
        s: [Decimal(p["actual_hours"]) for p in history if p["estimated_size"] == s] for s in SIZES
    }
    joined = pools["S"] + pools["M"] + pools["L"]
    chosen = [pools[s] if s in SIZES else joined for s in sizes]
    rng = random.Random(f"hours:{milestone}")  # nosec B311 - a seeded simulation, not security
    sums = [sum((rng.choice(pool) for pool in chosen), Decimal(0)) for _ in range(TRIALS)]
    return [tenth(v) for v in ranks(sums)]


def dates_of(weeks: list[int], need: int, milestone: str, today: date) -> list[str]:
    if sum(weeks) == 0:
        return [UNKNOWN, UNKNOWN]
    rng = random.Random(f"weeks:{milestone}")  # nosec B311 - a seeded simulation, not security
    counts = []
    for _ in range(TRIALS):
        got = k = 0
        while got < need and k < MOST_WEEKS:
            got += rng.choice(weeks)
            k += 1
        if k >= MOST_WEEKS:
            return [UNKNOWN, UNKNOWN]
        counts.append(k)
    return [friday_of(today, k).isoformat() for k in ranks(counts)]


def estimate(milestone: str, title: str, briefs: list, ctx: dict) -> list[str]:
    sizes = [size for size, _ in briefs]
    history, weeks = ctx["history"], ctx["weeks"]
    head = f"{milestone} {title}: "
    reasons = reasons_of(history, weeks, sizes, ctx["settings"]["calibration_min"])
    if not briefs:
        head += "hours done; finish P50 done P85 done"
    elif reasons:
        head += f"uncalibrated ({'; '.join(reasons)}); "
        head += f"{declared(briefs, ctx['settings']['default_hours'])}; finish unknown"
    else:
        p50, p85 = hours_of(history, sizes, milestone)
        d50, d85 = dates_of(weeks, ctx["need"], milestone, ctx["today"])
        head += f"hours P50 {p50} P85 {p85}; finish P50 {d50} P85 {d85}"
    return [head, ctx["waits"], inputs_line(milestone, ctx)]


def inputs_line(milestone: str, ctx: dict) -> str:
    history, weeks, today = ctx["history"], ctx["weeks"], ctx["today"]
    text = f"inputs: window {ctx['start'].date()} to {today} ({ctx['n']} ISO weeks), "
    if history is None:
        text += f"history {UNKNOWN}, "
    else:
        counts = " ".join(
            f"{s} {sum(1 for p in history if p['estimated_size'] == s)}" for s in SIZES
        )
        days = sorted(p["merged_at"][:10] for p in history)
        span = f"{days[0]} to {days[-1]}" if days else "none"
        text += f"history {counts} ({span}), "
    if weeks is None:
        text += f"throughput {UNKNOWN}, "
    else:
        middle = tenth(Decimal(median(weeks))) if weeks else "none"
        text += f"throughput {len(weeks)} weeks median {middle} a week, "
    review, merge = (ctx["medians"][k] for k in ("to_first_verdict", "cleared_to_merge"))
    text += f"waits review {hours_text(review)} merge {hours_text(merge)} queue {UNKNOWN}, "
    return text + f"trials {TRIALS} seeds hours:{milestone} weeks:{milestone}"


def hours_text(value: str) -> str:
    return value if value == UNKNOWN else f"{value} h"


# --- the command -------------------------------------------------------------------------------


def load(args: argparse.Namespace) -> tuple[dict, date, Path, str, dict]:
    """The facts, `today`, the plan folder, its milestones.md and the `[plan]` settings."""
    try:
        doc = json.loads(Path(args.facts).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        doc = None
    if not isinstance(doc, dict):
        raise Refusal("the facts cannot be read as a facts document (option: --facts)")
    today = day_of(args.today if args.today is not None else doc.get("today"), "--today")
    plan = Path(args.plan)
    try:
        text = (plan / "milestones.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise Refusal("the plan has no readable milestones.md (option: --plan)") from None
    try:
        settings = plan_settings(Path("."))
    except (CheckError, ValueError) as error:
        raise Refusal(
            str(error) if isinstance(error, CheckError) else "(setting: [plan])"
        ) from None
    return doc, today, plan, text, settings


def report(args: argparse.Namespace, change: dict | None = None, after: bool = False) -> list[str]:
    doc, today, plan, text, settings = load(args)
    start, end = window_start(today, args.weeks), start_of(today + timedelta(days=1))
    flow = doc.get("flow")
    briefs = flow.get("briefs") if isinstance(flow, dict) else None
    history = history_of(doc.get("pull_requests"), start, end)
    medians = {k: median_of(history or [], k) for k in WAITS}
    waits = "waits inside the hours, never added: " + ", ".join(
        f"{k.replace('_', ' ')} {hours_text(medians[k])}" for k in WAITS
    )
    ctx = {"history": history, "today": today, "start": start, "n": args.weeks}
    ctx |= {"weeks": throughput_of(briefs, start, end, today), "settings": settings}
    ctx |= {"medians": medians, "waits": waits + f", queue {UNKNOWN}", "need": 0}
    out: list[str] = []
    for milestone, title in HEADING.findall(text):
        if not isinstance(briefs, list):
            out += [f"{milestone} {title}: {UNKNOWN} (the facts' briefs cannot be read)"]
            out += [ctx["waits"], inputs_line(milestone, ctx)]
            continue
        found = open_briefs(briefs, plan, milestone, change, after)
        ctx["need"] += len(found)
        out += estimate(milestone, title, found, ctx)
    return [*out, LIMITS]


# --- the deadline fit (brief #1220, ADR-0519) --------------------------------------------------


def plan_briefs(plan: Path, text: str, defaults: dict, review: Decimal) -> tuple[list, dict]:
    """Every brief file of the milestones in order, by key, as (id, hours, depends-on, touches),
    with the counts the assumptions name."""
    from session import glob_regex, literal, shared_patterns, touches_of  # noqa: PLC0415

    shared = [glob_regex(p) for p in shared_patterns(Path("."))]
    raw, counts = [], {"owner": 0, "missing": 0, "outside": 0, "sizes": []}
    for milestone, _ in HEADING.findall(text):
        for path in sorted((plan / "briefs" / milestone).glob("*.md"), key=lambda f: f.stem):
            body = path.read_text(encoding="utf-8")
            size, expected = estimate_parts(body)
            counts["sizes"].append(size)
            found = RANGE.fullmatch(expected) if expected != UNKNOWN else None
            if found is None and size in defaults:
                found, counts["owner"] = RANGE.fullmatch(defaults[size]), counts["owner"] + 1
            if found is None:
                counts["missing"] += 1
            mid = (Decimal(found[1]) + Decimal(found[2])) / 2 if found else Decimal(0)
            deps = [d.strip() for line in DEPENDS.findall(body) for d in line.split(",")]
            touches = [
                literal(t)
                for t in touches_of(body)
                if not any(r.fullmatch(literal(t)) for r in shared)
            ]
            raw.append((f"{milestone}/{path.stem}", path.stem, mid + review, deps, touches))
    keys: dict[str, str] = {}
    for ident, key, *_ in raw:
        keys.setdefault(key, ident)
    items = []
    for ident, _, hours, deps, touches in raw:
        inside = {keys[d] for d in deps if d in keys}
        counts["outside"] += sum(1 for d in deps if d and d not in keys)
        items.append((ident, hours, frozenset(inside), touches))
    return items, counts


def overlaps(mine: list[str], theirs: list[str]) -> bool:
    return any(a.startswith(b) or b.startswith(a) for a in mine for b in theirs)


def makespan(items: list, lanes: int) -> Decimal | None:
    """The hours a list schedule of `lanes` builders takes, or None when briefs wait for each
    other forever (a `Depends-on` cycle)."""
    pending, running, done, now = list(items), [], set(), Decimal(0)
    while pending or running:
        for item in list(pending):
            if len(running) >= lanes:
                break
            _, hours, deps, touches = item
            if deps <= done and not any(overlaps(touches, r[3]) for _, r in running):
                running.append((now + hours, item))
                pending.remove(item)
        if not running:
            return None
        now = min(end for end, _ in running)
        done |= {r[0] for end, r in running if end == now}
        running = [(end, r) for end, r in running if end != now]
    return now


def soonest(items: list, builders: int) -> Decimal:
    """The soonest finish with at most `builders` at once: more builders never finish later."""
    spans = [makespan(items, lanes) for lanes in range(1, min(builders, len(items)) + 1)]
    return min((s for s in spans if s is not None), default=Decimal(0))


def working_days(hours: Decimal, per_day: Decimal) -> int:
    return int((hours / per_day).to_integral_value(rounding=ROUND_CEILING))


def nth_working_day(today: date, k: int) -> date:
    day = today
    while k > 0:
        day += timedelta(days=1)
        k -= day.weekday() < 5
    return day


def index_of(today: date, day: date) -> int:
    """The working days in (today, day], or minus those in (day, today] for an earlier day."""
    low, high, sign = (today, day, 1) if day >= today else (day, today, -1)
    days = (high - low).days
    return sign * sum(1 for i in range(1, days + 1) if (low + timedelta(days=i)).weekday() < 5)


def to_move(items: list, builders: int, limit: int, per_day: Decimal) -> list[str]:
    """The latest briefs first, each with the briefs that depend on it, until the rest fits."""
    moved: set[str] = set()
    for ident, *_ in reversed(items):
        if ident in moved:
            continue
        grow = {ident}
        while True:
            more = {i for i, _, deps, _ in items if i not in grow | moved and deps & grow}
            if not more:
                break
            grow |= more
        moved |= grow
        rest = [item for item in items if item[0] not in moved]
        if working_days(soonest(rest, builders), per_day) <= limit:
            break
    return [item[0] for item in items if item[0] in moved]


def deadline_fit(args: argparse.Namespace) -> list[str]:
    doc, today, plan, text, settings = load(args)
    review, per_day, deadline = args.review_hours, args.hours_per_day, args.deadline
    items, counts = plan_briefs(plan, text, settings["default_hours"], review)
    start, end = window_start(today, args.weeks), start_of(today + timedelta(days=1))
    flow = doc.get("flow")
    history = history_of(doc.get("pull_requests"), start, end)
    weeks = throughput_of(flow.get("briefs") if isinstance(flow, dict) else None, start, end, today)
    if not reasons_of(history, weeks, counts["sizes"], settings["calibration_min"]):
        raise Refusal(
            "the history is calibrated; the fit is for the uncalibrated estimate "
            "(option: --deadline)"
        )
    if makespan(items, 1) is None:
        raise Refusal("the brief files' Depends-on lines wait for each other (option: --plan)")
    builders = ", ".join(str(n) for n in args.builders)
    out = [f"internal estimate: deadline {deadline} for builders {builders} from {today}"]
    out.append(
        f"assumptions: {len(items)} briefs from the plan's brief files in milestone then key "
        f"order; hours per brief the mid point of its Expected: range ({counts['owner']} owner "
        f"default) plus {plain(review)} h of review; {counts['missing']} briefs without an "
        f"estimate count 0 h; {plain(per_day)} h a working day Monday to Friday, no holidays, from "
        f"the first working day after {today}; a brief starts only after its Depends-on and never "
        "beside a brief whose Touches or Adds overlap (shared-mechanical paths apart); "
        f"{counts['outside']} Depends-on outside the plan's brief files taken as done; at most N "
        "builders at once, fewer when that finishes sooner; history and throughput not used"
    )
    limit = index_of(today, deadline)
    for n in args.builders:
        k = working_days(soonest(items, n), per_day)
        buffer = limit - k
        line = f"builders {n}: finish {nth_working_day(today, k)}, buffer {buffer} working days; "
        if buffer >= 0:
            line += "meets the deadline"
        else:
            line += "to meet the deadline move " + ", ".join(to_move(items, n, limit, per_day))
        out.append(line)
    return [*out, LIMITS]


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(list(sys.argv[1:] if argv is None else argv))
        if args.deadline is not None:
            lines = deadline_fit(args)
        elif args.change is None:
            lines = report(args)
        else:
            change = scope_change(Path(args.plan), args.change)
            before = report(args, change)[:-1]
            lines = [f"effect of {args.change}: before", *before]
            lines += [f"effect of {args.change}: after", *report(args, change, after=True)]
    except Refusal as refusal:
        print(f"plan_estimate: {refusal}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
