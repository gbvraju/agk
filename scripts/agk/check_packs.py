# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The pack format check (SPEC-0077 rules 2, 3 and 12; REQ-084 AC1; brief #2031, ADR-0838).
Installed: `kit/manifest.json` lists it in `verbatim`.

A pack is `config/packs/<id>/` holding one `agk-pack.toml` (`format = 1`) with the keys of rule 3.
`findings` gives one line per problem, `rule 3: config/packs/<id>: <what> (key: <key>)`, never a
value: a missing or unknown key, a value of the wrong type (a `bool` is never a number) or form, a
kind outside rule 2's nine, a file not listed in `files`, missing or whose SHA-256 differs, a file
under no listed kind's folder, an entry of a TOML knowledge file with neither a dated `source` nor
`basis = "expected"`, and a line that `guard.scan_text` flags. A pack folder that `[packs] use`
does not list, or a refused `[packs]` table, is a `rule 12:` line; `packs.verify`'s `rule 4:` lines
(the pack lock, brief #2033, ADR-0840) follow. `check_playbooks.findings` adds
them, so the governance step `playbooks` prints them as `FAIL playbooks:` lines; run alone
(`--root DIR`) it prints those lines as `FAIL packs:`, `ok packs (<n> packs)`, or nothing with no
pack. The built-in pack `agk-core` is the kit's own files where they are today, read through
`kit_root.kit_file`, with no manifest (`Q-PA-1`). Reads files only: no network, no model.
"""

from __future__ import annotations

import hashlib
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import playbook_format
from common import CheckError, repo_root, run, utf8_output
from guard import scan_text

NAME = "packs"
FOLDER = "config/packs"
MANIFEST = "agk-pack.toml"
CORE = "agk-core"  # rule 2: the built-in pack, a reserved name with no manifest
KINDS = (
    "playbooks",
    "domains",
    "standards",
    "stack-defaults",
    "stack-signals",
    "domain-signals",
    "data-patterns",
    "parts",
    "skills",
)
TIERS = ("official", "curated", "community")
SLUG = re.compile(r"^[a-z][a-z0-9-]*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")  # exact, never a range
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REVIEWED = re.compile(r"^\d{4}-\d{2}-\d{2} by [^@\s][^@]*$")  # a role or team, never an address
SHA = re.compile(r"^[0-9a-f]{64}$")
NAMES = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
STR, INT, STRS, TABLE = "str", "int", "strs", "table"
REQUIRED = {
    "format": INT,
    "id": STR,
    "version": STR,
    "publisher": STR,
    "tier": STR,
    "licence": STR,
    "source": STR,
    "kit": STR,
    "as_of": STR,
    "reviewed": STR,
    "kinds": STRS,
    "files": TABLE,
    "permissions": TABLE,
}
OPTIONAL = {"evals": STR}
PERMISSIONS = {"network": STR, "mcp": STRS}  # rule 6: `network = "research"`, `mcp = [names]`


def _is(value: Any, kind: str) -> bool:
    if kind == INT:
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == STRS:
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if kind == TABLE:
        return isinstance(value, dict)
    return isinstance(value, str)


def core_file(root: Path, rel: str) -> Path:
    """Rule 2: where `agk-core`'s file `rel` is read, the kit's own file by `kit_root.kit_file`."""
    import kit_root

    return kit_root.kit_file(Path(root), rel)


def folders(root: Path) -> list[Path]:
    """The pack folders under `config/packs/`, sorted by name."""
    base = Path(root) / FOLDER
    return sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []


def _label(folder: Path) -> str:
    """The pack's path class: `config/packs/<id>`, or `config/packs/` for a name out of form or
    one that the data guard flags (never the name)."""
    name = folder.name
    return f"{FOLDER}/{name}" if SLUG.match(name) and not scan_text(name) else f"{FOLDER}/"


def load(path: Path) -> dict[str, Any] | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _keys(data: dict) -> list[tuple[str, str]]:
    out = [("the key is not of the format", k) for k in data if k not in {**REQUIRED, **OPTIONAL}]
    for key, kind in {**REQUIRED, **OPTIONAL}.items():
        if key in REQUIRED and key not in data:
            out.append(("a required key is missing", key))
        elif key in data and not _is(data[key], kind):
            out.append(("the key has the wrong type", key))
    perms = data.get("permissions")
    for key, value in perms.items() if isinstance(perms, dict) else ():
        if key not in PERMISSIONS:
            out.append(("the key is not of the format", f"permissions.{key}"))
        elif not _is(value, PERMISSIONS[key]):
            out.append(("the key has the wrong type", f"permissions.{key}"))
        elif key == "network" and value != "research":
            out.append(("the key has the wrong value", "permissions.network"))
        elif key == "mcp" and not all(NAMES.match(v) for v in value):  # brief #2044 (ADR-0845)
            out.append(("the key has the wrong value", "permissions.mcp"))
    return out


def _values(data: dict, folder: Path) -> list[tuple[str, str]]:
    def text(key: str) -> str | None:
        return data[key] if isinstance(data.get(key), str) else None

    out = []
    if _is(data.get("format"), INT) and data["format"] != 1:
        out.append(("the key has the wrong value", "format"))
    pid = text("id")
    if pid is not None and (not SLUG.match(pid) or pid == CORE):
        out.append(("the key has the wrong value", "id"))
    elif pid is not None and pid != folder.name:
        out.append(("the id is not the folder's name", "id"))
    checks = {"version": VERSION, "as_of": DATE, "reviewed": REVIEWED}
    out += [
        ("the key has the wrong value", k)
        for k, rx in checks.items()
        if text(k) is not None and not rx.match(text(k) or "")
    ]
    if text("tier") is not None and text("tier") not in TIERS:
        out.append(("the key has the wrong value", "tier"))
    kinds = data.get("kinds")
    if isinstance(kinds, list) and _is(kinds, STRS) and any(k not in KINDS for k in kinds):
        out.append(("a kind is not one of rule 2's nine", "kinds"))
    return out


def _sourced(entry: dict, section: str = "") -> bool:
    """Rule 3: a dated `source` or `basis = "expected"`; a `[[claims]]` entry's `basis` keeps its
    claim meaning, so a measured claim proves its provenance with a dated `source` (`Q-PS-1`)."""
    dated = playbook_format.source_date(entry.get("source")) is not None
    if section == "claims" and entry.get("basis") == "measured":
        return dated
    if "basis" in entry:
        return entry["basis"] == "expected"
    return dated


def _knowledge(path: Path) -> list[tuple[str, str]]:
    """Rule 3 (`Q-PA-2`): each entry of an array of tables in a TOML knowledge file carries a
    dated `source` or `basis = "expected"`; a Markdown file (a skill) needs none here."""
    if path.suffix != ".toml":
        return []
    data = load(path)
    if data is None:
        return [("a knowledge file is not readable TOML", "files")]
    rows = [
        (k, e) for k, v in data.items() if isinstance(v, list) for e in v if isinstance(e, dict)
    ]
    return [
        ('an entry has neither a dated `source` nor `basis = "expected"`', "source")
        for k, e in rows
        if not _sourced(e, k)
    ]


def _guarded(path: Path) -> list[tuple[str, str]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return []  # a binary file: its hash is checked, its text is not read
    return [
        (f"a line holds what the data guard flags {hit.kind}", "line") for hit in scan_text(text)
    ]


def _files(data: dict, folder: Path) -> list[tuple[str, str]]:
    files = data.get("files")
    listed: dict = files if isinstance(files, dict) else {}
    kinds = [k for k in data.get("kinds") or [] if isinstance(k, str)]
    out = []
    base = folder.resolve()
    for rel, want in listed.items():
        path = (folder / rel).resolve()
        if not path.is_relative_to(base) or Path(rel).is_absolute():
            out.append(("a listed file is outside the pack", "files"))
            continue
        if not isinstance(want, str) or not SHA.match(want):
            out.append(("the key has the wrong value", "files"))
        if rel.split("/", 1)[0] not in kinds or "/" not in rel:
            out.append(("a file is under no listed kind's folder", "kinds"))
        if not path.is_file():
            out.append(("a listed file is missing", "files"))
        elif isinstance(want, str) and SHA.match(want) and digest(path) != want:
            out.append(("a listed file's SHA-256 differs", "files"))
        else:
            out += _knowledge(path) + _guarded(path)
    on_disk = [p for p in folder.rglob("*") if p.is_file() and p != folder / MANIFEST]
    names = {(folder / rel).resolve() for rel in listed}
    out += [("a file is not listed", "files") for p in on_disk if p.resolve() not in names]
    return out


def problems(folder: Path, root: Path | None = None) -> list[str]:
    """Rule 3: the problems of one pack folder, each naming the rule, the pack and the key; with
    ROOT, rule 10's curated line too."""
    label = _label(folder)
    manifest = folder / MANIFEST
    if not manifest.is_file():
        return [f"rule 3: {label}: the pack has no {MANIFEST} (key: format)"]
    data = load(manifest)
    if data is None:
        return [f"rule 3: {label}: the manifest is not readable TOML (key: format)"]
    found = _keys(data) + _values(data, folder) + _files(data, folder) + _guarded(manifest)
    out = [f"rule 3: {label}: {what} (key: {key})" for what, key in found]
    if root is not None and data.get("tier") == "curated" and not _evaluated(root, data):
        out.append(f"rule 10: {label}: a curated pack needs an accepted eval record (key: evals)")
    return out


def _evaluated(root: Path, data: dict) -> bool:
    """SPEC-0077 rule 10 (brief #2043, ADR-0847, `Q-PH-5`): only where `evals/rubric.toml`
    exists (the kit), a curated pack's `evals` names an accepted record; elsewhere as today."""
    try:
        import eval_record  # noqa: PLC0415 - kit-only, absent from an installed copy
    except ImportError:  # a project: the kit-only script is absent
        return True
    if not eval_record.applies(root):
        return True
    named = data.get("evals")
    return isinstance(named, str) and eval_record.accepted(root, path=named) is not None


def _settings(root: Path) -> dict:
    import config  # here: config reads this module for the manifests of `[packs] use`

    return config.packs_settings(root)


def in_use(root: Path) -> list[str]:
    """Rule 2 and rule 12: `agk-core`, then each pack of `[packs] use` in its order; `agk-core`
    alone with no table or a refused one (`findings` names the refusal)."""
    try:
        return [CORE, *(e["id"] for e in _settings(root)["use"])]
    except CheckError:
        return [CORE]


def findings(root: Path) -> list[str]:
    """Every problem of every pack folder, a folder that `[packs] use` does not list, and a
    refused `[packs]` table."""
    out: list[str] = []
    try:
        used = {e["id"] for e in _settings(root)["use"]}
    except CheckError as exc:
        out.append(f"rule 12: {exc}")
        used = None
    for folder in folders(root):
        out += problems(folder, root)
        readable = load(folder / MANIFEST) is not None  # else its one line above names it
        if readable and used is not None and folder.name not in used:
            out.append(
                f"rule 12: {_label(folder)}: the pack is not listed in use (setting: packs.use)"
            )
    import packs  # rule 4 (brief #2033, ADR-0840): the lock, offline, in the same step

    return out + packs.verify(root, None if used is None else _settings(root)["use"])


def cmd_check(root: Path) -> int:
    found = findings(root)
    for line in found:
        print(f"FAIL {NAME}: {line}")
    if found:
        return 1
    count = len(folders(root))
    if count:
        print(f"ok {NAME} ({count} packs)")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if root is None and args:
        print("usage: check_packs.py [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
