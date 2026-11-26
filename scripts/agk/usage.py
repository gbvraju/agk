# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Print the token figure of the running session, split by kind, or why there is none.

SPEC-0045 rule 8 (brief #798 build (a)), as ADR-0835 (brief #2020) changes it. It reads the running
session's own transcript file, found by the runtime's session id variable under the runtime's home
folder (verify: `CLAUDE_CODE_SESSION_ID` and `<CLAUDE_CONFIG_DIR or
~/.claude>/projects/*/<id>.jsonl` are read from this cloud runtime, not from its documentation,
Q-798-5), or each file a `--transcript FILE` names, and with `--helpers` each one's own sub-agent
transcripts beside it, `<folder>/<id>/subagents/*.jsonl` (measured in this runtime, Q-CM-1). A
sub-agent sees its parent's session id (measured), so a session passes `--helpers` only when it is
the top-level session; without it no sibling's tokens enter its line. It sums, over the entries
with a distinct message id across all of them, the four token counts of each entry's usage record
(input, cache creation input, cache read input and output) and any other whole `*_tokens` count
whose key names no cache (so a flattened cache-creation count is never counted twice), named
`other`. Of an entry it reads only its message id, its timestamp and those counts, and prints
no text of the transcript. Its one line is `Usage: <n> tokens (input <a>, cache write <b>, cache
read <c>, output <d>[, other <e>])`, `<n>` the sum, or `Usage: not shown (<class>)`, the class one
of `no-session-id`, `no-transcript`, `unreadable` or `no-usage-record`, never a path, an id, 0 or an
estimate. `--since <UTC time>` (`YYYY-MM-DDTHH:MM:SSZ`) keeps only the messages first written at or
after that time (Q-798-7). Read-only: it writes no file, posts nothing and makes no network call.
Usage: python3 scripts/agk/usage.py [--transcript FILE ...] [--since TIME] [--helpers]
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import utf8_output

USAGE = "usage: usage.py [--transcript FILE ...] [--since YYYY-MM-DDTHH:MM:SSZ] [--helpers]"
NOT_SHOWN = "Usage: not shown"
NAMES = ("input", "cache write", "cache read", "output")
COUNTS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)
SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
SINCE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def stamp(value: object) -> datetime | None:
    """An entry's timestamp as a UTC time, or None when it cannot be read."""
    if not isinstance(value, str):
        return None
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when.astimezone(UTC) if when.tzinfo else None


def session_transcript(env: dict) -> tuple[Path | None, str]:
    """The running session's own transcript, by the runtime's variables (verify, Q-798-5), or the
    class of `not shown` when there is none."""
    session = env.get("CLAUDE_CODE_SESSION_ID", "")
    if not SESSION_ID.fullmatch(session):
        return None, "no-session-id"
    home = Path(env["CLAUDE_CONFIG_DIR"]) if env.get("CLAUDE_CONFIG_DIR") else None
    if home is None:
        if not env.get("HOME"):
            return None, "no-transcript"
        home = Path(env["HOME"]) / ".claude"
    try:
        found = sorted((home / "projects").glob(f"*/{session}.jsonl"))
    except OSError:
        return None, "unreadable"
    return (found[0], "") if found else (None, "no-transcript")


def with_helpers(path: Path) -> list[Path]:
    """The file and its sub-agents' transcripts, `<folder>/<stem>/subagents/*.jsonl` (Q-CM-1)."""
    try:
        return [path, *sorted((path.parent / path.stem / "subagents").glob("*.jsonl"))]
    except OSError:
        return [path]


def record_of(line: str) -> tuple[str, datetime | None, list[int]] | None:
    """(message id, timestamp, [input, cache write, cache read, output, other]) of one line; None
    without a usage record."""
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    message = entry.get("message") if isinstance(entry, dict) else None
    used = message.get("usage") if isinstance(message, dict) else None
    mid = message.get("id") if isinstance(message, dict) else None
    if not isinstance(used, dict) or not isinstance(mid, str) or not mid:
        return None
    counts = [used.get(k, 0) for k in COUNTS]
    if not all(type(c) is int and c >= 0 for c in counts) or not any(k in used for k in COUNTS):
        return None
    other = sum(
        v
        for k, v in used.items()
        if k not in COUNTS
        and isinstance(k, str)
        and k.endswith("_tokens")
        and "cache" not in k
        and type(v) is int
        and v >= 0
    )
    return mid, stamp(entry.get("timestamp")), [*counts, other]


def figures(paths: list[Path], since: datetime | None) -> tuple[list[int] | None, str]:
    """The five sums over distinct message ids across the files, each counted at its first entry,
    or None and the class of `not shown`."""
    seen: set[str] = set()
    sums: list[int] | None = None
    for path in paths:
        if not path.exists():
            return None, "no-transcript"
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None, "unreadable"
        for line in text.splitlines():
            record = record_of(line)
            if record is None or record[0] in seen:
                continue
            mid, when, counts = record
            seen.add(mid)
            if since is not None and (when is None or when < since):
                continue
            sums = [a + b for a, b in zip(sums or [0] * 5, counts, strict=True)]
    return (sums, "") if sums is not None else (None, "no-usage-record")


def line_of(sums: list[int] | None, reason: str) -> str:
    """The one printed line of ADR-0835."""
    if sums is None:
        return f"{NOT_SHOWN} ({reason})"
    kinds = [f"{name} {n}" for name, n in zip(NAMES, sums, strict=False)]
    kinds += [f"other {sums[4]}"] if sums[4] else []
    return f"Usage: {sum(sums)} tokens ({', '.join(kinds)})"


def total(path: Path, since: datetime | None) -> int | None:
    """The sum of one file; None for no figure."""
    sums, _ = figures([path], since)
    return None if sums is None else sum(sums)


def parse(argv: list[str]) -> dict | None:
    options: dict = {"transcript": [], "since": None, "helpers": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--helpers":
            options["helpers"] = True
            i += 1
            continue
        if arg not in ("--transcript", "--since") or i + 1 >= len(argv):
            return None
        value = argv[i + 1]
        if arg == "--since":
            if not SINCE.fullmatch(value) or stamp(value) is None:
                return None
            options["since"] = stamp(value)
        else:
            options["transcript"].append(Path(value))
        i += 2
    return options


def session_line(
    env: dict, transcripts: list[Path], since: datetime | None, helpers: bool = False
) -> str:
    """The line for the named files, else for the running session's own; with `helpers`, each
    file's own sub-agents too. A sub-agent sees its parent's session id (measured, ADR-0835), so
    the sub-agent files are read only when the top-level session asks, never by default."""
    if not transcripts:
        path, reason = session_transcript(env)
        if path is None:
            return line_of(None, reason)
        transcripts = [path]
    files = [p for t in transcripts for p in (with_helpers(t) if helpers else [t])]
    return line_of(*figures(files, since))


def tokens_figure(env: dict) -> str:
    """The running session's figure, with its own sub-agents, as a steward's `Ended:` note carries
    it (brief #2020 answer 5): `<n> (input <a>, ...)` or `not shown (<class>)`."""
    line = session_line(env, [], None, helpers=True)
    return line.removeprefix("Usage: ").replace(" tokens", "", 1)


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    options = parse(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(f"{USAGE}\n(refused: an option of usage.py is missing or malformed)")
        return 2
    print(
        session_line(dict(os.environ), options["transcript"], options["since"], options["helpers"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
