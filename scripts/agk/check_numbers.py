"""Duplicate numbers: two requirements, two specs or two ADRs, one number (SPEC-0025 rule 1).

It reads the checked-out tree only. In CI that tree is the pull request's merge commit, so a
collision with the default branch shows there. `intake.py renumber <id>` is the fix.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import NUM_FILE, CheckError, parse_requirements, read_text, repo_root, run

NAME = "numbers"


def duplicates(root: Path) -> list[str]:
    ids = Counter(
        r["id"] for r in parse_requirements(read_text(root, "docs/requirements.md") or "")
    )
    found = [rid for rid, count in sorted(ids.items()) if count > 1]
    for folder, label in (("specs", "SPEC"), ("adr", "ADR")):
        names = [p.name for p in sorted((root / "docs" / folder).glob("*.md"))]
        numbers = Counter(m.group(1) for n in names if (m := NUM_FILE.match(n)))
        found += [f"{label}-{number}" for number, count in sorted(numbers.items()) if count > 1]
    return found


def main() -> int:
    found = duplicates(repo_root())
    if found:
        raise CheckError("rule 1: more than one carries the number of " + ", ".join(found))
    print(f"ok {NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
