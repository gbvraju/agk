# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The measures of each delivered feature for a date range (brief #1557, ADR-0659, amendment 191).

`measures.py --from YYYY-MM-DD --to YYYY-MM-DD [--json] [--repo OWNER/REPO] [--api-dir DIR]
[--sidecar DIR]` prints one row per feature (a brief whose finishing pull request merged in the
range), the range totals and one row for the merged pull requests tied to no brief. Read-only: GET
only through `metrics.Gh`, `metrics.ApiDir` or, in personal mode, `forge.FilesForge`; it writes no
file and posts nothing. The rows reuse `metrics.build_record`, `metrics.escape_of`,
`caps.hours_used` and `caps.tokens_used`; no field of SPEC-0007 is computed again. The output
holds numbers only: dates, brief and pull request numbers, counts, hours, minutes and tokens,
never a title, body text, login, branch, path, label or host. A figure whose input is missing
is `unknown`, never 0.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import caps
import metrics
import minutes
import session
from common import MERGED_BY, CheckError, agent_apps, execution, finished_brief, git, repo_root
from full_run import contained_in
from reviewers import solo_person, verdict_authors

NAME = "measures"
USAGE = (
    "usage: measures.py --from YYYY-MM-DD --to YYYY-MM-DD [--json] [--repo OWNER/REPO] "
    "[--api-dir DIR | --sidecar DIR]"
)
UNKNOWN = metrics.UNKNOWN
MAX_DAYS = 92  # Q-1557-2: a quarter fits; a longer range is run in parts
LOCAL, PERSONAL = "none (local mode)", "none (personal mode)"
OWNER_STARTS = ("Approve:", "Confirmed:", "Merge:", "Question:")
RELAYED = "Owner said ("
OWNER_QUESTION = re.compile(r"Question: \S+ for the maintainers\b.*")
ANSWERS = ("Answer:", "Maintainer answer:", "Correction:")
NOT_REPORTED = "not-reported"


# --- the command line -------------------------------------------------------------------------


def day_of(text: str | None, option: str) -> date:
    if text is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise CheckError(f"a date YYYY-MM-DD is needed (option: {option})")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise CheckError(f"the date does not exist (option: {option})") from None


def parse_args(args: list[str]) -> dict:
    options: dict[str, Any] = {"json": False}
    names = {"--from": "from", "--to": "to", "--repo": "repo", "--api-dir": "api"}
    names["--sidecar"] = "sidecar"
    i = 0
    while i < len(args):
        if args[i] == "--json":
            options["json"] = True
            i += 1
        elif args[i] in names and i + 1 < len(args) and names[args[i]] not in options:
            options[names[args[i]]] = args[i + 1]
            i += 2
        else:
            raise CheckError(USAGE)
    if "api" in options and "sidecar" in options:
        raise CheckError("one source only (option: --sidecar)")
    start, end = day_of(options.get("from"), "--from"), day_of(options.get("to"), "--to")
    if end < start:
        raise CheckError("the range ends before it starts (option: --to)")
    if (end - start).days + 1 > MAX_DAYS:
        raise CheckError(f"the range is longer than {MAX_DAYS} days (option: --to)")
    options["from"], options["to"] = start, end
    return options


# --- small readers ----------------------------------------------------------------------------


def listed(value: Any) -> list[dict] | None:
    return [c for c in value if isinstance(c, dict)] if isinstance(value, list) else None


def order(c: dict) -> tuple[str, int]:
    cid = c.get("id")
    return str(c.get("created_at") or ""), cid if isinstance(cid, int) else 0


def ended(p: dict) -> datetime | None:
    """A merged pull request ends at its merge (GitHub may close it a second later), else at
    its close."""
    return metrics.stamp(p.get("merged_at") or p.get("closed_at"))


def first(c: dict) -> str:
    return session.first_line(c)


def total(values: list[Any]) -> str:
    """The sum of whole figures; `unknown` when any is unknown; not-reported ones are counted."""
    if any(v == UNKNOWN or v is None for v in values):
        return UNKNOWN
    known = [int(v) for v in values if v != NOT_REPORTED]
    missing = len(values) - len(known)
    if values and not known:
        return NOT_REPORTED
    return f"{sum(known)} (+{missing} {NOT_REPORTED})" if missing else str(sum(known))


def hours_sum(values: list[Any]) -> str:
    if any(not isinstance(v, Decimal) and not str(v).replace(".", "", 1).isdigit() for v in values):
        return UNKNOWN
    return metrics.tenths(sum((Decimal(str(v)) for v in values), Decimal(0)))


def leading(value: str) -> str:
    """The whole figure that starts a CI field (`12 (governance 10, proof 2)` gives 12)."""
    head = str(value).split(" ", 1)[0]
    return head if head.isdigit() else UNKNOWN


class Reader:
    def __init__(self, src: Any, root: Path, config: Path, msrc: Any, personal: bool) -> None:
        self.src, self.root, self.msrc, self.personal = src, root, msrc, personal
        self.authors = verdict_authors(config)
        self.allowed = {a.lstrip("@").lower() for a in self.authors}
        self.apps = tuple(agent_apps(config))
        self.local = execution(config) == "local"
        self.auto = session.auto_merge_on(root)
        self.ctx = metrics.Context(src, root, [], self.authors, solo_person(config), self.apps)

    def get(self, name: str, endpoint: str) -> Any:
        return self.src.get(name, endpoint)

    def comments(self, n: int) -> list[dict] | None:
        return listed(self.get(f"comments-{n}", f"repos/{{repo}}/issues/{n}/comments"))

    def events(self, n: int) -> list[dict] | None:
        return listed(self.get(f"events-{n}", f"repos/{{repo}}/issues/{n}/events?per_page=100"))

    def message(self, sha: Any) -> str | None:
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{7,40}", sha):
            return None
        try:
            return git(self.root, "log", "-1", "--format=%B", sha)
        except CheckError:
            return None

    # --- one feature --------------------------------------------------------------------------

    def feature(self, brief: int, issue: dict, pulls: list[dict], finish: dict) -> dict:
        done = metrics.stamp(finish.get("merged_at"))
        assert done is not None  # noqa: S101 - a finish is chosen by its merge time
        mine = [p for p in pulls if (ended(p) or done) <= done]
        after = [p for p in pulls if p.get("merged_at") and p not in mine]
        brief_comments = self.comments(brief)
        threads = {p["number"]: self.comments(p["number"]) for p in mine}
        records = [metrics.build_record(self.ctx, p) for p in mine]
        row: dict[str, str] = {"pulls": " ".join(f"#{p['number']}" for p in mine)}
        row |= self.times(issue, brief_comments, mine, threads, finish)
        row |= self.rework(brief, brief_comments, mine, threads, records, after)
        row |= self.defects(mine)
        row |= self.spend(brief_comments, mine, threads, records)
        row |= self.owner(brief_comments, mine, threads, done)
        return row

    def times(self, issue, brief_comments, mine, threads, finish) -> dict[str, str]:
        merged = finish.get("merged_at")
        take = None
        for c in sorted(brief_comments or [], key=order):
            if isinstance(c.get("body"), str) and session.TAKE.fullmatch(session.plain(c["body"])):
                take = c.get("created_at")
                break
        hours: list[Any] = []
        for p in mine:
            login = metrics.author_of(p)
            now = metrics.stamp(p.get("closed_at"))
            if now is None:
                hours.append(UNKNOWN)
                continue
            hours.append(
                caps.hours_used(
                    brief_comments, threads[p["number"]], login, self.allowed,
                    str(p.get("created_at")), now,
                )
            )  # fmt: skip
        return {
            "lead_hours": metrics.hours_between(issue.get("created_at"), merged),
            "queue_hours": metrics.hours_between(issue.get("created_at"), take),
            "build_hours": metrics.hours_between(take, merged),
            "builder_hours": hours_sum(hours),
        }

    def rework(self, brief, brief_comments, mine, threads, records, after) -> dict[str, str]:
        unmerged = sum(not p.get("merged_at") for p in mine)
        rounds = total([r["review_rounds"] for r in records])
        rejected = total([r["rejected_verdicts"] for r in records] + [unmerged])
        every = [brief_comments, *threads.values()]
        corrections = UNKNOWN
        if all(t is not None for t in every):
            corrections = str(sum(
                metrics.author_of(c) in self.allowed and first(c).startswith("Correction:")
                for t in every for c in t or []
            ))  # fmt: skip
        events = [self.events(brief), *(self.events(p["number"]) for p in mine)]
        reopened = UNKNOWN
        if all(e is not None for e in events):
            reopened = str(sum(e.get("event") == "reopened" for es in events for e in es or []))
        passed = UNKNOWN
        if rounds != UNKNOWN and rejected != UNKNOWN:
            passed = "yes" if rounds == "0" and rejected == "0" else "no"
        return {
            "fix_rounds": rounds,
            "rejected": rejected,
            "corrections": corrections,
            "reopened": reopened,
            "follow_ups": str(len(after)),
            "first_review_pass": passed,
        }

    def defects(self, mine: list[dict]) -> dict[str, str]:
        if self.personal:
            return dict.fromkeys(("escapes", "red_pushes", "escapes_unknown"), PERSONAL)
        contains = contained_in(self.root)
        found = [metrics.escape_of(self.src, p, contains) for p in mine if p.get("merged_at")]
        return {
            "escapes": str(found.count("escape")),
            "red_pushes": str(found.count("red")),
            "escapes_unknown": str(found.count(UNKNOWN)),
        }

    def spend(self, brief_comments, mine, threads, records) -> dict[str, str]:
        tokens: list[Any] = []
        for p in mine:
            used = caps.tokens_used(threads[p["number"]], metrics.author_of(p))
            if used == UNKNOWN and threads[p["number"]] is not None:
                used = NOT_REPORTED
            tokens.append(used)
        for login in sorted({metrics.author_of(p) for p in mine}):
            used = caps.tokens_used(brief_comments, login)
            if isinstance(used, int):
                tokens.append(used)
        row = {"tokens": total(tokens), "cost": "not priced"}  # Q-1557-4: no tier is known
        for field in ("minutes", "pool_minutes", "reruns"):
            if self.personal or self.local:
                row[field] = PERSONAL if self.personal else LOCAL
            else:
                row[field] = total([leading(r[field]) for r in records])
        return row

    def owner(self, brief_comments, mine, threads, done: datetime) -> dict[str, str]:
        merged = [p for p in mine if p.get("merged_at")]
        messages = [self.message(p.get("merge_commit_sha")) for p in merged]
        hand: str = UNKNOWN
        guarded: str = UNKNOWN
        if all(m is not None for m in messages):
            guarded = str(sum(MERGED_BY in (m or "").splitlines() for m in messages))
            hand = str(len(messages) - int(guarded)) + ("" if self.auto else " (auto_merge off)")
        every = [brief_comments, *threads.values()]
        row = {"hand_merges": hand, "guarded_merges": guarded}
        if any(t is None for t in every):
            return row | dict.fromkeys(
                ("owner_lines", "owner_questions", "owner_wait_minutes"), UNKNOWN
            )
        builders = {metrics.author_of(p) for p in mine}
        lines: str
        if self.personal:
            lines = PERSONAL
        elif any(
            metrics.author_of(c) in builders and not self.agent(c) for t in every for c in t or []
        ):
            lines = "unknown (no app mark)"  # Q-1557-6: one account, nothing tells them apart
        else:
            lines = str(sum(
                (not self.agent(c) and first(c).startswith(OWNER_STARTS))
                + any(x.startswith(RELAYED) for x in str(c.get("body") or "").splitlines())
                for t in every for c in t or []
            ))  # fmt: skip
        asked, waited = 0, Decimal(0)
        for t in every:
            ordered = sorted(t or [], key=order)
            for i, c in enumerate(ordered):
                if not OWNER_QUESTION.fullmatch(first(c)):
                    continue
                asked += 1
                answer = next((a for a in ordered[i + 1 :] if first(a).startswith(ANSWERS)), None)
                start = metrics.stamp(c.get("created_at"))
                end = metrics.stamp(answer.get("created_at")) if answer else done
                if start is not None and end is not None:
                    waited += Decimal(str(max(0.0, (end - start).total_seconds()))) / 60
        row |= {"owner_lines": lines, "owner_questions": str(asked)}
        return row | {"owner_wait_minutes": metrics.figure(waited)}

    def agent(self, c: dict) -> bool:
        app = c.get("performed_via_github_app")
        slug = app.get("slug") if isinstance(app, dict) else None
        return isinstance(slug, str) and slug.lower() in self.apps

    # --- the range ----------------------------------------------------------------------------

    def measure(self, start: date, end: date) -> dict:
        lo, hi = metrics.start_of(start), metrics.start_of(end + timedelta(days=1))

        def older(chunk: list[dict]) -> bool:
            last = metrics.stamp(chunk[-1].get("updated_at") or chunk[-1].get("closed_at"))
            return last is not None and last < lo

        pulls = self.src.get(
            "pulls", "repos/{repo}/pulls?state=closed&sort=updated&direction=desc", older
        )
        if not isinstance(pulls, list):
            raise CheckError("cannot list pull requests (path class: the GitHub API)")
        details = []
        for p in sorted(pulls, key=lambda p: p.get("number") or 0):
            closed = metrics.stamp(p.get("closed_at"))
            if closed is None or closed < lo:
                continue
            detail = self.get(f"pull-{p['number']}", f"repos/{{repo}}/pulls/{p['number']}")
            if isinstance(detail, dict) and "number" in detail:
                details.append(detail)

        def merged_in(d: dict) -> bool:
            when = metrics.stamp(d.get("merged_at"))
            return when is not None and lo <= when < hi

        groups: dict[int, list[dict]] = {}
        untied = []
        for d in details:
            brief = session.brief_number(d)
            if brief is None:
                untied += [d] if merged_in(d) else []
            else:
                groups.setdefault(brief, []).append(d)
        features = []
        for brief in sorted(groups):
            issue = self.get(f"issue-{brief}", f"repos/{{repo}}/issues/{brief}")
            if not isinstance(issue, dict):
                continue
            group = groups[brief]
            merged = sorted((d for d in group if d.get("merged_at")), key=lambda d: d["merged_at"])
            named = [d for d in merged if finished_brief(d.get("body")) == brief]
            if named:
                finish = named[0]
            elif merged and issue.get("state") == "closed":
                finish = merged[-1]
            else:
                continue
            if merged_in(finish):
                features.append({"brief": f"#{brief}"} | self.feature(brief, issue, group, finish))
        return {
            "range": {"from": start.isoformat(), "to": end.isoformat()},
            "features": features,
            "totals": self.totals(features, lo, hi),
            "untied": self.untied(untied),
        }

    def totals(self, features: list[dict], lo: datetime, hi: datetime) -> dict[str, str]:
        leads = [Decimal(f["lead_hours"]) for f in features if f["lead_hours"] != UNKNOWN]
        out = {
            "features": str(len(features)),
            "lead_hours_median": metrics.tenths(Decimal(median(leads))) if leads else UNKNOWN,
        }
        for field in ("fix_rounds", "rejected", "corrections", "reopened", "follow_ups",
                      "escapes", "red_pushes", "tokens", "minutes", "hand_merges",
                      "owner_questions"):  # fmt: skip
            nones = {f[field] for f in features if f[field].startswith("none (")}
            values = [f[field].split(" ", 1)[0] for f in features]
            out[field] = nones.pop() if nones else total(values) if features else UNKNOWN
        passes = [f["first_review_pass"] for f in features]
        out["first_review_pass"] = (
            f"{passes.count('yes')}/{len(passes)}" if passes and UNKNOWN not in passes else UNKNOWN
        )
        found = "repos/{repo}/issues?labels=found-bug&state=all&per_page=100"
        bugs = listed(self.get("issues-found-bug", found))
        opened = [b for b in bugs or [] if lo <= (metrics.stamp(b.get("created_at")) or hi) < hi]
        out["found_bugs_opened"] = UNKNOWN if bugs is None else str(len(opened))
        out["found_bugs_closed"] = (
            UNKNOWN if bugs is None else str(sum(b.get("state") == "closed" for b in opened))
        )
        out["billed_minutes"] = self.billed(lo, hi)
        return out

    def billed(self, lo: datetime, hi: datetime) -> str:
        if self.personal:
            return PERSONAL
        if self.local:
            return LOCAL
        est = minutes.estimate(self.msrc, lo, hi)
        if est.minutes is None:
            return UNKNOWN
        return str(est.minutes) + ("" if est.complete else " (incomplete)")

    def untied(self, pulls: list[dict]) -> dict[str, str]:
        records = [metrics.build_record(self.ctx, p) for p in pulls]
        tokens = []
        for p in pulls:
            used = caps.tokens_used(self.comments(p["number"]), metrics.author_of(p))
            tokens.append(NOT_REPORTED if used == UNKNOWN else used)
        return {
            "pulls": " ".join(f"#{p['number']}" for p in pulls) or "none",
            "fix_rounds": total([r["review_rounds"] for r in records]) if pulls else "0",
            "tokens": total(tokens) if pulls else "0",
        }


def render(data: dict) -> str:
    def joined(row: dict) -> str:
        return "; ".join(f"{k} {v}" for k, v in row.items())

    span = data["range"]
    lines = [f"agk measures {span['from']} to {span['to']} (UTC days, both included)"]
    for f in data["features"]:
        rest = {k: v for k, v in f.items() if k != "brief"}
        lines.append(f"feature {f['brief']}: {joined(rest)}")
    lines.append(f"totals: {joined(data['totals'])}")
    lines.append(f"not tied to a brief: {joined(data['untied'])}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
    except CheckError as exc:
        print(f"{NAME}: {exc}", file=sys.stderr)
        return 2
    root = repo_root()
    personal = "sidecar" in options
    if personal:
        from forge import FilesForge

        config = Path(options["sidecar"])
        src: Any = FilesForge(config, clone=root)
        msrc: Any = None
    elif "api" in options:
        config, src = root, metrics.ApiDir(Path(options["api"]))
        msrc = minutes.ApiDir(Path(options["api"]))
    else:
        repo = options.get("repo") or metrics.origin_repo()
        config, src, msrc = root, metrics.Gh(repo), minutes.Gh(repo)
    try:
        data = Reader(src, root, config, msrc, personal).measure(options["from"], options["to"])
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}", file=sys.stderr)
        return 1
    if options["json"]:
        sys.stdout.write(json.dumps(data, indent=2) + "\n")
    else:
        sys.stdout.write(render(data))
    return 0


if __name__ == "__main__":
    metrics.utf8_output()
    sys.exit(main())
