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
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import ESTIMATE_LINES, CheckError, estimate_parts, plan_settings  # noqa: F401, E402
from facts import window_start  # noqa: E402
from metrics import stamp, start_of  # noqa: E402

import check_plan  # noqa: E402

UNKNOWN = "unknown"
USAGE = (
    "usage: plan_estimate.py --facts FILE [--plan DIR] [--today YYYY-MM-DD] [--weeks N] "
    "[--with SC-<n>]"
)
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
    args = parser.parse_args(argv)
    if args.change is not None and not SC_ID.fullmatch(args.change):
        raise Refusal("--with names a scope change SC-<n> (option: --with)")
    if not (args.weeks.isdigit() and 4 <= int(args.weeks) <= 52):
        raise Refusal("--weeks must be a whole number from 4 to 52 (option: --weeks)")
    args.weeks = int(args.weeks)
    return args


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
    adds = [(k, size, hours) for m, k, size, hours in (change or {}).get("adds", []) if m == milestone]
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


def report(args: argparse.Namespace, change: dict | None = None, after: bool = False) -> list[str]:
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


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(list(sys.argv[1:] if argv is None else argv))
        if args.change is None:
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
