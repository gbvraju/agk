"""Which checks and rules of the kit ever refused something (brief #328, ADR-0188).

    python3 core_audit.py [--since YYYY-MM-DD] [--json] [--write] [--today YYYY-MM-DD]
        [--repo OWNER/REPO | --api-dir DIR] [--authors LOGIN,LOGIN]

A read-only report, evidence for a smaller kit core (brief #278), never a decision. It lists:

- each governance check (a named step of `.github/workflows/governance.yml` that runs a kit script,
  `agk.mk` or the secret scanner) with the number of pull requests whose `governance` check run
  failed on that step, read from the steps of the run's job; a failed step that is no check of the
  current workflow (renamed or removed) is listed apart;
- each session rule (`config/session-rules.md`) and each spec rule (the numbered rules of the
  `## Rules` section of `docs/specs/NNNN-*.md`) with the number of `Verdict:` comments by a listed
  author (`--authors`, default the `verdict_authors` of `config/reviewers.yaml`) that cite it, as
  `session rule N`, `session rules N and M`, `rule N of the session rules` or `SPEC-NNNN rule N`;
- the checks and rules with zero refusals in the period, and the totals of ADRs, specs,
  requirements and scripts.

The period is every pull request opened on or after `--since` (default: the whole history). A page
that cannot be read (a pull request's commits, check runs, job or comments; a failed run whose job
shows one combined step) is never zero: a count that could have grown there is `at least N`, a zero
is `cannot-check`, and neither is listed as never fired. It reads with `gh api` GET only (or saved
responses in `--api-dir`, named as in SPEC-0007 rule 20) and the files of the repository, and
writes only to stdout, except `--write`, which writes `docs/runs/core-audit-<today>.md` (the date
from `date -u`) and never overwrites one. Exit 1 when the page exists, 2 for a bad call or a missing
input. Messages name the path class or the setting, never a value.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, repo_root
from metrics import UNSPLIT_STEP, VERDICT, ApiDir, Gh, author_of, origin_repo
from reviewers import verdict_authors

NAME = "core_audit"
USAGE = (
    "usage: core_audit.py [--since YYYY-MM-DD] [--json] [--write] [--today YYYY-MM-DD] "
    "[--repo OWNER/REPO | --api-dir DIR] [--authors LOGIN,LOGIN]"
)
CANNOT = "cannot-check"
WORKFLOW = ".github/workflows/governance.yml"
SESSION_RULES = "config/session-rules.md"
SPECS = "docs/specs"
ADRS = "docs/adr"
REQUIREMENTS = "docs/requirements.md"
SCRIPTS = "scripts/agk"
RUNS = "docs/runs"
GOVERNANCE = "governance"
CHECK_RUN = re.compile(r"scripts/agk/|agk\.mk|gitleaks")
NUMBERED = re.compile(r"(\d+[a-z]?)\. \S")
SPEC_FILE = re.compile(r"(\d{4})-[^/]+\.md")
RULE_NUMBERS = r"(\d+[a-z]?(?:(?:,? and |, )\d+[a-z]?)*)"
SESSION_CITE = re.compile(r"\bsession rules? " + RULE_NUMBERS)
SESSION_LONG = re.compile(r"\brule (\d+[a-z]?) of the session rules\b")
SPEC_CITE = re.compile(r"\b(SPEC-\d{4}) rules? " + RULE_NUMBERS)
SPLIT = re.compile(r",? and |, ")
PAGE_NOTE = (
    "This page is evidence for #278, not a decision: it lists what the kit's checks and rules "
    "refused in the history read below. It changes no rule and no check; a person files any "
    "follow-up."
)


# --- the repository ---------------------------------------------------------------------------


def workflow_checks(text: str) -> list[str]:
    """The names of the steps of the governance job that run a kit script, `agk.mk` or the scanner,
    in workflow order. A small reader of the step list: `- name:` items and their `run:` text."""
    steps: list[tuple[str | None, str]] = []
    in_steps = False
    step_indent = -1
    for raw in text.splitlines():
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        if stripped == "steps:":
            in_steps, step_indent = True, -1
            continue
        if not in_steps or not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if step_indent < 0:
                step_indent = indent
            if indent == step_indent:
                steps.append((None, ""))
                stripped = stripped[2:].strip()
        elif step_indent >= 0 and indent < step_indent:
            in_steps = False
            continue
        if not steps:
            continue
        name, body = steps[-1]
        if stripped.startswith("name:") and name is None:
            name = stripped[5:].strip().strip("\"'")
        steps[-1] = (name, body + "\n" + stripped)
    return [name for name, body in steps if name and CHECK_RUN.search(run_text(body))]


def run_text(body: str) -> str:
    """The `run:` part of a step (the line itself and the lines after it)."""
    at = body.find("\nrun:")
    return body[at:] if at >= 0 else ""


def session_rules(text: str) -> list[str]:
    return [m.group(1) for m in (NUMBERED.match(line) for line in text.splitlines()) if m]


def spec_rules(root: Path) -> dict[str, list[str]]:
    """SPEC-NNNN -> the numbers of the rules of its `## Rules` section, by spec number."""
    found: dict[str, list[str]] = {}
    folder = root / SPECS
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        match = SPEC_FILE.fullmatch(path.name)
        if not match:
            continue
        numbers: list[str] = []
        inside = False
        for line in read(path).splitlines():
            if line.startswith("## "):
                inside = line.strip() == "## Rules"
                continue
            rule = NUMBERED.match(line) if inside else None
            if rule and rule.group(1) not in numbers:
                numbers.append(rule.group(1))
        found[f"SPEC-{match.group(1)}"] = numbers
    return found


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        where = path.parent.name
        raise CheckError(f"a file of the repository cannot be read (path class {where}/)") from None


def totals(root: Path) -> dict[str, int]:
    def numbered(rel: str) -> int:
        folder = root / rel
        return sum(1 for p in folder.glob("[0-9][0-9][0-9][0-9]-*.md")) if folder.is_dir() else 0

    req = root / REQUIREMENTS
    requirements = len(re.findall(r"(?m)^#+ REQ-\d+", read(req))) if req.is_file() else 0
    scripts = root / SCRIPTS
    return {
        "adrs": numbered(ADRS),
        "specs": numbered(SPECS),
        "requirements": requirements,
        "scripts": sum(1 for _ in scripts.glob("*.py")) if scripts.is_dir() else 0,
    }


# --- the history ------------------------------------------------------------------------------


def failed_steps(src: Any, number: int) -> set[str] | None:
    """The names of the steps that failed in a governance run of any commit of the pull request,
    or None when a page cannot be read or a failure cannot be attributed to a step."""
    commits = src.get(f"commits-{number}", f"repos/{{repo}}/pulls/{number}/commits")
    if not isinstance(commits, list) or not commits:
        return None
    failed: set[str] = set()
    seen = False
    for commit in commits:
        sha = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(sha, str):
            return None
        checks = src.get(f"checks-{sha}", f"repos/{{repo}}/commits/{sha}/check-runs?per_page=100")
        if not isinstance(checks, dict) or not isinstance(checks.get("check_runs"), list):
            return None
        # a commit inside a push has no run of its own; a pull request with none at all is unread
        for run_ in checks["check_runs"]:
            if not isinstance(run_, dict) or run_.get("name") != GOVERNANCE:
                continue
            seen = True
            if run_.get("conclusion") != "failure":
                continue
            job = src.get(f"jobs-{run_.get('id')}", f"repos/{{repo}}/actions/jobs/{run_.get('id')}")
            steps = job.get("steps") if isinstance(job, dict) else None
            if not isinstance(steps, list) or not steps:
                return None
            names = {s.get("name") for s in steps if isinstance(s, dict)}
            bad = {
                s["name"]
                for s in steps
                if isinstance(s, dict)
                and s.get("conclusion") == "failure"
                and isinstance(s.get("name"), str)
            }
            if UNSPLIT_STEP in names or not bad:
                return None
            failed |= bad
    return failed if seen else None


def citations(body: str) -> tuple[set[str], set[tuple[str, str]]]:
    """(session rule numbers, (spec, rule number)) cited in one verdict body."""
    session: set[str] = set()
    for match in SESSION_CITE.finditer(body):
        session |= set(SPLIT.split(match.group(1)))
    session |= {m.group(1) for m in SESSION_LONG.finditer(body)}
    spec = {(m.group(1), n) for m in SPEC_CITE.finditer(body) for n in SPLIT.split(m.group(2))}
    return session, spec


def verdict_bodies(comments: list, allowed: set[str]) -> list[str]:
    out = []
    for c in comments:
        if not isinstance(c, dict) or author_of(c) not in allowed:
            continue
        body = c.get("body") if isinstance(c.get("body"), str) else ""
        lines = body.splitlines()
        if lines and VERDICT.fullmatch(lines[0].strip()):
            out.append(body)
    return out


def in_period(pull: Any, since: date | None) -> bool:
    if not isinstance(pull, dict) or not isinstance(pull.get("number"), int):
        return False
    if since is None:
        return True
    text = str(pull.get("created_at") or "")
    try:
        opened = datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return True  # an undated pull request is kept: dropping it could hide a refusal
    return opened >= since


def older_than(since: date | None):
    def done(chunk: list) -> bool:
        if since is None or not chunk:
            return False
        return not in_period(chunk[-1], since) and isinstance(chunk[-1], dict)

    return done


def collect(src: Any, since: date | None, allowed: set[str]) -> dict[str, Any]:
    endpoint = "repos/{repo}/pulls?state=all&sort=created&direction=desc"
    pulls = src.get("pulls", endpoint, older_than(since))
    if not isinstance(pulls, list):
        return {"pulls": None}
    steps: dict[str, int] = {}
    session: dict[str, int] = {}
    spec: dict[tuple[str, str], int] = {}
    total = unread_checks = unread_verdicts = 0
    for pull in pulls:
        if not in_period(pull, since):
            continue
        total += 1
        number = pull["number"]
        failed = failed_steps(src, number)
        if failed is None:
            unread_checks += 1
        for name in failed or ():
            steps[name] = steps.get(name, 0) + 1
        comments = src.get(f"comments-{number}", f"repos/{{repo}}/issues/{number}/comments")
        if not isinstance(comments, list):
            unread_verdicts += 1
            continue
        for body in verdict_bodies(comments, allowed):
            cited_session, cited_spec = citations(body)
            for n in cited_session:
                session[n] = session.get(n, 0) + 1
            for key in cited_spec:
                spec[key] = spec.get(key, 0) + 1
    return {
        "pulls": total,
        "unread_checks": unread_checks,
        "unread_verdicts": unread_verdicts,
        "steps": steps,
        "session": session,
        "spec": spec,
    }


# --- the report -------------------------------------------------------------------------------


def shown(count: int, complete: bool) -> int | str:
    """A count as reported: the number when every page was read, else `at least N` or
    `cannot-check` (never zero)."""
    if complete:
        return count
    return f"at least {count}" if count else CANNOT


def build(root: Path, src: Any, since: date | None, allowed: set[str]) -> dict[str, Any]:
    if not (root / WORKFLOW).is_file():
        raise CheckError("the governance workflow is missing (path class .github/)")
    if not (root / SESSION_RULES).is_file():
        raise CheckError("the session rules are missing (path class config/)")
    checks = workflow_checks(read(root / WORKFLOW))
    rules = session_rules(read(root / SESSION_RULES))
    specs = spec_rules(root)
    got = collect(src, since, allowed)
    read_all = got["pulls"] is not None
    steps = got.get("steps", {})
    checks_done = read_all and got["unread_checks"] == 0
    verdicts_done = read_all and got["unread_verdicts"] == 0
    session = got.get("session", {})
    spec = got.get("spec", {})
    check_counts = {c: shown(steps.get(c, 0), checks_done) for c in checks}
    other = {s: shown(n, checks_done) for s, n in sorted(steps.items()) if s not in checks}
    session_counts = {r: shown(session.get(r, 0), verdicts_done) for r in rules}
    session_counts |= {
        r: shown(n, verdicts_done) for r, n in sorted(session.items()) if r not in session_counts
    }
    spec_counts: dict[str, dict[str, int | str]] = {}
    for name, numbers in specs.items():
        spec_counts[name] = {n: shown(spec.get((name, n), 0), verdicts_done) for n in numbers}
    for (name, n), count in sorted(spec.items()):
        spec_counts.setdefault(name, {}).setdefault(n, shown(count, verdicts_done))
    never_spec = {
        name: [n for n, v in counts.items() if v == 0]
        for name, counts in spec_counts.items()
        if any(v == 0 for v in counts.values())
    }
    return {
        "since": since.isoformat() if since else None,
        "pull_requests": {
            "total": got["pulls"] if read_all else CANNOT,
            "unread_checks": got.get("unread_checks", CANNOT),
            "unread_verdicts": got.get("unread_verdicts", CANNOT),
        },
        "checks": check_counts,
        "other_steps": other,
        "session_rules": session_counts,
        "spec_rules": spec_counts,
        "never_fired": {
            "checks": [c for c, v in check_counts.items() if v == 0],
            "session_rules": [r for r, v in session_counts.items() if v == 0],
            "spec_rules": never_spec,
        },
        "totals": totals(root),
    }


def render(data: dict[str, Any], today: str) -> str:
    period = f"since {data['since']}" if data["since"] else "the whole history"
    prs = data["pull_requests"]
    out = [
        f"agk core audit, {period}, read on {today}",
        f"pull requests: {prs['total']} (check runs unreadable: {prs['unread_checks']}, "
        f"comments unreadable: {prs['unread_verdicts']})",
        "",
        "Governance checks (pull requests whose governance run failed on the check):",
    ]
    out += [f"  {name}: {count}" for name, count in data["checks"].items()]
    if data["other_steps"]:
        out.append("Failed steps that are no check of the current workflow:")
        out += [f"  {name}: {count}" for name, count in data["other_steps"].items()]
    out += ["", "Session rules (verdicts that cite the rule):"]
    out += [f"  session rule {n}: {count}" for n, count in data["session_rules"].items()]
    out += ["", "Spec rules (verdicts that cite the rule):"]
    for name, counts in data["spec_rules"].items():
        cited = [f"  {name} rule {n}: {c}" for n, c in counts.items() if c != 0]
        out += cited
    never = data["never_fired"]
    out += [
        "",
        "Never fired in the period:",
        f"  checks: {', '.join(never['checks']) or 'none'}",
        f"  session rules: {', '.join(never['session_rules']) or 'none'}",
    ]
    if never["spec_rules"]:
        out.append("  spec rules:")
        out += [f"    {name}: {', '.join(ns)}" for name, ns in never["spec_rules"].items()]
    else:
        out.append("  spec rules: none")
    out.append("")
    t = data["totals"]
    out.append(
        f"Totals: ADRs {t['adrs']}, specs {t['specs']}, requirements {t['requirements']}, "
        f"scripts {t['scripts']}"
    )
    return "\n".join(out)


def page(text: str, today: str) -> str:
    return (
        f"# Core audit {today}\n\n{PAGE_NOTE}\n\nWritten by `python3 scripts/agk/core_audit.py "
        f"--write` on {today} (the date from `date -u`).\n\n```text\n{text}\n```\n"
    )


# --- the call ---------------------------------------------------------------------------------


def day(text: str) -> date | None:
    try:
        return date.fromisoformat(text) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else None
    except ValueError:
        return None


def parse(args: list[str]) -> dict[str, Any] | None:
    flags = {"--json", "--write"}
    valued = {"--since", "--today", "--repo", "--api-dir", "--authors"}
    opts: dict[str, Any] = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in flags and arg not in opts:
            opts[arg] = True
            i += 1
        elif arg in valued and arg not in opts and i + 1 < len(args):
            opts[arg] = args[i + 1]
            i += 2
        else:
            return None
    if "--repo" in opts and "--api-dir" in opts:
        return None
    for key in ("--since", "--today"):
        if key in opts and day(opts[key]) is None:
            return None
    return opts


def main(argv: list[str] | None = None) -> int:
    opts = parse(sys.argv[1:] if argv is None else argv)
    if opts is None:
        print(USAGE)
        return 2
    today = opts.get("--today") or datetime.now(UTC).date().isoformat()
    try:
        root = repo_root()
        if "--authors" in opts:
            listed = [a for a in opts["--authors"].split(",") if a]
        else:
            listed = verdict_authors(root) or []
        allowed = {a.lstrip("@").lower() for a in listed}
        if not allowed:
            raise CheckError("no listed verdict author (setting: verdict_authors)")
        if "--api-dir" in opts:
            src: Any = ApiDir(Path(opts["--api-dir"]))
        else:
            src = Gh(opts.get("--repo") or origin_repo())
        since = day(opts["--since"]) if "--since" in opts else None
        data = build(root, src, since, allowed)
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 2
    text = render(data, today)
    if opts.get("--write"):
        target = root / RUNS / f"core-audit-{today}.md"
        if target.exists():
            print(f"FAIL {NAME}: the page of that day exists (path class {RUNS}/)")
            return 1
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(text, today), encoding="utf-8")
        print(f"wrote {target.relative_to(root)}", file=sys.stderr)
    print(json.dumps(data, indent=2) if opts.get("--json") else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
