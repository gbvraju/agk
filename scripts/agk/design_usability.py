# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The usability record (SPEC-0073 rule 8; SPEC-0038 rule 10 and SPEC-0037 rule 7 by amendment
237; brief #1953, ADR-0809). Installed: `kit/manifest.json` lists it in `verbatim`, and
`check_design.py` imports it inside its inventory branch.

`docs/design/usability.md` holds one `## <version>` section per prototype or imported version
(`v<n>` or `i<n>`), and in it one `### <screen id>` per screen of `docs/design/inventory.md`, each
with one line `- <heuristic>: pass | finding: <text> | not applicable: <reason>` for each of the
ten `HEURISTICS`; the form is `kit/templates/usability.md`. `problems(root)` checks it only when
the declared `[delivery] work_type` is one of `SCREEN_WORK_TYPES`: it fails a missing record, a
missing section for the newest version (`newest`: the last kit version, else the last imported
one), a screen of the inventory with no section, a heuristic missing, twice or not one of the
ten, a value outside the three forms or with no text, and a screen the inventory does not hold.
An older version's section is read for its form only (`Q-73I-1`), and no version folder is read.
A refused declaration fails as `playbook_format.declaration` refuses it, naming the setting.
`note(root)` prints `design: usability not applicable (work type)` for any other work type or
none, and `design: usability waits for a prototype version` before the first version. Each
failure names `SPEC-0038 rule 10`, the path, the version and the screen, never a finding's text
(principle 8). Files only: no network, no model, nothing written.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_import
import design_inventory
import design_prototype_check
import playbook_format

RECORD = "docs/design/usability.md"
TEMPLATE = Path(__file__).resolve().parents[2] / "kit" / "templates" / "usability.md"
WHERE = f"SPEC-0038 rule 10: {RECORD}"
HEURISTICS = (
    "status",
    "real-world",
    "control",
    "consistency",
    "error-prevention",
    "recognition",
    "flexibility",
    "minimal",
    "error-recovery",
    "help",
)
SCREEN_WORK_TYPES = ("web-app", "mobile")  # the playbooks that name a screen design
VERSION = re.compile(r"^[vi][1-9]\d*$")
LINE = re.compile(r"^- ([a-z][a-z-]*):(.*)$")
VALUE = re.compile(r"^(?:pass|finding:\s*\S.*|not applicable:\s*\S.*)$")
NOT_APPLICABLE = "design: usability not applicable (work type)"
WAITS = "design: usability waits for a prototype version"


def newest(root: Path) -> str | None:
    """The version the record must cover: the last kit version, else the last imported one."""
    kit = design_prototype_check.versions(root)
    imported = design_import.versions(root)
    return (kit or imported or [None])[-1]


def _applies(root: Path) -> tuple[bool, list[str]]:
    """(checked, the declaration's problems): checked only for a declared screen work type."""
    value, refused = playbook_format.declaration(root)
    return value in SCREEN_WORK_TYPES, [f"SPEC-0038 {p}" for p in refused]


def note(root: Path) -> str | None:
    """The one information line of the check, or None when it checks the record."""
    checked, refused = _applies(root)
    if refused:
        return None
    if not checked:
        return NOT_APPLICABLE
    return None if newest(root) else WAITS


def _sections(text: str) -> tuple[list[tuple[str, list[tuple[str, list[str]]]]], bool]:
    """([(version, [(screen, its `- ` lines)])], whether a `##` heading is not a version)."""
    found: list[tuple[str, list[tuple[str, list[str]]]]] = []
    stray = False
    screens: list[tuple[str, list[str]]] | None = None
    current: list[str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            heading = line[3:].strip()
            screens, current = None, None
            if VERSION.match(heading):
                screens = []
                found.append((heading, screens))
            else:
                stray = True
        elif line.startswith("### ") and screens is not None:
            current = []
            screens.append((line[4:].strip(), current))
        elif line.startswith("- ") and current is not None:
            current.append(line)
    return found, stray


def _screen_lines(where: str, lines: list[str], out: list[str]) -> None:
    seen: set[str] = set()
    for line in lines:
        match = LINE.match(line)
        if not match or match.group(1) not in HEURISTICS:
            out.append(f"{where}: a line is not one of the ten heuristics")
            continue
        name = match.group(1)
        if name in seen:
            out.append(f"{where}: the heuristic {name} is listed twice")
            continue
        seen.add(name)
        if not VALUE.match(match.group(2).strip()):
            out.append(
                f"{where}: {name} is not pass, finding: <text> or not applicable: <reason>"
            )
    for name in HEURISTICS:
        if name not in seen:
            out.append(f"{where}: the heuristic {name} is missing")


def problems(root: Path) -> list[str]:
    """The SPEC-0038 rule 10 problems of the record; [] when it passes or is not checked."""
    root = Path(root)
    checked, refused = _applies(root)
    if refused or not checked:
        return refused
    version = newest(root)
    if version is None:
        return []
    path = root / RECORD
    if not path.is_file():
        return [f"{WHERE}: {version}: the usability record is missing"]
    inventory = design_inventory._parts(
        (root / design_inventory.INVENTORY).read_text(encoding="utf-8")
    )
    screens = [h for h, _ in inventory.get("Screens", []) if design_inventory.SLUG.match(h)]
    sections, stray = _sections(path.read_text(encoding="utf-8"))
    out: list[str] = []
    if stray:
        out.append(f"{WHERE}: a section is not headed by a version")
    if version not in [v for v, _ in sections]:
        out.append(f"{WHERE}: {version}: the version has no section")
    for name, listed in sections:
        newest_one = name == version
        seen: set[str] = set()
        for screen, lines in listed:
            if not design_inventory.SLUG.match(screen):
                out.append(f"{WHERE}: {name}: a screen id is not a lower-case slug")
                continue
            if screen in seen:
                out.append(f"{WHERE}: {name}: {screen}: the screen has more than one section")
                continue
            seen.add(screen)
            if newest_one and screen not in screens:
                out.append(f"{WHERE}: {name}: {screen}: the screen is not in the inventory")
                continue
            _screen_lines(f"{WHERE}: {name}: {screen}", lines, out)
        if newest_one:
            for screen in screens:
                if screen not in seen:
                    out.append(f"{WHERE}: {name}: {screen}: the screen has no section")
    return out
