# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `contract-tests` step (web-app, api-service; SPEC-0072 rule 3; brief #1597, ADR-0677).

Fails a contract (`contracts/openapi.json`, OpenAPI 3.1 in JSON) that does not parse, an operation
with no `operationId`, and an operation whose `operationId` no file under `test_dirs` names as a
whole word, in any stack. Not run while no contract in the kit's format exists. Each failure names
the rule and the path class, never an operation (principle 8). Files only: no network.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from common import test_dirs

from . import CONTRACT, NO_ID, contract, operations

RULE = "SPEC-0072 rule 3: an operation is named by no test"
WHERE = f"{CONTRACT}; setting: test_dirs"


def skipped(root: Path) -> str | None:
    return contract(root)[1]


def test_text(root: Path) -> str:
    """The text of every file under `test_dirs`, line ends normalised."""
    parts = []
    for rel in test_dirs(root):
        for folder, dirs, files in os.walk(root / rel):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "node_modules")
            for name in sorted(files):
                try:
                    parts.append((Path(folder) / name).read_bytes().decode("utf-8", "ignore"))
                except OSError:
                    continue
    return "\n".join(parts)


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    data, _, failed = contract(root)
    if data is None:
        return failed
    ops = operations(data)
    text = test_text(root)
    found = set()
    for oid, _ in ops:
        if oid is None:
            found.add((NO_ID, CONTRACT))
        elif not re.search(rf"(?<![A-Za-z0-9_]){re.escape(oid)}(?![A-Za-z0-9_])", text):
            found.add((RULE, WHERE))
    return sorted(found)
