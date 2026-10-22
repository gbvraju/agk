"""Totals of the shadow record (SPEC-0023 rule 8). Kit-only: never installed.

    python3 shadow_count.py FILE

Reads FILE only and prints, for the findings the maintainers marked
(`- <by> <mark> <where>: <text>`), the catches by both, by the person only and by the shadow
only, the false findings by each, the findings with no `<where>` and the lines with no mark
(both count for nothing), and the number of pasted verdicts that lack a line of the shape of
SPEC-0023 rule 4. It uses no network and no model, and fails nothing but a bad call (exit 2).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

USAGE = "usage: shadow_count.py FILE"
LINE = re.compile(r"^- (both|person|shadow)\b")
MARKS = ("catch", "false")
SHAPE = ("Read:", "Rules:", "Not proven:", "Lens:", "Gaps:", "Checklist:")
HEADINGS = ("### Person's verdict", "### Shadow verdict")


def has_shape(block: list[str]) -> bool:
    """The six lines of the shape, each starting a line, in order."""
    at = 0
    for line in block:
        if at < len(SHAPE) and line.startswith(SHAPE[at]):
            at += 1
    return at == len(SHAPE)


def verdict_blocks(lines: list[str]) -> list[list[str]]:
    """The fenced blocks under the two verdict headings."""
    blocks: list[list[str]] = []
    under, inside = False, False
    for line in lines:
        if line.startswith("#"):
            under = line.strip() in HEADINGS
        elif under and line.startswith("```"):
            inside = not inside
            if inside:
                blocks.append([])
        elif inside:
            blocks[-1].append(line)
    return blocks


def totals(text: str) -> list[str]:
    lines = text.splitlines()
    catch = {"both": 0, "person": 0, "shadow": 0}
    false = {"both": 0, "person": 0, "shadow": 0}
    no_where = unmarked = 0
    for line in lines:
        if not LINE.match(line):
            continue
        head, colon, _ = line[2:].partition(":")
        words = head.split(None, 2)  # by, mark, where (the where may hold spaces, never `: `)
        mark = words[1] if len(words) > 1 else ""
        if not colon or mark not in MARKS:
            unmarked += 1
        elif len(words) < 3:
            no_where += 1
        else:
            (catch if mark == "catch" else false)[words[0]] += 1
    blocks = verdict_blocks(lines)
    missing = sum(1 for block in blocks if not has_shape(block))
    requests = sum(1 for line in lines if line.startswith("## Pull request "))
    return [
        f"pull requests: {requests}",
        "catches: "
        f"both={catch['both']} person-only={catch['person']} shadow-only={catch['shadow']}",
        f"false: both={false['both']} person={false['person']} shadow={false['shadow']}",
        f"no where (count for nothing): {no_where}",
        f"unmarked (count for nothing): {unmarked}",
        f"verdicts: {len(blocks)}, missing a line of the shape: {missing}",
    ]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0].startswith("-"):
        print(USAGE)
        return 2
    try:
        text = Path(args[0]).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        print("shadow_count: cannot read the record file")
        return 2
    print("\n".join(totals(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
