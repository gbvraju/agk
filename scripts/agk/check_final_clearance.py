"""A fix list that names only the final commit clears that commit in advance (SPEC-0021).

    python3 check_final_clearance.py [--comments FILE] [--head SHA]

When the latest verdict by a listed author is a covered fix list (`Verdict: fix list <sha>`, `Final:
<path> <old> -> <new>` lines, no numbered item) and the head is the one commit after its reviewed
sha, the commit must change exactly the named status lines. Anything else passes unchecked. Without
`--comments` it prints `skipped (no comments file)` and passes. Git and the file only: no network,
no model. Messages name the rule, never a value.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from common import CheckError, covered_fix_list, final_commit_problems, git, repo_root, run
from metrics import VERDICT, author_of
from reviewers import verdict_authors

NAME = "final-clearance"
USAGE = "usage: check_final_clearance.py [--comments FILE] [--head SHA]"


def comments_of(path: Path) -> list[dict]:
    """The comments of `gh api --paginate`: an array, arrays, pages or one object a line."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the comments file cannot be read") from exc
    found: list[dict] = []
    decoder, at = json.JSONDecoder(), 0
    try:
        while at < len(text):
            if text[at].isspace():
                at += 1
                continue
            value, at = decoder.raw_decode(text, at)
            pending = [value]
            while pending:
                item = pending.pop(0)
                if isinstance(item, list):
                    pending = item + pending
                elif isinstance(item, dict):
                    found.append(item)
    except ValueError as exc:
        raise CheckError("the comments file is not JSON") from exc
    return found


def latest_verdict(root: Path, comments: list[dict]) -> str:
    """The body of the latest verdict comment by a listed author, or an empty string."""
    listed = set(verdict_authors(root))
    verdicts = [
        c
        for c in comments
        if author_of(c) in listed
        and isinstance(c.get("body"), str)
        and VERDICT.fullmatch(c["body"].splitlines()[0] if c["body"] else "")
    ]
    verdicts.sort(key=lambda c: str(c.get("created_at", "")))
    return verdicts[-1]["body"] if verdicts else ""


def check(root: Path, comments: Path, head: str) -> int:
    covered = covered_fix_list(latest_verdict(root, comments_of(comments)))
    if covered is not None:
        sha, edits = covered
        commit = git(root, "rev-parse", head).strip()
        parents = git(root, "rev-list", "--parents", "-n", "1", commit).split()[1:]
        if len(parents) == 1 and parents[0].startswith(sha):
            files_ok, bad = final_commit_problems(root, parents[0], commit, edits)
            moded = git(root, "diff", "--summary", parents[0], commit).strip()
            if not files_ok or bad or moded:
                raise CheckError("rule 3: the commit is not exactly the named status lines")
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    opts = dict(zip(args[::2], args[1::2], strict=False))
    if len(args) % 2 or not set(opts) <= {"--comments", "--head"}:
        print(USAGE)
        return 2
    if "--comments" not in opts:
        print("skipped (no comments file)")
        return 0
    root = repo_root()
    return run(NAME, lambda: check(root, Path(opts["--comments"]), opts.get("--head", "HEAD")))


if __name__ == "__main__":
    sys.exit(main())
