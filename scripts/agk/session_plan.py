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
   Overlap is judged by files (brief #330, ADR-0189): entries that name files overlap on a file
   they both name; a folder entry (`dir/`, `dir/**`, or a folder of the repository without its
   slash) covers every file under it unless its brief names files under it, and then counts only
   for those; two folder entries overlap as before. Each wait names the file (or, for two
   folders, the narrower folder).
   A claim whose session has posted nothing for `claim_stale_hours` (24 by default) and has no
   open pull request is stale: it holds nothing and is listed as `stale claim by <session>, <age>`.
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
import re
import string
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import matches, read_list
from session import (
    RELEASED,
    Survey,
    all_takes,
    brief_number,
    flow_int,
    gh,
    glob_regex,
    literal,
    live_takes,
    moment,
    pages,
    plain,
    priority_of,
    pull_files,
    repo_name,
    shared_patterns,
    survey,
    touches_of,
)

BUILDS_LINE = re.compile(r"Builds: (.+)")
BUILD_ITEM = re.compile(r"\(([A-Za-z0-9._-]+)\)\s*(.*)")
INDEPENDENT = "independent:"
MERGED_ALL = "every build is merged; the conductor closes it"
RULE = 15
WINDOW_DAYS = 14
DEFAULTS = {
    "reviews_in_flight": 3,
    "merge_hours": 1,
    "stale_commits": 20,
    "claim_stale_hours": 24,
}


def label_names(pr: dict) -> set[str]:
    return {str(x.get("name")) for x in pr.get("labels") or [] if isinstance(x, dict)}


def unshared(globs: list[str], shared: list) -> list[str]:
    return [g for g in globs if not any(r.fullmatch(literal(g)) for r in shared)]


def is_folder(glob: str) -> bool:
    """A folder entry of `Touches:`: `dir/`, `dir/**` or `**`; any other entry names files."""
    return glob.endswith("/") or glob == "**" or glob.endswith("/**")


def has_wildcard(glob: str) -> bool:
    return literal(glob) != glob


def file_clash(x: str, y: str) -> str | None:
    """The file that two file entries both name, else None (brief #330 answer 1)."""
    if x == y:
        return x
    if not has_wildcard(x) and glob_regex(y).fullmatch(x):
        return x
    if not has_wildcard(y) and glob_regex(x).fullmatch(y):
        return y
    if has_wildcard(x) and has_wildcard(y):
        a, b = literal(x), literal(y)
        if a.startswith(b) or b.startswith(a):
            return max((x, y), key=lambda g: len(literal(g)))
    return None


def under(path: str, folder: str) -> bool:
    """A path or the fixed part of a glob that lies in a folder entry."""
    return glob_regex(folder).fullmatch(path) is not None or literal(path).startswith(
        literal(folder)
    )


def covering(entries: list[str]) -> list[str]:
    """The folder entries that cover every file under them: those under which the same brief
    names no file (the verdict on 1f1969e, item 1). A folder under which the brief names files
    counts only for those files."""
    files = [g for g in entries if not is_folder(g)]
    return [f for f in entries if is_folder(f) and not any(under(g, f) for g in files)]


def clash(a: list[str], b: list[str]) -> str | None:
    """What two `Touches:` lists both touch, else None (brief #330 answers 1 and 3).

    Two entries that name files overlap on the file they both name. A folder entry covers every
    file under it unless its brief names files under it, so it overlaps an entry of the other
    brief that names a file under it (that file is named). Two folder entries overlap when one is
    above or below the other, as before (the narrower is named)."""
    for x in a:
        for y in b:
            if not is_folder(x) and not is_folder(y) and (found := file_clash(x, y)):
                return found
    for folders, files in ((covering(a), b), (covering(b), a)):
        for f in folders:
            for y in files:
                if not is_folder(y) and under(y, f):
                    return y
    for x in a:
        for y in b:
            if is_folder(x) and is_folder(y):
                if literal(x).startswith(literal(y)) or literal(y).startswith(literal(x)):
                    return max((x, y), key=lambda g: len(literal(g)))
    return None


def file_conflict(item: dict, mine: list[str], shared: list) -> str | None:
    """Why a changed file of a running pull request blocks a brief, else None.

    A modified, renamed or removed file blocks when an entry of the brief that names files matches
    it, or a folder entry that covers it (`covering`; a renamed file also by its old name). A
    file the pull request only *adds* blocks only on an exact path: every build adds an ADR, a
    changelog fragment and tests, and a new file cannot conflict with a brief that does not name
    it."""
    names = [str(item.get("filename"))]
    if item.get("status") == "renamed" and item.get("previous_filename"):
        names.append(str(item["previous_filename"]))
    folders = covering(mine)
    for path in names:
        if any(r.fullmatch(path) for r in shared):
            continue
        if item.get("status") == "added":
            if path in mine:
                return f"it adds {path}"
        elif any(glob_regex(g).fullmatch(path) for g in mine if not is_folder(g)):
            return f"it changes {path}"
        elif any(glob_regex(f).fullmatch(path) for f in folders):
            return f"it changes {path}"
    return None


def entries_of(root, globs: list[str]) -> list[str]:
    """The `Touches:` entries with a folder of the repository written without its slash read as
    that folder (`docs/guides` is `docs/guides/`; the verdict on 1f1969e, item 2)."""
    out = []
    for g in globs:
        plain_path = not has_wildcard(g) and not g.endswith("/")
        out.append(g + "/" if plain_path and g and (Path(root) / g).is_dir() else g)
    return out


def running_conflict(root, s: Survey, brief: dict, shared: list) -> dict | None:
    """What running work the brief waits for: a taken brief or an open builder pull request."""
    mine = unshared(entries_of(root, touches_of(brief["body"])), shared)
    for number, theirs in s.held:
        if number == brief["number"]:
            continue  # another build of the same brief is not a rival
        if found := clash(mine, unshared(entries_of(root, theirs), shared)):
            return {"brief": brief["number"], "waits_for": number, "why": f"both touch {found}"}
    for pr in s.builders:
        if pr_brief(pr) == brief["number"]:
            continue
        for item in pull_files(s, pr):
            found = file_conflict(item, mine, shared)
            if found:
                return {"brief": brief["number"], "pull_request": pr["number"], "why": found}
    return None


def builds_of(body: str) -> list[tuple[str, bool]]:
    """(name, independent) of each build of a brief, from its line `Builds: (a) ...; (b) ...`.

    A build is independent when its text starts with `independent:`; every other build waits for
    the builds before it. A brief with no such line has no builds."""
    for line in str(body or "").splitlines():
        found = BUILDS_LINE.fullmatch(line.rstrip())
        if not found:
            continue
        items = [BUILD_ITEM.fullmatch(x.strip()) for x in found.group(1).split(";")]
        return [
            (m.group(1), m.group(2).strip().lower().startswith(INDEPENDENT)) for m in items if m
        ]
    return []


def names_build(pr: dict, number: int, name: str) -> bool:
    """A pull request whose title says `brief #<n> build (<x>)`, as every builder title does.

    The build a pull request delivers is read from its title only, never from free text: a body
    that says "build (b) is not in this pull request" must not mark build (b) done."""
    title = str(pr.get("title") or "")
    return (
        re.search(rf"brief #{number} build \({re.escape(name)}\)", title, re.IGNORECASE) is not None
    )


def moved_on(s: Survey, number: int, take: tuple) -> bool:
    """True when the session of a take has a later `taken:` on another brief: its work on this
    brief is finished and the hold has no purpose (the verdict on 39b7f9a)."""
    return any(
        t[2] == take[2] and t[0] > take[0]
        for other, comments in s.comments.items()
        if other != number
        for t in all_takes(comments)
    )


def names_any_build(pr: dict, number: int) -> bool:
    """A title that says `brief #<n> build <x>` or `build (<x>)` for some build."""
    title = str(pr.get("title") or "")
    return re.search(rf"brief #{number} build \(?[A-Za-z0-9._-]+\)?", title, re.I) is not None


def fits(pr: dict, number: int, take: tuple) -> bool:
    """A pull request that may be the work of a take: it has `Brief: #<n>`, and the take is of the
    whole brief, or its title names the take's build, with or without the brackets, or no build.
    A title that names another build is another session's work (brief #330 answer 2)."""
    if brief_number(pr) != number:
        return False
    build = take[6] if len(take) > 6 else take[5]
    if build is None or not names_any_build(pr, number):
        return True
    title = str(pr.get("title") or "")
    pattern = rf"brief #{number} build \(?{re.escape(build)}\)?(?![A-Za-z0-9._-])"
    return re.search(pattern, title, re.I) is not None


POST_LINE = re.compile(r"(?:Progress|Report|Request):")
CONDUCTOR_LABEL = "agk-conductor"


def names(text: str, name: str) -> bool:
    """The session name as a whole word: `builder-f` is not `builder-ff`."""
    return re.search(rf"(?<![A-Za-z0-9._-]){re.escape(name)}(?![A-Za-z0-9._-])", text) is not None


def own_posts(comments: list | None, name: str, named_only: bool) -> list[datetime]:
    """When the session posted a `Progress:`, `Report:` or `Request:` comment among these: one
    that names it, or on its own pull request any such comment (`named_only` false)."""
    out = []
    for c in comments or []:
        text = plain(c["body"]) if isinstance(c.get("body"), str) else ""
        first = text.splitlines()[0] if text else ""
        if POST_LINE.match(first) and (not named_only or names(text, name)):
            out.append(moment(c.get("created_at")))
    return out


def conductor_comments(repo: str) -> list | None:
    """The comments of the open issues labelled `agk-conductor` ([] with none, None unread)."""
    found = pages(f"repos/{repo}/issues?state=open&labels={CONDUCTOR_LABEL}")
    if found is None:
        return None
    out: list = []
    for i in found:
        labels = {str(x.get("name")) for x in i.get("labels") or [] if isinstance(x, dict)}
        if CONDUCTOR_LABEL not in labels or "pull_request" in i:
            continue
        comments = pages(f"repos/{repo}/issues/{i['number']}/comments")
        if comments is None:
            return None
        out += comments
    return out


def gone_sessions(s: Survey, hours: int, now: datetime) -> dict[str, int]:
    """The sessions whose claims are stale, with the whole hours since their last post.

    A claim is stale when its session has posted nothing for `claim_stale_hours` and has no open
    pull request (brief #330 answer 2). Its posts are its `taken:` and `released:` comments on the
    open briefs, the pull requests that may be its work (`fits`), opened or merged, and its
    `Progress:`, `Report:` and `Request:` comments (the verdict on 1f1969e, item 3): those that
    name it on the briefs and on the `agk-conductor` issue, and every such comment on a pull
    request that may be its work. Those are read only for a session that would otherwise be
    stale; a read that fails keeps the session fresh."""
    last: dict[str, datetime] = {}
    open_work: set[str] = set()
    mine: dict[str, set[int]] = {}

    def seen(name: str, when: datetime) -> None:
        last[name] = max(when, last.get(name, when))

    def old(name: str) -> bool:
        return name not in open_work and now - last[name] >= timedelta(hours=hours)

    for number, comments in s.comments.items():
        for t in all_takes(comments):
            seen(t[2], t[0])
            for pr in s.prs:
                if not fits(pr, number, t):
                    continue
                mine.setdefault(t[2], set()).add(pr["number"])
                if pr.get("state") == "open":
                    open_work.add(t[2])
                for key in ("created_at", "merged_at"):
                    if pr.get(key):
                        seen(t[2], moment(pr[key]))
        for c in comments or []:
            text = plain(c["body"]) if isinstance(c.get("body"), str) else ""
            if found := RELEASED.fullmatch(text):
                seen(found.group(1), moment(c.get("created_at")))
    for name in [n for n in last if old(n)]:
        for comments in s.comments.values():
            for when in own_posts(comments, name, True):
                seen(name, when)
    unread: set[str] = set()
    if any(old(n) for n in last):
        board = conductor_comments(s.repo)
        for name in [n for n in last if old(n)]:
            if board is None:
                unread.add(name)
                continue
            for when in own_posts(board, name, True):
                seen(name, when)
            for number in sorted(mine.get(name, ())):
                if number not in s.posts:
                    s.posts[number] = pages(f"repos/{s.repo}/issues/{number}/comments")
                if s.posts[number] is None:
                    unread.add(name)
                    break
                for when in own_posts(s.posts[number], name, False):
                    seen(name, when)
    out: dict[str, int] = {}
    for name, when in last.items():
        if old(name) and name not in unread:
            out[name] = int((now - when).total_seconds() // 3600)
    return out


def age_text(hours: int) -> str:
    if hours >= 48:
        return f"{hours // 24} days"
    return f"{hours} hour" + ("" if hours == 1 else "s")


def stale_claims(s: Survey) -> list[dict]:
    """Each live take of a session that is gone: `stale claim by <session>, <age>`."""
    out: list[dict] = []
    for number in sorted(s.comments):
        for t in live_takes(s.comments.get(number, []), number, s.prs, s.hours):
            if t[2] in s.gone:
                why = f"stale claim by {t[2]}, {age_text(s.gone[t[2]])}"
                entry = {"brief": number, "session": t[2], "hours": s.gone[t[2]], "why": why}
                out.append(entry | ({"build": t[5]} if t[5] else {}))
    return out


def effective_takes(s: Survey, number: int) -> list[tuple]:
    """The live takes of a brief that are not those of a session that moved on or is gone."""
    live = live_takes(s.comments.get(number, []), number, s.prs, s.hours)
    return [t for t in live if not moved_on(s, number, t) and t[2] not in s.gone]


def hold_text(s: Survey, number: int, take: tuple) -> str:
    """How long a take holds a brief: while a pull request of it is open, else until the hour at
    which `claim_hours` after its latest sign of work (the take, a merge of it) end."""
    if any(brief_number(p) == number and p.get("state") == "open" for p in s.prs):
        return "while its pull request is open"
    merges = [
        moment(p["merged_at"]) for p in s.prs if brief_number(p) == number and p.get("merged_at")
    ]
    end = max([take[0], *merges]) + timedelta(hours=s.hours)
    return f"until {end:%H:%M} UTC"


def next_build(s: Survey, brief: dict) -> tuple[str | None, list[dict], str | None]:
    """(the build to start or None, the waits, why nothing starts) for a brief built in parts.

    The first build that is not merged and has no live take and no open pull request is named;
    it waits for the nearest unmerged build before it unless it is marked independent."""
    number = brief["number"]
    builds = builds_of(brief["body"])
    takes = effective_takes(s, number)
    merged = {
        n for n, _ in builds if any(p.get("merged_at") and names_build(p, number, n) for p in s.prs)
    }
    if whole := next((t for t in takes if t[5] is None), None):
        pending = [n for n, _ in builds if n not in merged]
        if not pending:
            return None, [], None
        text = f"build ({pending[0]}) is held for {whole[2]} {hold_text(s, number, whole)}"
        wait = {"brief": number, "build": pending[0], "held_by": whole[2], "why": text}
        return None, [wait], None
    busy = {t[5] for t in takes} | {
        n
        for n, _ in builds
        if any(p.get("state") == "open" and names_build(p, number, n) for p in s.prs)
    }
    if all(n in merged for n, _ in builds):
        return None, [], MERGED_ALL
    for index, (name, independent) in enumerate(builds):
        if name in merged or name in busy:
            continue
        before = [n for n, _ in builds[:index] if n not in merged]
        if before and not independent:
            wait = {
                "brief": number,
                "build": name,
                "waits_for_build": before[-1],
                "why": f"build ({name}) waits for build ({before[-1]})",
            }
            return None, [wait], None
        return name, [], None
    return None, [], None


def unplaced(
    s: Survey,
    started: list[dict],
    left: list[dict],
    hold: bool,
    waits: list[dict],
    skipped: list[tuple[int, str]],
    build_skips: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    """A brief the plan does not start never disappears without a word (the verdict on 6ef8389).

    Briefs that could start but have no slot, or are held by the merge queue, are listed with that;
    any other open brief that is in neither the start list, the waits nor the skips is listed with
    the reason that nothing is left to start."""
    out: list[tuple[int, str]] = []
    why = "the merge queue is above your merge rate" if hold else "no free slot"
    seen = {b["number"] for b in started} | {w["brief"] for w in waits}
    seen |= {n for n, _ in [*skipped, *build_skips]}
    for brief in left:
        if brief["number"] not in seen:
            out.append((brief["number"], why))
            seen.add(brief["number"])
    for number in sorted(s.briefs):
        if number not in seen:
            out.append((number, "every build is taken or in progress"))
    return out


def settle_takes(s: Survey) -> tuple[set[int], list[tuple[int, str]]]:
    """(the briefs built in parts whose takes all belong to sessions that moved on, the skips).

    A skip `taken by X` says until when the take holds the brief and names the oldest take that
    still holds it. A brief built in parts that is freed is no longer a skip or running work; a
    brief without builds keeps its take unless every take of it is stale (brief #330 answer 2)."""
    freed: set[int] = set()
    skipped: list[tuple[int, str]] = []
    for number, why in s.skipped:
        if not why.startswith("taken by"):
            skipped.append((number, why))
            continue
        takes = live_takes(s.comments.get(number, []), number, s.prs, s.hours)
        takes = [t for t in takes if t[2] not in s.gone]
        brief = s.briefs.get(number)
        if brief and builds_of(brief["body"]):
            takes = [t for t in takes if not moved_on(s, number, t)]
        if not takes and brief:
            freed.add(number)
            continue
        if takes:
            why = f"taken by {takes[0][2]} {hold_text(s, number, takes[0])}"
        skipped.append((number, why))
    return freed, skipped


def candidates(
    s: Survey, freed: set[int] = frozenset()
) -> tuple[list[dict], list[dict], list[tuple[int, str]]]:
    """The briefs to plan, each with the build to start (or None); the waits and the skips."""
    found: list[dict] = []
    waits: list[dict] = []
    skips: list[tuple[int, str]] = []
    taken = {n for n, why in s.skipped if why.startswith("taken by")} | set(freed)
    for brief in sorted(
        [*s.free, *(s.briefs[n] for n in taken if n in s.briefs)],
        key=lambda b: (priority_of(b["body"]), b["number"]),
    ):
        if not builds_of(brief["body"]):
            if brief in s.free or brief["number"] in freed:
                found.append({**brief, "build": None})
            continue
        name, more, why = next_build(s, brief)
        waits += more
        if why and (brief in s.free or brief["number"] in freed):
            skips.append((brief["number"], why))
        if name:
            found.append({**brief, "build": name})
    return found, waits, skips


def waves(root, s: Survey, ready: list[dict]) -> tuple[list[dict], list[dict]]:
    """(the briefs that can start together, the briefs that wait and for what)."""
    shared = [glob_regex(p) for p in shared_patterns(root)]
    chosen: list[dict] = []
    waits: list[dict] = []
    for brief in ready:
        if found := running_conflict(root, s, brief, shared):
            waits.append(found)
            continue
        mine = unshared(entries_of(root, touches_of(brief["body"])), shared)
        for other in chosen:
            theirs = unshared(entries_of(root, touches_of(other["body"])), shared)
            if found := clash(mine, theirs):
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
    behind_limit = flow_int(root, "stale_commits", DEFAULTS["stale_commits"], RULE)
    gone_hours = flow_int(root, "claim_stale_hours", DEFAULTS["claim_stale_hours"], RULE)
    s = survey(root, repo, "")
    default = _default_branch(root)
    now = datetime.now(UTC)
    s.gone = gone_sessions(s, gone_hours, now)
    stale = stale_claims(s)
    freed, skipped = settle_takes(s)
    s.held = [h for h in s.held if h[0] not in freed]
    s.skipped = skipped
    ready, build_waits, build_skips = candidates(s, freed)
    chosen, waits = waves(root, s, ready)
    waits = build_waits + waits
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
    unplanned = unplaced(s, chosen[:count], chosen[count:], hold, waits, skipped, build_skips)
    behind: list[dict] = []
    unread: list[int] = []
    updating: list[dict] = []
    for pr in ready_prs:
        far = behind_by(repo, default, pr)
        if far is None:
            unread.append(pr["number"])
        elif far > behind_limit:
            behind.append({"pr": pr["number"], "behind_by": far})
        if far is None or far <= behind_limit:
            updating.append(pr)
    conflicts = sorted(
        p["number"] for p in s.prs if p.get("state") == "open" and "agk:conflict" in label_names(p)
    )
    return {
        "start": [
            {"session": names[i], "brief": b["number"], "title": b.get("title")}
            | ({"build": b["build"]} if b.get("build") else {})
            for i, b in enumerate(chosen[:count])
        ],
        "waits": waits,
        "skipped": [{"brief": n, "why": why} for n, why in [*s.skipped, *build_skips, *unplanned]],
        "stale_claims": stale,
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
        "stale_commits": behind_limit,
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
        takes = ", ".join(
            f"{s['session']} takes #{s['brief']}"
            + (f" build ({s['build']})" if "build" in s else "")
            for s in started
        )
        lines.append(f"Start {len(started)}: {takes}.")
    else:
        lines.append(f"Start 0: {reason(plan)}.")
    for w in plan["waits"]:
        if "held_by" in w:
            lines.append(f"#{w['brief']} {w['why']}.")
            continue
        if "waits_for_build" in w:
            lines.append(
                f"#{w['brief']} build ({w['build']}) waits for build ({w['waits_for_build']})."
            )
            continue
        target = f"#{w['waits_for']}" if "waits_for" in w else f"pull request #{w['pull_request']}"
        lines.append(f"#{w['brief']} waits for {target} ({w['why']}).")
    if plan["stale_claims"]:
        lines.append(
            "Stale: " + ", ".join(f"#{c['brief']} ({c['why']})" for c in plan["stale_claims"]) + "."
        )
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
