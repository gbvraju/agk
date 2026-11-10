"""Print the token figure of the running session: `Usage: <n> tokens` or `Usage: not shown`.

SPEC-0045 rule 8 (brief #798 build (a), amendment 145 items 7 and 8). It reads the running session's
own transcript file, found by the runtime's session id variable under the runtime's home folder
(verify: `CLAUDE_CODE_SESSION_ID` and `<CLAUDE_CONFIG_DIR or ~/.claude>/projects/*/<id>.jsonl` are
read from this cloud runtime, not from its documentation, Q-798-5), or the file `--transcript FILE`
names. It sums, over the entries with a distinct message id, the four token counts of each entry's
usage record: input, cache creation input, cache read input and output (Q-798-6). Of an entry it
reads only its message id, its timestamp and those counts, and prints no text of the transcript.
`--since <UTC time>` (`YYYY-MM-DDTHH:MM:SSZ`, the form of a GitHub comment's `created_at`) keeps
only the messages first written at or after that time, so each `Report:` carries the tokens since
the previous one (Q-798-7). No transcript, an unreadable one or one with no usage record prints
`Usage: not shown`, never 0 and never an estimate. Read-only: it writes no file, posts nothing and
makes no network call. Usage: python3 scripts/agk/usage.py [--transcript FILE] [--since TIME]
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

USAGE = "usage: usage.py [--transcript FILE] [--since YYYY-MM-DDTHH:MM:SSZ]"
NOT_SHOWN = "Usage: not shown"
COUNTS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
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


def session_transcript(env: dict) -> Path | None:
    """The running session's own transcript, by the runtime's variables (verify, Q-798-5)."""
    session = env.get("CLAUDE_CODE_SESSION_ID", "")
    if not SESSION_ID.fullmatch(session):
        return None
    home = Path(env["CLAUDE_CONFIG_DIR"]) if env.get("CLAUDE_CONFIG_DIR") else None
    if home is None:
        if not env.get("HOME"):
            return None
        home = Path(env["HOME"]) / ".claude"
    try:
        found = sorted((home / "projects").glob(f"*/{session}.jsonl"))
    except OSError:
        return None
    return found[0] if found else None


def record_of(line: str) -> tuple[str, datetime | None, int] | None:
    """(message id, timestamp, the four counts summed) of one line; None without a usage record."""
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
    return mid, stamp(entry.get("timestamp")), sum(counts)


def total(path: Path, since: datetime | None) -> int | None:
    """The sum over distinct message ids, each counted at its first entry; None for no figure."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    seen: set[str] = set()
    figure = None
    for line in text.splitlines():
        record = record_of(line)
        if record is None or record[0] in seen:
            continue
        mid, when, tokens = record
        seen.add(mid)
        if since is not None and (when is None or when < since):
            continue
        figure = (figure or 0) + tokens
    return figure


def parse(argv: list[str]) -> dict | None:
    options: dict = {"transcript": None, "since": None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg not in ("--transcript", "--since") or i + 1 >= len(argv):
            return None
        value = argv[i + 1]
        if arg == "--since":
            if not SINCE.fullmatch(value) or stamp(value) is None:
                return None
            options["since"] = stamp(value)
        else:
            options["transcript"] = Path(value)
        i += 2
    return options


def main(argv: list[str] | None = None) -> int:
    options = parse(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(f"{USAGE}\n(refused: an option of usage.py is missing or malformed)")
        return 2
    path = options["transcript"] or session_transcript(dict(os.environ))
    figure = total(path, options["since"]) if path is not None else None
    print(NOT_SHOWN if figure is None else f"Usage: {figure} tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
