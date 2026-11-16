"""Print a log with every secret and personal value redacted, `agk logs` (SPEC-0042 rule 11).

Usage: python3 scripts/agk/guard_logs.py [--max-lines N] FILE|-|--refusals

Brief #561. Each finding of `guard.scan_text` is replaced by `[<KIND>-<n>]`, numbered per kind in
order of first appearance over the lines printed, so one value keeps one label in a run; the
mapping lives in memory only. Everything else of a line is printed unchanged. `--max-lines N`
(default 2000) prints only the last N lines. The last line holds counts per kind only. Bytes that
are not UTF-8 are replaced. It opens no socket, runs no program and writes no file: the
`[guard] patterns` come from the nearest `agk.toml` at or above the current folder, found by
walking up (patterns only add, so no default-branch check is needed). A usage error, a file it
cannot read or a refused `[guard]` table exits 2, naming the option or the setting, never a path
or a value.

Brief #1410 (ADR-0593): every hook refusal is kept on the machine. `record_refusal` appends one JSON
line per denial to `<git common dir>/agk/refusals.log` (found by reading `.git` and its `commondir`,
no program run): `at` (UTC), `session`, `role`, `hook`, `reason` (a code), `text` (the command or
path after `scan_text` redaction, cut at 500 characters) and, for a hook error, `error` with the
exception's type and the hook's function and line, never a value. The file is never tracked, rolls
over at 1 MB keeping one older file, and a failed write returns False and changes no decision.
`--refusals` prints both files, the older first, through the same redaction; `today_line` is the
count by reason that `agk status` prints.
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from collections import Counter, deque
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import utf8_output
from guard import scan_text

import config

DEFAULT_MAX_LINES = 2000
USAGE = "usage: guard_logs.py [--max-lines N] FILE|-|--refusals"
REFUSALS = "refusals.log"
ROLL_BYTES = 1_000_000
CUT = 500
NAME = re.compile(r"[\w.@-]{1,80}")


class Usage(Exception):
    """A usage error, an unreadable file or a refused setting (exit 2)."""


# --- the refusal log (brief #1410) ------------------------------------------------------------


def common_dir(start: Path) -> Path | None:
    """The git common dir of the checkout holding START, read from `.git` and `commondir`."""
    for folder in (start, *start.parents):
        dot = folder / ".git"
        if dot.is_dir():
            return dot
        if dot.is_file():
            head = dot.read_text(encoding="utf-8").strip()
            if not head.startswith("gitdir:"):
                return None
            gitdir = folder / head[len("gitdir:") :].strip()
            common = gitdir / "commondir"
            if common.is_file():
                return (gitdir / common.read_text(encoding="utf-8").strip()).resolve()
            return gitdir.resolve()
    return None


def refusal_path(root: Path) -> Path | None:
    found = common_dir(Path(os.path.abspath(root)))
    return found / "agk" / REFUSALS if found else None


def error_of(exc: BaseException, hook_file: str) -> dict:
    """The exception's type and the deepest place in the hook's own file; never its message."""
    frames = traceback.extract_tb(exc.__traceback__)
    own = [f for f in frames if os.path.basename(f.filename) == os.path.basename(hook_file)]
    place = (own or frames or [None])[-1]
    where = f"{place.name}:{place.lineno}" if place else "unknown"
    return {"type": type(exc).__name__, "place": where}


def refused_text(payload: object) -> str:
    data = payload.get("tool_input") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return ""
    for field in ("command", "file_path", "notebook_path", "pattern", "path"):
        if isinstance(data.get(field), str):
            return data[field]
    return ""


def record_refusal(
    payload: object, hook: str, reason: str, role: str, error: dict | None = None,
    now: datetime | None = None,
) -> bool:
    """Append one redacted line for a denial; False when it cannot, which changes nothing."""
    try:
        cwd = payload.get("cwd") if isinstance(payload, dict) else None
        root = os.environ.get("CLAUDE_PROJECT_DIR") or (cwd if isinstance(cwd, str) else "")
        path = refusal_path(Path(root or os.getcwd()))
        if path is None:
            return False
        session = os.environ.get("AGK_SESSION") or (
            payload.get("session_id") if isinstance(payload, dict) else None
        )
        role = os.environ.get("AGK_ROLE") or role
        try:
            patterns = config.guard_patterns(Path(root or os.getcwd()))
        except Exception:  # noqa: BLE001 - a refused table: the built-in detectors still redact
            patterns = ()
        text = redact(refused_text(payload), patterns)[0]
        line = {
            "at": (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session": session if isinstance(session, str) and NAME.fullmatch(session) else "unknown",
            "role": role if NAME.fullmatch(role or "") else "unknown",
            "hook": hook,
            "reason": redact(reason, patterns)[0][:CUT],
            "text": text[:CUT],
        }
        if error:
            line["error"] = error
        path.parent.mkdir(exist_ok=True)
        if path.is_file() and path.stat().st_size >= ROLL_BYTES:
            os.replace(path, path.with_name(REFUSALS + ".1"))
        with path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(line, sort_keys=True) + "\n")
        return True
    except Exception:  # noqa: BLE001 - keeping the line never changes the decision
        return False


def refusal_files(root: Path) -> list[Path]:
    path = refusal_path(root)
    if path is None:
        return []
    return [p for p in (path.with_name(REFUSALS + ".1"), path) if p.is_file()]


def today_line(root: Path, now: datetime) -> str:
    """`refusals today: <n> (<reason> <k>, ...)`, most first, or `refusals today: none`."""
    day, counts = now.strftime("%Y-%m-%d"), Counter()
    for path in refusal_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for raw in text.splitlines():
            try:
                line = json.loads(raw)
            except ValueError:
                continue
            if isinstance(line, dict) and str(line.get("at", "")).startswith(day):
                counts[str(line.get("reason", "unknown"))] += 1
    if not counts:
        return "refusals today: none"
    parts = ", ".join(f"{reason} {n}" for reason, n in counts.most_common())
    return f"refusals today: {sum(counts.values())} ({parts})"


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
        if source == "--refusals":
            files = refusal_files(Path.cwd())
            if not files:
                print("agk logs: no refusals recorded")
                return 0
            text = "".join(read_tail(str(p), max_lines) for p in files)
            text = "".join(text.splitlines(keepends=True)[-max_lines:])
        else:
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
