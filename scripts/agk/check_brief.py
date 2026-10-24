"""A saved copy of a brief has the shape of SPEC-0030 rule 4.

    python3 check_brief.py FILE

The body has one line `Sentence:` with the sentence in quotation marks (1 to 300 characters), one
line that starts `Answers` and ends with a colon followed by numbered items without a gap, zero or
more lines `Depends-on: #n` and one line `Size: S`, `Size: M` or `Size: L`. The shape is the
function `brief_problems` of `session.py`, which `session.py next` applies to the body it reads.
Reads the file only: no network, no model. Messages name the rule, never the sentence.
"""

from __future__ import annotations

import sys
from pathlib import Path

from common import CheckError, run
from session import brief_problems

NAME = "brief"
USAGE = "usage: check_brief.py FILE"


def check(path: Path) -> int:
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the brief file cannot be read") from exc
    problems = brief_problems(body)
    if problems:
        raise CheckError("; ".join(problems))
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(USAGE)
        return 2
    return run(NAME, lambda: check(Path(args[0])))


if __name__ == "__main__":
    sys.exit(main())
