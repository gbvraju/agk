# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `glossary` step and the product glossary (brief #1951, ADR-0812; SPEC-0073 rule 8; REQ-080).

    python3 scripts/agk/gates/glossary.py [--root DIR] [--write]

The product's one glossary, `docs/glossary.md`, is one table of the columns `Term`, `Meaning`,
`In code` and `Synonyms`. The step fails a table missing, a second table or other columns; a row
with an empty `Term` or `Meaning` or other cells; a term twice (case-folded and trimmed, against
every term and synonym of an earlier row); and more rows than `[quality] glossary_terms` (10 to
200, 40), whose refusal names `quality.glossary_terms` as `config.quality_settings` does. The other
`[quality]` keys are not read. Several names in `In code` (an adopted codebase's aliases) are one
row. Each failure names the rule, the path class and the row number, never a term (principle 8). A
`\\|` inside a cell is text; a fenced block is not read. `--write` writes the glossary from
`kit/templates/glossary.md`, read from the kit root as `layers.py` reads the architecture template,
once and never over a glossary (`Q-73E-1`); seeding it from the grill and the steward's `Term:`
notes is the steward's, by hand (`Q-73E-2`). It runs only where the glossary exists. Files only:
no network. Installed; it imports only installed modules; the runner's interface of
`scripts/agk/gates/` (`RULE`, `check`, `applies`).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

from common import config_source, utf8_output  # noqa: E402

import config  # noqa: E402

RECORD = "docs/glossary.md"
TEMPLATE = Path(__file__).resolve().parents[3] / "kit" / "templates" / "glossary.md"
COLUMNS = ("term", "meaning", "in code", "synonyms")
KEY = "glossary_terms"
RULE = "SPEC-0073 rule 8: the glossary breaks its form"
FORM = "SPEC-0073 rule 8: the glossary needs one table of Term, Meaning, In code and Synonyms"
EMPTY = "SPEC-0073 rule 8: a glossary row lacks its term or meaning"
CELLS = "SPEC-0073 rule 8: a glossary row has other cells than the four columns"
TWICE = "SPEC-0073 rule 8: a glossary term is in the glossary twice"
CAP = "SPEC-0073 rule 8: the glossary is over its cap (setting: quality.glossary_terms)"
REFUSED = "the [quality] table is refused (setting: quality.glossary_terms)"
USAGE = "usage: python3 scripts/agk/gates/glossary.py [--root DIR] [--write]"
SPLIT = re.compile(r"(?<!\\)\|")
SEPARATOR = re.compile(r"^:?-{3,}:?$")


def applies(root: Path) -> bool:
    return (root / RECORD).is_file()


def cap(root: Path) -> int | None:
    """`[quality] glossary_terms`, its default when unset, or None when refused; no other key."""
    try:
        table = config_source(root).get("quality", {})
    except (OSError, ValueError):
        return None
    if not isinstance(table, dict):
        return None
    value = table.get(KEY, config.QUALITY_DEFAULTS[KEY])
    low, high = config.QUALITY_NUMBERS[KEY]
    return value if type(value) is int and low <= value <= high else None


def tables(text: str) -> list[list[str]]:
    """Each run of lines that starts with `|`, outside a fenced block."""
    found: list[list[str]] = []
    fenced, last = False, False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("```", "~~~")):
            fenced, last = not fenced, False
            continue
        is_row = not fenced and line.startswith("|")
        if is_row and not last:
            found.append([])
        if is_row:
            found[-1].append(line)
        last = is_row
    return found


def cells(line: str) -> list[str]:
    inner = line[1:-1] if line.endswith("|") and not line.endswith("\\|") else line[1:]
    return [c.strip() for c in SPLIT.split(inner)]


def names(row: list[str]) -> set[str]:
    words = [row[0], *row[3].split(",")]
    return {w.strip().casefold() for w in words if w.strip()}


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """The runner's interface: (rule, path class) of each failure; each names its row."""
    limit = cap(root)
    if limit is None:
        return [(REFUSED, RECORD)]
    found = tables((root / RECORD).read_text(encoding="utf-8"))
    if len(found) != 1 or len(found[0]) < 2:
        return [(FORM, RECORD)]
    head, rule, *rows = (cells(line) for line in found[0])
    if [c.casefold() for c in head] != list(COLUMNS) or not all(SEPARATOR.match(c) for c in rule):
        return [(FORM, RECORD)]
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for number, row in enumerate(rows, 1):
        if len(row) != len(COLUMNS):
            out.append((f"{CELLS} (row {number})", RECORD))
            continue
        if not row[0] or not row[1]:
            out.append((f"{EMPTY} (row {number})", RECORD))
            continue
        mine = names(row)
        if mine & seen:
            out.append((f"{TWICE} (row {number})", RECORD))
        seen |= mine
    if len(rows) > limit:
        out.append((CAP, RECORD))
    return out


def write(root: Path) -> int:
    """`Q-73E-1`: the glossary is written from the template once, never over one."""
    target = root / RECORD
    if target.exists():
        print(f"FAIL glossary: the glossary exists (path class: {RECORD})")
        return 1
    if not TEMPLATE.is_file():
        print("FAIL glossary: SPEC-0073 rule 8: no template (path class: kit/templates/)")
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"ok glossary: wrote {RECORD}")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    writing = "--write" in args
    rest = [a for a in args if a != "--write"]
    if len(args) - len(rest) > 1 or rest and not (len(rest) == 2 and rest[0] == "--root"):
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(rest[1]) if rest else Path.cwd()
    if writing:
        return write(root)
    if not applies(root):
        return 0
    found = check(root, {})
    for rule, cls in found:
        print(f"FAIL glossary: {rule} (path class: {cls})")
    if not found:
        print("ok glossary")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
