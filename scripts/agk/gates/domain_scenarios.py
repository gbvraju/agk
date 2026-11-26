# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `domain-scenarios` step (SPEC-0074 rule 8, amendment 241; brief #1955, ADR-0811). REQ-081.

With `[domain] packs` set, each composed constraint (`check_domains.cited`) is one row of the
record's `## Quality scenarios`, ending ` [<pack>.<constraint>]`; a constraint with no row, or a row
citing no composed constraint, fails naming the id (`front_door.domain_scenario_problems`). It
applies only where the record holds its quality sections (else `architecture-quality` holds it)
and `[domain] packs` is set or refused; a refused table is `not run`, never a guess. Files only: no
network. Installed; the runner's interface of `scripts/agk/gates/` (`RULE`, `check`, `skipped`,
`applies`).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import check_domains  # noqa: E402
import front_door  # noqa: E402

RULE = f"{front_door.RULE_8}: a domain constraint lacks its quality scenario"
REFUSED = "[domain] is refused (setting: domain)"


def body(root: Path) -> dict[str, list[str]] | None:
    """The sections of a record that holds its quality sections, else None."""
    try:
        text = (root / front_door.RECORD).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if front_door.quality_held(text):
        return None
    return dict(front_door.sections_of(text.split("\n")))


def applies(root: Path) -> bool:
    return body(root) is not None and check_domains.cited(root) != {}


def skipped(root: Path) -> str | None:
    return REFUSED if check_domains.cited(root) is None else None


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    return front_door.domain_scenario_problems(body(root) or {}, check_domains.cited(root) or {})
