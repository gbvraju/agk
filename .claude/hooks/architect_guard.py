#!/usr/bin/env python3
"""PreToolUse guard of the architect role (SPEC-0013 rule 9).

Contract (verify; read from the Claude Code documentation): the hook receives JSON on
stdin with `tool_name` and `tool_input` (`file_path` for Edit and Write, `command` for Bash). To
deny, it prints {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision":
"deny", "permissionDecisionReason": ...}} and exits 0; to allow, it prints nothing and exits 0.
A hook of a project agent runs only in a trusted folder (verify for the `--agent` main session).

With the argument `--review` (the review agent, SPEC-0023) it denies `Edit`, `MultiEdit` and
`NotebookEdit` everywhere, `docs/` included, and `Write` everywhere but a regular file inside a
review scratch directory: `agk-review-<name>` directly in the system temp directory and outside the
project, judged by its real path, with no link and no `..` out of it (brief #1050, Q-1013-3,
ADR-0444; the limit of the conductor's guard). It judges `Bash` the same way, and allows besides
`evidence.py check RECORD [--head SHA] [--sample N] [--json]` (brief #982), which writes nothing in
the repository: its worktree is a temporary folder it removes; and the steps of a reviewer slot run
(`.claude/agents/architect-review.md`, brief #1050), exactly: `git fetch origin`;
`git checkout --detach <sha>`, the sha 7 to 40 lower-case hex characters and on a branch of origin
(a fork's head is on none; the conductor guard's `on_origin_branch`, imported for that one step,
runs the one `git branch -r --contains`);
`python3 scripts/agk/conductor.py check-verdict <file> --pr <n>`; the bundle saved with one `>`,
`python3 scripts/agk/review_bundle.py --pr <n> --sha <40-hex> [--base <ref>] > <file>` (brief
#1248, ADR-0528: the one redirect allowed); a comment `POST` to this
repository's issue comments with the one field `-F body=@<file>` whose first
line is a `Verdict:` line; and `python3 scripts/agk/session.py slot (--next | --release) r<N>`, a
reviewer slot (`session.REVIEWER_NAME`) only. Each file there is an existing regular file of a
review scratch directory. Any other option, slot name or file stays denied, and without
`--review` none of it is allowed.

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
import tempfile

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
        "review_bundle",
        "review_context",
        "traceability",
    }
)
# Brief #982: the review agent alone re-runs the evidence check, in this one form.
REVIEW_SCRIPT = re.compile(r"(?:\./)?scripts/agk/evidence\.py")
EVIDENCE_VALUES = {"--head": re.compile(r"[0-9a-fA-F]{7,40}"), "--sample": re.compile(r"[1-9]\d*")}
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
REVIEW_RULE = "architect guard rule 9: the review agent writes only in its scratch directory"
# Brief #1050 (ADR-0444): the reviewer slot's steps. The scratch test is the conductor guard's
# (`conductor_guard.scratch_dir`) with this role's name; it is copied, not imported, because that
# function reads the conductor's name and the conductor's guard imports this file.
REVIEW_SCRATCH = re.compile(r"agk-review-[A-Za-z0-9._-]+")
REVIEW_SHA = re.compile(r"[0-9a-f]{7,40}")
REVIEWER_NAME = re.compile(r"r[1-9]\d*")  # session.REVIEWER_NAME (brief #1013); a test pins it
PR_NUMBER = re.compile(r"[1-9][0-9]{0,9}")
SESSION_WORD = re.compile(r"(?:\./)?scripts/agk/session\.py")
CONDUCTOR_WORD = re.compile(r"(?:\./)?scripts/agk/conductor\.py")


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


GH_VALUE_OPTIONS = ("-H", "--header", "--jq", "-q", "--template", "-t", "--cache", "--hostname")
GH_FLAGS = ("--paginate", "--slurp", "--silent", "-i", "--include", "--verbose")


def gh_api_items(args: list[str]):
    """The arguments of `gh api` as `gh` reads them, one `(kind, arg, value)` at a time: kind is
    `method` (in each form: `--method V`, `--method=V`, `-X V`, `-XV`, `-X=V`; value upper-cased),
    `field`, `value` (a read-only option and its value), `flag`, `unknown` or `positional`. The one
    reading of the method, shared by the architect's and the conductor's guards (brief #531)."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--method", "-X"):
            yield "method", arg, args[i + 1].upper() if i + 1 < len(args) else ""
            i += 2
            continue
        if arg in FIELD_FLAGS or arg in GH_VALUE_OPTIONS:
            kind = "field" if arg in FIELD_FLAGS else "value"
            yield kind, arg, args[i + 1] if i + 1 < len(args) else ""
            i += 2
            continue
        if arg.startswith("--method="):
            yield "method", arg, arg.split("=", 1)[1].upper()
        elif arg.startswith("-X"):
            yield "method", arg, arg[2:].removeprefix("=").upper()
        elif arg.startswith("-"):
            known = arg in GH_FLAGS or (
                arg.startswith("--") and arg.split("=", 1)[0] in GH_VALUE_OPTIONS and "=" in arg
            )
            yield ("flag" if known else "unknown"), arg, ""
        else:
            yield "positional", arg, ""
        i += 1


def gh_api_methods(words: list[str]) -> list[str]:
    """Every method a `gh api` command names, in order, read by `gh_api_items`."""
    return [value for kind, _, value in gh_api_items(words[2:]) if kind == "method"]


def gh_api_allowed(words: list[str]) -> bool:
    """Every option is one the guard knows: the method in each form `gh` reads (`--method V`,
    `--method=V`, `-X V`, `-XV`, `-X=V`), a field, a read-only option; any other is denied."""
    method = None
    endpoint = None
    flags: set[str] = set()
    for kind, arg, value in gh_api_items(words[2:]):
        if kind == "method":
            method = value
        elif kind == "field":
            flags.add(arg)
        elif kind == "unknown":
            return False
        elif kind == "positional":
            if endpoint is not None:
                return False
            endpoint = arg
    if endpoint is None or not endpoint.lstrip("/").startswith("repos/"):
        return False
    if method == "GET" or (method is None and not flags):
        return not (flags & {"--input"})
    if method == "POST" and comment_target_ok(endpoint):
        return bool(flags) and flags <= {"-f", "--raw-field"}
    return False


def evidence_check_allowed(args: list[str]) -> bool:
    """`check` and one record, with only the options that change no file (brief #982)."""
    if not args or args[0] != "check":
        return False
    records, i = 0, 1
    while i < len(args):
        arg = args[i]
        if arg in EVIDENCE_VALUES:
            if i + 1 >= len(args) or not EVIDENCE_VALUES[arg].fullmatch(args[i + 1]):
                return False
            i += 2
            continue
        if arg != "--json":
            if arg.startswith("-"):
                return False
            records += 1
        i += 1
    return records == 1


def bash_allowed(command: object, review: bool = False) -> bool:
    if not isinstance(command, str):
        return False
    if review and bundle_save_allowed(command):
        return True
    words = tokens_of(command)
    if not words:
        return False
    head = words[0]
    if review and review_step_allowed(words):
        return True
    if review and head == "python3" and len(words) > 1 and REVIEW_SCRIPT.fullmatch(words[1]):
        return evidence_check_allowed(words[2:])
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


def review_scratch(path: object) -> str | None:
    """The real path of a review scratch directory that `path` is inside, else None: an absolute
    path with no `..`, whose real path is below `agk-review-<name>` directly in the system temp
    directory and outside the project (brief #1050; as `conductor_guard.scratch_dir`)."""
    if not isinstance(path, str) or not path or "\0" in path or not os.path.isabs(path):
        return None
    if ".." in path.split(os.sep):
        return None
    real = os.path.realpath(path)
    temp = os.path.realpath(tempfile.gettempdir())
    rel = os.path.relpath(real, temp)
    parts = rel.split(os.sep)
    root = project_root()
    inside = real == root or real.startswith(root + os.sep)
    if rel.startswith("..") or len(parts) < 2 or not REVIEW_SCRATCH.fullmatch(parts[0]) or inside:
        return None
    return os.path.join(temp, parts[0])


def review_write_ok(path: object) -> bool:
    """`Write` of a regular file (new or existing, never a folder) of a review scratch directory."""
    return review_scratch(path) is not None and not os.path.isdir(os.path.realpath(str(path)))


def review_file(path: str) -> str | None:
    """The first line of an existing regular file of a review scratch directory reached through no
    link, else None."""
    if review_scratch(path) is None or os.path.realpath(path) != os.path.normpath(path):
        return None
    try:
        if not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8") as handle:
            return handle.readline(512).rstrip("\n")
    except (OSError, UnicodeDecodeError):
        return None


def on_origin_branch(sha: str) -> bool:
    """The sha is on a branch of origin: the conductor guard's own test (`git branch -r --contains`,
    which reads only the local refs), imported when a checkout is judged; this file runs no command
    of its own."""
    if not REVIEW_SHA.fullmatch(sha):
        return False
    try:
        import conductor_guard  # imports this file; read late, so there is no import cycle
    except ImportError:  # without the conductor's guard no head is checked out
        return False
    return conductor_guard.on_origin_branch(sha)


def verdict_post_ok(words: list[str]) -> bool:
    """A comment `POST` to the origin's issue comments with the one field `-F body=@<file>`, the
    file a review scratch file whose first line is a `Verdict:` line; nothing else."""
    methods, fields, endpoints = [], [], []
    for kind, arg, value in gh_api_items(words[2:]):
        if kind == "method":
            methods.append(value)
        elif kind == "field":
            fields.append((arg, value))
        elif kind == "positional":
            endpoints.append(arg)
        else:
            return False
    if not methods or set(methods) != {"POST"} or len(endpoints) != 1 or len(fields) != 1:
        return False
    flag, value = fields[0]
    if flag != "-F" or not value.startswith("body=@") or not comment_target_ok(endpoints[0]):
        return False
    first = review_file(value[len("body=@") :])
    return first is not None and first.startswith("Verdict:")


BUNDLE_WORD = re.compile(r"(?:\./)?scripts/agk/review_bundle\.py")
FULL_SHA = re.compile(r"[0-9a-f]{40}")
BUNDLE_BASE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
PLAIN_PATH = re.compile(r"/[A-Za-z0-9._/-]+")


def bundle_save_allowed(command: str) -> bool:
    """`python3 scripts/agk/review_bundle.py --pr <n> --sha <40-hex> [--base <ref>] > <file>`, one
    `>` to a regular file of a review scratch directory, written plainly (brief #1248 answer 2,
    ADR-0528); the bundle's own arguments in its documented order, nothing else."""
    if command.count(">") != 1:
        return False
    left, right = command.split(">", 1)
    target = right.strip()
    words = tokens_of(left)
    if not words or not PLAIN_PATH.fullmatch(target) or not review_write_ok(target):
        return False
    if words[:2] != ["python3", words[1]] or not BUNDLE_WORD.fullmatch(words[1]):
        return False
    rest = words[2:]
    if len(rest) not in (4, 6) or rest[0] != "--pr" or rest[2] != "--sha":
        return False
    if not PR_NUMBER.fullmatch(rest[1]) or not FULL_SHA.fullmatch(rest[3]):
        return False
    return len(rest) == 4 or (rest[4] == "--base" and bool(BUNDLE_BASE.fullmatch(rest[5])))


def review_step_allowed(words: list[str]) -> bool:
    """One step of a reviewer slot run in its exact form (brief #1050 answer 2)."""
    if words == ["git", "fetch", "origin"]:
        return True
    if words[:3] == ["git", "checkout", "--detach"]:
        return len(words) == 4 and on_origin_branch(words[3])
    if words[:2] == ["gh", "api"] and "-F" in words:
        return verdict_post_ok(words)
    if len(words) < 3 or words[0] != "python3":
        return False
    if CONDUCTOR_WORD.fullmatch(words[1]):
        rest = words[2:]
        return (
            len(rest) == 4
            and rest[0] == "check-verdict"
            and rest[2] == "--pr"
            and bool(PR_NUMBER.fullmatch(rest[3]))
            and review_file(rest[1]) is not None
        )
    if SESSION_WORD.fullmatch(words[1]):
        rest = words[2:]
        return (
            len(rest) == 3
            and rest[0] == "slot"
            and rest[1] in ("--next", "--release")
            and bool(REVIEWER_NAME.fullmatch(rest[2]))
        )
    return False


def decide(payload: dict, review: bool = False) -> str | None:
    """A denial text, or None to allow; in review mode the one write is a review scratch file."""
    tool = payload.get("tool_name")
    data = payload.get("tool_input")
    data = data if isinstance(data, dict) else {}
    if tool in WRITE_TOOLS:
        if review:
            ok = tool == "Write" and review_write_ok(data.get("file_path"))
            return None if ok else REVIEW_RULE
        target = data.get("file_path", data.get("notebook_path"))
        return None if path_allowed(target, project_root()) else PATH_RULE
    if tool == "Bash":
        return None if bash_allowed(data.get("command"), review) else BASH_RULE
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
