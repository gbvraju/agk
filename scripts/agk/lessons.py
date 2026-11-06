"""The guard ladder of the catch logs, `lessons.py ladder` (brief #645, ADR-0309).

Usage: python3 scripts/agk/lessons.py ladder [--root DIR] [--today YYYY-MM-DD]

Every lesson a catch log records (`docs/runs/<name>-catches-<n>.md`, a table under `## The catches`
with the columns `#`, `Date`, `Kind`, `Cause` and `Guard`, and optionally `Cost`) carries a guard
level on one ladder, weakest first:

- `lesson`: no guard yet; it may be followed or not. Written `lesson`, `pending #<n>` (a brief that
  builds the guard) or `pending (to be filed)`.
- `rule`: a line of an agent or guide file that cites the row as `(row <n>)`.
- `test`: a test that fails the case.
- `check`: a governance check or a command that refuses the case.
- `workflow`: CI or a scheduled job enforces it (on the owner's hold list).

A guard after `lesson` is written `` <level> `<path>` `` with an optional note in parentheses;
several guards are separated by `; `. A row's level is the strongest it holds.

Promotion rules, decided from the logs alone (a due row is listed, never promoted):

- A `lesson` row is due to become a `rule` when another row has the same kind and cause (compared
  without case, spacing or a final period), or when its cost is one hour or more (`N h`, `N min`).
- A `rule` row is due to become a `test` or a `check` when a row of the same kind and cause is dated
  after it (its date stands for the day its rule line was added), or when it has stood 30 days.
- A `test` or `check` row is never due: a check becomes a workflow only with the owner's yes.

It prints every row with its level, the rows due to climb and why, every guard whose file is
missing or has no line citing the row, every malformed guard, every row the date rules cannot
decide, every log without a Guard column, and one count line. It reads files only: no network, no
program, no write. Exit 1 on a malformed guard or a missing line or file; the due list never
blocks. A usage error exits 2 naming the option, never a value.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

LEVELS = ["lesson", "rule", "test", "check", "workflow"]
RULE_DAYS = 30
LOG_GLOB = "*-catches-*.md"
USAGE = "usage: lessons.py ladder [--root DIR] [--today YYYY-MM-DD]"
NOTE = r"(?: \([^()]*(?:\([^()]*\)[^()]*)*\))?"
LESSON = r"(lesson)|pending #[1-9]\d*|pending \(to be filed\)"
GUARD = re.compile(rf"^(?:(rule|test|check|workflow) `([^`]+)`|{LESSON}){NOTE}$")
COST = re.compile(r"^(\d+(?:\.\d+)?) (h|min)\b")
DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")
REQUIRED = ("#", "Date", "Kind", "Cause", "Guard")


class Usage(Exception):
    """A usage error (exit 2)."""


@dataclass
class Row:
    log: str
    number: str
    date: date | None
    kind: str
    cause: str
    cost: str
    guards: list[tuple[str, str]] = field(default_factory=list)  # (level, path or "")
    malformed: bool = False
    cells: bool = True

    @property
    def ident(self) -> str:
        return f"{self.log}#{self.number}"

    @property
    def level(self) -> str:
        return max((g[0] for g in self.guards), key=LEVELS.index, default="lesson")

    @property
    def key(self) -> tuple[str, str]:
        cause = " ".join(self.cause.lower().split()).rstrip(".")
        return self.kind.strip().lower(), cause


def parse_args(args: list[str]) -> tuple[Path, date]:
    if not args or args[0] != "ladder":
        raise Usage(USAGE)
    root, today = Path.cwd(), datetime.now(UTC).date()
    rest = args[1:]
    while rest:
        option = rest.pop(0)
        if option not in ("--root", "--today"):
            raise Usage(USAGE)
        if not rest:
            raise Usage(f"{USAGE} (option: {option})")
        value = rest.pop(0)
        if option == "--root":
            root = Path(value)
        else:
            refused = Usage("the date must be YYYY-MM-DD (option: --today)")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise refused
            try:
                today = date.fromisoformat(value)
            except ValueError:
                raise refused from None
    return root, today


def parse_guard(cell: str) -> tuple[list[tuple[str, str]], bool]:
    guards = []
    for part in cell.split("; "):
        found = GUARD.match(part.strip())
        if not found:
            return [], True
        level = found.group(1) or "lesson"
        path = found.group(2) or ""
        if path and (path.startswith("/") or ".." in Path(path).parts):
            return [], True
        guards.append((level, path))
    return guards, False


def read_log(path: Path) -> tuple[list[Row], bool]:
    """Rows of one log, and False when it has no Guard column (not on the ladder)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if "## The catches" not in text:
        return [], False
    lines = [ln for ln in text.split("## The catches", 1)[1].splitlines() if ln.startswith("|")]
    cells = [[c.strip() for c in ln.strip().strip("|").split(" | ")] for ln in lines]
    if not cells or not all(name in cells[0] for name in REQUIRED):
        return [], False
    header, rows = cells[0], []
    for body in cells[2:]:
        values = dict(zip(header, body, strict=False))
        found = DATE.match(values.get("Date", ""))
        try:
            when = date.fromisoformat(found.group(1)) if found else None
        except ValueError:
            when = None
        guards, malformed = parse_guard(values.get("Guard", ""))
        rows.append(
            Row(
                log=path.stem,
                number=values.get("#", ""),
                date=when,
                kind=values.get("Kind", ""),
                cause=values.get("Cause", ""),
                cost=values.get("Cost", ""),
                guards=guards,
                malformed=malformed or len(body) != len(header),
                cells=len(body) == len(header),
            )
        )
    return rows, True


def costs_an_hour(cost: str) -> bool:
    found = COST.match(cost)
    if not found:
        return False
    amount = float(found.group(1))
    return amount >= 1 if found.group(2) == "h" else amount >= 60


def due(row: Row, rows: list[Row], today: date) -> list[str]:
    """The reasons a well-formed row is due to climb, in a fixed order."""
    same = [r for r in rows if r is not row and not r.malformed and r.key == row.key]
    reasons = []
    if row.level == "lesson":
        reasons += [f"lesson -> rule: {r.ident} has the same kind and cause" for r in same]
        if costs_an_hour(row.cost):
            reasons.append("lesson -> rule: its cost is one hour or more")
    elif row.level == "rule" and row.date is not None:
        later = [r for r in same if r.date is not None and r.date > row.date]
        reasons += [f"rule -> test or check: {r.ident} repeats it after the rule" for r in later]
        if today - row.date >= timedelta(days=RULE_DAYS):
            reasons.append(f"rule -> test or check: it has stood {RULE_DAYS} days since {row.date}")
    return reasons


def missing(row: Row, root: Path) -> list[str]:
    found = []
    for level, path in row.guards:
        if not path:
            continue
        target = root / path
        if not target.is_file():
            found.append(f"{path} does not exist")
        elif level == "rule":
            text = target.read_text(encoding="utf-8", errors="replace")
            if f"(row {row.number})" not in text:
                found.append(f"no line of {path} cites (row {row.number})")
    return found


def ladder(root: Path, today: date) -> tuple[list[str], int]:
    logs = sorted((root / "docs" / "runs").glob(LOG_GLOB))
    if not logs:
        return ["lessons ladder: no catch logs under docs/runs"], 0
    rows: list[Row] = []
    off = []
    for path in logs:
        found, on = read_log(path)
        rows += found
        if not on:
            off.append(f"not on the ladder: {path.stem} (no Guard column)")
    out, dues, gaps, bad = [], [], [], []
    for row in rows:
        if row.malformed:
            out.append(f"row {row.ident} malformed")
            what = (
                "the guard is not one of the ladder's forms"
                if row.cells
                else "its cells do not match the header"
            )
            bad.append(f"malformed {row.ident}: {what}")
            continue
        out.append(f"row {row.ident} {row.level}")
        if row.level == "rule" and row.date is None:
            dues.append(f"undecided {row.ident}: the date is not YYYY-MM-DD")
        dues += [f"due {row.ident} {reason}" for reason in due(row, rows, today)]
        gaps += [f"missing {row.ident}: {what}" for what in missing(row, root)]
    good = [r for r in rows if not r.malformed]
    counts = ", ".join(f"{level} {sum(r.level == level for r in good)}" for level in LEVELS)
    n_due = sum(line.startswith("due ") for line in dues)
    out += dues + gaps + bad + off
    tally = f"due {n_due}; missing {len(gaps)}; malformed {len(bad)}"
    out.append(f"lessons ladder: {len(rows)} rows ({counts}); {tally}")
    return out, 1 if gaps or bad else 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        root, today = parse_args(args)
    except Usage as exc:
        print(f"lessons: {exc}")
        return 2
    lines, code = ladder(root, today)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
