# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `mock-parity` step (web-app; SPEC-0072 rule 3; brief #1597, ADR-0677).

Each operation of `contracts/openapi.json` has a mock under `mocks/`: a JSON file
`{"operationId": ..., "response": {...}}` of the same `operationId` whose response keys are the
properties of the operation's first 2xx JSON response schema (a local `$ref` resolved). Fails a
missing mock and a mock with other keys, naming the rule and the path class, never an operation
(principle 8). Not run while no contract in the kit's format exists. Files only: no network.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import CONTRACT, NO_ID, contract, operations, read_json

RULE = "SPEC-0072 rule 3: an operation has no mock"
KEYS = "SPEC-0072 rule 3: a mock's response keys differ from the contract"
MOCKS = "mocks/"


def skipped(root: Path) -> str | None:
    return contract(root)[1]


def mocks(root: Path) -> dict[str, Any]:
    """operationId to the mock's response, over every JSON file under `mocks/`."""
    out: dict[str, Any] = {}
    folder = root / MOCKS
    for path in sorted(folder.rglob("*.json")) if folder.is_dir() else []:
        data = read_json(path)
        if isinstance(data, dict) and isinstance(data.get("operationId"), str):
            out.setdefault(data["operationId"], data.get("response"))
    return out


def dig(value: Any, *keys: str) -> Any:
    """The value under the keys, or None where a level is not a table (a malformed contract)."""
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def expected(data: dict[str, Any], op: dict[str, Any]) -> set[str]:
    """The property names of the first 2xx JSON response schema, empty when it names none."""
    raw = op.get("responses")
    responses: dict[str, Any] = raw if isinstance(raw, dict) else {}
    codes = sorted(str(c) for c in responses if str(c).startswith("2"))
    for code in codes:
        schema = dig(responses[code], "content", "application/json", "schema")
        ref = schema.get("$ref") if isinstance(schema, dict) else None
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            schema = dig(data, "components", "schemas", ref.rsplit("/", 1)[1])
        props = schema.get("properties") if isinstance(schema, dict) else None
        return set(props) if isinstance(props, dict) else set()
    return set()


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    data, _, failed = contract(root)
    if data is None:
        return failed
    have = mocks(root)
    found = set()
    for oid, op in operations(data):
        if oid is None:
            found.add((NO_ID, CONTRACT))
        elif oid not in have:
            found.add((RULE, MOCKS))
        else:
            keys = expected(data, op)
            response = have[oid]
            if keys and (not isinstance(response, dict) or set(response) != keys):
                found.add((KEYS, MOCKS))
    return sorted(found)
