"""The nine-point operations checklist (brief #799, REQ-054, ADR-0374; brief #981, ADR-0420).

    python3 scripts/agk/checklist.py [--root DIR] [--days N] [--saved FILE]

Prints nine lines `<n>. <name>: <yes|partly|no|unknown> <measure>` and exits 0: the owner's nine
points, in his order, each from a record AGK already keeps. Standard library and `common.py` only;
it writes nothing and never makes a network call. In GitHub mode it reads the one file that
`python3 scripts/agk/metrics.py --save-checklist` wrote (`--saved FILE`, by default
`agk-checklist.json` in the checkout's git directory); the window is the `--days` (7 by default)
before the file's `saved_at`. A value that cannot be read is `unknown` with the reason, never 0.
A point is `yes` only past its threshold in the optional `[checklist]` table of agk.toml; an
unknown key or a wrong value is refused naming the setting, never the value (exit 1).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, config_source, git, personal_table, run

NAME = "checklist"
SAVED_NAME = "agk-checklist.json"
UNKNOWN = "unknown"
USAGE = "usage: checklist.py [--root DIR] [--days N] [--saved FILE]"
NAMES = (
    "machine capacity",
    "conductor runs builders",
    "test optimization",
    "parallel runs",
    "auto-merge",
    "model selection",
    "conflict planning",
    "smart assignment",
    "cost per pull request",
)
SHARES = {"capacity_use": 0.5, "conductor_share": 0.8, "selected_share": 0.5, "usage_share": 0.8}
LIMITS = {"parallel_peak": 2, "merge_late": 0, "merge_failed_runs": 0, "false_hold_rate": 0.2}
LIMITS_MINUTES = {"idle_minutes": 60}
DEFAULTS = {**SHARES, **LIMITS, **LIMITS_MINUTES}  # the kit's first guesses (verify)
DEFAULT_MAX_BUILDERS = 3  # `FLOW_DEFAULTS` of facts.py
DEFAULT_STALL_HOURS = 4
LATE_MINUTES = 20  # brief #797 answer 5
STEP = timedelta(minutes=15)
HOLDS_FILE = "docs/runs/holds.jsonl"  # metrics.HOLDS_FILE
TAKE = re.compile(r"taken(?: over)?: (\S+) \d{4}-\d{2}-\d{2}(?: build \([\w.-]+\))?( retakes)?.*")
RELEASED = re.compile(r"released: (\S+)")
ASSIGN = re.compile(r"Assign: (\S+) #(\d+)\b")  # every brief form of session.py's ASSIGN
REFUSED = re.compile(r"\bRefused \((\d+)\)")
PR_TESTS = re.compile(
    r"pr tests: (\d+) runs; selected (\d+) of (\d+) \([^)]*\); test step ([\d.]+) minutes"
)
SELECTED_MEDIAN = re.compile(r"pr tests median: selected ([\d.]+) minutes")
FULL_MEDIAN = re.compile(r"full suite: median (\d+)s")
USAGE_FIGURE = re.compile(r"\bUsage: \d")
DEPENDS = re.compile(r"^Depends-on:(.*)$", re.M)
FAILED = ("failure", "timed_out", "startup_failure")
Point = tuple[str, str]


def stamp(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def settings(root: Path) -> dict:
    """The thresholds: the `[checklist]` table's, else the kit's; a bad one is refused by name."""
    table = config_source(root).get("checklist", {})
    if not isinstance(table, dict):
        raise CheckError("the [checklist] table is refused (setting: checklist)")
    for key, value in table.items():
        setting = f"checklist.{key}"
        if key not in DEFAULTS or not isinstance(value, int | float) or isinstance(value, bool):
            raise CheckError(f"the [checklist] table is refused (setting: {setting})")
        if value < 0 or (key in SHARES and value > 1):
            raise CheckError(f"the [checklist] table is refused (setting: {setting})")
    return {**DEFAULTS, **table}


def default_saved(root: Path) -> Path | None:
    """`agk-checklist.json` in the checkout's git directory, which git never tracks."""
    try:
        common_dir = git(root, "rev-parse", "--git-common-dir").strip()
    except CheckError:
        return None
    return (root / common_dir / SAVED_NAME) if common_dir else None


def load_saved(path: Path | None) -> dict | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8")) if path else None
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict) or stamp(document.get("saved_at")) is None:
        return None
    return document


def first_line(comment: dict) -> str:
    lines = str(comment.get("body") or "").splitlines()
    return lines[0].strip() if lines else ""


def issue_of(comment: dict) -> int | None:
    tail = str(comment.get("issue_url") or "").rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else None


class View:
    """The saved records of the window, read once."""

    def __init__(self, root: Path, saved: dict, days: int, limits: dict) -> None:
        source = config_source(root)
        self.flow = source.get("flow") if isinstance(source.get("flow"), dict) else {}
        self.testing = source.get("testing") if isinstance(source.get("testing"), dict) else {}
        self.limits = limits
        self.end = stamp(saved["saved_at"])
        self.start = self.end - timedelta(days=days)
        comments = saved.get("comments")
        self.comments = (
            [c for c in comments if stamp(c.get("created_at")) is not None]
            if isinstance(comments, list)
            else None
        )
        facts = saved.get("facts") if isinstance(saved.get("facts"), dict) else {}
        pulls = facts.get("pull_requests")
        self.pulls = pulls if isinstance(pulls, list) else None
        flow = facts.get("flow") if isinstance(facts.get("flow"), dict) else {}
        hours = flow.get("stall_hours")
        self.stall = timedelta(hours=hours if isinstance(hours, int) else DEFAULT_STALL_HOURS)
        self.runs = saved.get("runs") if isinstance(saved.get("runs"), list) else None
        self.briefs = saved.get("briefs") if isinstance(saved.get("briefs"), list) else None
        self.weekly = {k: saved.get(k) for k in ("pr_tests", "pr_tests_median", "full_suite")}
        window = saved.get("window_tests")
        self.window_tests = window if isinstance(window, dict) else None
        authors = saved.get("verdict_authors")
        self.authors = set(authors) if isinstance(authors, list) else None
        issues = saved.get("conductor_issues")
        self.conductor_issues = set(issues) if isinstance(issues, list) else None
        self.local = saved.get("local_mode") is True
        maximum = self.flow.get("max_builders", DEFAULT_MAX_BUILDERS)
        usable = isinstance(maximum, int) and not isinstance(maximum, bool) and maximum >= 1
        self.max_builders = maximum if usable else DEFAULT_MAX_BUILDERS

    def inside(self, value: Any) -> bool:
        when = stamp(value)
        return when is not None and self.start <= when <= self.end

    def reports(self) -> list[dict]:
        """The conductor's reports of the window, on the plan issue only."""
        plan = self.flow.get("plan_issue")
        return [
            c
            for c in self.comments or []
            if plan is not None
            and issue_of(c) == plan
            and first_line(c).startswith("Conductor report")
            and self.inside(c.get("created_at"))
        ]

    def takes(self) -> list[tuple[int, datetime, str, bool]]:
        """Every take, in time order: (brief, when, session, retake)."""
        found = []
        for comment in self.comments or []:
            match = TAKE.fullmatch(first_line(comment))
            number = issue_of(comment)
            if match and number is not None:
                retake = bool(match[2]) or first_line(comment).startswith("taken over:")
                found.append((number, stamp(comment["created_at"]), match[1], retake))
        return sorted(found, key=lambda item: item[1])

    def intervals(self) -> list[tuple[int, datetime, datetime]]:
        """A builder is alive from its take to its first `Report:`, its `released:`, the brief's
        close or the stall limit, whichever is first."""
        briefs_of_pulls = {
            p.get("number"): p.get("brief") for p in self.pulls or [] if isinstance(p, dict)
        }
        closed = {b.get("number"): stamp(b.get("closed_at")) for b in self.briefs or []}
        out = []
        for number, begin, session, _ in self.takes():
            limit = begin + self.stall
            ends = [limit, self.end]
            if closed.get(number) and closed[number] > begin:
                ends.append(closed[number])
            for comment in self.comments or []:
                when = stamp(comment.get("created_at"))
                line = first_line(comment)
                if when is None or when <= begin:
                    continue
                released = RELEASED.match(line)
                if (issue_of(comment) == number and released and released[1] == session) or (
                    line.startswith("Report:") and briefs_of_pulls.get(issue_of(comment)) == number
                ):
                    ends.append(when)
            end = min(ends)
            if end >= self.start and begin <= self.end:
                out.append((number, max(begin, self.start), end))
        return out


def alive(intervals: list[tuple[int, datetime, datetime]], moment: datetime) -> int:
    return sum(1 for _, begin, end in intervals if begin <= moment < end)


def peak(view: View) -> int | None:
    if view.comments is None:
        return None
    intervals = view.intervals()
    return max((alive(intervals, begin) for _, begin, _ in intervals), default=0)


def refused_of(view: View) -> int | None:
    counts = [int(m[1]) for c in view.reports() for m in [REFUSED.search(c["body"])] if m]
    return sum(counts) if counts else None


def capacity(view: View) -> Point:
    top = peak(view)
    if top is None:
        return UNKNOWN, "the comments were not saved"
    maximum, refused = view.max_builders, refused_of(view)
    shown = UNKNOWN if refused is None else refused
    measure = f"peak {top} of max_builders {maximum}; refused {shown}"
    if top == 0:
        return "no", measure
    if top / maximum >= view.limits["capacity_use"] and refused == 0:
        return "yes", measure
    return "partly", measure


def assigns(view: View) -> list[tuple[datetime, str, int]]:
    """Brief #981 answer 1: each `Assign: <slot> #<brief>` on the conductor issue by a listed
    verdict author, in time order: (when, slot, brief)."""
    found = []
    for comment in view.comments or []:
        match = ASSIGN.match(first_line(comment))
        if (
            match
            and comment.get("author") in (view.authors or ())
            and issue_of(comment) in (view.conductor_issues or ())
        ):
            found.append((stamp(comment["created_at"]), match[1], int(match[2])))
    return sorted(found, key=lambda item: item[0])


def conductor_starts(view: View) -> Point:
    if view.comments is None:
        return UNKNOWN, "the comments were not saved"
    takes = [t for t in view.takes() if view.inside(t[1].isoformat())]
    if not takes:
        return UNKNOWN, "no builder was started in the window"
    if view.authors is None or view.conductor_issues is None:
        return UNKNOWN, "the verdict authors or the conductor issue were not saved"
    open_assigns = assigns(view)
    started = 0
    for number, when, session, _ in takes:
        found = next((a for a in open_assigns if a[0] <= when and a[1:] == (session, number)), None)
        if found is not None:
            open_assigns.remove(found)  # one Assign starts one take
            started += 1
    stalls = sum(1 for t in takes if t[3])
    percent = round(100 * started / len(takes))
    measure = (
        f"conductor {started} of {len(takes)} ({percent}%); by hand {len(takes) - started}; "
        f"stalls replaced {stalls}"
    )
    if started == 0:
        return "no", measure
    return "yes" if started / len(takes) >= view.limits["conductor_share"] else "partly", measure


def test_figures(view: View) -> tuple[dict, str] | None:
    """The weekly lines when they count a run, else the window's (brief #981 answer 2)."""
    weekly = view.weekly.get("pr_tests")
    match = PR_TESTS.search(weekly) if isinstance(weekly, str) else None
    if match and int(match[1]) > 0:
        return view.weekly, "weekly line"
    if view.window_tests is not None:
        return view.window_tests, "window"
    return None


def minutes_of(pattern: re.Pattern, line: Any, scale: float = 1) -> float | None:
    match = pattern.search(line) if isinstance(line, str) else None
    return float(match[1]) / scale if match else None


def tests_point(view: View) -> Point:
    if view.local:
        return UNKNOWN, "local mode: no Actions runs to read"
    found, source = test_figures(view) or (view.weekly, "weekly line")
    line = found.get("pr_tests")
    match = PR_TESTS.search(line) if isinstance(line, str) else None
    if match is None:
        return UNKNOWN, "no weekly metrics line or window figures were saved"
    runs, selected = int(match[1]), int(match[2])
    if runs == 0:
        return UNKNOWN, f"no pull request runs in the {source}"
    pr = minutes_of(SELECTED_MEDIAN, found.get("pr_tests_median"))
    full = minutes_of(FULL_MEDIAN, found.get("full_suite"), 60)

    def shown(value: float | None) -> str:
        return UNKNOWN if value is None else f"{value:.1f} minutes"

    measure = (
        f"selected {selected} of {runs} pull request runs; test step {match[4]} minutes; "
        f"selected median {shown(pr)}; full suite median on main {shown(full)} ({source})"
    )
    if selected == 0:
        return "no", measure
    fast = pr is not None and full is not None and pr <= full
    return "yes" if selected / runs >= view.limits["selected_share"] and fast else "partly", measure


def parallel(view: View) -> Point:
    top = peak(view)
    if top is None:
        return UNKNOWN, "the comments were not saved"
    workers = view.testing.get("workers", 1)
    measure = f"peak {top} builders at once; full suite workers {workers} (setting)"
    if top == 0:
        return "no", measure
    return "yes" if top >= view.limits["parallel_peak"] and workers != 1 else "partly", measure


def auto_merge(view: View) -> Point:
    if view.flow.get("auto_merge") is not True:
        return "no", "setting off"
    if view.local:
        return UNKNOWN, "local mode: no Actions runs to read"
    if view.runs is None or view.pulls is None:
        return UNKNOWN, "the runs or the pull requests were not saved"
    failed = sum(
        1
        for r in view.runs
        if r.get("name") == "merger"
        and r.get("conclusion") in FAILED
        and view.inside(r.get("created_at"))
    )
    late = sum(1 for p in view.pulls if isinstance(p, dict) and late_cleared(p, view.end))
    measure = f"setting on; failed merger runs {failed}; cleared unmerged over 20 min {late}"
    good = failed <= view.limits["merge_failed_runs"] and late <= view.limits["merge_late"]
    return "yes" if good else "partly", measure


def late_cleared(pull: dict, end: datetime) -> bool:
    if pull.get("state") != "open" or pull.get("head_cleared") != "yes":
        return False
    head = str(pull.get("head") or "")
    verdicts = pull.get("verdicts") if isinstance(pull.get("verdicts"), list) else []
    times = [stamp(v.get("at")) for v in verdicts if head.startswith(str(v.get("sha") or "-"))]
    times = [t for t in times if t is not None]
    return bool(times) and (end - max(times)) > timedelta(minutes=LATE_MINUTES)


def models() -> Point:
    return UNKNOWN, "no start records its runtime model (Q-799-2)"


def conflicts(root: Path, view: View | None) -> Point:
    if view is None:
        return UNKNOWN, "no saved window"
    try:
        lines = (root / HOLDS_FILE).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        lines = []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and view.inside(row.get("at")):
            rows.append(row)
    if not rows:
        return UNKNOWN, "no hold recorded in the window"
    marks = [r for r in rows if r.get("mark") in ("true", "false")]
    if not marks:
        return UNKNOWN, f"holds {len(rows)}; false-hold rate unknown"
    wrong = sum(1 for r in marks if r["mark"] == "false")
    rate = wrong / len(marks)
    measure = f"holds {len(rows)}; false holds {wrong}/{len(marks)} ({round(100 * rate)}%)"
    limit = view.limits["false_hold_rate"]
    if rate <= limit:
        return "yes", measure
    return ("partly" if rate <= 2 * limit else "no"), measure


def ready_count(view: View, taken_at: dict, moment: datetime) -> int:
    def closed_by(number: int) -> bool:
        record = next((b for b in view.briefs if b.get("number") == number), None)
        if record is None:
            return True  # a dependency that is not a brief of the list is not waited on here
        when = stamp(record.get("closed_at"))
        return when is not None and when <= moment

    count = 0
    for brief in view.briefs:
        begin, end = stamp(brief.get("created_at")), stamp(brief.get("closed_at"))
        if begin is None or begin > moment or (end is not None and end <= moment):
            continue
        taken = taken_at.get(brief.get("number"))
        if taken is not None and taken <= moment:
            continue
        depends = DEPENDS.findall(str(brief.get("body") or ""))
        needs = [int(n) for line in depends for n in re.findall(r"#(\d+)", line)]
        if all(closed_by(number) for number in needs):
            count += 1
    return count


def assignment(view: View) -> Point:
    if view.briefs is None or view.comments is None:
        return UNKNOWN, "the briefs or the comments were not saved"
    taken_at: dict = {}
    for number, when, _, _ in view.takes():
        taken_at.setdefault(number, when)
    intervals = view.intervals()
    idle = 0
    moment = view.start
    while moment < view.end:
        free = max(0, view.max_builders - alive(intervals, moment))
        idle += min(free, ready_count(view, taken_at, moment)) * 15
        moment += STEP
    measure = f"idle builder-minutes {idle} while a brief was ready"
    limit = view.limits["idle_minutes"]
    if idle <= limit:
        return "yes", measure
    return ("partly" if idle <= 2 * limit else "no"), measure


def cost(view: View) -> Point:
    if view.comments is None:
        return UNKNOWN, "the comments were not saved"
    reports = [
        c
        for c in view.comments
        if first_line(c).startswith("Report:") and view.inside(c.get("created_at"))
    ]
    if not reports:
        return UNKNOWN, "no Report line in the window"
    figured = sum(1 for c in reports if USAGE_FIGURE.search(str(c.get("body") or "")))
    percent = round(100 * figured / len(reports))
    usage = [
        p["usage"]
        for p in view.pulls or []
        if isinstance(p, dict)
        and p.get("state") == "merged"
        and view.inside(p.get("merged_at"))
        and isinstance(p.get("usage"), int)
    ]
    tokens = (
        f"{round(sum(usage) / len(usage))} tokens per merged"
        if usage
        else f"tokens per merged {UNKNOWN}"
    )
    measure = f"Usage on {figured} of {len(reports)} reports ({percent}%); {tokens}"
    if figured == 0:
        return "no", measure
    enough = figured / len(reports) >= view.limits["usage_share"] and bool(usage)
    return "yes" if enough else "partly", measure


def points_of(root: Path, view: View) -> list[Point]:
    return [
        capacity(view),
        conductor_starts(view),
        tests_point(view),
        parallel(view),
        auto_merge(view),
        models(),
        conflicts(root, view),
        assignment(view),
        cost(view),
    ]


def unknown_points(reason: str) -> list[Point]:
    return [(UNKNOWN, reason)] * len(NAMES)


def parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="checklist.py", add_help=False)
    parser.add_argument("--root", default=".")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--saved")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return None
    return args if args.days >= 1 else None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args is None:
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(args.root)
    try:
        limits = settings(root)
        personal = personal_table(root) is not None
    except (CheckError, ValueError, OSError) as error:
        print(f"FAIL {NAME}: {error}")
        return 1
    path = Path(args.saved) if args.saved else default_saved(root)
    saved = load_saved(path)
    if personal:
        points = unknown_points("personal mode keeps no comment or run records")
    elif saved is None:
        points = unknown_points("no saved facts: run metrics.py --save-checklist")
    else:
        print(f"saved facts as of {saved['saved_at']}", file=sys.stderr)
        points = points_of(root, View(root, saved, args.days, limits))
    for number, (name, (status, measure)) in enumerate(zip(NAMES, points, strict=True), 1):
        print(f"{number}. {name}: {status} {measure}")
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
