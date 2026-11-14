"""`session.py plan`: which builder sessions to start, which briefs wait, what is safe to merge.

Brief 247 build (a); SPEC-0034 rule 15. It prints a plan in plain words, or with `--json` the
same plan as data, from what `session.py` already reads (the open briefs, the pull requests, their
files and labels, the comments with the takes) and one `compare` read for each ready pull request.
It posts nothing, runs no model and starts nothing: starting sessions is the adapter of build (b).

The plan, in the order it is decided:

1. **Ready briefs.** Open, not taken (a `taken:` comment counts even with no pull request yet),
   `Depends-on` merged and not stale (`session.py` already judged those).
2. **Waves.** A brief whose `Blocked-by: #<n>` business question is not closed waits for it
   (`waits for question #<n>`, brief #1196, ADR-0508), in `next` and `claim` too. A brief whose
   `Touches:` overlap running work (a taken brief, an open builder pull
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
   request yet) and `reviews_in_flight` (by default `max_builders`, brief #842, ADR-0384) less
   the pull requests waiting for a verdict: not a draft, the author's newest `Report:` says
   `ready for review`, `fix list applied` or `merge of main`, and no `Verdict:` by a listed
   author names the head. When
   `builder_memory_gb` of the `[flow]` table is set (brief #409, ADR-0223), also the machine's
   available memory divided by it, rounded down, and never below 1 while no builder runs (with
   builders running it may be 0, the verdict on 43ada36); memory that cannot be read is
   `memory: unknown` and leaves the figure as it was. The plan names the limit that applied:
   `max_builders`, `reviews` or `memory` (the first of them on a tie).
   The `[capacity]` table (brief #842 build (b), ADR-0409) adds profiles: each ceiling is the
   smaller of the two tables; `full` measures nothing; `balanced` and `small` keep 25 and 50
   percent of memory, cores and disk free where each per-builder setting is set, and `small`
   starts at most 2; `fixed` uses `max_builders` only. `auto` (brief #842 build (c), ADR-0435)
   measures memory, cores and disk with no reserve where each per-builder setting is set, none of
   them with `builders_run = "cloud"`, and adapts: from the last count in the record of
   `plan --record` it drops by one on reviews over `review_minutes` or memory or disk under a
   quarter of the machine, and rises by one when checks (the newest governance run within 1.5
   times its usual minutes) and reviews (under `review_minutes`) hold, at least one of them read;
   slow checks or reviews at the limit hold it. It stays between 1 and the smallest figure.
   Every plan prints `Capacity: <n> of <ceiling> (<profile>; limit: <name> <figure>).`
4. **The merge queue.** The merge rate is the merged pull requests of the last 14 days divided by
   the active hours (hour-long buckets, counted back from now, that hold a merge). While the
   cleared pull requests (`READY_LABELS`) exceed `merge_hours` times the rate, no session
   starts; a running session is never stopped. With no merge in the window the rate is unknown
   and the limit does not apply, and the plan says so.
5. **The safe merge set.** The cleared pull requests that share no changed file (shared
   mechanical files aside), ordered by the waiting briefs each unblocks, then priority, then age,
   with those that change a protected path marked.
6. **Drift.** A ready pull request more than `stale_commits` behind the default branch, and a
   pull request that conflicts, are listed for their builder to update.
7. **The lanes** (SPEC-0038 rule 8; brief #665, ADR-0318). With a declared work type
   (`[delivery] work_type` of `agk.toml`, read through `playbook_format.selected`) the plan names
   each ready brief's lane, the lane whose `kinds` hold the brief's `Kind:` line, or `lane: none`
   for a brief without one or whose kind no lane holds, never an error; it orders the ready briefs
   within a priority by phase (a kind's depth in the split's `depends_on`), then one per lane in
   turn, so that parallel builders are offered briefs from different lanes first; and it prints the
   playbook's `heavy_steps` once, as the steps a builder runs under `lock.py run --name heavy`. The
   waves, the capacity, the merge queue and the safe merge set are decided as above, so a lane never
   lets two overlapping briefs run together; no lock setting changes. Without a declaration the plan
   prints exactly what it printed before.
8. **The milestone order** (brief #1232, ADR-0523). Each ready brief's milestone is the GitHub
   milestone of its issue, ordered by `due_on` (a milestone with none after those with one), then
   its number; a brief without one comes last. The ready briefs are ordered by milestone first, so
   the waves and the slots fill from the earliest milestone that has a ready, non-overlapping brief
   and reach a later one only when the earlier ones have none. Within a milestone: the brief whose
   dependants (every open brief whose `Depends-on: #n` names it, directly or further down, each
   counted once) carry the most hours first, then priority, then the smaller own hours, then
   number; a brief's hours are the mid point of its `Expected:` range, else its `Size:` (S 3
   hours, M 6 hours), else none (0 for a dependant, last for its own). With a playbook the lane
   order of item 7 applies inside each milestone, this order breaking its ties. `[plan]
   active_milestones` (a list of titles) leaves every brief outside them unstarted, listed as
   skipped; without it every milestone is active. The plan prints `#<n> <milestone>: unblocks <h>
   h.` for each start and `idle: no ready brief in <milestones>[; first wait: <wait>].` for each
   free slot it cannot fill (none while the merge queue holds the starts), and `milestones` in
   the data; with no milestone on any open brief and no `active_milestones`, neither (Q-1232-2),
   so such a plan prints what it printed before.

The re-prove state (SPEC-0050 rule 6, build (b), brief #727, ADR-0339): `reprove_files` names, from
local git only, the files a pull request's head changes since its merge base with the default
branch that the default branch also changed after that merge base (added, modified, removed, or
renamed from or to; no exemption), sorted, or None when git cannot read them; `behind_merges`
counts the first-parent commits of the default branch after the merge base. `merge_cleared.py`
holds on both (rule 8).

The overlap rule (SPEC-0050 rules 2 to 4, build (c), brief #751): `next`, `plan` and `claim` judge
overlap with `running_conflict` and `clash`, leaving out the paths that `exempt` lists: the
shared-mechanical files and the shared indexes of `[flow] shared_indexes` (exact paths, default
`SHARED_INDEXES`; a set list replaces it, a bad value is refused naming the setting). A shared
index never makes an overlap; it still counts for the re-prove above, which has no exemption.

The light re-prove (SPEC-0050 amendment 171, brief #1163, ADR-0495): `reprove_state` returns the
re-prove files and whether every one is a shared index; `reprove_kind` says `light` when they all
are and the merge is clean (`git merge-tree --write-tree`), else `full`, `conflict` or `none`; and
`light_merge` says whether a commit is that light merge of the default branch into a head and
adds nothing beyond the default branch's change, the test `merge_cleared.py` carries a verdict by.

The table of files (amendment 141 item 3, build (b)): `exempt` also holds `Prose`, the row of
`[flow] reprove_paths`. Prose never makes an overlap, and the later change re-proves. A folder or
wildcard entry is in a row only when every file it matches in the tree is, and one that matches
none is held (`in_a_row`). `merge_set` keeps counting shared prose, as it counts a shared index.

The holders (item 4): `holders` ranks the open builder pull requests by the briefs they hold; a
brief held by two counts under each. `plan` prints `Holds <k>:`, and `Stall:` for a holder of two
or more idle over `[flow] stall_minutes` (30 by default); it posts nothing, the conductor does.

With `builder_start = "assign"` (brief #776 build (c), ADR-0402) nothing starts: `start` is empty
and an `assign` list names the free slots, each row with its `Assign:` line; `launch.py` starts
nothing.

Plan before filing and every hold measured (amendment 141 items 6 and 7, brief #772 build (c)):
`--what-if DIR` judges saved briefs with `waves` and posts and records nothing; `--record` appends
each hold to `docs/runs/holds.jsonl`, kept out of git (`Q-772-1` as read); `metrics.py` reads it.

Exact `Touches:` (amendment 141 item 1, brief #772): `touch_problems` is the one function behind
`check_brief.py --root`, `next`, `plan` and the doctor's `brief-broad-touches`. A folder or wildcard
`Touches:` entry that matches more than `[flow] max_touch_glob` files that can hold a brief is
refused unless the brief has one `Broad:` line, and an `Adds:` entry may not name an existing file.
`reservation_refusals` refuses a `Reserved:` number held elsewhere (item 5).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import string
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import tomllib
from datetime import UTC, datetime, timedelta
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import common
import playbook_format
from common import ESTIMATE_LINES, CheckError, estimate_parts, matches, plan_settings, read_list
from metrics import HOLDS_FILE, author_of, counted_authors, hold_rows
from reviewers import verdict_authors
from session import (
    ADDS,
    ASSIGN,
    BROAD,
    HELD_PREFIX,
    LABEL,
    RED_TITLE,
    RELEASED,
    TOUCHES,
    Survey,
    Walk,
    all_takes,
    brief_number,
    brief_shape,
    builder_slots,
    builder_start,
    depends_on,
    first_line,
    flow_int,
    flow_value,
    gh,
    glob_regex,
    hold_state,
    is_red,
    last_request,
    line_entries,
    literal,
    live_takes,
    moment,
    pages,
    plain,
    priority_of,
    protected_entries,
    pull_files,
    repo_name,
    reservations,
    shared_patterns,
    survey,
    touches_of,
    verdict_line,
)
from session import kind_of as task_kind  # SPEC-0045 rule 4; kind_of below is the lane's

import config
import session as reads  # the one copy whose `gh` the plan's reads go through

BUILDS_LINE = re.compile(r"Builds: (.+)")
BUILD_ITEM = re.compile(r"\(([A-Za-z0-9._-]+)\)\s*(.*)")
KIND_LINE = re.compile(r"Kind: (.+)")  # SPEC-0038 rule 8, Q-S0038-8: one kind of `brief_order`
HEAVY_LOCK = "a builder runs each under lock.py run --name heavy"
INDEPENDENT = "independent:"
MERGED_ALL = "every build is merged; the conductor closes it"
RULE = 15
READY_LABELS = frozenset({"agk:merge-ready", "agk:owner-merge", "agk:ready"})  # ADR-0385
WAITING_REPORT = re.compile(r"Report: \S+ (?:ready for review|fix list applied|merge of main)\b")
GIB = 1024**3  # builder_memory_gb counts in GiB, the lower reading of a GB (Q-409-2)
WINDOW_DAYS = 14
DEFAULTS = {
    "merge_hours": 1,
    "stale_commits": 20,
    "claim_stale_hours": 24,
}
SHARED_INDEXES = (
    "kit/manifest.json",
    "agk.toml",
    "config/rule-budget.txt",
    "docs/requirements.md",
    "docs/build-state.md",
)
INDEXES_REFUSED = "setting: flow.shared_indexes must be a list of exact repository paths"
MAX_TOUCH_GLOB = 5  # the default of `[flow] max_touch_glob`
REPROVE_PATHS = ("**/*.md", "!docs/specs/**", "!docs/adr/**")
REPROVE_REFUSED = "setting: flow.reprove_paths must be a list of non-empty strings"
STALL_MINUTES = 30  # the default of `[flow] stall_minutes`, `Q-772-7`
STALL_HOLDS = 2  # a holder of fewer briefs is not reported as a stall
HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
ADDED_NUMBER = re.compile(r"docs/(adr|specs)/(\d{4})-[^/]+\.md")
ADDED_AMENDMENT = re.compile(r"docs/runs/proposed-spec-amendments-(\d+)\.md")


def shared_indexes(root) -> list[str]:
    """The shared indexes of SPEC-0050 rule 3: `[flow] shared_indexes`, else the default; a value
    that is not a list of non-empty exact paths (no wildcard, no folder) is refused by its name."""
    value = flow_value(root, "shared_indexes", list(SHARED_INDEXES), RULE)
    if not isinstance(value, list) or not all(
        isinstance(v, str) and v.strip() and not has_wildcard(v) and not v.endswith("/")
        for v in value
    ):
        raise CheckError(INDEXES_REFUSED)
    return list(value)


class Prose:
    """The row of `[flow] reprove_paths`, read as one more pattern of `exempt`."""

    def __init__(self, rules: list[str]) -> None:
        self.rules = rules

    def fullmatch(self, path: str) -> bool:
        return is_prose(path, self.rules)


def exempt(root) -> list:
    """The paths that never make an overlap (the table of SPEC-0050 rule 3): the shared-mechanical
    files, the shared indexes and the prose. The one list `next`, `plan`, `claim` and the sweep
    judge with."""
    found: list = [glob_regex(p) for p in shared_patterns(root)]
    found += [re.compile(re.escape(p)) for p in shared_indexes(root)]
    return [*found, Prose(reprove_paths(root))]


def label_names(pr: dict) -> set[str]:
    return {str(x.get("name")) for x in pr.get("labels") or [] if isinstance(x, dict)}


def reprove_paths(root) -> list[str]:
    """`[flow] reprove_paths` (amendment 141 item 3), else the default; refused by its name."""
    value = flow_value(root, "reprove_paths", list(REPROVE_PATHS), RULE)
    if not isinstance(value, list) or not all(
        isinstance(v, str) and v.strip() and v.strip() != "!" for v in value
    ):
        raise CheckError(REPROVE_REFUSED)
    return value


def is_prose(path: str, rules: list[str]) -> bool:
    """Whether PATH is prose under the list, read in order: a `!` entry takes matches away."""
    found = False
    for rule in rules:
        if glob_regex(rule.removeprefix("!")).fullmatch(path):
            found = not rule.startswith("!")
    return found


def tree_files(root) -> list[str]:
    """The files under ROOT: git's list in a repository, else every file (`.git` is never one)."""
    base = Path(root)
    if (base / ".git").exists():
        return [p for p in common.git(base, "ls-files", "-z").split("\0") if p]
    return sorted(
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(base).parts
    )


def touch_rules(root) -> dict:
    """What `touch_problems` reads once per run; a bad setting is refused by its name."""
    held_not = exempt(root)
    shared = [glob_regex(p) for p in shared_patterns(root)]
    files = tree_files(root)
    return {
        "root": root,
        "limit": flow_int(root, "max_touch_glob", MAX_TOUCH_GLOB, 4),
        "files": files,
        "holding": [f for f in files if not any(r.fullmatch(f) for r in held_not)],
        "unshared": [f for f in files if not any(r.fullmatch(f) for r in shared)],
    }


def broad_entries(body: str, rules: dict) -> list[str]:
    """The `Touches:` entries refused for matching too many files that can hold a brief; none
    for a brief with exactly one `Broad:` line, its own statement that it sweeps."""
    if sum(1 for x in body.splitlines() if BROAD.fullmatch(x.rstrip())) == 1:
        return []
    broad = []
    for entry in line_entries(body, TOUCHES):
        read = entries_of(rules["root"], [entry])[0]
        if is_folder(read) or has_wildcard(read):
            pattern = glob_regex(read)
            if sum(1 for f in rules["holding"] if pattern.fullmatch(f)) > rules["limit"]:
                broad.append(entry)
    return broad


def touch_problems(body: str, rules: dict) -> list[str]:
    """Amendment 141 item 1, naming the rule, the setting and the entry, never a count."""
    problems = [
        f"rule 4: Touches entry {e} matches more than flow.max_touch_glob files"
        for e in broad_entries(body, rules)
    ]
    for entry in line_entries(body, ADDS):
        pattern = glob_regex(entries_of(rules["root"], [entry])[0])
        if any(pattern.fullmatch(f) for f in rules["unshared"]):
            problems.append(f"rule 4: Adds entry {entry} names an existing file")
    return problems


def added_numbers(s: Survey, pr: dict) -> set[str]:
    """The numbers a pull request adds: a new ADR, spec or amendment file, a new requirement."""
    found: set[str] = set()
    for item in pull_files(s, pr):
        name = str(item.get("filename"))
        if name == "docs/requirements.md":
            patch = str(item.get("patch") or "")
            found.update(f"REQ-{n}" for n in re.findall(r"(?m)^\+### REQ-(\d{3})\b", patch))
        elif item.get("status") == "added":
            if m := ADDED_NUMBER.fullmatch(name):
                found.add(("ADR-" if m.group(1) == "adr" else "SPEC-") + m.group(2))
            elif m := ADDED_AMENDMENT.fullmatch(name):
                found.add(f"amendment {m.group(1)}")
    return found


def reservation_refusals(s: Survey) -> list[tuple[int, str]]:
    """Amendment 141 item 5: (brief, why) for each open brief whose `Reserved:` number an open pull
    request of another brief adds, or an earlier open brief reserves; a brief yields to a pull
    request, and of two briefs the later is refused. No pull request is read when none reserves."""
    reserved = {n: reservations(str(b.get("body") or "")) for n, b in sorted(s.briefs.items())}
    if not any(reserved.values()):
        return []
    opened = [p for p in s.prs if p.get("state") == "open"]
    adds = {p["number"]: added_numbers(s, p) for p in opened}
    refused: list[tuple[int, str]] = []
    for number, mine in reserved.items():
        for held in mine:
            prs = [
                p["number"] for p in opened if pr_brief(p) != number and held in adds[p["number"]]
            ]
            earlier = [m for m, theirs in reserved.items() if m < number and held in theirs]
            if holder := (prs or earlier)[:1]:
                why = f"rule 4 of SPEC-0050: Reserved {held} is also held by #{holder[0]}"
                refused.append((number, why))
    return refused


def in_a_row(root, entry: str, shared: list) -> bool:
    """Whether a `Touches:` entry never holds: a file by its row, a folder or wildcard as today or
    when every file it matches in the tree is in a row; one that matches none is held."""
    if not is_folder(entry) and not has_wildcard(entry):
        return any(r.fullmatch(entry) for r in shared)
    if any(isinstance(r, re.Pattern) and r.fullmatch(literal(entry)) for r in shared):
        return True
    pattern = glob_regex(entry)
    found = [f for f in tree_files(root) if pattern.fullmatch(f)]
    return bool(found) and all(any(r.fullmatch(f) for r in shared) for f in found)


def unshared(root, globs: list[str], shared: list) -> list[str]:
    return [g for g in globs if not in_a_row(root, g, shared)]


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


BLOCKED_BY = re.compile(r"Blocked-by: #([1-9]\d*)")  # brief #1196 (ADR-0508), from publish
QUESTION_OPEN, QUESTION_UNREAD = "it is open", "it cannot be read"


def question_wait(s: Survey, brief: dict) -> dict | None:
    """Brief #1196 answer 3: the first business question the brief's `Blocked-by: #<n>` lines name
    that is not closed, read once per survey with one GET; a failed read is never closed."""
    states: dict = s.__dict__.setdefault("question_states", {})
    for line in str(brief.get("body") or "").splitlines():
        if not (line_match := BLOCKED_BY.fullmatch(line.rstrip())):
            continue
        number = int(line_match[1])
        if number not in states:
            issue = gh(f"repos/{s.repo}/issues/{number}")
            states[number] = issue.get("state") if isinstance(issue, dict) else None
        if states[number] != "closed":
            why = QUESTION_UNREAD if states[number] is None else QUESTION_OPEN
            return {"brief": brief["number"], "question": number, "why": why}
    return None


def running_conflict(root, s: Survey, brief: dict, shared: list) -> dict | None:
    """What running work the brief waits for: an open business question it names (brief #1196),
    a taken brief or an open builder pull request."""
    if asked := question_wait(s, brief):
        return asked
    mine = unshared(root, entries_of(root, touches_of(brief["body"])), shared)
    for number, theirs in s.held:
        if number == brief["number"]:
            continue  # another build of the same brief is not a rival
        if found := clash(mine, unshared(root, entries_of(root, theirs), shared)):
            return {"brief": brief["number"], "waits_for": number, "why": f"both touch {found}"}
    for pr in s.builders:
        if pr_brief(pr) == brief["number"]:
            continue
        if found := pull_conflict(s, pr, mine, shared):
            return {"brief": brief["number"], "pull_request": pr["number"], "why": found}
    return None


def pull_conflict(s: Survey, pr: dict, mine: list[str], shared: list) -> str | None:
    """Why the changed files of one open pull request block these entries, else None."""
    for item in pull_files(s, pr):
        if found := file_conflict(item, mine, shared):
            return found
    return None


def holder_state(pr: dict) -> str:
    """The `agk:` label without its prefix, or `draft`, or `open`."""
    marks = sorted(n for n in label_names(pr) if n.startswith("agk:"))
    return marks[0].removeprefix("agk:") if marks else "draft" if pr.get("draft") else "open"


def holders(root, s: Survey, held: list[dict], now: datetime) -> list[dict]:
    """Amendment 141 item 4: the open builder pull requests that hold briefs, most briefs first,
    then the lowest number. A holder of `STALL_HOLDS` or more idle over the setting has `stall`."""
    limit = flow_int(root, "stall_minutes", STALL_MINUTES, 4)
    shared = exempt(root)
    rows: list[dict] = []
    for pr in s.builders:
        briefs = {
            b["number"]
            for b in held
            if b["number"] != pr_brief(pr)
            and pull_conflict(
                s, pr, unshared(root, entries_of(root, touches_of(b["body"])), shared), shared
            )
        }
        if not briefs:
            continue
        idle = max(0, int((now - moment(pr.get("updated_at"))).total_seconds() // 60))
        row = {
            "pr": pr["number"],
            "state": holder_state(pr),
            "idle": idle,
            "head": str((pr.get("head") or {}).get("sha") or ""),
            "briefs": sorted(briefs),
        }
        if len(briefs) >= STALL_HOLDS and idle > limit:
            row["stall"] = f"Stall: #{pr['number']} holds {len(briefs)}, idle {idle} min"
        rows.append(row)
    return sorted(rows, key=lambda r: (-len(r["briefs"]), r["pr"]))


# --- every hold measured (amendment 141 item 7, `Q-772-1` as read) --------------------------------


def hold_pairs(
    root, s: Survey, ready: list[dict], chosen: list[dict]
) -> list[tuple[int, int, str]]:
    """(brief, holder, file) for every held brief and each of its holders (`Q-772-6`): the first
    holder alone would hide a second. A holder is a brief or a pull request; GitHub numbers the two
    from one sequence, so the number says which."""
    shared = exempt(root)
    pairs: list[tuple[int, int, str]] = []
    earlier: list[dict] = []
    for brief in ready:
        if brief in chosen:
            earlier.append(brief)
            continue
        number = brief["number"]
        mine = unshared(root, entries_of(root, touches_of(brief["body"])), shared)
        rivals = [(n, theirs) for n, theirs in s.held if n != number]
        rivals += [(b["number"], touches_of(b["body"])) for b in earlier]
        for other, theirs in rivals:
            if found := clash(mine, unshared(root, entries_of(root, theirs), shared)):
                pairs.append((number, other, found))
        for pr in s.builders:
            if pr_brief(pr) != number and (why := pull_conflict(s, pr, mine, shared)):
                pairs.append((number, pr["number"], why.split(" ", 2)[2]))
    return pairs


def _hunks(root, start: str, end: str, path: str) -> list[tuple[int, int, int, int]] | None:
    """The hunks of `git diff -U0` of one file: (old start, old count, new start, new count)."""
    out = _git(root, "diff", "-U0", "--no-renames", start, end, "--", path)
    if out is None:
        return None
    found = (HUNK.match(x) for x in out.splitlines() if x.startswith("@@ "))
    return [(int(m[1]), int(m[2] or 1), int(m[3]), int(m[4] or 1)) for m in found if m is not None]


def _span(start: int, count: int) -> tuple[int, int]:
    """The lines of one side of a hunk; a side of no lines is the two lines around the place."""
    return (start, start + count - 1) if count else (start, start + 1)


def _back(line: int, between: list[tuple[int, int, int, int]]) -> tuple[int, int]:
    """Where a line after the hunks stood before them; inside a hunk, the whole of its old side."""
    moved = 0
    for old, old_n, new, new_n in between:
        if new_n and new <= line < new + new_n:
            return _span(old, old_n)
        if line < new or (not new_n and line <= new):
            break
        moved += new_n - old_n
    return line - moved, line - moved


def hold_mark(root, path: str, first: str, second: str) -> str:
    """Amendment 141 item 7: `false` when the two merged diffs of PATH change no common line, a
    file only one changed included; `true` otherwise; `unknown` when the lines cannot be mapped.
    FIRST merged before SECOND; each is one commit on the default branch."""
    if is_folder(path) or has_wildcard(path):
        return "unknown"
    before, after = f"{first}^1", f"{second}^1"
    if _git(root, "merge-base", "--is-ancestor", first, after) is None:
        return "unknown"
    span = f"{before}..{second}"
    moves = _git(root, "log", "-M", "--diff-filter=R", "--name-status", "--format=", span)
    if moves is None or any(path in x.split("\t")[1:] for x in moves.splitlines()):
        return "unknown"
    changed = (_changed(root, before, first), _changed(root, after, second))
    if changed[0] is None or changed[1] is None:
        return "unknown"
    if any(n.startswith(f"{path}/") for n in changed[0] | changed[1]):
        return "unknown"
    theirs, later, between = (
        _hunks(root, before, first, path),
        _hunks(root, after, second, path),
        _hunks(root, first, after, path),
    )
    if theirs is None or later is None or between is None:
        return "unknown"
    if path in changed[0] & changed[1] and not (theirs and later):
        return "unknown"  # a binary file has no lines
    spans = [_span(h[2], h[3]) for h in theirs]
    for old, count, _new, _new_n in later:
        low, high = _span(old, count)
        low, high = _back(low, between)[0], _back(high, between)[1]
        if any(a <= high and low <= b for a, b in spans):
            return "true"
    return "false"


def merged_pulls(s: Survey, number: int) -> list[dict]:
    """The merged pull requests of a holder or a brief, read by number or by its `Brief:` line."""
    return [
        p for p in s.prs if p.get("merged_at") and (p["number"] == number or pr_brief(p) == number)
    ]


def hold_marks(root, s: Survey, known: list[dict], at: str) -> list[dict]:
    """One more line for each hold whose two pieces of work have merged and that has no mark. A
    commit this clone has not fetched waits for a later pass: a stale clone is no measurement."""
    marked = {(r["brief"], r["holder"]) for r in known if "mark" in r}
    pairs: dict[tuple[int, int], str] = {}
    for row in known:
        pairs.setdefault((row["brief"], row["holder"]), row["file"])
    rows: list[dict] = []
    for (brief, holder), path in pairs.items():
        ours, theirs = merged_pulls(s, brief), merged_pulls(s, holder)
        if (brief, holder) in marked or not ours or not theirs:
            continue
        mark = "unknown"
        if len(ours) == 1 and len(theirs) == 1:
            first, second = sorted([*ours, *theirs], key=lambda p: (p["merged_at"], p["number"]))
            shas = [str(first.get("merge_commit_sha")), str(second.get("merge_commit_sha"))]
            if any(_git(root, "cat-file", "-e", f"{sha}^{{commit}}") is None for sha in shas):
                continue
            mark = hold_mark(root, path, shas[0], shas[1])
        rows.append({"at": at, "brief": brief, "holder": holder, "file": path, "mark": mark})
    return rows


def keep_out_of_git(root, name: str = HOLDS_FILE) -> None:
    """`Q-772-1` as read: the record is kept out of git in any project, by this clone's own exclude
    file, so no tracked ignore line is needed; a rewritten tracked file would be a generated one."""
    out = _git(root, "rev-parse", "--git-path", "info/exclude")
    if out is None:
        return
    path = Path(root) / out.strip()
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if name not in text.splitlines():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as lines:
            lines.write(f"{name}\n")


def record_holds(root, s: Survey, ready: list[dict], chosen: list[dict], now: datetime) -> None:
    """Append this pass to the record (`plan --record`); lines are only ever appended."""
    known = hold_rows(root)
    first: dict[tuple, datetime] = {}
    for row in known:
        first.setdefault((row["brief"], row["holder"]), moment(row["at"]))
    at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict] = [
        {
            "at": at,
            "brief": brief,
            "holder": holder,
            "file": path,
            "minutes": int((now - first.get((brief, holder), now)).total_seconds() // 60),
        }
        for brief, holder, path in hold_pairs(root, s, ready, chosen)
    ] + hold_marks(root, s, known, at)
    if not rows:
        return
    target = Path(root) / HOLDS_FILE
    try:
        keep_out_of_git(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as out:
            out.write("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    except OSError as exc:
        raise CheckError("rule 4 of SPEC-0050: the record of holds cannot be written") from exc


# --- plan before filing (amendment 141 item 6) -----------------------------------------------


def holder_name(wait: dict, names: dict[int, str]) -> str:
    """The saved file that holds a brief back, or the number of the open work."""
    if "question" in wait:
        return f"question #{wait['question']}"
    number = int(wait.get("waits_for", wait.get("pull_request", 0)))
    return names.get(number) or f"#{number}"


def what_if_lines(root, directory: str) -> list[str]:
    """How the saved briefs of DIR would split with the open work, by the plan's own `waves`.
    Capacity is read from nothing; nothing is posted or recorded. A saved brief has a number below
    zero, which no running work can have, so it is never mistaken for a build of its own brief."""
    folder = Path(directory)
    if not folder.is_dir():
        raise CheckError("rule 4 of SPEC-0050: --what-if needs a folder of saved briefs")
    repo = repo_name(root)
    s = survey(root, repo, "")
    read_gone(root, s, datetime.now(UTC))
    _, ready, _, _ = settled(s)
    shape = brief_shape(root, repo)
    found: list[tuple[int, str, str]] = []
    malformed: list[str] = []
    paths = sorted(p for p in folder.glob("*.md") if p.is_file())
    for path in paths:
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            malformed.append(f"MALFORMED: {path.name} rule 2: the file is not readable text")
            continue
        if problems := shape(body):
            malformed.append(f"MALFORMED: {path.name} {problems[0]}")
            continue
        found.append((priority_of(body), path.name, body))
    found.sort(key=lambda x: x[:2])
    names = {-i: f[1] for i, f in enumerate(found, 1)}
    saved = [{"number": -i, "title": f[1], "body": f[2]} for i, f in enumerate(found, 1)]
    chosen, waits = waves(root, s, [*lane_order(playbook_of(root), ready), *saved])
    held = [
        f"{names[w['brief']]} waits for {holder_name(w, names)} ({w['why']})"
        for w in waits
        if w["brief"] in names
    ]
    start = sum(1 for b in chosen if b["number"] in names)
    order = ", ".join(f[1] for f in found) or "none"
    return [
        f"What-if: {start} of {len(paths)} can start together.",
        *held,
        *malformed,
        f"File in this order: {order}",
    ]


def what_if(root, directory: str) -> int:
    print("\n".join(what_if_lines(root, directory)))
    return 0


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
    if s.recent and len(merged) < len(builds) and all_takes(s.comments.get(number) or []):
        older = history_of(s, number)  # ADR-0529 decision 4: a build merged before the window
        merged |= {
            n for n, _ in builds if any(p.get("merged_at") and names_build(p, number, n) for p in older)
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


def history_of(s: Survey, number: int) -> list[dict]:
    """The pull requests that name a brief, from its timeline (one read), each with its
    `merged_at`; when the timeline cannot be read, every closed pull request, read once."""
    events = pages(f"repos/{s.repo}/issues/{number}/timeline")
    if events is not None:
        out: list[dict] = []
        for event in events:
            source = event.get("source") if isinstance(event, dict) else None
            found = source.get("issue") if isinstance(source, dict) else None
            pull = found.get("pull_request") if isinstance(found, dict) else None
            if isinstance(pull, dict):
                out.append({**found, "merged_at": pull.get("merged_at")})
        return out
    if s.closed is None:
        s.closed = pages(f"repos/{s.repo}/pulls?state=closed") or []
    return s.closed


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
    for number in s.unread:  # ADR-0529: passed the listing, not read since no slot was left
        if number not in seen:
            out.append((number, why))
            seen.add(number)
    for number in sorted(s.briefs):
        if number not in seen:
            out.append((number, "every build is taken or in progress"))
    return out


def holding(s: Survey, number: int, takes: list[tuple]) -> list[tuple]:
    """The takes that hold a brief by the plan's reading: not those of a session that is gone,
    and for a brief built in parts not those of a session that moved on. `next` and `claim` read
    takes the same way (brief #345, ADR-0195)."""
    takes = [t for t in takes if t[2] not in s.gone]
    brief = s.briefs.get(number)
    if brief and builds_of(brief["body"]):
        takes = [t for t in takes if not moved_on(s, number, t)]
    return takes


def read_gone(root, s: Survey, now: datetime | None = None) -> None:
    """Set the sessions whose claims are stale, by `claim_stale_hours` (refused by its name)."""
    hours = flow_int(root, "claim_stale_hours", DEFAULTS["claim_stale_hours"], RULE)
    s.gone = gone_sessions(s, hours, now or datetime.now(UTC))


def wait_text(w: dict) -> str:
    """Why a brief waits, in the words of the plan and of the skips of `next` (brief #345)."""
    if "held_by" in w or "waits_for_build" in w or "fixed_by" in w:
        return str(w["why"])
    if "question" in w:  # brief #1196 answer 3
        why = "" if w["why"] == QUESTION_OPEN else f" ({w['why']})"
        return f"waits for question #{w['question']}{why}"
    target = f"#{w['waits_for']}" if "waits_for" in w else f"pull request #{w['pull_request']}"
    return f"waits for {target} ({w['why']})"


def filer_of(s: Survey, number: int) -> str:
    """The login of the person who filed a brief, the one who can fix it; empty when not given."""
    user = s.briefs.get(number, {}).get("user")
    return str(user.get("login") or "") if isinstance(user, dict) else ""


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
        takes = holding(s, number, live_takes(s.comments.get(number, []), number, s.prs, s.hours))
        brief = s.briefs.get(number)
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


# --- the lanes (SPEC-0038 rule 8; brief #665, ADR-0318) -------------------------------------------


def kind_of(body: str) -> str | None:
    """The brief's one `Kind:` line (Q-S0038-8), or None."""
    for line in str(body or "").splitlines():
        if found := KIND_LINE.fullmatch(line.rstrip()):
            return found.group(1).strip() or None
    return None


def _strs(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def playbook_of(root) -> dict | None:
    """The declared playbook's lanes, kinds and heavy steps, or None.

    `playbook_format.selected` reads the declaration (ADR-0312): with none, or with one that
    `doctor.py` and `check_playbooks.py` refuse, nothing is read and the plan is as before. Only the
    parts the plan uses are taken, each as far as its type is right; the format check is
    `check_playbooks.py`'s, not the plan's."""
    path = playbook_format.selected(root)
    if path is None:
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None
    tables = data.get("lanes")
    lanes = [
        (str(lane["name"]), _strs(lane.get("kinds")))
        for lane in (tables if isinstance(tables, list) else [])
        if isinstance(lane, dict) and isinstance(lane.get("name"), str)
    ]
    found = data.get("split")
    split: dict = found if isinstance(found, dict) else {}
    listed = split.get("depends_on")
    pairs = [
        (str(p[0]), str(p[1]))
        for p in (listed if isinstance(listed, list) else [])
        if isinstance(p, list) and len(p) == 2
    ]
    return {
        "work_type": str(data.get("work_type") or path.stem),
        "lanes": lanes,
        "ranks": phase_ranks(_strs(split.get("brief_order")), pairs),
        "heavy_steps": _strs(data.get("heavy_steps")),
    }


def phase_ranks(order: list[str], pairs: list[tuple[str, str]]) -> dict[str, int]:
    """A kind's phase rank: its depth in the split's `depends_on` (Q-665-1). A kind that depends
    on no kind is 0; each later kind is one deeper than the deepest kind it depends on. A cycle,
    which the format check refuses, is cut at the kind's place in `brief_order`."""
    earlier: dict[str, list[str]] = {k: [] for k in order}
    for later, before in pairs:
        if later in earlier and before in earlier:
            earlier[later].append(before)
    ranks: dict[str, int] = {}

    def depth(kind: str, seen: tuple[str, ...]) -> int:
        if kind in ranks:
            return ranks[kind]
        if kind in seen:
            return order.index(kind)
        found = max((depth(b, (*seen, kind)) + 1 for b in earlier[kind]), default=0)
        ranks[kind] = found
        return found

    for kind in order:
        depth(kind, ())
    return ranks


def lane_of(pb: dict, kind: str | None) -> str | None:
    """The first lane whose kinds hold the kind, else None (`lane: none`)."""
    if kind is None:
        return None
    return next((name for name, kinds in pb["lanes"] if kind in kinds), None)


def lane_order(pb: dict | None, ready: list[dict]) -> list[dict]:
    """The ready briefs in the lane order (ADR-0318 decision 3): priority, then phase rank, then one
    brief per lane in turn (the playbook's lane order, then none), then the order given (by number
    from `candidates`; the milestone order's within a milestone, ADR-0523). A brief without a
    kind, or with a kind the playbook does not know, belongs to no phase and follows the kinded
    briefs of its priority (Q-665-2). Without a playbook the order is as given."""
    if pb is None:
        return ready
    last = len(pb["ranks"])
    lanes = [name for name, _ in pb["lanes"]]

    def group(brief: dict) -> tuple[int, int]:
        kind = kind_of(brief["body"])
        return priority_of(brief["body"]), pb["ranks"].get(kind, last) if kind else last

    def lane_index(brief: dict) -> int:
        lane = lane_of(pb, kind_of(brief["body"]))
        return lanes.index(lane) if lane in lanes else len(lanes)

    out: list[dict] = []
    for key in sorted({group(b) for b in ready}):
        queues: dict[int, list[dict]] = {}
        for brief in (b for b in ready if group(b) == key):  # the order given (ADR-0523)
            queues.setdefault(lane_index(brief), []).append(brief)
        while any(queues.values()):
            for index in sorted(queues):
                if queues[index]:
                    out.append(queues[index].pop(0))
    return out


def lanes_of(pb: dict, ready: list[dict]) -> list[dict]:
    """One `{brief, kind, lane}` per ready brief, in the plan's order."""
    out = []
    for brief in ready:
        kind = kind_of(brief["body"])
        out.append({"brief": brief["number"], "kind": kind, "lane": lane_of(pb, kind)})
    return out


def playbook_lines(plan: dict) -> list[str]:
    """The two lines of a declared playbook: the lanes of the ready briefs and the heavy steps."""
    pb = plan.get("playbook")
    if not pb:
        return []
    kind = pb["work_type"]
    lanes = "; ".join(f"#{x['brief']} lane: {x['lane'] or 'none'}" for x in pb["lanes"])
    lanes = lanes or "no ready brief"
    steps = "; ".join(pb["heavy_steps"])
    heavy = f"{steps}; {HEAVY_LOCK}." if steps else "none."
    return [f"Lanes ({kind}): {lanes}.", f"Heavy steps ({kind}): {heavy}"]


# --- the milestone order (brief #1232, ADR-0523) ------------------------------------------------

SIZE_HOURS = {"S": 3.0, "M": 6.0}  # a brief with no `Expected:` line (answer 2)
NO_MILESTONE = "no milestone"
INACTIVE = "not in an active milestone (setting: [plan] active_milestones)"


def own_hours(body: object) -> float | None:
    """The mid point of the brief's `Expected:` range, else its size's hours, else None."""
    size, expected = estimate_parts(body)
    found = ESTIMATE_LINES["Expected"].fullmatch(expected)
    if found:
        return (float(found.group(1)) + float(found.group(2))) / 2
    return SIZE_HOURS.get(size)


def milestone_of(brief: dict) -> dict | None:
    found = brief.get("milestone")
    title = found.get("title") if isinstance(found, dict) else None
    return found if isinstance(title, str) and title else None


def milestone_title(brief: dict) -> str:
    found = milestone_of(brief)
    return found["title"] if found else NO_MILESTONE


def milestone_rank(brief: dict) -> tuple:
    """Earlier `due_on` first, a milestone without one after, then its number; none last."""
    found = milestone_of(brief)
    if found is None:
        return (2, "", 0)
    due = found.get("due_on")
    number = found.get("number")
    number = number if isinstance(number, int) and not isinstance(number, bool) else 0
    return (0, due, number) if isinstance(due, str) and due else (1, "", number)


def unblocked_hours(issues: list) -> dict[int, float]:
    """Each open brief's dependants' hours: every open brief that waits on it by `Depends-on`,
    directly or further down, counted once (a cycle ends), each by `own_hours` or 0."""
    briefs = {
        i["number"]: i
        for i in issues
        if isinstance(i, dict) and isinstance(i.get("number"), int) and "pull_request" not in i
    }
    waiters: dict[int, set[int]] = {}
    for number, brief in briefs.items():
        for named in depends_on(str(brief.get("body") or "")):
            if named in briefs and named != number:
                waiters.setdefault(named, set()).add(number)
    out: dict[int, float] = {}
    for number in briefs:
        seen: set[int] = set()
        stack = list(waiters.get(number, ()))
        while stack:
            other = stack.pop()
            if other in seen or other == number:
                continue
            seen.add(other)
            stack += waiters.get(other, ())
        out[number] = sum(own_hours(briefs[n].get("body")) or 0.0 for n in seen)
    return out


def active_milestones(root) -> list[str] | None:
    """`[plan] active_milestones`, or None when it is not set (every milestone is active)."""
    return plan_settings(Path(root)).get("active_milestones")


def milestone_order(pb: dict | None, ready: list[dict], hours: dict[int, float]) -> list[dict]:
    """The ready briefs by milestone, then (answer 2) the hours they unblock, priority, the
    smaller own hours and number; with a playbook, its lane order inside each milestone."""

    def key(brief: dict) -> tuple:
        own = own_hours(brief.get("body"))
        return (
            -hours.get(brief["number"], 0.0),
            priority_of(brief["body"]),
            own is None,
            own or 0.0,
            brief["number"],
        )

    out: list[dict] = []
    for rank in sorted({milestone_rank(b) for b in ready}):
        group = sorted((b for b in ready if milestone_rank(b) == rank), key=key)
        out += lane_order(pb, group)
    return out


def _whole(value: float) -> float | int:
    return int(value) if float(value).is_integer() else value


def idle_lines(issues: list, active: list[str] | None, waits: list[dict], skipped: list, n: int):
    """One `idle:` line for each of `n` free slots the plan cannot fill (answer 4)."""
    if n <= 0:
        return []
    briefs = [i for i in issues if isinstance(i, dict) and "pull_request" not in i]
    if active is not None:
        briefs = [b for b in briefs if milestone_title(b) in active]
    ranks = {b["number"]: milestone_rank(b) for b in briefs}
    titles: list[str] = []
    for brief in sorted(briefs, key=lambda b: (milestone_rank(b), b["number"])):
        if milestone_title(brief) not in titles:
            titles.append(milestone_title(brief))
    blocked = [(w["brief"], f"#{w['brief']} {wait_text(w)}") for w in waits if "brief" in w]
    blocked += [(b, f"#{b} {why}") for b, why in skipped if str(why).startswith("waits for")]
    blocked = [x for x in blocked if x[0] in ranks]
    line = "idle: no ready brief in " + (", ".join(titles) if titles else "any milestone")
    if blocked:
        first = min(range(len(blocked)), key=lambda i: (ranks[blocked[i][0]], i))
        line += f"; first wait: {blocked[first][1]}"
    return [line + "."] * n


def waves(root, s: Survey, ready: list[dict]) -> tuple[list[dict], list[dict]]:
    """(the briefs that can start together, the briefs that wait and for what)."""
    shared = exempt(root)
    chosen: list[dict] = []
    waits: list[dict] = []
    for brief in ready:
        if brief["number"] in s.fixes:  # brief #1052: a red branch's fix goes before the overlap
            chosen.append(brief)
            continue
        if found := running_conflict(root, s, brief, shared):
            waits.append(found)
            continue
        mine = unshared(root, entries_of(root, touches_of(brief["body"])), shared)
        for other in chosen:
            theirs = unshared(root, entries_of(root, touches_of(other["body"])), shared)
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


def merged_list(s: Survey) -> list:
    """The pull requests the merge rate counts: a red branch's survey reads none (brief #854
    answer 8), and a read that fails is never `unknown`, which says that none merged."""
    if s.prs:
        return s.prs
    found = pages(f"repos/{s.repo}/pulls?state=all")
    if found is None:
        raise CheckError("rule 1: the pull requests cannot be read")
    return found


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


def _git(root, *args: str) -> str | None:
    """The output of `git ARGS` in ROOT, or None when git fails."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8"
    )
    return proc.stdout if proc.returncode == 0 else None


def _merge_base(root, default: str, head: str) -> str | None:
    out = _git(root, "merge-base", default, head)
    return (out or "").strip() or None


def _changed(root, start: str, end: str) -> set[str] | None:
    out = _git(root, "diff", "--name-only", "--no-renames", "-z", f"{start}..{end}")
    return None if out is None else {name for name in out.split("\0") if name}


def reprove_files(root, default: str, head: str) -> list[str] | None:
    """The files that put HEAD in the re-prove state against DEFAULT (SPEC-0050 rule 6): changed
    by HEAD since its merge base with DEFAULT and by DEFAULT after it, sorted; `--no-renames`
    names a rename by both paths. None when any read fails, never a clean empty list."""
    base = _merge_base(root, default, head)
    mine = _changed(root, base, head) if base else None
    theirs = _changed(root, base, default) if base else None
    if mine is None or theirs is None:
        return None
    return sorted(mine & theirs)


def reprove_state(
    root, default: str, head: str, shared: list[str] | None = None
) -> tuple[list[str] | None, bool]:
    """(`reprove_files`, whether every one is a shared index of rule 3) (SPEC-0050 amendment 171,
    brief #1163); SHARED defaults to `shared_indexes(root)`. An empty or unreadable list is never
    all shared."""
    files = reprove_files(root, default, head)
    indexes = set(shared_indexes(root) if shared is None else shared)
    return files, bool(files) and all(name in indexes for name in files or [])


def clean_merge(root, first: str, second: str) -> str | None:
    """The tree of the merge of FIRST and SECOND (`git merge-tree --write-tree`), or None on a
    conflict or a read that fails."""
    out = _git(root, "merge-tree", "--write-tree", "--no-messages", first, second)
    tree = (out or "").strip()
    return tree if re.fullmatch(r"[0-9a-f]{40}", tree) else None


def reprove_kind(
    root, default: str, head: str, shared: list[str] | None = None
) -> tuple[str | None, list[str]]:
    """(`none`, `light`, `full` or `conflict`, the re-prove files) of HEAD against DEFAULT
    (amendment 171): `light` when every re-prove file is a shared index and the merge is clean;
    `conflict` when it is not; (None, []) when git cannot read it, never `light`."""
    files, all_shared = reprove_state(root, default, head, shared)
    if files is None:
        return None, []
    if not files:
        return "none", []
    if not all_shared:
        return "full", files
    return ("light" if clean_merge(root, head, default) else "conflict"), files


def light_merge(root, old: str, new: str, default: str, shared: list[str]) -> bool:
    """Whether NEW is the light re-prove's merge of the default branch into OLD (amendment 171):
    a commit with exactly the parents OLD and one commit of DEFAULT, OLD in the light state
    against that parent, and NEW's tree the clean merge of the two, so that it adds nothing beyond
    the default branch's change. Any read that fails is False."""
    out = _git(root, "rev-list", "--parents", "-n", "1", new)
    parents = (out or "").split()[1:]
    if len(parents) != 2 or parents[0] != old:
        return False
    theirs = parents[1]
    if _git(root, "merge-base", "--is-ancestor", theirs, default) is None:
        return False
    kind, _ = reprove_kind(root, theirs, old, shared)
    tree = clean_merge(root, old, theirs)
    own = (_git(root, "rev-parse", f"{new}^{{tree}}") or "").strip()
    return kind == "light" and tree is not None and tree == own


def behind_merges(root, default: str, head: str) -> int | None:
    """The first-parent commits of DEFAULT after its merge base with HEAD (SPEC-0050 rule 8), or
    None when git cannot read them."""
    base = _merge_base(root, default, head)
    if base is None:
        return None
    out = _git(root, "rev-list", "--count", "--first-parent", f"{base}..{default}")
    return int(out) if out is not None and out.strip().isdigit() else None


def session_names(busy: set[str], count: int) -> list[str]:
    names = [f"builder-{c}" for c in string.ascii_lowercase if f"builder-{c}" not in busy]
    return names[:count]


def merge_set(root, s: Survey, ready: list[dict], waits: list[dict], briefs: dict) -> dict:
    """The cleared pull requests (`READY_LABELS`) that merge together, and the ones after."""
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


def running_sessions(s: Survey) -> list[dict]:
    """The sessions that hold work (brief #402, ADR-0219): one entry per open builder pull request
    whose brief has a live take, then one per live take of a brief with no open pull request.
    The take of a pull request is the newest by its author, else the newest; a pull request whose
    brief has no live take names no session and is left out rather than guessed."""
    found: list[dict] = []
    seen: set[str] = set()

    def add(take: tuple, number: int, pr: dict | None) -> None:
        if take[2] in seen:
            return
        seen.add(take[2])
        entry: dict = {"session": take[2], "brief": number}
        if take[5]:
            entry["build"] = take[5]
        if pr is not None:
            entry["pull_request"] = pr["number"]
        login = pr_login(pr) if pr is not None else str(take[3] or "")
        if login:
            entry["author"] = login
        found.append(entry)

    for pr in sorted(s.builders, key=lambda p: p["number"]):
        number = pr_brief(pr)
        takes = live_takes(s.comments.get(number, []), number, s.prs, s.hours)
        if number is None or not takes:
            continue
        mine = [t for t in takes if str(t[3] or "").lower() == pr_login(pr).lower()]
        add((mine or takes)[-1], number, pr)
    for number, _ in s.held:
        for take in live_takes(s.comments.get(number, []), number, s.prs, s.hours):
            add(take, number, None)
    return found


def pr_login(pr: dict) -> str:
    user = pr.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    return login if isinstance(login, str) else ""


def waiting_for_verdict(s: Survey, pr: dict, authors: list[str] | None) -> bool:
    """Whether the conductor owes this pull request a verdict (brief #842, ADR-0384); one read of
    its comments, and comments that cannot be read keep the router's label as the answer."""
    if pr.get("draft"):
        return False
    comments = pages(f"repos/{s.repo}/issues/{pr['number']}/comments")
    if comments is None:
        return "agk:review" in label_names(pr)
    me = pr_login(pr).lstrip("@").lower()
    counted = counted_authors(authors, me)
    reports = [c for c in comments if author_of(c) == me and first_line(c).startswith("Report:")]
    if not reports or not WAITING_REPORT.match(first_line(max(reports, key=comment_id))):
        return False
    head = pr.get("head")
    sha = head.get("sha") if isinstance(head, dict) else None
    return verdict_line(comments, 0, sha if isinstance(sha, str) else "", counted) is None


def comment_id(comment: dict) -> int:
    number = comment.get("id")
    return number if isinstance(number, int) else 0


def settled(s: Survey) -> tuple[list, list[dict], list[dict], list]:
    """The takes settled and the refused briefs left out: (skipped, ready, build waits, skips)."""
    freed, skipped = settle_takes(s)
    s.held = [h for h in s.held if h[0] not in freed]
    s.skipped = skipped + reservation_refusals(s)
    refused = {n for n, why in s.skipped if why.startswith("rule ")}
    s.free = [b for b in s.free if b["number"] not in refused]
    freed -= refused
    ready, build_waits, build_skips = candidates(s, freed)
    return skipped, ready, build_waits, build_skips


# --- one red head gets one fix (brief #962, ADR-0414) ---------------------------------------------

FIX_LINE = re.compile(r"\s*(?:(?:fixes|closes)\b|red:|plan:)", re.IGNORECASE)
FIX_FILED = re.compile(r"fix brief filed:\s*#(\d+)", re.IGNORECASE)


def names_red(body: object, red: int) -> bool:
    """Whether a body names the alarm: `#<red>` in a `Fixes`, `Closes`, `Red:` or `Plan:` line, or
    a line holding `for issue #<red>`, the whole number only."""
    number = re.compile(rf"#{red}(?!\d)")
    phrase = re.compile(rf"\bfor issue #{red}(?!\d)", re.IGNORECASE)
    for line in str(body or "").splitlines():
        if (FIX_LINE.match(line) and number.search(line)) or phrase.search(line):
            return True
    return False


def open_pulls(s: Survey) -> list:
    """The open pull requests: the survey's, or one read while the branch is red (it reads none)."""
    if s.prs:
        return [p for p in s.prs if p.get("state") == "open"]
    found = pages(f"repos/{s.repo}/pulls?state=open")
    if found is None:
        raise CheckError("rule 1: the pull requests cannot be read")
    return [p for p in found if p.get("state") == "open"]


def fix_briefs_of(root, alarms: list, issues: list, comments: dict, pulls) -> dict[int, int]:
    """Each alarm's fix, `min` of what names it: an open brief or pull request that names it, or
    `#n` of a listed author's `fix brief filed: #n` on it with `#n` an open brief (brief #962
    answer 1). PULLS is the open pull requests, or a callable that reads them; it is called only
    when a brief or a listed author names a fix, so that a red survey that has none reads none."""
    briefs = {
        i["number"]: i
        for i in issues
        if "pull_request" not in i and i.get("title") != RED_TITLE and not is_red(i)
    }
    allowed = {a.lstrip("@").lower() for a in verdict_authors(root)}
    named: dict[int, set[int]] = {}
    for red in alarms:
        number = red["number"]
        found = {n for n, i in briefs.items() if names_red(i.get("body"), number)}
        for c in comments.get(number) or []:
            if author_of(c) in allowed:
                said = FIX_FILED.findall(str(c.get("body") or ""))
                found |= {int(m) for m in said} & set(briefs)
        named[number] = found
    if not any(named.values()) and callable(pulls):
        pulls = []  # no brief is named: a pull request alone fixes nothing the red survey keeps
    open_ = pulls() if callable(pulls) else pulls
    out: dict[int, int] = {}
    for number, found in named.items():
        found |= {int(p["number"]) for p in open_ if names_red(p.get("body"), number)}
        found.discard(number)
        if found:
            out[number] = min(found)
    return out


def fix_briefs(root, issues: list, comments: dict, pulls) -> dict[int, int]:
    """Brief #1052 answer 1, the one rule of `survey`, `plan` and `claim`: fix brief -> the open
    red alarm (`is_red`) whose fix by `red_fixes`' rule it is: an open brief, not a pull request."""
    alarms = [i for i in issues if is_red(i)]
    if not alarms:
        return {}
    briefs = {i["number"] for i in issues if "pull_request" not in i and not is_red(i)}
    found = fix_briefs_of(root, alarms, issues, comments, pulls)
    return {fix: red for red, fix in sorted(found.items()) if fix in briefs}


def red_fixes(root, s: Survey, issues: list, ready: list[dict]) -> list[dict]:
    """A wait `#<red> is fixed by #<n>` for each ready alarm titled `RED_TITLE` that an open fix
    brief or pull request names, or that a listed author's `fix brief filed: #n` on it names with
    `#n` an open brief (brief #962 answer 1); an alarm with no fix gets none (answer 2)."""
    alarms = [b for b in ready if b.get("title") == RED_TITLE]
    if not alarms:
        return []
    found = fix_briefs_of(root, alarms, issues, s.comments, open_pulls(s))
    return [
        {"brief": red, "fixed_by": fix, "why": f"is fixed by #{fix}"} for red, fix in found.items()
    ]


READS_FILE = "agk-plan-reads.json"  # in the checkout's git directory (ADR-0529 decision 5)


def walk_key(issues: list, active: list[str] | None, hours: dict[int, float]) -> Callable:
    """The order in which the plan reads the briefs (ADR-0529 decision 2): an active milestone
    first, then the milestone order and the within-milestone order of ADR-0523."""

    def key(brief: dict) -> tuple:
        own = own_hours(brief.get("body"))
        return (
            active is not None and milestone_title(brief) not in active,
            milestone_rank(brief),
            -hours.get(brief["number"], 0.0),
            priority_of(str(brief.get("body") or "")),
            own is None,
            own or 0.0,
            brief["number"],
        )

    return key


def build(root, record: bool = False) -> dict:
    """The plan, reading only what it needs (brief #1251, ADR-0529): the comments of the briefs
    in reading order until the free slots are filled, more only while a slot stays free and a
    brief is left unread; each GET is made once in the run. It carries `reads`."""
    began = time.monotonic()
    reads.MEMO = {}  # this run's reads only, never a previous run's
    first = reads.CALLS, reads.CACHED
    want = flow_int(root, "max_builders", reads.MAX_BUILDERS, RULE)
    try:
        while True:
            found, more = plan_pass(root, False, want)
            if not more:
                break
            want *= 2
        if record:
            found, _ = plan_pass(root, True, want)
    finally:
        reads.MEMO = None
    found["reads"] = {
        "calls": reads.CALLS - first[0],
        "cached": reads.CACHED - first[1],
        "seconds": round(time.monotonic() - began, 1),
    }
    save_reads(root, found["reads"])
    return found


def ahead(
    s: Survey, pb: dict | None, ready: list[dict], started: list[dict], active: list[str] | None
) -> bool:
    """Whether a brief left unread would come before a start in the plan's order, as a ready
    brief: then the plan reads further, so that it starts what a full read starts."""
    if not started:
        return False
    unblocks = unblocked_hours(list(s.briefs.values()))
    unread = [s.briefs[n] for n in s.unread if n in s.briefs]
    unread = [b for b in unread if active is None or milestone_title(b) in active]
    order = [b["number"] for b in milestone_order(pb, [*ready, *unread], unblocks)]
    last = max(order.index(b["number"]) for b in started if b["number"] in order)
    return any(n in s.unread for n in order[:last])


def with_unread(
    s: Survey, pb: dict | None, ready: list[dict], active: list[str] | None, hours: dict
) -> list[dict]:
    """The ready briefs and, in the plan's order, those the walk left unread (ADR-0529)."""
    unread = [s.briefs[n] for n in s.unread if n in s.briefs]
    unread = [b for b in unread if active is None or milestone_title(b) in active]
    return milestone_order(pb, [*ready, *unread], hours) if unread else ready


def save_reads(root, figures: dict) -> None:
    """The last plan's reads, for `checklist.py`; a file that cannot be written is left."""
    common_dir = _git(root, "rev-parse", "--git-common-dir")
    if not common_dir:
        return
    try:
        target = Path(root) / common_dir.strip() / READS_FILE
        target.write_text(json.dumps(figures, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        return


def reads_line(figures: dict) -> str:
    return (
        f"reads: {figures['calls']} calls ({figures['cached']} from cache), "
        f"{figures['seconds']} s"
    )


def plan_pass(root, record: bool, want: int) -> tuple[dict, bool]:
    """One plan from at most `want` free briefs read; and whether reading more could start more."""
    repo = repo_name(root)
    hours = flow_int(root, "merge_hours", DEFAULTS["merge_hours"], RULE)
    behind_limit = flow_int(root, "stale_commits", DEFAULTS["stale_commits"], RULE)
    issues = pages(f"repos/{repo}/issues?state=open&labels={LABEL}")
    if issues is None:
        raise CheckError("rule 3: the open briefs cannot be read")
    window = max(WINDOW_DAYS * 24, flow_int(root, "claim_hours", reads.CLAIM_HOURS, RULE))
    key = walk_key(issues, active_milestones(root), unblocked_hours(issues))
    s = survey(root, repo, "", issues, Walk(key, want, window))
    default = _default_branch(root)
    now = datetime.now(UTC)
    read_gone(root, s, now)
    stale = stale_claims(s)
    skipped, ready, build_waits, build_skips = settled(s)
    fixed = red_fixes(root, s, issues, ready)
    ready = [b for b in ready if b["number"] not in {w["brief"] for w in fixed}]
    build_waits = fixed + build_waits
    pb = playbook_of(root)
    active = active_milestones(root)
    inactive = [] if active is None else [b for b in ready if milestone_title(b) not in active]
    ready = [b for b in ready if b not in inactive]
    unblocks = unblocked_hours(issues)
    ready = milestone_order(pb, ready, unblocks)
    chosen, waits = waves(root, s, ready)
    ranked = holders(root, s, [b for b in ready if b not in chosen], now)
    if record:
        record_holds(root, s, ready, chosen, now)
    waits = build_waits + waits
    running = len(s.builders) + len(s.held)
    authors = verdict_authors(root)
    waiting_review = sum(1 for p in s.builders if waiting_for_verdict(s, p, authors))
    ceil = ceilings(root, s.max_builders)
    reviews, profile = ceil["reviews_in_flight"], ceil["profile"]
    if profile == "small" and SMALL_MOST < ceil["max_builders"]:
        limits = [("small", SMALL_MOST - running)]
    else:
        limits = [("max_builders", ceil["max_builders"] - running)]
    limits.append(("reviews", reviews - waiting_review))
    memory = measured_capacity(root, ceil, running)
    limits += [(n, memory[n]["builders"]) for n, _ in MEASURES if isinstance(memory.get(n), dict)]
    adapted = adapt(root, s, ceil, memory, running, authors, record) if profile == "auto" else {}
    if adapted.get("history"):
        limits.append(("adapt", adapted["count"] - running))
    limit, lowest = min(limits, key=lambda x: x[1])  # min keeps the first of a tie
    slots = max(0, lowest)
    if s.fixes and chosen:  # brief #1052 answer 2: a red branch's fix goes before the capacity
        slots = max(1, slots)
    ready_prs = [p for p in s.prs if p.get("state") == "open" and label_names(p) & READY_LABELS]
    known, rate = merge_rate(merged_list(s), now)
    hold = known and rate is not None and len(ready_prs) > hours * rate
    briefs = {b["number"]: b for b in s.free}
    busy = {
        t[2]
        for number, comments in s.comments.items()
        for t in live_takes(comments, number, s.prs, s.hours)
    }
    assigning = builder_start(root) == "assign"
    free = []
    if assigning:
        pending = pending_assigns(s, authors, {i["number"] for i in issues})
        held_slots = busy | set(pending or {})
        free = [] if pending is None else [f"s{n + 1}" for n in range(builder_slots(root))]
        free = [name for name in free if name not in held_slots]
        sent = set((pending or {}).values())
        chosen = [b for b in chosen if (b["number"], b.get("build") or None) not in sent]
    count = 0 if hold else min(len(chosen), slots)
    if assigning:
        count = min(count, len(free))
    names = free[:count] if assigning else session_names(busy, count)
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
    protected = protected_entries(Path(root))
    conflicts = sorted(
        p["number"] for p in s.prs if p.get("state") == "open" and "agk:conflict" in label_names(p)
    )
    playbook = (
        {
            "playbook": {
                "work_type": pb["work_type"],
                "lanes": lanes_of(pb, with_unread(s, pb, ready, active, unblocks)),
                "heavy_steps": pb["heavy_steps"],
            }
        }
        if pb
        else {}
    )
    malformed_rows = [row for row in s.skipped if row[1].startswith("rule ")]
    held, ignored_holds = holds_of(root, s)
    held_rows = [row for row in s.skipped if row[1].startswith(HELD_PREFIX)]
    entries = [start_entry(names[i], b, protected) for i, b in enumerate(chosen[:count])]
    fillable = 0 if hold else (min(slots, len(free)) if assigning else slots)
    milestones = {
        "active": active,
        "starts": [
            {
                "brief": b["number"],
                "milestone": milestone_title(b),
                "unblocks": _whole(unblocks.get(b["number"], 0.0)),
            }
            for b in chosen[:count]
        ],
        "idle": idle_lines(issues, active, waits, s.skipped, fillable - count),
    }
    found = {
        "start": [] if assigning else entries,
        "running": running_sessions(s),
        "waits": waits,
        "holders": ranked,
        "skipped": [
            {"brief": n, "why": why}
            for n, why in [
                *s.skipped,
                *build_skips,
                *unplanned,
                *((b["number"], INACTIVE) for b in inactive),
            ]
            if (n, why) not in malformed_rows and (n, why) not in held_rows
        ],
        "malformed": [
            {"brief": n, "why": why, "filer": filer_of(s, n)} for n, why in malformed_rows
        ],
        "stale_claims": stale,
        "capacity": {
            "max_builders": ceil["max_builders"],
            "profile": profile,
            "ceiling": min(ceil["max_builders"], SMALL_MOST)
            if profile == "small"
            else ceil["max_builders"],
            "running": running,
            "reviews_in_flight": reviews,
            "waiting_for_verdict": waiting_review,
            "slots": slots,
            "ready": len(chosen),
            "limit": limit,
        }
        | memory
        | ({"adapt": adapted} if adapted else {})
        | ({"free_slots": len(free)} if assigning else {}),
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
    } | playbook
    if active is not None or any(milestone_of(i) for i in issues if isinstance(i, dict)):
        found["milestones"] = milestones  # Q-1232-2: with no milestone the plan is as before
    if assigning:
        found["assign"] = [e | {"line": assign_line_of(e)} for e in entries]
    if held:
        found["held"] = held
    if ignored_holds:
        found["ignored_holds"] = ignored_holds
    return found, bool(s.unread) and (count < fillable or ahead(s, pb, ready, chosen[:count], active))


def holds_of(root, s: Survey) -> tuple[list[dict], list[dict]]:
    """Amendment 142: (every held brief with its reason, each `Hold:` by someone not listed)."""
    held: list[dict] = []
    ignored: list[dict] = []
    for number, comments in sorted(s.comments.items()):
        reason, logins = hold_state(root, comments, number)
        if reason:
            held.append({"brief": number, "reason": reason})
        ignored += [{"brief": number, "by": login} for login in logins]
    return held, ignored


def assign_spent(
    number: int, build: str | None, cid: int, open_briefs: set[int] | None, takes: list, prs: list
) -> bool:
    """Brief #1020 answers 1 and 2: whether the `Assign: <slot> #<number> [build (<x>)]` of comment
    `cid` is spent for any slot: the brief is not among the open briefs read (closed), a slot has
    a live `taken:` of it (of that build, when the line names one) after the line, or an open pull
    request has `Brief: #<number>` (and that build in its title). False when the open briefs were
    not read (None): a brief's state is never guessed, so the slot stays held as before."""
    if open_briefs is None:
        return False
    if number not in open_briefs:
        return True
    if any(t[1] > cid and not t[5] and build in (None, t[6]) for t in takes):
        return True
    return any(
        p.get("state") == "open"
        and brief_number(p) == number
        and (build is None or names_build(p, number, build))
        for p in prs
    )


def pending_assigns(
    s: Survey, authors: list[str], open_briefs: set[int] | None = None
) -> dict[str, tuple] | None:
    """Each slot's newest `Assign: <slot> #<brief> [build (<x>)]` by a listed author on the
    assignments issue, newer than the slot's last `Request:` and with no `taken:` of the slot after
    it, as (brief, build): that slot and that brief are spoken for (the verdict on 0534baa item 2).
    A line that `assign_spent` finds spent on the open briefs read holds nothing (brief #1020).
    None when the assignments issue cannot be read, so that no slot reads as free."""
    board = conductor_comments(s.repo)
    if board is None:
        return None
    allowed = {a.lstrip("@").lower() for a in authors}
    takes = [t for comments in s.comments.values() for t in all_takes(comments)]
    newest: dict[str, tuple] = {}
    for c in sorted((c for c in board if isinstance(c.get("id"), int)), key=lambda c: c["id"]):
        match = ASSIGN.fullmatch(first_line(c))
        if match and author_of(c) in allowed:
            newest[match.group(1)] = (c["id"], match)
    out = {}
    for slot, (cid, match) in newest.items():
        if match.group(3) is None or match.group(5) or cid < last_request(board, slot):
            continue
        if any(t[2] == slot and t[1] > cid for t in takes):
            continue
        number, build = int(match.group(3)), match.group(4)
        mine = all_takes(s.comments.get(number) or [])
        if assign_spent(number, build, cid, open_briefs, mine, s.prs):
            continue
        out[slot] = (int(match.group(3)), match.group(4))
    return out


def assign_line_of(entry: dict) -> str:
    """The `Assign:` line the conductor posts for a row of the plan's `assign` list (ADR-0402)."""
    build = f" build ({entry['build']})" if "build" in entry else ""
    return f"Assign: {entry['session']} #{entry['brief']}{build}"


def start_entry(name: str, brief: dict, protected: list[str] | None) -> dict:
    """One entry of the plan's `start` list, with the brief's kind by SPEC-0045 rule 4 (brief
    709): a body that cannot be read gives `design`, the highest; the conductor only raises it."""
    body = brief.get("body")
    kind = task_kind(body, protected) if isinstance(body, str) else "design"
    entry = {"session": name, "brief": brief["number"], "title": brief.get("title"), "kind": kind}
    return entry | ({"build": brief["build"]} if brief.get("build") else {})


RESERVES = {"balanced": 0.25, "small": 0.5}  # the share of the machine each profile keeps free
SMALL_MOST = 2  # `small` runs at most 2 builders at once
AUTO_RESERVE = RESERVES["balanced"]  # `auto` drops under a quarter of the machine (Q-842-5)
MEASURES = (("memory", "builder_memory_gb"), ("cpu", "builder_cpus"), ("disk", "builder_disk_gb"))
FREE_KEYS = {"memory": "available_bytes", "cpu": "free_cores", "disk": "free_bytes"}


def total_memory() -> int | None:
    """The machine's memory in bytes (`os.sysconf`), None where it cannot be read."""
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None


def cpu_figures() -> tuple[float, int] | None:
    """(free cores: `os.cpu_count()` less the one-minute load, the cores), None when unread."""
    count = os.cpu_count()
    try:
        load = os.getloadavg()[0]
    except (AttributeError, OSError):
        return None
    return (max(0.0, count - load), count) if count else None


def disk_figures(root) -> tuple[int, int] | None:
    """(free bytes, total bytes) of the disk under the repository, None when unread."""
    try:
        usage = shutil.disk_usage(root)
    except OSError:
        return None
    return usage.free, usage.total


def ceilings(root, flow_max: int) -> dict:
    """SPEC-0034 rule 1: each ceiling the smaller of `[flow]` and `[capacity]`, and the profile
    (`none` without a table); `reviews_in_flight` is `max_builders` when unset, and always under
    `fixed`, which reads no other ceiling."""
    table = config.capacity_settings(Path(root)) or {}
    found: dict = {"profile": table.get("profile", "none")}
    for key in ("max_builders", "reviews_in_flight", "builder_memory_gb"):
        set_in_flow = flow_value(root, key, None, RULE) is not None
        values = [flow_int(root, key, 1, RULE)] if set_in_flow else []
        found[key] = min([*values, table[key]] if key in table else values, default=None)
    found["max_builders"] = min(flow_max, found["max_builders"] or flow_max)
    found |= {k: table.get(k) for k in ("builder_cpus", "builder_disk_gb")}
    found["builders_run"] = table.get("builders_run", "here")
    found["review_minutes"] = table.get("review_minutes", config.REVIEW_MINUTES)
    if found["profile"] == "fixed" or found["reviews_in_flight"] is None:
        found["reviews_in_flight"] = found["max_builders"]
    return found


def figure(root, name: str) -> tuple[float | None, float | None]:
    """(free, total) of one figure; either may be None when it cannot be read."""
    if name == "memory":
        return common.available_memory(), total_memory()
    got = cpu_figures() if name == "cpu" else disk_figures(root)
    return got if got else (None, None)


def measured_capacity(root, ceil: dict, running: int) -> dict:
    """The measured figures of the profile: none under `full` and `fixed`; memory alone with no
    reserve under `none` and `auto` (brief #409); memory, cores and disk under `balanced` and
    `small`, each only where its per-builder setting is set, with the profile's reserve. A figure
    is (free - reserve x total) // per builder, never below 1 while no builder runs (the verdict
    on 43ada36), or `unknown`, which is left out, never read as 0."""
    profile = ceil["profile"]
    if profile in ("full", "fixed") or (profile == "auto" and ceil["builders_run"] == "cloud"):
        return {}
    reserve = RESERVES.get(profile, 0)
    found: dict = {}
    for name, key in MEASURES if reserve or profile == "auto" else MEASURES[:1]:
        per = ceil[key]
        if per is None:
            continue
        found[key] = per
        free, total = figure(root, name)
        if free is None or (reserve and total is None):
            found[name] = "unknown"
            continue
        unit = per if name == "cpu" else per * GIB
        builders = max(0, int((free - reserve * (total or 0)) // unit))
        if running == 0:
            builders = max(1, builders)
        found[name] = {FREE_KEYS[name]: free, "builders": builders}
    return found


def figure_text(cap: dict, name: str) -> str:
    """The figure that a limit names: a setting's number, or a measured one."""
    if name == "reviews":
        return f"{cap['waiting_for_verdict']} waiting of {cap['reviews_in_flight']}"
    if name in ("max_builders", "small"):
        return str(cap["ceiling"])
    if name == "adapt":
        return f"{cap['adapt']['count']} {cap['adapt']['why']}"
    free = cap[name][FREE_KEYS[name]]
    if name == "cpu":
        return f"{int(free)} cores free"
    return f"{free // GIB} GB " + ("available" if name == "memory" else "free")


def capacity_line(cap: dict) -> str:
    """`Capacity: <n> of <ceiling> (<profile>; limit: <name> <figure>).` (amendment 149 item 7),
    then ` Unknown: <names>.` for each counted figure that cannot be read."""
    line = (
        f"Capacity: {cap['slots']} of {cap['ceiling']} ({cap['profile']}; "
        f"limit: {cap['limit']} {figure_text(cap, cap['limit'])})."
    )
    unknown = [name for name, _ in MEASURES if cap.get(name) == "unknown"]
    return line + (f" Unknown: {', '.join(unknown)}." if unknown else "")


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
    if cap.get("limit") == "small":
        most = f"at most {SMALL_MOST} builders at once"
        return f"the small profile runs {most} ({cap['running']} running)"
    if cap.get("limit") == "adapt":
        got = cap["adapt"]
        return f"the adapted capacity is {got['count']} ({got['why']}; {cap['running']} running)"
    if cap.get("limit") in ("cpu", "disk"):
        name = cap["limit"]
        key = dict(MEASURES)[name]
        figures = f"{figure_text(cap, name)}, {key} is {cap[key]}"
        return f"the machine's {name} has room for no more builders ({figures})"
    if cap.get("limit") == "memory":
        return (
            "the machine's memory has room for no more builders "
            f"({cap['memory']['available_bytes'] // GIB} GB available, "
            f"builder_memory_gb is {cap['builder_memory_gb']})"
        )
    if cap.get("free_slots") == 0:
        return "every builder slot is working (builder_slots in the flow table)"
    if cap["reviews_in_flight"] - cap["waiting_for_verdict"] <= 0:
        return (
            f"the conductor has {cap['waiting_for_verdict']} pull requests waiting for a verdict "
            f"(reviews_in_flight is {cap['reviews_in_flight']})"
        )
    return f"{cap['running']} builders already run (max_builders is {cap['max_builders']})"


def words(plan: dict) -> str:
    lines: list[str] = []
    started = plan["start"]
    if plan.get("assign"):
        rows = ", ".join(row["line"].removeprefix("Assign: ") for row in plan["assign"])
        lines.append(f"Assign {len(plan['assign'])}: {rows}.")
    elif started:
        takes = ", ".join(
            f"{s['session']} takes #{s['brief']}"
            + (f" build ({s['build']})" if "build" in s else "")
            for s in started
        )
        lines.append(f"Start {len(started)}: {takes}.")
    else:
        lines.append(f"Start 0: {reason(plan)}.")
    lines.append(capacity_line(plan["capacity"]))
    if "adapt" in plan["capacity"]:
        got = plan["capacity"]["adapt"]
        lines.append(f"Adapt: {got['count']} of {got['highest']} ({got['why']}).")
    found = plan.get("milestones") or {}
    lines += [
        f"#{x['brief']} {x['milestone']}: unblocks {x['unblocks']:g} h."
        for x in found.get("starts", [])
    ]
    lines += list(found.get("idle", []))
    lines += playbook_lines(plan)
    for w in plan["waits"]:
        lines.append(f"#{w['brief']} {wait_text(w)}.")
    for h in plan["holders"]:
        held = ", ".join(f"#{n}" for n in h["briefs"])
        lines.append(
            f"Holds {len(h['briefs'])}: #{h['pr']} ({h['state']}, idle {h['idle']} min) for {held}"
        )
        if "stall" in h:
            lines.append(h["stall"])
    if plan["stale_claims"]:
        lines.append(
            "Stale: " + ", ".join(f"#{c['brief']} ({c['why']})" for c in plan["stale_claims"]) + "."
        )
    lines += [
        f"MALFORMED: #{m['brief']} {m['why']}" + (f" (fix: {m['filer']})" if m["filer"] else "")
        for m in plan["malformed"]
    ]
    lines += [f"HELD: #{h['brief']} {HELD_PREFIX}{h['reason']}" for h in plan.get("held", [])]
    lines += [f"HOLD IGNORED: #{h['brief']} by {h['by']}" for h in plan.get("ignored_holds", [])]
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
    if "reads" in plan:
        lines.append(reads_line(plan["reads"]))
    return "\n".join(lines) + "\n"


# --- `auto` adapts by evidence (SPEC-0034 rule 15, amendment 149 items 5 and 6, ADR-0435) -------

CAPACITY_FILE = "docs/runs/capacity-record.jsonl"  # `plan --record` only, kept out of git (Q-842-2)
CHANGES_KEPT = 20
USUAL_RUNS = 20  # "usual": the median of the last 20 successful governance runs (Q-842-6)
USUAL_TIMES = 1.5
REVIEWS_KEPT = 10
REVIEW_PULLS = 30  # the newest pull requests read for the last 10 verdicts
CHECK_RUNS = "repos/{}/actions/workflows/governance.yml/runs?status=success&per_page={}"


def median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def check_runs(repo: str) -> list[float] | None:
    """Minutes of the last successful governance runs, newest first; None when unread."""
    got = gh(CHECK_RUNS.format(repo, USUAL_RUNS))
    runs = got.get("workflow_runs") if isinstance(got, dict) else None
    if not isinstance(runs, list):
        return None
    found = []
    for run in runs:
        try:
            start = datetime.strptime(str(run.get("run_started_at")), "%Y-%m-%dT%H:%M:%SZ")
            end = datetime.strptime(str(run.get("updated_at")), "%Y-%m-%dT%H:%M:%SZ")
        except (AttributeError, ValueError):
            continue
        found.append((end - start).total_seconds() / 60)
    return found


def checks_hold(runs: list[float] | None) -> bool | None:
    """The newest run within 1.5 times the median of the last 20; None with fewer than 20."""
    if not runs or len(runs) < USUAL_RUNS:
        return None
    return runs[0] <= USUAL_TIMES * median(runs[:USUAL_RUNS])


def review_times(s: Survey, authors: list[str] | None) -> list[float] | None:
    """Minutes from a `Report:` that asks for a verdict to the `Verdict:` by a listed author that
    names its head, for the last 10 verdicts of the newest pull requests, newest first."""
    pulls = sorted(s.prs, key=lambda p: str(p.get("updated_at")), reverse=True)[:REVIEW_PULLS]
    found: list[tuple[datetime, float]] = []
    for pr in pulls:
        comments = pages(f"repos/{s.repo}/issues/{pr['number']}/comments")
        if comments is None:
            continue
        me = pr_login(pr).lstrip("@").lower()
        counted = {a.lstrip("@").lower() for a in counted_authors(authors, me) or []}
        asked: list[tuple[str, datetime]] = []
        for c in sorted(comments, key=comment_id):
            line = first_line(c)
            if author_of(c) == me and WAITING_REPORT.match(line):
                asked.append((line.split()[1], moment(c.get("created_at"))))
            verdict = VERDICT_HEAD.match(line)
            if verdict and author_of(c) in counted:
                head = verdict.group(1)
                named = [x for x in asked if head.startswith(x[0]) or x[0].startswith(head)]
                if named:  # the newest report that asked about this head, never an older one
                    when = moment(c.get("created_at"))
                    found.append((when, (when - named[-1][1]).total_seconds() / 60))
                    asked = [x for x in asked if x not in named]
    found.sort(key=lambda x: x[0], reverse=True)
    return [minutes for _, minutes in found[:REVIEWS_KEPT]]


VERDICT_HEAD = re.compile(r"Verdict: (?:cleared|fix list|rejected) ([0-9a-f]{7,40})")


def review_state(times: list[float] | None, limit: int) -> str:
    """The median review against `review_minutes`: `ok` under it, `at` on it (stops the rise),
    `over` it (drops the count), `unknown` when no review can be read."""
    if not times:
        return "unknown"
    got = median(times)
    return "ok" if got < limit else "at" if got == limit else "over"


def capacity_rows(root) -> list[dict]:
    """The record's lines that read as JSON objects with a whole `count`; others are left out."""
    path = Path(root) / CAPACITY_FILE
    try:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
    except OSError:
        return []
    rows = []
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and type(row.get("count")) is int:
            rows.append(row)
    return rows


def adapt(root, s: Survey, ceil: dict, measured: dict, running: int, authors, record: bool) -> dict:
    """The count under `auto`: the smallest figure with no history, else the last count moved by
    one by the readable conditions (a condition that cannot be read counts neither way)."""
    figures = [running + m["builders"] for m in measured.values() if isinstance(m, dict)]
    highest = max(1, min([ceil["max_builders"], *figures]))
    rows = capacity_rows(root)
    conditions = {"starts": "unknown"}  # a refused start is recorded nowhere (Q-842-8)
    if rows:
        # Item 5: checks and reviews (with starts) decide a rise; a refused start, memory or disk
        # under its reserve, or reviews over `review_minutes` decide a drop. Slow checks and
        # reviews at the limit only stop the rise; the reserve never raises the count.
        checks = {True: "ok", False: "over", None: "unknown"}[checks_hold(check_runs(s.repo))]
        conditions["checks"] = checks
        conditions["reviews"] = review_state(review_times(s, authors), ceil["review_minutes"])
        for name in ("memory", "disk"):
            if isinstance(measured.get(name), dict):
                free, total = figure(root, name)
                room = None if free is None or total is None else free >= AUTO_RESERVE * total
                conditions[name] = {True: "ok", False: "under", None: "unknown"}[room]
        drops = [n for n, v in conditions.items() if v in ("over", "under") and n != "checks"]
        rises = {n: conditions[n] for n in ("checks", "reviews") if conditions[n] != "unknown"}
        stops = [n for n, v in rises.items() if v != "ok"]
        last = rows[-1]["count"]
        if drops:
            count, why = max(1, min(highest, last - 1)), "drop: " + ", ".join(drops)
        elif rises and not stops:
            count, why = min(highest, last + 1), "rise"
        elif stops:
            count, why = min(highest, last), "held: " + ", ".join(stops)
        else:
            count, why = min(highest, last), "nothing read"
        change = count - last
    else:
        count, why, change = highest, "no history", 0
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {"at": now, "count": count, "change": change, "why": why}
    if record:
        write_capacity(root, row)
    changes = [r for r in [*rows, row] if r.get("change")][-CHANGES_KEPT:]
    return {
        "count": count,
        "highest": highest,
        "change": change,
        "why": why,
        "history": bool(rows),
        "conditions": conditions,
        "changes": changes,
    }


def write_capacity(root, row: dict) -> None:
    """Append one line to the record (`plan --record`), kept out of git like the holds."""
    target = Path(root) / CAPACITY_FILE
    try:
        keep_out_of_git(root, CAPACITY_FILE)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as out:
            out.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError as exc:
        raise CheckError("rule 15: the record of capacity cannot be written") from exc


def plan(root, as_json: bool, record: bool = False) -> int:
    found = build(root, record)
    print(json.dumps(found, indent=2) if as_json else words(found), end="" if not as_json else "\n")
    return 0
