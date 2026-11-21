# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `architecture-record` step (brief #1595, ADR-0675; amendment 204, SPEC-0072 rule 5; REQ-079).

The product's one record, `docs/architecture.md`, holds `## Context`, `## Parts`, `## Data stores`,
`## Outside services` (each service of the chosen stack option's `External services:`), `## Needs`
(`- Busiest hour:`, `- Downtime:`, `- Cost:`, `- Recovery time:`, `- Logged:`; the first three's
numbers are those of the quoted needs answer), `## Diagram` (a fenced Mermaid or text block that
draws each outside service) and `## Layers`. The check is `front_door.py`'s (`record_problems`),
which `check-design` runs too; each failure names the rule and the section, never a value
(principle 8). A record with none of the new sections was written before this change and is
`not run` until its next edit (principle 11). It runs only where the record exists. Files only:
no network. Installed; it imports only installed modules; the runner's interface of
`scripts/agk/gates/` (`RULE`, `check`, `skipped`, `applies`).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import front_door  # noqa: E402

RULE = f"{front_door.RULE_5}: the architecture record lacks a required part"
HELD = "the record predates its required sections; held until its next edit"


def applies(root: Path) -> bool:
    return (root / front_door.RECORD).is_file()


def skipped(root: Path) -> str | None:
    if front_door.record_held((root / front_door.RECORD).read_text(encoding="utf-8")):
        return HELD
    return None


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """The runner's interface: (rule, path class) of each failure; each names its section."""
    return front_door.record_problems(root)
