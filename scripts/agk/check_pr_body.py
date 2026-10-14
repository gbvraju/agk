"""PR body must carry `Advances: REQ-nnn` and a dated `Build-state row:` (file or stdin)."""

from __future__ import annotations

import re
import sys

from common import REQ_ID, CheckError, run

NAME = "pr-body"
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def field(text: str, label: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(label):
            return line[len(label) :].strip()
    return None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        raise CheckError("usage: check_pr_body.py [FILE|-]")
    try:
        if not args or args[0] == "-":
            text = sys.stdin.read()
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
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if not problems:
        print(f"ok {NAME}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
