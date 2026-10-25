#!/usr/bin/env python3
"""PreToolUse guard of the conductor role (SPEC-0030 rule 6).

Contract (verify; read from the Claude Code documentation, as for the architect's
guard): the hook receives JSON on stdin with `tool_name` and `tool_input`. To deny, it prints
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
"permissionDecisionReason": ...}} and exits 0; to allow, it prints nothing and exits 0.

Denies `Edit`, `MultiEdit` and `NotebookEdit` everywhere, `Write` outside a scratch directory, and
`Bash` unless the command is one of: a read-only `git` command; `git fetch origin`; `gh api` with
`--method GET` or no method; the one `gh api --method POST` of a comment on an issue or pull request
of the repository named by this checkout's origin remote (`-f` fields only); `date -u`; or a bounded
run of a pull request in a scratch worktree (SPEC-0030 rule 6, amendment 53):
`git worktree add <scratch> <sha>` where the sha is on a branch of origin (a fork head is on none),
`git worktree remove [--force] <scratch>`, and, only with the exact prefix
`env -i PATH="$PATH" HOME=<scratch>` (the run's own scratch directory, so that neither an
environment token nor the home directory's stored credentials reach the code) and, optionally, one
`AGK_BASE=<sha>` right after it, as CI sets it,
`make -C <scratch> test` or `governance` and `python3 -I <scratch>/scripts/agk/<name>.py ...`.
A scratch directory is `agk-conductor-<name>` directly in the system temp directory and outside
the work tree. A POST
to anything else, a PATCH, a PUT, a DELETE, any other script and any other `make` are denied. The
judging of `git` and `gh api` is the architect's (`architect_guard.py`), which this file imports.
With the one argument `--shadow` (the shadow reviewer of SPEC-0035, `.claude/agents/shadow.md`) the
comment `POST` is allowed only on the issue-comment endpoint of the checkout's origin repository
and with exactly one field: `-f body=Shadow: #<pr> <sha> cleared|fix list|rejected` followed by
anything, or `-F body=@<file>` where the file is a regular file inside a scratch directory and its
first line has that shape, so that the findings of several lines can be posted: a verdict, a
`Marks:` comment, a file elsewhere or a second field is denied. The hook cannot tell the
`agk-shadow` issue from another issue without a network call, so that choice is the role file's
(a residual of SPEC-0035). Any other argument denies everything.
The message names the rule, never the command or the path. Standard library only; no network.
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile

from architect_guard import (
    WRITE_TOOLS,
    comment_target_ok,
    gh_api_allowed,
    git_allowed,
    project_root,
    tokens_of,
)

ENV_PREFIX = 'env -i PATH="$PATH" HOME='
BASE_VAR = "AGK_BASE="  # the one variable a run may add, a sha, as CI sets it
SCRATCH_NAME = re.compile(r"agk-conductor-[A-Za-z0-9._-]+")
SHA = re.compile(r"[0-9a-f]{7,40}")
SCRIPT = re.compile(r"(\w+)\.py")
WRITE_RULE = "conductor guard rule 6: the conductor writes only in a scratch directory"
BASH_RULE = "conductor guard rule 6: this command is not on the conductor's list"
SHADOW_BODY = re.compile(
    r"body=Shadow: #\d+ [0-9a-f]{7,40} (?:cleared|fix list|rejected)(?:\s.*)?", re.S
)
POST_METHODS = ("--method", "-X")
FIELDS = ("-f", "--raw-field")
FILE_FIELDS = ("-F", "--field")


def scratch_dir(path: str) -> str | None:
    """The real path of a scratch directory (or of a path inside one), else None."""
    if not path or "\0" in path or not os.path.isabs(path):
        return None
    real = os.path.realpath(path)
    temp = os.path.realpath(tempfile.gettempdir())
    rel = os.path.relpath(real, temp)
    top = rel.split(os.sep, 1)[0]
    root = os.path.realpath(project_root())
    inside = real == root or real.startswith(root + os.sep)
    if rel.startswith("..") or not SCRATCH_NAME.fullmatch(top) or inside:
        return None
    return os.path.join(temp, top)


def exact_scratch(path: str) -> bool:
    """A scratch directory itself, with no `..` or link between it and the temp directory."""
    found = scratch_dir(path)
    return found is not None and os.path.normpath(path) == found


def on_origin_branch(sha: str) -> bool:
    """The sha is contained in a remote-tracking branch of origin; a fork's head is in none."""
    if not SHA.fullmatch(sha):
        return False
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", project_root(), "branch", "-r", "--contains", sha, "--format=%(refname)"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and any(
        line.startswith("refs/remotes/origin/") and not line.endswith("/HEAD")
        for line in proc.stdout.splitlines()
    )


def run_allowed(words: list[str], home: str) -> bool:
    """`make -C <scratch> test|governance` or `python3 -I <scratch>/scripts/agk/<name>.py ...`,
    where <scratch> is `home`, the HOME of the clean environment."""
    if words[0] == "make":
        return (
            len(words) == 4
            and words[1] == "-C"
            and words[3] in ("test", "governance")
            and words[2] == home
        )
    if words[0] == "python3" and len(words) > 2 and words[1] == "-I":
        head, name = os.path.split(words[2])
        scripts, agk = os.path.split(head)
        scratch, scripts_dir = os.path.split(scripts)
        return (
            agk == "agk"
            and scripts_dir == "scripts"
            and bool(SCRIPT.fullmatch(name))
            and scratch == home
        )
    return False


def git_judged(words: list[str]) -> bool:
    """`git fetch origin`, the scratch worktree commands, or a read-only `git` command."""
    if words[1:] == ["fetch", "origin"]:
        return True
    if len(words) > 2 and words[1] == "worktree":
        rest = words[2:]
        if len(rest) == 3 and rest[0] == "add":
            return exact_scratch(rest[1]) and on_origin_branch(rest[2])
        if rest[:1] == ["remove"] and len(rest) in (2, 3):
            return exact_scratch(rest[-1]) and rest[1:-1] in ([], ["--force"])
        return False
    return git_allowed(words)


def is_post(words: list[str]) -> bool:
    args = words[2:]
    methods = [args[i + 1].upper() for i, a in enumerate(args[:-1]) if a in POST_METHODS] + [
        a.split("=", 1)[1].upper() for a in args if a.startswith("--method=")
    ]
    return "POST" in methods


def shadow_post_ok(words: list[str]) -> bool:
    """In shadow mode a `POST` carries one field: a `Shadow:` body given inline with `-f`, or read
    from a file of a scratch directory with `-F body=@<file>` whose first line is a `Shadow:` line,
    on the issue-comment endpoint of the origin repository."""
    args = words[2:]
    endpoint = [a for a in args if a.startswith(("repos/", "/repos/"))]
    fields = [(a, args[i + 1]) for i, a in enumerate(args[:-1]) if a in FIELDS + FILE_FIELDS]
    others = [a for a in args if a.startswith("-") and a not in POST_METHODS + FIELDS + FILE_FIELDS]
    if len(endpoint) != 1 or not comment_target_ok(endpoint[0]) or len(fields) != 1 or others:
        return False
    flag, value = fields[0]
    if flag in FIELDS:
        return SHADOW_BODY.fullmatch(value) is not None
    return value.startswith("body=@") and shadow_file_ok(value[len("body=@") :])


def shadow_file_ok(path: str) -> bool:
    """A regular file inside a scratch directory whose first line is a `Shadow:` line."""
    real = scratch_dir(path)
    if real is None or os.path.realpath(path) != os.path.normpath(path) or not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as handle:
            first = handle.readline(512).rstrip("\n")
    except (OSError, UnicodeDecodeError):
        return False
    return SHADOW_BODY.fullmatch("body=" + first) is not None


def bash_allowed(command: object, shadow: bool = False) -> bool:
    if not isinstance(command, str):
        return False
    clean = command.startswith(ENV_PREFIX)
    words = tokens_of(command[len(ENV_PREFIX) :] if clean else command)
    if not words:
        return False
    if clean:
        home, rest = words[0], words[1:]
        if rest and rest[0].startswith(BASE_VAR):  # one optional AGK_BASE=<sha>, nothing else
            if not SHA.fullmatch(rest[0][len(BASE_VAR) :]):
                return False
            rest = rest[1:]
        return bool(rest) and exact_scratch(home) and run_allowed(rest, home)
    if words[0] == "git":
        return git_judged(words)
    if words[0] == "gh":
        if len(words) < 3 or words[1] != "api":
            return False
        if shadow and is_post(words):
            return shadow_post_ok(words)
        return gh_api_allowed(words)
    if words[0] == "date":
        return all(w == "-u" or w.startswith("+") for w in words[1:])
    return False


def decide(payload: dict, shadow: bool = False) -> str | None:
    """A denial text, or None to allow."""
    tool = payload.get("tool_name")
    data = payload.get("tool_input")
    data = data if isinstance(data, dict) else {}
    if tool in WRITE_TOOLS:
        target = data.get("file_path")
        ok = tool == "Write" and isinstance(target, str) and scratch_dir(target) is not None
        return None if ok else WRITE_RULE
    if tool == "Bash":
        return None if bash_allowed(data.get("command"), shadow) else BASH_RULE
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = None
    arguments = sys.argv[1:]
    if arguments not in ([], ["--shadow"]):  # an unknown argument fails closed
        reason = BASH_RULE
    else:
        shadow = arguments == ["--shadow"]
        reason = decide(payload, shadow) if isinstance(payload, dict) else BASH_RULE
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
