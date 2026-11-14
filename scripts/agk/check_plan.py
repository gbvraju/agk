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
count (`<c>` with `--facts`, else `... and a test: not read`). A scenario is a `Scenario: `
heading under a `Requirement: ` heading of such a file outside
`changes/`, located as the reading writes it (`<file>#<heading>`, or `<file>:<line>` when the
heading repeats in its file); it has an acceptance line when a line of a requirement block ends
with ` (<location>)`, and a test when that line is criterion n of a `REQ-nnn` block (its `ACn` on
an `Acceptance:` line, or its place in the list after `Criteria:`) and a test marks `REQ-nnn ACn`.
With a `Kind: design` source, a scenario names the screen of a `<screen>/<state>` heading when a
`GIVEN`, `WHEN`, `THEN` or `AND` step holds that screen as whole words, case, hyphens and
underscores aside; before rule 11's line one `unmatched scenario: <location>` per scenario that
names none and one `unmatched screen: <screen>` per screen no scenario names are printed, and
`--trace` adds `info plan: scenario <location>: <screens>` (or `names no screen`) per scenario
after the matrix: information, never a failure.

Brief #1118, amendment 167 (ADR-0478), with `--trace` and information only: each sentence of a
block's `Statement:` line holding `SHALL` is one rule `<key>.r<n>`, and an acceptance line names
the rules it proves with `(rules r1, r2)`; when a block has a statement, `info plan: <a> of <b>
rules have an acceptance line and <c> a test` and one line per rule with none. When
`docs/plan/access.md` (`| Persona | Screen | Allowed | Sources |`) exists, an acceptance line names
a cell with `(access <persona>/<screen>)`, and `info plan: <a> of <b> access cells have a test`
with one line per cell no acceptance line names. A test is a `REQ-nnn ACn` marker of the naming
criterion, read with `--facts`, else `not read`.

Brief #1183 (ADR-0502): a block of `docs/requirements.md` numbered REQ-001 to REQ-099, the range
that file reserves for the kit, with no `Source:` line is left out of rule 10, the trace and the
counts of rule 11; such a block that carries a `Source:` line is checked as any other.

Brief #1217, amendment 175 (ADR-0516): rule 10 also fails each file under `docs/sources/` with no
location that a requirement's `Source:` line cites and that resolves, unless a list line under the
`Out of scope` heading of `docs/plan/scope.md` names the file by its own path (a backticked span
with no line or heading) and gives a reason (text beside its spans), with one line
`<file> is a source no requirement cites (list it out of scope or cite it)`, never its text. With
`--trace`, after the matrix, one line per source file `<file>: <a> of <b> headings or rows cited`:
the units are a Markdown file's headings (outside fences) and table rows (after a separator line),
or a text file's non-blank lines after its header, each cited by `<file>#<heading>` or by
`<file>:<line>` of its line. Rule 11's coverage line is unchanged. With the maintainers' answer to
`Q-1217-1`, two more locations cite a source: a requirement's acceptance line ending with
` (<location>)` into a `Kind: openspec` source, and a `Source:` line of a brief file that carries a
`Component:` line (the brief of a shared component, which `plan_intake.py render` writes).

Build (g), rules 20 to 22 (brief #1095, ADR-0467), when `docs/plan/` exists: rule 20 fails a
`docs/plan/baseline.json` that is not `schema` 1 with a full `head`, a real `date`, an `https://`
`link` and a list of `milestones` (each an `id` `M<n>`, its `briefs` keys, its `target` date or
null and its `estimate` text), and, read from git, a baseline that the merge base with `--base REF`
(else the default branch) holds and the working tree changed or removed; a base that does not
resolve in CI fails (`common.resolve_base`), and only outside CI with no base, or outside a git
work tree, is it not read. Rule 21 fails a `Scope change: SC-<n>` block of
`docs/plan/scope-changes.md` without its `What:`, `Why:`, `Source:` (a location, or `person
<date>`), `Effect:` or `Status: proposed` line, a number used twice, and a `Briefs:` entry other
than `+M<n>/<key> <size> <low>-<high> hours` or `-M<n>/<key>` (`; ` between entries). Rule 22
fails an `Approved:` line that is not `<date> <https link>`, a brief file whose `Milestone:` is a
baseline milestone and whose key is neither in that milestone's `briefs` nor added there by an
approved scope change, and a baseline brief no longer under its milestone that no approved scope
change removes, naming the key. A scope change is approved by its `Approved:` line; with
`--comments FILE` (the saved comments of the pull request) only when an account of
`spec_approvers` also gave `Approve: scope SC-<n> <full head ID>` (`reviewers.scope_approvals`, in
solo mode inside the person's `Confirmed:` comment) on this pull request, or when the merge base
already holds the whole approved block unchanged (approved on the pull request that merged it;
brief #1166, ADR-0496). The governance job passes the saved comments on a pull request event; a
push and a local run read the `Approved:` line alone.

Brief #1219, amendment 176 (ADR-0518): when `docs/plan/scope-lock.md` exists, rule 10 also fails
each of its lines, once per kind, that holds a requirement number (`REQ-` and digits), a file path
(a word holding `/` whose last part has a file extension, or one starting `./`, `../`, `~/` or a
repository folder; a link holding `://` is not one), a brief key (a brief file's name under
`docs/plan/briefs/`, as a whole word) or a builder or pull request figure (`builder`, `pull
request`, `PR rate`, whole words, any case, plurals too), as `rule 10: <file>:<line>: <kind>`,
never the text.

`header(text)` and `location_problem(root, location)` are imported by builds (c) and (d): a
location of rule 1 is `<file>:<line>` or `<file>#<heading>` with the file under `docs/sources/`,
or a charter's `docs/adr/<NNNN>-project-charter.md#Milestones` (SPEC-0013; the `CHARTER_NAME` of
`playbook.py`, which is kit-only, so the pattern is kept here and a test holds the two equal).
Files and a read of git only: no network, no model, nothing written (principle 5).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    REQ_HEADER,
    ac_markers_for,
    agent_apps,
    git,
    markers_for,
    merge_base,
    repo_root,
    resolve_base,
    run,
    show,
    utf8_output,
)

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
USAGE = (
    "usage: check_plan.py [--root DIR] [--trace] [--facts FILE] [--numbers FILE] "
    "[--comments FILE] [--base REF]"
)
SCOPE = f"{PLAN}/scope.md"
PROPOSED = f"{PLAN}/requirements-proposed.md"
PERSONAS = f"{PLAN}/personas.md"
PERSONA_HEADING = re.compile(r"^###\s+(P[1-9]\d*)\b")
PERSONA_LINE = re.compile(r"^\s*Persona:\s*(\S+)")
REQUIREMENTS = "docs/requirements.md"
MILESTONES = f"{PLAN}/milestones.md"
BRIEFS = f"{PLAN}/briefs"
IN_SCOPE = "In scope"
OUT_OF_SCOPE = "Out of scope"
BLOCK = re.compile(r"^###\s+(\S+)")
MILESTONE = re.compile(r"^###\s+(M\d+)\b")
KIT_RANGE = re.compile(r"^REQ-(\d{3})$")
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
ACCEPTANCE_LINE = re.compile(r"^\s*(?:[-*]\s+)?Acceptance:\s")
AC_NUMBER = re.compile(r"(?:^|[:;]\s*)AC(\d+)\s")
CRITERIA = re.compile(r"^\s*Criteria:\s*$")
REQ_KEY = re.compile(r"^REQ-\d+$")
STATEMENT_LINE = re.compile(r"^\s*(?:[-*]\s+)?Statement:\s*(.+?)\s*$")
SHALL = re.compile(r"\bSHALL\b")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
RULES_MARK = re.compile(r"\(rules?\s+(r[1-9]\d*(?:\s*,\s*r[1-9]\d*)*)\)")
ACCESS_MARK = re.compile(r"\(access\s+(P[1-9]\d*/[^()]*[^()\s])\s*\)")
ACCESS = f"{PLAN}/access.md"
ACCESS_COLUMNS = ("Persona", "Screen", "Allowed", "Sources")


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


def acceptance_lines(root: Path) -> dict[str, list[tuple[str, int | None]]]:
    """Build (u): each location a requirement block's line ends with, to (the block's id, the
    criterion's number n). On an `Acceptance:` line n is that of its last `ACn`; on a list line
    after a `Criteria:` line, n is the list line's place there; else None."""
    out: dict[str, list[tuple[str, int | None]]] = {}
    for rel, pattern in ((PROPOSED, BLOCK), (REQUIREMENTS, REQ_HEADER)):
        current: str | None = None
        place: int | None = None
        for line in (_read(root / rel) or "").splitlines():
            if match := pattern.match(line):
                current, place = match.group(1).rstrip(":"), None
                continue
            if line.startswith("#"):
                current = None
                continue
            if current is None:
                continue
            if CRITERIA.match(line):
                place = 0
                continue
            listed = LIST_ITEM.match(line) is not None and place is not None
            if listed:
                place = (place or 0) + 1
            elif line.strip() and place is not None:
                place = None
            end = ACCEPTANCE.search(line)
            if end is None:
                continue
            numbers = AC_NUMBER.findall(line) if ACCEPTANCE_LINE.match(line) else []
            n = int(numbers[-1]) if numbers else (place if listed else None)
            out.setdefault(end.group(1), []).append((current, n))
    return out


def _words(text: str) -> str:
    return " " + " ".join(re.sub(r"[-_]", " ", text).lower().split()) + " "


def names_screen(steps: list[str], screen: str) -> bool:
    """Whether a step names the screen of a `<file>#<screen>/<state>` location, as whole words."""
    name = _words(screen.partition("#")[2].partition("/")[0]).strip()
    return bool(name) and any(
        re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", _words(step)) for step in steps
    )


def rules_of(statement: str) -> list[str]:
    """Amendment 167 item 1: each sentence of a statement that holds `SHALL` is one rule."""
    return [s for s in SENTENCE_END.split(statement.strip()) if SHALL.search(s)]


def marked_rules(text: str) -> list[str]:
    """The `r<n>` of every `(rules r1, r2)` mark of an acceptance line."""
    return [r.strip() for m in RULES_MARK.finditer(text) for r in m.group(1).split(",")]


def marked_cells(text: str) -> list[str]:
    """The `<persona>/<screen>` of every `(access ...)` mark of an acceptance line."""
    return [m.group(1).strip() for m in ACCESS_MARK.finditer(text)]


def blocks(root: Path) -> list[tuple[str, str, list[tuple[int | None, str]]]]:
    """Amendment 167: each requirement block as (id, its statement, its acceptance lines as
    (criterion n, text)): an `ACn` segment of an `Acceptance:` line is criterion n, the n-th list
    line after `Criteria:` criterion n, and any other line None, as `acceptance_lines` reads."""
    out: list[tuple[str, str, list[tuple[int | None, str]]]] = []
    for rel, pattern in ((PROPOSED, BLOCK), (REQUIREMENTS, REQ_HEADER)):
        lines: list[tuple[int | None, str]] | None = None
        place: int | None = None
        for line in (_read(root / rel) or "").splitlines():
            if match := pattern.match(line):
                lines, place = [], None
                out.append((match.group(1).rstrip(":"), "", lines))
                continue
            if line.startswith("#"):
                lines = None
            if lines is None:
                continue
            if statement := STATEMENT_LINE.match(line):
                key, text, _ = out[-1]
                out[-1] = (key, f"{text} {statement.group(1)}".strip(), lines)
                continue
            if CRITERIA.match(line):
                place = 0
                continue
            listed = LIST_ITEM.match(line) is not None and place is not None
            if listed:
                place = (place or 0) + 1
            elif line.strip() and place is not None:
                place = None
            starts = list(AC_NUMBER.finditer(line)) if ACCEPTANCE_LINE.match(line) else []
            if starts:
                ends = [m.start() for m in starts[1:]] + [len(line)]
                lines += [
                    (int(m.group(1)), line[m.start() : e])
                    for m, e in zip(starts, ends, strict=True)
                ]
            else:
                lines.append((place if listed else None, line))
    return out


def access_cells(root: Path) -> list[tuple[str, str]] | None:
    """Amendment 167 item 2: the rows of `docs/plan/access.md` as (`<persona>/<screen>`,
    allowed), or None without the file."""
    text = _read(root / ACCESS)
    if text is None:
        return None
    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        cells = _cells(line) if line.strip().startswith("|") else []
        if len(cells) == len(ACCESS_COLUMNS) and tuple(cells) != ACCESS_COLUMNS:
            if not _separator(cells):
                out.append((f"{cells[0]}/{cells[1]}", cells[2]))
    return out


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


def out_of_scope_files(root: Path) -> set[str]:
    """Brief #1217 (ADR-0516): the files under `docs/sources/` that a list line under the
    `Out of scope` heading of scope.md names by its own path (a backticked span with no `:<line>`
    or `#<heading>`) with a reason, that is with text beside its spans."""
    text = _read(root / SCOPE) or ""
    out: set[str] = set()
    inside = False
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            inside = match.group(1) == OUT_OF_SCOPE
        elif inside and (item := LIST_ITEM.match(line)):
            rest = SPAN.sub("", line[item.end() :])
            if not re.sub(r"[\W_]", "", rest):
                continue  # no reason given
            for span in SPAN.findall(line):
                if span.startswith(f"{SOURCES}/") and (root / span).is_file():
                    out.add(span)
    return out


def source_units(text: str, markdown: bool) -> list[tuple[int, str | None]]:
    """Brief #1217 answer 2: the headings (outside fenced blocks) and the table rows (a `|` line
    after a separator line) of a Markdown source, or each non-blank line of a text source after
    its header, as (line number, heading text or None)."""
    lines = text.splitlines()
    if not markdown:
        start = next((i for i, line in enumerate(lines) if not line.strip()), len(lines))
        return [(n, None) for n in range(start + 2, len(lines) + 1) if lines[n - 1].strip()]
    out: list[tuple[int, str | None]] = []
    fenced, table = False, False
    for n, line in enumerate(lines, start=1):
        if FENCE.match(line):
            fenced, table = not fenced, False
            continue
        if fenced:
            continue
        if match := HEADING.match(line):
            out.append((n, match.group(1)))
            table = False
        elif line.lstrip().startswith("|"):
            if _separator(_cells(line)):
                table = True
            elif table:
                out.append((n, None))
        else:
            table = False
    return out


def other_citations(root: Path) -> set[str]:
    """Q-1217-1 (maintainer answer): the locations that cite a source outside a requirement's
    `Source:` line: an acceptance line's ` (<location>)` into a `Kind: openspec` source, and the
    `Source:` lines of a brief file that carries a `Component:` line (a component's brief)."""
    out: set[str] = set()
    for location in acceptance_lines(root):
        rel = location.partition("#")[0] if "#" in location else location.rpartition(":")[0]
        text = _read(root / rel) if rel.startswith(f"{SOURCES}/") else None
        if text is not None and (header(text) or {}).get("Kind") == OPENSPEC:
            out.add(location)
    folder = root / BRIEFS
    for path in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
        text = _read(path) or ""
        if _line_value(text, "Component") is None:
            continue
        for line in text.splitlines():
            if source := SOURCE_LINE.match(line):
                out.add(source.group(1).strip("`"))
    return out


def kit_requirement(rel: str, req: str, sources: list[str]) -> bool:
    """Brief #1183 (ADR-0502): a block of `docs/requirements.md` numbered REQ-001 to REQ-099, the
    range that file reserves for the kit, with no `Source:` line: it has no project source."""
    match = KIT_RANGE.match(req) if rel == REQUIREMENTS else None
    return match is not None and 1 <= int(match.group(1)) <= 99 and not sources


def requirements(root: Path) -> list[tuple[str, str, list[str]]]:
    """Each requirement block as (file, id or key, its Source: locations), proposed file first,
    without the kit's own requirements (`kit_requirement`)."""
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
    return [block for block in out if not kit_requirement(*block)]


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


# --- build (g): the baseline and the scope changes (rules 20 to 22) -----------------------------

BASELINE = f"{PLAN}/baseline.json"
CHANGES = f"{PLAN}/scope-changes.md"
FULL_HEAD = re.compile(r"^[0-9a-f]{40}$")
CHANGE_HEAD = re.compile(r"^Scope change: (SC-[1-9]\d*)\s*$")
CHANGE_FIELDS = ("What", "Why", "Source", "Effect", "Status")
CHANGE_LINE = re.compile(r"^(What|Why|Source|Effect|Status|Briefs|Approved):[ \t]*(.*?)\s*$")
ADDED = re.compile(
    r"^\+(M[1-9]\d*)/([A-Za-z0-9][A-Za-z0-9._-]*) ([SML]) (\d+(?:\.\d+)?-\d+(?:\.\d+)? hours)$"
)
REMOVED = re.compile(r"^-(M[1-9]\d*)/([A-Za-z0-9][A-Za-z0-9._-]*)$")
PERSON = re.compile(r"^person (\d{4}-\d{2}-\d{2})$")
APPROVED_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (https://\S+)$")
BAD_BRIEFS = "a Briefs: entry is not +M<n>/<key> <size> <low>-<high> hours or -M<n>/<key>"


def _milestone_ok(item: object) -> bool:
    if not isinstance(item, dict) or set(item) != {"id", "briefs", "target", "estimate"}:
        return False
    keys = item["briefs"]
    target = item["target"]
    return (
        isinstance(item["id"], str)
        and MILESTONE.match(f"### {item['id']}") is not None
        and isinstance(keys, list)
        and all(isinstance(k, str) and k for k in keys)
        and len(set(keys)) == len(keys)
        and (target is None or (isinstance(target, str) and real_date(target)))
        and isinstance(item["estimate"], str)
    )


def read_baseline(root: Path) -> tuple[dict[str, list[str]] | None, list[str]]:
    """Rule 20: the baseline's brief keys per milestone, or None, and the problems of its shape."""
    path = root / BASELINE
    if not path.is_file():
        return None, []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        doc = None
    if not isinstance(doc, dict):
        return None, [f"rule 20: {BASELINE}: not a JSON object"]
    fields = {
        "schema": doc.get("schema") == 1 and not isinstance(doc.get("schema"), bool),
        "head": isinstance(doc.get("head"), str) and FULL_HEAD.match(doc["head"]) is not None,
        "date": isinstance(doc.get("date"), str) and real_date(doc["date"]),
        "link": isinstance(doc.get("link"), str) and doc["link"].startswith("https://"),
        "milestones": isinstance(doc.get("milestones"), list),
    }
    out = [f"rule 20: {BASELINE}: {k} is not as rule 20 says" for k, ok in fields.items() if not ok]
    found: dict[str, list[str]] = {}
    for n, item in enumerate(doc["milestones"] if fields["milestones"] else [], start=1):
        if not _milestone_ok(item) or item["id"] in found:
            out.append(f"rule 20: {BASELINE}: milestones[{n}] is not as rule 20 says")
        else:
            found[item["id"]] = list(item["briefs"])
    return (None if out else found), out


def baseline_changed(root: Path, base: str | None) -> list[str]:
    """Rule 20: a baseline the merge base holds is never changed or removed (principle 4). The
    base is `common.resolve_base`'s: a base that does not resolve in CI raises `CheckError`, which
    `run` prints as a failure; only outside CI with no base, or a root outside any git work tree
    (no history to compare), is the comparison not made."""
    if git(root, "rev-parse", "--is-inside-work-tree", check=False).strip() != "true":
        return []
    ref = resolve_base(root, base)
    old = show(root, merge_base(root, ref), BASELINE) if ref else None
    if old is None:
        return []
    path = root / BASELINE
    now = path.read_bytes().decode("utf-8", "replace") if path.is_file() else None
    if now == old:
        return []
    return [f"rule 20: {BASELINE}: changed or removed after it was written"]


def scope_changes(root: Path) -> tuple[list[dict], list[str]]:
    """Rule 21: the blocks of `scope-changes.md` (id, fields, adds, removes, approved) and the
    problems of their shape; rule 22's `Approved:` line shape too."""
    return _changes_of(root, _read(root / CHANGES) or "")


def _changes_of(root: Path, text: str) -> tuple[list[dict], list[str]]:
    out: list[dict] = []
    for line in text.splitlines():
        if head := CHANGE_HEAD.match(line):
            out.append({"id": head[1], "fields": {}, "adds": [], "removes": [], "approved": None})
        elif out and (field := CHANGE_LINE.match(line)):
            out[-1]["fields"].setdefault(field[1], field[2])
    problems: list[str] = []
    seen: set[str] = set()
    for sc in out:
        where = f"{CHANGES}: {sc['id']}"
        fields = sc["fields"]
        if sc["id"] in seen:
            problems.append(f"rule 21: {where}: the number is used twice")
        seen.add(sc["id"])
        problems += [f"rule 21: {where}: no {k}: line" for k in CHANGE_FIELDS if k not in fields]
        if "Status" in fields and fields["Status"] != "proposed":
            problems.append(f"rule 21: {where}: Status: is not proposed")
        source = fields.get("Source")
        if source is not None and not _source_ok(root, source):
            problems.append(f"rule 21: {where}: Source: is neither a location nor person <date>")
        for entry in filter(None, (e.strip() for e in fields.get("Briefs", "").split(";"))):
            if added := ADDED.match(entry):
                sc["adds"].append((added[1], added[2], added[3], added[4]))
            elif removed := REMOVED.match(entry):
                sc["removes"].append((removed[1], removed[2]))
            else:
                problems.append(f"rule 21: {where}: {BAD_BRIEFS}")
                break
        if "Approved" in fields:
            approved = APPROVED_LINE.match(fields["Approved"])
            if approved and real_date(approved[1]):
                sc["approved"] = approved[1]
            else:
                problems.append(f"rule 22: {where}: Approved: is not <date> <https link>")
    return out, problems


def _source_ok(root: Path, source: str) -> bool:
    person = PERSON.match(source)
    if person:
        return real_date(person[1])
    return location_problem(root, source.strip("`")) is None


def merged_approvals(root: Path, changes: list[dict], base: str | None) -> set[str]:
    """Rule 22 with the saved comments (brief #1166, ADR-0496 decision 2): the approved scope
    changes whose whole block the merge base already holds unchanged. Each was approved on the
    pull request that merged it, so a later pull request's comments need not name it again. A new
    or changed block gets nothing here; outside a git work tree, or outside CI with no base, no
    block is carried (the stricter reading); a base that does not resolve in CI raises
    `CheckError` as in rule 20."""
    if git(root, "rev-parse", "--is-inside-work-tree", check=False).strip() != "true":
        return set()
    ref = resolve_base(root, base)
    old = show(root, merge_base(root, ref), CHANGES) if ref else None
    if old is None:
        return set()
    kept = [sc for sc in _changes_of(root, old)[0] if sc["approved"]]
    return {sc["id"] for sc in changes if sc["approved"] and sc in kept}


def approved_ids(
    root: Path, changes: list[dict], comments: list | None, base: str | None = None
) -> set[str]:
    """Rule 22: the scope changes with an `Approved:` line and, with the saved comments, a listed
    approver's `Approve: scope SC-<n> <full head ID>` (never through an agent app) on this pull
    request, or an unchanged approved block of the merge base (`merged_approvals`)."""
    ids = {sc["id"] for sc in changes if sc["approved"]}
    if comments is None:
        return ids
    import reviewers  # noqa: PLC0415 - only a check given --comments reads approvals

    apps = agent_apps(root)
    items = reviewers.confirmed_comments(
        [c for c in comments if isinstance(c, dict)], apps, reviewers.solo_person(root)
    )
    given = {sc for sc, _ in reviewers.scope_approvals(items, reviewers.spec_approvers(root), apps)}
    return ids & (given | merged_approvals(root, changes, base))


def scope_problems(root: Path, comments: list | None = None, base: str | None = None) -> list[str]:
    """Rules 20 to 22 together, in that order."""
    baseline, problems = read_baseline(root)
    problems += baseline_changed(root, base)
    changes, found = scope_changes(root)
    problems += found
    if baseline is None:
        return problems
    approved = approved_ids(root, changes, comments, base)
    adds = {(m, k) for sc in changes if sc["id"] in approved for m, k, _, _ in sc["adds"]}
    removes = {(m, k) for sc in changes if sc["id"] in approved for m, k in sc["removes"]}
    current = {(milestone, key) for key, milestone, _ in briefs(root)}
    for key, milestone, _ in briefs(root):
        if milestone in baseline and key not in baseline[milestone]:
            if (milestone, key) not in adds:
                problems.append(
                    f"rule 22: {BRIEFS}: {key}: under baselined milestone {milestone}, in neither "
                    "the baseline nor an approved scope change"
                )
    for milestone, keys in baseline.items():
        for key in keys:
            if (milestone, key) not in current and (milestone, key) not in removes:
                problems.append(
                    f"rule 22: {BASELINE}: {key}: removed from {milestone} with no approved "
                    "scope change"
                )
    return problems


# --- brief #1219, amendment 176 (ADR-0518): the business scope lock ---------------------------

SCOPE_LOCK = f"{PLAN}/scope-lock.md"
LOCK_REQ = re.compile(r"\bREQ-\d+")
LOCK_FIGURE = re.compile(r"\b(?:builders?|pull[\s-]+requests?|PR\s+rates?)\b", re.I)
LOCK_ROOTS = (
    "docs", "src", "app", "lib", "scripts", "tests", "test", "skills", "config", "kit",
    ".github", ".claude",
)  # fmt: skip
LOCK_EXTENSION = re.compile(r"[A-Za-z0-9_-]\.[A-Za-z0-9]{1,6}$")
LOCK_STRIP = "`'\"()[]<>{}.,;:!?*"
LOCK_WORD = "[A-Za-z0-9._-]"


def _is_path(word: str) -> bool:
    """A file path of the scope lock: a word holding `/` whose last part has a file extension, or
    one starting `./`, `../`, `~/` or a repository folder; a link (`://`) is not a path."""
    word = word.strip(LOCK_STRIP)
    if "://" in word:
        return False
    if re.match(r"^[A-Za-z]:\\", word):
        return True
    if "/" not in word:
        return False
    if word.startswith(("./", "../", "~/")):
        return True
    parts = [p for p in word.split("/") if p]
    if not parts:
        return False
    return parts[0] in LOCK_ROOTS or LOCK_EXTENSION.search(parts[-1]) is not None


def scope_lock_problems(root: Path) -> list[str]:
    """Rule 10 with amendment 176: each line of `docs/plan/scope-lock.md` that holds a
    requirement number, a file path, a brief key or a builder or pull request figure, once per
    kind, naming the line and never its text. Nothing when the file does not exist."""
    text = _read(root / SCOPE_LOCK)
    if text is None:
        return []
    keys = [key for key, _, _ in briefs(root)]
    key_pattern = None
    if keys:
        alternatives = "|".join(map(re.escape, keys))
        key_pattern = re.compile(rf"(?<!{LOCK_WORD})(?:{alternatives})(?![A-Za-z0-9_-]|\.\w)")
    out: list[str] = []
    for n, line in enumerate(text.splitlines(), start=1):
        kinds = [
            ("a requirement number", LOCK_REQ.search(line) is not None),
            ("a file path", any(_is_path(word) for word in line.split())),
            ("a brief key", key_pattern is not None and key_pattern.search(line) is not None),
            ("a builder or pull request figure", LOCK_FIGURE.search(line) is not None),
        ]
        out += [f"rule 10: {SCOPE_LOCK}:{n}: {kind}" for kind, found in kinds if found]
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
        self.resolved = {s for s in self.cited if location_problem(root, s) is None}
        self.resolved |= {s for s in other_citations(root) if location_problem(root, s) is None}
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
        out += self.uncited()
        named = {milestone for _, milestone, _ in self.briefs}
        for milestone in milestones(self.root):
            if milestone not in named:
                out.append(f"rule 10: {MILESTONES}: {milestone}: no brief names this milestone")
        if design_source(self.root):
            out += [f"rule 10: {MILESTONES}: {m}: no Demo: line" for m in undemoed(self.root)]
        return out

    def _file_of(self, location: str) -> str:
        return location.partition("#")[0] if "#" in location else location.rpartition(":")[0]

    def uncited(self) -> list[str]:
        """Brief #1217 answer 1: each source file with no resolving cited location that is not
        listed out of scope, named by its path and never its text."""
        cited = {self._file_of(location) for location in self.resolved}
        skipped = out_of_scope_files(self.root)
        out: list[str] = []
        for path in source_files(self.root):
            rel = path.relative_to(self.root).as_posix()
            if rel not in cited and rel not in skipped:
                out.append(
                    f"{rel} is a source no requirement cites (list it out of scope or cite it)"
                )
        return out

    def file_lines(self) -> list[str]:
        """Brief #1217 answer 2: one `<file>: <a> of <b> headings or rows cited` per source file,
        a unit cited by `<file>#<heading>` or by `<file>:<line>` of its line."""
        out: list[str] = []
        for path in source_files(self.root):
            rel = path.relative_to(self.root).as_posix()
            text = _read(path) if path.suffix in SUFFIXES else None
            units = source_units(text, path.suffix == ".md") if text is not None else []
            a = sum(
                1
                for n, name in units
                if f"{rel}:{n}" in self.resolved
                or (name is not None and f"{rel}#{name}" in self.resolved)
            )
            out.append(f"{rel}: {a} of {len(units)} headings or rows cited")
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
            parts.append(self.scenario_count(facts))
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

    def scenario_count(self, facts: bool) -> str:
        """Build (u): `<a> of <b> scenarios have an acceptance line and <c> a test`, where a test
        marks `REQ-nnn ACn` for criterion n of `REQ-nnn`; `<c>` with `--facts`, else `not read`."""
        accepted = acceptance_lines(self.root)
        lines = [accepted.get(location, []) for location, _ in self.scenarios or []]
        a = sum(1 for found in lines if found)
        head = f"{a} of {len(lines)} scenarios have an acceptance line and"
        if not facts:
            return f"{head} a test: {NOT_READ}"
        marked = {(m["req"], m["ac"]) for m in ac_markers_for(self.root) if m["ac"]}
        c = sum(
            1
            for found in lines
            if any(
                REQ_KEY.match(req) and n is not None and (req, f"AC{n}") in marked
                for req, n in found
            )
        )
        return f"{head} {c} a test"

    def matches(self) -> list[tuple[str, list[str]]]:
        """Build (u): each scenario and the screen headings its steps name (a design source)."""
        if self.scenarios is None or not design_source(self.root):
            return []
        return [
            (loc, [s for s in self.screens if names_screen(steps, s)])
            for loc, steps in self.scenarios
        ]

    def unmatched(self) -> list[str]:
        """Build (u): `unmatched scenario: <location>` and `unmatched screen: <screen>` lines."""
        matches = self.matches()
        if not matches:
            return []
        named = {s for _, found in matches for s in found}
        out = [f"unmatched scenario: {loc}" for loc, found in matches if not found]
        names: dict[str, bool] = {}
        for screen in self.screens:
            name = screen.partition("#")[2].partition("/")[0]
            names[name] = names.get(name, False) or screen in named
        return out + [f"unmatched screen: {name}" for name, hit in names.items() if not hit]

    def screen_lines(self) -> list[str]:
        """Build (u): each scenario's screens, printed with `--trace`."""
        return [
            f"info plan: scenario {loc}: " + (", ".join(found) or "names no screen")
            for loc, found in self.matches()
        ]

    def _tested(self, facts: bool) -> set[tuple[str, str]] | None:
        """The `(REQ-nnn, ACn)` pairs a test marks, read with `--facts` only (ADR-0474)."""
        if not facts:
            return None
        return {(m["req"], m["ac"]) for m in ac_markers_for(self.root) if m["ac"]}

    @staticmethod
    def _has_test(found: list[tuple[str, int | None]], marked: set[tuple[str, str]]) -> bool:
        return any(REQ_KEY.match(r) and n is not None and (r, f"AC{n}") in marked for r, n in found)

    def rule_lines(self, facts: bool) -> list[str]:
        """Amendment 167 item 1: the rules count and each rule with no acceptance line or test."""
        found = blocks(self.root)
        if not any(statement for _, statement, _ in found):
            return []
        marked = self._tested(facts)
        total, named, tested, missing = 0, 0, 0, []
        for key, statement, lines in found:
            for n in range(1, len(rules_of(statement)) + 1):
                total += 1
                hits = [(key, c) for c, text in lines if f"r{n}" in marked_rules(text)]
                if not hits:
                    missing.append(f"info plan: rule {key}.r{n}: no acceptance line")
                    continue
                named += 1
                if marked is not None and self._has_test(hits, marked):
                    tested += 1
                elif marked is not None:
                    missing.append(f"info plan: rule {key}.r{n}: no test")
        head = f"info plan: {named} of {total} rules have an acceptance line and"
        count = f"{head} a test: {NOT_READ}" if marked is None else f"{head} {tested} a test"
        return [count, *missing]

    def access_lines(self, facts: bool) -> list[str]:
        """Amendment 167 item 2: the access cells with a test, and each cell with none."""
        cells = access_cells(self.root)
        if cells is None:
            return []
        marked = self._tested(facts)
        lines = [(key, c, text) for key, _, found in blocks(self.root) for c, text in found]
        tested, missing = 0, []
        for cell, _ in cells:
            hits = [(key, c) for key, c, text in lines if cell in marked_cells(text)]
            if not hits:
                missing.append(f"info plan: access {cell}: no acceptance line")
            elif marked is not None and self._has_test(hits, marked):
                tested += 1
            elif marked is not None:
                missing.append(f"info plan: access {cell}: no test")
        if marked is None:
            return [f"info plan: {len(cells)} access cells; with a test: {NOT_READ}", *missing]
        return [f"info plan: {tested} of {len(cells)} access cells have a test", *missing]

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
    comments: list | None = None,
    base: str | None = None,
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
        lines = plan.trace(facts is not None) + plan.file_lines() + plan.screen_lines()
        lines += plan.rule_lines(facts is not None) + plan.access_lines(facts is not None)
        print("\n".join(lines))
    problems += plan.problems() + scope_lock_problems(root) + scope_problems(root, comments, base)
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    for line in plan.unmatched():
        print(line)
    print(("plan: " if problems else "ok plan: ") + plan.coverage(facts is not None))
    return 1 if problems else 0


def _json(path: str, option: str) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise SystemExit(f"check_plan.py: {option}: not a readable JSON file") from None


OPTIONS = ("--root", "--facts", "--numbers", "--comments", "--base")


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    values: dict[str, str] = {}
    trace = False
    while args:
        arg = args.pop(0)
        if arg == "--trace":
            trace = True
        elif arg in OPTIONS and args and arg not in values:
            values[arg] = args.pop(0)
        else:
            print(USAGE, file=sys.stderr)
            return 2
    try:
        facts = _json(values["--facts"], "--facts") if "--facts" in values else None
        numbers = _json(values["--numbers"], "--numbers") if "--numbers" in values else {}
        comments = _json(values["--comments"], "--comments") if "--comments" in values else None
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
    if comments is not None and not isinstance(comments, list):
        print("check_plan.py: --comments: not a list of comments", file=sys.stderr)
        return 2
    root = Path(values["--root"]) if "--root" in values else None
    base = values.get("--base")
    return run(NAME, lambda: cmd_check(root or repo_root(), trace, facts, numbers, comments, base))


if __name__ == "__main__":
    sys.exit(main())
