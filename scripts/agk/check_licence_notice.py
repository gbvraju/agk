# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Every kit file names its owner and licence (brief #1419, ADR-0596, REQ-014).

    python3 scripts/agk/check_licence_notice.py [--write]

In the kit's repository (it has `kit/manifest.json`) the kit files are the files of the manifest
(`verbatim`, `experimental`, `rendered`) and every tracked file under `scripts/agk/`, `.claude/`,
`skills/`, `.claude-plugin/` and `kit/` but `kit/templates/` (a template becomes a project's own
file). `LICENSE` and `LICENSE-AGK` are the licence and carry no header. Each kit file carries the
header in its own comment form (`style_of`), or is covered by an annotation of `REUSE.toml` that
names the owner and `LicenseRef-AGK-Proprietary`; a file that cannot hold a comment (JSON) needs
the annotation. In a project (no manifest) the check needs `LICENSE-AGK` at the root and the
header in each tracked file under `scripts/agk/` that can hold one.

`--write` adds the header to each kit file that can hold one and lacks it, then checks. A failure
names the file and its path class, never a value. No network.

The header is three parts: the `SPDX-FileCopyrightText` line, the `SPDX-License-Identifier` line
and the notice. In the `#` form the notice is wrapped at word boundaries so that no line passes
100 characters (the lint's limit); in the HTML form it is one line inside one `<!-- -->` block.
`rules.py` takes the header off before it counts an instruction file (`without_header`).
"""

from __future__ import annotations

import fnmatch
import re
import sys
import textwrap
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, git, read_list, repo_root, run, utf8_output

NAME = "licence-notice"
USAGE = "usage: check_licence_notice.py [--write]"
OWNER = "Balavardhi Raju Gangula"
IDENTIFIER = "LicenseRef-AGK-Proprietary"
COPYRIGHT_LINE = f"SPDX-FileCopyrightText: 2026 {OWNER}"
IDENTIFIER_LINE = f"SPDX-License-Identifier: {IDENTIFIER}"
NOTICE = (
    f"AGK is built and owned by {OWNER}. Use only in the repository named in the owner's written "
    "grant; no use in any other repository without the owner's permission. See LICENSE-AGK."
)
WIDTH = 100
MANIFEST = "kit/manifest.json"
REUSE = "REUSE.toml"
LICENCE_COPY = "LICENSE-AGK"
LICENCE_FILES = ("LICENSE", LICENCE_COPY)
KIT_FOLDERS = ("scripts/agk/", ".claude/", "skills/", ".claude-plugin/", "kit/")
NOT_KIT = ("kit/templates/",)
PROJECT_FOLDER = "scripts/agk/"
PROTECTED = "config/protected-paths.txt"

HASH_SUFFIXES = (".py", ".sh", ".ps1", ".yml", ".yaml", ".toml", ".mk", ".txt", ".cfg", ".ini")
HASH_NAMES = ("Makefile", "GNUmakefile", ".gitignore", ".gitattributes", "CODEOWNERS")
HTML_SUFFIXES = (".md", ".html", ".htm")
ENCODING = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*[-\w.]+")


def style_of(rel: str) -> str | None:
    """`hash`, `html`, or None for a file that cannot hold a comment."""
    name = rel.rsplit("/", 1)[-1]
    if name in HASH_NAMES or name.endswith(HASH_SUFFIXES):
        return "hash"
    if name.endswith(HTML_SUFFIXES):
        return "html"
    return None


def header_lines(style: str) -> list[str]:
    if style == "html":
        return ["<!--", COPYRIGHT_LINE, IDENTIFIER_LINE, NOTICE, "-->"]
    notice = textwrap.wrap(NOTICE, width=WIDTH - 2, break_long_words=False)
    return [f"# {line}" for line in [COPYRIGHT_LINE, IDENTIFIER_LINE, *notice]]


def insert_at(lines: list[str], style: str) -> int:
    """The index the header goes to: after a `#!` and an encoding line, or after front matter."""
    if style == "html":
        if lines and lines[0].strip() == "---":
            end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
            return end + 1 if end is not None else 0
        return 0
    at = 1 if lines and lines[0].startswith("#!") else 0
    if at < len(lines) and at < 2 and ENCODING.match(lines[at]):
        at += 1
    return at


def has_header(text: str, style: str) -> bool:
    lines = text.splitlines()
    at = insert_at(lines, style)
    head = header_lines(style)
    return lines[at : at + len(head)] == head


def add_header(text: str, style: str) -> str:
    """TEXT with the header of STYLE in its place; unchanged when it is already there."""
    if has_header(text, style):
        return text
    lines = text.splitlines(keepends=True)
    at = insert_at([ln.rstrip("\r\n") for ln in lines], style)
    if at and not lines[at - 1].endswith("\n"):
        lines[at - 1] += "\n"
    block = [f"{line}\n" for line in header_lines(style)]
    return "".join([*lines[:at], *block, *lines[at:]])


def without_header(text: str) -> str:
    """TEXT with its header taken off, in either form; unchanged when it has none."""
    for style in ("html", "hash"):
        if has_header(text, style):
            lines = text.splitlines(keepends=True)
            at = insert_at([ln.rstrip("\r\n") for ln in lines], style)
            return "".join([*lines[:at], *lines[at + len(header_lines(style)) :]])
    return text


def glob_regex(pattern: str) -> re.Pattern[str]:
    """A REUSE.toml path glob: `**` crosses folders, `*` and `?` do not."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def annotated(root: Path) -> list[re.Pattern[str]]:
    """The path globs of REUSE.toml whose annotation names the owner and the AGK licence."""
    path = root / REUSE
    if not path.is_file():
        return []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise CheckError(f"{REUSE} cannot be read (path class {REUSE})") from None
    found: list[re.Pattern[str]] = []
    for entry in data.get("annotations") or []:
        if not isinstance(entry, dict):
            continue
        owner = entry.get("SPDX-FileCopyrightText")
        owners = owner if isinstance(owner, list) else [owner]
        if entry.get("SPDX-License-Identifier") != IDENTIFIER:
            continue
        if not any(isinstance(o, str) and OWNER in o for o in owners):
            continue
        paths = entry.get("path")
        for glob in paths if isinstance(paths, list) else [paths]:
            if isinstance(glob, str):
                found.append(glob_regex(glob))
    return found


def path_class(root: Path, rel: str) -> str:
    """The protected entry that matches REL, else its top folder."""
    entries: list[str] = []
    listed = root / PROTECTED
    if listed.is_file():
        entries = read_list(listed.read_text(encoding="utf-8"))
    for entry in entries:
        if (rel.startswith(entry) if entry.endswith("/") else rel == entry) or fnmatch.fnmatch(
            rel, entry
        ):
            return entry
    return rel.split("/", 1)[0] + "/" if "/" in rel else rel


def kit_files(root: Path, tracked: list[str]) -> list[str]:
    """The kit files of the kit's repository, sorted; the licence files are left out."""
    import json

    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    wanted = {
        *manifest.get("verbatim", []),
        *manifest.get("experimental", []),
        *manifest.get("rendered", []),
    }
    wanted |= {rel for rel in tracked if rel.startswith(KIT_FOLDERS)}
    wanted = {rel for rel in wanted if not rel.startswith(NOT_KIT) and rel not in LICENCE_FILES}
    return sorted(rel for rel in wanted if (root / rel).is_file())


def problems_of(root: Path, write: bool) -> list[str]:
    tracked = [p for p in git(root, "ls-files", "-z").split("\0") if p]
    problems: list[str] = []
    if (root / MANIFEST).is_file():
        files = kit_files(root, tracked)
        globs = annotated(root)
    else:
        files = sorted(rel for rel in tracked if rel.startswith(PROJECT_FOLDER))
        globs = []
        if not (root / LICENCE_COPY).is_file():
            problems.append(f"{LICENCE_COPY} is missing (path class {LICENCE_COPY}: run upgrade)")
    for rel in files:
        if any(g.match(rel) for g in globs):
            continue
        style = style_of(rel)
        if style is None:
            if globs or (root / MANIFEST).is_file():
                problems.append(
                    f"{rel} cannot hold a header and no {REUSE} annotation covers it "
                    f"(path class {path_class(root, rel)})"
                )
            continue
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            problems.append(f"{rel} cannot be read (path class {path_class(root, rel)})")
            continue
        if has_header(text, style):
            continue
        if write:
            path.write_bytes(add_header(text, style).encode("utf-8"))
            continue
        problems.append(
            f"{rel} has no owner and licence header (path class {path_class(root, rel)})"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if args not in ([], ["--write"]):
        print(USAGE, file=sys.stderr)
        return 2
    root = repo_root()
    if args:
        problems_of(root, write=True)
    problems = problems_of(root, write=False)
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if problems:
        print(f"{NAME}: {len(problems)} files; `check_licence_notice.py --write` adds the header")
        return 1
    print(f"ok {NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
