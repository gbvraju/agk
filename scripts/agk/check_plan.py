"""The plan check, the sources (SPEC-0043 rules 1 and 2, and rule 10's no-plan pass). Installed:
`kit/manifest.json` lists it in `verbatim`. Build (b) of SPEC-0043 rule 27 (amendment 163).

Rule 1: every file under `docs/sources/` (any depth) is `.md` or `.txt`, UTF-8 text, and starts
with exactly the lines `Source: <title>`, `Kind: <sow|brd|prd|design|charter|openspec|other>`,
`Version: <version>` and `Date: <YYYY-MM-DD>`, in this order, then one blank line and the text.
Rule 2: the design links are the rows of `docs/sources/design-links.md` (`Kind: design`), a table
with the columns `Name`, `Link` (an `https://` address), `Version` and `Frames`, each row with the
four values. No link is opened. A failure names the rule and the file (and the row), never a value.

With no problem it prints `ok plan (no plan)` when `docs/plan/` does not exist (rule 10).

Build (d), rules 9 to 11 with amendment 163 item 4 (ADR-0457), when `docs/plan/` exists:
- rule 10 fails a requirement block of `docs/plan/requirements-proposed.md` (`### <key> <title>`)
  or `docs/requirements.md` (`### REQ-nnn`) with no `Source:` line that resolves, an `In scope`
  location of `docs/plan/scope.md` (a backticked `docs/...` span of a list line) that no
  requirement's `Source:` line cites, an `In scope` line with no location, a `## <screen>/<state>`
  heading of a `Kind: design` source that no requirement cites, and a `### M<n>` milestone of
  `docs/plan/milestones.md` that no brief file (`docs/plan/briefs/**/<key>.md`) names in its
  `Milestone:` line; each names the rule and the item, never its text;
- rule 11 ends with one line `ok plan: <a> of <b> in-scope source lines have a requirement, ...`
  (`plan: ...` after a failure); the last three counts need `--facts FILE`, else `not read`;
- rule 9, `--trace` prints the matrix first, one row per source location: requirement, spec rule,
  brief, merged pull request (the facts' `brief` of a merged pull request, the brief's number from
  `--numbers FILE`, rule 25's key-to-number file) and test (`common.markers_for`, the reading
  `traceability.py` prints), `none` where a link is missing. It is printed, never written.

Build (p), amendment 164 item 2 (ADR-0462): rule 10 also fails a requirement block of
`docs/plan/requirements-proposed.md` whose `Persona: P<n> <name>` line names a key that no
`### P<n> <name>` heading of `docs/plan/personas.md` holds, naming the requirement and the key,
never a name; a block without a `Persona:` line is not failed. The trace (rule 9) has a `Persona`
column after `Requirement`: the `Persona:` keys of the row's requirements, `none` where none.

Build (r), amendment 164 item 4 (ADR-0464): when `docs/sources/` holds a `Kind: design` file, rule
10 also fails a `### M<n>` block of `docs/plan/milestones.md` after `M1` with no `Demo:` line,
naming the milestone.

Build (u), amendment 166 item 5 (ADR-0474): when `docs/sources/` holds a `Kind: openspec` file,
rule 11's line gains `<a> of <b> scenarios have an acceptance line and <c> a test` after its first
count. A scenario is a `Scenario: ` heading under a `Requirement: ` heading of such a file outside
`changes/`, located as the reading writes it (`<file>#<heading>`, or `<file>:<line>` when the
heading repeats in its file); it has an acceptance line when a line of a requirement block ends
with ` (<location>)`, and a test when that block's id has a test marker. With `--trace` and a
`Kind: design` source, each scenario is printed `info plan: scenario <location>: <screens>` (the
`<screen>/<state>` headings whose screen its `GIVEN`, `WHEN`, `THEN` or `AND` steps name as whole
words, case, hyphens and underscores aside) or `...: names no screen`, then each screen no
scenario names `info plan: screen <location>: no scenario names it`: information, never a failure.

`header(text)` and `location_problem(root, location)` are imported by builds (c) and (d): a
location of rule 1 is `<file>:<line>` or `<file>#<heading>` with the file under `docs/sources/`,
or a charter's `docs/adr/<NNNN>-project-charter.md#Milestones` (SPEC-0013; the `CHARTER_NAME` of
`playbook.py`, which is kit-only, so the pattern is kept here and a test holds the two equal).
Files only: no network, no model, nothing written (principle 5).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import REQ_HEADER, markers_for, repo_root, run

NAME = "plan"
SOURCES = "docs/sources"
PLAN = "docs/plan"
LINKS = f"{SOURCES}/design-links.md"
HEADER = ("Source", "Kind", "Version", "Date")
KINDS = ("sow", "brd", "prd", "design", "charter", "openspec", "other")
SUFFIXES = (".md", ".txt")
COLUMNS = ("Name", "Link", "Version", "Frames")
CHARTER_NAME = re.compile(r"^docs/adr/(\d{4})-project-charter\.md$")
CHARTER_HEADING = "Milestones"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
ITEM = re.compile(r"^\d+\.\s+\*\*([^*]+)\*\*")
USAGE = "usage: check_plan.py [--root DIR] [--trace] [--facts FILE] [--numbers FILE]"
SCOPE = f"{PLAN}/scope.md"
PROPOSED = f"{PLAN}/requirements-proposed.md"
PERSONAS = f"{PLAN}/personas.md"
PERSONA_HEADING = re.compile(r"^###\s+(P[1-9]\d*)\b")
PERSONA_LINE = re.compile(r"^\s*Persona:\s*(\S+)")
REQUIREMENTS = "docs/requirements.md"
MILESTONES = f"{PLAN}/milestones.md"
BRIEFS = f"{PLAN}/briefs"
IN_SCOPE = "In scope"
BLOCK = re.compile(r"^###\s+(\S+)")
MILESTONE = re.compile(r"^###\s+(M\d+)\b")
SOURCE_LINE = re.compile(r"^\s*(?:[-*]\s+)?Source:\s*(.+?)\s*$")
LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s+")
SPAN = re.compile(r"`(docs/[^`]+)`")
SPEC_TITLE = re.compile(r"^#\s+(SPEC-\d{4})\b")
SPEC_REQS = re.compile(r"^-\s+Requirements:\s*(.*)$")
RULE = re.compile(r"^(\d+[a-z]?)\.\s")
NOT_READ = "not read"
OPENSPEC = "openspec"
REQUIREMENT, SCENARIO = "Requirement: ", "Scenario: "
CAPABILITY_LINE = re.compile(r"^\*Capability `[^`]+`")
STEP = re.compile(r"^\s*[-*+]\s+(?:\*\*)?(GIVEN|WHEN|THEN|AND)\b(?:\*\*)?:?\s*(.*?)\s*$", re.I)
ACCEPTANCE = re.compile(r"\s\((docs/[^()]+)\)\s*$")


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


def _line_value(text: str, key: str) -> str | None:
    for line in text.splitlines():
        value = _value(line.strip(), key)
        if value is not None:
            return value
    return None


def screens(root: Path) -> list[str]:
    """Amendment 163 item 4: each `## <screen>/<state>` heading of a `Kind: design` source."""
    out: list[str] = []
    for path in source_files(root):
        text = _read(path) if path.suffix == ".md" else None
        values = header(text) if text is not None else None
        if text is None or values is None or values["Kind"] != "design":
            continue
        rel = path.relative_to(root).as_posix()
        fenced = False
        for line in text.splitlines():
            if FENCE.match(line):
                fenced = not fenced
                continue
            name = line[3:].strip() if line.startswith("## ") and not fenced else ""
            screen, slash, state = name.partition("/")
            if slash and screen.strip() and state.strip() and "/" not in state:
                out.append(f"{rel}#{name}")
    return out


def _scenarios_of(rel: str, text: str, folder: bool) -> list[tuple[str, list[str]]]:
    """The scenarios of one `Kind: openspec` file as (location, step texts), in order. A combined
    file (`folder` False) reads requirements only under a capability, as `plan_intake.py` does."""
    lines = text.splitlines()
    counts: dict[str, int] = {}
    for h in headings(text):
        counts[h] = counts.get(h, 0) + 1
    out: list[tuple[str, list[str]]] = []
    capability, requirement = folder, False
    steps: list[str] | None = None
    fenced = False
    for index, line in enumerate(lines):
        if FENCE.match(line):
            fenced = not fenced
            continue
        match = None if fenced else HEADING.match(line)
        if match is None:
            if steps is not None and not fenced and (step := STEP.match(line)):
                steps.append(step.group(2))
            continue
        name, steps = match.group(1), None
        following = next((x.strip() for x in lines[index + 1 :] if x.strip()), "")
        if not folder and CAPABILITY_LINE.match(following):
            capability, requirement = True, False
        elif capability and name.startswith(REQUIREMENT):
            requirement = True
        elif requirement and name.startswith(SCENARIO):
            location = f"{rel}#{name}" if counts[name] == 1 else f"{rel}:{index + 1}"
            steps = []
            out.append((location, steps))
        else:
            requirement = False
    return out


def scenarios(root: Path) -> list[tuple[str, list[str]]] | None:
    """Build (u): the scenarios of the `Kind: openspec` sources outside `changes/`, or None when
    there is no such source."""
    found = False
    out: list[tuple[str, list[str]]] = []
    for path in source_files(root):
        text = _read(path) if path.suffix == ".md" else None
        if text is None or (header(text) or {}).get("Kind") != OPENSPEC:
            continue
        found = True
        parts = path.relative_to(root / SOURCES).parts
        if "changes" in parts:
            continue
        folder = "specs" in parts[:-1]
        out += _scenarios_of(path.relative_to(root).as_posix(), text, folder)
    return out if found else None


def acceptance_lines(root: Path) -> dict[str, list[str]]:
    """Build (u): each location a requirement block's line ends with, to the blocks' ids."""
    out: dict[str, list[str]] = {}
    for rel, pattern in ((PROPOSED, BLOCK), (REQUIREMENTS, REQ_HEADER)):
        current: str | None = None
        for line in (_read(root / rel) or "").splitlines():
            if match := pattern.match(line):
                current = match.group(1).rstrip(":")
            elif line.startswith("#"):
                current = None
            elif current is not None and (end := ACCEPTANCE.search(line)):
                out.setdefault(end.group(1), []).append(current)
    return out


def _words(text: str) -> str:
    return " " + " ".join(re.sub(r"[-_]", " ", text).lower().split()) + " "


def names_screen(steps: list[str], screen: str) -> bool:
    """Whether a step names the screen of a `<file>#<screen>/<state>` location, as whole words."""
    name = _words(screen.partition("#")[2].partition("/")[0]).strip()
    return bool(name) and any(
        re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", _words(step)) for step in steps
    )


def scope_lines(root: Path) -> list[tuple[int, list[str]]]:
    """The list lines under the `In scope` heading of scope.md: (line number, locations)."""
    text = _read(root / SCOPE) or ""
    out: list[tuple[int, list[str]]] = []
    inside = False
    for n, line in enumerate(text.splitlines(), start=1):
        match = HEADING.match(line)
        if match:
            inside = match.group(1) == IN_SCOPE
        elif inside and LIST_ITEM.match(line):
            out.append((n, SPAN.findall(line)))
    return out


def requirements(root: Path) -> list[tuple[str, str, list[str]]]:
    """Each requirement block as (file, id or key, its Source: locations), proposed file first."""
    out: list[tuple[str, str, list[str]]] = []
    for rel, pattern in ((PROPOSED, BLOCK), (REQUIREMENTS, REQ_HEADER)):
        current: list[str] | None = None
        for line in (_read(root / rel) or "").splitlines():
            match = pattern.match(line)
            if match:
                current = []
                out.append((rel, match.group(1).rstrip(":"), current))
            elif line.startswith("#"):
                current = None
            elif current is not None and (source := SOURCE_LINE.match(line)):
                current.append(source.group(1).strip("`"))
    return out


def personas(root: Path) -> tuple[dict[str, str], set[str]]:
    """Build (p): each proposed requirement's `Persona:` key, and the keys of `personas.md`."""
    named: dict[str, str] = {}
    current: str | None = None
    for line in (_read(root / PROPOSED) or "").splitlines():
        if match := BLOCK.match(line):
            current = match.group(1).rstrip(":")
        elif line.startswith("#"):
            current = None
        elif current is not None and current not in named and (key := PERSONA_LINE.match(line)):
            named[current] = key.group(1)
    text = (_read(root / PERSONAS) or "").splitlines()
    return named, {m.group(1) for m in map(PERSONA_HEADING.match, text) if m}


def briefs(root: Path) -> list[tuple[str, str | None, list[str]]]:
    """Each brief file as (key, its Milestone:, its Advances: ids)."""
    folder = root / BRIEFS
    out: list[tuple[str, str | None, list[str]]] = []
    for path in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
        text = _read(path) or ""
        advances = re.split(r"[,\s]+", _line_value(text, "Advances") or "")
        out.append((path.stem, _line_value(text, "Milestone"), [a for a in advances if a]))
    return out


def milestones(root: Path) -> list[str]:
    text = _read(root / MILESTONES) or ""
    return [m.group(1) for m in map(MILESTONE.match, text.splitlines()) if m]


def undemoed(root: Path) -> list[str]:
    """Build (r): each milestone after the first whose block has no `Demo:` line."""
    found: dict[str, bool] = {}
    current: str | None = None
    for line in (_read(root / MILESTONES) or "").splitlines():
        if match := MILESTONE.match(line):
            current = match.group(1)
            found.setdefault(current, False)
        elif line.startswith("#"):
            current = None
        elif current is not None and line.startswith("Demo:"):
            found[current] = True
    return [m for m, demo in found.items() if m != "M1" and not demo]


def design_source(root: Path) -> bool:
    """Whether a file under `docs/sources/` has the header `Kind: design`."""
    return any(
        (header(_read(path) or "") or {}).get("Kind") == "design" for path in source_files(root)
    )


def spec_rules(root: Path) -> dict[str, list[str]]:
    """Requirement id to `SPEC-nnnn rule N` (the rules citing it) or `SPEC-nnnn`."""
    out: dict[str, list[str]] = {}
    folder = root / "docs" / "specs"
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        lines = (_read(path) or "").splitlines()
        title = SPEC_TITLE.match(lines[0]) if lines else None
        names = next((m.group(1) for m in map(SPEC_REQS.match, lines) if m), "")
        if title is None:
            continue
        in_rules = False
        cited: dict[str, list[str]] = {}
        for line in lines:
            if line.startswith("## "):
                in_rules = line.strip() == "## Rules"
            elif in_rules and (rule := RULE.match(line)):
                for token in set(re.findall(r"[A-Za-z0-9_-]+", line)):
                    cited.setdefault(token, []).append(f"{title.group(1)} rule {rule.group(1)}")
        for req in (n for n in re.split(r"[,\s]+", names) if n):
            out.setdefault(req, []).extend(cited.get(req) or [title.group(1)])
    return out


def _cell(values: list[str]) -> str:
    return ", ".join(dict.fromkeys(values)) or "none"


class Plan:
    """What rules 9 to 11 read from the plan's files, once."""

    LAST = (
        "requirements have a brief",
        "briefs have a merged pull request",
        "requirements have a test",
    )

    def __init__(self, root: Path, facts: dict | None, numbers: dict[str, int]) -> None:
        self.root = root
        self.reqs = requirements(root)
        self.briefs = briefs(root)
        self.scope = scope_lines(root)
        self.screens = screens(root)
        self.persona_of, self.personas = personas(root)
        self.scenarios = scenarios(root)
        self.cited: dict[str, list[str]] = {}
        for _, req, sources in self.reqs:
            for source in sources:
                self.cited.setdefault(source, []).append(req)
        pulls = (facts or {}).get("pull_requests")
        self.merged: dict[int, list[int]] | None = None
        if isinstance(pulls, list):
            self.merged = {}
            for pr in pulls:
                if (
                    isinstance(pr, dict)
                    and pr.get("state") == "merged"
                    and isinstance(pr.get("brief"), int)
                ):
                    self.merged.setdefault(pr["brief"], []).append(int(pr.get("number", 0)))
        self.numbers = numbers

    def in_scope(self) -> list[str | None]:
        """Rule 11's in-scope locations, each once, in order; None for a line with no location."""
        seen: dict[str, None] = {}
        units: list[str | None] = []
        for _, locations in self.scope:
            if not locations:
                units.append(None)
            for location in locations:
                if location not in seen:
                    seen[location] = None
                    units.append(location)
        units += [s for s in self.screens if s not in seen]
        return units

    def problems(self) -> list[str]:
        out: list[str] = []
        for rel, req, sources in self.reqs:
            if not any(location_problem(self.root, s) is None for s in sources):
                out.append(f"rule 10: {rel}: {req}: no Source: line resolves")
        for _, req, _ in (r for r in self.reqs if r[0] == PROPOSED):
            key = self.persona_of.get(req)
            if key is not None and key not in self.personas:
                out.append(
                    f"rule 10: {PROPOSED}: {req}: Persona: {key} names no persona of {PERSONAS}"
                )
        reported: set[str] = set()
        for n, locations in self.scope:
            if not locations:
                out.append(f"rule 10: {SCOPE}:{n}: an In scope line names no location")
            for location in locations:
                if location not in self.cited and location not in reported:
                    reported.add(location)
                    out.append(f"rule 10: {SCOPE}:{n}: no requirement cites {location}")
        for screen in self.screens:
            if screen not in self.cited and screen not in reported:
                out.append(f"rule 10: {screen}: no requirement cites this screen and state")
        named = {milestone for _, milestone, _ in self.briefs}
        for milestone in milestones(self.root):
            if milestone not in named:
                out.append(f"rule 10: {MILESTONES}: {milestone}: no brief names this milestone")
        if design_source(self.root):
            out += [f"rule 10: {MILESTONES}: {m}: no Demo: line" for m in undemoed(self.root)]
        return out

    def _merged_of(self, keys: list[str]) -> list[str]:
        merged = self.merged or {}
        return [
            f"#{n}"
            for key in keys
            if key in self.numbers
            for n in merged.get(self.numbers[key], [])
        ]

    def coverage(self, facts: bool) -> str:
        units = self.in_scope()
        a = sum(1 for unit in units if unit is not None and unit in self.cited)
        parts = [f"{a} of {len(units)} in-scope source lines have a requirement"]
        if self.scenarios is not None:
            parts.append(self.scenario_count())
        ids = [req for _, req, _ in self.reqs]
        if not facts:
            return ", ".join(parts + [f"{what}: {NOT_READ}" for what in self.LAST])
        advanced = {req for _, _, advances in self.briefs for req in advances}
        parts.append(
            f"{sum(1 for r in ids if r in advanced)} of {len(ids)} requirements have a brief"
        )
        if self.merged is None:
            parts.append(f"{self.LAST[1]}: {NOT_READ}")
        else:
            done = sum(1 for key, _, _ in self.briefs if self._merged_of([key]))
            parts.append(f"{done} of {len(self.briefs)} briefs have a merged pull request")
        tested = markers_for(self.root)
        parts.append(
            f"{sum(1 for r in ids if tested.get(r))} of {len(ids)} requirements have a test"
        )
        return ", ".join(parts)

    def scenario_count(self) -> str:
        """Build (u): `<a> of <b> scenarios have an acceptance line and <c> a test`."""
        accepted = acceptance_lines(self.root)
        tested = markers_for(self.root)
        lines = [accepted.get(location, []) for location, _ in self.scenarios or []]
        a = sum(1 for ids in lines if ids)
        c = sum(1 for ids in lines if any(tested.get(i) for i in ids))
        return f"{a} of {len(lines)} scenarios have an acceptance line and {c} a test"

    def screen_lines(self) -> list[str]:
        """Build (u): each scenario's screens, then each screen no scenario names (`--trace`)."""
        if self.scenarios is None or not design_source(self.root):
            return []
        out: list[str] = []
        named: set[str] = set()
        for location, steps in self.scenarios:
            matched = [s for s in self.screens if names_screen(steps, s)]
            named.update(matched)
            out.append(
                f"info plan: scenario {location}: " + (", ".join(matched) or "names no screen")
            )
        out += [f"info plan: screen {s}: no scenario names it" for s in self.screens if s not in named]
        return out

    def trace(self, facts: bool) -> list[str]:
        rows = [u for u in self.in_scope() if u is not None]
        rows += [loc for loc in self.cited if loc not in rows]
        specs = spec_rules(self.root)
        tested = markers_for(self.root)
        out = [
            "| Location | Requirement | Persona | Spec rule | Brief | Pull request | Test |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for location in rows:
            reqs = list(dict.fromkeys(self.cited.get(location, [])))
            keys = [key for key, _, advances in self.briefs if set(advances) & set(reqs)]
            pulls = _cell(self._merged_of(keys)) if facts and self.merged is not None else NOT_READ
            cells = [
                location,
                _cell(reqs),
                _cell([self.persona_of[req] for req in reqs if req in self.persona_of]),
                _cell([rule for req in reqs for rule in specs.get(req, [])]),
                _cell(keys),
                pulls,
                _cell([file for req in reqs for file in tested.get(req, [])]),
            ]
            out.append("| " + " | ".join(cells) + " |")
        return out


def cmd_check(
    root: Path,
    trace: bool = False,
    facts: dict | None = None,
    numbers: dict[str, int] | None = None,
) -> int:
    problems = source_problems(root) + link_problems(root)
    if not (root / PLAN).is_dir():
        for problem in problems:
            print(f"FAIL {NAME}: {problem}")
        if not problems:
            print("ok plan (no plan)")
        return 1 if problems else 0
    plan = Plan(root, facts, numbers or {})
    if trace:
        print("\n".join(plan.trace(facts is not None) + plan.screen_lines()))
    problems += plan.problems()
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    print(("plan: " if problems else "ok plan: ") + plan.coverage(facts is not None))
    return 1 if problems else 0


def _json(path: str, option: str) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise SystemExit(f"check_plan.py: {option}: not a readable JSON file") from None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    values: dict[str, str] = {}
    trace = False
    while args:
        arg = args.pop(0)
        if arg == "--trace":
            trace = True
        elif arg in ("--root", "--facts", "--numbers") and args and arg not in values:
            values[arg] = args.pop(0)
        else:
            print(USAGE, file=sys.stderr)
            return 2
    try:
        facts = _json(values["--facts"], "--facts") if "--facts" in values else None
        numbers = _json(values["--numbers"], "--numbers") if "--numbers" in values else {}
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    if facts is not None and not isinstance(facts, dict):
        print("check_plan.py: --facts: not a facts object", file=sys.stderr)
        return 2
    if not isinstance(numbers, dict) or not all(
        isinstance(k, str) and isinstance(v, int) for k, v in numbers.items()
    ):
        print(
            "check_plan.py: --numbers: not an object of brief key to issue number", file=sys.stderr
        )
        return 2
    root = Path(values["--root"]) if "--root" in values else None
    return run(NAME, lambda: cmd_check(root or repo_root(), trace, facts, numbers))


if __name__ == "__main__":
    sys.exit(main())
