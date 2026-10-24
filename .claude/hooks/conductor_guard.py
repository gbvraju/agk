#!/usr/bin/env python3
"""PreToolUse guard of the conductor role (SPEC-0030 rule 6).

Contract (verify; read from the Claude Code documentation on 2026-10-19, as for the architect's
guard): the hook receives JSON on stdin with `tool_name` and `tool_input`. To deny, it prints
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
"permissionDecisionReason": ...}} and exits 0; to allow, it prints nothing and exits 0.

Denies `Edit`, `Write`, `MultiEdit` and `NotebookEdit` everywhere, and `Bash` unless the command is
a read-only `git` command, `gh api` with `--method GET` or no method, the one `gh api --method POST`
of a comment on an issue or pull request of the repository named by this checkout's origin remote
(`-f` fields only), or `date -u`. A POST to anything else, a PATCH, a PUT, a DELETE, a script and
`make` are denied. The judging of `git` and `gh api` is the architect's (`architect_guard.py`),
which this file imports. The message names the rule, never the command or the path. Standard
library only; no network.
"""

from __future__ import annotations

import json
import sys

from architect_guard import WRITE_TOOLS, gh_api_allowed, git_allowed, tokens_of

WRITE_RULE = "conductor guard rule 6: the conductor writes no file"
BASH_RULE = "conductor guard rule 6: this command is not on the conductor's list"


def bash_allowed(command: object) -> bool:
    if not isinstance(command, str):
        return False
    words = tokens_of(command)
    if not words:
        return False
    if words[0] == "git":
        return git_allowed(words)
    if words[0] == "gh":
        return len(words) > 2 and words[1] == "api" and gh_api_allowed(words)
    if words[0] == "date":
        return all(w == "-u" or w.startswith("+") for w in words[1:])
    return False


def decide(payload: dict) -> str | None:
    """A denial text, or None to allow."""
    tool = payload.get("tool_name")
    data = payload.get("tool_input")
    data = data if isinstance(data, dict) else {}
    if tool in WRITE_TOOLS:
        return WRITE_RULE
    if tool == "Bash":
        return None if bash_allowed(data.get("command")) else BASH_RULE
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = None
    reason = decide(payload) if isinstance(payload, dict) else BASH_RULE
    if reason:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
