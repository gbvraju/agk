# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The steward's measured quality: the daily list, the override share and its warning, and the
fresh re-check of a requirement answer (SPEC-0059 rules 3 and 13; brief #1323, ADR-0560).

Usage: python3 scripts/agk/steward_daily.py daily
       python3 scripts/agk/steward_daily.py bundle --question FILE

`daily` runs after `steward.py start`, from its cache of the memory issue. At the first start of a
UTC day it posts one comment `Daily: <date>` on the memory issue, covering each day since the last
list (Q-S0059-9: no scheduler; the days missed are listed): each steward `Answer:` with its comment
id and evidence, each pass's calls and tokens from its `Ended:` marker, each brief filed without an
`Owner said` line with its priority, the owner questions asked and answered, the override share and
any warning. It reads the repository's comments once with `since=` (seven days before the first day
listed) and the issues once; a figure it cannot read is `unknown`, never 0. Each new override (an
owner's `Maintainer answer:` that changes a steward answer, or a `Correction:` naming its Q id) is
posted first as one `Override: Q-<id> class <class>: ...` entry. Two overrides of one class within
seven days are a warning, lifted by a later `Decision:` that names `class <class>`. In personal mode
the list is printed and kept in the sidecar's memory file, and nothing is posted. `bundle` prints
what the fresh reviewer agent is given (ADR-0430's form): the question and the cited evidence only,
never the steward's answer.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import personal_table, repo_root, utf8_output  # noqa: E402

WHO = "Who: AGK steward"
MAX_DAYS = 14
WINDOW = timedelta(days=7)
DAILY = re.compile(r"^Daily: (\d{4}-\d{2}-\d{2})")
ANSWER = re.compile(r"^Answer: (Q-[\w-]+) (.*?)(?: \(evidence: (.*)\))?$")
CLASS = re.compile(r"^Class: (\S+)", re.M)
OWNER = re.compile(r"^(?:Maintainer answer: (Q-[\w-]+) (.*)|Correction:.*)$")
QID = re.compile(r"\bQ-[\w-]+\b")
ENDED = re.compile(r"^Ended: steward (\S+)(?: calls (.+?); tokens (.+))?$")
OVERRIDE = re.compile(r"^Override: (Q-[\w-]+) class (\S+):")
PRIORITY = re.compile(r"^Priority: ([0-3])\s*$", re.M)
OWNER_SAID = re.compile(r"^Owner said \(", re.M)
COMMENTS = "repos/{owner}/{repo}/issues/comments?per_page=100&since={since}&page={page}"
LISTED = "repos/{owner}/{repo}/issues?state=all&per_page=100&since={since}&page={page}"


def first(body: str) -> str:
    return (body or "").strip().splitlines()[0] if (body or "").strip() else ""


def day_of(item: dict) -> str:
    return str(item.get("created_at", ""))[:10]


def norm(text: str) -> str:
    return " ".join(str(text).casefold().strip().rstrip(".").split())


def days_to_list(memory: list[dict], today: date) -> list[date]:
    """The days since the last `Daily:` list, oldest first; none when today's is posted."""
    dated = [date.fromisoformat(m[1]) for c in memory if (m := DAILY.match(first(c["body"])))]
    last = max(dated, default=None)
    if last is not None and last >= today:
        return []
    start = max(last or today - timedelta(days=1), today - timedelta(days=MAX_DAYS))
    return [start + timedelta(days=n) for n in range((today - start).days)]


def steward_answers(comments: list[dict]) -> list[dict]:
    out = []
    for item in comments:
        found = ANSWER.match(first(item["body"]))
        if found and WHO in item["body"]:
            cls = CLASS.search(item["body"])
            number = str(item.get("issue_url", "")).rsplit("/", 1)[-1]
            out.append(
                {
                    "id": item["id"],
                    "qid": found[1],
                    "answer": found[2],
                    "evidence": found[3] or "not shown",
                    "cls": cls[1] if cls else "unknown",
                    "number": number,
                    "created_at": item["created_at"],
                }
            )
    return out


def overrides(comments: list[dict], answers: list[dict]) -> list[dict]:
    """Rule 13: an owner's answer that changes a steward answer, or a correction naming it."""
    out = []
    for item in comments:
        found = OWNER.match(first(item["body"]))
        if not found:
            continue
        qids = [found[1]] if found[1] else QID.findall(first(item["body"]))
        for ans in answers:
            if ans["qid"] in qids and ans["created_at"] < item["created_at"]:
                if found[1] and norm(found[2]) == norm(ans["answer"]):
                    continue
                out.append({"qid": ans["qid"], "cls": ans["cls"], "id": item["id"], "of": ans})
                out[-1]["created_at"] = item["created_at"]
                break
    return out


def warned(memory: list[dict], now: datetime) -> set[str]:
    """Rule 3: two overrides of one class within seven days, until a `Decision:` names the class."""
    since = (now - WINDOW).strftime("%Y-%m-%dT%H:%M:%SZ")
    times: dict[str, list[str]] = {}
    for item in memory:
        found = OVERRIDE.match(first(item["body"]))
        if found and item["created_at"] >= since:
            times.setdefault(found[2], []).append(item["created_at"])
    out = set()
    for cls, seen in times.items():
        if len(seen) < 2:
            continue
        second = sorted(seen)[1]
        lifted = any(
            first(c["body"]).startswith("Decision:")
            and f"class {cls}" in c["body"]
            and c["created_at"] > second
            for c in memory
        )
        if not lifted:
            out.add(cls)
    return out


def daily_text(
    today: date,
    days: list[date],
    comments: list[dict] | None,
    memory: list[dict],
    issues: list[dict] | None,
) -> str:
    """The `Daily:` comment; `comments` or `issues` None when they could not be read."""
    lines = [f"Daily: {today.isoformat()}"]
    if days and days[0] < today - timedelta(days=1):
        lines.append(f"Days listed: {', '.join(d.isoformat() for d in days)} (missed lists)")
    answers = steward_answers(comments) if comments is not None else None
    found = overrides(comments, answers) if comments is not None and answers is not None else None
    for day in (d.isoformat() for d in days):
        mine = [a for a in answers if day_of(a) == day] if answers is not None else None
        lines.append(f"Answers ({day}): {'unknown' if mine is None else len(mine)}")
        lines += [
            f"- {a['qid']} {a['answer']} (comment {a['id']} on #{a['number']}; evidence: "
            f"{a['evidence']})"
            for a in mine or []
        ]
        lines.append(f"Passes ({day}):")
        for item in memory:
            if day_of(item) == day and (m := ENDED.match(first(item["body"]))):
                lines.append(
                    f"- steward {m[1]}: calls {m[2] or 'not shown'}; tokens {m[3] or 'not shown'}"
                )
        cut = sum(
            1 for m in memory if day_of(m) == day and first(m["body"]).startswith("Shortened:")
        )
        lines.append(f"Replies shortened ({day}): {cut}")
        filed = None
        if issues is not None:
            filed = [
                i
                for i in issues
                if day_of(i) == day
                and WHO in (i.get("body") or "")
                and not OWNER_SAID.search(i.get("body") or "")
            ]
        lines.append(
            f"Filed without the owner's word ({day}): {'unknown' if filed is None else len(filed)}"
        )
        for i in filed or []:
            prio = PRIORITY.search(i.get("body") or "")
            lines.append(f"- #{i['number']} priority {prio[1] if prio else 'not shown'}")
        asked = sum(
            1 for m in memory if day_of(m) == day and first(m["body"]).startswith("Owner question:")
        )
        done = sum(
            1 for m in memory if day_of(m) == day and first(m["body"]).startswith("Decision:")
        )
        lines.append(f"Owner questions ({day}): asked {asked}; answered {done}")
        over = [o for o in found if day_of(o) == day] if found is not None else None
        share = "unknown" if over is None or mine is None else f"{len(over)}/{len(mine)}"
        lines.append(f"Override share ({day}): {share}")
    for cls in sorted(warned(memory, datetime.combine(today, datetime.min.time(), UTC))):
        lines.append(
            f"Warning: class {cls} overridden twice in seven days; it goes to the owner until a "
            "`Decision:` says otherwise"
        )
    lines.append("Reads: since= (the cached readers of #1251 and #1262 are not used)")
    return "\n".join(lines) + f"\n\n{WHO}\n"


def read_all(gh, template: str, since: str) -> list[dict] | None:
    out, page = [], 1
    while True:
        items = gh("GET", template.format(owner="{owner}", repo="{repo}", since=since, page=page))
        if items is None:
            return None
        out += list(items)
        if len(items) < 100:
            return out
        page += 1


def post_daily(cache: dict, gh, now: datetime) -> tuple[int, list[str]]:
    """Post the new `Override:` entries and today's `Daily:` on the memory issue of the cache."""
    from steward import Unreadable, post

    today = now.date()
    days = days_to_list(cache["comments"], today)
    if not days:
        return 0, [f"daily: already posted for {today.isoformat()}"]
    since = f"{(days[0] - WINDOW).isoformat()}T00:00:00Z"
    comments = read_all(gh, COMMENTS, since)
    issues = read_all(gh, LISTED, f"{days[0].isoformat()}T00:00:00Z")
    issues = None if issues is None else [i for i in issues if "pull_request" not in i]
    if comments is not None:
        recorded = {m[1] for c in cache["comments"] if (m := OVERRIDE.match(first(c["body"])))}
        for item in overrides(comments, steward_answers(comments)):
            if item["qid"] not in recorded:
                post(
                    gh,
                    cache,
                    f"Override: {item['qid']} class {item['cls']}: owner comment {item['id']} "
                    f"changed steward answer {item['of']['id']}",
                )
    text = daily_text(today, days, comments, cache["comments"], issues)
    try:
        post(gh, cache, text.removesuffix(f"\n\n{WHO}\n"))
    except Unreadable:
        return 4, ["error: comments cannot be written"]
    return 0, [text.splitlines()[0]]


def recheck_bundle(question: dict) -> str:
    """Rule 13, ADR-0430's form: the question and the cited evidence only."""
    from steward_evidence import SOURCES

    lines = [
        f"Question: {question['id']} {question.get('text', '')}".rstrip(),
        "Evidence (read each place; state your own answer in one line):",
    ]
    for item in question.get("findings", []):
        src = SOURCES[item["source"] - 1] if item.get("source") in range(1, 6) else "unknown"
        lines.append(f"- {src} {item.get('place', '')} (rule: {item.get('rule', '')})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(prog="steward_daily.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("daily")
    sub.add_parser("bundle").add_argument("--question", type=Path, required=True)
    opts = parser.parse_args(argv)
    root, now = repo_root(), datetime.now(UTC)
    if opts.command == "bundle":
        print(recheck_bundle(json.loads(opts.question.read_text(encoding="utf-8"))))
        return 0
    from steward import (
        Unreadable,
        gh_api,
        load_cache,
        memory_issue,
        personal_append,
        personal_entries,
        save_cache,
    )

    if personal_table(root) is not None:
        memory = personal_entries(root)
        days = days_to_list(memory, now.date())
        if not days:
            print(f"daily: already posted for {now.date().isoformat()}")
            return 0
        text = daily_text(now.date(), days, None, memory, None)
        personal_append(root, text.removesuffix(f"\n\n{WHO}\n"))
        print(text)
        return 0
    cache = load_cache(root)
    try:
        if "issue" not in cache:
            memory_issue(gh_api, root, cache)
        code, lines = post_daily(cache, gh_api, now)
    except Unreadable as exc:
        print(f"error: {exc} cannot be read", file=sys.stderr)
        return 4
    save_cache(root, cache)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
