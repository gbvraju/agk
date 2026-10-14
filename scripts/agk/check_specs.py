"""An Approved spec changes only with a proposed-spec-amendments file in the same change set.

A PR that modifies or deletes a spec whose base version is `Status: Approved` fails unless it also
adds or modifies a `docs/runs/proposed-spec-amendments-*.md` file that names the spec's path. A
Draft spec, a new spec and the Draft -> Approved flip pass. Messages name the spec path, never
content.
"""

from __future__ import annotations

import re
import sys

from common import STATUS_LINE, base_arg, base_context, changed_files, repo_root, run, show

NAME = "specs"
SPEC_PREFIX = "docs/specs/"
AMENDMENT = re.compile(r"^docs/runs/proposed-spec-amendments-[^/]+\.md$")


def status_of(text: str) -> str | None:
    for line in text.splitlines():
        match = STATUS_LINE.match(line)
        if match:
            return match.group(1)
    return None


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    mb = base_context(root, NAME, base_arg(argv))
    if mb is None:
        return 0
    changed = changed_files(root, mb)
    amendments = [
        p
        for p, s in changed.items()
        if AMENDMENT.match(p) and s in ("A", "M") and (root / p).is_file()
    ]
    texts = [(root / p).read_text(encoding="utf-8") for p in amendments]
    failures = []
    for path in sorted(changed):
        if not (path.startswith(SPEC_PREFIX) and path.endswith(".md")):
            continue
        old = show(root, mb, path)
        if old is None or status_of(old) != "Approved":
            continue
        if not any(path in text for text in texts):
            failures.append(path)
    for path in failures:
        print(
            f"FAIL {NAME}: approved spec '{path}' changed without a proposed-spec-amendments file "
            "that names it"
        )
    if not failures:
        print(f"ok {NAME}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
