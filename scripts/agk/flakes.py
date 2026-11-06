"""The flake ledger: what is due on it (brief #435, ADR-0234), and a strike added (brief #670,
ADR-0323).

    python3 scripts/agk/flakes.py [check] [--today YYYY-MM-DD] [--json]
    python3 scripts/agk/flakes.py add --test ID [--owner ID] [--issue REF] [--today YYYY-MM-DD]

Reads `docs/runs/flakes.md` at the top of the repository, one Markdown table with the header
`| test | owner | strikes | status | expires | issue |`, and lists, in the order of the file:

- `expired`: each entry whose `expires` date is before today (a quarantine, or since ADR-0323 a
  watched strike: a fix removes the row);
- `brief due`: each entry with two strikes or more and no issue;
- `malformed`: each row that is not an entry (its line number and the column at fault, never the
  value), each row after a break in the table, and a file without the one ledger table.

The table ends at the first line that is not a row; a row below it, outside a fence, is malformed
(it is never skipped). Rows inside a fenced block are an example and are not read. Today is
`--today`, else the UTC date (as `date -u`). Exit 0 when nothing is listed (also when there is no
ledger), 1 otherwise, 2 on a bad call or a ledger that cannot be read. It reads one file, uses no
network and changes nothing. It is not a governance step and blocks nothing; a project that wants
it in its checks adds it. `check` is the same call, named.

`add` records one strike for the test (`project_tests.py` calls it after a test that failed in the
full run passed alone, SPEC-0044 rule 1 as amendment 135 proposes): a new row is `watch` with one
strike, the owner (`--owner`, else `unassigned`) and an expiry 30 days from today; an existing row
gains one strike and keeps its owner, status and expiry (an empty expiry gets one), and `--issue`
fills an empty issue. The ledger is created when absent. It refuses (exit 2), changing nothing, a
ledger with a malformed row and a test id or owner that is not one cell, naming the option.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, repo_root

NAME = "flakes"
LEDGER = "docs/runs/flakes.md"
USAGE = "usage: flakes.py [--today YYYY-MM-DD] [--json]"
ADD_USAGE = "usage: flakes.py add --test ID [--owner ID] [--issue REF] [--today YYYY-MM-DD]"
EXPIRY_DAYS = 30
UNASSIGNED = "unassigned"
NEW_LEDGER = "# Flake ledger\n\nOne row per flaky test (ADR-0234).\n\n"
COLUMNS = ("test", "owner", "strikes", "status", "expires", "issue")
STATUSES = ("watch", "quarantined")
DUE_STRIKES = 2
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
ISSUE = re.compile(r"#\d+|https?://\S+")
SEPARATOR = re.compile(r":?-{3,}:?")
FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Report:
    entries: int = 0
    expired: list[dict] = field(default_factory=list)
    brief_due: list[dict] = field(default_factory=list)
    malformed: list[dict] = field(default_factory=list)

    def listed(self) -> int:
        return len(self.expired) + len(self.brief_due) + len(self.malformed)


def utc_today() -> str:
    """Today's date on the UTC clock, as `date -u +%Y-%m-%d` prints it."""
    return datetime.now(UTC).date().isoformat()


def as_date(text: str) -> date | None:
    if not DATE.fullmatch(text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def cells(line: str) -> list[str] | None:
    """The cells of a table row (`| a | b |`), or None when LINE is not a row."""
    text = line.strip()
    if not text.startswith("|"):
        return None
    inner = text[1:-1] if text.endswith("|") and len(text) > 1 else text[1:]
    return [c.strip() for c in inner.split("|")]


def is_header(line: str) -> bool:
    return [c.lower() for c in cells(line) or []] == list(COLUMNS)


def is_separator(line: str) -> bool:
    row = cells(line)
    return bool(row) and len(row) == len(COLUMNS) and all(SEPARATOR.fullmatch(c) for c in row)


def fault(row: list[str]) -> str | None:
    """Why ROW is not an entry, naming the column and never its value; None for a good row."""
    if len(row) != len(COLUMNS):
        return f"{len(row)} cells, the header has {len(COLUMNS)}"
    test, owner, strikes, status, expires, issue = row
    if not test:
        return "test is empty"
    if not owner:
        return "owner is empty"
    if not OWNER.fullmatch(owner):
        return "owner is not one role or session id"
    if not strikes.isdigit() or not strikes.isascii():
        return "strikes is not a whole number"
    if status not in STATUSES:
        return "status is not watch or quarantined"
    if status == "quarantined" and not expires:
        return "expires is empty for a quarantine"
    if expires and as_date(expires) is None:
        return "expires is not a YYYY-MM-DD date"
    if issue and not ISSUE.fullmatch(issue):
        return "issue is not #n or a link"
    return None


def read_ledger(text: str, today: str) -> Report:
    """The report of the ledger TEXT on the day TODAY (YYYY-MM-DD)."""
    report = Report()
    day = date.fromisoformat(today)
    lines = text.splitlines()
    seen: dict[str, int] = {}
    fenced = False
    header_at: int | None = None
    in_table = False
    n = 0
    while n < len(lines):
        line, number = lines[n], n + 1
        n += 1
        if FENCE.match(line):
            fenced, in_table = not fenced, False
            continue
        if fenced:
            continue
        if in_table:
            row = cells(line)
            if row is None:
                in_table = False
            else:
                add_row(report, row, number, day, seen)
                continue
        if is_header(line):
            if header_at is not None:
                report.malformed.append(
                    {"line": number, "reason": "a second ledger table (the ledger holds one)"}
                )
                if n < len(lines) and is_separator(lines[n]):
                    n += 1  # its separator is part of it, not a stray row
                continue
            header_at = number
            if n < len(lines) and is_separator(lines[n]):
                n += 1
                in_table = True
            else:
                report.malformed.append(
                    {"line": number + 1, "reason": "no separator line under the header"}
                )
                if n < len(lines) and cells(lines[n]) is not None:
                    n += 1  # that line is reported already, by its number
        elif header_at is not None and cells(line) is not None:
            # A row cut off from the table (a blank line, prose) is reported, never hidden.
            report.malformed.append({"line": number, "reason": "a row outside the ledger table"})
    if header_at is None:
        header = " | ".join(COLUMNS)
        report.malformed.insert(0, {"line": 1, "reason": f"no ledger table (header: {header})"})
    return report


def add_row(report: Report, row: list[str], number: int, day: date, seen: dict[str, int]):
    why = fault(row)
    if why is None and row[0] in seen:
        why = f"test is listed already on line {seen[row[0]]}"
    if why is not None:
        report.malformed.append({"line": number, "reason": why})
        return
    test, owner, strikes, status, expires, issue = row
    seen[test] = number
    report.entries += 1
    ends = as_date(expires)
    if ends is not None and ends < day:
        entry = {"line": number, "test": test, "owner": owner, "expires": expires}
        if status == "watch":  # ADR-0323; a quarantine's entry is as ADR-0234 printed it
            entry["status"] = status
        report.expired.append(entry)
    if int(strikes) >= DUE_STRIKES and not issue:
        report.brief_due.append(
            {"line": number, "test": test, "owner": owner, "strikes": int(strikes)}
        )


def held(entry: dict) -> str:
    return "watched" if entry.get("status") == "watch" else "quarantined"


def text_lines(report: Report) -> list[str]:
    """The listed lines in file order (an entry in both lists: expired first), then the summary."""
    items: list[tuple[int, int, str]] = []
    for e in report.expired:
        items.append(
            (
                e["line"],
                0,
                f"expired: line {e['line']}: {e['test']} "
                f"(owner {e['owner']}; {held(e)} until {e['expires']})",
            )
        )
    for e in report.brief_due:
        items.append(
            (
                e["line"],
                1,
                f"brief due: line {e['line']}: {e['test']} "
                f"(owner {e['owner']}; {e['strikes']} strikes, no issue)",
            )
        )
    for e in report.malformed:
        items.append((e["line"], 2, f"malformed: line {e['line']}: {e['reason']}"))
    out = [text for _, _, text in sorted(items)]
    if report.listed():
        out.append(
            f"flakes: {report.listed()} listed ({len(report.expired)} expired, "
            f"{len(report.brief_due)} brief due, {len(report.malformed)} malformed) in {LEDGER}"
        )
    else:
        noun = "entry" if report.entries == 1 else "entries"
        out.append(f"flakes: nothing due ({report.entries} {noun}) in {LEDGER}")
    return out


def parse_args(args: list[str]) -> tuple[str | None, bool] | None:
    today: str | None = None
    as_json = False
    i = 0
    while i < len(args):
        if args[i] == "--json" and not as_json:
            as_json = True
        elif args[i] == "--today" and today is None and i + 1 < len(args):
            today = args[i + 1]
            i += 1
        else:
            return None
        i += 1
    return today, as_json


class Refused(Exception):
    """A strike that cannot be added; the message names the option or the ledger (exit 2)."""


def row_text(row: list[str]) -> str:
    return "| " + " | ".join(row) + " |"


def add_strike(
    text: str | None, test: str, owner: str, today: str, issue: str = ""
) -> tuple[str, list[str]]:
    """The ledger TEXT (None: absent) with one strike for TEST, and the row as written."""
    if not test or "|" in test or "\n" in test or test != test.strip():
        raise Refused("the test id is not one table cell (option: --test)")
    if not OWNER.fullmatch(owner):
        raise Refused("the owner is not one role or session id (option: --owner)")
    if issue and not ISSUE.fullmatch(issue):
        raise Refused("the issue is not #n or a link (option: --issue)")
    expiry = (date.fromisoformat(today) + timedelta(days=EXPIRY_DAYS)).isoformat()
    if text is None:
        text = NEW_LEDGER + "| " + " | ".join(COLUMNS) + " |\n" + "| --- " * len(COLUMNS) + "|\n"
    report = read_ledger(text, today)
    if report.malformed:
        raise Refused(f"the ledger has malformed rows; fix them first ({LEDGER})")
    lines = text.splitlines(keepends=True)
    last = None
    fenced = False
    in_table = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            fenced, in_table = not fenced, False
            continue
        if fenced:
            continue
        if is_header(line):
            in_table = True
            last = i + 1  # the separator
            continue
        if in_table:
            row = cells(line)
            if row is None:
                break
            if i == last:
                continue
            last = i
            if row[0] == test:
                row[2] = str(int(row[2]) + 1)
                row[4] = row[4] or expiry
                row[5] = row[5] or issue
                lines[i] = row_text(row) + "\n"
                return "".join(lines), row
    row = [test, owner, "1", "watch", expiry, issue]
    if last is None:  # read_ledger has refused a file without the table
        raise Refused(f"the ledger has malformed rows; fix them first ({LEDGER})")
    if not lines[last].endswith("\n"):
        lines[last] += "\n"
    lines.insert(last + 1, row_text(row) + "\n")
    return "".join(lines), row


def strike_lines(row: list[str]) -> list[str]:
    test, owner, strikes, _, expires, issue = row
    out = [f"{NAME}: strike {strikes} for {test} (owner {owner}; expires {expires}) in {LEDGER}"]
    if int(strikes) >= DUE_STRIKES and not issue:
        out.append(f"{NAME}: brief due: {test} has {strikes} strikes and no issue")
    return out


def record_strike(root: Path, test: str, owner: str, today: str, issue: str = "") -> list[str]:
    """Write one strike for TEST to the ledger under ROOT; the lines that say what was written."""
    path = root / LEDGER
    try:
        text = path.read_text(encoding="utf-8") if path.is_file() else None
    except (OSError, UnicodeDecodeError):
        raise Refused(f"cannot read the ledger ({LEDGER})") from None
    new, row = add_strike(text, test, owner, today, issue)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
    except OSError:
        raise Refused(f"cannot write the ledger ({LEDGER})") from None
    return strike_lines(row)


def add_main(args: list[str]) -> int:
    opts: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i] not in ("--test", "--owner", "--issue", "--today") or args[i] in opts:
            print(ADD_USAGE)
            return 2
        if i + 1 >= len(args):
            print(ADD_USAGE)
            return 2
        opts[args[i]] = args[i + 1]
        i += 2
    if "--test" not in opts:
        print(ADD_USAGE)
        return 2
    today = opts.get("--today") or utc_today()
    if as_date(today) is None:
        print(f"{NAME}: --today is not a YYYY-MM-DD date")
        return 2
    try:
        lines = record_strike(
            repo_root(),
            opts["--test"],
            opts.get("--owner", UNASSIGNED),
            today,
            opts.get("--issue", ""),
        )
    except (Refused, CheckError) as exc:
        print(f"{NAME}: {exc}")
        return 2
    print("\n".join(lines))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["add"]:
        return add_main(args[1:])
    if args[:1] == ["check"]:
        args = args[1:]
    parsed = parse_args(args)
    if parsed is None:
        print(USAGE)
        return 2
    today, as_json = parsed
    if today is not None and as_date(today) is None:
        print(f"{NAME}: --today is not a YYYY-MM-DD date")
        return 2
    today = today or utc_today()
    try:
        path = repo_root() / LEDGER
    except CheckError as exc:
        print(f"{NAME}: {exc}")
        return 2
    present = path.is_file()
    if present:
        try:
            report = read_ledger(path.read_text(encoding="utf-8"), today)
        except (OSError, UnicodeDecodeError):
            print(f"{NAME}: cannot read the ledger ({LEDGER})")
            return 2
    else:
        report = Report()
    if as_json:
        doc = {
            "ledger": LEDGER,
            "present": present,
            "today": today,
            "entries": report.entries,
            "expired": report.expired,
            "brief_due": report.brief_due,
            "malformed": report.malformed,
        }
        print(json.dumps(doc, indent=1))
    elif present:
        print("\n".join(text_lines(report)))
    else:
        print(f"{NAME}: no ledger at {LEDGER}; nothing due")
    return 1 if report.listed() else 0


if __name__ == "__main__":
    sys.exit(main())
