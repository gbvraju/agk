# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `parts` step (SPEC-0076 rule 8; brief #2071, ADR-0867; REQ-083 AC4).

Run by `run_gates.py` after `pins` where a work type is declared. Per runtime of `pins.runtimes_of`
it reads the parts record `docs/parts.md` (one `## <runtime>` section each with two runtimes, every
row with one), the build files through `pins.declared` and the lock through `pins.locked`, names
compared after `pins.norm`, and finds: a direct dependency that neither the record nor the chosen
option's `Parts:` names (`Q-PD-2`); a record part missing from its build file, or at another
version than the build file or the lock; a row with an empty required column; a second part for
one need with no `Decision: <need>` line; a health `read` date older than `parts.max_age_months`.
Each line names the rule and the component class, never a name or a version (principle 8).
Under `[parts] record = "required"` the findings fail, but a stale date fails only a change that
touches the record, a build file or a lock (`run_gates.touched`), and warns otherwise; under
`optional` (no table) every finding is a warning (`notes`, printed `warn parts:`). Files only.
`confirmed(root)` is the one reader of the record's last `Confirmed by:` line (rule 3).
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

from common import CheckError  # noqa: E402
from parts_record import COLUMNS, RECORD  # noqa: E402

import config  # noqa: E402
from gates import glossary, pins  # noqa: E402

RULE = "SPEC-0076 rule 8: the build files and the parts record are not in step"
NOTED = "setting: parts.record"
NO_RECORD = "no parts record"
NO_READER = "no reader for this stack"
NOT_READ = "the build files are not read"
REQUIRED = ("Why", "Alternatives considered", "Licence", "Health (date)", "For the business")
STDLIB = "stdlib"
UNNAMED = "a direct dependency the record does not name"
STALE = "a record row's health date is older than the limit"
READ = re.compile(r"\bread (\d{4}-\d{2}-\d{2})\b")
CONFIRMED = re.compile(r"^Confirmed by:\s*(.+?)\s*\((\d{4}-\d{2}-\d{2})\)\s*$")
SEPARATOR = re.compile(r"^:?-+:?$")
Finding = tuple[str, str, str]  # (what, component class, the file it is held to)


def applies(root: Path) -> bool:
    return pins.applies(root)


def settings(root: Path) -> dict | str:
    """`config.parts_settings`, or the refusal's line (`the [parts] table is refused ...`)."""
    try:
        return config.parts_settings(Path(root))
    except CheckError as exc:
        return str(exc)


def skipped(root: Path) -> str | None:
    """Answer 2's reasons, in order; None (the step runs) also when the table is refused."""
    root = Path(root)
    if isinstance(settings(root), str):
        return None
    chosen = pins.chosen_parts(pins.records(root) or [])
    if not chosen:
        return pins.NO_STACK
    found = pins.runtimes_of(root)
    if found is None:
        return NO_READER
    if not (root / RECORD).is_file():
        return NO_RECORD
    if pins.waiting(root):
        return pins.NO_FOUNDATION
    for one in found:
        try:
            if one.split:
                return NOT_READ
            pins.declared(root / one.folder, one.row[3], one.build)
        except (pins.Unreadable, OSError, UnicodeDecodeError, ValueError, AttributeError):
            return NOT_READ
    return None


def sections(text: str) -> tuple[dict[str, list[dict[str, str]]], dict[str, set[str]]] | None:
    """(rows by section, `Decision:` needs by section) of the record; None with no table of the
    nine columns. A row with fewer cells reads the missing ones as empty."""
    chunks: dict[str, list[str]] = {"": []}
    current = ""
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            chunks.setdefault(current, [])
        else:
            chunks[current].append(line)
    rows: dict[str, list[dict[str, str]]] = {}
    decisions: dict[str, set[str]] = {}
    seen = False
    for name, lines in chunks.items():
        body = "\n".join(lines)
        for table in glossary.tables(body):
            if tuple(glossary.cells(table[0])) != COLUMNS:
                continue
            seen = True
            for line in table[1:]:
                cells = glossary.cells(line)
                if all(SEPARATOR.match(c) for c in cells):
                    continue
                cells += [""] * (len(COLUMNS) - len(cells))
                rows.setdefault(name, []).append(dict(zip(COLUMNS, cells, strict=False)))
        said = [
            ln.strip()[len("Decision:") :] for ln in lines if ln.strip().startswith("Decision:")
        ]
        decisions[name] = {s.split(":", 1)[0].strip().casefold() for s in said}
    return (rows, decisions) if seen else None


def _months(old: datetime.date, today: datetime.date) -> int:
    return (today.year - old.year) * 12 + today.month - old.month - (today.day < old.day)


def _stale(health: str, limit: int, today: datetime.date) -> bool:
    match = READ.search(health)
    try:
        read = datetime.date.fromisoformat(match.group(1)) if match else None
    except ValueError:
        return False
    return read is not None and _months(read, today) > limit


def _key(one: pins.Runtime) -> str:
    return next(k for k, v in pins.STACKS.items() if v == one.row)


def runtime(root: Path, one: pins.Runtime, found: tuple, limit: int, today: datetime.date):
    """(findings, stale findings, the files of this runtime) of one runtime, in its folder."""
    rows, decisions = found
    if len(pins.runtimes_of(root) or []) > 1:
        names = [n for n in rows if pins.RUNTIME_NAMES.get(n.casefold()) == _key(one)]
    else:
        names = list(rows) + [n for n in decisions if n not in rows]
    mine = [r for n in names for r in rows.get(n, [])]
    decided = {d for n in names for d in decisions.get(n, set())}
    _, _, lock_file, reader = one.row
    base = root / one.folder
    deps = [(n, v, one.at(h)) for n, v, h in pins.declared(base, reader, one.build)]
    try:
        have = pins.locked(reader, (base / lock_file).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        have = {}  # `pins` fails the lock; the record is compared with the build file only
    named = {pins.norm(r["Part"]) for r in mine} | {pins.norm(p[0]) for p in one.option}
    out: list[Finding] = [(UNNAMED, "dependency", held) for n, _, held in deps if n not in named]
    versions = {n: v for n, v, _ in reversed(deps)}
    stale: list[Finding] = []
    for r in mine:
        if any(not r[c] for c in REQUIRED):
            out.append(("a record row is empty in a required column", "record row", RECORD))
        if r["Part"].casefold() == STDLIB:
            continue
        name = pins.norm(r["Part"])
        if name not in versions:
            out.append(("a record part is missing from its build file", "record part", RECORD))
            continue
        if versions[name] is not None and versions[name] != r["Version"]:
            out.append(("a record version differs from the build file", "record part", RECORD))
        if name in have and have[name] != r["Version"]:
            out.append(("a record version differs from the lock", "record part", RECORD))
        if _stale(r["Health (date)"], limit, today):
            stale.append((STALE, "record row", RECORD))
    needs = [r["Need"].casefold() for r in mine]
    twice = {n for n in needs if needs.count(n) > 1} - decided
    out += [("a second part for one need has no Decision: line", "record row", RECORD)] * len(twice)
    files = {RECORD, one.at(one.build), one.at(lock_file)} | {h for _, _, h in deps}
    return out, stale, files


def evaluate(root: Path, today: datetime.date | None = None) -> tuple[list[Finding], list[Finding]]:
    """(failures, warnings), each sorted; both empty when the step does not run."""
    root = Path(root)
    found = settings(root)
    if isinstance(found, str) or skipped(root):
        return [], []
    today = today or datetime.datetime.now(datetime.UTC).date()
    try:
        record = sections((root / RECORD).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        record = None
    if record is None:
        out = [("the parts record cannot be read", "record", RECORD)]
        return (out, []) if found["record"] == "required" else ([], out)
    fails: list[Finding] = []
    stale: list[Finding] = []
    files: set[str] = set()
    for one in pins.runtimes_of(root) or []:
        got, old, held = runtime(root, one, record, found["max_age_months"], today)
        fails, stale, files = fails + got, stale + old, files | held
    if found["record"] != "required":
        return [], sorted(fails + stale)
    if stale and _touches(root, files):
        return sorted(fails + stale), []
    return sorted(fails), sorted(stale)


def _touches(root: Path, files: set[str]) -> bool:
    """Whether the change touches one of the files; never with no base or no `.git`."""
    import run_gates  # noqa: PLC0415 - the runner imports this module by name

    try:
        changed = run_gates.touched(root)
    except CheckError:
        return False
    return bool(changed and changed & files)


def line(what: str, cls: str) -> str:
    return f"{RULE}: {what} (component class: {cls})"


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """The runner's interface: (the rule and component class, the file's path class) of each."""
    found = settings(root)
    if isinstance(found, str):
        what, _, where = found.rpartition(" (")
        return [(what, where.rstrip(")"))]
    return sorted({(line(w, c), f) for w, c, f in evaluate(root)[0]})


def notes(root: Path, playbook: dict[str, Any]) -> list[str]:
    """Answer 3: the warnings, each `<rule>: <finding> (component class) (path class)`."""
    return sorted({f"{line(w, c)} (path class: {f})" for w, c, f in evaluate(root)[1]})


def confirmed(root: Path) -> bool:
    """Rule 3: the record's last line is `Confirmed by: <name> (<YYYY-MM-DD>)`, the name not a
    `TODO(` mark and the date a real date."""
    try:
        text = (Path(root) / RECORD).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    lines = [ln for ln in text.splitlines() if ln.strip()]
    match = CONFIRMED.match(lines[-1].strip()) if lines else None
    if not match or match.group(1).startswith("TODO("):
        return False
    try:
        datetime.date.fromisoformat(match.group(2))
    except ValueError:
        return False
    return True


# --- the weekly lines (SPEC-0076 rule 12; brief #2076, ADR-0866) ----------------------------------

DETAIL = 10  # detail lines at most, then `parts: and <k> more`
NO_SCAN = "flagged unknown (no advisory scan)"  # Q-PI-3: never 0 while no scan result is read
RELEASE = re.compile(r"\blast release ([^\s;,)]+)")
GONE = ("deprecated", "archived")
OLDER = "older than [parts] max_age_months"


def _over(day: datetime.date, today: datetime.date, months: int) -> bool:
    """`packs._over`'s count: calendar months, the day ignored, over and never at."""
    return (today.year - day.year) * 12 + today.month - day.month > months


def _week(name: str, r: dict[str, str], limit: int, today: datetime.date) -> tuple[list, bool]:
    """((kind, line) of each detail of one row, whether its health is not read)."""
    cell = r["Health (date)"].strip()
    part = f"{r['Part']} ({name or 'record'})"
    if cell.casefold().startswith("not read"):
        return [], True
    out = []
    found = RELEASE.search(cell)
    if found:
        try:
            last = datetime.date.fromisoformat(found.group(1))
        except ValueError:
            return [], True  # a date out of form: never old (answer 6)
        if _over(last, today, limit):
            out.append(("old", f"parts: old {part} released {last}, {OLDER}"))
    status = cell.split(";", 1)[0].strip().casefold()
    if status in GONE:
        read = READ.search(cell)
        when = f"read {read.group(1)}" if read else "no read date"
        out.append(("gone", f"parts: deprecated {part} recorded {status} ({when})"))
    return out, False


def report_lines(root: Path, today: datetime.date | None = None) -> list[str]:
    """Answer 1: the weekly report's `parts:` lines from the record's rows, in record order: the
    old, the deprecated or archived, the unread count, then one summary whose flagged count is
    unknown while no advisory scan runs. Every refusal is one line; files only, never a failure."""
    root = Path(root)
    if not pins.applies(root):
        return [f"parts: not run ({pins.NO_STACK})"]
    found = settings(root)
    if isinstance(found, str):
        named = re.search(r"\(setting: [^)]+\)", found)
        return [f"parts: unknown {named.group(0) if named else '(setting: parts)'}"]
    if not (root / RECORD).is_file():
        return [f"parts: not run ({NO_RECORD})"]
    try:
        record = sections((root / RECORD).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        record = None
    if record is None:
        return [f"parts: unknown (path class: {RECORD})"]
    today = today or datetime.datetime.now(datetime.UTC).date()
    details: list[tuple[str, str]] = []
    total = unread = 0
    for name, rows in record[0].items():
        for r in rows:
            total += 1
            got, blank = _week(name, r, found["max_age_months"], today)
            details += got
            unread += blank
    lines = [text for _, text in details]
    if unread:
        lines.append(f"parts: health not read {unread} rows")
    if len(lines) > DETAIL:
        lines = lines[:DETAIL] + [f"parts: and {len(lines) - DETAIL} more"]
    old = sum(kind == "old" for kind, _ in details)
    gone = sum(kind == "gone" for kind, _ in details)
    return lines + [f"parts: {total} recorded; old {old}; deprecated {gone}; {NO_SCAN}"]
