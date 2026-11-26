# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `domain-threats` step (SPEC-0074 rule 8, amendment 241; brief #1955, ADR-0811). REQ-081.

Each flow of the record's `## Threats` that names a data item of `docs/domain/data.md` carries its
class as `(class: <class>)`; a missing class, or one outside the five of SPEC-0074 rule 7, fails
naming the flow's number and the item, never the flow's text
(`front_door.threat_class_problems`). It applies where the record holds its quality sections and
`data.md` exists or `[domain] packs` is set; with packs and no `data.md` it is `not run: no data
classification`. Files only: no network. Installed; the runner's interface of
`scripts/agk/gates/` (`RULE`, `check`, `skipped`, `applies`).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import check_domains  # noqa: E402
import domain_model  # noqa: E402
import front_door  # noqa: E402

from gates.domain_scenarios import body  # noqa: E402

RULE = f"{front_door.RULE_8}: a threat flow lacks its data class"
UNCLASSIFIED = "no data classification"


def data(root: Path) -> Path:
    return domain_model.folder(root) / "data.md"


def applies(root: Path) -> bool:
    return body(root) is not None and (data(root).is_file() or check_domains.cited(root) != {})


def skipped(root: Path) -> str | None:
    return None if data(root).is_file() else UNCLASSIFIED


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    items = domain_model.data_items(domain_model.read(data(root)) or "")
    return front_door.threat_class_problems(body(root) or {}, items)
