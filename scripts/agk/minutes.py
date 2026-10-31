"""The GitHub Actions minutes of this month, before they run out (brief 324, ADR-0184).

Usage: python3 scripts/agk/minutes.py [--json | --line] [--repo OWNER/REPO]
                                      [--today YYYY-MM-DD] [--api-dir DIR]

Standard library only. It reads the GitHub REST API with `gh api` (GET only; `gh` holds the
credential, this script holds none) or recorded responses (`--api-dir`, one `<name>.json` per
read, or `<name>.status` holding the HTTP status of a refused read). It prints the minutes used this
month, the plan's included minutes where the billing API answers, an estimate from the repository's
run history (each job rounded up to a whole minute, as GitHub bills it), the minutes per merged pull
request, and a warning past `minutes_warn` percent of the included minutes. It writes nothing.
A figure that cannot be read is `unknown` with its reason class, never 0.

Brief #370 (ADR-0215): it also gives a level, `ok`, `50%`, `<minutes_warn>%` or `95%`, the highest
one the used minutes have reached of the included minutes (`unknown` when those are unknown), and
the day they run out at this month's daily rate so far (`runs out about YYYY-MM-DD`, or
`not this month`). `--line` prints only that, in one line, reading billing first and the run
history only when billing cannot be read; `doctor.py` (`actions-minutes`) and `/agk:launch` print
the same line.

Exit: 0 read, 3 the warning was printed, 1 refused (the repository cannot be read, or a setting is
invalid), 2 usage.
"""

from __future__ import annotations

import json
import math
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, minutes_warn, repo_root, run
from metrics import origin_repo

NAME = "minutes"
USAGE = (
    "usage: minutes.py [--json | --line] [--repo OWNER/REPO] [--today YYYY-MM-DD] [--api-dir DIR]"
)
PAGE = 100
# The run list answers at most this many runs for a filtered query (verify); past it the estimate
# is a lower bound.
RUN_CAP = 1000
GUIDE = "docs/guides/project-ci.md"
LOCAL_MODE = "docs/guides/local-mode.md"
HALF, TOP = 50, 95  # the fixed levels around minutes_warn (brief #370)
NOT_THIS_MONTH = "not this month"
SELF_HOSTED = "self-hosted"
# The rates at which a private repository's job uses the included minutes, by the runner's
# operating system as its labels name it (verify); any other runner counts once.
MULTIPLIERS = (("windows", 2), ("macos", 10))
# Job lists read at once: one `gh api` each, so a month of a thousand runs reads in minutes.
READERS = 8


def reason_of(status: int) -> str:
    """The reason class of a read that did not answer: refused, missing or unreadable."""
    if status in (401, 403):
        return "refused"
    if status in (404, 410):
        return "missing"
    return "unreadable"


# --- the sources ------------------------------------------------------------------------------


class ApiDir:
    """Recorded responses: `<name>.json` answers 200, `<name>.status` holds a refused read's status,
    and a read with neither is missing (404)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self, name: str, endpoint: str, until: Any = None) -> tuple[int, Any]:
        status = self.path / f"{name}.status"
        if status.is_file():
            text = status.read_text(encoding="utf-8").strip()
            return (int(text) if text.isdigit() else 0), None
        file = self.path / f"{name}.json"
        if not file.is_file():
            return 404, None
        try:
            return 200, json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise CheckError(f"{name}.json in --api-dir is not JSON (path class api-dir)") from None


class Gh:
    """Live reads: `gh api` with GET only, paged by hand."""

    def __init__(self, repo: str) -> None:
        self.repo = repo

    def one(self, endpoint: str) -> tuple[int, Any]:
        try:
            proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
                ["gh", "api", "--method", "GET", endpoint],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        except OSError:
            return 0, None
        if proc.returncode != 0:
            match = re.search(r"\(HTTP (\d{3})\)", proc.stderr or "")
            return (int(match.group(1)) if match else 0), None
        try:
            return 200, json.loads(proc.stdout)
        except ValueError:
            return 0, None

    def get(self, name: str, endpoint: str, until: Any = None) -> tuple[int, Any]:
        endpoint = endpoint.replace("{repo}", self.repo)
        if name == "runs":
            return self.keyed(endpoint, "workflow_runs", RUN_CAP // PAGE)
        if name.startswith("jobs-"):
            return self.keyed(endpoint, "jobs", None)
        if name == "pulls":
            return self.listed(endpoint, until)
        return self.one(endpoint)

    def keyed(self, endpoint: str, key: str, last_page: int | None) -> tuple[int, Any]:
        out: dict = {"total_count": 0, key: []}
        page = 1
        while True:
            status, chunk = self.one(f"{endpoint}&per_page={PAGE}&page={page}")
            if status != 200 or not isinstance(chunk, dict):
                return status, None
            out["total_count"] = chunk.get("total_count", 0)
            items = chunk.get(key) or []
            out[key] += items
            if len(items) < PAGE or len(out[key]) >= out["total_count"]:
                return 200, out
            if last_page is not None and page >= last_page:
                return 200, out
            page += 1

    def listed(self, endpoint: str, until: Any) -> tuple[int, Any]:
        out: list = []
        page = 1
        while True:
            status, chunk = self.one(f"{endpoint}&per_page={PAGE}&page={page}")
            if status != 200 or not isinstance(chunk, list):
                return status, None
            out += chunk
            if len(chunk) < PAGE or (until and until(chunk)):
                return 200, out
            page += 1


# --- the month --------------------------------------------------------------------------------


def stamp(text: Any) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def month_of(today: date) -> tuple[datetime, datetime]:
    """The calendar month of `today` in UTC: its first instant and the first of the next month."""
    start = datetime(today.year, today.month, 1, tzinfo=UTC)
    nxt = datetime(today.year + (today.month == 12), today.month % 12 + 1, 1, tzinfo=UTC)
    return start, nxt


def multiplier(job: dict) -> int:
    """The rate of a job's runner, read from its labels: Windows 2, macOS 10, otherwise 1."""
    labels = [str(x).lower() for x in job.get("labels") or []]
    for prefix, rate in MULTIPLIERS:
        if any(label.startswith(prefix) for label in labels):
            return rate
    return 1


def job_minutes(job: dict) -> int | None:
    """The minutes GitHub bills one job: its duration rounded up to a whole minute; a skipped job
    bills none; a job without both times (still running) is None."""
    started, completed = stamp(job.get("started_at")), stamp(job.get("completed_at"))
    if started is None or completed is None:
        return None
    if job.get("conclusion") == "skipped":
        return 0
    seconds = (completed - started).total_seconds()
    return math.ceil(seconds / 60) if seconds > 0 else 0


# --- the reading ------------------------------------------------------------------------------


@dataclass
class Estimate:
    minutes: int | None = 0
    reason: str | None = None
    complete: bool = True
    runs: int = 0
    self_hosted_jobs: int = 0
    running_jobs: int = 0
    workflows: dict[str, int] = field(default_factory=dict)


def estimate(src: Any, start: datetime, end: datetime, rates: bool = True) -> Estimate:
    """The month's minutes from the run history: each job of a GitHub-hosted runner that started
    in the month, rounded up per job, then multiplied by its runner's rate when `rates` (a private
    repository). A run created the day before the month is read, since its jobs may start in it;
    a re-run of an older run keeps its old creation time and is not read."""
    since = (start - timedelta(days=1)).date().isoformat()
    status, data = src.get("runs", f"/repos/{{repo}}/actions/runs?created=%3E%3D{since}")
    if status != 200 or not isinstance(data, dict):
        return Estimate(minutes=None, reason=reason_of(status), complete=False)
    runs = data.get("workflow_runs") or []
    est = Estimate()
    if isinstance(data.get("total_count"), int) and data["total_count"] > len(runs):
        est.complete = False
    floor = start - timedelta(days=1)
    chosen = [r for r in runs if (c := stamp(r.get("created_at"))) is not None and floor <= c < end]
    est.runs = len(chosen)

    def jobs_of(run_: dict) -> tuple[int, Any]:
        rid = run_.get("id")
        return src.get(f"jobs-{rid}", f"/repos/{{repo}}/actions/runs/{rid}/jobs?filter=all")

    with ThreadPoolExecutor(max_workers=READERS) as pool:
        answers = list(pool.map(jobs_of, chosen))
    for run_, (status, jobs) in zip(chosen, answers, strict=True):
        if status != 200 or not isinstance(jobs, dict):
            est.complete = False
            continue
        name = str(run_.get("name") or run_.get("path") or "unknown")
        for job in jobs.get("jobs") or []:
            started = stamp(job.get("started_at"))
            if started is None or not start <= started < end:
                continue
            est.workflows.setdefault(name, 0)
            if SELF_HOSTED in (job.get("labels") or []):
                est.self_hosted_jobs += 1
                continue
            minutes = job_minutes(job)
            if minutes is None:
                est.running_jobs += 1
                continue
            est.workflows[name] += minutes * (multiplier(job) if rates else 1)
    est.minutes = sum(est.workflows.values())
    return est


def merged_pulls(src: Any, start: datetime, end: datetime) -> int | None:
    """The pull requests merged in the month, or None when they cannot be read."""

    def older(chunk: list) -> bool:
        last = stamp(chunk[-1].get("updated_at")) if chunk else None
        return last is not None and last < start

    status, pulls = src.get(
        "pulls", "/repos/{repo}/pulls?state=closed&sort=updated&direction=desc", older
    )
    if status != 200 or not isinstance(pulls, list):
        return None
    count = 0
    for pull in pulls:
        merged = stamp(pull.get("merged_at"))
        if merged is not None and start <= merged < end:
            count += 1
    return count


def billing(src: Any, owner: dict) -> tuple[str, int | None, int | None, str | None]:
    """The endpoint read, the minutes used, the included minutes and a reason class when unknown."""
    kind = "orgs" if owner.get("type") == "Organization" else "users"
    endpoint = f"/{kind}/{owner.get('login')}/settings/billing/actions"
    status, data = src.get("billing", endpoint)
    if status != 200:
        return endpoint, None, None, reason_of(status)
    used = data.get("total_minutes_used") if isinstance(data, dict) else None
    included = data.get("included_minutes") if isinstance(data, dict) else None
    if not all(isinstance(x, int | float) and not isinstance(x, bool) for x in (used, included)):
        return endpoint, None, None, "unreadable"
    return endpoint, math.ceil(used), int(included), None


def level_of(used: int | None, included: int | None, warn: int) -> str:
    """The highest level the used minutes have reached: `ok`, `50%`, `<warn>%` or `95%`;
    `unknown` when either figure is unknown (brief #370 answer 1)."""
    if used is None or not included:
        return "unknown"
    reached = [t for t in sorted({HALF, warn, TOP}) if used * 100 >= t * included]
    return f"{reached[-1]}%" if reached else "ok"


def runs_out(used: int | None, included: int | None, today: date) -> str | None:
    """The day the included minutes run out at this month's daily rate so far (the used minutes
    over the days of the month through today), `not this month`, or None when unknown."""
    if used is None or not included:
        return None
    if used >= included:
        return today.isoformat()
    if used <= 0:
        return NOT_THIS_MONTH
    rate = used / today.day
    day = today + timedelta(days=math.ceil((included - used) / rate))
    _, end = month_of(today)
    return day.isoformat() if day < end.date() else NOT_THIS_MONTH


def run_out_text(day: str | None) -> str:
    return f"runs out {NOT_THIS_MONTH}" if day == NOT_THIS_MONTH else f"runs out about {day}"


def line_of(
    used: int | None,
    included: int | None,
    included_reason: str | None,
    estimate_reason: str | None,
    warn: int,
    today: date,
) -> tuple[str, str]:
    """(level, the one line): what the doctor and `/agk:launch` print (brief #370)."""
    if used is None:
        return "unknown", (
            f"actions minutes: unknown (the token cannot read billing: {included_reason}, "
            f"nor the run history: {estimate_reason})"
        )
    if included is None:
        return "unknown", (
            f"actions minutes: {used} used this month (estimate from run history), included "
            f"minutes unknown ({included_reason}); level unknown"
        )
    level = level_of(used, included, warn)
    text = (
        f"actions minutes: {used} of {included} used ({used * 100 // included}%), level {level}; "
        f"{run_out_text(runs_out(used, included, today))}"
    )
    if level == f"{TOP}%":
        text += f"; at this level, see local mode in {LOCAL_MODE}"
    return level, text


def repo_of(src: Any) -> dict:
    status, repo = src.get("repo", "/repos/{repo}")
    if status != 200 or not isinstance(repo, dict):
        raise CheckError(
            f"the repository cannot be read ({reason_of(status)}; path class: repository)"
        )
    return repo


def outlook(src: Any, repo: dict, today: date, warn: int) -> tuple[str, str]:
    """(level, line) reading billing first and the run history only when billing cannot be read
    (the doctor's check and `--line`, brief #370 answer 2)."""
    _, used, included, reason = billing(src, repo.get("owner") or {})
    if used is not None:
        return line_of(used, included, None, None, warn, today)
    start, end = month_of(today)
    est = estimate(src, start, end, repo.get("private") is not False)
    return line_of(est.minutes, None, reason, est.reason, warn, today)


def read(src: Any, today: date, warn: int, repo_name: str | None) -> dict:
    repo = repo_of(src)
    start, end = month_of(today)
    endpoint, used, included, reason = billing(src, repo.get("owner") or {})
    rates = repo.get("private") is not False
    est = estimate(src, start, end, rates)
    merged = merged_pulls(src, start, end)
    if used is not None:
        used_entry = {"minutes": used, "source": "billing"}
    elif est.minutes is not None:
        used_entry = {"minutes": est.minutes, "source": "estimate"}
    else:
        used_entry = {"minutes": None, "source": None}
    per_pull = None
    if merged and est.minutes is not None:
        per_pull = round(est.minutes / merged, 1)
    warning = None
    known = [x for x in (used, est.minutes) if x is not None]
    top = max(known) if known else None
    if included and top is not None:
        if top * 100 >= warn * included:
            warning = (
                f"warning: {top} of {included} included minutes used ({top * 100 // included}%), "
                f"past minutes_warn ({warn}%); when they run out, see local mode in {GUIDE}"
            )
    return {
        "repository": repo_name or repo.get("full_name"),
        "private": repo.get("private"),
        "month": start.strftime("%Y-%m"),
        "through": today.isoformat(),
        "billing_endpoint": endpoint,
        "used": used_entry,
        "included": {"minutes": included, "reason": reason},
        "estimate": {
            "minutes": est.minutes,
            "reason": est.reason,
            "complete": est.complete,
            "runs": est.runs,
            "self_hosted_jobs": est.self_hosted_jobs,
            "running_jobs": est.running_jobs,
            "workflows": est.workflows,
            "multipliers": rates,
        },
        "merged_pulls": merged,
        "per_merged_pull": per_pull,
        "warn_percent": warn,
        "warning": warning,
        "level": level_of(top, included, warn),
        "runs_out": runs_out(top, included, today),
    }


def plural(n: int, word: str) -> str:
    return word if n == 1 else f"{word}s"


def render(data: dict) -> str:
    used, inc, est = data["used"], data["included"], data["estimate"]
    lines = [
        f"agk minutes: {data['repository']}, month {data['month']} (UTC, through {data['through']})"
    ]
    if used["source"] == "billing":
        lines.append(f"minutes used this month: {used['minutes']} (billing, the whole account)")
    elif used["source"] == "estimate":
        lines.append(f"minutes used this month: {used['minutes']} (estimate from run history)")
    else:
        lines.append("minutes used this month: unknown")
    if inc["minutes"] is not None:
        lines.append(f"included minutes: {inc['minutes']}")
    else:
        lines.append(f"included minutes: unknown (the token cannot read billing: {inc['reason']})")
    if est["minutes"] is None:
        lines.append(
            f"estimate from run history: unknown (the token cannot read the run history: "
            f"{est['reason']})"
        )
    else:
        bound = "" if est["complete"] else "at least "
        lines.append(
            f"estimate from run history: {bound}{est['minutes']} "
            "(this repository, each job rounded up to a whole minute)"
        )
        ordered = sorted(est["workflows"].items(), key=lambda kv: (-kv[1], kv[0]))
        lines += [f"  {name}: {minutes}" for name, minutes in ordered]
        if est["multipliers"]:
            lines.append(
                "  (runner rates applied: a Windows job counts 2x, a macOS job 10x) (verify)"
            )
        lines.append("  (re-runs of runs created before this month are not counted)")
        if not est["complete"]:
            lines.append(
                "  (a lower bound: the run list was capped, or a run's jobs could not be read)"
            )
        if est["self_hosted_jobs"]:
            n = est["self_hosted_jobs"]
            lines.append(f"  ({n} {plural(n, 'job')} on a self-hosted runner, not billed)")
        if est["running_jobs"]:
            n = est["running_jobs"]
            lines.append(f"  ({n} {plural(n, 'job')} still running, not counted yet)")
    if est["minutes"] is None or data["merged_pulls"] is None:
        lines.append("minutes per merged pull request: unknown")
    elif not data["merged_pulls"]:
        lines.append("minutes per merged pull request: - (no pull request merged this month)")
    else:
        bound = "" if est["complete"] else "at least "
        lines.append(
            f"minutes per merged pull request: {bound}{data['per_merged_pull']} "
            f"({data['merged_pulls']} merged this month)"
        )
    if data["private"] is False:
        lines.append(
            "note: a public repository's standard runners are not billed; the figures show its "
            "use, not its cost (verify)"
        )
    if data["level"] != "unknown":
        lines.append(f"level: {data['level']}; {run_out_text(data['runs_out'])}")
    if data["warning"]:
        lines.append(data["warning"])
    return "\n".join(lines) + "\n"


# --- command line -----------------------------------------------------------------------------


def parse_args(args: list[str]) -> dict | None:
    options: dict = {"today": None, "repo": None, "api": None, "json": False, "line": False}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--json", "--line"):
            options[arg[2:]] = True
            i += 1
        elif arg in ("--today", "--repo", "--api-dir") and i + 1 < len(args):
            value = args[i + 1]
            if arg == "--today":
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    return None
                try:
                    options["today"] = date.fromisoformat(value)
                except ValueError:
                    return None
            else:
                options[{"--repo": "repo", "--api-dir": "api"}[arg]] = value
            i += 2
        else:
            return None
    return None if options["json"] and options["line"] else options


def main(argv: list[str] | None = None) -> int:
    options = parse_args(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    warn = minutes_warn(repo_root())
    today = options["today"] or datetime.now(UTC).date()
    if options["api"]:
        src: Any = ApiDir(Path(options["api"]))
        name = options["repo"]
    else:
        name = options["repo"] or origin_repo()
        src = Gh(name)
    if options["line"]:
        level, text = outlook(src, repo_of(src), today, warn)
        print(text)
        past = level not in ("ok", "unknown") and int(level.rstrip("%")) >= warn
        return 3 if past else 0
    data = read(src, today, warn, name)
    if options["json"]:
        print(json.dumps(data, indent=2))
    else:
        sys.stdout.write(render(data))
    return 3 if data["warning"] else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
