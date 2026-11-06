#!/usr/bin/env python3
"""PreToolUse hook: the data guard's layer 1 (SPEC-0042 rules 1 to 6 and 9, brief #589).

Contract (SPEC-0042 rule 2; the input fields are `(verify)` there): the hook receives JSON on stdin
with `tool_name`, `tool_input` and `cwd`. To deny it prints {"hookSpecificOutput": {"hookEventName":
"PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": <line>}} and exits 0; to
allow it prints nothing. It is registered in `.claude/settings.json` with `"onFailure": "block"`.

It denies a read or an edit of a secret file (rule 5) or a raw log (rule 6), by any tool, by every
path form (`..`, `~`, a link, any case), and by any command line (rule 4): split at the shell's
operators, with prefixes and wrappers stripped, nested shells judged again to a depth of 3, globs
and braces expanded, `$'...'` decoded, redirection targets and every word searched for a denied
name. A recursive search is denied when its folder holds such a file. `.env.example`, files under
a test folder and an `allow_paths` file are read by the hook itself first and allowed only clean.
The denial is one line that names the rule and the class, never a path, a command or a value
(rule 9). Anything it cannot judge denies (`cannot-judge`); it never allows on an error.
Standard library only; no network. Rules 7 (remote access) and 8 (the environment) are not judged
here yet: they are left to a later build of the brief (Q-589-1).
"""

from __future__ import annotations

import codecs
import fnmatch
import glob as globlib
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
SCRIPTS = HOOKS.parents[1] / "scripts" / "agk"
ALTERNATIVE = {
    "secret-file": "ask the person for the one value you need, or for a cleaned copy",
    "raw-log": "read it through `agk logs <file>` (python3 scripts/agk/guard_logs.py)",
    "cannot-judge": "ask the person to run it and give you a cleaned copy",
}
TEST_DIRS = {"tests", "test", "spec", "__tests__", "fixtures"}
HOME_STORES = (".ssh", ".aws", ".azure", ".config/gcloud", ".kube", ".config/gh")
HOME_FILES = (".netrc", ".git-credentials", ".docker/config.json")
TOKEN_FILES = (".npmrc", ".pypirc")
TOKEN_LINE = re.compile(r"(?im)^[^#;\n]*(?:_authtoken|_auth|token|password)\s*[=:]\s*\S")
LOG_NAME = re.compile(r".*\.log(?:\.\d+)?")
SAMPLES = (".env", ".env.local", "x.pem", "x.key", "x.p12", "x.pfx", "id_rsa", "x.tfstate",
           "x.tfstate.1", "secrets.json", "x.log", "x.log.1")
CHUNK = re.compile(r"[\w.~/\\-]+")
ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.S)
ANSI_C = re.compile(r"\$'((?:[^'\\]|\\.)*)'", re.S)
BRACE = re.compile(r"\{([^{}]*,[^{}]*)\}")
UNSPLITTABLE = re.compile(r"\$\(|`|<<|<\(|>\(")
DECODER = re.compile(
    r"\bbase64\b[^|;&]*\s(?:-\w*d\w*|--decode)\b|\bxxd\b[^|;&]*\s-\w*r|\bopenssl\b[^|;&]*\s-d\b"
    r"|\bprintf\b[^|;&]*\\(?:x[0-9a-fA-F]|[0-7]{3})|\becho\s+-\w*e"
)
FEEDS = {"xargs", "sh", "bash", "zsh", "dash", "ksh", "eval", "source", "."}
KEYWORDS = {"{", "}", "!", "if", "then", "else", "elif", "do", "while", "until", "fi", "done"}
WRAPPERS = {
    "env": {"-u", "-C", "-S", "--unset", "--chdir"}, "sudo": {"-u", "-g", "-C", "-h", "-p", "-U"},
    "doas": {"-u"}, "timeout": {"-k", "-s"}, "time": {"-f", "-o"}, "nice": {"-n"}, "nohup": set(),
    "stdbuf": {"-i", "-o", "-e"}, "command": set(), "builtin": set(), "exec": {"-a"},
    "xargs": {"-I", "-n", "-P", "-d", "-E", "-L", "-s", "-a"}, "watch": {"-n", "-d"},
}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
LOG_COMMANDS = {"journalctl": None, "dmesg": None, "kubectl": "logs", "docker": "logs",
                "docker-compose": "logs", "podman": "logs", "heroku": "logs", "aws": "logs",
                "gcloud": "logging", "az": "monitor"}
GREPS = {"grep", "egrep", "fgrep"}
READER = re.compile(r"python(?:3(?:\.\d+)?)?(?:\.exe)?")
MAX_DEPTH = 3
DEADLINE = 7.0  # seconds, under rule 2's timeout of 10
MAX_BYTES = 2_000_000  # one file the hook scans itself
MAX_EXPANSION = 2000


class Denied(Exception):
    def __init__(self, rule: str, kind: str) -> None:
        super().__init__(rule)
        self.rule, self.kind = rule, kind

    def line(self) -> str:
        return f"data guard: {self.rule} ({self.kind}): {ALTERNATIVE[self.rule]}"


def load_settings(root: str) -> dict:
    """The `[guard]` additions that count; a refused table is reported and adds nothing (rule 1)."""
    sys.path.insert(0, str(SCRIPTS))
    import config  # noqa: PLC0415 - found through SCRIPTS, the kit's own folder

    try:
        return config.guard_settings(Path(root))
    except config.GuardSettingError as exc:
        print(f"data guard: {exc}", file=sys.stderr)
        return {"patterns": [], "deny_paths": [], "deny_commands": [], "allow_paths": []}


class Guard:
    def __init__(self, root: str, cwd: str, settings: dict) -> None:
        self.root, self.cwd, self.settings = os.path.realpath(root), cwd, settings
        home = os.path.expanduser("~")
        self.homes = {os.path.normpath(home).lower(), os.path.realpath(home).lower()}
        self.allow = {e["path"].replace("\\", "/").lower() for e in settings["allow_paths"]}
        self.started = time.monotonic()

    def tick(self) -> None:
        if time.monotonic() - self.started > DEADLINE:
            raise Denied("cannot-judge", "scan limit")

    # --- paths (rules 3, 5 and 6) -----------------------------------------------------------------

    def hit(self, path: str, parts: bool) -> tuple[str, str, str] | None:
        """(rule, kind, how) for one absolute path; how is "name", "content" or "token"."""
        low = path.lower()
        for home in self.homes:
            if low.startswith(home + os.sep):
                rel = low[len(home) + 1 :].replace(os.sep, "/")
                stored = rel in HOME_FILES
                if stored or any(rel == d or rel.startswith(d + "/") for d in HOME_STORES):
                    return "secret-file", "credential store", "name"
        rel = os.path.relpath(path, self.root)
        inside = not rel.startswith("..")
        comps = (rel if inside else path).replace("\\", "/").lower().strip("/").split("/")
        name, folders = comps[-1], comps[:-1]
        exempt = name == ".env.example" or bool(TEST_DIRS & set(folders))
        if name in TOKEN_FILES:
            return "secret-file", "token file", "token"
        found = self.name_hit(name)
        logs = "logs" in folders or (name == "logs" and os.path.isdir(path))
        if found is None and parts and logs:
            found = ("raw-log", "log file")
        if found is None:
            rel_low = "/".join(comps)
            for pattern in self.settings["deny_paths"]:
                if fnmatch.fnmatchcase(name, pattern.lower()) or fnmatch.fnmatchcase(
                    rel_low, pattern.lower()
                ):
                    found = ("secret-file", "custom path")
        if found is None:
            return None
        allowed = inside and "/".join(comps) in self.allow
        lifted = allowed and found[1] in ("log file", "custom path")
        return (*found, "content" if exempt or lifted else "name")

    @staticmethod
    def name_hit(name: str) -> tuple[str, str] | None:
        name = name.lower()
        if name == ".env" or name.startswith(".env."):
            return "secret-file", "env file"
        if name.endswith((".pem", ".key", ".p12", ".pfx")) or re.fullmatch(r"id_[^.]*", name):
            return "secret-file", "key file"
        if name.endswith(".tfstate") or ".tfstate." in name:
            return "secret-file", "state file"
        if name.startswith("secrets."):
            return "secret-file", "secrets file"
        if LOG_NAME.fullmatch(name):
            return "raw-log", "log file"
        return None

    def scan(self, path: str, how: str) -> bool:
        """True when the file, read by the hook itself, holds a finding (or a token line)."""
        if not os.path.isfile(path):
            return False
        if os.path.getsize(path) > MAX_BYTES:
            raise Denied("cannot-judge", "scan limit")
        self.tick()
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        import guard  # noqa: PLC0415 - loaded with config from SCRIPTS

        if how == "token" and TOKEN_LINE.search(text):
            return True
        return bool(guard.scan_text(text, self.settings["patterns"]))

    def path(self, word: str, parts: bool = True, lift_logs: bool = False, base: str = "") -> None:
        if not word or "\0" in word:
            return
        given = os.path.expanduser(word) if word.startswith("~") else word
        full = os.path.normpath(os.path.join(base or self.cwd, given))
        for candidate in dict.fromkeys((full, os.path.realpath(full))):
            found = self.hit(candidate, parts)
            if found is None or (lift_logs and found[0] == "raw-log"):
                continue
            rule, kind, how = found
            if how == "name" or self.scan(candidate, how):
                raise Denied(rule, kind)

    def folder(self, top: str) -> None:
        """Rule 5's folder check: deny a search over a folder that holds a file of rule 5 or 6."""
        seen: set[str] = set()
        for dirpath, dirnames, filenames in os.walk(top, followlinks=True):
            real = os.path.realpath(dirpath)
            if real in seen:
                dirnames[:] = []
                continue
            seen.add(real)
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for name in filenames:
                self.tick()
                try:
                    self.path(os.path.join(dirpath, name))
                except Denied as denied:
                    if denied.rule == "cannot-judge":
                        raise
                    raise Denied(denied.rule, "folder search") from None

    def pattern(self, text: str, rules: tuple[str, ...], expand: bool) -> None:
        """A glob: matched against the denied names, and expanded in cwd when `expand`."""
        tail = text.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if not any(c in tail for c in "*?["):
            found = self.name_hit(tail)
            if found and found[0] in rules:
                raise Denied(*found)
        elif re.search(r"[^*?\[\]!/]", tail):
            for sample in SAMPLES:
                found = self.name_hit(sample)
                if fnmatch.fnmatchcase(sample, tail) and found and found[0] in rules:
                    raise Denied(*found)
        if expand:
            where = os.path.join(self.cwd, os.path.expanduser(text))
            matches = globlib.iglob(where, recursive=True)
            for i, match in enumerate(matches):
                if i > MAX_EXPANSION:
                    raise Denied("cannot-judge", "scan limit")
                self.path(match)

    def word(self, word: str, lift_logs: bool = False) -> None:
        """Every word: as a path, as a glob, and every name-like chunk inside it (rule 4)."""
        home = os.path.expanduser("~")
        for name in ("${HOME}", "$HOME", "${USERPROFILE}", "$USERPROFILE", "%USERPROFILE%"):
            word = word.replace(name, home)
        for variant in braces(word):
            if any(c in variant for c in "*?["):
                self.pattern(variant, ("secret-file", "raw-log"), expand=not lift_logs)
            self.path(variant, lift_logs=lift_logs)
            for sep in (":", "="):
                if sep in variant and "://" not in variant:
                    rest = variant.split(sep, 1)[1]
                    self.path(rest, lift_logs=lift_logs, base=self.root if sep == ":" else "")
            for chunk in CHUNK.findall(variant):
                self.path(chunk, parts="/" in chunk, lift_logs=lift_logs)

    # --- commands (rule 4) ------------------------------------------------------------------------

    def command(self, text: str, depth: int = 0) -> None:
        if depth > MAX_DEPTH:
            raise Denied("cannot-judge", "nested shell")
        text = ANSI_C.sub(lambda m: shlex.quote(codecs.decode(m.group(1), "unicode_escape")), text)
        simple = split(text)
        if simple is None:  # judged on its raw text
            if DECODER.search(text):
                raise Denied("cannot-judge", "decoded name")
            words = re.findall(r"[^\s'\"`$()<>|;&]+", text)
            for w in words:
                self.word(w)
            self.log_command([w.lower() for w in words])
            return
        leads = [lead(words) for words, _ in simple]
        for i, (words, cut) in enumerate(simple):
            if DECODER.search(" ".join(words)) and FEEDS & set().union(*leads[i + 1 :]):
                raise Denied("cannot-judge", "decoded name")
            following = leads[i + 1] if cut in ("|", "|&") and i + 1 < len(leads) else set()
            self.simple(words, depth, following)

    def simple(self, words: list[str], depth: int, following: set[str]) -> None:
        args: list[str] = []
        i = 0
        while i < len(words):
            w = words[i]
            if w and set(w) <= set("<>&|") and set(w) & set("<>"):
                if i + 1 < len(words):
                    self.word(words[i + 1])
                i += 2
                continue
            args.append(w)
            i += 1
        for w in args:  # assignments and wrappers included: `F=.env`, `sudo -u x`
            self.word(w, lift_logs=self.reader(strip(args)))
        rest = strip(args)
        if not rest:
            return
        name, low = os.path.basename(rest[0]).lower(), [w.lower() for w in rest]
        self.log_command(low)
        if name in SHELLS:
            for j, w in enumerate(rest[1:], 1):
                if re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", w) and j + 1 < len(rest):
                    self.command(rest[j + 1], depth + 1)
                    break
        elif name in ("pwsh", "powershell", "pwsh.exe", "powershell.exe"):
            for j, w in enumerate(low[1:], 1):
                if w in ("-c", "-command") and j + 1 < len(rest):
                    self.command(" ".join(rest[j + 1 :]), depth + 1)
                    break
        elif name == "eval":
            self.command(" ".join(rest[1:]), depth + 1)
        for top in self.searched(name, rest, following):
            self.folder(top)

    def reader(self, rest: list[str]) -> bool:
        """`python3 scripts/agk/guard_logs.py <file>`: the project's own regular reader (rule 6)."""
        if len(rest) < 2 or not READER.fullmatch(os.path.basename(rest[0]).lower()):
            return False
        script = os.path.join(self.cwd, rest[1])
        own = os.path.join(self.root, "scripts", "agk", "guard_logs.py")
        regular = os.path.isfile(script) and not os.path.islink(script)
        return regular and os.path.isfile(own) and os.path.samefile(script, own)

    def log_command(self, low: list[str]) -> None:
        if not low:
            return
        name = os.path.basename(low[0])
        if name in LOG_COMMANDS and (LOG_COMMANDS[name] is None or LOG_COMMANDS[name] in low[1:]):
            raise Denied("raw-log", "log command")
        for entry in self.settings["deny_commands"]:
            first, *more = entry.lower().split()
            if name == first and all(m in low[1:] for m in more):
                raise Denied("raw-log", "log command")

    def searched(self, name: str, rest: list[str], following: set[str]) -> list[str]:
        """The folders a recursive search reads (rule 4), or [] when it is not one."""
        low = [w.lower() for w in rest[1:]]
        recursive = (
            name in ("rg", "ag", "ack")
            or (name == "git" and "grep" in low[:3])
            or (name in GREPS and any(
                w in ("-r", "-R", "--recursive", "--directories=recurse", "--dereference-recursive")
                or re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", w) for w in rest[1:]
            ) or (name in GREPS and "recurse" in low))
            or (name == "find" and (bool({"-exec", "-execdir", "-ok", "-okdir"} & set(low))
                                    or "xargs" in following))
            or (name == "select-string" and "-recurse" in low)
            or (name in ("get-childitem", "gci", "dir", "ls") and "-recurse" in low
                and "select-string" in following)
        )
        if not recursive:
            return []
        operands = [os.path.join(self.cwd, os.path.expanduser(w)) for w in rest[1:] if w[:1] != "-"]
        folders = [p for p in operands if os.path.isdir(p)]
        if folders:
            return folders
        return [] if any(os.path.isfile(p) for p in operands) else [self.cwd]


def braces(word: str, limit: int = 64) -> list[str]:
    """Bash brace expansion, enough to see `.{e,x}nv` as `.env`."""
    out, todo = [], [word]
    while todo and len(out) + len(todo) <= limit:
        w = todo.pop()
        m = BRACE.search(w)
        if not m:
            out.append(w)
            continue
        todo.extend(w[: m.start()] + part + w[m.end() :] for part in m.group(1).split(","))
    if todo:
        raise Denied("cannot-judge", "scan limit")
    return out


def lead(words: list[str]) -> set[str]:
    """The program names that start a simple command, wrappers included (`sudo xargs cat`)."""
    names = [os.path.basename(w).lower() for w in words if w[:1] != "-" and not ASSIGN.fullmatch(w)]
    return set(names[:3])


def strip(words: list[str] | str) -> list[str]:
    """The words after leading assignments, keywords and wrappers with their options (rule 4)."""
    words = [words] if isinstance(words, str) else list(words)
    while words:
        first = words[0]
        name = os.path.basename(first).lower()
        if ASSIGN.fullmatch(first) or first in KEYWORDS:
            words = words[1:]
            continue
        if name not in WRAPPERS:
            break
        i = 1
        while i < len(words) and words[i].startswith("-") and words[i] != "-":
            i += 2 if words[i] in WRAPPERS[name] else 1
            if words[i - 1] == "--":
                break
        if name == "timeout" and i < len(words):
            i += 1
        words = words[i:]
    return words


def hash_outside_quotes(command: str) -> bool:
    sys.path.insert(0, str(HOOKS))
    from architect_guard import hash_outside_quotes as outside  # noqa: PLC0415

    return outside(command)


def split(command: str) -> list[tuple[list[str], str]] | None:
    """Simple commands with the operator after each, or None when the line cannot be split."""
    if UNSPLITTABLE.search(command) or hash_outside_quotes(command):
        return None
    lexer = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
    lexer.commenters = ""
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return None
    out: list[tuple[list[str], str]] = []
    current: list[str] = []
    for token in tokens:
        if token and set(token) <= set("();|&\n"):
            if current:
                out.append((current, token.strip("\n") or ";"))
            current = []
        else:
            current.append(token)
    if current:
        out.append((current, ""))
    return out


FIELDS = {
    "Read": ("file_path",), "Edit": ("file_path",), "Write": ("file_path",),
    "MultiEdit": ("file_path",), "NotebookEdit": ("notebook_path",), "Bash": ("command",),
    "PowerShell": ("command",), "Glob": ("pattern",), "Grep": (),
}


def decide(payload: object) -> None:
    if not isinstance(payload, dict) or not isinstance(payload.get("tool_input"), dict):
        raise Denied("cannot-judge", "unreadable input")
    tool, data = payload.get("tool_name"), payload["tool_input"]
    if tool not in FIELDS:
        return
    for field in ("file_path", "notebook_path", "command", "pattern", "path", "glob"):
        value = data.get(field)
        if (value is None and field in FIELDS[tool]) or not isinstance(value, (str, type(None))):
            raise Denied("cannot-judge", "unreadable input")
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()
    guard = Guard(root, cwd or root, load_settings(root))
    if tool in ("Bash", "PowerShell"):
        guard.command(data["command"])
    elif tool == "Glob":
        guard.pattern(data["pattern"], ("secret-file",), expand=False)
    elif tool == "Grep":
        if data.get("glob"):
            guard.pattern(data["glob"], ("secret-file", "raw-log"), expand=False)
        target = data.get("path") or guard.cwd
        guard.path(target)
        full = os.path.join(guard.cwd, os.path.expanduser(target))
        if os.path.isdir(full):
            guard.folder(full)
    else:
        guard.path(data[FIELDS[tool][0]])


def judge(payload: object) -> str | None:
    """The denial line of rule 9, or None to allow. Any error denies (rule 2)."""
    try:
        decide(payload)
    except Denied as denied:
        return denied.line()
    except Exception:  # noqa: BLE001 - fails closed: an error inside the hook never allows
        return Denied("cannot-judge", "hook error").line()
    return None


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        payload = None
    line = judge(payload)
    if line is not None:
        out = {"hookEventName": "PreToolUse", "permissionDecision": "deny",
               "permissionDecisionReason": line}
        print(json.dumps({"hookSpecificOutput": out}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
