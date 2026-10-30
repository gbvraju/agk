#!/usr/bin/env python3
"""PreToolUse guard of the conductor role (SPEC-0030 rule 6).

Contract (verify; read from the Claude Code documentation, as for the architect's
guard): the hook receives JSON on stdin with `tool_name` and `tool_input`. To deny, it prints
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
"permissionDecisionReason": ...}} and exits 0; to allow, it prints nothing and exits 0.

Denies `Edit`, `MultiEdit` and `NotebookEdit` everywhere, `Write` outside a scratch directory, and
`Bash` unless the command is one of: a read-only `git` command; `git fetch origin`; `gh api` with
`--method GET` or no method; the one `gh api --method POST` of a comment on an issue or pull request
of the repository named by this checkout's origin remote (`-f` fields only, or one `-F body=@<file>`
where the file is a regular file of a scratch directory); `date -u`; or a bounded
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
A comment whose body starts with `Verdict:` is read with `common.verdict_problem` (the reading the
router applies, brief 238) and denied, with that message, when the router could not read a `Final:`
line of it. With the one argument `--shadow` (the shadow reviewer of SPEC-0035,
`.claude/agents/shadow.md`) the comment `POST` is allowed only on the issue-comment endpoint of the
checkout's origin repository and with exactly one field: `-f body=Shadow: #<pr> <sha> cleared|fix
list|rejected` followed by anything, or `-F body=@<file>` where the file is a regular file inside a
scratch directory and its first line has that shape, so that the findings of several lines can be
posted: a verdict, a `Marks:` comment, a file elsewhere or a second field is denied. The hook
cannot tell the `agk-shadow` issue from another issue without a network call, so that choice is the
role file's (a residual of SPEC-0035). Any other argument denies everything.
Without `--shadow` the conductor may also file a brief (brief 276, ADR-0170): the one issue creation
`gh api --method POST repos/<origin>/issues` with exactly three fields, `-f title=<text>`,
`-f labels[]=agk-brief` and `-F body=@<file>`, where the file is a regular file of a scratch
directory (no link out of it, at most 65536 characters) that `check_brief.py FILE --root <project>`
accepts. Any other label or a second one, another field or flag, another repository, an issue
edit, a label creation and an inline body stay denied; the shadow mode files nothing.
Without `--shadow` the conductor may also read its queue (brief 284, ADR-0175) with the project's
own script, the regular file `scripts/agk/session.py` of the project directory (named relative to
the session's working directory or by its full path, never through a link): exactly
`python3 scripts/agk/session.py review-queue`, with `--all` or `--fingerprint` or neither, and
`python3 scripts/agk/session.py queue --role conductor`. Both only read GitHub (GET); every other
command of the script (`watch`, `next`, `claim`, `after` and the rest), another role, another flag,
another interpreter or another copy of the script, such as one in a pull request's worktree, stays
denied, and the shadow mode gets none of them.
A comment whose first line is `Confirmed:` (the person's one yes of solo mode, brief 277) is refused
by name in both modes: only the person posts it, from the browser or the GitHub app (session rule
29), because GitHub cannot tell a comment the person typed from one a session posted.
A comment `POST` whose `body=@` file is not an absolute path is refused with a message that names
the likely cause (a backslash path loses its backslashes in a POSIX shell such as Git Bash), so
that the conductor writes the forward-slash form; nothing more is allowed by it.
The message names the rule, never the command or the path. Standard library only; no network.
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
from pathlib import Path

from architect_guard import (
    WRITE_TOOLS,
    comment_target_ok,
    gh_api_allowed,
    git_allowed,
    origin_repo,
    project_root,
    tokens_of,
)

SCRIPTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "agk"
)
try:  # the one reading of a verdict, shared with the router (brief 238)
    sys.path.insert(0, SCRIPTS)
    import common

    READ_VERDICT = common.verdict_problem
except ImportError:  # a checkout without the scripts: the hook cannot judge a verdict
    READ_VERDICT = None
try:  # the one reading of a brief, `check_brief.py`'s (brief 276)
    import check_brief

    BRIEF_PROBLEMS = check_brief.brief_problems
    ABSENT_REQUIREMENTS = check_brief.absent_requirements
except ImportError:  # without the check no brief is filed
    BRIEF_PROBLEMS = ABSENT_REQUIREMENTS = None

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
ISSUES_ENDPOINT = re.compile(r"^/?repos/([^/\s]+)/([^/\s]+)/issues$")
BRIEF_LABEL = "labels[]=agk-brief"
BODY_LIMIT = 65536  # GitHub's limit of an issue body; a longer file is not read in part
SESSION_SCRIPT = os.path.join("scripts", "agk", "session.py")
QUEUE_FORMS = (  # the read-only commands of the conductor's queue (brief 284), exactly these
    ["review-queue"],
    ["review-queue", "--all"],
    ["review-queue", "--fingerprint"],
    ["queue", "--role", "conductor"],
)
CONFIRMED_RULE = (
    "conductor guard rule 6: a session never posts a Confirmed: comment; print the text and the "
    "person posts it (session rule 29)"
)
PATH_RULE = (
    "conductor guard rule 6: the comment's body file is not an absolute path of a scratch "
    "directory; write the path with forward slashes (a backslash path loses its backslashes in a "
    "POSIX shell)"
)


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
        encoding="utf-8",
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


def scratch_text(path: str) -> str | None:
    """The text of a regular file inside a scratch directory (no link out of it), else None."""
    if scratch_dir(path) is None or os.path.realpath(path) != os.path.normpath(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read(65536) if os.path.isfile(path) else None
    except (OSError, UnicodeDecodeError):
        return None


def comment_body(words: list[str]) -> str | None:
    """The body of a comment `POST` (`-f body=...` or `-F body=@<scratch file>`), else None."""
    args = words[2:]
    if not is_post(words) or sum(1 for a in args if a.startswith(("repos/", "/repos/"))) != 1:
        return None
    for i, flag in enumerate(args[:-1]):
        value = args[i + 1]
        if flag in FIELDS and value.startswith("body="):
            return value[len("body=") :]
        if flag in FILE_FIELDS and value.startswith("body=@"):
            return scratch_text(value[len("body=@") :])
    return None


def confirmed_denial(command: object) -> str | None:
    """The reason to deny a comment whose first line is `Confirmed:` (brief 277), else None."""
    words = tokens_of(command) if isinstance(command, str) else None
    if not words or words[:2] != ["gh", "api"]:
        return None
    body = comment_body(words)
    return CONFIRMED_RULE if body is not None and body.lstrip().startswith("Confirmed:") else None


def verdict_denial(command: object) -> str | None:
    """The reason to deny a comment whose body is a `Verdict:` with a problem, else None."""
    words = tokens_of(command) if isinstance(command, str) else None
    if not words or words[:2] != ["gh", "api"]:
        return None
    body = comment_body(words)
    problem = READ_VERDICT(body) if body is not None and READ_VERDICT else None
    return f"conductor guard rule 6: {problem}" if problem else None


def conductor_file_post_ok(words: list[str]) -> bool:
    """The conductor's comment `POST` of a body from a scratch file: one field, the origin's
    issue-comment endpoint."""
    args = words[2:]
    endpoint = [a for a in args if a.startswith(("repos/", "/repos/"))]
    fields = [(a, args[i + 1]) for i, a in enumerate(args[:-1]) if a in FIELDS + FILE_FIELDS]
    others = [a for a in args if a.startswith("-") and a not in POST_METHODS + FIELDS + FILE_FIELDS]
    if len(endpoint) != 1 or not comment_target_ok(endpoint[0]) or len(fields) != 1 or others:
        return False
    flag, value = fields[0]
    return (
        flag in FILE_FIELDS and value.startswith("body=@") and scratch_text(value[6:]) is not None
    )


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


def brief_text(path: str) -> str | None:
    """The whole text of a regular file of a scratch directory (no link out of it), else None."""
    if scratch_dir(path) is None or os.path.realpath(path) != os.path.normpath(path):
        return None
    try:
        if not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8") as handle:
            text = handle.read(BODY_LIMIT + 1)
    except (OSError, UnicodeDecodeError):
        return None
    return text if len(text) <= BODY_LIMIT else None


def brief_checked(text: str) -> bool:
    """`check_brief.py FILE --root <project>` accepts the text: the shape and the requirements."""
    if BRIEF_PROBLEMS is None or ABSENT_REQUIREMENTS is None or BRIEF_PROBLEMS(text):
        return False
    try:
        return not ABSENT_REQUIREMENTS(text, Path(project_root()))
    except check_brief.CheckError:  # an unreadable requirements file files nothing
        return False


def brief_post_ok(words: list[str]) -> bool:
    """The one issue creation of the conductor (brief 276): `POST repos/<origin>/issues` with
    exactly one `-f title=<text>`, one `-f labels[]=agk-brief` and one `-F body=@<file>`, the file
    a regular file of a scratch directory that `check_brief.py` accepts; no other flag or field."""
    args = words[2:]
    endpoint: list[str] = []
    fields: list[tuple[str, str]] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in POST_METHODS + FIELDS + FILE_FIELDS:
            if i + 1 >= len(args):
                return False
            if arg in POST_METHODS:
                if args[i + 1].upper() != "POST":
                    return False
            else:
                fields.append((arg, args[i + 1]))
            i += 2
            continue
        if arg.startswith("--method="):
            if arg.split("=", 1)[1].upper() != "POST":
                return False
        elif arg.startswith("-"):
            return False
        else:
            endpoint.append(arg)
        i += 1
    match = ISSUES_ENDPOINT.match(endpoint[0]) if len(endpoint) == 1 else None
    own = origin_repo(project_root())
    if not match or own is None or f"{match.group(1)}/{match.group(2)}".lower() != own:
        return False
    if len(fields) != 3:
        return False
    titles = [v for f, v in fields if f in FIELDS and v.startswith("title=") and v[6:].strip()]
    labels = [v for f, v in fields if f in FIELDS and v == BRIEF_LABEL]
    bodies = [v[6:] for f, v in fields if f in FILE_FIELDS and v.startswith("body=@")]
    if len(titles) != 1 or len(labels) != 1 or len(bodies) != 1:
        return False
    text = brief_text(bodies[0])
    return text is not None and brief_checked(text)


def queue_allowed(words: list[str], cwd: object) -> bool:
    """`python3 scripts/agk/session.py review-queue [--all | --fingerprint]` or `... queue --role
    conductor`, where the script is the regular file of the project directory itself (brief 284)."""
    if len(words) < 2 or words[0] != "python3" or words[2:] not in QUEUE_FORMS:
        return False
    path = words[1]
    if not path or "\0" in path or path.startswith("-"):
        return False
    base = cwd if isinstance(cwd, str) and os.path.isabs(cwd) else os.getcwd()
    full = os.path.join(base, path)
    own = os.path.join(os.path.realpath(project_root()), SESSION_SCRIPT)
    return os.path.realpath(full) == own and os.path.isfile(own) and not os.path.islink(full)


def body_path_not_absolute(command: object) -> bool:
    """A comment `POST` whose `body=@` file is not an absolute path (brief 284, field note)."""
    words = tokens_of(command) if isinstance(command, str) else None
    if not words or words[:2] != ["gh", "api"] or not is_post(words):
        return False
    args = words[2:]
    return any(
        flag in FILE_FIELDS
        and value.startswith("body=@")
        and not os.path.isabs(value[len("body=@") :])
        for flag, value in zip(args, args[1:], strict=False)
    )


def bash_allowed(command: object, shadow: bool = False, cwd: object = None) -> bool:
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
        if is_post(words) and brief_post_ok(words):
            return True
        if is_post(words) and any(a in FILE_FIELDS for a in words[2:]):
            return conductor_file_post_ok(words)
        return gh_api_allowed(words)
    if words[0] == "date":
        return all(w == "-u" or w.startswith("+") for w in words[1:])
    if words[0] == "python3" and not shadow:
        return queue_allowed(words, cwd)
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
        if message := confirmed_denial(data.get("command")):
            return message
        if not shadow and (message := verdict_denial(data.get("command"))):
            return message
        command = data.get("command")
        if bash_allowed(command, shadow, payload.get("cwd")):
            return None
        return PATH_RULE if body_path_not_absolute(command) else BASH_RULE
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
