# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""One owner per new path across the plan, and free names from the feature (brief #1425, ADR-0598).

    python3 plan_names.py next --base <path> [--root DIR] [--issues FILE] [--pulls FILE]
    python3 plan_names.py batch FILE [--root DIR] [--issues FILE] [--pulls FILE]
    python3 plan_names.py impact PATH [--root DIR] [--issues FILE] [--pulls FILE]

A path a brief adds (`Adds:`) belongs to one brief from filing until it merges or closes. An entry
clashes with (a) a file of the default branch's tree, (b) an `Adds:` entry of another open brief,
parked and taken ones included, or (c) a file an open pull request adds, by an exact or covering
match: a folder against a file under it, either way, and a glob against a path it matches. A match
with another brief's `Touches:` alone is no clash: the plan orders the two (answer 1).

Paths compare as the forge and the file systems do (answer 3): `./`, a trailing `/`, `/**`,
backslashes and repeated slashes are normalised and case is ignored. A Windows reserved name and a
path over 200 characters are refused. The files every build adds by rule are left out: the
`changelog.d/brief-<n>.md` fragment, ADR and spec files (their numbers are `Reserved:`) and
`docs/runs/decisions/` files.

`next` prints the base when free, else the base with `-2`, `-3`, ...: free means absent from the
tree, every open brief's `Adds:` and `Touches:` and every open pull request's added files. `batch`
names one base per line of FILE in one pass, so a batch never clashes with itself. `impact` lists
every open brief and pull request that names a path, and who renames it: the steward edits a brief
not yet taken, a taken brief gets a fix list (answer 6). Names are lower case `[a-z0-9-]`, by the
convention `<feature>-m<milestone>-<part>` (`access-control-m7-api`).

The open briefs are one listing (`--issues FILE`, a saved list of issues, else one paged GET of the
`agk-brief` issues); the open pull requests are `--pulls FILE` (`[{"number", "brief", "added"}]`)
or one listing and one file read each. No model; no network with both files given.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import session
import session_plan
from common import CheckError, run, utf8_output

NAME = "plan-names"
USAGE = (
    "usage: plan_names.py (next --base PATH | batch FILE | impact PATH) "
    "[--root DIR] [--issues FILE] [--pulls FILE]"
)
MAX_PATH = 200
MAX_TRIES = 999
RESERVED = {"con", "prn", "aux", "nul"} | {f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10)}
BY_RULE = re.compile(
    r"changelog\.d/brief-\d+\.md|docs/(adr|specs)/\d{4}-[^/]+\.md|docs/runs/decisions/.+"
)
NAME_PART = re.compile(r"[a-z0-9][a-z0-9-]*")
TAKEN_LABEL = "agk:taken"
ORIGIN_URL = re.compile(
    r'\[remote "origin"\][^\[]*?^\s*url\s*=\s*\S*github\.com[:/]'
    r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?\s*$",
    re.M,
)


def norm(path: str) -> str:
    """A path as the forge and the file systems compare it: slashes, `./`, `/**`, case."""
    p = re.sub(r"/+", "/", path.strip().replace("\\", "/"))
    while p.startswith("./"):
        p = p[2:]
    p = p.removesuffix("/**").rstrip("/")
    return p.lower()


def by_rule(path: str) -> bool:
    """A file every build adds by rule, its name already unique (answer 3)."""
    return BY_RULE.fullmatch(norm(path)) is not None


def name_problems(entry: str) -> list[str]:
    """Answer 3: a Windows reserved name or a path over 200 characters, naming the entry."""
    out = []
    if any(part.split(".")[0] in RESERVED for part in norm(entry).split("/")):
        out.append(f"rule 4: Adds entry {entry} uses a name Windows reserves")
    if len(norm(entry)) > MAX_PATH:
        out.append(f"rule 4: Adds entry {entry} is over {MAX_PATH} characters")
    return out


def _wild(p: str) -> bool:
    return session.literal(p) != p


def _ancestors(p: str) -> list[str]:
    parts = p.split("/")
    return ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]


def covers(a: str, b: str) -> bool:
    """An exact or covering match: equal, a folder above the other, or a glob matching it or a
    folder above it; two globs whose fixed parts meet."""
    x, y = norm(a), norm(b)
    if x == y or y.startswith(x + "/") or x.startswith(y + "/"):
        return True
    for g, p in ((x, y), (y, x)):
        if (
            _wild(g)
            and not _wild(p)
            and any(session.glob_regex(g).fullmatch(q) for q in _ancestors(p))
        ):
            return True
    if _wild(x) and _wild(y):
        lx, ly = session.literal(x), session.literal(y)
        return lx.startswith(ly) or ly.startswith(lx)
    return False


def adds_of(body: str) -> list[str]:
    return [e for e in session.line_entries(body or "", session.ADDS) if e and not by_rule(e)]


def touches_only(body: str) -> list[str]:
    return [e for e in session.line_entries(body or "", session.TOUCHES) if e and not by_rule(e)]


@dataclass
class Holders:
    """What holds a path: the tree, the open briefs (issues) and the open pull requests."""

    tree: list[str] = field(default_factory=list)
    briefs: list[dict] = field(default_factory=list)
    pulls: list[dict] = field(default_factory=list)  # {"number", "brief", "added": [paths]}


def is_taken(brief: dict) -> bool:
    names = {str(x.get("name")) for x in brief.get("labels") or [] if isinstance(x, dict)}
    return TAKEN_LABEL in names


def clashes(number: int | None, entries: list[str], h: Holders) -> list[dict]:
    """Answer 1: each entry against (a) the tree, (b) other briefs' `Adds:`, (c) pull requests'
    added files; one row per entry, the first holder found."""
    out = []
    for e in (x for x in entries if not by_rule(x)):
        holder = next((("main", f) for f in h.tree if covers(e, f)), None)
        holder = holder or next(
            (
                (f"#{b['number']}", a)
                for b in h.briefs
                if b.get("number") != number
                for a in adds_of(str(b.get("body") or ""))
                if covers(e, a)
            ),
            None,
        )
        holder = holder or next(
            (
                (f"#{p['number']}", f)
                for p in h.pulls
                if p.get("brief") != number
                for f in p.get("added") or []
                if not by_rule(f) and covers(e, f)
            ),
            None,
        )
        if holder:
            out.append({"path": e, "holder": holder[0], "theirs": holder[1]})
    return out


def orders(number: int | None, entries: list[str], h: Holders) -> list[dict]:
    """Answer 1 (d): another open brief's `Touches:` meets an entry: the plan orders them."""
    return [
        {"path": e, "brief": b["number"]}
        for e in entries
        for b in h.briefs
        if b.get("number") != number and any(covers(e, t) for t in touches_only(str(b.get("body"))))
    ]


def _at_or_below(entry: str, candidate: str) -> bool:
    """A `Touches:` entry holds a name only at it or below it, never from a folder above it."""
    t, c = norm(entry), norm(candidate)
    return (
        t == c
        or t.startswith(c + "/")
        or (_wild(t) and session.glob_regex(t).fullmatch(c) is not None)
    )


def _held(candidate: str, h: Holders, extra: list[str]) -> bool:
    """Answer 5: a name is held by any of the four sources, or is refused by answer 3."""
    every = list(h.tree) + extra + [f for p in h.pulls for f in p.get("added") or []]
    touched: list[str] = []
    for b in h.briefs:
        body = str(b.get("body") or "")
        every += adds_of(body)
        touched += touches_only(body)
    return (
        any(covers(candidate, x) for x in every)
        or any(_at_or_below(t, candidate) for t in touched)
        or bool(name_problems(candidate))
    )


def free(base: str, h: Holders, extra: list[str] | None = None) -> str:
    """Answer 5: the base when free, else the base with -2, -3, ... (folder slash kept)."""
    slash = "/" if base.replace("\\", "/").rstrip().endswith("/") else ""
    path = norm(base)
    head, _, last = path.rpartition("/")
    stem, dot, ext = last.partition(".")
    if not NAME_PART.fullmatch(stem) or (dot and not re.fullmatch(r"[a-z0-9.]+", ext)):
        raise CheckError("rule 5: the base's last part is not lower case [a-z0-9-]")
    prefix = f"{head}/" if head else ""
    for n in range(1, MAX_TRIES + 1):
        name = f"{prefix}{stem}{'' if n == 1 else f'-{n}'}{dot}{ext}"
        if not _held(name, h, extra or []):
            return name + slash
    raise CheckError(f"rule 5: no free name within {MAX_TRIES} tries of the base")


def batch(bases: list[str], h: Holders) -> list[str]:
    """Answer 5: a whole batch in one pass; each name holds for the ones after it."""
    named: list[str] = []
    for base in bases:
        named.append(free(base, h, named))
    return named


def impact(path: str, h: Holders) -> list[str]:
    """Answer 6: every open brief and pull request that names PATH, and who renames it."""
    want = norm(path)
    out = []
    for b in h.briefs:
        text = norm_text(str(b.get("body") or ""))
        if want in text:
            who = "fix list (taken)" if is_taken(b) else "steward edits (not taken)"
            out.append(f"#{b['number']} brief: {who}")
    for p in h.pulls:
        text = norm_text(str(p.get("body") or "")) + " " + " ".join(map(norm, p.get("added") or []))
        if want in text:
            out.append(f"#{p['number']} pull request: fix list")
    return out


def norm_text(text: str) -> str:
    return re.sub(r"/+", "/", text.replace("\\", "/")).lower()


def plan_clashes(issues: list[dict], taken: set[int], tree: list[str] | None = None) -> list[dict]:
    """Answer 2: two open briefs whose `Adds:` already clash (filed before this check), each
    pair once, with a free name for the one not taken (the later one when neither is)."""
    out: list[dict] = []
    added = [(i, adds_of(str(i.get("body") or ""))) for i in issues]
    added = sorted(((i, a) for i, a in added if a), key=lambda x: x[0]["number"])
    for k, (a, mine) in enumerate(added):
        for b, theirs in added[k + 1 :]:
            hit = next(((x, y) for x in mine for y in theirs if covers(x, y)), None)
            if hit is None:
                continue
            rename, keep = (
                (a, hit) if b["number"] in taken and a["number"] not in taken else (b, hit[::-1])
            )
            rest = Holders(tree or [], [i for i in issues if i["number"] != rename["number"]])
            try:
                name = free(rename_base(keep[0], keep[1]), rest)
            except CheckError:
                name = "none from this entry; name one with plan_names.py next"
            out.append(
                {
                    "briefs": [a["number"], b["number"]],
                    "path": hit[0],
                    "rename": rename["number"],
                    "free": name,
                    "taken": [n for n in (a["number"], b["number"]) if n in taken],
                }
            )
    return out


def clash_line(c: dict) -> str:
    a, b = c["briefs"]
    return (
        f"CLASH: #{a} and #{b} both add {c['path']}; rename in the one not taken "
        f"(#{c['rename']}, free: {c['free']})"
    )


def cached_issues(root: Path) -> list[dict]:
    """Answer 9: the open briefs from the read cache the plan already wrote, with no request; none
    when the repository or the cache cannot be read."""
    try:  # the origin from `.git/config` itself: the check runs no command
        origin = ORIGIN_URL.search((Path(root) / ".git" / "config").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return []
    if origin is None:
        return []
    repo = origin.group(1)
    found: list[dict] = []
    for page in range(1, 100):
        endpoint = f"repos/{repo}/issues?state=open&labels={session.LABEL}"
        entry = session.CACHE.entry(f"{endpoint}&per_page={session.PAGE}&page={page}")
        body = entry.get("body") if entry else None
        if not isinstance(body, list):
            break
        found += [x for x in body if isinstance(x, dict) and "pull_request" not in x]
        if len(body) < session.PAGE:
            break
    return found


def rename_base(mine: str, theirs: str) -> str:
    """The level to rename: where the two paths meet, so a file under a held folder gets a free
    folder and not a free file name that the folder still covers."""
    a, b = norm(mine).split("/"), norm(theirs).split("/")
    if _wild(norm(theirs)) or len(a) <= len(b):
        return mine
    return "/".join(a[: len(b)]) + "/"


def brief_problems(number: int | None, body: str, h: Holders) -> list[str]:
    """Answers 1 to 3 for one brief: what another open brief or pull request holds, each with a
    free name, and the names answer 3 refuses."""
    entries = adds_of(body)
    out = [p for e in entries for p in name_problems(e)]
    for c in clashes(number, entries, h):
        rest = Holders(h.tree, [b for b in h.briefs if b.get("number") != number], h.pulls)
        try:
            name = free(rename_base(c["path"], c["theirs"]), rest)
        except CheckError:
            name = "none from this entry; name one with plan_names.py next"
        out.append(
            f"rule 4: Adds entry {c['path']} is held by {c['holder']} ({c['theirs']}); free: {name}"
        )
    return out


def load_json(path: str, what: str) -> list:
    try:
        found = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CheckError(f"{what} cannot be read") from exc
    if not isinstance(found, list):
        raise CheckError(f"{what} is not a list")
    return [x for x in found if isinstance(x, dict)]


def read_holders(root: Path, issues: str | None, pulls: str | None) -> Holders:
    """The four sources, each read once: a saved file where given, else one listing."""
    tree = session_plan.tree_files(root, f"origin/{session_plan._default_branch(root)}")
    repo = None if issues and pulls else session.repo_name(root)
    listed = (
        load_json(issues, "the issues file")
        if issues
        else session.pages(f"repos/{repo}/issues?state=open&labels={session.LABEL}")
    )
    if listed is None:
        raise CheckError("the open briefs cannot be read")
    briefs = session_plan.plan_briefs([b for b in listed if "pull_request" not in b])
    if pulls:
        prs = load_json(pulls, "the pulls file")
    else:
        prs = []
        for p in session.pages(f"repos/{repo}/pulls?state=open") or []:
            files = session.pages(f"repos/{repo}/pulls/{p['number']}/files") or []
            added = [str(f.get("filename")) for f in files if f.get("status") == "added"]
            found = re.search(r"(?m)^Brief: #(\d+)", str(p.get("body") or ""))
            brief = int(found.group(1)) if found else None
            prs.append(
                {"number": p["number"], "brief": brief, "added": added, "body": p.get("body")}
            )
    return Holders(tree=tree, briefs=briefs, pulls=prs)


def parsed(args: list[str]) -> tuple[str, str, dict[str, str]] | None:
    if len(args) < 2 or args[0] not in ("next", "batch", "impact"):
        return None
    verb, rest = args[0], args[1:]
    if verb == "next":
        if rest[:1] != ["--base"] or len(rest) < 2:
            return None
        value, rest = rest[1], rest[2:]
    else:
        value, rest = rest[0], rest[1:]
    flags: dict[str, str] = {}
    while len(rest) >= 2 and rest[0] in ("--root", "--issues", "--pulls") and rest[0] not in flags:
        flags[rest[0]] = rest[1]
        rest = rest[2:]
    return (verb, value, flags) if not rest else None


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    found = parsed(sys.argv[1:] if argv is None else argv)
    if found is None:
        print(USAGE)
        return 2
    verb, value, flags = found

    def act() -> int:
        h = read_holders(
            Path(flags.get("--root", ".")), flags.get("--issues"), flags.get("--pulls")
        )
        if verb == "next":
            print(free(value, h))
        elif verb == "batch":
            try:
                bases = Path(value).read_text(encoding="utf-8").split()
            except (OSError, UnicodeDecodeError) as exc:
                raise CheckError("the batch file cannot be read") from exc
            print("\n".join(batch(bases, h)))
        else:
            print(
                "\n".join(impact(value, h))
                or f"impact: no open brief or pull request names {value}"
            )
        return 0

    return run(NAME, act)


if __name__ == "__main__":
    sys.exit(main())
