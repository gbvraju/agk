"""Print the REQ -> tests matrix to stdout. Never written to disk; never committed."""

from __future__ import annotations

import sys

from check_requirements import dirs_arg
from common import CheckError, markers_for, parse_requirements, repo_root, run, untagged_test_files

NAME = "traceability"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = repo_root()
    path = root / "docs" / "requirements.md"
    if not path.is_file():
        raise CheckError("docs/requirements.md is missing")
    reqs = parse_requirements(path.read_text(encoding="utf-8"))
    markers = markers_for(root, dirs_arg(argv))
    print("| REQ | Status | Tests |")
    print("| --- | ------ | ----- |")
    for req in reqs:
        files = ", ".join(markers.get(req["id"], [])) or "-"
        print(f"| {req['id']} | {req['status'] or '?'} | {files} |")
    retired = [r["id"] for r in reqs if r["status"] == "retired"]
    untagged = untagged_test_files(root, dirs_arg(argv))
    if retired or untagged:
        print()
    if retired:
        print(f"Retired: {', '.join(retired)}")
    if untagged:
        print(f"Untagged test files ({len(untagged)}): {', '.join(untagged)}")
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
