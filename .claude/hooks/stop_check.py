#!/usr/bin/env python3
"""Stop hook: run `make -f agk.mk agk-governance` and block stopping while it is red.

Contract (verify): the hook receives JSON on stdin (including `stop_hook_active` and `cwd`);
printing {"decision": "block", "reason": ...} with exit code 0 keeps the session going.
When `stop_hook_active` is true the hook has already blocked once in this stop sequence; it then
allows the stop so that an unfixable failure cannot loop forever (verify).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

TAIL_LINES = 30
TIMEOUT_SECONDS = 300


def block(reason: str) -> int:
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    if payload.get("stop_hook_active"):
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    try:
        proc = subprocess.run(
            ["make", "-f", "agk.mk", "agk-governance"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return block(
            "`make -f agk.mk agk-governance` could not run to completion; fix the environment."
        )
    if proc.returncode == 0:
        return 0
    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-TAIL_LINES:])
    return block(f"`make -f agk.mk agk-governance` is red. Fix it before stopping.\n{tail}")


if __name__ == "__main__":
    sys.exit(main())
