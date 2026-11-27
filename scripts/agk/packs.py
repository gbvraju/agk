# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The knowledge resolver (SPEC-0077 rule 5; REQ-084 AC2; brief #2032, ADR-0839).
Installed: `kit/manifest.json` lists it in `verbatim`.

`files(root, kind)` gives each file of one of rule 2's nine kinds as `(layer, path)`, in one order:
`agk-core` (the kit's file or folder through `kit_root.kit_file`), then each pack of `[packs] use`
in its listed order (the files its manifest lists under `<kind>/`), then the project's own files.
In the installed layout the kit's file is the project's path, so it is read once, as `agk-core`
(`Q-2032-1`). A refused `[packs]` table, or a pack in use that `check_packs.problems` fails, raises
`Refused` with one line naming the setting or the rule and the pack, never a value: a reader stops
there, never with a partial read. `rows` composes rows by a key, a later layer's rows of a name
replacing the earlier ones (a proposal for a person to confirm, `Q-PB-1`). Standard library,
`config`, `check_packs` and `kit_root` only; reads files only: no network, no model.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import kit_root
from common import CheckError

CORE = "agk-core"
PROJECT = "project"
# Rule 2: where `agk-core` keeps each kind today; None: no built-in file of the kind yet.
KIT = {
    "playbooks": "config/playbooks",
    "domains": "config/domains",
    "standards": "config/standards.toml",
    "stack-defaults": "config/stack-defaults.toml",
    "stack-signals": "config/stack-signals.toml",
    "domain-signals": "config/domain-signals.toml",
    "data-patterns": None,
    "parts": None,
    "skills": "skills",
}
PROVENANCE = ("source", "basis")  # rule 3's keys of a pack's entry, not the reader's format


class Refused(CheckError):
    """A pack in use cannot be read; the line names the setting or the rule, never a value."""


def _expand(path: Path | None, kind: str) -> list[Path]:
    if path is None:
        return []
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(path.glob("*/SKILL.md" if kind == "skills" else "*.toml"))


def used(root: Path) -> list[tuple[str, Path]]:
    """Each pack of `[packs] use` in its order with its folder; raises `Refused`."""
    import check_packs  # here: check_packs imports playbook_format, which imports this module

    import config

    try:
        ids = [entry["id"] for entry in config.packs_settings(Path(root))["use"]]
    except config.PacksSettingError as exc:
        raise Refused(f"packs: {exc}") from None
    out = []
    for pid in ids:
        folder = Path(root) / check_packs.FOLDER / pid
        found = check_packs.problems(folder)
        if found:
            raise Refused(f"packs: {found[0]}")
        out.append((pid, folder))
    return out


def files(root: Path, kind: str, core: Path | None = None) -> list[tuple[str, Path]]:
    """Rule 5: the `(layer, path)` of each file of KIND, `agk-core` first, the project's last.
    CORE names `agk-core`'s file in place of `kit_root.kit_file` (a reader given its kit root).
    Raises `Refused`, and `kit_root.Refused` as `kit_file` does, each naming the setting."""
    import check_packs

    if kind not in KIT:
        raise ValueError(kind)
    root = Path(root)
    rel = KIT[kind]
    if core is None and rel is not None:
        core = kit_root.kit_file(root, rel)
    out = [(CORE, path) for path in _expand(core, kind)]
    for pid, folder in used(root):
        listed = (check_packs.load(folder / check_packs.MANIFEST) or {}).get("files", {})
        out += [(pid, folder / name) for name in sorted(listed) if name.startswith(f"{kind}/")]
    own = root / rel if rel is not None else None
    if own is not None and core is not None and own.resolve() != core.resolve():
        out += [(PROJECT, path) for path in _expand(own, kind)]
    return out


def label(layer: str, rel: str) -> str:
    """The path class a reader names for a layer's file: a pack's folder, else REL."""
    return f"config/packs/{layer}" if layer not in (CORE, PROJECT) else rel


def plain(entry: dict, layer: str) -> dict:
    """A pack's entry without its provenance keys (rule 3); the kit's and project's as they are."""
    if layer in (CORE, PROJECT):
        return entry
    return {k: v for k, v in entry.items() if k not in PROVENANCE}


def rows(layers: list[tuple[str, list[dict]]], key: str) -> list[dict]:
    """`Q-PB-1`: the rows of each layer in order, a later layer's rows of one KEY value replacing
    every earlier row of that value; the first place of a value is kept."""
    out: dict[object, list[dict]] = {}
    for layer, found in layers:
        mine: dict[object, list[dict]] = {}
        for row in found:
            mine.setdefault(row.get(key), []).append(plain(row, layer))
        out.update(mine)
    return [row for group in out.values() for row in group]
