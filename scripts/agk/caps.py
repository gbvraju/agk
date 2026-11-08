"""The cap of a builder pull request and what the build used (SPEC-0049 rules 3, 5 to 7, brief
#714, ADR-0324). Read-only: GET only, posts nothing and writes no file.

`conductor.py sweep` calls `over_lines`, which prints nothing without the `[caps]` table of
agk.toml (`config.caps_settings`). For each open pull request with a line `Brief: #n` it reads the
brief and its comments and the pull request's comments, and gives one line per cap passed,
`OVER #<brief> <used>/<cap> tokens|hours #<pr>`, and `UNKNOWN #<brief> tokens #<pr>` when no token
figure was reported; ` size unknown` ends the line when the brief's `Size:` cannot be read.

- The cap (rule 3): the size of the brief's one valid `Size:` line (`session.SIZE`, the parse that
  `check_brief.py` applies); a missing, repeated or unreadable line, or a brief that cannot be
  read, gives the `L` cap.
- The tokens (rule 5): `metrics.usage_of` over the author's `Report:` lines, plus the figure that
  ends the author's newest `Progress:` line (`; Usage: <n> tokens`) when it was edited after the
  newest `Report:`; `unknown` when no figure was reported, never 0 and never over.
- The hours (rule 6): the builder's turns only. From the newest `taken:` comment by the pull
  request's author at or before its opening, to the first `Report: ... ready for review`; then
  from each `Verdict: fix list` or `Correction:` by a listed verdict author to the author's next
  `Report:`; the last open turn runs to now. From the author's `Question:` to the next comment
  by a listed verdict author is not counted. One decimal, rounded half up; `unknown` when the
  take or the comments cannot be read.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import session
from metrics import usage_of

from config import caps_settings

UNKNOWN = "unknown"
PROGRESS_USAGE = re.compile(r"Progress: .*; Usage: (\d+) tokens")
READY = re.compile(r"Report: \S+ ready for review\b.*")
OPENS = re.compile(r"(?:Verdict: fix list\b|Correction:).*")


def size_of(body: object) -> str | None:
    """The size of the one valid `Size:` line of a brief body, else None."""
    lines = [x.rstrip() for x in str(body).splitlines()] if isinstance(body, str) else []
    found = [x for x in lines if session.SIZE.fullmatch(x)]
    sizes = [x for x in lines if x.startswith("Size")]
    return found[0][-1] if len(found) == 1 and len(sizes) == 1 else None


def cap_of(table: dict, body: object) -> tuple[str | None, dict]:
    """(size, cap); the size is None and the cap is L's when the size cannot be read."""
    size = size_of(body)
    return size, table[size or "L"]


def _order(c: dict) -> tuple[datetime, int]:
    return session.moment(c.get("created_at")), c.get("id") or 0


def tokens_used(comments: object, login: str) -> int | str:
    """Rule 5: the reports' sum plus a progress figure edited after the newest report."""
    summed = usage_of(comments, login)
    if not isinstance(comments, list) or summed == UNKNOWN:
        return UNKNOWN
    me = login.lower()
    mine = [c for c in comments if isinstance(c, dict) and session.author_of(c) == me]
    reports = [c for c in mine if session.first_line(c).startswith("Report:")]
    newest = max((session.moment(c.get("created_at")) for c in reports), default=None)
    figures = [int(summed)] if isinstance(summed, int) else []
    progress = [c for c in mine if session.first_line(c).startswith("Progress:")]
    if progress:
        line = max(progress, key=_order)
        found = PROGRESS_USAGE.fullmatch(session.first_line(line))
        edited = session.moment(line.get("updated_at") or line.get("created_at"))
        if found and (newest is None or edited > newest):
            figures.append(int(found.group(1)))
    return sum(figures) if figures else UNKNOWN


def _take_time(brief: list, login: str, opened: datetime) -> datetime | None:
    takes = [t for t in session.all_takes(brief) if t[3] == login and t[0] <= opened]
    return max(takes, key=lambda t: t[:2])[0] if takes else None


def hours_used(
    brief: object, pull: object, login: str, allowed: set[str], opened: str, now: datetime
) -> Decimal | str:
    """Rule 6: the hours of the builder's turns, to one decimal, or `unknown`."""
    if not isinstance(brief, list) or not isinstance(pull, list):
        return UNKNOWN
    me = login.lower()
    start = _take_time(brief, me, session.moment(opened))
    if start is None:
        return UNKNOWN
    later = [c for c in [*brief, *pull] if isinstance(c, dict) and _order(c)[0] > start]
    turn: datetime | None = start  # the open turn's start, or None while the builder waits
    seconds, ready, asked = 0.0, False, False
    for c in sorted(later, key=_order):
        first, who, moment = session.first_line(c), session.author_of(c), _order(c)[0]
        report = who == me and first.startswith("Report:") and (ready or READY.fullmatch(first))
        if asked:  # the conductor's time, until a listed verdict author answers
            if who in allowed:
                turn, asked = moment, False
            elif report:
                ready, asked = True, False
        elif turn is not None and who == me and first.startswith("Question:"):
            seconds, turn, asked = seconds + (moment - turn).total_seconds(), None, True
        elif turn is not None and report:
            seconds, turn, ready = seconds + (moment - turn).total_seconds(), None, True
        elif turn is None and ready and who in allowed and OPENS.fullmatch(first):
            turn = moment
    if turn is not None:
        seconds += (now - turn).total_seconds()
    return (Decimal(str(seconds)) / 3600).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def over_lines(root, repo: str, pulls: list, allowed: set[str], now: datetime) -> list[str]:
    """Rule 7: the OVER and UNKNOWN lines of the open builder pull requests, in number order."""
    table = caps_settings(root)
    if table is None:
        return []
    lines = []
    for pull in sorted(pulls, key=lambda p: p["number"]):
        brief = session.brief_number(pull)
        if brief is None:
            continue
        number, login = pull["number"], str((pull.get("user") or {}).get("login") or "")
        issue = session.gh(f"repos/{repo}/issues/{brief}")
        size, cap = cap_of(table, issue.get("body") if isinstance(issue, dict) else None)
        tail = "" if size else " size unknown"
        comments = session.pages(f"repos/{repo}/issues/{number}/comments")
        brief_comments = session.pages(f"repos/{repo}/issues/{brief}/comments")
        tokens = tokens_used(comments, login)
        hours = hours_used(
            brief_comments, comments, login, allowed, str(pull.get("created_at")), now
        )
        if tokens == UNKNOWN:
            lines.append(f"UNKNOWN #{brief} tokens #{number}{tail}")
        elif int(tokens) > cap["tokens"]:
            lines.append(f"OVER #{brief} {tokens}/{cap['tokens']} tokens #{number}{tail}")
        if hours != UNKNOWN and Decimal(hours) > cap["hours"]:
            lines.append(f"OVER #{brief} {hours}/{cap['hours']} hours #{number}{tail}")
    return lines
