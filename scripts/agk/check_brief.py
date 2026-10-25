"""A saved copy of a brief has the shape of SPEC-0030 rule 4.

    python3 check_brief.py FILE [--root DIR]

The body has one line `Sentence:` with the sentence in quotation marks (1 to 300 characters), one
line that starts `Answers` and ends with a colon followed by numbered items without a gap, zero or
more lines `Depends-on: #n`, one line `Size: S`, `Size: M` or `Size: L`, and (SPEC-0034 rule 2) one
line `Advances:` (REQ ids or `new`), one line `Touches:` (globs) and at most one `Priority:`
(0 to 3; SPEC-0032 rule 9: a `Priority: 0` brief needs one line `Measured:` with the command and the
output before and after a change that turns it green, except the red-branch brief of the
router). The
shape is the function `brief_problems` of `session.py`, which `session.py next` applies to the body
it reads. With `--root DIR` an `Advances:` that names a requirement that is not a `### REQ-n`
section of `DIR/docs/requirements.md` also fails.
Reads the file only: no network, no model. Messages name the rule, never the sentence.
"""

from __future__ import annotations

import sys
from pathlib import Path

from common import REQ_HEADER, CheckError, run
from session import advances_ids, brief_problems

NAME = "brief"
USAGE = "usage: check_brief.py FILE [--root DIR]"
REQUIREMENTS = "docs/requirements.md"


def absent_requirements(body: str, root: Path) -> list[str]:
    try:
        text = (root / REQUIREMENTS).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"rule 2: {REQUIREMENTS} cannot be read under the root") from exc
    known = {m.group(1) for m in map(REQ_HEADER.match, text.splitlines()) if m}
    if all(req in known for req in advances_ids(body)):
        return []
    return [f"rule 2: Advances names a requirement that is not a section of {REQUIREMENTS}"]


def check(path: Path, root: Path | None = None) -> int:
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the brief file cannot be read") from exc
    problems = brief_problems(body)
    if root is not None and not problems:
        problems = absent_requirements(body, root)
    if problems:
        raise CheckError("; ".join(problems))
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[2]) if len(args) == 3 and args[1] == "--root" else None
    if len(args) != 1 and root is None:
        print(USAGE)
        return 2
    return run(NAME, lambda: check(Path(args[0]), root))


if __name__ == "__main__":
    sys.exit(main())
