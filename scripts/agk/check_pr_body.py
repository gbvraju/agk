"""PR body must carry `Advances: REQ-nnn` and a dated `Build-state row:` (file or stdin).

An optional `Behaviour:` line must be exactly `Behaviour: unchanged` (SPEC-0010 rule 18).

`--draft true` (the workflow passes the draft flag of the pull request) skips the check until
the pull request is marked ready for review (SPEC-0033 rule 2); any other value checks as before.

SPEC-0034 rule 9: `--issues FILE` is a saved copy of the repository's issues (a JSON list, as
`gh api repos/OWNER/REPO/issues` returns it); when it holds an issue labelled `agk-brief` (a pull
request does not count) the body needs `Brief: #n`, or `Brief: none (design)` for a change of
`docs/design/`, or `Brief: none (spec)` for a change of `docs/specs/` or `docs/requirements.md`
(brief #273), each with at most `docs/adr/`, `docs/runs/proposed-spec-amendments-*.md` and
`docs/runs/decisions-log.md` beside it and no other path: the changed files are read with git
from the base (`AGK_BASE`, as the other checks) to the work tree, and a base that does not
resolve fails the form. A body
whose `Build-state row:` sets a requirement to `done` needs `Closes #n`. SPEC-0036 rule 1: every
body that is not a draft has exactly one line `Summary: <one sentence>` of 1 to 120 characters, and
the message says which case found (missing, repeated with the count, empty, or too long with its
length; brief #237). Messages name the rule, never a value or a word of the body. Files and git
only."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    BEHAVIOUR_UNCHANGED,
    REQ_ID,
    CheckError,
    behaviour_lines,
    changed_files,
    merge_base,
    repo_root,
    resolve_base,
    run,
)

NAME = "pr-body"
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
USAGE = "usage: check_pr_body.py [--draft VALUE] [--issues FILE] [FILE|-]"
LINK = re.compile(r"#\d+")
DONE = re.compile(r"\bREQ-\d{3}\s+done\b", re.IGNORECASE)
SUMMARY = "Summary:"
SUMMARY_MAX = 120
NONE_FORMS = {
    "none (design)": ("docs/design/",),
    "none (spec)": ("docs/specs/", "docs/requirements.md"),
}
# Documents either form may also carry (the verdict on Q-273-1); never code.
NONE_SHARED = (
    "docs/adr/",
    "docs/runs/proposed-spec-amendments-*.md",
    "docs/runs/decisions-log.md",
)
NONE_RULE = (
    "rule 9: 'Brief: none (design)' is for a change of docs/design/, and 'Brief: none (spec)' "
    "for a "
    "change of docs/specs/ or docs/requirements.md, each with at most docs/adr/, "
    "docs/runs/proposed-spec-amendments-*.md and docs/runs/decisions-log.md beside (path classes)"
)


def field(text: str, label: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(label):
            return line[len(label) :].strip()
    return None


def has_brief(path: str) -> bool:
    """Whether the saved copy lists an `agk-brief` issue; an unreadable copy lists none."""
    try:
        with open(path, encoding="utf-8") as fh:
            issues = json.load(fh)
    except (OSError, ValueError):
        return False
    return isinstance(issues, list) and any(
        isinstance(i, dict)
        and "pull_request" not in i
        and any(isinstance(x, dict) and x.get("name") == "agk-brief" for x in i.get("labels") or [])
        for i in issues
    )


def path_in(path: str, entries: tuple[str, ...]) -> bool:
    """An entry ending `/` is a prefix, one with `*` a pattern within one folder, else a file."""
    for entry in entries:
        if entry.endswith("/") and path.startswith(entry):
            return True
        if "*" in entry and re.fullmatch("[^/]*".join(map(re.escape, entry.split("*"))), path):
            return True
        if path == entry:
            return True
    return False


def none_form_fits(form: str, changed: dict[str, str]) -> bool:
    """Whether a changed path is the form's own, and every other one is a shared document."""
    own = NONE_FORMS[form]
    return any(path_in(p, own) for p in changed) and all(
        path_in(p, own + NONE_SHARED) for p in changed
    )


def changed_now() -> dict[str, str] | None:
    """The changed files from the base to the work tree, or None when they cannot be read."""
    try:
        root = repo_root()
        base = resolve_base(root)
        return None if base is None else changed_files(root, merge_base(root, base))
    except CheckError:
        return None


def brief_problem(brief: str | None) -> str | None:
    if brief in NONE_FORMS:
        changed = changed_now()
        return None if changed is not None and none_form_fits(brief, changed) else NONE_RULE
    if brief is None or not re.fullmatch(LINK, brief):
        return "rule 9: 'Brief: #n' line is required (the repository has a brief)"
    return None


def summary_problem(summaries: list[str]) -> str | None:
    """What is wrong with the `Summary:` lines (SPEC-0036 rule 1): the case and a count, no text."""
    rule = "SPEC-0036 rule 1: "
    if not summaries:
        return rule + "the 'Summary:' line is missing"
    if len(summaries) > 1:
        return rule + f"there are {len(summaries)} 'Summary:' lines; exactly one is required"
    if not summaries[0]:
        return rule + "the 'Summary:' line is empty"
    if len(summaries[0]) > SUMMARY_MAX:
        return (
            rule
            + f"the text after 'Summary:' is {len(summaries[0])} characters; at most {SUMMARY_MAX}"
        )
    return None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    options: dict[str, str] = {}
    while args[:1] in (["--draft"], ["--issues"]):
        if len(args) < 2:
            raise CheckError(USAGE)
        options[args[0]], args = args[1], args[2:]
    if options.get("--draft") == "true":
        print("skipped (draft pull request)")
        return 0
    if len(args) > 1:
        raise CheckError(USAGE)
    try:
        if not args or args[0] == "-":
            text = sys.stdin.buffer.read().decode("utf-8")
        else:
            with open(args[0], encoding="utf-8") as fh:
                text = fh.read()
    except OSError as exc:
        raise CheckError("cannot read the PR body file") from exc
    problems = []
    advances = field(text, "Advances:")
    if advances is None or not REQ_ID.search(advances):
        problems.append("'Advances:' line with at least one REQ-nnn is required")
    row = field(text, "Build-state row:")
    if not row or not DATE.search(row):
        problems.append("'Build-state row:' line with a YYYY-MM-DD date is required")
    summaries = [x[len(SUMMARY) :].strip() for x in text.splitlines() if x.startswith(SUMMARY)]
    if problem := summary_problem(summaries):
        problems.append(problem)
    if "--issues" in options and has_brief(options["--issues"]):
        if problem := brief_problem(field(text, "Brief:")):
            problems.append(problem)
    if row and DONE.search(row):
        closes = field(text, "Closes")
        if closes is None or not re.fullmatch(LINK, closes):
            problems.append("rule 9: 'Closes #n' line is required (a requirement is set to done)")
    if any(line != BEHAVIOUR_UNCHANGED for line in behaviour_lines(text)):
        problems.append("'Behaviour:' must be 'unchanged'")
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if not problems:
        print(f"ok {NAME}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
