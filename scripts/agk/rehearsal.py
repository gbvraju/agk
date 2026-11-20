# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The rehearsal record of SPEC-0071 rule 11 and its check (brief #1459, ADR-0617). Kit-only.

    python3 rehearsal.py check [--root KIT_ROOT]

Reads the `### Rehearsal record` table of SPEC-0071's proof in KIT_ROOT (default: the plugin this
script runs from): one `installed` and one `clean` row, each with its run dates, the same five
briefs and the four figures of rule 11 (lead time per brief in hours, tokens per merged pull request
from `metrics.py --cost`, first-review pass rate in percent and failed checks), then one
`Accepted: <YYYY-MM-DD> by the maintainers` line. The check fails when a figure or the dates are
missing, the briefs are not the same five, or a clean figure is worse than the installed one by more
than 10% (higher is worse but for the pass rate, and 10% of the installed figure is the bound). Each
line names the figure, never a value. The proof is held, and `upgrade.py --clean-repo` stops
refusing without `--rehearsal`, only when the check passes and the acceptance line is dated. It
reads one file, writes nothing, uses no network and no model; exit 0 held, 1 not held, 2 a bad call.
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

SPEC = (
    "docs/specs/"
    "0071-the-kit-runs-from-the-plugin-and-a-product-repository-keeps-only-its-project.md"
)
HEADING = "### Rehearsal record"
RUNS = ("installed", "clean")
# (name, higher is worse): the four figures of rule 11, in the table's column order.
FIGURES = (
    ("lead time per brief", True),
    ("tokens per merged pull request", True),
    ("first-review pass rate", False),
    ("failed checks", True),
)
BOUND = Decimal("0.10")
DATES = re.compile(r"^\d{4}-\d{2}-\d{2}(\.\.\d{4}-\d{2}-\d{2})?$")
ACCEPTED = re.compile(r"^Accepted: \d{4}-\d{2}-\d{2} by the maintainers\s*$", re.M)
USAGE = "usage: rehearsal.py check [--root KIT_ROOT]"
NO_RECORD = "the rehearsal record of SPEC-0071 rule 11 is missing (path class docs/specs/)"


def number(cell: str) -> Decimal | None:
    try:
        value = Decimal(cell.replace(",", "").strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() and value >= 0 else None


def rows(text: str) -> dict[str, list[str]] | None:
    """The record's rows by run, or None when the record's heading is not in the text."""
    if HEADING not in text:
        return None
    found: dict[str, list[str]] = {}
    for line in text.split(HEADING, 1)[1].splitlines():
        if line.startswith("#"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and cells[0] in RUNS:
            found.setdefault(cells[0], (cells + [""] * 7)[1:7])
    return found


def read(text: str) -> tuple[list[str], bool]:
    """(problems, accepted): each problem names a figure or a run, never a value."""
    found = rows(text)
    if found is None:
        return [NO_RECORD], False
    problems: list[str] = []
    values: dict[str, list[Decimal | None]] = {}
    briefs: dict[str, frozenset[str]] = {}
    for run in RUNS:
        cells = found.get(run)
        if cells is None:
            problems.append(f"missing: the {run} run")
            continue
        if not DATES.match(cells[0]):
            problems.append(f"missing: the run dates ({run})")
        found_briefs = frozenset(re.findall(r"#\d+", cells[1]))
        if found_briefs:
            briefs[run] = found_briefs
        else:
            problems.append(f"missing: the briefs ({run})")
        values[run] = [number(c) for c in cells[2:6]]
        for (name, _), value in zip(FIGURES, values[run], strict=True):
            if value is None:
                problems.append(f"missing: {name} ({run})")
    same = len(briefs) == 2 and briefs["installed"] == briefs["clean"]
    if len(briefs) == 2 and (len(briefs["installed"]) != 5 or not same):
        problems.append("not the same five briefs in both runs")
    if len(values) == 2:
        for i, (name, higher_worse) in enumerate(FIGURES):
            base, clean = values["installed"][i], values["clean"][i]
            if base is None or clean is None:
                continue
            worse = clean > base * (1 + BOUND) if higher_worse else clean < base * (1 - BOUND)
            if worse:
                problems.append(f"worse by more than 10%: {name}")
    return problems, bool(ACCEPTED.search(text.split(HEADING, 1)[1]))


def proof_held(root: Path) -> bool:
    """True only when the record passes the check and the maintainers' acceptance is dated."""
    try:
        text = (root / SPEC).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    problems, accepted = read(text)
    return not problems and accepted


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[2]
    if argv[:1] != ["check"] or len(argv) not in (1, 3) or (len(argv) == 3 and argv[1] != "--root"):
        print(USAGE)
        return 2
    if len(argv) == 3:
        root = Path(argv[2])
    try:
        text = (root / SPEC).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        print(f"not held: {NO_RECORD}")
        return 1
    problems, accepted = read(text)
    if not problems and not accepted:
        problems = ["not accepted: the record has no dated acceptance line of the maintainers"]
    for problem in problems:
        print(f"not held: {problem}")
    if problems:
        return 1
    print("proof held: both runs' four figures are within 10% and accepted (SPEC-0071 rule 11)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
