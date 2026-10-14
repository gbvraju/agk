"""docs/build-state.md stays untouched in a PR unless the PR touches only docs/.

Creating the file (absent at the base) is allowed, so the PR that introduces this check can add it.
"""

from __future__ import annotations

import sys

from common import base_arg, base_context, changed_files, repo_root, run, show

NAME = "build-state"
PATH = "docs/build-state.md"


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    mb = base_context(root, NAME, base_arg(argv))
    if mb is None:
        return 0
    changed = changed_files(root, mb)
    if PATH not in changed:
        print(f"ok {NAME}")
        return 0
    if show(root, mb, PATH) is None:
        print(f"ok {NAME} (file created)")
        return 0
    if changed[PATH] == "D":
        print(f"FAIL {NAME}: {PATH} cannot be deleted")
        return 1
    outside = sorted(p for p in changed if not p.startswith("docs/"))
    if outside:
        print(f"FAIL {NAME}: {PATH} changed in a PR that also touches paths outside docs/")
        return 1
    print(f"ok {NAME} (docs-only change)")
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
