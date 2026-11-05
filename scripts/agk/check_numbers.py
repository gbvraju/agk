"""Duplicate numbers: two requirements, two specs or two ADRs, one number (SPEC-0025 rule 1).

    python3 check_numbers.py [--open FILE --number N]

It reads the checked-out tree. In CI that tree is the pull request's merge commit, so a
collision with the default branch shows there. `intake.py renumber <id>` is the fix.

A spec amendment (`docs/runs/proposed-spec-amendments-<n>.md`) that the pull request adds, against
the merge base with the base ref, fails when the base ref already has that number, and, with a saved
open-pull-requests file and the pull request's own number, when another open pull request's record
lists the same path in its `files` (ADR-0275). A record without a file list is never guessed at.
Files and git only: no network. Messages name the number and the pull request, never a title.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    NUM_FILE,
    CheckError,
    changed_files,
    json_records,
    merge_base,
    parse_requirements,
    read_text,
    repo_root,
    resolve_base,
    run,
    show,
)

NAME = "numbers"
USAGE = "usage: check_numbers.py [--open FILE --number N]"
AMENDMENT = re.compile(r"docs/runs/proposed-spec-amendments-(\d+)\.md")


def duplicates(root: Path) -> list[str]:
    ids = Counter(
        r["id"] for r in parse_requirements(read_text(root, "docs/requirements.md") or "")
    )
    found = [rid for rid, count in sorted(ids.items()) if count > 1]
    for folder, label in (("specs", "SPEC"), ("adr", "ADR")):
        names = [p.name for p in sorted((root / "docs" / folder).glob("*.md"))]
        numbers = Counter(m.group(1) for n in names if (m := NUM_FILE.match(n)))
        found += [f"{label}-{number}" for number, count in sorted(numbers.items()) if count > 1]
    return found


def amendment_clashes(root: Path, opened: list[dict] | None, own: int | None) -> list[str]:
    """The amendment numbers this pull request adds that main or another open one already has."""
    base = resolve_base(root)
    if base is None:
        return []
    added = sorted(
        (int(m.group(1)), path)
        for path, status in changed_files(root, merge_base(root, base)).items()
        if status == "A" and (m := AMENDMENT.fullmatch(path))
    )
    others: dict[str, list[int]] = {}
    for record in opened or []:
        number, files = record.get("number"), record.get("files")
        if not isinstance(number, int) or number == own or not isinstance(files, list):
            continue
        for path in files:
            if isinstance(path, str):
                others.setdefault(path, []).append(number)
    found = []
    for number, path in added:
        if show(root, base, path) is not None:
            found.append(f"amendment {number} is on the default branch")
        found += [
            f"amendment {number} is also added by #{n}" for n in sorted(set(others.get(path, [])))
        ]
    return found


def check(root: Path, opts: dict[str, str]) -> int:
    found = duplicates(root)
    problems = ["more than one carries the number of " + ", ".join(found)] if found else []
    opened = json_records(Path(opts["--open"]), "open pull requests") if "--open" in opts else None
    problems += amendment_clashes(
        root, opened, int(opts["--number"]) if opened is not None else None
    )
    if problems:
        raise CheckError("rule 1: " + "; ".join(problems))
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    opts = dict(zip(args[::2], args[1::2], strict=False))
    if (
        len(args) % 2
        or not set(opts) <= {"--open", "--number"}
        or ("--open" in opts) != ("--number" in opts)
        or not opts.get("--number", "0").isdigit()
    ):
        print(USAGE)
        return 2
    root = repo_root()
    return run(NAME, lambda: check(root, opts))


if __name__ == "__main__":
    sys.exit(main())
