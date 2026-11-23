# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `licences` step (brief #1596, ADR-0676; SPEC-0054 rule 4 as amendment 206 proposes;
REQ-061, REQ-079).

    python3 scripts/agk/gates/licences.py [--root DIR]

Each package of the chosen stack's committed lock (`pins.py` finds the stack, the lock and its
reader) has a licence: the lock's own where it states one (`package-lock.json`'s `license`), else
the Accepted stack record's `Parts:` entry of that name, else none. The step fails on a licence
outside the project's allowed list, `allowed` of `config/licences.toml` (absent: `DEFAULT`, the
list of `kit/templates/licences.toml`), and on a package with no licence it can read, as
`unknown`, never clean. An SPDX expression passes when one `OR` side has every `AND` id on the
list. Each line names the rule and the component class (`python`, `node`), never a name, a
version or an id (principle 8); a list of another form is refused naming the setting. With no
stack chosen or no lock it prints `not run: no lock`. `counts` gives the findings per file (the
lock's failing packages, the setting's form), so the runner's baseline holds an adopted project's
existing ones, counted on every run (brief #1777, ADR-0743). Offline, files only; widening the list is a project ADR
(principle 11). The runner calls it, as `layers`, where it `applies` (brief #1586's interface).
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

from common import utf8_output  # noqa: E402

from gates import pins  # noqa: E402

RULE = "SPEC-0054 rule 4 (amendment 206): a dependency's licence is not on the allowed list"
UNKNOWN = "SPEC-0054 rule 4 (amendment 206): a dependency's licence is unknown"
FORM = "SPEC-0054 rule 4 (amendment 206): the allowed list is not of its form"
SETTING = "config/licences.toml"
DEFAULT = frozenset(("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "PSF-2.0"))
NOT_RUN = "not run: no lock"
USAGE = "usage: python3 scripts/agk/gates/licences.py [--root DIR]"
CLASSES = {"requirements": "python", "npm": "node"}


def components(reader: str, text: str, parts: list[tuple[str, str, str]]) -> list[tuple[str, ...]]:
    """(class, name, version, licence or '') of each package of the lock, sorted."""
    have = pins.locked(reader, text)
    stated: dict[str, str] = {}
    if reader == "npm":
        for key, value in (json.loads(text).get("packages") or {}).items():
            licence = value.get("license") if isinstance(value, dict) else None
            if key.startswith("node_modules/") and isinstance(licence, str):
                stated[pins.norm(key.rsplit("node_modules/", 1)[1])] = licence.strip()
    named = {pins.norm(name): licence for name, _, licence in parts}
    cls = CLASSES[reader]
    return sorted((cls, n, v, stated.get(n) or named.get(n, "")) for n, v in have.items())


def lock_of(root: Path) -> tuple[str, str, list[tuple[str, str, str]]] | None:
    """(reader, lock text, record parts) of the chosen stack's lock, None with no stack or lock."""
    found = pins.chosen(Path(root))
    if found is None:
        return None
    (_, _, lock_file, reader), parts = found
    try:
        return reader, (Path(root) / lock_file).read_text(encoding="utf-8"), parts
    except (OSError, UnicodeDecodeError):
        return None


def allowed_from(text: str) -> frozenset[str] | None:
    """The `allowed` list of the setting's text, None when it is not of its form."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    items = data.get("allowed")
    if set(data) != {"allowed"} or not isinstance(items, list):
        return None
    if not all(isinstance(i, str) and i.strip() for i in items):
        return None
    return frozenset(i.strip() for i in items)


def passes(expression: str, allowed: frozenset[str]) -> bool:
    text = " ".join(expression.replace("(", " ").replace(")", " ").split())
    return any(all(i in allowed for i in side.split(" AND ")) for side in text.split(" OR "))


def problems(root: Path) -> list[tuple[str, str]] | None:
    """(rule, class or setting) of each failure, sorted; None when no lock is read."""
    found = tally(root)
    return None if found is None else sorted({(r, w) for r, w, _ in found})


def tally(root: Path) -> list[tuple[str, str, str]] | None:
    """(rule, class or setting, file) of each failing package or setting; None with no lock."""
    found = lock_of(root)
    if found is None:
        return None
    path = Path(root) / SETTING
    try:
        allowed = allowed_from(path.read_text(encoding="utf-8")) if path.is_file() else DEFAULT
    except (OSError, UnicodeDecodeError):
        allowed = None
    if allowed is None:
        return [(FORM, f"setting: {SETTING}", SETTING)]
    lock = pins.chosen(Path(root))[0][2]  # type: ignore[index]  # lock_of read it
    try:
        items = components(*found)
    except (AttributeError, ValueError):
        return [(UNKNOWN, f"component class: {CLASSES[found[0]]}", lock)]
    out = []
    for cls, _, _, licence in items:
        if not licence:
            out.append((UNKNOWN, f"component class: {cls}", lock))
        elif not passes(licence, allowed):
            out.append((RULE, f"component class: {cls}", lock))
    return out


def applies(root: Path) -> bool:
    """The runner runs the step only where a stack is chosen and its lock is read."""
    return lock_of(root) is not None


HELD = True  # brief #1777: a pass on a baseline that holds findings prints `held`, never `ok`


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """The runner's interface: (rule, path class) of each failure."""
    lock = (pins.chosen(Path(root)) or ((None, None, None),))[0][2]
    return [
        (f"{r} ({w})", SETTING if w.startswith("setting") else lock)
        for r, w in problems(root) or []
    ]


def counts(root: Path, playbook: dict[str, Any]) -> dict[str, int]:
    """The runner's baseline interface (SPEC-0072 rule 7): the findings per file."""
    out: dict[str, int] = {}
    for _, _, rel in tally(root) or []:
        out[rel] = out.get(rel, 0) + 1
    return out


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if args and not (len(args) == 2 and args[0] == "--root" and args[1]):
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(args[1]) if args else Path.cwd()
    if problems(root) is None:
        print(f"licences: {NOT_RUN}")
        return 0
    found = problems(root) or []
    for rule, where in found:
        print(f"FAIL licences: {rule} ({where})")
    if found:
        return 1
    print("ok licences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
