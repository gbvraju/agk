#!/usr/bin/env python3
"""Stop hook: run `make -f agk.mk agk-governance` and block stopping while it is red.

Contract (verify): the hook receives JSON on stdin (including `stop_hook_active` and `cwd`);
printing {"decision": "block", "reason": ...} with exit code 0 keeps the session going.
When `stop_hook_active` is true the hook has already blocked once in this stop sequence; it then
allows the stop so that an unfixable failure cannot loop forever (verify).

When `AGK_PR_BODY` is unset, the hook reads the body of the open pull request whose head is the
checkout's branch (one GET through `gh api`), writes it to a temporary file and runs governance
with `AGK_PR_BODY` naming it, so `check_protected_changes.py` sees its `Covered-by:` line
(brief #1029, ADR-0438). Any failure to read runs governance as before; the file is removed.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
from urllib.parse import quote

TAIL_LINES = 30
TIMEOUT_SECONDS = 300
GH_TIMEOUT_SECONDS = 20


def block(reason: str) -> int:
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def git_out(root: str, *args: str) -> str | None:
    """The stripped output of a git command, or None when it fails."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=GH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = proc.stdout.strip()
    return out if proc.returncode == 0 and out else None


def origin_repo(url: str) -> tuple[str, str] | None:
    """Owner and repository from the last two parts of an `origin` URL (https, ssh or a proxy)."""
    path = url.rstrip("/").removesuffix(".git").replace(":", "/")
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return None
    return parts[-2], parts[-1]


def pull_request_body(root: str) -> str | None:
    """The body of the open pull request whose head is the current branch, or None."""
    branch = git_out(root, "symbolic-ref", "--short", "-q", "HEAD")
    url = git_out(root, "remote", "get-url", "origin")
    found = origin_repo(url) if url else None
    if not branch or not found:
        return None
    owner, repo = found
    route = f"repos/{owner}/{repo}/pulls?head={quote(owner)}:{quote(branch, safe='/')}&state=open"
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell, a GET
            ["gh", "api", route],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=GH_TIMEOUT_SECONDS,
        )
        pulls = json.loads(proc.stdout) if proc.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(pulls, list) or not pulls or not isinstance(pulls[0], dict):
        return None
    body = pulls[0].get("body")
    return body if isinstance(body, str) else None


def body_file(root: str) -> str | None:
    """A temporary file holding the pull request body, or None (the caller removes it)."""
    body = pull_request_body(root)
    if body is None:
        return None
    try:
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", prefix="agk-pr-body-", suffix=".md", delete=False
        )
        with handle:
            handle.write(body)
    except OSError:
        return None
    return handle.name


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
    env = dict(os.environ)
    temp = None if env.get("AGK_PR_BODY") else body_file(root)
    if temp:
        env["AGK_PR_BODY"] = temp
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["make", "-f", "agk.mk", "agk-governance"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return block(
            "`make -f agk.mk agk-governance` could not run to completion; fix the environment."
        )
    finally:
        if temp:
            try:
                os.unlink(temp)
            except OSError:
                pass
    if proc.returncode == 0:
        return 0
    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-TAIL_LINES:])
    return block(f"`make -f agk.mk agk-governance` is red. Fix it before stopping.\n{tail}")


if __name__ == "__main__":
    sys.exit(main())
