"""The changelog fragments of flow mode (SPEC-0031). Kit-only: never installed.

In flow mode a build pull request adds one file `changelog.d/<slug>.md` holding one line,
`- <one-line change>`, and does not edit `CHANGELOG.md`. The release pull request runs

    python3 scripts/agk/changelog_fragments.py gather --version V [--date YYYY-MM-DD]

which moves the line of every committed fragment under a new heading `## V (<date>)` of
`CHANGELOG.md`, in the order of the pull request numbers, each as `- #<n> <one-line change>`, and
deletes the fragments. `<n>` is read on the first-parent history from the commit that added the
file: a subject ending `(#<n>)` (squash merge) or starting `Merge pull request #<n>` (merge commit).
The lines already under `## Unreleased` move first, unchanged. A fragment whose number cannot be
read stops the script before it writes anything. Git and files only: no network, no model.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from common import CheckError, git, repo_root, run

NAME = "changelog-fragments"
USAGE = "usage: changelog_fragments.py gather --version V [--date YYYY-MM-DD]"
FRAG_DIR = "changelog.d/"
CHANGELOG = "CHANGELOG.md"
UNRELEASED = "## Unreleased"
SLUG_FILE = re.compile(r"changelog\.d/[a-z0-9-]+\.md")
LINE = re.compile(r"- (?!#\d+(?:\s|$))\S[^\n]*\n")
PR_SUBJECT = re.compile(r"\(#(\d+)\)\s*$|^Merge pull request #(\d+)\b")
VERSION = re.compile(r"\d+(?:\.\d+)*")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def well_formed(path: str, text: str) -> bool:
    """Rule 1: a slug of `[a-z0-9-]+`, and exactly one line `- <change>` with no number."""
    return SLUG_FILE.fullmatch(path) is not None and LINE.fullmatch(text) is not None


def tree_fragments(root: Path, rev: str) -> list[str]:
    """The files under `changelog.d/` in the commit `rev`, sorted."""
    out = git(root, "ls-tree", "-r", "--name-only", rev, "--", FRAG_DIR)
    return sorted(line for line in out.splitlines() if line)


def pr_number(root: Path, rev: str, path: str) -> int | None:
    """The pull request number of the commit that added `path` on the first-parent history.

    A squash merge ends its subject with `(#<n>)`; a merge commit starts it with
    `Merge pull request #<n>`. Anything else is not readable."""
    out = git(
        root,
        "log",
        "-m",
        "--first-parent",
        "--diff-filter=A",
        "--format=%s",
        rev,
        "--",
        path,
        check=False,
    )
    subjects = [line for line in out.splitlines() if line.strip()]
    match = PR_SUBJECT.search(subjects[-1]) if subjects else None
    return int(match.group(1) or match.group(2)) if match else None


def gathered_lines(root: Path, rev: str, rule: str) -> tuple[list[str], list[str]]:
    """(paths, lines `- #<n> <change>`) of the fragments of `rev`, in pull request order."""
    found: list[tuple[int, str, str]] = []
    for path in tree_fragments(root, rev):
        number = pr_number(root, rev, path)
        text = git(root, "show", f"{rev}:{path}", check=False)
        if number is None or not well_formed(path, text):
            raise CheckError(
                f"{rule}: a fragment has no readable pull request number or is not one line "
                f"(path class {FRAG_DIR})"
            )
        found.append((number, path, f"- #{number} {text[2:].rstrip()}"))
    found.sort()
    return [path for _, path, _ in found], [line for _, _, line in found]


def moved_text(old: str, heading: str, extra: list[str]) -> str:
    """CHANGELOG text with the Unreleased lines and `extra` under `heading`, Unreleased empty."""
    lines = old.splitlines()
    if UNRELEASED not in [ln.strip() for ln in lines]:
        raise CheckError(f"rule 3: {CHANGELOG} has no {UNRELEASED} heading")
    start = [ln.strip() for ln in lines].index(UNRELEASED)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    moved = [ln.rstrip() for ln in lines[start + 1 : end] if ln.strip()] + extra
    before = "\n".join(lines[:start]) + ("\n" if start else "")
    rest = "\n".join(lines[end:]) + "\n" if end < len(lines) else ""
    body = "".join(f"{ln}\n" for ln in moved)
    return f"{before}{UNRELEASED}\n\n{heading}\n\n{body}" + (f"\n{rest}" if rest else "")


def gather(root: Path, version: str, date: str) -> None:
    if not VERSION.fullmatch(version) or not DATE.fullmatch(date):
        raise CheckError("rule 3: the version or the date has the wrong form (options)")
    paths, lines = gathered_lines(root, "HEAD", "rule 3")
    file = root / CHANGELOG
    try:
        old = file.read_text(encoding="utf-8")
    except OSError:
        raise CheckError(f"rule 3: {CHANGELOG} cannot be read") from None
    text = moved_text(old, f"## {version} ({date})", lines)
    file.write_text(text, encoding="utf-8")
    for path in paths:
        (root / path).unlink(missing_ok=True)
    print(f"gathered {len(paths)} fragments")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    opts: dict[str, str] = {}
    if not args or args[0] != "gather":
        print(USAGE, file=sys.stderr)
        return 2
    rest = args[1:]
    for i in range(0, len(rest) - 1, 2):
        if rest[i] not in ("--version", "--date"):
            print(USAGE, file=sys.stderr)
            return 2
        opts[rest[i][2:]] = rest[i + 1]
    if len(rest) % 2 or "version" not in opts:
        print(USAGE, file=sys.stderr)
        return 2
    date = opts.get("date") or datetime.now(UTC).date().isoformat()
    gather(repo_root(), opts["version"], date)
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
