#!/usr/bin/env python3
"""PreToolUse guard of the architect role (SPEC-0013 rule 9).

Contract (verify; read from the Claude Code documentation): the hook receives JSON on
stdin with `tool_name` and `tool_input` (`file_path` for Edit and Write, `command` for Bash). To
deny, it prints {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision":
"deny", "permissionDecisionReason": ...}} and exits 0; to allow, it prints nothing and exits 0.
A hook of a project agent runs only in a trusted folder (verify for the `--agent` main session).

With the argument `--review` (the read-only review agent, SPEC-0023) it denies `Edit`, `Write`,
`MultiEdit` and `NotebookEdit` everywhere, `docs/` included, and judges `Bash` the same way.

Denies `Edit`, `Write`, `MultiEdit` and `NotebookEdit` outside `docs/` and `constitution/vision.md`,
and `Bash` unless the command is one of: a read-only `git` command; `gh api` with `--method GET` or
no method (and no field or input flag); `gh api --method POST` to the comments of an issue or pull
request of the repository named by this checkout's origin remote (read from `.git/config`), with
`-f` fields only; `date -u`; `make governance`; or a read-only script of `scripts/agk/`
(READ_ONLY_SCRIPTS). Options of an allowed `git` command that run a program, write a file or reach a
config-driven command are denied (GIT_FORBIDDEN_LONG). Shell operators, substitutions, redirections
and a `#` outside a quoted string (brief #351: bash and the lexer read it differently) are denied.
The message names the rule, never the command or the path. Standard library only; no network.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

READ_ONLY_SCRIPTS = frozenset(
    {
        "check_adrs",
        "check_build_state",
        "check_kit_tests",
        "check_neutrality",
        "check_pr_body",
        "check_protected_changes",
        "check_requirements",
        "check_review_report",
        "check_specs",
        "doctor",
        "facts",
        "product_report",
        "review_context",
        "traceability",
    }
)
READ_GIT = frozenset(
    {
        "status",
        "diff",
        "log",
        "show",
        "rev-parse",
        "ls-files",
        "ls-tree",
        "blame",
        "cat-file",
        "merge-base",
        "describe",
        "shortlog",
        "grep",
        "rev-list",
        "name-rev",
        "show-ref",
    }
)
BRANCH_READ = frozenset({"--list", "-a", "-r", "-v", "-vv", "--show-current", "--all", "--remotes"})
WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
WRITE_ALLOWED_FILE = "constitution/vision.md"
COMMENT_ENDPOINT = re.compile(r"^/?repos/([^/\s]+)/([^/\s]+)/issues/\d+/comments$")
FIELD_FLAGS = frozenset({"-f", "--raw-field", "-F", "--field", "--input"})
UNSAFE = re.compile(r"[$`\n\r]")
# Options of an allowed `git` subcommand that run a program, write a file or reach a config-driven
# command (a pager, an external diff, a text conversion, a filter, a signature check). Git accepts
# any unambiguous prefix of a long option, so a long word is denied when it is a prefix of one of
# these; a short-option cluster is denied when it holds `O` (`-O<pager>` runs the pager).
GIT_FORBIDDEN_LONG = (
    "open-files-in-pager",
    "ext-diff",
    "textconv",
    "filters",
    "output",
    "exec",
    "exec-path",
    "show-signature",
    "upload-pack",
    "receive-pack",
    "config-env",
    "git-dir",
    "work-tree",
    "paginate",
)
SHORT_WITH_O = re.compile(r"^-[A-Za-z0-9]*O")
REMOTE_SECTION = re.compile(r'^\[remote "origin"\]\s*$')
URL_LINE = re.compile(r"^\s*url\s*=\s*(\S.*?)\s*$")
PATH_RULE = "architect guard rule 9: writes only under docs/ and constitution/vision.md"
BASH_RULE = "architect guard rule 9: this command is not on the architect's list"
REVIEW_RULE = "architect guard rule 9: the review agent writes nothing"


def project_root() -> str:
    return os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def path_allowed(file_path: object, root: str) -> bool:
    if not isinstance(file_path, str) or not file_path or "\0" in file_path:
        return False
    full = file_path if os.path.isabs(file_path) else os.path.join(root, file_path)
    real = os.path.realpath(full)  # follows symlinks, resolves `..`, works for a new file
    rel = os.path.relpath(real, root)
    if rel.startswith(".."):
        return False
    return rel.startswith("docs" + os.sep) or rel == WRITE_ALLOWED_FILE


def hash_outside_quotes(command: str) -> bool:
    """True when a `#` stands outside a quoted string, escaped or not (brief #351).

    Bash starts a comment with a `#` only at the start of a word, while the lexer's default starts
    one anywhere; a command whose `#` the two could read differently is refused, never guessed.
    """
    quote = ""
    escaped = False
    for c in command:
        if escaped:
            escaped = False
            if c == "#" and not quote:
                return True
        elif quote == "'":
            quote = "" if c == "'" else quote
        elif c == "\\":
            escaped = True
        elif quote == '"':
            quote = "" if c == '"' else quote
        elif c in "'\"":
            quote = c
        elif c == "#":
            return True
    return False


def tokens_of(command: str) -> list[str] | None:
    """The words of a simple command, or None when it has an operator, a substitution or a `#`
    outside a quoted string (brief #351: the words are the words bash would pass)."""
    if UNSAFE.search(command) or hash_outside_quotes(command):
        return None
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.commenters = ""
    lexer.whitespace_split = True
    try:
        words = list(lexer)
    except ValueError:
        return None
    if any(w and all(c in "();<>|&" for c in w) for w in words):
        return None
    return words


def git_option_denied(word: str) -> bool:
    if word.startswith("--"):
        name = word[2:].split("=", 1)[0]
        return bool(name) and any(f.startswith(name) for f in GIT_FORBIDDEN_LONG)
    return bool(SHORT_WITH_O.match(word))


def git_allowed(words: list[str]) -> bool:
    if len(words) < 2 or words[1].startswith("-"):
        return False
    if any(git_option_denied(w) for w in words[2:]):
        return False
    if words[1] == "branch":
        return all(w in BRANCH_READ for w in words[2:])
    return words[1] in READ_GIT


def origin_repo(root: str) -> str | None:
    """`owner/repo` of the origin remote, read from the git config; None if unreadable."""
    git_dir = os.path.join(root, ".git")
    try:
        if os.path.isfile(git_dir):
            with open(git_dir, encoding="utf-8") as fh:
                first = fh.readline().strip()
            if not first.startswith("gitdir:"):
                return None
            git_dir = os.path.normpath(os.path.join(root, first.split(":", 1)[1].strip()))
            common = os.path.join(git_dir, "commondir")
            if os.path.isfile(common):
                with open(common, encoding="utf-8") as fh:
                    git_dir = os.path.normpath(os.path.join(git_dir, fh.readline().strip()))
        with open(os.path.join(git_dir, "config"), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    urls: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("["):
            inside = bool(REMOTE_SECTION.match(line.strip()))
        elif inside:
            match = URL_LINE.match(line)
            if match:
                urls.append(match.group(1))
    names = set()
    for url in urls:
        parts = [p for p in re.split(r"[/:]", url.removesuffix("/").removesuffix(".git")) if p]
        if len(parts) < 2:
            return None
        names.add(f"{parts[-2]}/{parts[-1]}".lower())
    return names.pop() if len(names) == 1 else None


def comment_target_ok(endpoint: str) -> bool:
    """A comment POST names the repository of this checkout's origin remote, and no other."""
    match = COMMENT_ENDPOINT.match(endpoint)
    if not match:
        return False
    own = origin_repo(project_root())
    return own is not None and f"{match.group(1)}/{match.group(2)}".lower() == own


def gh_api_allowed(words: list[str]) -> bool:
    args = words[2:]
    method = None
    endpoint = None
    flags: set[str] = set()
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--method", "-X"):
            method = args[i + 1].upper() if i + 1 < len(args) else None
            i += 2
            continue
        if arg.startswith("--method="):
            method = arg.split("=", 1)[1].upper()
        elif arg in FIELD_FLAGS:
            flags.add(arg)
            i += 2
            continue
        elif arg.startswith("-"):
            if arg in ("-H", "--header", "--jq", "-q", "--template", "-t", "--cache", "--hostname"):
                i += 2
                continue
        elif endpoint is None:
            endpoint = arg
        else:
            return False
        i += 1
    if endpoint is None or not endpoint.lstrip("/").startswith("repos/"):
        return False
    if method == "GET" or (method is None and not flags):
        return not (flags & {"--input"})
    if method == "POST" and comment_target_ok(endpoint):
        return bool(flags) and flags <= {"-f", "--raw-field"}
    return False


def bash_allowed(command: object) -> bool:
    if not isinstance(command, str):
        return False
    words = tokens_of(command)
    if not words:
        return False
    head = words[0]
    if head == "git":
        return git_allowed(words)
    if head == "gh":
        return len(words) > 2 and words[1] == "api" and gh_api_allowed(words)
    if head == "date":
        return all(w == "-u" or w.startswith("+") for w in words[1:])
    if head == "make":
        return words[1:] in (["governance"], ["-f", "agk.mk", "agk-governance"])
    if head == "python3" and len(words) > 1:
        match = re.fullmatch(r"(?:\./)?scripts/agk/(\w+)\.py", words[1])
        return bool(match) and match.group(1) in READ_ONLY_SCRIPTS and "--write" not in words
    return False


def decide(payload: dict, review: bool = False) -> str | None:
    """A denial text, or None to allow; in review mode no write is ever allowed."""
    tool = payload.get("tool_name")
    data = payload.get("tool_input")
    data = data if isinstance(data, dict) else {}
    if tool in WRITE_TOOLS:
        if review:
            return REVIEW_RULE
        target = data.get("file_path", data.get("notebook_path"))
        return None if path_allowed(target, project_root()) else PATH_RULE
    if tool == "Bash":
        return None if bash_allowed(data.get("command")) else BASH_RULE
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = None
    review = "--review" in sys.argv[1:]
    reason = decide(payload, review) if isinstance(payload, dict) else BASH_RULE
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
