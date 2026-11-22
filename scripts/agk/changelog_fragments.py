# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
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

The release pull request also runs (brief #1706, ADR-0710)

    python3 scripts/agk/changelog_fragments.py accept --comments FILE

which sets to `Accepted` the one `- Status: Proposed` line of each ADR that `check_adrs.py
--pending` lists (records verified by their Final comments in FILE only), byte for byte otherwise,
so no session edits a Status line by hand. Every file is read before the first write; a refusal
writes nothing.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_adrs
from common import STATUS_LINE, CheckError, base_arg, git, repo_root, run

NAME = "changelog-fragments"
USAGE = (
    "usage: changelog_fragments.py gather --version V [--date YYYY-MM-DD]\n"
    "       changelog_fragments.py accept --comments FILE [--base REF]"
)
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


def accepted_text(data: bytes) -> bytes:
    """DATA with its Status line (the first `STATUS_LINE`) set to Accepted, line end kept."""
    lines = data.decode("utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        body = line.rstrip("\r\n")
        if STATUS_LINE.match(body):
            lines[i] = "- Status: Accepted" + line[len(body) :]
            break
    return "".join(lines).encode("utf-8")


def accept(root: Path, comments_path: str | None, base: str | None) -> None:
    """SPEC-0028 rule 4: flip each file `check_adrs.pending_paths` lists; nothing on a refusal."""
    try:
        comments = check_adrs.read_comments(comments_path)
        listed = check_adrs.pending_paths(root, check_adrs.adr_files(root), comments, base)
        flips = [(p, accepted_text(p.read_bytes())) for p in listed]
    except (OSError, UnicodeDecodeError):
        raise CheckError("rule 4: a decision cannot be read (path class docs/adr/)") from None
    if not flips:
        print("accept: none pending")
        return
    for path, data in flips:
        path.write_bytes(data)
        print(f"accepted: {path.relative_to(root).as_posix()}")
    print(f"accept: {len(flips)} decisions")


def accept_main(rest: list[str]) -> int:
    names = rest[::2]
    if len(rest) % 2 or any(name not in ("--comments", "--base") for name in names):
        print(USAGE, file=sys.stderr)
        return 2
    opts = dict(zip(rest[::2], rest[1::2], strict=True))
    accept(repo_root(), opts.get("--comments"), base_arg(rest))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    opts: dict[str, str] = {}
    if args and args[0] == "accept":
        return accept_main(args[1:])
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
