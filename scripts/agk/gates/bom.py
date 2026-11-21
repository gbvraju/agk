# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `bom` step (brief #1596, ADR-0676; SPEC-0054 rule 4 as amendment 206 proposes; REQ-061).

Where a stack is chosen and its lock is read (`licences.applies`), the runner makes the product's
bill of `HEAD` in memory, as `sbom.py make` does, and checks it as `sbom.py check` does: a file
the bill reads that cannot be parsed at the commit, or a bill its own check refuses, is red naming
the rule and the path class, never a value. Nothing is written; local `git` only, no socket. The
kit's own repository declares no work type, so the runner never calls it there (rule 4 unchanged).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import sbom  # noqa: E402
from common import CheckError  # noqa: E402

from gates import licences  # noqa: E402

RULE = "SPEC-0054 rule 4 (amendment 206): the product's bill cannot be made or is refused"


def applies(root: Path) -> bool:
    return licences.applies(root)


def check(root: Path, playbook: dict[str, Any]) -> list[str]:
    """The runner's interface: the path classes that fail, none when the bill is made and ok."""
    try:
        doc = sbom.build(Path(root), sbom.resolve(Path(root), "HEAD"))
    except CheckError:
        return ["bill of materials"]
    again = json.loads(json.dumps(doc))
    return sorted({cls for cls, _ in sbom.document_problems(again, doc)})
