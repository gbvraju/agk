# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""ADR format; Accepted ADRs change only their Status line relative to the base.

An ADR that a squash message line `ADR-nnnn Accepted (Final <comment id>)` in the base's history
records is Accepted too (SPEC-0021 rule 3a, brief 557), whatever its file says until the release
pull request flips it. `check_adrs.py --pending --comments FILE` prints, one path a line, each such
ADR, recorded in HEAD's history or in that of the merge base with the base (brief #1370), whose
file still says `Proposed` and whose record its Final comment in FILE verifies (the comments as
`gh api repos/{repo}/issues/comments/<id>` answers): the flips the release pull request makes.
A record that FILE does not verify is not counted; without FILE, while a record exists, it fails
closed. `check_adrs.py --record-ids` prints the Final comment id of each record read in
HEAD's history, one a line, so that the governance workflow can fetch those comments; with
`--body FILE` only those a check will read: all for a release pull request, those of the ADRs a
`Covered-by:` line names, else none (brief #1181, ADR-0501).

A pull request merged by hand (brief #1738, ADR-0724) carries no record: `hand_merges` lists each
first-parent squash commit `(#n)` with one parent and no `MERGED_BY` line that adds or changes an
ADR the ref reads `Proposed`, and `lost_final` reads, from that pull request's comments, the Final
of its latest verdict by a record author that no record accepts (doctor's `lost-record` line).
`--pending --pulls FILE` (FILE holds the merged pull requests as `GET pulls/<n>` returns them) also
lists such an ADR, only when its Final comment in `--comments FILE` verifies, is the latest verdict
there, and the payload says `merged: true`, names that squash commit as `merge_commit_sha` and the
verdict's head as `head.sha`. Without `--pulls` nothing changes; a FILE that is not such a list is
refused naming the option.

In a sidecar only (SPEC-0041 rule 8, brief #1502), `check_adrs.py --comments FILE` also fails an ADR
whose status line moves to `Accepted` without the `Accept: <C> ADR-nnnn` line of the person's
terminal confirmation at a `<C>` where the ADR equals its text apart from its status line; without
`--comments`, or without a base, such a move fails rather than being skipped (Q-1502-1 answer (a)).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    MERGED_BY,
    SQUASH_SUBJECT,
    STATUS_LINE,
    CheckError,
    accepted_by_final,
    agent_apps,
    base_arg,
    changed_files,
    changed_lines,
    covered_fix_list,
    final_accepts,
    final_records,
    git,
    merge_base,
    personal_table,
    repo_root,
    resolve_base,
    run,
    show,
    utf8_output,
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


# --- a decision cleared on a pull request merged by hand (brief #1738, ADR-0724) --------------

PULLS = "--pulls"
BAD_PULLS = "--pulls must name a JSON list of pull requests as GET pulls/<n> returns them (option --pulls)"
SHA = re.compile(r"[0-9a-f]{40}")


def adr_paths(names: list[str]) -> list[str]:
    return [n for n in names if n.startswith("docs/adr/") and FILE_RE.match(n[len("docs/adr/") :])]


def hand_merges(root: Path, ref: str) -> list[tuple[int, str]]:
    """(pull request, commit) of each squash commit on REF's first-parent line, newest first, that
    merge_cleared.py did not make: one parent, a subject that ends `(#n)`, no `MERGED_BY` line, and
    a change to (or the addition of) an ADR that REF reads `Proposed`. Local git only."""
    out = git(
        root,
        "log",
        "--first-parent",
        "--name-only",
        "--format=%x1e%H%x1f%P%x1f%B%x1f",
        ref,
        "--",
        "docs/adr/",
        check=False,
    )
    found: list[tuple[int, str]] = []
    status: dict[str, str | None] = {}
    for record in out.split("\x1e")[1:]:
        parts = record.split("\x1f")
        if len(parts) < 4:
            continue
        sha, parents, message, names = parts[0], parts[1], parts[2], parts[3]
        lines = [ln.strip() for ln in message.strip().splitlines()]
        subject = SQUASH_SUBJECT.fullmatch(lines[0]) if lines else None
        if len(parents.split()) != 1 or subject is None or MERGED_BY in lines:
            continue
        for path in adr_paths(names.split()):
            if path not in status:
                status[path] = status_of(show(root, ref, path) or "")
            if status[path] == "Proposed":
                found.append((int(subject.group(1)), sha))
                break
    return found


def login_of(comment: dict) -> str | None:
    user = comment.get("user")
    return user.get("login") if isinstance(user, dict) else None


def latest_verdict(comments: list[dict], authors: list[str] | None) -> dict | None:
    """The latest comment (by time, then id) whose first line starts `Verdict:`, by an author of
    AUTHORS; None when there is none or AUTHORS is empty."""
    if not authors:
        return None
    verdicts = [
        c
        for c in comments
        if isinstance(c, dict)
        and str(c.get("body") or "").startswith("Verdict:")
        and login_of(c) in authors
    ]

    def order(c: dict) -> tuple[str, int]:
        cid = c.get("id")
        return str(c.get("created_at") or ""), cid if isinstance(cid, int) else -1

    return max(verdicts, key=order) if verdicts else None


def lost_final(
    root: Path, ref: str, comments: list[dict], authors: list[str] | None
) -> tuple[dict, str, list[str]] | None:
    """(verdict, head it names, ADR paths) when the latest verdict among COMMENTS by AUTHORS is a
    covered fix list whose `Final:` lines accept ADRs that REF reads `Proposed` and no record of
    REF accepts; else None (a numbered fix list, `rejected` or a cleared verdict among them)."""
    verdict = latest_verdict(comments, authors)
    covered = covered_fix_list(str(verdict.get("body") or "")) if verdict else None
    paths = final_accepts(covered[1]) if covered else None
    if verdict is None or covered is None or not paths:
        return None
    recorded = set(final_records(root, ref))
    left = [
        path
        for path in paths
        if (m := FILE_RE.match(path.removeprefix("docs/adr/")))
        and m.group(1) not in recorded
        and status_of(show(root, ref, path) or "") == "Proposed"
    ]
    return (verdict, covered[0], left) if left else None


def read_pulls(path: str | None) -> list[dict] | None:
    """The pull requests of `--pulls FILE`: a JSON list, or payloads one after another, each an
    object with an integer `number`; a CheckError naming the option for anything else."""
    if path is None:
        return None
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise CheckError(BAD_PULLS) from None
    decoder, items, at = json.JSONDecoder(), [], 0
    try:
        while (at := len(text) - len(text[at:].lstrip())) < len(text):
            value, at = decoder.raw_decode(text, at)
            items.extend(value if isinstance(value, list) else [value])
    except ValueError:
        raise CheckError(BAD_PULLS) from None
    if not items or not all(
        isinstance(i, dict) and isinstance(i.get("number"), int) and not isinstance(i["number"], bool)
        for i in items
    ):
        raise CheckError(BAD_PULLS)
    return items


def hand_merged_records(
    root: Path, ref: str, comments: list[dict] | None, pulls: list[dict]
) -> set[str]:
    """The ADR numbers of REF's hand merges (`hand_merges`) that the release may accept: the latest
    verdict by a record author among the pull request's COMMENTS verifies as a record would
    (`final_record_verified`), and its payload in PULLS says `merged: true`, names that squash
    commit as `merge_commit_sha` and the verdict's head as `head.sha` (Q-1738-1)."""
    merges = hand_merges(root, ref)
    if not merges or not comments:
        return set()
    authors = record_authors(root)
    by_number = {p["number"]: p for p in pulls}
    found: set[str] = set()
    for number, sha in merges:
        pull = by_number.get(number)
        head = pull.get("head") if isinstance(pull, dict) else None
        if (
            not isinstance(pull, dict)
            or pull.get("merged") is not True
            or pull.get("merge_commit_sha") != sha
            or not isinstance(head, dict)
        ):
            continue
        own = [
            c
            for c in comments
            if isinstance(c, dict) and str(c.get("issue_url") or "").endswith(f"/issues/{number}")
        ]
        lost = lost_final(root, ref, own, authors)
        if lost is None or not SHA.fullmatch(lost[1]) or head.get("sha") != lost[1]:
            continue
        verdict = lost[0]
        for path in lost[2]:
            if final_record_verified(path, (number, verdict.get("id")), verdict, authors):
                found.add(path.removeprefix("docs/adr/")[:4])
    return found


def record_ids(root: Path, argv: list[str]) -> int:
    """Print, one a line, the Final comment id of each record that `final_records` reads in HEAD's
    history: the governance workflow fetches each one for `--comments`. With `--body FILE` (the pull
    request body), only the ids a check will read (brief #1181, ADR-0501): every record's (in HEAD's
    history or the merge base's) for a release pull request (`check_release.reads_records`), else
    those of each ADR that a `Covered-by:` line of FILE names, else none. A body that cannot be
    read or a base that does not resolve narrows nothing: every id, as without the option."""
    records = final_records(root, "HEAD")
    wanted = {record[1] for record in records.values()}
    at = argv.index("--body") + 1 if "--body" in argv else None
    try:
        if at is not None:
            if at >= len(argv):
                raise CheckError("--body needs a value")
            text = Path(argv[at]).read_text(encoding="utf-8")
            base = resolve_base(root, base_arg(argv))
            mb = merge_base(root, base) if base else "HEAD"
            wanted = needed_ids(root, mb, text, records)
    except (OSError, UnicodeDecodeError, CheckError):
        pass  # fail closed: every id
    for cid in sorted(wanted):
        print(cid)
    return 0


def needed_ids(root: Path, mb: str, body: str, records: dict[str, tuple[int, int]]) -> set[int]:
    """The Final comment ids that `check_release` and `check_protected_changes` read for BODY on
    merge base MB, given RECORDS of HEAD's history (`record_ids`)."""
    import check_release  # noqa: PLC0415 - kit-only, imports this module
    from check_protected_changes import COVERED_BY, COVERED_FORM  # noqa: PLC0415

    sources = (records, final_records(root, mb))
    if check_release.reads_records(root, mb):
        return {record[1] for source in sources for record in source.values()}
    named = {
        m.group(1)
        for line in body.splitlines()
        if line.startswith(COVERED_BY) and (m := COVERED_FORM.search(line))
    }
    return {source[n][1] for source in sources for n in named if n in source}


def pending(
    root: Path,
    files: list[Path],
    comments: list[dict] | None = None,
    base: str | None = None,
    pulls: list[dict] | None = None,
) -> int:
    """Print, once each, every ADR accepted by a verified Final record of HEAD's history or of the
    merge base with BASE (the records a merge of main brought in sit on the merge's second parent,
    brief #1370, ADR-0575) whose file still says Proposed; HEAD alone when no base resolves."""
    try:
        listed = pending_paths(root, files, comments, base, pulls)
    except CheckError as err:
        print(f"FAIL {NAME}: {err}")
        return 1
    for p in listed:
        print(p.relative_to(root).as_posix())
    return 0


def pending_paths(
    root: Path,
    files: list[Path],
    comments: list[dict] | None = None,
    base: str | None = None,
    pulls: list[dict] | None = None,
) -> list[Path]:
    """The FILES that `pending` prints, in order; a CheckError as `verified_records` raises one.
    The release script flips exactly these (`changelog_fragments.py accept`, brief #1706). With
    PULLS, also the ADRs of a hand merge that `hand_merged_records` verifies (brief #1738)."""
    recorded = verified_records(root, "HEAD", comments)
    resolved = resolve_base(root, base)
    refs = ["HEAD"] + ([merge_base(root, resolved)] if resolved is not None else [])
    if resolved is not None:
        recorded |= verified_records(root, refs[1], comments)
    if pulls is not None:
        for ref in refs:
            recorded |= hand_merged_records(root, ref, comments, pulls)
    return [
        p
        for p in files
        if (m := FILE_RE.match(p.name))
        and m.group(1) in recorded
        and status_of(p.read_text(encoding="utf-8")) == "Proposed"
    ]


def pulls_arg(args: list[str]) -> str | None:
    """The value of `--pulls`, or None without the option; a CheckError naming it when empty."""
    if PULLS not in args:
        return None
    at = args.index(PULLS) + 1
    if at >= len(args) or args[at].startswith("--"):
        raise CheckError(BAD_PULLS)
    return args[at]


def adr_files(root: Path) -> list[Path]:
    """The decision files of docs/adr/, sorted, without the template."""
    adr_dir = root / "docs" / "adr"
    if not adr_dir.is_dir():
        return []
    return sorted(p for p in adr_dir.glob("*.md") if p.name != "TEMPLATE.md")


def terminal_failures(root: Path, mb: str, args: list[str]) -> list[str]:
    """SPEC-0041 rule 8, in a sidecar only (brief #1502): an ADR whose status line moves to
    `Accepted` needs an `Accept: <C> ADR-nnnn` line that `reviewers.terminal_confirmations`
    derives from `--comments FILE`, at a `<C>` of the head's history where the ADR equals its text
    apart from its status line; without `--comments` it fails (Q-1502-1 answer (a)). Team and
    solo mode take no such reading."""
    if personal_table(root) is None:
        return []
    from check_specs import in_history  # noqa: PLC0415 - the sidecar reading only
    from reviewers import (  # noqa: PLC0415
        SIDECAR_NO_COMMENTS,
        derived_only,
        solo_person,
        status_moved_only,
        terminal_shas,
    )

    given = "--comments" in args
    at = args.index("--comments") + 1 if given else 0
    if given and at >= len(args):
        raise CheckError("--comments needs a value")
    saved = (read_comments(args[at]) or []) if given else []
    derived = derived_only(saved, agent_apps(root), solo_person(root))
    problems: list[str] = []
    for path, state in sorted(changed_files(root, mb).items()):
        number = FILE_RE.match(path.removeprefix("docs/adr/"))
        if not path.startswith("docs/adr/") or not number or state not in ("A", "M"):
            continue
        new = show_work(root, path)
        old = show(root, mb, path)
        if new is None or status_of(new) != "Accepted" or (old and status_of(old) == "Accepted"):
            continue
        rid = f"ADR-{number.group(1)}"
        shas = terminal_shas(derived, rid)
        if not given:  # Q-1502-1 answer (a): refused, never skipped
            problems.append(f"{rid}: {SIDECAR_NO_COMMENTS}")
        elif not shas:
            problems.append(f"{rid}: SPEC-0041 rule 8: no Accept line of a terminal confirmation")
        elif not any(
            in_history(root, sha) and status_moved_only(show(root, sha, path) or "", new)
            for sha in shas
        ):
            problems.append(f"{rid}: SPEC-0041 rule 8: the ADR changed after the confirmed sha")
    return problems


def show_work(root: Path, path: str) -> str | None:
    try:
        return (root / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


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
    utf8_output()
    root = repo_root()
    files = adr_files(root)
    known = {m.group(1) for p in files if (m := FILE_RE.match(p.name))}
    args = sys.argv[1:] if argv is None else argv
    if "--record-ids" in args:
        return record_ids(root, list(args))
    if "--pending" in args:
        at = args.index("--comments") + 1 if "--comments" in args else None
        try:
            comments = read_comments(args[at] if at is not None and at < len(args) else None)
            base = base_arg(args)
            pulls = read_pulls(pulls_arg(args))
        except CheckError as err:
            print(f"FAIL {NAME}: {err}")
            return 1
        return pending(root, files, comments, base, pulls)
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
        if personal_table(root) is not None:  # Q-1502-1 answer (a): a sidecar fails closed
            from reviewers import SIDECAR_NO_BASE  # noqa: PLC0415

            problems.append(SIDECAR_NO_BASE)
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
        problems += terminal_failures(root, mb, args)
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if not problems:
        print(f"ok {NAME} ({len(files)} ADRs)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
