"""The weekly scorecard: one table of this repository's level numbers (SPEC-0047 rules 1 to 3,
brief #713, build (b), ADR-0311).

    python3 scripts/agk/scorecard.py [findings | issues] [--today YYYY-MM-DD] [--repo OWNER/REPO]
        [--api-dir DIR] [--previous FILE]

The week is the seven days before the run date (`--today`, default `date -u`). Each row is a
level metric of rule 1, its value and its line (the `[scorecard]` table of agk.toml or the kit
default, `-` for none); higher is worse. It reads the readers that exist (`metrics.py`,
`minutes.py`, `full_run.py`, `rules.py`) over the repository's own pull requests,
comments, issues and CI runs, with `gh api --method GET` only, or saved responses (`--api-dir`:
`runs-week`, `run-jobs-<id>`, `repo`, `pulls`, `comments-<n>`, `issues-open`, `issues-closed`).
A value whose inputs cannot be read, or that has nothing to count, is `unknown`, never 0. It
prints and writes nothing; no check, `make governance` or `prepush.py` step runs it (rule 2).
The freshness rows (rule 8, brief #719, build (c)) read the default branch with `git` and one GET
of each upstream's releases (`releases-<owner>-<name>`, `kit-releases`).
`findings` (rules 4 and 7, brief #723, build (d)) also reads the earlier weeks from the previous
audit body (`--previous FILE`), prints the section of the last `trend_weeks` weeks and the
findings, and writes nothing. `goals_not_met` and the `acceptance:` line (SPEC-0051 rule 9, brief
#903) read the records of the default branch with `check_acceptance.py`'s reader, from a temporary
copy of that branch, or the checkout when it has no default branch. `issues` (rule 5) then reads
the open `agk-scorecard` issues (`issues-scorecard`) and opens, comments on or closes one issue per
metric with `gh api`; the weekly wiring is build (e).
"""

from __future__ import annotations

import io
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tarfile
import tempfile
import tomllib
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_acceptance
import metrics
from common import CheckError, git, installed_version, load_config, repo_root, run
from doctor import kit_repo, version_numbers
from drift_audit import d4_documents, d4_register
from full_run import FULL
from guard import scan_text
from minutes import estimate
from reviewers import verdict_authors

from config import scorecard_settings

NAME = "scorecard"
USAGE = (
    "usage: scorecard.py [findings | issues] [--today YYYY-MM-DD] [--repo OWNER/REPO] "
    "[--api-dir DIR] [--previous FILE]"
)
COMMANDS = ("findings", "issues")
LABEL = "agk-scorecard"  # never agk-brief or found-bug (Q-S0047-4)
WEEKS_START, WEEKS_END = "<!-- scorecard weeks -->", "<!-- /scorecard weeks -->"
NUMBER = re.compile(r"^\d+(?:\.\d+)?$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UNKNOWN = metrics.UNKNOWN
NOT_APPLICABLE = "not applicable"
RED_TITLE = "The default branch is red"  # session.RED_TITLE (SPEC-0032 rule 7)
FAILURE_LINE = "Failure-signature:"  # SPEC-0046 rule 3
OLD_DAYS = 7
LEVEL = (
    "full_check_minutes prepush_seconds red_hours flaky_rate fix_list_rate lead_time_hours "
    "restore_hours ci_minutes_per_merge rule_words rule_lines old_failure_issues"
).split()
FRESH = (
    "verify_marks verify_oldest_days residuals_past_due pins_behind pins_oldest_gap_days "
    "kit_releases_behind stale_guides"
).split()
GOALS = "goals_not_met"  # SPEC-0051 rule 9, by amendment 156
METRICS = [*LEVEL, *FRESH, GOALS]
ACCEPTANCE_UNKNOWN = "acceptance: unknown"
MARK = re.compile(r"\(verify[):]")
APPROVED = re.compile(r"^- Status: Approved\s*$", re.MULTILINE)
PIN = re.compile(
    r"^\s*(?:-\s+)?uses:\s*([\w.-]+/[\w.-]+)(?:/\S*)?@[0-9a-f]{40}\s+#\s*(\S+)", re.MULTILINE
)
EXACT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*==(?!=)")
SPAN = re.compile(r"`([^`\n]+)`")
NAMED = re.compile(r"\b(?:scripts/agk/)?([a-z0-9_]+\.py)\b")
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


# --- the freshness metrics of rules 1 and 8 ---------------------------------------------------


def git_out(root: Path, *args: str) -> str | None:
    """`common.git`'s output, or None when the command fails."""
    try:
        return git(root, *args)
    except CheckError:
        return None


def default_ref(root: Path, branch: str) -> str | None:
    """`origin/<branch>`, else `<branch>`: the default branch as this checkout knows it."""
    for ref in (f"origin/{branch}", branch):
        if git_out(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"):
            return ref
    return None


def shallow(root: Path) -> bool:
    """A shallow history dates every older line at its cut, so it dates nothing (unknown)."""
    return (git_out(root, "rev-parse", "--is-shallow-repository") or "true").strip() != "false"


def tracked(root: Path, ref: str, folder: str) -> list[str]:
    listing = git_out(root, "ls-tree", "-r", "--name-only", ref, "--", folder) or ""
    return sorted(p for p in listing.splitlines() if p.endswith(".md"))


def verify_metrics(root: Path, ref: str | None, today: date) -> tuple[str, str]:
    """verify_marks and verify_oldest_days: the marks of Approved specs, each dated by the
    author time `git blame` of the default branch gives its line (Q-S0047-18)."""
    if ref is None:
        return UNKNOWN, UNKNOWN
    marks, oldest = 0, None
    for rel in tracked(root, ref, "docs/specs"):
        text = git_out(root, "show", f"{ref}:{rel}")
        if text is None:
            return UNKNOWN, UNKNOWN
        if not APPROVED.search(text) or not MARK.search(text):
            continue
        blame = git_out(root, "blame", "--line-porcelain", ref, "--", rel)
        if blame is None:
            return UNKNOWN, UNKNOWN
        when = None
        for line in blame.splitlines():
            if line.startswith("author-time "):
                when = int(line.split()[1])
            elif line.startswith("\t") and (found := len(MARK.findall(line))):
                marks += found
                if when is not None and (oldest is None or when < oldest):
                    oldest = when
    if not marks:
        return "0", UNKNOWN  # no mark: nothing has an age
    if oldest is None or shallow(root):
        return str(marks), UNKNOWN
    return str(marks), str((today - datetime.fromtimestamp(oldest, UTC).date()).days)


def residuals_past_due(root: Path, today: date) -> str:
    """The overdue residual bullets and register lines, by the drift audit's D4."""
    found = d4_documents(root, today)[0] + d4_register(root, today)
    return str(sum(1 for f in found if "overdue since" in f.sentence))


def action_pins(root: Path) -> list[tuple[str, str]]:
    """(owner/name, release tag) of each SHA-pinned `uses:` line of the workflows, once each."""
    pins = set()
    for path in sorted((root / ".github/workflows").glob("*.yml")):
        pins |= set(PIN.findall(path.read_text(encoding="utf-8")))
    return sorted(pins)


def python_pins(root: Path) -> list[str]:
    """The packages that `pyproject.toml` pins with `==` (Q-S0047-11)."""
    try:
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    found_project = data.get("project")
    project: dict = found_project if isinstance(found_project, dict) else {}
    groups = [project.get("dependencies")]
    for table in (project.get("optional-dependencies"), data.get("dependency-groups")):
        groups += list(table.values()) if isinstance(table, dict) else []
    found = {
        m.group(1)
        for group in groups
        if isinstance(group, list)
        for item in group
        if isinstance(item, str) and (m := EXACT.match(item))
    }
    return sorted(found)


def published(item: dict) -> date | None:
    moment = metrics.stamp(item.get("published_at"))
    return moment.date() if moment else None


def releases(src: Any, repo: str, name: str) -> list[dict] | None:
    """One GET of a repository's release list; None when it cannot be read."""
    found = listed(src.get(name, f"repos/{repo}/releases?per_page=100"))
    if found is None:
        return None
    return [r for r in found if not r.get("draft")]


def pin_gap(found: list[dict] | None, tag: str) -> tuple[bool, int] | None:
    """Whether the pinned release is behind the newest one (on the tag) and by how many days
    (0 on the same day), or None (unknown)."""
    final = [r for r in found or [] if not r.get("prerelease") and published(r)]
    pinned = [r for r in found or [] if r.get("tag_name") == tag and published(r)]
    if not final or not pinned:
        return None
    first = datetime.min.replace(tzinfo=UTC)
    newest = max(final, key=lambda r: metrics.stamp(r.get("published_at")) or first)
    if newest.get("tag_name") == tag:
        return False, 0
    gap = ((published(newest) or date.min) - (published(pinned[0]) or date.min)).days
    return True, max(gap, 0)


def pin_metrics(root: Path, src: Any) -> tuple[str, str, int]:
    """pins_behind, pins_oldest_gap_days and the pins whose upstream cannot be read. A Python
    package's index is a source the spec marks `(verify)`: it is not read, so its pin is unknown
    (Q-719-1)."""
    upstream: dict[str, list[dict] | None] = {}
    gaps = []
    for repo, tag in action_pins(root):
        if repo not in upstream:
            upstream[repo] = releases(src, repo, "releases-" + repo.replace("/", "-"))
        gaps.append(pin_gap(upstream[repo], tag))
    known = [g for g in gaps if g is not None]
    unknown = len(gaps) - len(known) + len(python_pins(root))
    if not known:
        return UNKNOWN, UNKNOWN, unknown
    return str(sum(1 for behind, _ in known if behind)), str(max(d for _, d in known)), unknown


def kit_releases_behind(root: Path, src: Any, installed: object) -> str:
    """The kit releases newer than the installed `version`; unknown when the kit's repository
    cannot be resolved from the installed copy (Q-S0047-10)."""
    repo, _ = kit_repo(root)
    mine = version_numbers(installed)
    found = releases(src, repo, "kit-releases") if repo else None
    if mine is None or found is None:
        return UNKNOWN

    def padded(numbers: tuple[int, ...]) -> tuple[int, ...]:
        return numbers + (0,) * (8 - len(numbers))

    newer = [
        r
        for r in found
        if not r.get("prerelease")
        and (v := version_numbers(r.get("tag_name"))) is not None
        and padded(v) > padded(mine)
    ]
    return str(len(newer))


def stale_guides(root: Path, ref: str | None) -> str:
    """The guides whose last change on the default branch is older than a script they name in
    backticks (Q-S0047-19)."""
    if ref is None or shallow(root):
        return UNKNOWN
    scripts = {
        Path(p).name
        for p in (git_out(root, "ls-tree", "--name-only", ref, "scripts/agk/") or "").split()
    }
    seen: dict[str, int | None] = {}

    def changed(rel: str) -> int | None:
        if rel not in seen:
            out = (git_out(root, "log", "-1", "--format=%at", ref, "--", rel) or "").strip()
            seen[rel] = int(out) if out.isdigit() else None
        return seen[rel]

    stale = 0
    for rel in tracked(root, ref, "docs/guides"):
        text = git_out(root, "show", f"{ref}:{rel}")
        guide = changed(rel)
        if text is None or guide is None:
            return UNKNOWN
        named = {n for span in SPAN.findall(text) for n in NAMED.findall(span) if n in scripts}
        times = [changed(f"scripts/agk/{n}") for n in sorted(named)]
        if any(t is None for t in times):
            return UNKNOWN
        stale += any((t or 0) > guide for t in times)
    return str(stale)


def freshness(root: Path, src: Any, today: date, config: dict) -> dict:
    ref = default_ref(root, config["default_branch"])
    values: dict[str, Any] = {}
    values["verify_marks"], values["verify_oldest_days"] = verify_metrics(root, ref, today)
    values["residuals_past_due"] = residuals_past_due(root, today)
    behind, gap, values["pins_unknown"] = pin_metrics(root, src)
    values["pins_behind"], values["pins_oldest_gap_days"] = behind, gap
    values["kit_releases_behind"] = kit_releases_behind(root, src, installed_version(root))
    values["stale_guides"] = stale_guides(root, ref)
    return values


# --- the goals of accepted products (SPEC-0051 rule 9) ----------------------------------------


def goal_counts(tree: Path) -> tuple[str, str]:
    """`goals_not_met` and the information line of the records of TREE: a record counts only in
    state `accepted` or `accepted with <n> not met` of rule 7, so a stale or proposed one counts in
    neither number."""
    paths = check_acceptance.records(tree)
    if not paths:
        return "0", "acceptance: no record"
    total, unmet, counted = 0, 0, 0
    for path in paths:
        if not check_acceptance.inspect(tree, path)[1].startswith("accepted"):
            continue
        lines = path.read_text(encoding="utf-8").split("\n")
        goals = check_acceptance.form_of(path.name, path.stem, lines)[1]
        counted += 1
        total += len(goals)
        unmet += sum(1 for _, _, evidence in goals if evidence == check_acceptance.NOT_MET)
    return str(unmet), f"acceptance: {total - unmet} of {total} goals met in {counted} records"


def acceptance(root: Path, ref: str | None) -> tuple[str, str]:
    """`goal_counts` of the default branch REF, whose whole tree is copied because a record's
    evidence may be any file; of the checkout when REF is None; `unknown` when REF is unreadable."""
    if ref is None:
        return goal_counts(root)
    listing = git_out(root, "ls-tree", "--name-only", ref, f"{check_acceptance.FOLDER}/")
    if listing is None:
        return UNKNOWN, ACCEPTANCE_UNKNOWN
    if not listing.strip():
        return "0", "acceptance: no record"
    tree = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "archive", ref], cwd=root, capture_output=True
    )
    if tree.returncode != 0:
        return UNKNOWN, ACCEPTANCE_UNKNOWN
    with tempfile.TemporaryDirectory() as folder:
        try:
            with tarfile.open(fileobj=io.BytesIO(tree.stdout)) as archive:
                archive.extractall(folder, filter="data")
        except (OSError, tarfile.TarError):
            return UNKNOWN, ACCEPTANCE_UNKNOWN
        return goal_counts(Path(folder))


def scorecard(root: Path, src: Any, today: date) -> tuple[list[tuple[str, str, str]], list[str]]:
    """(metric, value, line) for every metric, in rule 1's order, and the notes under the table."""
    settings = scorecard_settings(root)
    config = load_config(root)
    end = metrics.start_of(today)
    start = end - timedelta(days=7)
    first, last = (start - timedelta(days=1)).date(), (end - timedelta(days=1)).date()
    runs = src.get("runs-week", f"repos/{{repo}}/actions/runs?created={first}..{last}")
    values = run_metrics(src, runs, config["default_branch"], start, end)
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
    values.update(freshness(root, src, today, config))
    values[GOALS], information = acceptance(root, default_ref(root, config["default_branch"]))
    notes = [f"pins unknown: {values['pins_unknown']}", information]
    shown = [(m, values[m], "-" if lines[m] is None else f"{lines[m]:g}") for m in METRICS]
    return shown, notes


def render(rows: list[tuple[str, str, str]], today: date, notes: list[str] | None = None) -> str:
    end = metrics.start_of(today)
    start, last = (end - timedelta(days=7)).date(), (end - timedelta(days=1)).date()
    out = [
        f"scorecard: the week {start} to {last} (higher is worse)",
        "",
        "| metric | value | line |",
    ]
    out.append("| --- | --- | --- |")
    out += [f"| {m} | {v} | {line} |" for m, v, line in rows]
    out += ["", *notes] if notes else []
    return "\n".join(out)


# --- findings, trends and the issue writer (rules 4, 5 and 7) --------------------------------


def number(value: str) -> Decimal | None:
    return Decimal(value) if NUMBER.match(value) else None


def judge(values: list[str], line: Decimal | None, trend_weeks: int = 4) -> str | None:
    """The finding of the newest of VALUES (oldest first): `level` above the line, `trend` when
    the last three weeks inside the window are known and each is higher than the one before."""
    now = number(values[-1]) if values else None
    if now is None:
        return None
    if line is not None and now > line:
        return "level"
    last = [number(v) for v in values[-3:]] if trend_weeks >= 3 and len(values) >= 3 else []
    if len(last) == 3 and all(v is not None for v in last):
        a, b, c = (v or Decimal(0) for v in last)
        if a < b < c:
            return "trend"
    return None


def closable(
    values: list[str], line: Decimal | None, close_weeks: int, trend_weeks: int = 4
) -> bool:
    """True when the last `close_weeks` known weeks were neither finding; an unknown week counts as
    neither inside nor outside and resets nothing (Q-S0047-16)."""
    quiet = []
    for i in range(len(values) - 1, -1, -1):
        if number(values[i]) is None:
            continue
        quiet.append(judge(values[: i + 1], line, trend_weeks) is None)
        if len(quiet) == close_weeks:
            return all(quiet)
    return False


def choose_issue(open_numbers: list[int], finding: bool, close: bool) -> str:
    """`create`, `comment N`, `close N` (N the lowest open one) or `none`."""
    if finding:
        return f"comment {min(open_numbers)}" if open_numbers else "create"
    return f"close {min(open_numbers)}" if open_numbers and close else "none"


def week_days(today: date, weeks: int) -> list[date]:
    return [today - timedelta(days=7 * k) for k in range(weeks - 1, -1, -1)]


def history(previous: str | None, today: date, weeks: int) -> dict[str, list[str]]:
    """Each metric's values of the `weeks - 1` weeks before TODAY, oldest first, read from the
    previous body's section; a missing week or a cell that is not a number is unknown."""
    cells: dict[str, dict[str, str]] = {}
    text = previous or ""
    if WEEKS_START in text and WEEKS_END in text:
        table = text.split(WEEKS_START, 1)[1].split(WEEKS_END, 1)[0].strip().splitlines()
        head = [c.strip() for c in table[0].strip().strip("|").split("|")] if table else []
        for row in table[2:]:
            got = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(got) == len(head) and got[0] in METRICS:
                cells[got[0]] = {
                    d: v for d, v in zip(head[2:], got[2:], strict=True) if DAY.match(d)
                }
    earlier = [str(d) for d in week_days(today, weeks)[:-1]]
    out = {}
    for metric in METRICS:
        found = cells.get(metric, {})
        out[metric] = [
            v if NUMBER.match(v := found.get(d, "")) or v == NOT_APPLICABLE else UNKNOWN
            for d in earlier
        ]
    return out


def weeks_section(today: date, lines: dict[str, str], table: dict[str, list[str]]) -> str:
    """The audit body's section of the last weeks (rule 7), one column per run date."""
    days = week_days(today, len(next(iter(table.values()))) if table else 1)
    out = [WEEKS_START, "| metric | line | " + " | ".join(map(str, days)) + " |"]
    out.append("| --- | --- | " + " | ".join("---" for _ in days) + " |")
    out += [f"| {m} | {lines.get(m, '-')} | " + " | ".join(v) + " |" for m, v in table.items()]
    return "\n".join([*out, WEEKS_END])


def guarded(text: str) -> tuple[str | None, str]:
    """TEXT, or None and `withheld: <kind> <count>` when the guard scan finds anything."""
    found = scan_text(text)
    if not found:
        return text, ""
    kinds: dict[str, int] = {}
    for f in found:
        kinds[f.kind] = kinds.get(f.kind, 0) + 1
    return None, "withheld: " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items()))


def issue_text(metric: str, kind: str, values: list[str], line: str, today: date) -> str:
    first = today - timedelta(days=7 * (len(values) - 1))
    return (
        f"scorecard: {metric}\nkind: {kind}\nvalue: {values[-1]}\n"
        f"line: {'none (trend only)' if line == '-' else line} (setting: scorecard.{metric})\n"
        f"weeks: {', '.join(values)} ({first} to {today})\n"
    )


def gh_write(method: str, endpoint: str, *fields: str) -> None:
    args = [a for f in fields for a in ("-f", f)]
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["gh", "api", "--method", method, endpoint, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise CheckError(f"rule 5: the {LABEL} issue cannot be written")


def ensure_label(repo: str) -> None:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["gh", "api", "--method", "GET", f"repos/{repo}/labels/{LABEL}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        gh_write("POST", f"repos/{repo}/labels", f"name={LABEL}", "color=c5def5")


def findings(root: Path, src: Any, today: date, previous: str | None) -> tuple[str, list, dict]:
    """The section, the findings (metric, kind, values, line) and each metric's closable flag."""
    settings = scorecard_settings(root)
    weeks, close_weeks = settings["trend_weeks"], settings["close_weeks"]
    rows, notes = scorecard(root, src, today)
    earlier = history(previous, today, weeks)
    table = {m: [*earlier[m], v] for m, v, _ in rows}
    lines = {m: line for m, _, line in rows}
    found, close = [], {}
    for metric, values in table.items():
        line = number(lines[metric])
        kind = judge(values, line, weeks)
        if kind:
            found.append((metric, kind, values, lines[metric]))
        close[metric] = closable(values, line, close_weeks, weeks)
    return f"{weeks_section(today, lines, table)}\n\n{notes[-1]}", found, close


def write_issues(src: Any, repo: str, today: date, found: list, close: dict) -> list[str]:
    """Open, comment on or close one `agk-scorecard` issue per metric (rule 5)."""
    listing = listed(
        src.get("issues-scorecard", f"repos/{{repo}}/issues?state=open&labels={LABEL}")
    )
    if listing is None:
        raise CheckError(f"rule 5: the open {LABEL} issues cannot be read")
    numbers: dict[str, list[int]] = {}
    for item in listing:
        title, n = str(item.get("title") or ""), item.get("number")
        if "pull_request" not in item and title.startswith("scorecard: ") and isinstance(n, int):
            numbers.setdefault(title.removeprefix("scorecard: "), []).append(n)
    by_metric = {f[0]: f for f in found}
    done = []
    for metric in METRICS:
        action = choose_issue(
            numbers.get(metric, []), metric in by_metric, close.get(metric, False)
        )
        if action == "none":
            continue
        verb, _, n = action.partition(" ")
        if verb == "close":
            gh_write("PATCH", f"repos/{repo}/issues/{n}", "state=closed", "state_reason=completed")
            done.append(f"issue: close {n} {metric}")
            continue
        _, kind, values, line = by_metric[metric]
        text, note = guarded(issue_text(metric, kind, values, line, today))
        if text is None:
            done.append(note)
        elif verb == "create":
            ensure_label(repo)
            title = f"title=scorecard: {metric}"
            gh_write("POST", f"repos/{repo}/issues", title, f"body={text}", f"labels[]={LABEL}")
            done.append(f"issue: create {metric}")
        else:
            gh_write("POST", f"repos/{repo}/issues/{n}/comments", f"body={text}")
            done.append(f"issue: comment {n} {metric}")
    return done


def parse_args(args: list[str]) -> dict | None:
    opts: dict[str, str] = {}
    if args and args[0] in COMMANDS:
        opts["command"] = args.pop(0)
    flags = ("--today", "--repo", "--api-dir") + (("--previous",) if "command" in opts else ())
    while args:
        flag = args.pop(0)
        if flag not in flags or not args or flag[2:] in opts:
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
    live = "api-dir" not in opts or opts.get("command") == "issues"
    repo = opts.get("repo") or (metrics.origin_repo() if live else "")
    src: Any = metrics.ApiDir(Path(opts["api-dir"])) if "api-dir" in opts else Live(repo)
    if "command" not in opts:
        rows, notes = scorecard(root, src, today)
        print(render(rows, today, notes))
        return 0
    previous = None
    if "previous" in opts:
        try:
            previous = Path(opts["previous"]).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            previous = None  # every earlier week is unknown (rule 7)
    section, found, close = findings(root, src, today, previous)
    out = [section, "", f"findings: {len(found)}"]
    out += [f"finding: {m} {k} value {v[-1]} line {line}" for m, k, v, line in found]
    if opts["command"] == "issues":
        out += write_issues(src, repo, today, found, close)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
