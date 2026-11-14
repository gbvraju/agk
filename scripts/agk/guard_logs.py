"""Print a log with every secret and personal value redacted, `agk logs` (SPEC-0042 rule 11).

Usage: python3 scripts/agk/guard_logs.py [--max-lines N] FILE|-

Brief #561. Each finding of `guard.scan_text` is replaced by `[<KIND>-<n>]`, numbered per kind in
order of first appearance over the lines printed, so one value keeps one label in a run; the
mapping lives in memory only. Everything else of a line is printed unchanged. `--max-lines N`
(default 2000) prints only the last N lines. The last line holds counts per kind only. Bytes that
are not UTF-8 are replaced. It opens no socket, runs no program and writes no file: the
`[guard] patterns` come from the nearest `agk.toml` at or above the current folder, found by
walking up (patterns only add, so no default-branch check is needed). A usage error, a file it
cannot read or a refused `[guard]` table exits 2, naming the option or the setting, never a path
or a value.
"""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import utf8_output
from guard import scan_text

import config

DEFAULT_MAX_LINES = 2000
USAGE = "usage: guard_logs.py [--max-lines N] FILE|-"


class Usage(Exception):
    """A usage error, an unreadable file or a refused setting (exit 2)."""


def parse(args: list[str]) -> tuple[int, str]:
    max_lines = DEFAULT_MAX_LINES
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--max-lines":
            if i + 1 >= len(args) or not args[i + 1].isdigit() or int(args[i + 1]) < 1:
                raise Usage("--max-lines needs a whole number of at least 1 (option: --max-lines)")
            max_lines = int(args[i + 1])
            i += 2
        else:
            rest.append(args[i])
            i += 1
    if len(rest) != 1:
        raise Usage(USAGE)
    return max_lines, rest[0]


def read_tail(source: str, max_lines: int) -> str:
    try:
        if source == "-":
            stream = sys.stdin.buffer
            lines = deque(stream, maxlen=max_lines)
        else:
            with open(source, "rb") as stream:
                lines = deque(stream, maxlen=max_lines)
    except OSError:
        raise Usage("the log cannot be read (option: FILE)") from None
    return b"".join(lines).decode("utf-8", errors="replace")


def redact(text: str, patterns) -> tuple[str, dict[str, int]]:
    labels: dict[tuple[str, str], str] = {}
    per_kind: dict[str, int] = {}
    counts: dict[str, int] = {}
    out = []
    pos = 0
    for f in scan_text(text, patterns=patterns):
        value = text[f.start : f.start + f.length]
        key = (f.kind, value)
        if key not in labels:
            per_kind[f.kind] = per_kind.get(f.kind, 0) + 1
            labels[key] = f"[{f.kind}-{per_kind[f.kind]}]"
        counts[f.kind] = counts.get(f.kind, 0) + 1
        out.append(text[pos : f.start])
        out.append(labels[key])
        pos = f.start + f.length
    out.append(text[pos:])
    return "".join(out), counts


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        max_lines, source = parse(args)
        try:
            patterns = config.guard_patterns(Path.cwd())
        except config.GuardSettingError as exc:
            raise Usage(str(exc)) from None
        text = read_tail(source, max_lines)
    except Usage as exc:
        print(f"agk logs: {exc}")
        return 2
    redacted, counts = redact(text, patterns)
    sys.stdout.write(redacted)
    if redacted and not redacted.endswith("\n"):
        sys.stdout.write("\n")
    summary = ", ".join(f"{kind} {n}" for kind, n in counts.items())
    print(f"agk logs: {summary or 'no findings'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
