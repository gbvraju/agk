# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `cut-over-order` step (cloud-migration; SPEC-0072 rule 3, ADR-0666): the split puts the
inventory, then the wave plan, then the cut-over, each cut-over brief depending on its wave plan
brief and that on the inventory brief."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import PLAYBOOKS, ordered, split

RULE = "the split does not put inventory, then wave plan, then cut-over"


def check(root: Path, playbook: dict[str, Any]) -> list[str]:
    order, pairs = split(playbook)
    needed = {("wave-plan", "inventory"), ("cut-over", "wave-plan")}
    sound = ordered(order, ["inventory", "wave-plan", "cut-over"]) and needed <= pairs
    return [] if sound else [PLAYBOOKS]
