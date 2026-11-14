#!/usr/bin/env python3
"""Stop hook: run the governance checks a session's changes need and block stopping while red.

Brief #1254 (ADR-0531): with `[flow] stop_check = "changed"` (the default) the hook reads what the
session changed with local git only (`governance_map.changed_paths`). No change: it allows the stop
at once and runs nothing. Changes: it runs only the checks `governance_map.select` names, each with
this Python, in the recipe's order, stopping at the first red one; a path the map does not know, or
changes git cannot read, run the full `make -f agk.mk agk-governance` as before. `"full"` runs the
full set on every stop; `"off"` runs nothing (refused in solo review mode, and a refused setting
works as `"changed"`). Each run prints one `stop check: ...` line on standard error, and a blocking
run puts it first in its reason.

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
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

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


def settings(root: str) -> tuple[str, str, str | None]:
    """(mode, default branch, refusal line or None); the default mode when anything is wrong."""
    try:
        import config  # the installed module beside agk.mk's scripts

        cfg = config.load_config(Path(root))
        branch = cfg.get("default_branch") or "main"
    except Exception:  # noqa: BLE001 - a broken config must never stop the hook
        return "changed", "main", None
    try:
        return config.stop_check_mode(Path(root)), str(branch), None
    except config.CheckError as err:
        return "changed", str(branch), f"stop check: {err}; working as changed"


def selection(root: str, branch: str) -> tuple[list[tuple[str, ...]] | None, int | None, int]:
    """(commands, None for the full set; changed files, None when unread; size of the full set)."""
    try:
        import governance_map
    except Exception:  # noqa: BLE001 - without the map the hook runs the full set, as before
        return None, None, 0
    full = len(governance_map.CHECKS)
    paths = governance_map.changed_paths(Path(root), branch)
    if paths is None:
        return None, None, full
    return governance_map.select(paths), len(paths), full


def run_commands(root: str, env: dict, commands: list[tuple[str, ...]] | None):
    """(return code, output, failing command) of the full recipe (None) or of each command."""
    if commands is None:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["make", "-f", "agk.mk", "agk-governance"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TIMEOUT_SECONDS,
        )
        return proc.returncode, proc.stdout + proc.stderr, "make -f agk.mk agk-governance"
    deadline = time.monotonic() + TIMEOUT_SECONDS
    for argv in commands:
        left = max(1.0, deadline - time.monotonic())
        proc = subprocess.run(  # nosec B603 - fixed argument list from the map, no shell
            [sys.executable, *argv],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=left,
        )
        if proc.returncode != 0:
            return proc.returncode, proc.stdout + proc.stderr, " ".join(argv)
    return 0, "", ""


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
    mode, branch, refusal = settings(root)
    if refusal:
        print(refusal, file=sys.stderr)
    if mode == "off":
        print("stop check: off", file=sys.stderr)
        return 0
    commands, changed, full = selection(root, branch)
    if mode == "full":
        commands, changed = None, None
    if commands == []:
        print("stop check: no changes", file=sys.stderr)
        return 0
    began = time.monotonic()
    env = dict(os.environ)
    temp = None if env.get("AGK_PR_BODY") else body_file(root)
    if temp:
        env["AGK_PR_BODY"] = temp
    try:
        code, output, failed = run_commands(root, env, commands)
    except (OSError, subprocess.TimeoutExpired):
        return block("the governance checks could not run to completion; fix the environment.")
    finally:
        if temp:
            try:
                os.unlink(temp)
            except OSError:
                pass
    count = len(commands) if commands is not None else full
    seconds = f"{time.monotonic() - began:.1f} s"
    if mode == "full":
        line = f"stop check: {count} checks (full set), {seconds}"
    elif changed is None:
        line = f"stop check: {count} checks (changes not read), {seconds}"
    else:
        line = f"stop check: {count} checks for {changed} changed files, {seconds}"
    print(line, file=sys.stderr)
    if code == 0:
        return 0
    tail = "\n".join(output.splitlines()[-TAIL_LINES:])
    return block(f"{line}\n`{failed}` is red. Fix it before stopping.\n{tail}")


if __name__ == "__main__":
    sys.exit(main())
