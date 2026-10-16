"""Weekly drift audit of the default branch (SPEC-0004).

Standard library only; no network, no `gh`, no model, no writes. It reads git history and repository
files and prints one report on stdout. `--print-action` and `--print-title` give the issue
action and title from the same inputs, so the decision stays in this tested script.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import reviewers
from common import (
    CheckError,
    ac_coverage_mode,
    ac_markers_for,
    ac_shortfalls,
    git,
    load_config,
    markers_for,
    matches,
    parse_requirements,
    read_list,
    repo_root,
    run,
    show,
    stray_markers,
)

NAME = "drift-audit"
USAGE = (
    "usage: drift_audit.py [--today YYYY-MM-DD] [--branch NAME] [--open-issues 'N N'] "
    "[--print-action | --print-title]"
)
WINDOW_DAYS = 7
STALE_DAYS = 14
MARKER = "<!-- agk-drift-audit -->"
NOTICE = (
    "Scheduled runs can stop after a period of repository inactivity; "
    "run the audit by hand with workflow_dispatch."
)
PROTECTED_LIST = "config/protected-paths.txt"
REQUIREMENTS = "docs/requirements.md"
REGISTER = "docs/runs/residuals.md"
PLACEHOLDER = "@REPLACE-ME"
CODES = ("D1", "D2", "D3", "D4", "D5", "D6", "D7")
RULES = {
    "D1": "principle 1",
    "D2": "principle 10",
    "D3": "SPEC-0004 rule 8",
    "D4": "SPEC-0004 rule 9",
    "D5": "SPEC-0004 rule 10",
    "D6": "SPEC-0004 rule 15",
    "D7": "SPEC-0010 rule 4",
}
DATE_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}")
DUE = re.compile(r"\(due (\d{4}-\d{2}-\d{2})\)")


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    subject: str
    sentence: str

    def line(self) -> str:
        return f"- {self.code} {self.subject} | {RULES[self.code]} | {self.sentence}"


def parse_date(text: str) -> date | None:
    if not DATE_TEXT.fullmatch(text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def choose_action(open_issues: Sequence[int], has_findings: bool) -> str:
    """`create`, `update N` (the lowest-numbered open issue) or `none` (always when clean)."""
    if not has_findings:
        return "none"
    if not open_issues:
        return "create"
    return f"update {min(open_issues)}"


# --- the default branch -----------------------------------------------------------------------


def resolve_ref(root: Path, branch: str) -> str:
    for candidate in (f"refs/heads/{branch}", f"refs/remotes/origin/{branch}"):
        if git(root, "rev-parse", "--verify", "-q", f"{candidate}^{{commit}}", check=False).strip():
            return candidate
    raise CheckError("the default branch does not resolve")


def read(root: Path, rel: str) -> str | None:
    path = root / rel
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else None
    except (OSError, UnicodeDecodeError):
        return None


def docs(root: Path, folder: str) -> list[str]:
    base = root / "docs" / folder
    return sorted(p.relative_to(root).as_posix() for p in base.glob("[0-9][0-9][0-9][0-9]-*.md"))


# --- D1 ---------------------------------------------------------------------------------------


def commit_changes(root: Path, sha: str, parent: str | None) -> dict[str, str]:
    base = ["diff-tree", "--no-commit-id", "--no-renames", "-r", "-z", "--name-status"]
    out = git(root, *base, *(["--root", sha] if parent is None else [parent, sha]))
    tokens = out.split("\0")
    return {tokens[i + 1]: tokens[i][:1] for i in range(0, len(tokens) - 1, 2)}


def commit_lines(root: Path, sha: str, parent: str | None, path: str) -> list[str]:
    if parent is None:
        return []
    out = git(root, "diff", "-U0", "--no-renames", parent, sha, "--", path)
    lines, in_hunk = [], False
    for line in out.splitlines():
        if line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line[:1] in "+-":
            lines.append(line)
    return lines


def status_only(lines: list[str]) -> bool:
    return all(line[1:].startswith("- Status:") for line in lines)


def touched_classes(root: Path, sha: str, parent: str | None, changes: dict[str, str]) -> list[str]:
    listing = show(root, parent or sha, PROTECTED_LIST) or show(root, sha, PROTECTED_LIST)
    if listing is None:
        return []
    entries = read_list(listing)
    classes: list[str] = []
    for path, status in sorted(changes.items()):
        for entry in entries:
            if not matches(path, entry):
                continue
            if path == REQUIREMENTS and status == "M":
                lines = commit_lines(root, sha, parent, path)
                if lines and status_only(lines):
                    break
            if entry not in classes:
                classes.append(entry)
            break
    return classes


def covered(
    root: Path, sha: str, parent: str | None, changes: dict[str, str], classes: list[str]
) -> bool:
    for path, status in sorted(changes.items()):
        is_adr = (
            path.startswith("docs/adr/") and path.endswith(".md") and path != "docs/adr/TEMPLATE.md"
        )
        if not is_adr or status not in ("A", "M"):
            continue
        if status == "M" and status_only(commit_lines(root, sha, parent, path)):
            continue
        text = show(root, sha, path) or ""
        if all(entry in text for entry in classes):
            return True
    return False


def d1(root: Path, ref: str, today: date) -> list[Finding]:
    since = today - timedelta(days=WINDOW_DAYS)
    found = []
    log = git(root, "log", "--first-parent", "--format=%H%x1f%P%x1f%cI", ref)
    for line in log.splitlines():
        sha, parents, stamp = line.split("\x1f")
        when = datetime.fromisoformat(stamp).astimezone(UTC).date()
        if not since <= when <= today:
            continue
        parent = parents.split()[0] if parents.strip() else None
        changes = commit_changes(root, sha, parent)
        classes = touched_classes(root, sha, parent, changes)
        if classes and not covered(root, sha, parent, changes, classes):
            found += [
                Finding(
                    "D1", sha[:12], f"protected class `{c}` changed without an ADR that names it"
                )
                for c in classes
            ]
    return found


# --- D2, D3 -----------------------------------------------------------------------------------


def d2(root: Path) -> list[Finding]:
    text = read(root, REQUIREMENTS)
    if text is None:
        return []
    markers = markers_for(root)
    return [
        Finding("D2", req["id"], "done requirement has no test marker")
        for req in parse_requirements(text)
        if req["status"] == "done" and req["id"] not in markers
    ]


def added_on(root: Path, ref: str, rel: str) -> date | None:
    stamps = [
        s
        for s in git(root, "log", ref, "--diff-filter=A", "--format=%cI", "--", rel).splitlines()
        if s
    ]
    return datetime.fromisoformat(stamps[-1]).astimezone(UTC).date() if stamps else None


def d3(root: Path, ref: str, today: date) -> list[Finding]:
    found = []
    for rel in docs(root, "specs"):
        text = read(root, rel) or ""
        if re.search(r"^- Status:\s*Draft\s*$", text, flags=re.M):
            added = added_on(root, ref, rel)
            if added and (today - added).days > STALE_DAYS:
                age = (today - added).days
                found.append(
                    Finding("D3", rel, f"Draft spec is {age} days old (limit {STALE_DAYS})")
                )
    for rel in docs(root, "adr"):
        text = read(root, rel) or ""
        stamp = re.search(r"^- Date:\s*(\d{4}-\d{2}-\d{2})\s*$", text, flags=re.M)
        if re.search(r"^- Status:\s*Proposed\s*$", text, flags=re.M) and stamp:
            written = parse_date(stamp.group(1))
            if written and (today - written).days > STALE_DAYS:
                age = (today - written).days
                found.append(
                    Finding("D3", rel, f"Proposed ADR is {age} days old (limit {STALE_DAYS})")
                )
    return found


# --- D4 ---------------------------------------------------------------------------------------


def residual_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## Residual"
        elif in_section and line.startswith("- "):
            bullets.append(line)
        elif in_section and bullets and line.startswith(" ") and line.strip():
            bullets[-1] += " " + line.strip()
    return bullets


def d4_documents(root: Path, today: date) -> tuple[list[Finding], int]:
    found, undated = [], 0
    for rel in docs(root, "specs") + docs(root, "adr"):
        for number, bullet in enumerate(residual_bullets(read(root, rel) or ""), 1):
            due = DUE.search(bullet)
            if not due:
                undated += 1
            elif (when := parse_date(due.group(1))) is None:
                found.append(
                    Finding("D4", rel, f"residual bullet {number} has a malformed due date")
                )
            elif when < today:
                found.append(
                    Finding("D4", rel, f"residual bullet {number} is overdue since {when}")
                )
    return found, undated


def register_lines(text: str) -> list[dict]:
    """The lines of `## Open` of the register as {number, source, text, due, owner, well_formed}.

    A line with a missing or invalid due date, or an empty field, has `well_formed` False.
    """
    lines, in_open = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            in_open = line.strip() == "## Open"
        elif in_open and line.startswith("- "):
            parts = line[2:].split(" | ")
            due = DUE.fullmatch(parts[-2]) if len(parts) >= 4 else None
            when = parse_date(due.group(1)) if due else None
            fields = [parts[0], " | ".join(parts[1:-2]), parts[-1]] if len(parts) >= 4 else []
            lines.append(
                {
                    "number": number,
                    "source": parts[0],
                    "text": fields[1] if fields else line[2:],
                    "due": when,
                    "owner": fields[2] if fields else "",
                    "well_formed": when is not None and all(f.strip() for f in fields),
                }
            )
    return lines


def d4_register(root: Path, today: date) -> list[Finding]:
    text = read(root, REGISTER)
    if text is None:
        return []
    found = []
    for item in register_lines(text):
        if not item["well_formed"]:
            found.append(Finding("D4", f"{REGISTER}:{item['number']}", "malformed register line"))
        elif item["due"] < today:
            found.append(
                Finding("D4", item["source"], f"register line is overdue since {item['due']}")
            )
    return found


# --- D5 ---------------------------------------------------------------------------------------


def d5(root: Path) -> list[Finding]:
    config_text = read(root, reviewers.CONFIG)
    protected = read(root, PROTECTED_LIST)
    if config_text is None or protected is None:
        return [
            Finding(
                "D5", reviewers.CONFIG, "the reviewers configuration or protected list is missing"
            )
        ]
    try:
        data = reviewers.parse(config_text)
    except CheckError:
        return [Finding("D5", reviewers.CONFIG, "the reviewers configuration cannot be parsed")]
    found: list[Finding] = []
    problems = reviewers.validate(data, protected)
    differs = f"differs from {reviewers.PROTECTED_LIST}"
    if any(p.endswith(differs) for p in problems):
        found.append(
            Finding(
                "D5", reviewers.CONFIG, f"class protected differs from {reviewers.PROTECTED_LIST}"
            )
        )
    if any(not p.endswith(differs) for p in problems):
        found.append(Finding("D5", reviewers.CONFIG, "the reviewers configuration is invalid"))
    if PLACEHOLDER in config_text:
        found.append(Finding("D5", reviewers.CONFIG, "a team maps to the placeholder handle"))
    if problems:
        return found
    committed = read(root, reviewers.CODEOWNERS)
    if committed is None:
        return found + [Finding("D5", reviewers.CODEOWNERS, "the file is missing")]
    try:
        if reviewers.BLOCK_BEGIN in committed or reviewers.BLOCK_END in committed:
            committed = reviewers.extract_block(committed)
    except CheckError:
        return found + [
            Finding("D5", reviewers.CODEOWNERS, "the agk block is broken or duplicated")
        ]
    if committed != reviewers.render_codeowners(data):
        found.append(
            Finding("D5", reviewers.CODEOWNERS, f"differs from the rendering of {reviewers.CONFIG}")
        )
    return found


# --- D7 ---------------------------------------------------------------------------------------


def d7(root: Path) -> list[Finding]:
    """Stray markers always; in `warn` mode also each criterion shortfall (in `block` it fails)."""
    text = read(root, REQUIREMENTS)
    if text is None:
        return []
    reqs = parse_requirements(text)
    markers = ac_markers_for(root)
    found = [
        Finding(
            "D7",
            f"{m['file']}:{m['line']}",
            f"marker names {m['req']} {m['ac']}, which the requirement does not have",
        )
        for m in stray_markers(reqs, markers)
    ]
    if ac_coverage_mode(root) == "warn":
        found += [Finding("D7", rid, message) for rid, message in ac_shortfalls(reqs, markers)]
    return found


# --- the report -------------------------------------------------------------------------------


def audit(
    root: Path, today: date, branch: str | None, open_issues: Sequence[int]
) -> tuple[list[Finding], int]:
    ref = resolve_ref(root, branch or load_config(root)["default_branch"])
    found = d1(root, ref, today) + d2(root) + d3(root, ref, today)
    documents, undated = d4_documents(root, today)
    found += documents + d4_register(root, today) + d5(root) + d7(root)
    if len(open_issues) > 1:
        ordered = sorted(open_issues)
        subject = ",".join(f"#{n}" for n in ordered)
        found.append(
            Finding("D6", subject, f"duplicate audit issues; #{ordered[0]} is the one updated")
        )
    return sorted(found), undated


def render(today: date, found: list[Finding], undated: int) -> str:
    since = today - timedelta(days=WINDOW_DAYS)
    counts = " ".join(f"{c}={sum(1 for f in found if f.code == c)}" for c in CODES)
    lines = [
        f"agk drift audit {today} (window {since} to {today}): findings={len(found)} {counts}",
        "",
        f"Residual bullets without a due date: {undated} (not findings).",
        "",
    ]
    lines += [f.line() for f in found] or ["No findings."]
    return "\n".join([*lines, "", NOTICE, MARKER]) + "\n"


def parse_args(args: list[str]) -> dict | None:
    options: dict = {"today": None, "branch": None, "open": [], "mode": "report"}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--today", "--branch", "--open-issues") and i + 1 < len(args):
            value = args[i + 1]
            if arg == "--today":
                if parse_date(value) is None:
                    return None
                options["today"] = date.fromisoformat(value)
            elif arg == "--branch":
                options["branch"] = value
            else:
                tokens = value.replace(",", " ").split()
                if not all(t.isdigit() for t in tokens):
                    return None
                options["open"] = [int(t) for t in tokens]
            i += 2
        elif arg in ("--print-action", "--print-title") and options["mode"] == "report":
            options["mode"] = arg[len("--print-") :]
            i += 1
        else:
            return None
    return options


def main(argv: list[str] | None = None) -> int:
    options = parse_args(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    today = options["today"] or datetime.now(UTC).date()
    if options["mode"] == "title":
        print(f"agk drift audit {today}")
        return 0
    found, undated = audit(repo_root(), today, options["branch"], options["open"])
    if options["mode"] == "action":
        print(choose_action(options["open"], bool(found)))
    else:
        sys.stdout.write(render(today, found, undated))
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
