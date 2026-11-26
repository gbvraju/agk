# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The domain pack check (SPEC-0074 rule 2; REQ-081 AC1; brief #1935, ADR-0804). Installed:
`kit/manifest.json` lists it in `verbatim`.

A domain pack is `config/domains/<slug>.toml`: public, cited knowledge of one domain (its terms,
actors, regulations, constraints, questions and gates), never a customer's specifics. `findings`
gives one line per problem of each pack, `rule 2: config/domains/<file>: <what> (key: <key>)`, never
a value, then the lines of the project domain model, `docs/domain/`, that `domain_model.findings`
gives (rule 7, ADR-0810). `check_playbooks.findings` adds them, so the governance step `playbooks`
prints them as `FAIL playbooks:` lines; run alone (`--root DIR`) it prints `ok domains (<n> packs)`
or `ok domains (none)`. An `as_of` older than `[domain] stale_months` is a `warn domains:` line on
stderr and never fails (rule 14). Reads files only: no network, no model, nothing written. In a
clean layout the project's pack is read first by name, then the plugin's.

The one composition (SPEC-0074 rules 3 and 4, amendment 240 to SPEC-0048 rule 23; REQ-081 AC2;
brief #1936, ADR-0805): `compose(root, layers)` appends to the playbook's layers the packs of
`[domain] packs` in `order`: the shipped packs in the person's order, each followed by its
jurisdiction layers (`<domain>-<region>`, in list order, even when listed before it), then the
project's own packs (a name `SHIPPED` does not hold). `check_playbooks.composed` judges every layer
by its one `_weakened`. `items` keeps each `[[discovery]]`, `[[terms]]` and `[[acceptance]]` item
once at its first place and every constraint with its pack; `warnings` gives a `warn domains:` line
for two constraints of one attribute that differ (both kept, never chosen, Q-D74B-2) and for a
jurisdiction layer whose domain is not listed. With no `[domain]` table nothing is appended.
"""

from __future__ import annotations

import datetime
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import domain_model
import playbook_format
from common import repo_root, run, utf8_output
from guard import scan_text

NAME = "domains"
FOLDER = "config/domains"
RULE = "rule 2"
STR, INT, BOOL, STRS = "str", "int", "bool", "strs"
ATTRIBUTES = ("residency", "encryption", "audit", "retention", "availability", "latency")
TOP = {"format": INT, "domain": STR, "title": STR, "as_of": STR}
IDS = {"id": STR, "text": STR}
SOURCED = {"source": STR, "basis": STR}
# section -> (required keys, optional keys); `terms` is the one required section
SECTIONS: dict[str, tuple[dict[str, str], dict[str, str]]] = {
    "terms": ({"term": STR, "meaning": STR, "synonyms": STRS}, {}),
    "actors": (IDS, {}),
    "entities": (IDS, {}),
    "workflows": (IDS, {}),
    "kpis": ({**IDS, "unit": STR}, {}),
    "regulations": (
        {"id": STR, "title": STR, "jurisdiction": STR, "as_of": STR, "critical": BOOL},
        SOURCED,
    ),
    "constraints": (
        {"id": STR, "attribute": STR, "scenario": STR, "hard": BOOL},
        {"regulation": STR, **SOURCED},
    ),
    "discovery": ({**IDS, "depth": STR, "critical": BOOL}, {}),
    "references": ({**IDS, "source": STR}, {}),
    "acceptance": (IDS, {"regulation": STR, "constraint": STR}),
    "data_shapes": ({"id": STR, "field": STR, "format": STR}, {}),
    "gates": (
        {"id": STR, "kind": STR, "text": STR, "owner_only": BOOL},
        {"step": STR, "reason": STR, "regulation": STR, **SOURCED},
    ),
}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEY_AT = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
SHIPPED = ("field-service", "payments")  # the seed packs; a test holds them to kit/manifest.json
KEPT_ONCE = {"discovery": "id", "terms": "term", "acceptance": "id"}


def _is(value: Any, kind: str) -> bool:
    if kind == INT:
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == BOOL:
        return isinstance(value, bool)
    if kind == STRS:
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    return isinstance(value, str)


def _date(value: Any) -> datetime.date | None:
    if not isinstance(value, str) or not DATE.match(value):
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def folders(root: Path) -> list[Path]:
    """The folders packs are read from: the project's own first (a project's pack, rule 15), then
    the kit's by `kit_root.kit_file`, the same folder in the installed layout."""
    own = Path(root) / FOLDER
    if playbook_format.kit_root is None:
        return [own]
    try:
        kit = playbook_format.kit_root.kit_file(Path(root), FOLDER)
    except playbook_format.Refused:
        return [own]
    return [own] if kit == own else [own, kit]


def packs(root: Path) -> list[Path]:
    """The pack files, one per name (the project's first), sorted by name."""
    chosen: dict[str, Path] = {}
    for where in folders(root):
        for path in sorted(where.glob("*.toml")) if where.is_dir() else []:
            chosen.setdefault(path.name, path)
    return [chosen[name] for name in sorted(chosen)]


def pack_path(root: Path, name: str) -> Path | None:
    """The file of the pack `name` by `folders`, or None."""
    if not playbook_format.SLUG.match(name):
        return None
    found = [where / f"{name}.toml" for where in folders(root)]
    return next((p for p in found if p.is_file()), None)


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return f"{FOLDER}/{path.name}"


def load(path: Path) -> dict[str, Any] | None:
    """The pack's table (a BOM or CRLF read as UTF-8 TOML), or None when it cannot be read."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None


def kit_ids(root: Path) -> set[str]:
    """The question ids a pack's `[[discovery]]` never reuses: the topics, the fixed ids and every
    playbook's `[[discovery]]` ids, its grill ids among them."""
    ids = set(playbook_format.TOPIC_IDS) | set(playbook_format.DISCOVERY_IDS)
    places = list(playbook_format.playbooks(root))
    try:
        base = playbook_format.folder(root, playbook_format.BASE)
        places += sorted(base.glob("*.toml")) if base.is_dir() else []
    except playbook_format.Refused:
        pass
    for path in dict.fromkeys(places):
        rows = (load(path) or {}).get("discovery")
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                ids.add(row["id"])
    return ids


def _keys(line: str, table: dict, required: dict, optional: dict) -> list[str]:
    out = []
    for key in table:
        if key not in required and key not in optional:
            out.append(f"{line} has a key outside the format (key: {key})")
    for key, kind in {**required, **optional}.items():
        if key in required and key not in table:
            out.append(f"{line} is missing a required key (key: {key})")
        elif key in table and not _is(table[key], kind):
            out.append(f"{line} key has the wrong type (key: {key})")
    return out


def _entries(data: dict) -> dict[str, list[dict]]:
    return {
        name: [e for e in data.get(name, []) if isinstance(e, dict)]
        for name in SECTIONS
        if isinstance(data.get(name), list)
    }


def _sources(name: str, entry: dict) -> list[str]:
    if "source" not in entry and "basis" not in entry:
        return [f'a `[[{name}]]` entry has neither `source` nor `basis = "expected"` (key: source)']
    if "basis" in entry and entry["basis"] != "expected":
        return [f"a `[[{name}]]` `basis` is not expected (key: basis)"]
    return []


def _text(entry: dict, key: str) -> str | None:
    """The string at `key`, or None: a value of another type is `_keys`'s wrong-type line."""
    value = entry.get(key)
    return value if isinstance(value, str) else None


def _references(rows: dict[str, list[dict]]) -> list[str]:
    regs = {_text(e, "id"): e for e in rows.get("regulations", [])}
    cons = {_text(e, "id") for e in rows.get("constraints", [])}
    out = []
    for name in ("constraints", "acceptance", "gates"):
        for entry in rows.get(name, []):
            if "regulation" in entry and _text(entry, "regulation") not in regs.keys() - {None}:
                out.append(f"a `[[{name}]]` `regulation` names no regulation (key: regulation)")
            if "constraint" in entry and _text(entry, "constraint") not in cons - {None}:
                out.append(f"a `[[{name}]]` `constraint` names no constraint (key: constraint)")
    for entry in rows.get("gates", []):
        if entry.get("kind") not in playbook_format.GATE_KINDS:
            out.append("a `[[gates]]` `kind` is not check or judgement (key: kind)")
        held = regs.get(_text(entry, "regulation"), {})
        if entry.get("kind") == "judgement" and held.get("critical") is not True:
            out.append("a judgement gate names no critical regulation (key: regulation)")
    return out


def _values(rows: dict[str, list[dict]], kit: set[str]) -> list[str]:
    out = []
    for entry in rows.get("regulations", []):
        if "as_of" in entry and _date(entry["as_of"]) is None:
            out.append("a `[[regulations]]` `as_of` is not a date (key: as_of)")
    for entry in rows.get("constraints", []):
        if entry.get("attribute") not in ATTRIBUTES:
            out.append("a `[[constraints]]` `attribute` is not one of the six (key: attribute)")
    for entry in rows.get("discovery", []):
        if entry.get("depth") not in playbook_format.GRILL_DEPTHS:
            out.append("a `[[discovery]]` `depth` is not light, standard or deep (key: depth)")
        if _text(entry, "id") in kit:
            out.append("a `[[discovery]]` id reuses a kit question id (key: id)")
    for name in ("regulations", "constraints", "gates"):
        for entry in rows.get(name, []):
            out.extend(_sources(name, entry))
    ids = [e["id"] for entries in rows.values() for e in entries if isinstance(e.get("id"), str)]
    if len(set(ids)) != len(ids):
        out.append("an id is used twice in the pack (key: id)")
    return out


def _guarded(text: str) -> list[str]:
    lines = text.splitlines()
    out = []
    for hit in scan_text(text):
        found = KEY_AT.match(lines[hit.line - 1]) if hit.line <= len(lines) else None
        key = found.group(1) if found else "line"
        out.append(f"line {hit.line} holds what the data guard flags {hit.kind} (key: {key})")
    return out


def problems(path: Path, root: Path, kit: set[str] | None = None) -> list[str]:
    """Rule 2: the problems of one pack, each naming the rule, the file and the key."""
    rel = _rel(path, root)
    data = load(path)
    if data is None:
        return [f"{RULE}: {rel}: the pack is not readable TOML (key: format)"]
    sections = tuple(f"(key: {name})" for name in SECTIONS)  # the sections are checked below
    found = [line for line in _keys("the pack", data, TOP, {}) if not line.endswith(sections)]
    for name in SECTIONS:
        if name in data and not (
            isinstance(data[name], list) and all(isinstance(e, dict) for e in data[name])
        ):
            found.append(f"`[[{name}]]` is not a list of tables (key: {name})")
    if "terms" not in data:
        found.append("the pack is missing a required section (key: terms)")
    if data.get("format") != playbook_format.FORMAT and _is(data.get("format"), INT):
        found.append("the key has the wrong value (key: format)")
    if isinstance(data.get("domain"), str) and data["domain"] != path.stem:
        found.append("the `domain` is not the file's name (key: domain)")
    if isinstance(data.get("title"), str) and ("\n" in data["title"] or not data["title"].strip()):
        found.append("the `title` is not one plain line (key: title)")
    if "as_of" in data and _date(data["as_of"]) is None:
        found.append("the `as_of` is not a date (key: as_of)")
    rows = _entries(data)
    for name, entries in rows.items():
        for entry in entries:
            found.extend(_keys(f"a `[[{name}]]` entry", entry, *SECTIONS[name]))
    found += _values(rows, kit_ids(root) if kit is None else kit) + _references(rows)
    try:
        found += _guarded(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError):
        pass
    return [f"{RULE}: {rel}: {line}" for line in dict.fromkeys(found)]


def findings(root: Path) -> list[str]:
    """The problems of every pack, and a `domain` that two packs hold."""
    kit = kit_ids(root)
    out: list[str] = []
    held: dict[str, str] = {}
    for path in packs(root):
        out += problems(path, root, kit)
        domain = (load(path) or {}).get("domain")
        if isinstance(domain, str) and domain in held:
            rel = _rel(path, root)
            out.append(f"{RULE}: {rel}: the domain of {held[domain]} (key: domain)")
        elif isinstance(domain, str):
            held[domain] = _rel(path, root)
    return out + domain_model.findings(root)  # rule 7: the project domain model, ADR-0810


def _listed(root: Path) -> list[str]:
    import config  # here: config reads this module for `[domain] packs`

    return list(config.domain_settings(root)["packs"])


def _parent(root: Path, name: str, names: list[str]) -> tuple[str, bool] | None:
    """The domain of a jurisdiction layer `name` (`<domain>-<region>`) and whether it is listed:
    the longest listed prefix, else the longest that is a pack on disk; None for any other pack, and
    always for a shipped pack, which is never another pack's layer (fix list on 0ed1a719 item 4)."""
    if name in SHIPPED:
        return None
    cuts = [name[:i] for i, c in enumerate(name) if c == "-"][::-1]
    listed = next((d for d in cuts if d in names), None)
    if listed is not None:
        return listed, True
    found = next((d for d in cuts if pack_path(root, d) is not None), None)
    return (found, False) if found is not None else None


def order(root: Path, names: list[str]) -> list[str]:
    """Rule 4: the shipped packs in the person's order, each followed by its listed jurisdiction
    layers, then the project's own packs the same way; a layer whose domain is not listed stays
    where it is listed, among the shipped packs (fix list on 0ed1a719 item 2)."""
    found = {n: _parent(root, n, names) for n in names}
    layers = {n: p[0] for n, p in found.items() if p and p[1]}
    heads = [n for n in names if n not in layers]
    first = [n for n in heads if n in SHIPPED or found[n] is not None]
    out: list[str] = []
    for name in first + [n for n in heads if n not in first]:
        out += [name] + [n for n in names if layers.get(n) == name]
    return out


def compose(root: Path, layers: list[dict]) -> tuple[list[tuple[str | None, dict]], list[str]]:
    """Rule 4: the playbook's layers (each with no file of its own) and then each pack of
    `[domain] packs` in `order` with its file; and the problem of a refused table."""
    pairs: list[tuple[str | None, dict]] = [(None, layer) for layer in layers]
    try:
        names = _listed(root)
    except Exception as refused:  # config.DomainSettingError: its line names the setting
        return pairs, [f"rule 4: agk.toml: {refused}"]
    for name in order(root, names):
        path = pack_path(root, name)
        if path is not None:
            pairs.append((_rel(path, root), load(path) or {}))
    return pairs, []


def items(root: Path) -> dict[str, list[dict]]:
    """Rule 4: the composed packs' items, each with its `pack`: `[[discovery]]`, `[[terms]]` and
    `[[acceptance]]` once at their first place, and every `[[constraints]]` entry but a repeat."""
    try:
        names = order(root, _listed(root))
    except Exception:  # a refused table is the composition's problem line
        names = []
    out: dict[str, list[dict]] = {name: [] for name in (*KEPT_ONCE, "constraints")}
    seen: set[tuple] = set()
    for name in names:
        path = pack_path(root, name)
        rows = _entries(load(path) or {}) if path is not None else {}
        for section in out:
            for entry in rows.get(section, []):
                key = KEPT_ONCE.get(section)
                mark = (
                    (section, entry.get(key))
                    if key
                    else (section, *map(entry.get, ("id", "attribute", "scenario")))
                )
                if mark not in seen:
                    seen.add(mark)
                    out[section].append({**entry, "pack": name})
    return out


def warnings(root: Path) -> list[str]:
    """Rule 4: one `warn domains:` line per constraint whose attribute an earlier one names with a
    different scenario (ids and pack names only; the stricter holds until a person decides), and
    per jurisdiction layer whose domain `[domain] packs` does not list. Never a failure."""
    try:
        names = _listed(root)
    except Exception:  # a refused table is the composition's problem line
        return []
    out = []
    for name in names:
        found = _parent(root, name, names)
        if found is not None and not found[1]:
            out.append(
                f"warn {NAME}: {name} is a jurisdiction layer of {found[0]}, which "
                "`[domain] packs` does not list"
            )
    first: dict[Any, dict] = {}
    for entry in items(root)["constraints"]:
        held = first.setdefault(entry.get("attribute"), entry)
        if held is not entry and held.get("scenario") != entry.get("scenario"):
            out.append(
                f"warn {NAME}: attribute {entry['attribute']}: {held['id']} ({held['pack']}) and "
                f"{entry['id']} ({entry['pack']}) differ; the stricter holds until a person decides"
            )
    return out


def _months(root: Path) -> int:
    import config  # here: config reads this module for `[domain] packs`

    try:
        return int(config.domain_settings(root)["stale_months"])
    except Exception:  # a refused table is doctor's line; the default holds here
        return config.DOMAIN_DEFAULTS["stale_months"]


def stale(root: Path, today: datetime.date | None = None) -> list[str]:
    """Rule 14: one `warn domains:` line per pack whose `as_of`, or a regulation's, is older than
    `[domain] stale_months`; never a failure."""
    today = today or datetime.datetime.now(datetime.UTC).date()
    months = _months(root)
    out = []
    for path in packs(root):
        data = load(path) or {}
        regs = data.get("regulations")
        dates = [data.get("as_of")] + [
            e.get("as_of") for e in (regs if isinstance(regs, list) else []) if isinstance(e, dict)
        ]
        found = [d for d in map(_date, dates) if d is not None]
        if any((today.year - d.year) * 12 + today.month - d.month > months for d in found):
            out.append(
                f"warn {NAME}: {_rel(path, root)} as_of is older than [domain] stale_months "
                "(verify)"
            )
    return out


def cmd_check(root: Path) -> int:
    found = findings(root)
    for line in found:
        print(f"FAIL {NAME}: {line}")
    if found:
        return 1
    for line in stale(root) + warnings(root):
        print(line, file=sys.stderr)
    count = len(packs(root))
    print(f"ok {NAME} ({count} packs)" if count else f"ok {NAME} (none)")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if root is None and args:
        print("usage: check_domains.py [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
