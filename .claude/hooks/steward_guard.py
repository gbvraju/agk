#!/usr/bin/env python3
"""PreToolUse guard of the steward role (SPEC-0059 rule 11, brief #1320, ADR-0557).

Contract (verify; as `architect_guard.py`): JSON on stdin with `tool_name`, `tool_input` and `cwd`;
a denial prints {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
"permissionDecisionReason": ...}} and exits 0; an allow prints nothing.

Denies: a comment whose first line starts `Approve:`, `Confirmed:`, `Verdict:`, `Final:` or
`Correction:`; a `Maintainer answer:` whose second line is not `Owner said (<UTC time>): "…"`; a
merge, `merge_cleared.py`, auto-merge, a push to the default branch, a force push, a tag; a change
to a file under `.github/`, the ruleset, a required check or a secret; an issue creation whose
`Priority:` is above `[steward] auto_file` with no `Owner said` line; any label write other than
`agk:parked` and `agk-steward`; a comment or issue body it cannot read (fail closed); a GraphQL
call (`CLAUDE.md item 10`). Each denial names the rule and the setting or path class, never the
value. It reads the command, the files a body names and `agk.toml`; no network, nothing stored.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

RULE = "SPEC-0059 rule 11"
RESERVED = ("Approve:", "Confirmed:", "Verdict:", "Final:", "Correction:")
OWNER_SAID = re.compile(r'Owner said \(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z\): ".+"\s*\Z')
OWNER_LINE = re.compile(r'^Owner said \(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z\): ".+"', re.M)
PRIORITY = re.compile(r"^Priority:\s*(\d+)", re.M)
LABELS = frozenset({"agk:parked", "agk-steward"})
OPERATORS = frozenset({";", "&&", "||", "|", "&", "\n"})
WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
FIELD_FLAGS = frozenset({"-f", "--raw-field", "-F", "--field"})
VALUE_FLAGS = frozenset({"-H", "--header", "-q", "--jq", "-t", "--template", "--cache", "-p"})
READ_GIT = frozenset({"log", "diff", "show", "status", "blame", "grep", "ls-files", "fetch"})
SHELLS = frozenset({"bash", "sh", "zsh", "eval"})
BODY_FLAGS = frozenset({"-b", "--body"})
FORCE = re.compile(r"^(?:-f|--force(?:-with-lease|-if-includes)?(?:=.*)?|--mirror|--tags|--delete|-d)$")
API_DENIED = (
    (re.compile(r"/pulls/\d+/merge$|/merges$"), "a merge"),
    (re.compile(r"/git/|/releases|/tags"), "a tag or a push"),
    (re.compile(r"/contents/"), "a push to the default branch or a change under `.github/`"),
    (re.compile(r"/rulesets|/protection"), "a ruleset or required check change"),
    (re.compile(r"/secrets|/actions/|/environments/|/keys"), "a secret or workflow change"),
    (re.compile(r"^/?repos/[^/]+/[^/]+/labels"), "a label write"),
)


def reason(what: str, where: str) -> str:
    return f"steward guard: {RULE} denies {what} (path class: {where})"


def default_branch(project: Path) -> str:
    try:
        import tomllib

        value = tomllib.loads((project / "agk.toml").read_text(encoding="utf-8"))
        return str(value.get("default_branch") or "main")
    except (OSError, ValueError, ImportError):
        return "main"


def read_value(value: str, cwd: Path) -> str | None:
    """A `-F key=@file` value's text; None when it cannot be read (stdin, a missing file)."""
    if not value.startswith("@"):
        return value
    if value == "@-":
        return None
    path = Path(value[1:])
    try:
        return (path if path.is_absolute() else cwd / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def body_problem(text: str | None, inline: bool = False) -> str | None:
    """A typed body may hold no substitution (`$(` or a backtick): the shell would run it."""
    if text is None or (inline and ("$(" in text or "`" in text)):
        return reason("a body it cannot read", "comment body")
    lines = text.lstrip().splitlines() or [""]
    if lines[0].startswith(RESERVED):
        return reason("a reserved first line", "comment first line")
    if lines[0].startswith("Maintainer answer:"):
        if len(lines) < 2 or not OWNER_SAID.match(lines[1]):
            return reason("an owner answer without the owner's quote", "comment second line")
    return None


def filing_problem(text: str | None, project: Path) -> str | None:
    if text is None:
        return reason("a body it cannot read", "issue body")
    found = PRIORITY.search(text)
    if found is None or OWNER_LINE.search(text):
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))
    try:
        from config import steward_settings

        limit = steward_settings(project)["auto_file"]
    except Exception as exc:  # noqa: BLE001 - a refused or unreadable table fails closed
        setting = re.search(r"setting: ([\w.]+)", str(exc))
        return f"steward guard: {RULE} denies a filing (setting: {setting[1] if setting else 'steward'})"
    if limit is False or int(found[1]) > limit:
        return f"steward guard: {RULE} denies a filing above the priority (setting: steward.auto_file)"
    return None


def labels_problem(values: list[str], allowed: frozenset[str]) -> str | None:
    names = [n.strip() for v in values for n in v.split(",")]
    return None if all(n in allowed for n in names) else reason("a label write", "label")


def option_values(words: list[str], flags: frozenset[str]) -> list[str]:
    out = []
    for i, word in enumerate(words):
        for flag in flags:
            if word == flag and i + 1 < len(words):
                out.append(words[i + 1])
            elif word.startswith(flag + "=") and flag.startswith("--"):
                out.append(word.split("=", 1)[1])
    return out


def gh_problem(words: list[str], cwd: Path, project: Path) -> str | None:
    sub = words[1] if len(words) > 1 else ""
    verb = words[2] if len(words) > 2 else ""
    if sub == "api":
        return api_problem(words[2:], cwd, project)
    if sub == "pr" and verb == "merge":
        return reason("a merge or auto-merge", "pull request")
    if sub == "release" or (sub == "workflow" and verb in ("run", "enable", "disable")):
        return reason("a tag or a workflow change", "`.github/`")
    if sub in ("secret", "ruleset") and verb not in ("list", "view", "check"):
        return reason("a secret or ruleset change", sub)
    if sub == "label" and verb not in ("list", "view"):
        return reason("a label write", "label")
    added = option_values(words, frozenset({"--add-label", "--remove-label", "--label", "-l"}))
    if sub == "pr" and verb == "edit":
        return labels_problem(added, frozenset({"agk:parked"}))
    if sub == "issue" and verb in ("create", "edit"):
        if problem := labels_problem(added, frozenset({"agk-steward"})):
            return problem
    texts = [(v, True) for v in option_values(words, BODY_FLAGS)]
    files = option_values(words, frozenset({"--body-file", "-F"}))
    texts += [(None if v == "-" else read_value("@" + v, cwd), False) for v in files]
    for text, inline in texts:
        if sub == "issue" and verb == "create":
            problem = filing_problem(text, project) or body_problem(text, inline)
        else:
            problem = body_problem(text, inline) if verb in ("comment", "review", "edit") else None
        if problem:
            return problem
    return None


def api_problem(words: list[str], cwd: Path, project: Path) -> str | None:
    endpoint, method, fields, skip, inline = "", None, {}, False, set()
    for i, word in enumerate(words):
        if skip:
            skip = False
            continue
        if word in ("-X", "--method") and i + 1 < len(words):
            method, skip = words[i + 1].upper(), True
        elif word in VALUE_FLAGS:
            skip = True
        elif word.startswith("--method="):
            method = word.split("=", 1)[1].upper()
        elif word in FIELD_FLAGS and i + 1 < len(words):
            key, _, value = words[i + 1].partition("=")
            typed = word in ("-f", "--raw-field") or not value.startswith("@")
            fields.setdefault(key, []).append(value if typed else read_value(value, cwd))
            if typed:
                inline.add(key)
            skip = True
        elif word == "--input":
            return reason("a body it cannot read", "request input")
        elif not word.startswith("-") and not endpoint:
            endpoint = word
    if endpoint.strip("/") == "graphql":
        return "steward guard: CLAUDE.md item 10 denies a GraphQL call (path class: gh api graphql)"
    if (method or ("POST" if fields else "GET")) == "GET":
        return None
    path = endpoint.split("?", 1)[0]
    for pattern, what in API_DENIED:
        if pattern.search(path):
            return reason(what, "gh api endpoint")
    if re.search(r"/issues/\d+/labels", path):
        named = [v or "?" for k, vs in fields.items() if k.startswith("labels") for v in vs]
        if method == "DELETE" and not fields:
            named = [path.rsplit("/", 1)[1]]
        return labels_problem(named or ["?"], LABELS)
    named = [v or "?" for k, vs in fields.items() if k.startswith("labels") for v in vs]
    if re.search(r"/issues$", path):
        if problem := labels_problem(named, frozenset({"agk-steward"})):
            return problem
        text = (fields.get("body") or [""])[0]
        return filing_problem(text, project) or body_problem(text, "body" in inline)
    if named:
        return reason("a label write", "label")
    for text in fields.get("body", []):
        if problem := body_problem(text, "body" in inline):
            return problem
    return None


def git_problem(words: list[str], project: Path) -> str | None:
    i = 1
    while i < len(words) and words[i].startswith("-"):
        i += 2 if words[i] in ("-C", "-c") else 1
    sub, args = (words[i], words[i + 1 :]) if i < len(words) else ("", [])
    if any(".github/" in a for a in args) and sub not in READ_GIT:
        return reason("a change to a workflow file", "`.github/`")
    if sub == "merge":
        return reason("a merge", "git merge")
    if sub == "tag" and any(a not in ("-l", "--list") and not a.startswith("--sort") for a in args):
        return reason("a tag", "git tag")
    if sub != "push":
        return None
    if any(FORCE.match(a) or a.startswith("+") for a in args):
        return reason("a force push, a tag or a delete", "git push")
    refs = [a for a in args if not a.startswith("-")][1:]
    branch = default_branch(project)
    if not refs:
        return reason("a push with no branch named", "git push")
    for ref in refs:
        target = ref.rsplit(":", 1)[-1].removeprefix("refs/heads/")
        if target in (branch, "HEAD") or target.startswith("refs/tags/"):
            return reason("a push to the default branch or a tag", "default branch")
    return None


def segments(command: str) -> list[list[str]] | None:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        words = list(lexer)
    except ValueError:
        return None
    out: list[list[str]] = [[]]
    for word in words:
        if word in OPERATORS or set(word) <= set(";&|\n"):
            out.append([])
        else:
            out[-1].append(word)
    return [s for s in out if s]


def decide(payload: dict) -> str | None:
    tool = payload.get("tool_name")
    data = payload.get("tool_input") or {}
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")
    cwd = Path(payload.get("cwd") or project)
    if tool in WRITE_TOOLS:
        target = Path(str(data.get("file_path") or data.get("notebook_path") or ""))
        rel = os.path.relpath(target if target.is_absolute() else cwd / target, project)
        if rel.replace("\\", "/").startswith(".github/"):
            return reason("a change to a workflow file", "`.github/`")
        return None
    if tool != "Bash":
        return None
    return bash_problem(str(data.get("command") or ""), cwd, project, 0)


def bash_problem(command: str, cwd: Path, project: Path, depth: int) -> str | None:
    found = segments(command)
    if found is None or depth > 3:
        return reason("a command it cannot read", "Bash")
    for words in found:
        if any("merge_cleared" in w for w in words):
            return reason("a merge", "`scripts/agk/merge_cleared.py`")
        if any(w.startswith(".github/") or "/.github/" in w for w in words) and words[0] not in (
            "cat", "ls", "head", "grep", "git", "gh", *SHELLS
        ):
            return reason("a change to a workflow file", "`.github/`")
        while words and re.match(r"^[A-Za-z_]\w*=", words[0]):
            words = words[1:]  # an environment assignment before the command
        name = os.path.basename(words[0]) if words else ""
        problem = None
        if name in SHELLS:
            inner = words[words.index("-c") + 1] if "-c" in words[:-1] else " ".join(words[1:])
            problem = bash_problem(inner, cwd, project, depth + 1)
        if name == "git":
            problem = git_problem(words, project)
        elif name == "gh":
            problem = gh_problem(words, cwd, project)
        if problem:
            return problem
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = None
    found = decide(payload) if isinstance(payload, dict) else reason("an unreadable call", "hook input")
    if found:
        out = {"hookEventName": "PreToolUse", "permissionDecision": "deny"}
        print(json.dumps({"hookSpecificOutput": {**out, "permissionDecisionReason": found}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
