"""Per-PR metrics and the weekly report (SPEC-0007).

Standard library only. It reads the GitHub REST API with `gh api` (GET only; `gh` holds the
credential, this script holds none) or recorded JSON files (`--api-dir`), and local git objects.
It writes only to stdout. Every field is derived; nothing is typed by an agent, and a field whose
inputs are missing is `unknown`, never 0 or no (rule 10).
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from common import CheckError, git, matches, read_list, repo_root, run, show, test_dirs

NAME = "metrics"
USAGE = (
    "usage: metrics.py [--today YYYY-MM-DD] [--repo OWNER/REPO] [--api-dir DIR] [--issues FILE] "
    "[--print-action | --print-title | --print-body]"
)
UNKNOWN = "unknown"
NONE = "-"
PROTECTED_LIST = "config/protected-paths.txt"
NOTE = "Derived from git and the GitHub REST API; no field is typed by an agent."
WEAKENING_SET = frozenset(
    {
        "check_protected_changes",
        "check_requirements",
        "check_adrs",
        "check_specs",
        "reviewers --check-codeowners",
        "check_kit_tests",
    }
)
UNSPLIT_STEP = "Governance checks"
VERDICT = re.compile(r"Verdict: (?:cleared ([0-9a-f]{4,40})|(fix list)|(rejected))")
ADR_FILE = re.compile(r"docs/adr/\d{4}-[^/]+\.md")
AMENDMENT_FILE = re.compile(r"docs/runs/proposed-spec-amendments-[^/]+\.md")
TEST_PATTERN = r"^[[:space:]]*(async[[:space:]]+)?def test_"
COLUMNS = (
    "number state source opened_at closed_at hours_open_to_merge rejected rejected_verdicts "
    "review_rounds merged_head_cleared blocked_weakenings governance_failures deviations "
    "cost_class protected_classes adrs_added additions deletions changed_files tests_before "
    "tests_after"
).split()
PAGE = 100


# --- the sources ------------------------------------------------------------------------------


class ApiDir:
    """Recorded responses: one JSON file per request, named as in SPEC-0007 rule 20."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self, name: str, endpoint: str, until: Any = None) -> Any:
        file = self.path / f"{name}.json"
        if not file.is_file():
            return None
        try:
            return json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise CheckError(f"{name}.json in --api-dir is not JSON (path class api-dir)") from None


class Gh:
    """Live reads: `gh api` with GET only, paged by hand. A failed read is None (unknown)."""

    def __init__(self, repo: str) -> None:
        self.repo = repo

    def one(self, endpoint: str) -> Any:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["gh", "api", "--method", "GET", endpoint], capture_output=True, text=True
        )
        if proc.returncode != 0:
            return None
        try:
            return json.loads(proc.stdout)
        except ValueError:
            return None

    def get(self, name: str, endpoint: str, until: Any = None) -> Any:
        endpoint = endpoint.replace("{repo}", self.repo)
        if name == "pulls" or name.startswith(("comments-", "files-", "commits-")):
            return self.pages(endpoint, until)
        return self.one(endpoint)

    def pages(self, endpoint: str, until: Any) -> Any:
        sep = "&" if "?" in endpoint else "?"
        out: list = []
        page = 1
        while True:
            chunk = self.one(f"{endpoint}{sep}per_page={PAGE}&page={page}")
            if chunk is None:
                return None
            out += chunk
            if len(chunk) < PAGE or (until and until(chunk)):
                return out
            page += 1


def origin_repo() -> str:
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    url = git(repo_root(), "remote", "get-url", "origin", check=False).strip()
    match = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?$", url)
    if not match:
        raise CheckError("repository unknown; pass --repo OWNER/REPO (path class: git remote)")
    return match.group(1)


# --- the window -------------------------------------------------------------------------------


def window(today: date) -> tuple[date, date]:
    """The full ISO week before the week of `today`: Monday to the next Monday (half-open)."""
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(days=7), monday


def week_label(start: date) -> str:
    year, week, _ = start.isocalendar()
    return f"{year}-W{week:02d}"


def stamp(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def start_of(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


# --- the issue --------------------------------------------------------------------------------


def marker(week: str) -> str:
    return f"<!-- agk-metrics {week} -->"


def matching(issues: list[dict], week: str) -> list[int]:
    return sorted(int(i["number"]) for i in issues if marker(week) in (i.get("body") or ""))


def choose_action(issues: list[dict], week: str) -> str:
    """`create`, or `update N` for the lowest-numbered issue of that week; never `none`."""
    found = matching(issues, week)
    return f"update {found[0]}" if found else "create"


# --- verdict comments -------------------------------------------------------------------------


def verdicts(comments: list[dict] | None) -> list[tuple[str, str]] | None:
    """(kind, sha) of every verdict comment, in time order; kind is cleared, fix or rejected."""
    if comments is None:
        return None
    found = []
    for c in sorted(comments, key=lambda c: c.get("created_at") or ""):
        lines = (c.get("body") or "").splitlines()
        match = VERDICT.fullmatch(lines[0].strip()) if lines else None
        if match:
            kind = "cleared" if match.group(1) else "fix" if match.group(2) else "rejected"
            found.append((kind, match.group(1) or ""))
    return found


# --- the record -------------------------------------------------------------------------------


@dataclass
class Context:
    src: Any
    root: Path
    dirs: list[str]


def hours_between(opened: str | None, closed: str | None) -> str:
    a, b = stamp(opened), stamp(closed)
    if a is None or b is None:
        return UNKNOWN
    value = Decimal((b - a).total_seconds()) / Decimal(3600)
    return str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def governance(ctx: Context, shas: list[str] | None) -> tuple[str, str]:
    """(blocked_weakenings, governance_failures) over the head commits of the pull request."""
    if shas is None:
        return UNKNOWN, UNKNOWN
    failures = 0
    blocked = 0
    unsplit = False
    for sha in shas:
        checks = ctx.src.get(
            f"checks-{sha}", "repos/{repo}/commits/" + sha + "/check-runs?per_page=100"
        )
        if not isinstance(checks, dict) or "check_runs" not in checks:
            return UNKNOWN, UNKNOWN
        for run_ in checks["check_runs"]:
            if run_.get("name") != "governance" or run_.get("conclusion") != "failure":
                continue
            failures += 1
            job = ctx.src.get(
                f"jobs-{run_.get('id')}", f"repos/{{repo}}/actions/jobs/{run_.get('id')}"
            )
            steps = job.get("steps") if isinstance(job, dict) else None
            if not steps:
                unsplit = True
                continue
            names = {s.get("name") for s in steps}
            if UNSPLIT_STEP in names:
                unsplit = True
                continue
            if any(
                s.get("conclusion") == "failure" and s.get("name") in WEAKENING_SET for s in steps
            ):
                blocked += 1
    return (UNKNOWN if unsplit else str(blocked)), str(failures)


def protected_classes(ctx: Context, rev: str | None, files: list[dict] | None) -> str:
    if rev is None or files is None:
        return UNKNOWN
    listing = show(ctx.root, rev, PROTECTED_LIST)
    if listing is None:
        return UNKNOWN
    entries = read_list(listing)
    found = sorted({e for f in files for e in entries if matches(f.get("filename", ""), e)})
    return ", ".join(found) if found else NONE


def count_tests(ctx: Context, sha: str | None) -> str:
    if not sha:
        return UNKNOWN
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "grep", "-c", "-E", TEST_PATTERN, sha, "--", *ctx.dirs],
        cwd=ctx.root,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 1:
        return "0"
    if proc.returncode != 0:
        return UNKNOWN
    total = 0
    for line in proc.stdout.splitlines():
        path, _, count = line.rpartition(":")
        if path.endswith(".py") and count.isdigit():
            total += int(count)
    return str(total)


def cost_class(merged: bool, rounds: str, hours: str) -> str:
    if not merged:
        return "L"
    if rounds == UNKNOWN or hours == UNKNOWN:
        return UNKNOWN
    n, h = int(rounds), float(hours)
    if n == 0 and h < 24:
        return "S"
    if n <= 2 and h < 72:
        return "M"
    return "L"


def build_record(ctx: Context, detail: dict) -> dict[str, str]:
    n = detail["number"]
    merged = bool(detail.get("merged_at"))
    comments = ctx.src.get(f"comments-{n}", f"repos/{{repo}}/issues/{n}/comments")
    files = ctx.src.get(f"files-{n}", f"repos/{{repo}}/pulls/{n}/files")
    commits = ctx.src.get(f"commits-{n}", f"repos/{{repo}}/pulls/{n}/commits")
    listed = verdicts(comments if isinstance(comments, list) else None)
    head = (detail.get("head") or {}).get("sha") or ""

    hours = hours_between(detail.get("created_at"), detail.get("merged_at")) if merged else NONE
    if not merged:
        rejected = "yes"
    elif listed is None:
        rejected = UNKNOWN
    else:
        rejected = "yes" if any(k == "rejected" for k, _ in listed) else "no"
    rejected_verdicts = UNKNOWN if listed is None else str(sum(k == "rejected" for k, _ in listed))
    rounds = str(sum(k == "fix" for k, _ in listed)) if listed else UNKNOWN
    if not merged:
        cleared = NONE
    elif not listed:
        cleared = UNKNOWN
    else:
        named = any(k == "cleared" and head.startswith(sha) for k, sha in listed)
        cleared = "yes" if named else "no"

    shas = [c.get("sha") for c in commits] if isinstance(commits, list) else None
    blocked, failures = governance(ctx, shas)

    names = (
        [(f.get("filename", ""), f.get("status", "")) for f in files]
        if isinstance(files, list)
        else None
    )
    adrs = deviations = UNKNOWN
    if names is not None:
        adrs = str(sum(1 for f, s in names if s == "added" and ADR_FILE.fullmatch(f)))
        deviations = str(sum(1 for f, s in names if s == "added" and AMENDMENT_FILE.fullmatch(f)))

    merge_sha = detail.get("merge_commit_sha") if merged else None
    rev = f"{merge_sha}^1" if merge_sha else (detail.get("base") or {}).get("sha")
    classes = protected_classes(ctx, rev, files if isinstance(files, list) else None)
    before = count_tests(ctx, rev) if merged else NONE
    after = count_tests(ctx, merge_sha) if merged else NONE

    def num(key: str) -> str:
        value = detail.get(key)
        return str(value) if isinstance(value, int) else UNKNOWN

    return {
        "number": str(n),
        "state": "merged" if merged else "closed",
        "source": "derived",
        "opened_at": detail.get("created_at") or UNKNOWN,
        "closed_at": detail.get("closed_at") or UNKNOWN,
        "hours_open_to_merge": hours,
        "rejected": rejected,
        "rejected_verdicts": rejected_verdicts,
        "review_rounds": rounds,
        "merged_head_cleared": cleared,
        "blocked_weakenings": blocked,
        "governance_failures": failures,
        "deviations": deviations,
        "cost_class": cost_class(merged, rounds, hours),
        "protected_classes": classes,
        "adrs_added": adrs,
        "additions": num("additions"),
        "deletions": num("deletions"),
        "changed_files": num("changed_files"),
        "tests_before": before,
        "tests_after": after,
    }


# --- the report -------------------------------------------------------------------------------


def listed_in_window(pulls: list[dict], start: date, end: date) -> list[dict]:
    lo, hi = start_of(start), start_of(end)
    found = []
    for p in pulls:
        closed = stamp(p.get("closed_at"))
        if closed is not None and lo <= closed < hi:
            found.append(p)
    return sorted(found, key=lambda p: p["number"])


def totals(records: list[dict[str, str]]) -> str:
    def total(field: str) -> int:
        return sum(int(r[field]) for r in records if r[field].isdigit())

    classes = [r["cost_class"] for r in records]
    return (
        f"totals: rejected={sum(r['rejected'] == 'yes' for r in records)} "
        f"blocked_weakenings={total('blocked_weakenings')} deviations={total('deviations')} "
        f"cost S={classes.count('S')} M={classes.count('M')} L={classes.count('L')} "
        f"unknown={classes.count(UNKNOWN)}"
    )


def render(
    week: str, start: date, end: date, records: list[dict[str, str]], listed: int, flags: list[str]
) -> str:
    unknown_cells = sum(1 for r in records for v in r.values() if v == UNKNOWN)
    lines = [*flags, f"agk metrics {week} (window {start} to {end})", ""]
    lines += ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(r[c] for c in COLUMNS) + " |" for r in records]
    lines += [
        "",
        totals(records),
        f"closed in window: {listed}; recorded: {len(records)}; unknown cells: {unknown_cells}",
        "",
        NOTE,
        marker(week),
    ]
    return "\n".join(lines) + "\n"


def report(ctx: Context, today: date, issues: list[dict]) -> tuple[str, bool]:
    start, end = window(today)
    week = week_label(start)
    cutoff = start_of(start)

    def older(chunk: list[dict]) -> bool:
        last = stamp(chunk[-1].get("updated_at") or chunk[-1].get("closed_at"))
        return last is not None and last < cutoff

    pulls = ctx.src.get(
        "pulls",
        "repos/{repo}/pulls?state=closed&sort=updated&direction=desc",
        older,
    )
    if not isinstance(pulls, list):
        raise CheckError("cannot list pull requests (path class: the GitHub API)")
    in_window = listed_in_window(pulls, start, end)
    records = []
    for p in in_window:
        detail = ctx.src.get(f"pull-{p['number']}", f"repos/{{repo}}/pulls/{p['number']}")
        if isinstance(detail, dict) and "number" in detail:
            records.append(build_record(ctx, detail))
    records.sort(key=lambda r: int(r["number"]))
    flags = []
    duplicates = matching(issues, week)
    if len(duplicates) > 1:
        ordered = ",".join(f"#{n}" for n in duplicates)
        flags.append(f"duplicate metrics issues: {ordered}; #{duplicates[0]} is the one updated")
    incomplete = len(records) != len(in_window)
    if incomplete:
        flags.append(f"INCOMPLETE: closed in window {len(in_window)}, recorded {len(records)}")
    return render(week, start, end, records, len(in_window), flags), incomplete


# --- command line -----------------------------------------------------------------------------


def parse_args(args: list[str]) -> dict | None:
    options: dict = {"today": None, "repo": None, "api": None, "issues": None, "mode": "body"}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--today", "--repo", "--api-dir", "--issues") and i + 1 < len(args):
            value = args[i + 1]
            if arg == "--today":
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    return None
                try:
                    options["today"] = date.fromisoformat(value)
                except ValueError:
                    return None
            else:
                options[{"--repo": "repo", "--api-dir": "api", "--issues": "issues"}[arg]] = value
            i += 2
        elif arg in ("--print-action", "--print-title", "--print-body") and not options.get(
            "mode_set"
        ):
            options["mode"] = arg[len("--print-") :]
            options["mode_set"] = True
            i += 1
        else:
            return None
    return options


def load_issues(path: str | None) -> list[dict]:
    if not path:
        return []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise CheckError("--issues file is not readable JSON (path class: issues file)") from None
    if not isinstance(data, list):
        raise CheckError("--issues file is not a JSON list (path class: issues file)")
    return data


def main(argv: list[str] | None = None) -> int:
    options = parse_args(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    today = options["today"] or datetime.now(UTC).date()
    start, _ = window(today)
    week = week_label(start)
    if options["mode"] == "title":
        print(f"agk metrics {week}")
        return 0
    issues = load_issues(options["issues"])
    if options["mode"] == "action":
        print(choose_action(issues, week))
        return 0
    root = repo_root()
    src = ApiDir(Path(options["api"])) if options["api"] else Gh(options["repo"] or origin_repo())
    ctx = Context(src, root, test_dirs(root))
    body, incomplete = report(ctx, today, issues)
    sys.stdout.write(body)
    return 1 if incomplete else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
