"""Spec lifecycle: Approved specs change by amendment; an implementation advances an Approved spec.

(1) A PR that modifies or deletes a spec whose base version is `Status: Approved` fails unless it
also adds or modifies a `docs/runs/proposed-spec-amendments-*.md` file that names the spec's path.
A Draft spec, a new spec and the Draft -> Approved flip pass.
(2) Rule a (SPEC-0013 rule 23), with `--body FILE|-`: an implementation PR (its diff touches a path
outside `docs/` and `.github/ISSUE_TEMPLATE/`) must name, on its `Advances:` line, only requirements
that an Approved spec names; a requirement that no spec names and an ADR names is exempt.
(3) With `--comments FILE [--reviews FILE] [--runs FILE]` (saved comments, reviews and
`pull_request` workflow runs of the pull request; SPEC-0032 rule 5): a spec whose Approved status
line is added or changed in the diff, through a `Final:` line or an ordinary commit, needs an
approval by an account in `spec_approvers`: a first line `Approve: <sha> SPEC-<n>`, a first line
`Approve: SPEC-<n>` (the text at the `head_sha` of the latest run created before the comment,
GitHub's time, never a commit date), or a review in state `APPROVED` (at its own `commit_id`, for
the one spec the pull request sets Approved or the one its first line names). The spec file at the
head must equal the approved text apart from its status line. Without `--comments` the approval is
not checked (a local run has no comments).
(4) Rule b (SPEC-0013 rule 24): a spec whose Approved status line is added or changed in the diff
has no open `Q-` id (a table row or list item in the spec or its notes file that has no row in the
notes' `## Rulings` section and no `<id> ruled` row in the decisions log).
Messages name the spec path, the requirement or the question id, never content.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from check_final_clearance import comments_of
from check_pr_body import field
from common import (
    REQ_ID,
    STATUS_LINE,
    CheckError,
    base_arg,
    base_context,
    changed_files,
    changed_lines,
    find_questions,
    git,
    read_text,
    repo_root,
    run,
    show,
)
from reviewers import approval_shas, spec_approvers

NAME = "specs"
SPEC_PREFIX = "docs/specs/"
AMENDMENT = re.compile(r"^docs/runs/proposed-spec-amendments-[^/]+\.md$")
SPEC_FILE = re.compile(r"^docs/specs/(\d{4})-[^/]+\.md$")
REQUIREMENTS_LINE = re.compile(r"(?m)^- Requirements:\s*(.*?)\s*$")
ASKED = re.compile(r"^\s*[|-]\s*(Q-[A-Z0-9]+-[0-9]+)")
DOC_ONLY = ("docs/", ".github/ISSUE_TEMPLATE/")


def status_of(text: str) -> str | None:
    for line in text.splitlines():
        match = STATUS_LINE.match(line)
        if match:
            return match.group(1)
    return None


def body_arg(argv: list[str] | None) -> str | None:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--body" not in args:
        return None
    i = args.index("--body")
    if i + 1 >= len(args):
        raise CheckError("--body needs a value")
    value = args[i + 1]
    try:
        if value == "-":
            return sys.stdin.read()
        with open(value, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        raise CheckError("cannot read the PR body file (option --body)") from None


def file_arg(argv: list[str] | None, name: str) -> str | None:
    args = list(sys.argv[1:] if argv is None else argv)
    if name not in args:
        return None
    i = args.index(name)
    if i + 1 >= len(args):
        raise CheckError(f"{name} needs a value")
    return args[i + 1]


def without_status(text: str) -> str:
    return re.sub(r"(?m)^- Status:.*$", "- Status: -", text, count=1)


def unchanged_since(root, sha: str, path: str) -> bool:
    """The spec at the head equals the spec at `sha` apart from its status line."""
    full = git(root, "rev-parse", "--verify", "-q", f"{sha}^{{commit}}", check=False).strip()
    old = show(root, full, path) if full else None
    new = read_text(root, path)
    if old is None or new is None:
        return False
    return without_status(old) == without_status(new)


def requirements_of(root, folder: str) -> dict[str, tuple[list[str], str | None]]:
    """Path -> (the requirement ids on its `Requirements:` line, its status) for docs/<folder>/."""
    found: dict[str, tuple[list[str], str | None]] = {}
    base = root / "docs" / folder
    for path in sorted(base.glob("*.md")) if base.is_dir() else []:
        if path.name == "TEMPLATE.md":
            continue
        rel = path.relative_to(root).as_posix()
        text = read_text(root, rel) or ""
        line = REQUIREMENTS_LINE.search(text)
        found[rel] = (REQ_ID.findall(line.group(1)) if line else [], status_of(text))
    return found


def advances_failures(root, changed: dict[str, str], body: str) -> list[str]:
    """Rule a: the requirements an implementation PR advances, each named by an Approved spec."""
    if all(path.startswith(DOC_ONLY) for path in changed):
        return []
    line = field(body, "Advances:") or ""
    specs, adrs = requirements_of(root, "specs"), requirements_of(root, "adr")
    failures = []
    for req in dict.fromkeys(REQ_ID.findall(line)):
        named = [status for ids, status in specs.values() if req in ids]
        approved = "Approved" in named
        exempt = not named and any(req in ids for ids, _ in adrs.values())
        if not approved and not exempt:
            failures.append(f"{req}: no Approved spec names it")
    return failures


def spec_number(path: str) -> str:
    match = SPEC_FILE.match(path)
    return match.group(1) if match else ""


def open_questions(root, spec_path: str) -> list[str]:
    """Rule b: ids asked in the spec or its notes file with no ruling."""
    notes = f"docs/runs/spec-{spec_number(spec_path)}-notes.md"
    asked: list[str] = []
    for rel in (spec_path, notes):
        for line in (read_text(root, rel) or "").splitlines():
            match = ASKED.match(line)
            if match and match.group(1) not in asked:
                asked.append(match.group(1))
    rulings = section_lines(read_text(root, notes) or "", "Rulings")
    state = {q["id"]: q["ruled"] for q in find_questions(root) or []}
    return [
        q
        for q in asked
        if state.get(q) is not True
        and not any(
            re.match(r"\s*\|\s*" + re.escape(q) + r"(?![A-Za-z0-9-])", ln) for ln in rulings
        )
    ]


def section_lines(text: str, heading: str) -> list[str]:
    """The lines under the first `## <heading>` (the heading may continue: `## Rulings (date)`)."""
    found: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip() == f"## {heading}" or line.startswith(f"## {heading} ")
        elif inside:
            found.append(line)
    return found


def flipped_specs(root, mb: str, changed: dict[str, str]) -> dict[str, str]:
    """SPEC-<n> -> path, for each spec whose Approved status line is added or changed."""
    found = {}
    for path, state in sorted(changed.items()):
        if not SPEC_FILE.match(path) or state not in ("A", "M") or not (root / path).is_file():
            continue
        if status_of(read_text(root, path) or "") != "Approved":
            continue
        if state == "M" and not any(
            ln.startswith("+") and STATUS_LINE.match(ln[1:]) for ln in changed_lines(root, mb, path)
        ):
            continue
        found[f"SPEC-{spec_number(path)}"] = path
    return found


def approval_failures(
    root, mb: str, changed: dict[str, str], approvals: dict[str, list[str]] | None = None
) -> list[str]:
    failures = []
    noted = False
    for number, path in flipped_specs(root, mb, changed).items():
        failures += [f"{number}: {q} has no ruling" for q in open_questions(root, path)]
        if approvals is None:
            if not noted:
                print(f"{NAME}: no comments file; an approval of a spec is not checked")
                noted = True
        elif not approvals.get(number):
            failures.append(f"{number}: rule 5: no Approve line by an account in spec_approvers")
        elif not any(unchanged_since(root, sha, path) for sha in approvals[number]):
            failures.append(f"{number}: rule 5: the spec changed after the approved sha")
    return failures


def runs_of(root, path: str | None) -> list[dict]:
    """The saved `pull_request` workflow runs of the pull request (`actions/runs`, pages or not),
    only those whose head is in the history of the head, so that a run of another pull request of
    the same branch name pins nothing. Unreadable means none: a short line then counts for nothing
    (SPEC-0032 rule 5, build (g))."""
    if path is None:
        return []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    found: list[dict] = []
    decoder, at = json.JSONDecoder(), 0
    try:
        while at < len(text):
            if text[at].isspace():
                at += 1
                continue
            value, at = decoder.raw_decode(text, at)
            pages = value if isinstance(value, list) else [value]
            for page in pages:
                items = page.get("workflow_runs") if isinstance(page, dict) else None
                found += [x for x in items or [] if isinstance(x, dict)]
                if isinstance(page, dict) and "head_sha" in page:  # one run, not a page of runs
                    found.append(page)
    except ValueError:
        return []
    return [x for x in found if in_history(root, x.get("head_sha"))]


def in_history(root, sha) -> bool:
    """The commit `sha` is the head or one of its ancestors."""
    if not isinstance(sha, str) or not sha:
        return False
    commit = git(root, "rev-parse", "--verify", "-q", f"{sha}^{{commit}}", check=False).strip()
    return bool(commit) and commit == git(root, "merge-base", commit, "HEAD", check=False).strip()


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    body = body_arg(argv)
    mb = base_context(root, NAME, base_arg(argv))
    if mb is None:
        return 0
    changed = changed_files(root, mb)
    amendments = [
        p
        for p, s in changed.items()
        if AMENDMENT.match(p) and s in ("A", "M") and (root / p).is_file()
    ]
    texts = [(root / p).read_text(encoding="utf-8") for p in amendments]
    failures = []
    for path in sorted(changed):
        if not (path.startswith(SPEC_PREFIX) and path.endswith(".md")):
            continue
        old = show(root, mb, path)
        if old is None or status_of(old) != "Approved":
            continue
        if not any(path in text for text in texts):
            failures.append(path)
    messages = [
        f"approved spec '{path}' changed without a proposed-spec-amendments file that names it"
        for path in failures
    ]
    comments = file_arg(argv, "--comments")
    approvals = None
    if comments is not None:
        reviews = file_arg(argv, "--reviews")
        runs = file_arg(argv, "--runs")
        approvals = approval_shas(
            comments_of(Path(comments)),
            comments_of(Path(reviews)) if reviews else [],
            spec_approvers(root),
            runs_of(root, runs),
            set(flipped_specs(root, mb, changed)),
        )
    messages += approval_failures(root, mb, changed, approvals)
    if body is None or not body.strip():
        print(f"{NAME}: no pull request body; the lifecycle rule for Advances is skipped")
    else:
        messages += advances_failures(root, changed, body)
    for message in messages:
        print(f"FAIL {NAME}: {message}")
    if not messages:
        print(f"ok {NAME}")
    return 1 if messages else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
