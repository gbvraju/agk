"""Fail when a protected path changes without an ADR in the same change set that names its class."""

from __future__ import annotations

import sys

from common import (
    CheckError,
    base_arg,
    base_context,
    changed_files,
    changed_lines,
    matches,
    read_list,
    repo_root,
    run,
    show,
)

NAME = "protected-changes"
LIST_PATH = "config/protected-paths.txt"
STATUS_ONLY_FILE = "docs/requirements.md"


def is_adr(path: str, status: str) -> bool:
    return (
        path.startswith("docs/adr/")
        and path.endswith(".md")
        and path != "docs/adr/TEMPLATE.md"
        and status in ("A", "M")
    )


def covering_adrs(root, mb, changed: dict[str, str], classes: list[str]) -> list[str]:
    """ADRs added or modified (not Status-only) whose text names every changed class."""
    found = []
    for path, status in sorted(changed.items()):
        if not is_adr(path, status):
            continue
        if status == "M":
            lines = changed_lines(root, mb, path)
            if all(ln[1:].startswith("- Status:") for ln in lines):
                continue
        text = (root / path).read_text(encoding="utf-8")
        if all(entry in text for entry in classes):
            found.append(path)
    return found


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    mb = base_context(root, NAME, base_arg(argv))
    if mb is None:
        return 0
    listing = show(root, mb, LIST_PATH)
    if listing is None:
        path = root / LIST_PATH
        if not path.is_file():
            raise CheckError(f"{LIST_PATH} is missing")
        listing = path.read_text(encoding="utf-8")
    entries = read_list(listing)
    changed = changed_files(root, mb)

    classes: list[str] = []
    for path, status in sorted(changed.items()):
        for entry in entries:
            if not matches(path, entry):
                continue
            if path == STATUS_ONLY_FILE and status == "M":
                lines = changed_lines(root, mb, path)
                if lines and all(ln[1:].startswith("- Status:") for ln in lines):
                    break
            if entry not in classes:
                classes.append(entry)
            break

    if not classes:
        print(f"ok {NAME}")
        return 0
    if covering_adrs(root, mb, changed, classes):
        print(f"ok {NAME} (protected change covered by an ADR)")
        return 0
    for entry in classes:
        print(
            f"FAIL {NAME}: protected path class '{entry}' changed without an ADR that names it "
            "(added or modified, not a Status-only edit)"
        )
    return 1


if __name__ == "__main__":
    sys.exit(run(NAME, main))
