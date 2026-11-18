#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The plugin's one hook: the five guards from the plugin (SPEC-0071 rule 4, #1454, ADR-0612).

`.claude-plugin/plugin.json` registers it as `plugin_hooks.py pre` (PreToolUse) and `plugin_hooks.py
stop` (Stop). It runs the guard of this folder, the plugin's own copy, with the hook's input on its
stdin, and passes back a refusal unchanged:

- the data guard (PreToolUse) and `stop_check.py` (Stop) only for a project that does not register
  them itself: `[kit] layout = "plugin"` in its `agk.toml`, or an `agk.toml` with no own copy of the
  guard. An installed project, the kit's own repository and a project with no `agk.toml` keep
  `.claude/settings.json` as today, so nothing runs twice;
- the agent's guard when the hook's `agent_type` names a guarded role (`ROLE_GUARDS`) in any
  spelling but the project's own agent file, on a tool the agents' matcher names: a recorded run
  (ADR-0612) showed that a plugin agent's own frontmatter hooks do not fire, in either layout.

The project is the git top level of `CLAUDE_PROJECT_DIR` (or the input's `cwd`). It fails closed:
input it cannot read, or a guard that is missing, crashes or passes `GUARD_SECONDS`, denies a
PreToolUse call (or blocks a stop once) with the one line `DENY`, never the guard's message.
Standard library; no network.
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
ROLE_GUARDS = {
    "architect": ("architect_guard.py",),
    "architect-review": ("architect_guard.py", "--review"),
    "conductor": ("conductor_guard.py",),
    "shadow": ("conductor_guard.py", "--shadow"),
    "steward": ("steward_guard.py",),
}
GUARD_SECONDS = 4  # each PreToolUse guard; two fit the hook's 10-second budget
DENY = "plugin hooks: cannot-judge (hook input or guard): ask the person to run it"


def project_root(start: Path) -> Path:
    """The git top level of `start`, as `kit_root.project_root` (SPEC-0071 rule 2)."""
    try:
        out = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            timeout=GUARD_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return start
    top = out.stdout.strip()
    return Path(top) if out.returncode == 0 and top else start


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


def agent_guard(agent: str, root: Path) -> tuple[str, ...] | None:
    """The guard of a role in any spelling (`agk:conductor`, `conductor`). A bare name is the
    project's own agent when its file exists, whose frontmatter hook runs the guard already."""
    role = agent.rsplit(":", 1)[-1]
    if role not in ROLE_GUARDS:
        return None
    if ":" not in agent and (root / ".claude" / "agents" / f"{role}.md").is_file():
        return None
    return ROLE_GUARDS[role]


def plan(event: str, payload: dict, root: Path) -> list[tuple[str, ...]]:
    """The guards to run, in order, each as (file, *arguments)."""
    if event == "stop":
        return [] if project_runs_own(root, "stop_check.py") else [("stop_check.py",)]
    runs = [] if project_runs_own(root, "data_guard.py") else [("data_guard.py",)]
    agent = agent_guard(str(payload.get("agent_type") or ""), root)
    if agent and payload.get("tool_name") in AGENT_TOOLS:
        runs.append(agent)
    return runs


def deny(event: str, payload: object = None) -> int:
    """The one fixed line: a PreToolUse denial, or a blocked stop (once, as `stop_check.py`)."""
    if event == "pre":
        out = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": DENY,
        }
        print(json.dumps({"hookSpecificOutput": out}))
    elif not (isinstance(payload, dict) and payload.get("stop_hook_active")):
        print(json.dumps({"decision": "block", "reason": DENY}))
    return 0


def main(argv: list[str]) -> int:
    event = argv[0] if argv else ""
    raw = sys.stdin.buffer.read()
    payload = None
    try:
        payload = json.loads(raw.decode("utf-8"))
        if event not in ("pre", "stop") or not isinstance(payload, dict):
            raise ValueError("input")
        start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")
        root = project_root(start)
        runs = plan(event, payload, root)
    except (ValueError, UnicodeDecodeError, OSError):
        return deny(event if event == "stop" else "pre", payload)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}  # each guard sees the top level
    for guard, *args in runs:
        script = HOOKS / guard
        try:
            if not script.is_file():
                raise OSError("guard")
            proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
                [sys.executable, str(script), *args],
                input=raw,
                capture_output=True,
                env=env,
                timeout=GUARD_SECONDS if event == "pre" else None,
            )
        except (OSError, subprocess.TimeoutExpired):
            return deny(event, payload)
        if proc.returncode != 0:  # a crash: its message may name a path, so it is not passed on
            return deny(event, payload)
        if proc.stdout.strip():  # a refusal: passed back unchanged
            sys.stdout.buffer.write(proc.stdout)
            return 0
        sys.stderr.buffer.write(proc.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
