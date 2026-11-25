# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `architecture-quality` step (SPEC-0073 rule 8, amendment 236; brief #1952, ADR-0808).

REQ-080.

The hold of the record's quality sections, `front_door.QUALITY_SECTIONS` (`## Quality scenarios`,
`## Threats`, `## Operations`): a `docs/architecture.md` that holds none of them is a note until its
next edit, printed `not run architecture-quality: <reason>` beside the `architecture-record` line,
never `ok`. A record that holds any of them is checked whole by `front_door.record_problems`
through the `architecture-record` step, so this step then does not apply and prints nothing. Files
only: no network. Installed; it imports only installed modules; the runner's interface of
`scripts/agk/gates/` (`RULE`, `check`, `skipped`, `applies`).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import front_door  # noqa: E402

RULE = f"{front_door.RULE_5}: the architecture record lacks its quality sections"
HELD = front_door.QUALITY_HELD


def applies(root: Path) -> bool:
    """Only where the record exists and holds none of the quality sections."""
    try:
        text = (root / front_door.RECORD).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return front_door.quality_held(text)


def skipped(root: Path) -> str | None:
    return HELD if applies(root) else None


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """Never reached while held; a record with any quality section is `architecture-record`'s."""
    return []
