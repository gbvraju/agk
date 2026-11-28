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

    python3 scripts/agk/gates/parts.py --harvest --at YYYY-MM-DD [--root DIR]

Rule 10 (brief #2074, ADR-0864): `--harvest` drafts the record of an adopted project once from
the build files and locks `front_door.detect_facts` finds, every row `inferred`; `counts` holds
every finding per file to `config/agk-baseline/parts.txt`, and an `inferred` row, an `unassigned`
need or a `not recorded` or `not read` column counts as an empty one. Exit 0, 1 refused, 2 usage.
"""

from __future__ import annotations

import datetime
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import common  # noqa: E402
from common import CheckError, utf8_output  # noqa: E402
from parts_record import COLUMNS, RECORD  # noqa: E402

import config  # noqa: E402
from gates import glossary, licences, pins  # noqa: E402

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
# brief #2074 (ADR-0864): the harvest's words, and the step's baseline interface
INFERRED = "inferred: not recorded"
FROM_STACK = "inferred: from the stack record"
NOT_RECORDED = "not recorded"
UNASSIGNED = "unassigned"
TOUCHED = "an inferred row's version changed; it needs its full row"
HELD = 1
USAGE = "usage: python3 scripts/agk/gates/parts.py --harvest --at YYYY-MM-DD [--root DIR]"
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def incomplete(r: dict[str, str]) -> bool:
    """A required column empty, `not recorded` or `not read (...)`, an `inferred` reason or an
    `unassigned` need (brief #2074 answer 2)."""
    empty = any(not r[c] or r[c] == NOT_RECORDED or r[c].startswith("not read (") for c in REQUIRED)
    return empty or r["Why"].startswith("inferred") or r["Need"] == UNASSIGNED


def based(root: Path) -> dict[str, str]:
    """Part -> version of each `inferred` row of the record at the merge base; {} with none."""
    try:
        base = common.resolve_base(root) if (root / ".git").exists() else None
        text = common.show(root, common.merge_base(root, base), RECORD) if base else None
    except CheckError:
        return {}
    found = sections(text or "")
    rows = [r for rs in (found or ({}, {}))[0].values() for r in rs]
    return {pins.norm(r["Part"]): r["Version"] for r in rows if r["Why"].startswith("inferred")}


def runtime(
    root: Path,
    one: pins.Runtime,
    found: tuple,
    limit: int,
    today: datetime.date,
    was: dict[str, str] | None = None,
):
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
    held = {n: h for n, _, h in deps}
    for r in mine:
        name = pins.norm(r["Part"])
        if r["Why"].startswith("inferred") and (was or {}).get(name, r["Version"]) != r["Version"]:
            out.append((TOUCHED, "record row", held.get(name, one.at(one.build))))
        if incomplete(r):
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
    needs = [r["Need"].casefold() for r in mine if r["Need"] != UNASSIGNED]
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
    base = based(root)
    for one in pins.runtimes_of(root) or []:
        got, old, held = runtime(root, one, record, found["max_age_months"], today, base)
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


def counts(root: Path, playbook: dict[str, Any]) -> dict[str, int]:
    """Brief #2074 answer 2: every finding, failure or warning, per file it is held to."""
    out: dict[str, int] = {}
    fails, warns = evaluate(root)
    for _, _, held in fails + warns:
        out[held] = out.get(held, 0) + 1
    return out


def unheld(root: Path) -> bool:
    """A refused `[parts]` table fails as it is; no baseline is written for it."""
    return isinstance(settings(root), str)


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


def _dev(base: Path, reader: str, build: str) -> set[str]:
    """The names of `devDependencies` or of every `optional-dependencies` group (`Q-PG-2`)."""
    text = (base / build).read_text(encoding="utf-8")
    if reader == "npm":
        return {pins.norm(n) for n in json.loads(text).get("devDependencies") or {}}
    if build == pins.REQUIREMENTS:
        return set()
    groups = (tomllib.loads(text).get("project") or {}).get("optional-dependencies") or {}
    return {r[0] for g in groups.values() for s in g if (r := pins.requirement(s))}


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def harvestable(root: Path) -> tuple[list[tuple[str, str, str]], int]:
    """(stack key, folder, build file from the root) of each detected runtime `pins` reads, and
    the number of detected stacks with no reader; ([], 0) when `detect` cannot read the root."""
    import front_door  # noqa: PLC0415 - front_door reads this module's facts lazily too

    try:
        facts = front_door.detect_facts(Path(root), Path(__file__).resolve().parents[3])
    except (front_door.Refusal, OSError, ValueError):
        return [], 0
    return front_door.parts_runtimes(facts["stack"]["rows"], pins)


def harvest(root: Path, at: str) -> tuple[int, list[str]]:
    """Rule 10's draft, written once; (exit code, lines to print)."""
    import parts_record  # noqa: PLC0415

    root = Path(root)
    if (root / RECORD).exists():
        why = "it is edited by hand, never rewritten (path class: docs/)"
        return 1, [f"refused: SPEC-0076 rule 10: {RECORD} exists; {why}; nothing is written"]
    runtimes, other = harvestable(root)
    lines = [f"parts: {NO_READER}"] if other else []
    stack = {pins.norm(p[0]): p for p in pins.chosen_parts(pins.records(root) or []) or []}
    try:
        catalogues = parts_record._catalogue(root)[1]
    except parts_record.Refused:
        catalogues = {}
    out: dict[str, list[list[str]]] = {}
    for key, folder, build in runtimes:
        (_, _, lock_file, reader), base = pins.STACKS[key], root / folder
        name = build.rsplit("/", 1)[-1]
        try:
            deps, dev = pins.declared(base, reader, name), _dev(base, reader, name)
        except (pins.Unreadable, OSError, UnicodeDecodeError, ValueError, AttributeError):
            lines.append(f"parts: not harvested {name}: cannot be read")
            continue
        lock = _read(base / lock_file)
        try:
            have = pins.locked(reader, lock) if lock else {}
            found = licences.components(reader, lock, list(stack.values())) if lock else []
        except (ValueError, AttributeError):
            have, found = {}, []
        licence = {c[1]: c[3] for c in found}
        listed = catalogues.get(pins.STACKS[key][0], [])
        cat = {pins.norm(str(r.get("name"))): r.get("need") for r in listed}
        rows = out.setdefault(key, [])
        for dep, version, _ in deps:
            if dep in {r[1] for r in rows}:
                continue
            why = FROM_STACK if dep in stack else INFERRED
            got = licence.get(dep) or (stack[dep][2] if dep in stack else "") or NOT_RECORDED
            kind = "dev" if dep in dev else "runtime"
            ver = have.get(dep) or version or NOT_RECORDED
            rows.append([cat.get(dep) or UNASSIGNED, dep, ver, kind, why, NOT_RECORDED, got])
            rows[-1] += [f"not read ({at})", NOT_RECORDED]
    if not out:
        return 1, [*lines, "parts: nothing harvested; nothing is written"]
    template = _read(parts_record.TEMPLATE) or "# Parts\n"
    text = [template.split("\n## ", 1)[0].rstrip("\n"), ""]
    for key, rows in out.items():
        text += [f"## {key}", "", "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
        text += ["| " + " | ".join(c.replace("|", "/") for c in r) + " |" for r in rows] + [""]
    text += ["Questions for the person:", "", f"Confirmed by: not yet (harvested {at})", ""]
    (root / RECORD).parent.mkdir(parents=True, exist_ok=True)
    with (root / RECORD).open("x", encoding="utf-8") as handle:  # never over an existing file
        handle.write("\n".join(text))
    rows = [r for rs in out.values() for r in rs]
    named = sum(r[0] != UNASSIGNED for r in rows)
    said = (
        f"parts: harvested {len(rows)} rows ({named} needs named, {len(rows) - named} unassigned)"
    )
    return 0, [*lines, said, "protected: none"]


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    opts = dict(zip(args[1::2], args[2::2], strict=False))
    ok = args[:1] == ["--harvest"] and len(args) % 2 == 1 and set(opts) <= {"--at", "--root"}
    try:
        ok = (
            ok and bool(DAY.match(opts["--at"])) and bool(datetime.date.fromisoformat(opts["--at"]))
        )
    except (KeyError, ValueError):
        ok = False
    if not ok:
        print(USAGE, file=sys.stderr)
        return 2
    code, lines = harvest(Path(opts.get("--root", ".")), opts["--at"])
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
