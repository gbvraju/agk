# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The step registry of `run_gates.py` (SPEC-0072 rule 3; brief #1586, ADR-0666). Installed with it.

One module per check step, named by the step with `-` as `_`. Each holds `RULE`, the rule a
failure names, and `check(root, playbook)`, which reads only the project's files, offline, and
returns the path classes that fail (none when the step passes), never a value.
A step may also hold `counts(root, playbook)`, its findings per file, which the runner holds to
the project's baseline (SPEC-0072 rule 7; brief #1600, ADR-0680).
"""

from __future__ import annotations

from typing import Any

PLAYBOOKS = "config/playbooks/"


def split(playbook: dict[str, Any]) -> tuple[list[str], set[tuple[str, str]]]:
    """The playbook's `[split] brief_order` and its `depends_on` pairs, (kind, kind it needs)."""
    table = playbook.get("split")
    table = table if isinstance(table, dict) else {}
    order = [k for k in table.get("brief_order", []) if isinstance(k, str)]
    pairs = {tuple(p) for p in table.get("depends_on", []) if isinstance(p, list) and len(p) == 2}
    return order, pairs  # type: ignore[return-value]


def ordered(order: list[str], kinds: list[str]) -> bool:
    """True when each kind is in `order` and they come in the given sequence."""
    return all(k in order for k in kinds) and [order.index(k) for k in kinds] == sorted(
        order.index(k) for k in kinds
    )
