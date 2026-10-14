"""No token of config/neutrality.txt appears in tracked files outside docs/adr/."""

from __future__ import annotations

import sys

from common import CheckError, git, read_list, repo_root, run

NAME = "neutrality"
TOKENS = "config/neutrality.txt"
EXEMPT_PREFIX = "docs/adr/"


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    path = root / TOKENS
    if not path.is_file():
        raise CheckError(f"{TOKENS} is missing")
    tokens = [t.lower() for t in read_list(path.read_text(encoding="utf-8"))]
    hits: list[str] = []
    if tokens:
        for rel in filter(None, git(root, "ls-files", "-z").split("\0")):
            if rel.startswith(EXEMPT_PREFIX) or rel == TOKENS:
                continue
            try:
                text = (root / rel).read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                low = line.lower()
                for idx, token in enumerate(tokens, 1):
                    if token in low:
                        hits.append(f"{rel}:{n} (token #{idx} of {TOKENS})")
    for hit in hits:
        print(f"FAIL {NAME}: {hit}")
    if not hits:
        print(f"ok {NAME} ({len(tokens)} tokens)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
