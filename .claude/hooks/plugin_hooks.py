#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The plugin's one hook: the five guards from the plugin (SPEC-0071 rule 4, #1454, ADR-0612).

`.claude-plugin/plugin.json` registers it as `plugin_hooks.py pre` (PreToolUse) and `plugin_hooks.py
stop` (Stop). It runs the guard of this folder, the plugin's own copy, with the hook's input on its
stdin, and passes back the guard's output and exit code unchanged:

- the data guard (PreToolUse) and `stop_check.py` (Stop) only for a project that does not register
  them itself: `[kit] layout = "plugin"` in its `agk.toml`, or an `agk.toml` with no own copy of the
  guard. An installed project, the kit's own repository and a project with no `agk.toml` keep
  `.claude/settings.json` as today, so nothing runs twice;
- the agent's guard when the hook's `agent_type` names a plugin agent (`agk:conductor` and the
  others of `AGENT_GUARDS`) on a tool its frontmatter matcher names: a recorded run (ADR-0612)
  showed that a plugin agent's own frontmatter hooks do not fire, in either layout.

It fails closed: input it cannot read, or a guard it cannot run, denies a PreToolUse call with one
line naming the hook, never a value. Standard library; no network.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
AGENT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"}  # the agents' matcher
AGENT_GUARDS = {
    "agk:architect": ("architect_guard.py",),
    "agk:architect-review": ("architect_guard.py", "--review"),
    "agk:conductor": ("conductor_guard.py",),
    "agk:shadow": ("conductor_guard.py", "--shadow"),
    "agk:steward": ("steward_guard.py",),
}
DENY = "plugin hooks: cannot-judge (hook input or guard): ask the person to run it"


def project_runs_own(root: Path, guard: str) -> bool:
    """True when the project's own `.claude/settings.json` runs `guard` (the installed layout)."""
    path = root / "agk.toml"
    if not path.is_file():
        return True  # not an agk project: the plugin adds no guard of its own
    try:
        kit = tomllib.loads(path.read_text(encoding="utf-8")).get("kit", {})
        clean = isinstance(kit, dict) and kit.get("layout") == "plugin"
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        clean = False  # unreadable: the own copy below decides
    return not clean and (root / ".claude" / "hooks" / guard).is_file()


def plan(event: str, payload: dict, root: Path) -> list[tuple[str, ...]]:
    """The guards to run, in order, each as (file, *arguments)."""
    if event == "stop":
        return [] if project_runs_own(root, "stop_check.py") else [("stop_check.py",)]
    runs = [] if project_runs_own(root, "data_guard.py") else [("data_guard.py",)]
    agent = AGENT_GUARDS.get(str(payload.get("agent_type") or ""))
    if agent and payload.get("tool_name") in AGENT_TOOLS:
        runs.append(agent)
    return runs


def deny(event: str) -> int:
    if event == "pre":
        out = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": DENY,
        }
        print(json.dumps({"hookSpecificOutput": out}))
    return 0


def main(argv: list[str]) -> int:
    event = argv[0] if argv else ""
    raw = sys.stdin.buffer.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
        if event not in ("pre", "stop") or not isinstance(payload, dict):
            raise ValueError("input")
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")
        runs = plan(event, payload, root)
    except (ValueError, UnicodeDecodeError, OSError):
        return deny(event)
    for guard, *args in runs:
        try:
            proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
                [sys.executable, str(HOOKS / guard), *args], input=raw, capture_output=True
            )
        except OSError:
            return deny(event)
        if proc.returncode != 0 or proc.stdout.strip():  # a refusal: pass it back unchanged
            sys.stdout.buffer.write(proc.stdout)
            sys.stderr.buffer.write(proc.stderr)
            return proc.returncode
        sys.stderr.buffer.write(proc.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
