#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""SessionStart hook: say so when a session opens off the default branch (SPEC-0066 rule 3).

Brief #1583 (ADR-0663). The project's `.claude/settings.json` registers it with the agent line
(`common.with_agent`), never the kit's own copy. It prints the one line of `common.branch_check`
on standard output, the same line the steward's start prints, and nothing on the default branch,
so a person who chose plain Claude is told too `(verify: the hook's output shown to the person at
session start)`. It changes nothing: it runs no fetch (the steward's start fetches), reads no
network and always exits 0. A start that names another agent (`AGK_AGENT`, ADR-0662) is the kit's
own builder, conductor or reviewer on its branch, and gets no line. Standard library only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))


def main() -> int:
    if os.environ.get("AGK_AGENT", "steward") != "steward":
        return 0
    try:
        from common import branch_check  # noqa: PLC0415 - the project's own kit scripts

        line = branch_check(Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()), fetch=False)
    except Exception:  # noqa: BLE001 - a start hook never stops a session
        return 0
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
