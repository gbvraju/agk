# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The parts catalogue check (SPEC-0076 rules 4 and 5; REQ-083 AC1; brief #2068, ADR-0858).
Installed: `kit/manifest.json` lists it in `verbatim`.

The needs catalogue is `config/parts/needs.toml` (`format = 1`, one `[[needs]]` per need with
`id`, `text` and `signals`); a stack catalogue is `config/parts/<stack>.toml` (`format = 1`, one
`[[parts]]` per row with `need`, `name`, `pick` (`recommended` or `alternative`, `Q-PA-1`), `when`,
`trade_offs`, `licence`, `source` and `reviewed`, never a `version`). `findings(root, files,
stacks)` takes the `(layer, path)` files in their reading order and the stack names from its
caller (`check_playbooks.findings`, through `packs.files` and `playbook_format.stacks`, `Q-PA-4`)
and gives one line per problem, `rule 4|5: <path class>: <what> (key: <key>)`, never a value.
Run alone it reads `DIR/config/parts/` only and prints those lines as `FAIL parts-catalogue:` or
`ok parts-catalogue (<n> needs, <m> stack catalogues)`. Standard library and `common.py` only;
reads files only: no network, no model.

    python3 scripts/agk/check_parts_catalogue.py [--root DIR]

Exit 0 ok, 1 a problem, 2 usage.
"""

from __future__ import annotations

import datetime
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import repo_root, run, utf8_output

NAME = "parts-catalogue"
FOLDER = "config/parts"
NEEDS = "needs.toml"
OWN_LAYERS = ("agk-core", "project")  # `packs.CORE` and `packs.PROJECT`; any other is a pack id
SLUG = re.compile(r"^[a-z][a-z0-9-]*$")
SOURCE = re.compile(r"^https?://\S+ \(accessed (\d{4}-\d{2}-\d{2})\)$")  # playbook_format's
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SPDX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]*$")  # one SPDX id, never an expression
PICKS = ("recommended", "alternative")
NEED_KEYS = ("id", "text", "signals")
PACK_KEYS = ("source", "basis")  # a pack's entry may carry them (SPEC-0077 rule 3)
PART_KEYS = ("need", "name", "pick", "when", "trade_offs", "licence", "source", "reviewed")


def label(layer: str, path: Path) -> str:
    """The path class a line names: the kit's or project's file, or the pack's folder."""
    return f"{FOLDER}/{path.name}" if layer in OWN_LAYERS else f"config/packs/{layer}"


def _date(text: str) -> bool:
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _load(path: Path, out: list[str], cls: str) -> dict | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        out.append(f"{cls}: the file is not TOML (key: file)")
        return None


def _rows(data: dict, section: str, out: list[str], cls: str) -> list[dict]:
    """The top-level form (`format = 1`, only SECTION beside it); its rows that are tables."""
    if "format" not in data:
        out.append(f"{cls}: a key is missing (key: format)")
    elif type(data["format"]) is not int or data["format"] != 1:
        out.append(f"{cls}: format is not 1 (key: format)")
    for key in sorted(set(data) - {"format", section}):
        out.append(f"{cls}: a key is unknown (key: {key})")
    rows = data.get(section, [])
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        out.append(f"{cls}: a value has the wrong type (key: {section})")
        return []
    return rows


def _keys(row: dict, keys: tuple[str, ...], extra: tuple[str, ...], section: str) -> list[str]:
    what = [f"a key is missing (key: {section}.{k})" for k in keys if k not in row]
    return what + [
        f"a key is unknown (key: {section}.{k})"
        for k in sorted(row)
        if k not in keys and k not in extra and k != "version"
    ]


def _text(value: Any, section: str, key: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return f"a value has the wrong type (key: {section}.{key})"
    if "\n" in value:
        return f"a value is out of form (key: {section}.{key})"
    return None


def need_problems(row: dict, extra: tuple[str, ...]) -> list[str]:
    """Rule 4: one `[[needs]]` row's keys, types and form."""
    what = _keys(row, NEED_KEYS, extra, "needs")
    if "version" in row:
        what.append("a key is unknown (key: needs.version)")
    if "id" in row:
        if not isinstance(row["id"], str):
            what.append("a value has the wrong type (key: needs.id)")
        elif not SLUG.match(row["id"]):
            what.append("a value is out of form (key: needs.id)")
    if "text" in row and (line := _text(row["text"], "needs", "text")):
        what.append(line)
    signals = row.get("signals", ["-"])
    if not isinstance(signals, list) or not signals:
        what.append("a value has the wrong type (key: needs.signals)")
    elif any(_text(s, "needs", "signals") for s in signals):
        what.append("a value has the wrong type (key: needs.signals)")
    return what


def part_problems(row: dict, ids: set[str]) -> list[str]:
    """Rule 5: one `[[parts]]` row's keys, types and form."""
    what = _keys(row, PART_KEYS, (), "parts")
    if "version" in row:
        what.append("a row holds a version (key: parts.version)")
    for key in PART_KEYS:
        if key in row and (line := _text(row[key], "parts", key)):
            what.append(line)
    value = lambda key: row[key] if isinstance(row.get(key), str) else None  # noqa: E731
    if value("need") is not None and value("need") not in ids:
        what.append("a row names a need no needs id names (key: parts.need)")
    if value("pick") is not None and value("pick") not in PICKS:
        what.append("a value is out of form (key: parts.pick)")
    if value("licence") is not None and not SPDX.match(value("licence")):
        what.append("a value is out of form (key: parts.licence)")
    found = SOURCE.match(value("source") or "-")
    if value("source") is not None and not (found and _date(found.group(1))):
        what.append("a value is out of form (key: parts.source)")
    reviewed = value("reviewed")
    if reviewed is not None and not (DATE.match(reviewed) and _date(reviewed)):
        what.append("a value is out of form (key: parts.reviewed)")
    return what


def _counts(rows: list[dict]) -> list[str]:
    """Rule 5: per need in one file, one `recommended`, two `alternative`, each name once."""
    what: list[str] = []
    seen: dict[tuple, int] = {}
    for row in rows:
        need, name, pick = (row.get(k) for k in ("need", "name", "pick"))
        if not all(isinstance(v, str) for v in (need, name, pick)):
            continue
        seen[(need, pick)] = seen.get((need, pick), 0) + 1
        if seen[(need, pick)] == 2 and pick == "recommended":
            what.append("a need has more than one recommended row (key: parts.pick)")
        if seen[(need, pick)] == 3 and pick == "alternative":
            what.append("a need has more than two alternative rows (key: parts.pick)")
        seen[(need, "name", name)] = seen.get((need, "name", name), 0) + 1
        if seen[(need, "name", name)] == 2:
            what.append("a name is used twice for one need (key: parts.name)")
    return what


def findings(root: Path, files: list[tuple[str, Path]], stacks: list[str] | None) -> list[str]:
    """The problems of FILES, the needs files first (rule 4), then each stack catalogue (rule
    5) against the needs ids and STACKS (None: no stack name is known). ROOT is unused: every
    path is given (kept for the form of the other checks of the step)."""
    del root
    out: list[str] = []
    ids: set[str] = set()
    for layer, path in files:
        if path.name != NEEDS:
            continue
        cls = f"rule 4: {label(layer, path)}"
        data = _load(path, out, cls)
        extra = () if layer in OWN_LAYERS else PACK_KEYS
        for row in _rows(data, "needs", out, cls) if data is not None else []:
            out += [f"{cls}: {line}" for line in need_problems(row, extra)]
            if isinstance(row.get("id"), str):
                if row["id"] in ids:
                    out.append(f"{cls}: a need id is used twice (key: needs.id)")
                ids.add(row["id"])
    for layer, path in files:
        if path.name == NEEDS:
            continue
        cls = f"rule 5: {label(layer, path)}"
        if path.stem not in (stacks or []):
            out.append(f"{cls}: the file names no stack (key: file)")
        data = _load(path, out, cls)
        rows = _rows(data, "parts", out, cls) if data is not None else []
        for row in rows:
            out += [f"{cls}: {line}" for line in part_problems(row, ids)]
        out += [f"{cls}: {line}" for line in _counts(rows)]
    return list(dict.fromkeys(out))


def _stacks(root: Path) -> list[str] | None:
    path = root / "config" / "stack-signals.toml"
    if not path.is_file():
        return None
    try:
        rows = tomllib.loads(path.read_text(encoding="utf-8")).get("stack")
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None
    rows = rows if isinstance(rows, list) else []
    return [r["name"] for r in rows if isinstance(r, dict) and isinstance(r.get("name"), str)]


def cmd_check(root: Path) -> int:
    files = [("agk-core", p) for p in sorted((root / FOLDER).glob("*.toml"))]
    found = findings(root, files, _stacks(root))
    for line in found:
        print(f"FAIL {NAME}: {line}")
    if found:
        return 1
    needs = [p for _, p in files if p.name == NEEDS]
    count = sum(len(tomllib.loads(p.read_text(encoding="utf-8")).get("needs", [])) for p in needs)
    print(f"ok {NAME} ({count} needs, {len(files) - len(needs)} stack catalogues)")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if root is None and args:
        print("usage: check_parts_catalogue.py [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
