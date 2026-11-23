# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Principle 4: docs/build-state.md is only appended, and only by docs commits.

The file stays untouched in a PR unless the PR touches only docs/, and then every line of the base
must still be there, byte for byte and in the same order; rows may be inserted anywhere (brief
#1836, ADR-0765). Creating the file (absent at the base) is allowed, so the PR that introduces this
check can add it.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    base_arg,
    base_context,
    changed_files,
    committed_bytes,
    repo_root,
    run,
    utf8_output,
)

NAME = "build-state"
PATH = "docs/build-state.md"


def base_bytes(root: Path, mb: str) -> bytes | None:
    """The file's bytes at the merge base MB (never decoded, so CRLF stays), or None when absent."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "cat-file", "blob", f"{mb}:{PATH}"], cwd=root, capture_output=True, check=False
    )
    return proc.stdout if proc.returncode == 0 else None


def appended(old: bytes, new: bytes) -> bool:
    """Whether every line of OLD (line ends kept) is a line of NEW, in order (one greedy pass). The
    last line of OLD with no line end also matches that line plus one line end."""
    lines = new.splitlines(keepends=True)
    j = 0
    for line in old.splitlines(keepends=True):
        ok = {line} if line.endswith((b"\n", b"\r")) else {line, line + b"\n", line + b"\r\n"}
        while j < len(lines) and lines[j] not in ok:
            j += 1
        if j == len(lines):
            return False
        j += 1
    return True


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    root = repo_root()
    mb = base_context(root, NAME, base_arg(argv))
    if mb is None:
        return 0
    changed = changed_files(root, mb)
    if PATH not in changed:
        print(f"ok {NAME}")
        return 0
    old = base_bytes(root, mb)
    if old is None:
        print(f"ok {NAME} (file created)")
        return 0
    if changed[PATH] == "D":
        print(f"FAIL {NAME}: {PATH} cannot be deleted")
        return 1
    outside = sorted(p for p in changed if not p.startswith("docs/"))
    if outside:
        print(f"FAIL {NAME}: {PATH} changed in a PR that also touches paths outside docs/")
        return 1
    disk = (root / PATH).read_bytes()
    new = committed_bytes(root, {PATH: disk})[PATH]
    if not appended(old, new):
        print(
            f"FAIL {NAME}: {PATH} is only appended; an existing row was changed or removed "
            f"(path class: {PATH})"
        )
        return 1
    print(f"ok {NAME} (docs-only change)" if old == new else f"ok {NAME} (rows appended)")
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
