# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `rollback-order` step (data-pipeline; SPEC-0072 rule 3, ADR-0666): the split puts a rollback
brief before every cut-over brief, and the cut-over depends on it."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import PLAYBOOKS, ordered, split

RULE = "the split does not put a rollback brief before every cut-over brief"


def check(root: Path, playbook: dict[str, Any]) -> list[str]:
    order, pairs = split(playbook)
    sound = ordered(order, ["rollback", "cut-over"]) and ("cut-over", "rollback") in pairs
    return [] if sound else [PLAYBOOKS]
