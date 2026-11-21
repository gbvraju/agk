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

import json
from pathlib import Path
from typing import Any

from common import load_config

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


# Brief #1597 (ADR-0677): the interface contract that `contract_tests` and `mock_parity` read.
CONTRACT = "contracts/openapi.json"
UNPARSED = "SPEC-0072 rule 3: the contract does not parse"
NOT_31 = "SPEC-0072 rule 3: the contract is not OpenAPI 3.1"
NO_ID = "SPEC-0072 rule 3: an operation has no operationId"
METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def read_json(path: Path) -> Any:
    """A JSON file after line-end normalising, or None when it cannot be read or parsed."""
    try:
        return json.loads(path.read_bytes().decode("utf-8").replace("\r\n", "\n"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def contract(root: Path) -> tuple[dict[str, Any] | None, str | None, list[tuple[str, str]]]:
    """(the contract, a reason it is not run, failures). Not run with no contract, and in
    `mode = "adopt"` for a contract in another format (brief #1597 item 4)."""
    path = root / CONTRACT
    if not path.is_file():
        return None, "no contract in the kit's format", []
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("paths", {}), dict):
        return None, None, [(UNPARSED, CONTRACT)]
    if not str(data.get("openapi", "")).startswith("3.1."):
        if load_config(root)["mode"] == "adopt":
            return None, "a contract in another format", []
        return None, None, [(NOT_31, CONTRACT)]
    return data, None, []


def operations(data: dict[str, Any]) -> list[tuple[str | None, dict[str, Any]]]:
    """(operationId or None, operation) for each operation of the contract's `paths`."""
    out = []
    for item in data.get("paths", {}).values():
        for method in METHODS if isinstance(item, dict) else ():
            op = item.get(method)
            if isinstance(op, dict):
                oid = op.get("operationId")
                out.append((oid if isinstance(oid, str) and oid else None, op))
    return out
