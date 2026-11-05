"""ADR format; Accepted ADRs change only their Status line relative to the base.

An ADR that a squash message line `ADR-nnnn Accepted (Final <comment id>)` in the base's history
records is Accepted too (SPEC-0021 rule 3a, brief 557), whatever its file says until the release
pull request flips it. `check_adrs.py --pending --comments FILE` prints, one path a line, each such
ADR whose file still says `Proposed` and whose record its Final comment in FILE verifies (the
comments as `gh api repos/{repo}/issues/comments/<id>` answers): the flips the release pull request
makes. A record that FILE does not verify is not counted; without FILE, while a record exists, it
fails closed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    STATUS_LINE,
    CheckError,
    accepted_by_final,
    base_arg,
    changed_files,
    changed_lines,
    covered_fix_list,
    final_accepts,
    final_records,
    git,
    merge_base,
    repo_root,
    resolve_base,
    run,
    show,
)

NAME = "adrs"
STATUSES = ("Proposed", "Accepted", "Superseded", "Rejected")
FIELDS = ("Status", "Date", "Deciders", "Related", "Requirements")
SECTIONS = ("Context", "Decision", "Consequences", "Residual")
FILE_RE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
TITLE_RE = re.compile(r"^# ADR-(\d{4}): \S")
FIELD_RE = re.compile(r"^- ([A-Za-z]+):\s*(.*?)\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
AMENDS_RE = re.compile(r"^ADR-(\d{4})$")


def status_of(text: str) -> str | None:
    for line in text.splitlines():
        m = STATUS_LINE.match(line)
        if m:
            return m.group(1)
    return None


def final_record_verified(
    path: str, record: tuple[int, int], comment: dict | None, authors: list[str] | None
) -> bool:
    """Whether COMMENT (`repos/{repo}/issues/comments/<id>`) is the record's Final: the same id, on
    the record's pull request, by a listed verdict author, a covered fix list whose `Final:` lines
    accept PATH (rule 3a). A copied squash message cannot pass it."""
    if not isinstance(comment, dict) or comment.get("id") != record[1]:
        return False
    user = comment.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    if not authors or login not in authors:
        return False
    if not str(comment.get("issue_url") or "").endswith(f"/issues/{record[0]}"):
        return False
    covered = covered_fix_list(str(comment.get("body") or ""))
    return covered is not None and path in (final_accepts(covered[1]) or [])


NO_COMMENTS = (
    "rule 3a: a Final record is counted only once its comment verifies it; "
    "give the Final comments with --comments"
)


def record_authors(root: Path) -> list[str]:
    """The accounts whose Final may accept an ADR: `conductor_accounts` when listed (the accounts
    merge_cleared.py takes a verdict from, SPEC-0039 rule 3), else the verdict authors."""
    from reviewers import CONFIG, conductors_of, parse, verdict_authors

    try:
        listed = conductors_of(parse((root / CONFIG).read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, CheckError):
        listed = []
    return listed or verdict_authors(root)


def verified_records(root: Path, ref: str, comments: list[dict] | None) -> set[str]:
    """The ADR numbers that a record in REF's history accepts and that its Final comment, among
    COMMENTS, verifies (`final_record_verified`); a CheckError without COMMENTS while a record
    exists (fail closed: a copied squash message cannot accept an ADR)."""
    records = final_records(root, ref)
    if not records:
        return set()
    if comments is None:
        raise CheckError(NO_COMMENTS)
    by_id = {c.get("id"): c for c in comments}
    authors = record_authors(root)
    names = git_names(root, ref)
    return {
        number
        for number, record in records.items()
        if any(
            final_record_verified(f"docs/adr/{name}", record, by_id.get(record[1]), authors)
            for name in names
            if name.startswith(f"{number}-")
        )
    }


def git_names(root: Path, ref: str) -> list[str]:
    """The file names of docs/adr/ in REF."""
    out = git(root, "ls-tree", "-z", "--name-only", f"{ref}:docs/adr", check=False)
    return [name for name in out.split("\0") if FILE_RE.match(name)]


def read_comments(path: str | None) -> list[dict] | None:
    """The comments of FILE (any shape `check_final_clearance.comments_of` reads), or None."""
    if path is None:
        return None
    from check_final_clearance import comments_of

    return comments_of(Path(path))


def pending(root: Path, files: list[Path], comments: list[dict] | None = None) -> int:
    """Print each ADR accepted by a verified Final record whose file still says Proposed."""
    try:
        recorded = verified_records(root, "HEAD", comments)
    except CheckError as err:
        print(f"FAIL {NAME}: {err}")
        return 1
    for p in files:
        m = FILE_RE.match(p.name)
        if m and m.group(1) in recorded and status_of(p.read_text(encoding="utf-8")) == "Proposed":
            print(p.relative_to(root).as_posix())
    return 0


def validate(name: str, text: str, known: set[str]) -> list[str]:
    problems: list[str] = []
    fm = FILE_RE.match(name)
    if not fm:
        return [f"{name}: file name must be NNNN-slug.md"]
    lines = text.splitlines()
    tm = TITLE_RE.match(lines[0]) if lines else None
    if not tm:
        problems.append(f"{name}: first line must be '# ADR-NNNN: Title'")
    elif tm.group(1) != fm.group(1):
        problems.append(f"{name}: title number differs from file number")
    fields: dict[str, str] = {}
    for line in lines[1:]:
        m = FIELD_RE.match(line)
        if m:
            fields.setdefault(m.group(1), m.group(2))
    for field in FIELDS:
        if not fields.get(field):
            problems.append(f"{name}: missing field '{field}'")
    if fields.get("Status") and fields["Status"] not in STATUSES:
        problems.append(f"{name}: Status is not one of {', '.join(STATUSES)}")
    if fields.get("Date") and not DATE_RE.match(fields["Date"]):
        problems.append(f"{name}: Date must be YYYY-MM-DD")
    if "Amends" in fields:
        am = AMENDS_RE.match(fields["Amends"])
        if not am or am.group(1) not in known:
            problems.append(f"{name}: Amends must name an existing ADR as ADR-NNNN")
    for section in SECTIONS:
        if f"## {section}" not in lines:
            problems.append(f"{name}: missing section '## {section}'")
    return problems


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    adr_dir = root / "docs" / "adr"
    files = (
        sorted(p for p in adr_dir.glob("*.md") if p.name != "TEMPLATE.md")
        if adr_dir.is_dir()
        else []
    )
    known = {m.group(1) for p in files if (m := FILE_RE.match(p.name))}
    args = sys.argv[1:] if argv is None else argv
    if "--pending" in args:
        at = args.index("--comments") + 1 if "--comments" in args else None
        try:
            comments = read_comments(args[at] if at is not None and at < len(args) else None)
        except CheckError as err:
            print(f"FAIL {NAME}: {err}")
            return 1
        return pending(root, files, comments)
    problems: list[str] = []

    numbers: dict[str, str] = {}
    for p in files:
        m = FILE_RE.match(p.name)
        if m and m.group(1) in numbers:
            problems.append(f"{p.name}: number also used by {numbers[m.group(1)]}")
        elif m:
            numbers[m.group(1)] = p.name
        problems += validate(p.name, p.read_text(encoding="utf-8"), known)

    base = resolve_base(root, base_arg(argv))
    if base is None:
        print(f"{NAME}: no base ref available outside CI; immutability check skipped")
    else:
        mb = merge_base(root, base)
        recorded = accepted_by_final(root, mb)
        for path, status in sorted(changed_files(root, mb).items()):
            if not path.startswith("docs/adr/") or path.endswith("/TEMPLATE.md"):
                continue
            old = show(root, mb, path)
            number = FILE_RE.match(path.rsplit("/", 1)[-1])
            final = bool(number) and number.group(1) in recorded  # rule 3a
            if old is None or (status_of(old) != "Accepted" and not final):
                continue
            if status == "D":
                problems.append(f"{path}: an Accepted ADR cannot be deleted")
            elif status == "M" and not all(
                ln[1:].startswith("- Status:") for ln in changed_lines(root, mb, path)
            ):
                problems.append(f"{path}: an Accepted ADR may change only its Status line")
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if not problems:
        print(f"ok {NAME} ({len(files)} ADRs)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
