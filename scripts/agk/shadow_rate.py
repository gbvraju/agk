"""The conductor's catch rate from the marks of the shadow review (SPEC-0035 rules 3, 4 and 8).

    python3 shadow_rate.py --api-dir DIR --shadow-issue N [--authors LOGIN,LOGIN]

Reads recorded GitHub responses in DIR, named as in SPEC-0007 rule 20 (`pulls.json` and
`comments-<n>.json` for each pull request and for the `agk-shadow` issue N), and prints, per ISO
week of the merge and in total: the heads reviewed by both reviewers, the right findings of the
conductor only, of the shadow only and of both, the wrong findings of each, the unmarked heads and
findings, and the catch rate, which is the right conductor findings divided by the right conductor
findings plus the right shadow-only findings (`none` without a right finding, never 0). A finding
is a numbered item of a verdict (`C<sha7>-<n>`) or an `S<n>.` line of a `Shadow:` comment
(`S<sha7>-<n>`); a head with no `Marks:` comment is unmarked, never zero findings. Only comments
by `--authors` (default: the `verdict_authors` of `config/reviewers.yaml`) count, and a `Marks:`
comment also by the pull request's own author. No network and no model; messages name the rule,
never a comment. Exit 1 when a mark is refused, 2 for a bad call or a missing input.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from common import CheckError, repo_root
from metrics import ApiDir, author_of
from reviewers import verdict_authors

NAME = "shadow_rate"
USAGE = "usage: shadow_rate.py --api-dir DIR --shadow-issue N [--authors LOGIN,LOGIN]"
VERDICT = re.compile(r"Verdict: (?:cleared|fix list|rejected) ([0-9a-f]{7,40})")
SHADOW = re.compile(r"Shadow: #(\d+) ([0-9a-f]{7,40}) (?:cleared|fix list|rejected)")
MARK = re.compile(r"([CS])([0-9a-f]{7})-(\d+) (right|wrong|both)")
ITEM = {"C": re.compile(r"(\d+)\. \S"), "S": re.compile(r"S(\d+)\. \S")}
KEYS = (
    "heads reviewed by both",
    "right, conductor only",
    "right, shadow only",
    "right, both",
    "wrong, conductor",
    "wrong, shadow",
    "unmarked heads",
    "unmarked findings",
)


def first_line(comment: dict) -> str:
    body = comment.get("body")
    return body.splitlines()[0].strip() if isinstance(body, str) and body.strip() else ""


def ordered(comments: list) -> list[dict]:
    return sorted((c for c in comments if isinstance(c, dict)), key=lambda c: c.get("id") or 0)


def findings(kind: str, comment: dict) -> list[str]:
    """The numbers of the findings of a verdict or a Shadow comment (the lines after the first)."""
    body = comment.get("body") if isinstance(comment.get("body"), str) else ""
    found = (ITEM[kind].match(line) for line in body.splitlines()[1:])
    return [m.group(1) for m in found if m]


def week_of(text: Any) -> str | None:
    try:
        when = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    year, week, _ = when.isocalendar()
    return f"{year}-W{week:02d}"


def rate(right_conductor: int, right_shadow_only: int) -> str:
    total = right_conductor + right_shadow_only
    if total == 0:
        return "none"
    return f"{right_conductor}/{total} ({100 * right_conductor / total:.1f}%)"


def heads_of(comments: list, allowed: set[str]) -> dict[str, tuple[str, list[str]]]:
    """sha7 -> (author, finding numbers) of the latest verdict of a listed author for that head."""
    heads: dict[str, tuple[str, list[str]]] = {}
    for c in ordered(comments):
        match = VERDICT.fullmatch(first_line(c))
        if match and author_of(c) in allowed:
            heads[match.group(1)[:7]] = (author_of(c), findings("C", c))
    return heads


def shadows_of(comments: list, allowed: set[str]) -> list[tuple[int, str, str, list[str]]]:
    """(pull request, sha7, author, finding numbers) of every Shadow comment of a listed author."""
    found = []
    for c in ordered(comments):
        match = SHADOW.fullmatch(first_line(c))
        if match and author_of(c) in allowed:
            found.append((int(match.group(1)), match.group(2)[:7], author_of(c), findings("S", c)))
    return found


def count(src: ApiDir, issue: int, allowed: set[str]) -> tuple[dict, int, int]:
    pulls = src.get("pulls", "")
    if not isinstance(pulls, list):
        raise CheckError("pulls.json in --api-dir is missing or not a list (path class api-dir)")
    shadow_comments = src.get(f"comments-{issue}", "")
    if not isinstance(shadow_comments, list):
        raise CheckError("the comments of the shadow issue are missing in --api-dir (path class)")
    merged = [p for p in pulls if isinstance(p, dict) and p.get("merged_at")]
    return count_pulls(
        [(p, src.get(f"comments-{p.get('number')}", "")) for p in merged], shadow_comments, allowed
    )


def count_pulls(
    merged: list[tuple[dict, Any]], shadow_comments: list, allowed: set[str]
) -> tuple[dict, int, int]:
    """The counts from merged pull requests with their comments (a list, or anything else when the
    copy is unreadable) and the comments of the shadow issue; `facts.py` calls this too."""
    shadows = shadows_of(shadow_comments, allowed)
    verdicts = {}
    unread = 0
    for pull, comments in merged:
        if isinstance(comments, list):
            verdicts[pull["number"]] = (pull, comments, heads_of(comments, allowed))
        else:
            unread += 1
    conductors = {a for _, _, heads in verdicts.values() for a, _ in heads.values()}
    shadowers = {a for _, _, a, _ in shadows}
    # one account for both reviewers cannot be told apart (a residual of SPEC-0035)
    differ = len(conductors | shadowers) > 1
    totals: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(KEYS, 0))
    paired = set()
    totals["total"]  # a total even when no head was reviewed by both
    for number, (pull, comments, heads) in sorted(verdicts.items()):
        week = week_of(pull["merged_at"]) or "unknown"
        mine = [(sha, a, nums) for n, sha, a, nums in shadows if n == number and sha in heads]
        paired |= {(number, sha) for sha, _, _ in mine}
        ids = {f"C{sha}-{n}": (a, sha) for sha, (a, nums) in heads.items() for n in nums} | {
            f"S{sha}-{n}": (a, sha) for sha, a, nums in mine for n in nums
        }
        marks = marks_of(comments, pull, ids, allowed, differ, number)
        has_marks = bool(marks[1])
        for sha, _, _ in mine:
            for bucket in (week, "total"):
                totals[bucket]["heads reviewed by both"] += 1
                totals[bucket]["unmarked heads"] += 0 if has_marks else 1
            for fid, (_, head) in ids.items():
                if head != sha:
                    continue
                tally(totals, (week, "total"), fid, marks[0].get(fid), has_marks)
    unpaired = sum(1 for n, sha, _, _ in shadows if (n, sha) not in paired)
    return totals, unpaired, unread


def tally(totals: dict, buckets: tuple, fid: str, mark: str | None, has_marks: bool) -> None:
    keys = {
        ("C", "right"): "right, conductor only",
        ("C", "both"): "right, both",
        ("C", "wrong"): "wrong, conductor",
        ("S", "right"): "right, shadow only",
        ("S", "wrong"): "wrong, shadow",
    }
    key = keys.get((fid[0], mark or ""))
    for bucket in buckets:
        if key:
            totals[bucket][key] += 1
        elif has_marks and mark is None:
            totals[bucket]["unmarked findings"] += 1


def marks_of(
    comments: list, pull: dict, ids: dict, allowed: set[str], differ: bool, number: int
) -> tuple[dict[str, str], bool]:
    """(mark by finding id, whether a counted Marks comment exists); a later line wins."""
    counted = allowed | {author_of(pull)}
    marks: dict[str, str] = {}
    seen = False
    for c in ordered(comments):
        if first_line(c) != "Marks:" or author_of(c) not in counted:
            continue
        seen = True
        for line in str(c.get("body")).splitlines()[1:]:
            found = MARK.fullmatch(line.strip())
            if not found:
                continue
            fid = f"{found.group(1)}{found.group(2)}-{found.group(3)}"
            if fid not in ids:
                raise MarkRefused(f"rule 3: a mark names no finding of pull request #{number}")
            if differ and ids[fid][0] == author_of(c):
                raise MarkRefused(f"rule 3: a mark is by the author of its finding (#{number})")
            marks[fid] = found.group(4)
    return marks, seen


class MarkRefused(CheckError):
    pass


def render(totals: dict, unpaired: int, unread: int) -> str:
    weeks = sorted(w for w in totals if w != "total")
    out = []
    for bucket in (*(f"week {w}" for w in weeks), "total"):
        data = totals["total" if bucket == "total" else bucket[5:]]
        out.append(bucket)
        out += [f"  {key}: {data[key]}" for key in KEYS]
        if bucket == "total":
            out.append(f"  unpaired shadow comments: {unpaired}")
            out.append(f"  unread pull requests: {unread}")
        right = data["right, conductor only"] + data["right, both"]
        out.append(f"  catch rate: {rate(right, data['right, shadow only'])}")
    return "\n".join(out)


FIELDS = {
    "heads reviewed by both": "heads",
    "right, conductor only": "right_conductor_only",
    "right, shadow only": "right_shadow_only",
    "right, both": "right_both",
    "wrong, conductor": "wrong_conductor",
    "wrong, shadow": "wrong_shadow",
    "unmarked heads": "unmarked_heads",
    "unmarked findings": "unmarked_findings",
}


def summary(totals: dict) -> dict[str, Any]:
    """The counts as JSON fields: `weeks` (ISO week of the merge -> counts) and `total`."""
    return {
        "weeks": {
            w: {FIELDS[k]: v for k, v in totals[w].items()} for w in sorted(totals) if w != "total"
        },
        "total": {FIELDS[k]: v for k, v in totals["total"].items()},
    }


def parse(args: list[str]) -> dict[str, str] | None:
    if len(args) % 2 or not args:
        return None
    opts = dict(zip(args[::2], args[1::2], strict=True))
    if len(opts) != len(args) // 2 or not set(opts) <= {"--api-dir", "--shadow-issue", "--authors"}:
        return None
    if not {"--api-dir", "--shadow-issue"} <= set(opts) or not opts["--shadow-issue"].isdigit():
        return None
    return opts


def main(argv: list[str] | None = None) -> int:
    opts = parse(sys.argv[1:] if argv is None else argv)
    if opts is None:
        print(USAGE)
        return 2
    try:
        if "--authors" in opts:
            listed = [a for a in opts["--authors"].split(",") if a]
        else:
            listed = verdict_authors(repo_root()) or []
        allowed = {a.lstrip("@").lower() for a in listed}
        if not allowed:
            raise CheckError("rule 4: no listed author (setting: verdict_authors)")
        totals, unpaired, unread = count(
            ApiDir(Path(opts["--api-dir"])), int(opts["--shadow-issue"]), allowed
        )
    except MarkRefused as exc:
        print(f"FAIL {NAME}: {exc}")
        return 1
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 2
    print(render(totals, unpaired, unread))
    return 0


if __name__ == "__main__":
    sys.exit(main())
