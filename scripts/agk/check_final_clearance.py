"""A fix list that names only the final commit clears that commit in advance (SPEC-0021).

    python3 check_final_clearance.py [--comments FILE] [--reviews FILE] [--head SHA]
        [--author LOGIN] [--draft VALUE]

When the latest verdict by a listed author is a covered fix list (`Verdict: fix list <sha>`, `Final:
<path> <old> -> <new>` lines, no numbered item) and the head is the one commit after its reviewed
sha, the commit must change exactly the named status lines (one that also sets the `Chosen` line
of a stack ADR fails saying that line is set by an ordinary commit, brief 274); a head two or more
commits past the reviewed sha (counted on the first-parent line) fails (SPEC-0030 rule 7).
A covered fix list whose sha is the head and whose every `Final:` line accepts an ADR is the
acceptance itself (rule 3a, brief 557): each named ADR must be one that the pull request adds or
changes (`git diff` from the merge base) and `Proposed` at the head, and no status commit follows; a
stack-options ADR keeps rule 3.
A numbered item of the latest fix list that does not end with `(rule: <file> <n>)` or `(rule: none)`
is a warning, and a failure from the date in `rule_tags_from` of agk.toml on (brief 647, ADR-0310).
Each row that the pull request adds to `docs/design/signoffs.md` (absent at the merge base with the
default branch) counts only with the `Approve: design|inventory` line of an account in
`spec_approvers` naming its head and, for a `design` row, its version, `v<n>` or an imported `i<n>`
(SPEC-0037 amendment 161 item 4, ADR-0449), and each commit that adds a row (absent at every
parent) changes only that file (SPEC-0037 rules 3 and 9, brief #459).
Anything else passes unchecked. With `review_mode = "solo"` in agk.toml the one listed person's
confirmation counts as its verdict and its `Approve:` lines (brief 277,
`reviewers.confirmed_comments`). Without
`--comments` it prints `skipped (no comments file)` and passes. With two or more listed
authors the verdicts of `--author`, the pull request's own author, do not count (SPEC-0025 rule 4).
Git and the file only: no network, no model. Messages name the rule, never a value.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_signoff
from check_adrs import status_of
from common import (
    CheckError,
    agent_apps,
    covered_fix_list,
    final_accepts,
    final_commit_problems,
    fix_items,
    git,
    item_tag,
    repo_root,
    resolve_base,
    rule_tags_from,
    run,
    show,
    utf8_output,
)
from metrics import counted_authors, latest_verdict_body
from reviewers import (
    confirmed_comments,
    design_approvals,
    person_approvals,
    solo_person,
    spec_approvers,
    verdict_authors,
)

NAME = "final-clearance"
SPEC_FILE = re.compile(r"docs/specs/(\d{4})-[^/]+\.md")
STACK_ADR = re.compile(r"docs/adr/\d{4}-stack-options\.md")
CHOSEN_LINE = re.compile(r"\s*\d+\.\s+\*\*Chosen\*\*")
STACK_CHOSEN = "rule 3: a stack's Chosen line is set by an ordinary commit, not a Final commit"
ACCEPT_NOT_PROPOSED = "rule 3a: a Final line accepts only an ADR that is Proposed at the head"
ACCEPT_NOT_CHANGED = (
    "rule 3a: a Final line accepts only an ADR that the pull request adds or changes; "
    "this pull request does not change a named path of docs/adr/"
)
UNTAGGED = (
    "brief 647: {n} fix-list {item} no rule; end each numbered item with (rule: <file> <n>) "
    "or (rule: none) (setting: rule_tags_from)"
)
SIGNOFF_NO_LINE = (
    "rule 9: a design sign-off row has no Approve line by an account in spec_approvers"
)
SIGNOFF_MORE = f"rule 9: the sign-off commit changes more than {design_signoff.SIGNOFFS}"
NO_BASE = "rule 3a: no base ref resolves, so the pull request's files cannot be read"
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


def sets_stack_chosen(root: Path, first: str, second: str) -> bool:
    """Whether the commit changes the `Chosen` line of a stack ADR (brief 274 answer 3)."""
    names = git(root, "diff", "-z", "--name-only", "--no-renames", first, second).split("\0")
    for path in filter(STACK_ADR.fullmatch, names):
        diff = git(root, "diff", "-U0", "--no-renames", first, second, "--", path)
        if any(CHOSEN_LINE.match(ln[1:]) for ln in diff.splitlines() if ln[:1] in "+-"):
            return True
    return False


def pull_request_files(root: Path, commit: str) -> set[str]:
    """The paths that the pull request adds or changes: `git diff` from the merge base of the
    default branch to COMMIT (rule 3a). Fails closed when no base resolves."""
    base = resolve_base(root, None)
    if base is None:
        raise CheckError(NO_BASE)
    mb = git(root, "merge-base", base, commit, check=False).strip()
    if not mb:
        raise CheckError(NO_BASE)
    out = git(root, "diff", "-z", "--name-only", "--no-renames", "--diff-filter=AM", mb, commit)
    return set(filter(None, out.split("\0")))


def specs_set_approved(edits: list[tuple[str, str | None, str, str]]) -> set[str]:
    """The specs a covered fix list sets to `Approved` (SPEC-0032 rule 5)."""
    found = set()
    for path, _, _, new in edits:
        match = SPEC_FILE.fullmatch(path)
        if match and new == "Approved":
            found.add(f"SPEC-{match.group(1)}")
    return found


def rule_tags(root: Path, body: str) -> None:
    """Brief 647 (ADR-0310): each numbered item of the latest fix list names the rule it enforces.
    An item with no tag is a warning, and a failure from the date in `rule_tags_from` on."""
    required = rule_tags_from(root)
    n = sum(1 for item in fix_items(body) if item_tag(item) is None)
    if not n:
        return
    message = UNTAGGED.format(n=n, item="item names" if n == 1 else "items name")
    if required is not None and datetime.now(UTC).date() >= required:
        raise CheckError(message)
    print(f"warning: {message.removeprefix('brief 647: ')}")


def signoff_rows_added(root: Path, commit: str) -> tuple[list[dict], str]:
    """(the sign-off rows the pull request adds, absent at its merge base with the default branch;
    that merge base). Fails closed when the head has rows and no base resolves."""
    at_head = _rows_at(root, commit)
    if not at_head:
        return [], ""
    base = resolve_base(root, None)
    mb = git(root, "merge-base", base, commit, check=False).strip() if base else ""
    if not mb:
        raise CheckError(NO_BASE)
    before = {_row_key(r) for r in _rows_at(root, mb)}
    return [r for r in at_head if _row_key(r) not in before], mb


def signoff_commits(root: Path, mb: str, commit: str) -> list[tuple[str, list[str]]]:
    """(each commit after the merge base that adds a row, absent at every parent; its parents)."""
    found = []
    for line in git(root, "rev-list", "--parents", f"{mb}..{commit}").splitlines():
        sha, *parents = line.split()
        keys = {_row_key(r) for r in _rows_at(root, sha)}
        for p in parents:
            keys -= {_row_key(r) for r in _rows_at(root, p)}
        if keys:
            found.append((sha, parents))
    return found


def _rows_at(root: Path, rev: str) -> list[dict]:
    text = show(root, rev, design_signoff.SIGNOFFS)
    return [] if text is None else design_signoff.parse_rows(text)


def _row_key(row: dict) -> tuple[str, ...]:
    return tuple(row[c] for c in design_signoff.COLUMNS)


def signoff_problems(root: Path, commit: str, items: list[dict]) -> None:
    """SPEC-0037 rules 3 and 9: a row the pull request adds needs the person's line on its head, and
    each commit adding a row changes only the sign-off record (compared with its first parent)."""
    added, mb = signoff_rows_added(root, commit)
    if not added:
        return
    given = design_approvals(items, spec_approvers(root), agent_apps(root))
    if any((r["kind"], r["version"], r["head"]) not in given for r in added):
        raise CheckError(SIGNOFF_NO_LINE)
    for sha, parents in signoff_commits(root, mb, commit):
        if not parents:
            continue
        names = git(root, "diff", "-z", "--name-only", "--no-renames", parents[0], sha)
        if set(filter(None, names.split("\0"))) - {design_signoff.SIGNOFFS}:
            raise CheckError(SIGNOFF_MORE)


def check(
    root: Path, comments: Path, head: str, author: str | None = None, reviews: Path | None = None
) -> int:
    authors = counted_authors(verdict_authors(root), author)
    items = comments_of(comments)
    items = confirmed_comments(items, agent_apps(root), solo_person(root))  # brief 277
    body = latest_verdict_body(items, authors)
    rule_tags(root, body)
    signoff_problems(root, git(root, "rev-parse", head).strip(), items)
    covered = covered_fix_list(body)
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
        accepts = final_accepts(edits)
        if commit.startswith(sha) and accepts is not None:
            changed = pull_request_files(root, commit)
            for path in accepts:  # rule 3a: the Final line is the acceptance; no commit follows
                if path not in changed:
                    raise CheckError(ACCEPT_NOT_CHANGED)
                if status_of(show(root, commit, path) or "") != "Proposed":
                    raise CheckError(ACCEPT_NOT_PROPOSED)
        elif len(parents) == 1 and parents[0].startswith(sha):
            files_ok, bad = final_commit_problems(root, parents[0], commit, edits)
            moded = git(root, "diff", "--summary", parents[0], commit).strip()
            if not files_ok or bad or moded:
                if sets_stack_chosen(root, parents[0], commit):
                    raise CheckError(STACK_CHOSEN)
                raise CheckError("rule 3: the commit is not exactly the named status lines")
        elif commits_past(root, sha, commit) >= 2:
            raise CheckError("rule 7: the head is two or more commits past the reviewed commit")
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
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
