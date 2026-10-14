"""Requirements file: unique ids, valid Status, and a test marker for every `done`."""

from __future__ import annotations

import sys

from common import (
    ALLOWED_STATUS,
    CheckError,
    markers_for,
    parse_requirements,
    repo_root,
    run,
)

NAME = "requirements"
PATH = "docs/requirements.md"


def dirs_arg(argv: list[str]) -> list[str]:
    dirs: list[str] = []
    for i, arg in enumerate(argv):
        if arg == "--tests-dir":
            if i + 1 >= len(argv):
                raise CheckError("--tests-dir needs a value")
            dirs.append(argv[i + 1])
    return dirs


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = repo_root()
    path = root / PATH
    if not path.is_file():
        raise CheckError(f"{PATH} is missing")
    reqs = parse_requirements(path.read_text(encoding="utf-8"))
    if not reqs:
        raise CheckError(f"{PATH} defines no requirement")
    markers = markers_for(root, dirs_arg(argv))

    problems: list[str] = []
    seen: set[str] = set()
    for req in reqs:
        rid = req["id"]
        if rid in seen:
            problems.append(f"{rid}: duplicate id (line {req['line']})")
        seen.add(rid)
        if req["status_count"] != 1:
            problems.append(f"{rid}: needs exactly one '- Status:' line")
        elif req["status"] not in ALLOWED_STATUS:
            problems.append(f"{rid}: Status is not one of {', '.join(ALLOWED_STATUS)}")
        elif req["status"] == "done" and rid not in markers:
            problems.append(f"{rid}: done requires a test marker under the test directories")
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if not problems:
        print(f"ok {NAME} ({len(reqs)} requirements)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
