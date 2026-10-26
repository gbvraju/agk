"""A fix list that names only the final commit clears that commit in advance (SPEC-0021).

    python3 check_final_clearance.py [--comments FILE] [--reviews FILE] [--head SHA]
        [--author LOGIN] [--draft VALUE]

When the latest verdict by a listed author is a covered fix list (`Verdict: fix list <sha>`, `Final:
<path> <old> -> <new>` lines, no numbered item) and the head is the one commit after its reviewed
sha, the commit must change exactly the named status lines; a head two or more commits past the
reviewed sha (counted on the first-parent line) fails (SPEC-0030 rule 7). Anything else passes
unchecked. Without
`--comments` it prints `skipped (no comments file)` and passes. With two or more listed
authors the verdicts of `--author`, the pull request's own author, do not count (SPEC-0025 rule 4).
Git and the file only: no network, no model. Messages name the rule, never a value.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from common import (
    CheckError,
    agent_apps,
    covered_fix_list,
    final_commit_problems,
    git,
    repo_root,
    run,
)
from metrics import counted_authors, latest_verdict_body
from reviewers import person_approvals, spec_approvers, verdict_authors

NAME = "final-clearance"
SPEC_FILE = re.compile(r"docs/specs/(\d{4})-[^/]+\.md")
USAGE = (
    "usage: check_final_clearance.py [--comments FILE] [--reviews FILE] [--head SHA] "
    "[--author LOGIN] [--draft VALUE]"
)


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


def commits_past(root: Path, sha: str, head: str) -> int:
    """How many commits of the first-parent line lie between the reviewed sha and the head; 0
    when the sha is not in the history of the head (nothing can be said about it)."""
    reviewed = git(root, "rev-parse", "--verify", "-q", f"{sha}^{{commit}}", check=False).strip()
    if not reviewed or git(root, "merge-base", reviewed, head, check=False).strip() != reviewed:
        return 0
    return int(git(root, "rev-list", "--count", "--first-parent", f"{reviewed}..{head}").strip())


def specs_set_approved(edits: list[tuple[str, str | None, str, str]]) -> set[str]:
    """The specs a covered fix list sets to `Approved` (SPEC-0032 rule 5)."""
    found = set()
    for path, _, _, new in edits:
        match = SPEC_FILE.fullmatch(path)
        if match and new == "Approved":
            found.add(f"SPEC-{match.group(1)}")
    return found


def check(
    root: Path, comments: Path, head: str, author: str | None = None, reviews: Path | None = None
) -> int:
    authors = counted_authors(verdict_authors(root), author)
    items = comments_of(comments)
    covered = covered_fix_list(latest_verdict_body(items, authors))
    if covered is not None:
        sha, edits = covered
        flipped = specs_set_approved(edits)
        waiting = flipped - person_approvals(
            items,
            comments_of(reviews) if reviews else [],
            spec_approvers(root),
            flipped,
            agent_apps(root),
        )
        if waiting:
            raise CheckError(
                "rule 5: a spec set to Approved has no Approve line by an account in spec_approvers"
            )
        commit = git(root, "rev-parse", head).strip()
        parents = git(root, "rev-list", "--parents", "-n", "1", commit).split()[1:]
        if len(parents) == 1 and parents[0].startswith(sha):
            files_ok, bad = final_commit_problems(root, parents[0], commit, edits)
            moded = git(root, "diff", "--summary", parents[0], commit).strip()
            if not files_ok or bad or moded:
                raise CheckError("rule 3: the commit is not exactly the named status lines")
        elif commits_past(root, sha, commit) >= 2:
            raise CheckError("rule 7: the head is two or more commits past the reviewed commit")
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    opts = dict(zip(args[::2], args[1::2], strict=False))
    known = {"--comments", "--reviews", "--head", "--author", "--draft"}
    if len(args) % 2 or not set(opts) <= known:
        print(USAGE)
        return 2
    if opts.get("--draft") == "true":  # SPEC-0033 rule 2: a draft is ignored until it is ready
        print("skipped (draft pull request)")
        return 0
    if "--comments" not in opts:
        print("skipped (no comments file)")
        return 0
    root = repo_root()
    return run(
        NAME,
        lambda: check(
            root,
            Path(opts["--comments"]),
            opts.get("--head", "HEAD"),
            opts.get("--author"),
            Path(opts["--reviews"]) if "--reviews" in opts else None,
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
