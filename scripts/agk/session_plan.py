"""`session.py plan`: which builder sessions to start, which briefs wait, what is safe to merge.

Brief 247 build (a); SPEC-0034 rule 15. It prints a plan in plain words, or with `--json` the
same plan as data, from what `session.py` already reads (the open briefs, the pull requests, their
files and labels, the comments with the takes) and one `compare` read for each ready pull request.
It posts nothing, runs no model and starts nothing: starting sessions is the adapter of build (b).

The plan, in the order it is decided:

1. **Ready briefs.** Open, not taken (a `taken:` comment counts even with no pull request yet),
   `Depends-on` merged and not stale (`session.py` already judged those).
2. **Waves.** A brief whose `Touches:` overlap running work (a taken brief, an open builder pull
   request's files) waits for it. Of two ready briefs that overlap, the one earlier by priority
   and then number starts; the other waits for it. Shared mechanical files never overlap.
3. **Capacity.** The sessions to start are the smallest of the ready, non-overlapping briefs,
   `max_builders` less the running builders (open builder pull requests and claims with no pull
   request yet) and `reviews_in_flight` less the pull requests waiting for a verdict.
4. **The merge queue.** The merge rate is the merged pull requests of the last 14 days divided by
   the active hours (hour-long buckets, counted back from now, that hold a merge). While the
   `agk:ready` pull requests exceed `merge_hours` times the rate, no session starts; a running
   session is never stopped. With no merge in the window the rate is unknown and the limit does
   not apply, and the plan says so.
5. **The safe merge set.** The `agk:ready` pull requests that share no changed file (shared
   mechanical files aside), ordered by the waiting briefs each unblocks, then priority, then age,
   with those that change a protected path marked.
6. **Drift.** A ready pull request more than `stale_commits` behind the default branch, and a
   pull request that conflicts, are listed for their builder to update.
"""

from __future__ import annotations

import json
import string
from datetime import UTC, datetime, timedelta

from common import matches, read_list
from session import (
    Survey,
    flow_int,
    gh,
    glob_regex,
    literal,
    live_takes,
    priority_of,
    pull_files,
    repo_name,
    shared_patterns,
    survey,
    touches_of,
)

RULE = 15
WINDOW_DAYS = 14
DEFAULTS = {"reviews_in_flight": 3, "merge_hours": 1, "stale_commits": 20}


def label_names(pr: dict) -> set[str]:
    return {str(x.get("name")) for x in pr.get("labels") or [] if isinstance(x, dict)}


def unshared(globs: list[str], shared: list) -> list[str]:
    return [g for g in globs if not any(r.fullmatch(literal(g)) for r in shared)]


def clash(a: list[str], b: list[str]) -> str | None:
    """The broader of the first two `Touches:` globs that overlap, else None."""
    for x in a:
        for y in b:
            if literal(x).startswith(literal(y)) or literal(y).startswith(literal(x)):
                return min((x, y), key=lambda g: len(literal(g)))
    return None


def running_conflict(root, s: Survey, brief: dict, shared: list) -> dict | None:
    """What running work the brief waits for: a taken brief or an open builder pull request."""
    mine = unshared(touches_of(brief["body"]), shared)
    for number, theirs in s.held:
        if found := clash(mine, unshared(theirs, shared)):
            return {"brief": brief["number"], "waits_for": number, "why": f"both touch {found}"}
    for pr in s.builders:
        for item in pull_files(s, pr):
            path = str(item.get("filename"))
            if any(r.fullmatch(path) for r in shared):
                continue
            if any(glob_regex(g).fullmatch(path) for g in mine):
                return {
                    "brief": brief["number"],
                    "pull_request": pr["number"],
                    "why": f"it changes {path}",
                }
    return None


def waves(root, s: Survey) -> tuple[list[dict], list[dict]]:
    """(the briefs that can start together, the briefs that wait and for what)."""
    shared = [glob_regex(p) for p in shared_patterns(root)]
    chosen: list[dict] = []
    waits: list[dict] = []
    for brief in s.free:
        if found := running_conflict(root, s, brief, shared):
            waits.append(found)
            continue
        mine = unshared(touches_of(brief["body"]), shared)
        for other in chosen:
            if found := clash(mine, unshared(touches_of(other["body"]), shared)):
                waits.append(
                    {
                        "brief": brief["number"],
                        "waits_for": other["number"],
                        "why": f"both touch {found}",
                    }
                )
                break
        else:
            chosen.append(brief)
    return chosen, waits


def merge_rate(prs: list, now: datetime) -> tuple[bool, float | None]:
    """(known, merges an active hour) over the last 14 days; an active hour holds a merge."""
    buckets: list[int] = []
    for pr in prs:
        when = str(pr.get("merged_at") or "")
        try:
            at = datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            continue
        if now - at <= timedelta(days=WINDOW_DAYS):
            buckets.append(int((now - at).total_seconds() // 3600))
    if not buckets:
        return False, None
    return True, round(len(buckets) / len(set(buckets)), 2)


def behind_by(repo: str, default: str, pr: dict) -> int | None:
    sha = str((pr.get("head") or {}).get("sha") or "")
    found = gh(f"repos/{repo}/compare/{default}...{sha}") if sha else None
    value = found.get("behind_by") if isinstance(found, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def session_names(busy: set[str], count: int) -> list[str]:
    names = [f"builder-{c}" for c in string.ascii_lowercase if f"builder-{c}" not in busy]
    return names[:count]


def merge_set(root, s: Survey, ready: list[dict], waits: list[dict], briefs: dict) -> dict:
    """The `agk:ready` pull requests that can be merged together, and the ones that go after."""
    shared = [glob_regex(p) for p in shared_patterns(root)]
    protected = []
    try:
        protected = read_list((root / "config" / "protected-paths.txt").read_text(encoding="utf-8"))
    except OSError:
        pass
    paths = {
        pr["number"]: {
            str(f.get("filename"))
            for f in pull_files(s, pr)
            if not any(r.fullmatch(str(f.get("filename"))) for r in shared)
        }
        for pr in ready
    }

    def order(pr: dict) -> tuple:
        unblocks = sum(1 for w in waits if w.get("pull_request") == pr["number"])
        brief = briefs.get(pr_brief(pr))
        return (-unblocks, priority_of(brief["body"]) if brief else 2, str(pr.get("created_at")))

    together: list[int] = []
    later: list[dict] = []
    for pr in sorted(ready, key=order):
        n = pr["number"]
        for other in together:
            if common := sorted(paths[n] & paths[other]):
                later.append({"pr": n, "after": other, "shares": common[0]})
                break
        else:
            together.append(n)
    changes = [n for n in together if any(matches(p, e) for p in paths[n] for e in protected)]
    return {"together": together, "later": later, "protected": changes}


def pr_brief(pr: dict) -> int | None:
    for line in str(pr.get("body") or "").splitlines():
        if line.startswith("Brief: #") and line[8:].rstrip().isdigit():
            return int(line[8:].rstrip())
    return None


def build(root) -> dict:
    repo = repo_name(root)
    reviews = flow_int(root, "reviews_in_flight", DEFAULTS["reviews_in_flight"], RULE)
    hours = flow_int(root, "merge_hours", DEFAULTS["merge_hours"], RULE)
    stale = flow_int(root, "stale_commits", DEFAULTS["stale_commits"], RULE)
    s = survey(root, repo, "")
    default = _default_branch(root)
    now = datetime.now(UTC)
    chosen, waits = waves(root, s)
    running = len(s.builders) + len(s.held)
    waiting_review = sum(1 for p in s.builders if "agk:review" in label_names(p))
    slots = max(0, min(s.max_builders - running, reviews - waiting_review))
    ready_prs = [p for p in s.prs if p.get("state") == "open" and "agk:ready" in label_names(p)]
    known, rate = merge_rate(s.prs, now)
    hold = known and rate is not None and len(ready_prs) > hours * rate
    briefs = {b["number"]: b for b in s.free}
    busy = {
        t[2]
        for number, comments in s.comments.items()
        for t in live_takes(comments, number, s.prs, s.hours)
    }
    count = 0 if hold else min(len(chosen), slots)
    names = session_names(busy, count)
    behind: list[dict] = []
    unread: list[int] = []
    updating: list[dict] = []
    for pr in ready_prs:
        far = behind_by(repo, default, pr)
        if far is None:
            unread.append(pr["number"])
        elif far > stale:
            behind.append({"pr": pr["number"], "behind_by": far})
        if far is None or far <= stale:
            updating.append(pr)
    conflicts = sorted(
        p["number"] for p in s.prs if p.get("state") == "open" and "agk:conflict" in label_names(p)
    )
    return {
        "start": [
            {"session": names[i], "brief": b["number"], "title": b.get("title")}
            for i, b in enumerate(chosen[:count])
        ],
        "waits": waits,
        "skipped": [{"brief": n, "why": why} for n, why in s.skipped],
        "capacity": {
            "max_builders": s.max_builders,
            "running": running,
            "reviews_in_flight": reviews,
            "waiting_for_verdict": waiting_review,
            "slots": slots,
            "ready": len(chosen),
        },
        "merge": {
            "waiting": len(ready_prs),
            "merge_hours": hours,
            "known": known,
            "rate": rate,
            "hold": hold,
        },
        "merge_set": merge_set(root, s, updating, waits, briefs),
        "behind": behind,
        "behind_unknown": unread,
        "conflicts": conflicts,
        "default_branch": default,
        "stale_commits": stale,
    }


def _default_branch(root) -> str:
    from common import load_config

    return str(load_config(root)["default_branch"])


def reason(plan: dict) -> str:
    cap, merge = plan["capacity"], plan["merge"]
    if not cap["ready"]:
        return "no brief is ready"
    if merge["hold"]:
        return (
            f"{merge['waiting']} pull requests wait for your merge, more than "
            f"{merge['merge_hours']} hour(s) of your merge rate ({merge['rate']:g} an hour)"
        )
    if cap["reviews_in_flight"] - cap["waiting_for_verdict"] <= 0:
        return (
            f"the conductor has {cap['waiting_for_verdict']} pull requests waiting for a verdict "
            f"(reviews_in_flight is {cap['reviews_in_flight']})"
        )
    return f"{cap['running']} builders already run (max_builders is {cap['max_builders']})"


def words(plan: dict) -> str:
    lines: list[str] = []
    started = plan["start"]
    if started:
        takes = ", ".join(f"{s['session']} takes #{s['brief']}" for s in started)
        lines.append(f"Start {len(started)}: {takes}.")
    else:
        lines.append(f"Start 0: {reason(plan)}.")
    for w in plan["waits"]:
        target = f"#{w['waits_for']}" if "waits_for" in w else f"pull request #{w['pull_request']}"
        lines.append(f"#{w['brief']} waits for {target} ({w['why']}).")
    if plan["skipped"]:
        lines.append(
            "Skipped: " + ", ".join(f"#{s['brief']} ({s['why']})" for s in plan["skipped"]) + "."
        )
    merge, picked = plan["merge"], plan["merge_set"]
    if merge["waiting"]:
        parts = []
        if picked["together"]:
            ids = ", ".join(f"#{n}" for n in picked["together"])
            note = "safe to merge together" if len(picked["together"]) > 1 else "safe to merge"
            marked = picked["protected"]
            if marked:
                what = "changes a protected path" if len(marked) == 1 else "change protected paths"
                note += "; " + ", ".join(f"#{n}" for n in marked) + f" {what}"
            parts.append(f"{ids} ({note})")
        parts += [
            f"#{x['pr']} after #{x['after']} (both change {x['shares']})" for x in picked["later"]
        ]
        noun = "pull request waits" if merge["waiting"] == 1 else "pull requests wait"
        lines.append(f"{merge['waiting']} {noun} for your merge: " + ", ".join(parts) + ".")
    for b in plan["behind"]:
        far, base = b["behind_by"], plan["default_branch"]
        lines.append(f"#{b['pr']} is {far} commits behind {base}: its builder updates it.")
    for n in plan["conflicts"]:
        lines.append(f"#{n} conflicts with {plan['default_branch']}: its builder updates it.")
    if merge["known"]:
        lines.append(
            f"Your merge rate over the last {WINDOW_DAYS} days is {merge['rate']:g} an hour."
        )
    else:
        lines.append(
            f"Your merge rate is unknown (no pull request merged in the last {WINDOW_DAYS} days): "
            "the merge queue limit does not apply."
        )
    return "\n".join(lines) + "\n"


def plan(root, as_json: bool) -> int:
    found = build(root)
    print(json.dumps(found, indent=2) if as_json else words(found), end="" if not as_json else "\n")
    return 0
