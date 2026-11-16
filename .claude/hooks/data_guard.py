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
Brief #1360 (ADR-0572): a `$(...)`, `<(...)`, `>(...)` or backquote command is judged as a nested
shell and the outer line with a placeholder word; a here-document body is data, searched for a
denied name and never expanded as a glob; a PowerShell line (the PowerShell tool or a `pwsh
-Command` argument) is split at `;`, `|`, `&&` and `||` with the backquote read as its escape
(`u{...}`, `n and the others decoded) and continuation. A Bash tool line is always judged as
bash, and in a `pwsh` session shell also as PowerShell, denied when either reader denies. A form
it cannot take apart, and nesting past 3, deny with the hint `split it into single commands`.
Standard library only; no network. Rules 7 (remote access) and 8 (the environment) are not judged
here yet: they are left to a later build of the brief (Q-589-1).
Brief #1410 (ADR-0593): each denial is kept, redacted, in `<git common dir>/agk/refusals.log`
(`guard_logs.record_refusal`); a hook error keeps the exception's type and place, never a value,
and its denial adds `see agk logs --refusals`. A here-document line with a CRLF line end closes
the here-document as the same line without its carriage return does.
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
SUB = "agk_sub"  # the placeholder word of a command or process substitution (brief #1360)
SPLIT_KINDS = {"nested shell", "compound form"}  # their denial adds `split it into single commands`
POWERSHELL = {"pwsh", "powershell", "pwsh.exe", "powershell.exe"}
PS_ESCAPES = {"0": "\0", "a": "\a", "b": "\b", "e": "\x1b", "f": "\f", "n": "\n", "r": "\r",
              "t": "\t", "v": "\v"}
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
        hint = "split it into single commands, or " if self.kind in SPLIT_KINDS else ""
        more = "; see agk logs --refusals" if self.kind == "hook error" else ""
        return f"data guard: {self.rule} ({self.kind}): {hint}{ALTERNATIVE[self.rule]}{more}"


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

    def command(self, text: str, depth: int = 0, ps: bool = False) -> None:
        if depth > MAX_DEPTH:
            raise Denied("cannot-judge", "nested shell")
        if ps:
            self.powershell(text, depth)
            return
        text = ANSI_C.sub(lambda m: shlex.quote(codecs.decode(m.group(1), "unicode_escape")), text)
        outer, subs, bodies = lift(text)
        for inner in subs:  # brief #1360 answer 1a: a nested shell, within the same depth
            self.nested(inner, depth, ps=False)
        for body, expands in bodies:  # answer 1b: a here-document body is data
            self.data(body, depth, expands)
        simple = split(outer)
        if simple is None:  # judged on its raw text
            if DECODER.search(outer):
                raise Denied("cannot-judge", "decoded name")
            words = re.findall(r"[^\s'\"`$()<>|;&]+", outer)
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

    def nested(self, inner: str, depth: int, ps: bool) -> None:
        """A substitution's command; its output becomes words, so a decoder in it denies."""
        if DECODER.search(inner):
            raise Denied("cannot-judge", "decoded name")
        self.command(inner, depth + 1, ps)

    def data(self, body: str, depth: int, expands: bool) -> None:
        """A here-document body (answer 1b): searched for a denied name as a redirection target is,
        never expanded as a glob; an unquoted delimiter's substitutions are judged as commands."""
        if expands:
            for inner in walk(body, 0, "", True, [], [])[2]:
                self.nested(inner, depth, ps=False)
        home = os.path.expanduser("~")
        for name in ("${HOME}", "$HOME", "${USERPROFILE}", "$USERPROFILE", "%USERPROFILE%"):
            body = body.replace(name, home)
        for chunk in CHUNK.findall(body):
            self.path(chunk, parts="/" in chunk)

    def powershell(self, text: str, depth: int) -> None:
        """Answer 1c: a PowerShell line, split at `;`, `|`, `&&`, `||` and line ends, the backquote
        read as its escape and continuation, `$(...)` judged as a nested PowerShell line."""
        parts, subs = ps_split(text)
        for inner in subs:
            self.nested(inner, depth, ps=True)
        leads = [lead(words) for words, _ in parts]
        for i, (words, cut) in enumerate(parts):
            following = leads[i + 1] if cut == "|" and i + 1 < len(leads) else set()
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
            if SUB in w and w != SUB:  # `.e$(...)`: the substitution may complete a denied name
                self.pattern(w.replace(SUB, "*"), ("secret-file", "raw-log"), expand=False)
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
        elif name in POWERSHELL:
            for j, w in enumerate(low[1:], 1):
                if w in ("-c", "-command") and j + 1 < len(rest):
                    self.command(" ".join(rest[j + 1 :]), depth + 1, ps=True)
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


HEREDOC = re.compile(r"<<(-?)[ \t]*(\\|'|\")?([\w.@%+:-]+)(['\"]?)")


def compound() -> Denied:
    return Denied("cannot-judge", "compound form")


def walk(
    text: str, i: int, closer: str, literal: bool, subs: list[str], bodies: list[tuple[str, bool]]
) -> tuple[str, int, list[str], list[tuple[str, bool]]]:
    """Bash (brief #1360 answer 1): the text from `i` with each `$(...)`, `<(...)`, `>(...)` and
    backquote replaced by SUB and each here-document body taken out, up to `closer`. `literal`
    reads quotes as plain text (an unquoted here-document body). Raises `compound form` when it
    cannot take the text apart."""
    out: list[str] = []
    quote, pending, n = "", [], len(text)
    while i < n:
        c = text[i]
        if quote == "'":
            quote = "" if c == "'" else quote
            out.append(c)
            i += 1
        elif c == "\\" and i + 1 < n:
            out.append(text[i : i + 2])
            i += 2
        elif text.startswith("$(", i) or (
            not quote and not literal and text[i : i + 2] in ("<(", ">(")
        ):
            j = walk(text, i + 2, ")", False, [], [])[1]
            subs.append(text[i + 2 : j - 1])
            out.append(SUB)
            i = j
        elif c == "`":
            j = text.find("`", i + 1)
            if j < 0 or "\\" in text[i + 1 : j]:
                raise compound()
            subs.append(text[i + 1 : j])
            out.append(SUB)
            i = j + 1
        elif quote == '"' or (not literal and c in "'\""):
            quote = "" if quote == '"' and c == '"' else (quote or c)
            out.append(c)
            i += 1
        elif not literal and text.startswith("<<<", i):  # a here-string: a redirection word
            out.append("<<<")
            i += 3
        elif not literal and text.startswith("<<", i):
            m = HEREDOC.match(text, i)
            opened, word, close = (m.group(2) or "", m.group(3), m.group(4)) if m else ("", "", "")
            if not m or (opened in "'\"" and opened != close) or (opened == "\\" and close):
                raise compound()
            pending.append((word, bool(m.group(1)), not opened))
            out.append(" ")
            i = m.end()
        elif c == "\n" and pending:
            out.append(c)
            i += 1
            for word, tabs, expands in pending:
                lines: list[str] = []
                while True:
                    if i >= n:
                        raise compound()
                    j = text.find("\n", i)
                    j = n if j < 0 else j
                    line, i = text[i:j], j + 1
                    line = line.removesuffix("\r")  # a CRLF line end (brief #1410)
                    if (line.lstrip("\t") if tabs else line) == word:
                        break
                    lines.append(line)
                bodies.append(("\n".join(lines), expands))
            pending = []
        elif closer and c == "(":
            j = walk(text, i + 1, ")", False, [], [])[1]
            out.append(text[i:j])
            i = j
        elif closer and c == closer:
            if pending or quote:
                raise compound()
            return "".join(out), i + 1, subs, bodies
        else:
            out.append(c)
            i += 1
    if closer or pending:
        raise compound()
    return "".join(out), min(i, n), subs, bodies


def lift(text: str) -> tuple[str, list[str], list[tuple[str, bool]]]:
    """The line with its substitutions as SUB, their commands, and its here-document bodies."""
    out, _, subs, bodies = walk(text, 0, "", False, [], [])
    return out, subs, bodies


def ps_close(text: str, i: int) -> int:
    """The index of the `)` that closes a PowerShell `$(` opened before `i`."""
    depth, quote = 1, ""
    while i < len(text):
        c = text[i]
        if c == "`" and quote != "'":
            i += 2
            continue
        if quote:
            quote = "" if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise compound()


def ps_split(text: str) -> tuple[list[tuple[list[str], str]], list[str]]:
    """A PowerShell line as simple commands with the operator after each, and its `$(...)`
    commands; the backquote escapes the next character and continues a line (answer 1c)."""
    parts: list[tuple[list[str], str]] = []
    subs: list[str] = []
    words: list[str] = []
    word: list[str] = []
    quote, i, n = "", 0, len(text)

    def end() -> None:
        if word:
            words.append("".join(word))
            word.clear()

    while i < n:
        c = text[i]
        if quote == "'":
            if text.startswith("''", i):
                word.append("'")
                i += 1
            elif c == "'":
                quote = ""
            else:
                word.append(c)
            i += 1
        elif c == "`":
            rest = text[i + 1 : i + 3]
            if not rest:
                raise compound()
            if rest.startswith(("\n", "\r\n")):  # a continuation: the line goes on
                end()
                i += 2 if rest[0] == "\n" else 3
            elif rest[0] == "u" and text.startswith("{", i + 2):  # `u{2e}: a code point
                m = re.match(r"\{([0-9a-fA-F]{1,6})\}", text[i + 2 :])
                if not m or int(m.group(1), 16) > 0x10FFFF:
                    raise compound()
                word.append(chr(int(m.group(1), 16)))
                i += 2 + m.end()
            else:  # `n, `t, `0 and the rest become their character; any other is kept as is
                word.append(PS_ESCAPES.get(rest[0], rest[0]))
                i += 2
        elif text.startswith("$(", i):
            j = ps_close(text, i + 2)
            subs.append(text[i + 2 : j])
            word.append(SUB)
            i = j + 1
        elif quote == '"':
            if text.startswith('""', i):
                word.append('"')
                i += 1
            elif c == '"':
                quote = ""
            else:
                word.append(c)
            i += 1
        elif c in "'\"":
            quote = c
            i += 1
        elif c in " \t\r":
            end()
            i += 1
        elif c in ";\n|" or text.startswith("&&", i):
            op = text[i : i + 2] if text[i : i + 2] in ("&&", "||") else c
            end()
            if words and words[0] in ("&", "."):  # the call operators
                words.pop(0)
            if words:
                parts.append((list(words), ";" if op == "\n" else op))
            words.clear()
            i += len(op)
        else:
            word.append(c)
            i += 1
    if quote:
        raise compound()
    end()
    if words and words[0] in ("&", "."):
        words.pop(0)
    if words:
        parts.append((list(words), ""))
    return parts, subs


def split(command: str) -> list[tuple[list[str], str]] | None:
    """Simple commands with the operator after each, or None when the line cannot be split."""
    if hash_outside_quotes(command):
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


def powershell_session() -> bool:
    """The session's shell is PowerShell (`SHELL` names `pwsh` or `powershell`, verify)."""
    name = os.path.basename(os.environ.get("SHELL", "").replace("\\", "/")).lower()
    return name.removesuffix(".exe") in ("pwsh", "powershell")


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
        guard.command(data["command"], ps=tool == "PowerShell")
        if tool == "Bash" and powershell_session():  # the Bash tool runs bash: both readers judge
            guard.command(data["command"], ps=True)
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


def verdict(payload: object) -> tuple[Denied | None, BaseException | None]:
    """The denial, or None to allow, and the error that caused it. Any error denies (rule 2)."""
    try:
        decide(payload)
    except Denied as denied:
        return denied, None
    except Exception as exc:  # noqa: BLE001 - fails closed: an error inside the hook never allows
        return Denied("cannot-judge", "hook error"), exc
    return None, None


def judge(payload: object) -> str | None:
    """The denial line of rule 9, or None to allow."""
    denied = verdict(payload)[0]
    return denied.line() if denied else None


def keep(payload: object, denied: Denied, exc: BaseException | None) -> bool:
    """Brief #1410: one redacted line per denial; a failure here leaves the denial as it was."""
    try:
        sys.path.insert(0, str(SCRIPTS))
        import guard_logs  # noqa: PLC0415 - found through SCRIPTS, only when something is denied

        error = guard_logs.error_of(exc, __file__) if exc else None
        reason = f"{denied.rule} ({denied.kind})"
        return guard_logs.record_refusal(payload, "data guard", reason, "unknown", error)
    except Exception:  # noqa: BLE001 - keeping the line never changes the decision
        return False


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        payload = None
    denied, exc = verdict(payload)
    line = denied.line() if denied else None
    if denied is not None:
        keep(payload, denied, exc)
        out = {"hookEventName": "PreToolUse", "permissionDecision": "deny",
               "permissionDecisionReason": line}
        print(json.dumps({"hookSpecificOutput": out}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
