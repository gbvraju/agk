"""Fail when a protected path changes without an ADR in the same change set that names its class.

Brief #545 (ADR-0271): with the pull request body (`--body FILE`, or the file that `AGK_PR_BODY`
names), a change set that no ADR of its own covers also passes on one `Covered-by: ADR-nnnn` line
naming an ADR that is Accepted on the merge base, names every changed class, and has a
`Requirements:` entry that the body's `Advances:` line names. It never covers `constitution/`,
`.github/workflows/`, `config/reviewers.yaml`, the ruleset (`kit/templates/ruleset.json`) or
`.github/CODEOWNERS`. Messages name the rule or the class, never a value.

Brief #601 (ADR-0293): a `Covered-by:` ADR whose file still says `Proposed` counts as Accepted when
a SPEC-0021 rule 3a record of it on the merge base is verified by its Final comment among the
comments of `--comments FILE` (the workflow's `Record comments` step), or, without the option, of
the file `AGK_RECORD_COMMENTS` names (merge_cleared.py's after-merge run and prepush, amendment
122); without either, while such a record exists, the check fails closed and names the option.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    REQ_ID,
    STATUS_LINE,
    CheckError,
    base_arg,
    base_context,
    changed_files,
    changed_lines,
    final_records,
    git,
    matches,
    read_list,
    repo_root,
    run,
    show,
)

NAME = "protected-changes"
LIST_PATH = "config/protected-paths.txt"
STATUS_ONLY_FILE = "docs/requirements.md"
COVERED_BY = "Covered-by:"
COVERED_FORM = re.compile(r"Covered-by: ADR-(\d{4})")
# Paths a `Covered-by:` line never covers: each needs an ADR in the same PR (ADR-0271).
OWN_ADR = (
    "constitution/",
    ".github/workflows/",
    "config/reviewers.yaml",
    "kit/templates/ruleset.json",
    ".github/CODEOWNERS",
)


def is_adr(path: str, status: str) -> bool:
    return (
        path.startswith("docs/adr/")
        and path.endswith(".md")
        and path != "docs/adr/TEMPLATE.md"
        and status in ("A", "M")
    )


def covering_adrs(root, mb, changed: dict[str, str], classes: list[str]) -> list[str]:
    """ADRs added or modified (not Status-only) whose text names every changed class."""
    found = []
    for path, status in sorted(changed.items()):
        if not is_adr(path, status):
            continue
        if status == "M":
            lines = changed_lines(root, mb, path)
            if all(ln[1:].startswith("- Status:") for ln in lines):
                continue
        text = (root / path).read_text(encoding="utf-8")
        if all(entry in text for entry in classes):
            found.append(path)
    return found


def body_text(argv: list[str] | None) -> str | None:
    """The pull request body from `--body FILE` or the file `AGK_PR_BODY` names, else None."""
    args = list(sys.argv[1:] if argv is None else argv)
    path = None
    if "--body" in args:
        i = args.index("--body")
        if i + 1 >= len(args):
            raise CheckError("--body needs a value")
        path = args[i + 1]
    elif os.environ.get("AGK_PR_BODY"):
        path = os.environ["AGK_PR_BODY"]
    if path is None:
        return None
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckError("cannot read the PR body file (option: --body or AGK_PR_BODY)") from exc


def first_field(text: str, label: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(label):
            return line[len(label) :].strip()
    return None


def own_status(text: str) -> str | None:
    """The value of the ADR's own first `- Status:` line."""
    for line in text.splitlines():
        m = STATUS_LINE.match(line)
        if m:
            return m.group(1)
    return None


RECORD_COMMENTS = "AGK_RECORD_COMMENTS"  # the comments file without --comments (amendment 122)
NOT_ACCEPTED = f"the '{COVERED_BY}' ADR is not '- Status: Accepted' on the merge base"


def final_accept_problems(root, mb, number: str, comments_file: str | None) -> list[str]:
    """[] when a rule 3a record of ADR NUMBER in the merge base's history is verified by its Final
    comment in COMMENTS_FILE (brief #601, ADR-0293); else why the ADR does not count as Accepted.
    Without the file, while such a record exists, it fails closed and names the option. The
    readers are kit-only, so a project, which does not have them, keeps ADR-0271's rule."""
    try:
        import check_adrs  # noqa: PLC0415 - kit-only reader of the records
    except ImportError:
        return [NOT_ACCEPTED]
    if number not in final_records(root, mb):
        return [NOT_ACCEPTED]
    if comments_file is None:
        return [f"'{COVERED_BY}': {check_adrs.NO_COMMENTS}"]
    try:
        verified = check_adrs.verified_records(root, mb, check_adrs.read_comments(comments_file))
    except CheckError:
        return [NOT_ACCEPTED]
    return [] if number in verified else [NOT_ACCEPTED]


def covered_by_problems(
    root,
    mb,
    body: str | None,
    changed: dict[str, str],
    classes: list[str],
    comments_file: str | None = None,
) -> list[str] | None:
    """None when the body has no `Covered-by:` line; [] when it covers; else what is missing."""
    if body is None:
        return None
    lines = [ln.strip() for ln in body.splitlines() if ln.startswith(COVERED_BY)]
    if not lines:
        return None
    if len(lines) != 1:
        return [f"the body needs exactly one '{COVERED_BY}' line, it has {len(lines)}"]
    form = COVERED_FORM.fullmatch(lines[0])
    if not form:
        return [f"the '{COVERED_BY}' line must be '{COVERED_BY} ADR-nnnn'"]
    problems = [
        f"'{COVERED_BY}' never covers '{x}': it needs an ADR in the same PR"
        for x in OWN_ADR
        if any(matches(p, x) for p in changed)
    ]
    number = form.group(1)
    names = [
        n
        for n in git(root, "ls-tree", "--name-only", mb, "docs/adr/").splitlines()
        if Path(n).name.startswith(f"{number}-") and n.endswith(".md")
    ]
    text = show(root, mb, names[0]) if len(names) == 1 else None
    if text is None:
        problems.append(f"the '{COVERED_BY}' ADR is not one file of docs/adr/ on the merge base")
        return problems
    if changed.get(names[0]) == "D":
        problems.append(f"the '{COVERED_BY}' ADR is deleted or renamed in the change set")
    if own_status(text) != "Accepted":
        problems += final_accept_problems(root, mb, number, comments_file)
    for entry in classes:
        if f"`{entry}`" not in text:
            problems.append(
                f"protected path class '{entry}' is not named in backticks "
                f"by the '{COVERED_BY}' ADR"
            )
    reqs = set(REQ_ID.findall(first_field(text, "- Requirements:") or ""))
    advances = set(REQ_ID.findall(first_field(body, "Advances:") or ""))
    if not reqs & advances:
        problems.append(
            f"no requirement of the '{COVERED_BY}' ADR's 'Requirements:' line is in 'Advances:'"
        )
    return problems


def comments_arg(argv: list[str] | None) -> str | None:
    """The file of `--comments FILE`: the Final comments of the base's records; without the
    option, the file that `AGK_RECORD_COMMENTS` names (the after-merge run of merge_cleared.py and
    prepush, amendment 122, brief #601); else None."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--comments" not in args:
        return os.environ.get(RECORD_COMMENTS) or None
    i = args.index("--comments")
    if i + 1 >= len(args):
        raise CheckError("--comments needs a value")
    return args[i + 1]


def release_pull_request(root, mb, comments_file: str | None = None) -> bool:
    """A valid release pull request of SPEC-0028 needs no ADR: it changes only the release files,
    and the release check passes, given the Final comments of COMMENTS_FILE (SPEC-0021 rule 3a;
    an unreadable file is no exemption). That check is kit-only, so a project, which does not
    have it, has no exemption."""
    try:
        import check_adrs  # noqa: PLC0415 - kit-only reader of the comments
        import check_release  # noqa: PLC0415 - kit-only, absent from an installed copy
    except ImportError:
        return False
    try:
        comments = check_adrs.read_comments(comments_file)
    except CheckError:
        return False
    return check_release.valid_release(root, mb, comments)


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    mb = base_context(root, NAME, base_arg(argv))
    if mb is None:
        return 0
    listing = show(root, mb, LIST_PATH)
    if listing is None:
        list_file = root / LIST_PATH
        if not list_file.is_file():
            raise CheckError(f"{LIST_PATH} is missing")
        listing = list_file.read_text(encoding="utf-8")
    entries = read_list(listing)
    changed = changed_files(root, mb)

    classes: list[str] = []
    for path, status in sorted(changed.items()):
        for entry in entries:
            if not matches(path, entry):
                continue
            if path == STATUS_ONLY_FILE and status == "M":
                lines = changed_lines(root, mb, path)
                if lines and all(ln[1:].startswith("- Status:") for ln in lines):
                    break
            if entry not in classes:
                classes.append(entry)
            break

    if not classes:
        print(f"ok {NAME}")
        return 0
    if release_pull_request(root, mb, comments_arg(argv)):
        print(f"ok {NAME} (a release pull request)")
        return 0
    if covering_adrs(root, mb, changed, classes):
        print(f"ok {NAME} (protected change covered by an ADR)")
        return 0
    problems = covered_by_problems(root, mb, body_text(argv), changed, classes, comments_arg(argv))
    if problems == []:
        print(f"ok {NAME} (protected change covered by an Accepted ADR named in '{COVERED_BY}')")
        return 0
    for problem in problems or []:
        print(f"FAIL {NAME}: {problem}")
    for entry in classes:
        print(
            f"FAIL {NAME}: protected path class '{entry}' changed without an ADR that names it "
            "(added or modified, not a Status-only edit)"
        )
    return 1


if __name__ == "__main__":
    sys.exit(run(NAME, main))
