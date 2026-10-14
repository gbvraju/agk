"""config/reviewers.yaml: schema check and CODEOWNERS rendering (stdlib only).

Parses only the restricted YAML subset the file uses: `key: scalar`, top-level `classes:` and
`teams:` mappings, and one flow mapping per entry line,
e.g. `name: {paths: [a, b], approvers: [t]}`.
"""

from __future__ import annotations

import re
import sys

from common import CheckError, read_list, repo_root, run

NAME = "reviewers"
CONFIG = "config/reviewers.yaml"
PROTECTED_LIST = "config/protected-paths.txt"
CODEOWNERS = ".github/CODEOWNERS"
BLOCK_BEGIN = "# >>> agk\n"
BLOCK_END = "# <<< agk\n"
HANDLE_RE = re.compile(r"^@[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)?$")
NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


class ReviewerError(CheckError):
    pass


def strip_comment(line: str) -> str:
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            return line[:i]
    return line


class Flow:
    """Recursive-descent parser for flow mappings, lists and scalars."""

    def __init__(self, text: str) -> None:
        self.s = text
        self.i = 0

    def ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def value(self):
        self.ws()
        if self.i >= len(self.s):
            raise ReviewerError("unexpected end of value")
        ch = self.s[self.i]
        if ch == "{":
            return self.mapping()
        if ch == "[":
            return self.sequence()
        return self.scalar()

    def mapping(self) -> dict:
        self.i += 1
        out: dict = {}
        self.ws()
        if self.s[self.i : self.i + 1] == "}":
            self.i += 1
            return out
        while True:
            key = self.scalar(stop=":")
            self.ws()
            if self.s[self.i : self.i + 1] != ":":
                raise ReviewerError("expected ':' in mapping")
            self.i += 1
            out[key] = self.value()
            self.ws()
            ch = self.s[self.i : self.i + 1]
            self.i += 1
            if ch == "}":
                return out
            if ch != ",":
                raise ReviewerError("expected ',' or '}' in mapping")

    def sequence(self) -> list:
        self.i += 1
        out: list = []
        self.ws()
        if self.s[self.i : self.i + 1] == "]":
            self.i += 1
            return out
        while True:
            out.append(self.value())
            self.ws()
            ch = self.s[self.i : self.i + 1]
            self.i += 1
            if ch == "]":
                return out
            if ch != ",":
                raise ReviewerError("expected ',' or ']' in list")

    def scalar(self, stop: str = "") -> str:
        self.ws()
        if self.i < len(self.s) and self.s[self.i] in "\"'":
            q = self.s[self.i]
            end = self.s.find(q, self.i + 1)
            if end < 0:
                raise ReviewerError("unterminated quote")
            val = self.s[self.i + 1 : end]
            self.i = end + 1
            return val
        start = self.i
        while self.i < len(self.s) and self.s[self.i] not in ",]}" + stop:
            self.i += 1
        val = self.s[start : self.i].strip()
        if not val:
            raise ReviewerError("empty value")
        return val


def parse(text: str) -> dict:
    data: dict = {}
    section: dict | None = None
    for raw in text.splitlines():
        line = strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        key, sep, rest = body.partition(":")
        if not sep:
            raise ReviewerError("line without ':'")
        rest = rest.strip()
        if indent == 0:
            if rest:
                if rest[0] in "[{":
                    raise ReviewerError("top-level keys take scalar values")
                data[key] = rest
                section = None
            else:
                section = data.setdefault(key, {})
        else:
            if section is None:
                raise ReviewerError("indented line outside a mapping")
            flow = Flow(rest)
            section[key] = flow.value()
            flow.ws()
            if flow.i != len(flow.s):
                raise ReviewerError("trailing text after value")
    return data


def validate(data: dict, protected_list: str) -> list[str]:
    problems: list[str] = []
    if data.get("version") != "1":
        problems.append("version must be 1")
    classes = data.get("classes")
    teams = data.get("teams")
    if not isinstance(classes, dict) or not classes:
        problems.append("classes must be a non-empty mapping")
        classes = {}
    if not isinstance(teams, dict) or not teams:
        problems.append("teams must be a non-empty mapping")
        teams = {}
    for tname, team in teams.items():
        if not NAME_RE.match(tname):
            problems.append(f"team '{tname}': name must be lowercase letters, digits, - or _")
        handle = team.get("github_team") if isinstance(team, dict) else None
        if not isinstance(handle, str) or not HANDLE_RE.match(handle):
            problems.append(f"team '{tname}': github_team must be an @handle or @org/team")
    for cname, cls in classes.items():
        if not isinstance(cls, dict):
            problems.append(f"class '{cname}': must be a mapping")
            continue
        paths = cls.get("paths")
        if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
            problems.append(f"class '{cname}': paths must be a non-empty list")
        approvers = cls.get("approvers")
        if not isinstance(approvers, list) or not approvers:
            problems.append(f"class '{cname}': approvers must be a non-empty list")
            continue
        for a in approvers:
            if a not in teams:
                problems.append(f"class '{cname}': approvers must name teams defined in 'teams'")
                break
    prot = classes.get("protected")
    if isinstance(prot, dict) and isinstance(prot.get("paths"), list):
        if sorted(prot["paths"]) != sorted(read_list(protected_list)):
            problems.append(f"class 'protected' differs from {PROTECTED_LIST}")
    elif "protected" not in classes:
        problems.append("class 'protected' is required")
    return problems


def extract_block(text: str) -> str:
    """The text between the agk markers of a project CODEOWNERS; the rest of the file is ignored."""
    if text.count(BLOCK_BEGIN) != 1 or text.count(BLOCK_END) != 1:
        raise CheckError(f"{CODEOWNERS} has a broken or duplicated agk block")
    start = text.index(BLOCK_BEGIN) + len(BLOCK_BEGIN)
    end = text.index(BLOCK_END)
    if end < start:
        raise CheckError(f"{CODEOWNERS} has a broken or duplicated agk block")
    return text[start:end]


def render_codeowners(data: dict) -> str:
    owned: dict[str, str] = {}
    for cls in data["classes"].values():
        owners = " ".join(data["teams"][a]["github_team"] for a in cls["approvers"])
        for path in cls["paths"]:
            owned[path] = owners  # a path in two classes: the later class wins
    entries = sorted(owned.items(), key=lambda e: (e[0].rstrip("/").count("/"), len(e[0])))
    lines = [
        "# Generated by scripts/agk/reviewers.py --codeowners from config/reviewers.yaml.",
        "# Later lines win: broad paths first, narrow paths last.",
    ]
    lines += [f"/{path} {owners}" for path, owners in entries]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or argv[0] not in ("--check", "--codeowners", "--check-codeowners"):
        raise CheckError("usage: reviewers.py --check | --codeowners | --check-codeowners")
    root = repo_root()
    try:
        data = parse((root / CONFIG).read_text(encoding="utf-8"))
        protected = (root / PROTECTED_LIST).read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckError(f"cannot read {CONFIG} or {PROTECTED_LIST}") from exc
    problems = validate(data, protected)
    if argv[0] == "--check":
        for problem in problems:
            print(f"FAIL {NAME}: {problem}")
        if not problems:
            print(f"ok {NAME}")
        return 1 if problems else 0
    if problems:
        raise CheckError(f"{CONFIG} is invalid; run --check")
    rendered = render_codeowners(data)
    if argv[0] == "--codeowners":
        sys.stdout.write(rendered)
        return 0
    try:
        committed = (root / CODEOWNERS).read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckError(f"{CODEOWNERS} is missing; render it with --codeowners") from exc
    if BLOCK_BEGIN in committed or BLOCK_END in committed:
        committed = extract_block(committed)
    if committed != rendered:
        raise CheckError(f"{CODEOWNERS} differs from the rendering of {CONFIG}; re-render it")
    print(f"ok {NAME} ({CODEOWNERS} matches)")
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
