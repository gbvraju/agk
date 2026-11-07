"""The weekly scorecard: one table of this repository's level numbers (SPEC-0047 rules 1 to 3,
brief #713, build (b), ADR-0311).

    python3 scripts/agk/scorecard.py [--today YYYY-MM-DD] [--repo OWNER/REPO] [--api-dir DIR]

The week is the seven days before the run date (`--today`, default `date -u`). Each row is a
level metric of rule 1, its value and its line (the `[scorecard]` table of agk.toml or the kit
default, `-` for none); higher is worse. It reads the readers that exist (`metrics.py`,
`minutes.py`, `full_run.py`, `rules.py`) over the repository's own pull requests,
comments, issues and CI runs, with `gh api --method GET` only, or saved responses (`--api-dir`:
`runs-week`, `run-jobs-<id>`, `repo`, `pulls`, `comments-<n>`, `issues-open`, `issues-closed`).
A value whose inputs cannot be read, or that has nothing to count, is `unknown`, never 0. It
prints and writes nothing; no check, `make governance` or `prepush.py` step runs it (rule 2).
The freshness metrics, findings, trends and issues are builds (c) to (e).
"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import metrics
from common import CheckError, load_config, repo_root, run
from full_run import FULL
from minutes import estimate
from reviewers import verdict_authors

from config import scorecard_settings

NAME = "scorecard"
USAGE = "usage: scorecard.py [--today YYYY-MM-DD] [--repo OWNER/REPO] [--api-dir DIR]"
UNKNOWN = metrics.UNKNOWN
NOT_APPLICABLE = "not applicable"
RED_TITLE = "The default branch is red"  # session.RED_TITLE (SPEC-0032 rule 7)
FAILURE_LINE = "Failure-signature:"  # SPEC-0046 rule 3
OLD_DAYS = 7
LEVEL = (
    "full_check_minutes prepush_seconds red_hours flaky_rate fix_list_rate lead_time_hours "
    "restore_hours ci_minutes_per_merge rule_words rule_lines old_failure_issues"
).split()
RULES_READER = Path(__file__).resolve().parent / "rules.py"  # kit-only (Q-S0047-14)


class Live(metrics.Gh):
    """`metrics.Gh`, paging the issue lists as well."""

    def read(self, name: str, endpoint: str, until: Any = None) -> Any:
        if name.startswith("issues-"):
            return self.pages(endpoint.replace("{repo}", self.repo), until)
        return super().read(name, endpoint, until)


class Paired:
    """`minutes.estimate` reads (status, data); this answers it from the week's runs and the
    same job lists `metrics.jobs_of` reads."""

    def __init__(self, src: Any, runs: Any) -> None:
        self.src, self.runs = src, runs

    def get(self, name: str, endpoint: str, until: Any = None) -> tuple[int, Any]:
        if name == "runs":
            data = self.runs
        else:
            rid = name.removeprefix("jobs-")
            data = self.src.get(
                f"run-jobs-{rid}", f"repos/{{repo}}/actions/runs/{rid}/jobs?filter=all"
            )
        return (200, data) if isinstance(data, dict) else (404, None)


def tenth(value: float | Decimal) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def middle(values: list[Any]) -> str:
    """The median of numbers, as one decimal; unknown when one is unknown or there are none."""
    if not values or any(v == UNKNOWN or v is None for v in values):
        return UNKNOWN
    return tenth(median(Decimal(str(v)) for v in values))


def inside(item: dict, key: str, start: datetime, end: datetime) -> bool:
    moment = metrics.stamp(item.get(key))
    return moment is not None and start <= moment < end


def listed(data: Any) -> list[dict] | None:
    if not isinstance(data, list) or not all(isinstance(i, dict) for i in data):
        return None
    return data


# --- the metrics of rule 1 --------------------------------------------------------------------


def run_metrics(src: Any, runs: Any, branch: str, start: datetime, end: datetime) -> dict:
    """full_check_minutes, prepush_seconds, flaky_rate (Q-S0047-12) and ci_minutes_per_merge's
    minutes, from one list of the week's runs."""
    values: dict[str, Any] = dict.fromkeys(
        ("full_check_minutes", "prepush_seconds", "flaky_rate"), UNKNOWN
    )
    found = listed(runs.get("workflow_runs") if isinstance(runs, dict) else None)
    if found is None:
        return {**values, "minutes": None}
    week = [r for r in found if inside(r, "created_at", start, end)]
    gov = [r for r in week if metrics.is_governance(r) and r.get("conclusion")]
    full = [
        r
        for r in gov
        if r.get("display_title") == FULL
        and r.get("event") == "push"
        and r.get("head_branch") == branch
    ]
    spans = [
        {"started_at": r.get("run_started_at"), "completed_at": r.get("updated_at")} for r in full
    ]
    taken = [metrics.seconds_of(span) for span in spans]  # the run's span (verify)
    known = [t for t in taken if t is not None]
    if full and len(known) == len(taken):
        values["full_check_minutes"] = tenth(median(Decimal(t) / 60 for t in known))
    seconds = [metrics.project_test_seconds(src, [r]) for r in full]
    if seconds and UNKNOWN not in seconds:
        values["prepush_seconds"] = str(
            Decimal(median(int(s) for s in seconds)).quantize(1, ROUND_HALF_UP)
        )
    if gov:
        flaky = [r for r in gov if (r.get("run_attempt") or 1) > 1 and r["conclusion"] == "success"]
        values["flaky_rate"] = tenth(Decimal(100 * len(flaky)) / len(gov))
    repo = src.get("repo", "repos/{repo}")
    rates = not (isinstance(repo, dict) and repo.get("private") is False)
    est = estimate(Paired(src, runs), start, end, rates)
    values["minutes"] = est.minutes if est.complete else None
    return values


def pull_metrics(src: Any, root: Path, start: datetime, end: datetime) -> tuple[dict, int | None]:
    """fix_list_rate and lead_time_hours of the pull requests merged in the week."""
    values = dict.fromkeys(("fix_list_rate", "lead_time_hours"), UNKNOWN)

    def older(chunk: list[dict]) -> bool:
        last = metrics.stamp(chunk[-1].get("updated_at")) if chunk else None
        return last is not None and last < start

    pulls = listed(
        src.get("pulls", "repos/{repo}/pulls?state=closed&sort=updated&direction=desc", older)
    )
    if pulls is None:
        return values, None
    merged = [p for p in pulls if inside(p, "merged_at", start, end)]
    if not merged:
        return values, 0
    hours = [metrics.hours_between(p.get("created_at"), p.get("merged_at")) for p in merged]
    values["lead_time_hours"] = middle(hours)
    authors = verdict_authors(root)
    fixes = 0
    for pull in merged:
        n = pull.get("number")
        found = metrics.verdicts(
            listed(src.get(f"comments-{n}", f"repos/{{repo}}/issues/{n}/comments")), authors
        )
        if found is None:
            return values, len(merged)
        fixes += sum(1 for kind, _ in found if kind == "fix")
    values["fix_list_rate"] = tenth(Decimal(100 * fixes) / len(merged))
    return values, len(merged)


def issue_metrics(src: Any, start: datetime, end: datetime) -> dict:
    """red_hours and restore_hours (Q-S0047-13), and old_failure_issues."""
    values = dict.fromkeys(("red_hours", "restore_hours", "old_failure_issues"), UNKNOWN)
    since = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    opened = listed(src.get("issues-open", "repos/{repo}/issues?state=open"))
    closed = listed(src.get("issues-closed", f"repos/{{repo}}/issues?state=closed&since={since}"))
    if opened is not None:
        old = end - timedelta(days=OLD_DAYS)
        values["old_failure_issues"] = str(
            sum(
                1
                for i in opened
                if "pull_request" not in i
                and "found-bug"
                in [lab.get("name") for lab in i.get("labels") or [] if isinstance(lab, dict)]
                and any(
                    line.startswith(FAILURE_LINE) for line in str(i.get("body") or "").splitlines()
                )
                and (metrics.stamp(i.get("created_at")) or end) < old
            )
        )
    if opened is None or closed is None:
        return values
    red = [i for i in opened + closed if i.get("title") == RED_TITLE and "pull_request" not in i]
    total = Decimal(0)
    for i in red:
        a, b = metrics.stamp(i.get("created_at")), metrics.stamp(i.get("closed_at")) or end
        if a is None:
            return values
        lo, hi = max(a, start), min(b, end)
        total += Decimal(max((hi - lo).total_seconds(), 0)) / 3600
    values["red_hours"] = tenth(total)
    restored = [i for i in red if inside(i, "closed_at", start, end)]
    values["restore_hours"] = middle(
        [metrics.hours_between(i.get("created_at"), i.get("closed_at")) for i in restored]
    )
    return values


def rule_counts(root: Path, available: bool) -> tuple[str, str]:
    """rule_words and rule_lines, the totals of `rules.py budget` (Q-S0047-14)."""
    if not available:
        return NOT_APPLICABLE, NOT_APPLICABLE
    import rules  # noqa: PLC0415 - kit-only, never installed

    files = [root / rel for rel in rules.instruction_files(root) if (root / rel).is_file()]
    if not files:
        return UNKNOWN, UNKNOWN
    counted = [rules.counts(p.read_text(encoding="utf-8")) for p in files]
    return str(sum(w for w, _ in counted)), str(sum(r for _, r in counted))


def budget_lines(root: Path) -> tuple[int | None, int | None]:
    """The totals of `config/rule-budget.txt`, the default lines of the rule counts (rule 3)."""
    if not RULES_READER.is_file() or not (root / "config/rule-budget.txt").is_file():
        return None, None
    import rules  # noqa: PLC0415 - kit-only, never installed

    baseline, problems = rules.read_baseline(root)
    if problems or not baseline:
        return None, None
    return sum(w for w, _ in baseline.values()), sum(r for _, r in baseline.values())


def scorecard(root: Path, src: Any, today: date) -> list[tuple[str, str, str]]:
    """(metric, value, line) for every level metric, in rule 1's order."""
    settings = scorecard_settings(root)
    end = metrics.start_of(today)
    start = end - timedelta(days=7)
    first, last = (start - timedelta(days=1)).date(), (end - timedelta(days=1)).date()
    runs = src.get("runs-week", f"repos/{{repo}}/actions/runs?created={first}..{last}")
    values = run_metrics(src, runs, load_config(root)["default_branch"], start, end)
    pulls, merged = pull_metrics(src, root, start, end)
    values.update(pulls)
    values.update(issue_metrics(src, start, end))
    ci = values.pop("minutes")
    values["ci_minutes_per_merge"] = (
        tenth(Decimal(ci) / merged) if ci is not None and merged else UNKNOWN
    )
    values["rule_words"], values["rule_lines"] = rule_counts(root, RULES_READER.is_file())
    lines = dict(settings["lines"])
    budget = budget_lines(root)
    for key, total in zip(("rule_words", "rule_lines"), budget, strict=True):
        lines[key] = lines[key] if lines[key] is not None else total
    return [(m, values[m], "-" if lines[m] is None else f"{lines[m]:g}") for m in LEVEL]


def render(rows: list[tuple[str, str, str]], today: date) -> str:
    end = metrics.start_of(today)
    start, last = (end - timedelta(days=7)).date(), (end - timedelta(days=1)).date()
    out = [
        f"scorecard: the week {start} to {last} (higher is worse)",
        "",
        "| metric | value | line |",
    ]
    out.append("| --- | --- | --- |")
    out += [f"| {m} | {v} | {line} |" for m, v, line in rows]
    return "\n".join(out)


def parse_args(args: list[str]) -> dict | None:
    opts: dict[str, str] = {}
    while args:
        flag = args.pop(0)
        if flag not in ("--today", "--repo", "--api-dir") or not args or flag[2:] in opts:
            return None
        opts[flag[2:]] = args.pop(0)
    return opts


def main(argv: list[str] | None = None) -> int:
    opts = parse_args(list(sys.argv[1:] if argv is None else argv))
    if opts is None:
        print(USAGE)
        return 2
    try:
        today = date.fromisoformat(opts["today"]) if "today" in opts else datetime.now(UTC).date()
    except ValueError:
        raise CheckError("--today is not a date (setting: --today)") from None
    root = repo_root()
    if "api-dir" in opts:
        src: Any = metrics.ApiDir(Path(opts["api-dir"]))
    else:
        src = Live(opts.get("repo") or metrics.origin_repo())
    print(render(scorecard(root, src, today), today))
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
