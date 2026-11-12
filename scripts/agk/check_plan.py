"""The plan check, the sources (SPEC-0043 rules 1 and 2, and rule 10's no-plan pass). Installed:
`kit/manifest.json` lists it in `verbatim`. Build (b) of SPEC-0043 rule 27 (amendment 163).

Rule 1: every file under `docs/sources/` (any depth) is `.md` or `.txt`, UTF-8 text, and starts
with exactly the lines `Source: <title>`, `Kind: <sow|brd|prd|design|charter|other>`,
`Version: <version>` and `Date: <YYYY-MM-DD>`, in this order, then one blank line and the text.
Rule 2: the design links are the rows of `docs/sources/design-links.md` (`Kind: design`), a table
with the columns `Name`, `Link` (an `https://` address), `Version` and `Frames`, each row with the
four values. No link is opened. A failure names the rule and the file (and the row), never a value.

With no problem it prints `ok plan (no plan)` when `docs/plan/` does not exist (rule 10), and
`ok plan sources` when it does: the plan's own rules (9 to 11) are build (d)'s.

`header(text)` and `location_problem(root, location)` are imported by builds (c) and (d): a
location of rule 1 is `<file>:<line>` or `<file>#<heading>` with the file under `docs/sources/`,
or a charter's `docs/adr/<NNNN>-project-charter.md#Milestones` (SPEC-0013; the `CHARTER_NAME` of
`playbook.py`, which is kit-only, so the pattern is kept here and a test holds the two equal).
Files only: no network, no model, nothing written.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import repo_root, run

NAME = "plan"
SOURCES = "docs/sources"
PLAN = "docs/plan"
LINKS = f"{SOURCES}/design-links.md"
HEADER = ("Source", "Kind", "Version", "Date")
KINDS = ("sow", "brd", "prd", "design", "charter", "other")
SUFFIXES = (".md", ".txt")
COLUMNS = ("Name", "Link", "Version", "Frames")
CHARTER_NAME = re.compile(r"^docs/adr/(\d{4})-project-charter\.md$")
CHARTER_HEADING = "Milestones"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
ITEM = re.compile(r"^\d+\.\s+\*\*([^*]+)\*\*")
USAGE = "usage: check_plan.py [--root DIR]"


def _value(line: str, key: str) -> str | None:
    prefix = f"{key}:"
    if not line.startswith(prefix):
        return None
    value = line[len(prefix) :].strip()
    return value or None


def header(text: str) -> dict[str, str] | None:
    """The four header values of a source of rule 1, or None when its first four lines are not."""
    lines = text.splitlines()[: len(HEADER)]
    if len(lines) < len(HEADER):
        return None
    values = {key: _value(line, key) for key, line in zip(HEADER, lines, strict=True)}
    if any(value is None for value in values.values()):
        return None
    return {key: str(value) for key, value in values.items()}


def real_date(value: str) -> bool:
    if not DATE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def header_problems(text: str) -> list[str]:
    """Rule 1's header problems of a source's text, each naming a header line, never a value."""
    lines = text.splitlines()
    first = lines[: len(HEADER)]
    found = {key for key in HEADER if any(_value(line, key) for line in first)}
    missing = [key for key in HEADER if key not in found]
    if missing:
        return [f"the header line {key}: is missing" for key in missing]
    values = header(text)
    if values is None:
        return ["the header lines are out of order"]
    out: list[str] = []
    if values["Kind"] not in KINDS:
        out.append("Kind: is outside the list " + ", ".join(KINDS))
    if not real_date(values["Date"]):
        out.append("Date: is not a real YYYY-MM-DD date")
    if len(lines) <= len(HEADER) or lines[len(HEADER)].strip():
        out.append("the header is not followed by one blank line")
    return out


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def source_files(root: Path) -> list[Path]:
    folder = root / SOURCES
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("*") if p.is_file())


def source_problems(root: Path) -> list[str]:
    """Rule 1 over every file under docs/sources/."""
    out: list[str] = []
    for path in source_files(root):
        rel = path.relative_to(root).as_posix()
        if path.suffix not in SUFFIXES:
            out.append(f"rule 1: {rel}: a source is .md or .txt")
            continue
        text = _read(path)
        if text is None:
            out.append(f"rule 1: {rel}: not UTF-8 text")
            continue
        out += [f"rule 1: {rel}: {problem}" for problem in header_problems(text)]
    return out


def _cells(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") else inner
    return [cell.strip() for cell in inner.split("|")]


def _separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def link_problems(root: Path) -> list[str]:
    """Rule 2 over docs/sources/design-links.md, when it exists."""
    path = root / LINKS
    if not path.is_file():
        return []
    text = _read(path)
    values = header(text) if text is not None else None
    if text is None or values is None:
        return []  # rule 1 names it
    out: list[str] = []
    if values["Kind"] != "design":
        out.append(f"rule 2: {LINKS}: Kind: is not design")
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip().startswith("|")), None)
    names = _cells(lines[start]) if start is not None else []
    if start is None or not set(COLUMNS) <= set(names) or len(names) != len(set(names)):
        return [*out, f"rule 2: {LINKS}: no table with the columns " + ", ".join(COLUMNS)]
    index = {name: names.index(name) for name in COLUMNS}
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        if not line.lstrip().startswith("|"):
            break
        cells = _cells(line)
        if not rows and _separator(cells):
            continue
        rows.append(cells)
    for n, cells in enumerate(rows, start=1):
        for name in COLUMNS:
            cell = cells[index[name]] if index[name] < len(cells) else ""
            if not cell:
                out.append(f"rule 2: {LINKS}: row {n}: the {name} value is empty")
            elif name == "Link" and not cell.startswith("https://"):
                out.append(f"rule 2: {LINKS}: row {n}: Link is not an https:// address")
    return out


def headings(text: str) -> list[str]:
    """The exact texts of the Markdown headings of a text, outside fenced blocks."""
    out: list[str] = []
    fenced = False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            continue
        match = None if fenced else HEADING.match(line)
        if match:
            out.append(match.group(1))
    return out


def _decision(text: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index("## Decision")
    except ValueError:
        return []
    rest = lines[start + 1 :]
    end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return rest[:end]


def location_problem(root: Path, location: str) -> str | None:
    """None when a location of rule 1 resolves; otherwise the problem, never the location's text."""
    if "#" in location:
        rel, _, anchor = location.partition("#")
        kind = "heading"
    else:
        rel, _, anchor = location.rpartition(":")
        kind = "line"
    path = PurePosixPath(rel)
    if not rel or not anchor or path.is_absolute() or ".." in path.parts or "\\" in rel:
        return "rule 1: a location is <file>:<line> or <file>#<heading>"
    charter = kind == "heading" and CHARTER_NAME.match(rel)
    if not charter and path.parts[:2] != tuple(SOURCES.split("/")):
        return f"rule 1: a location's file is under {SOURCES}/ or is a charter's #{CHARTER_HEADING}"
    text = _read(root / rel)
    if text is None or not (root / rel).is_file():
        return "rule 1: a location's file does not exist"
    if charter:
        items = [m.group(1).strip().rstrip(".:") for m in map(ITEM.match, _decision(text)) if m]
        if anchor != CHARTER_HEADING or CHARTER_HEADING not in items:
            return f"rule 1: a charter location is its #{CHARTER_HEADING} item"
        return None
    if kind == "line":
        if not anchor.isdigit() or not 1 <= int(anchor) <= len(text.splitlines()):
            return "rule 1: a location's line does not exist in its file"
        return None
    if path.suffix != ".md" or anchor not in headings(text):
        return "rule 1: a location's heading is not a heading of its file"
    return None


def cmd_check(root: Path) -> int:
    problems = source_problems(root) + link_problems(root)
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if problems:
        return 1
    print("ok plan sources" if (root / PLAN).is_dir() else "ok plan (no plan)")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if root is None and args:
        print(USAGE, file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
