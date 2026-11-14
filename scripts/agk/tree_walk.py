"""The folders and file names of a test walk (brief #997; brief #1214, ADR-0514).

`adopt.py` (`detect_tests`, kit-only) and `doctor.py` (installed in every project) both read these
names, so they live in this small installed module and never in `adopt.py`, which a project does not
have. Standard library only; no network.
"""

from __future__ import annotations

from pathlib import Path

# Front-end test runners' file names (SPEC-0044 rule 10); their topmost folders are found the same
# way, `__tests__/`, `e2e/` and `cypress/` among them, always as folder prefixes, never as globs.
FRONTEND_PATTERNS = ("*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx")
SKIP_DIRS = {
    "node_modules",
    "__pycache__",
    "venv",
    "env",
    "build",
    "dist",
    "site-packages",
    "tox",
}
# The kit's own folders; the tests folder is written as two parts, since an installed file's text
# never names it (lean install, ADR-0052).
KIT_DIRS = (Path("tests", "kit").as_posix(), "scripts/agk")


def walked_dirs(rel_here: str, dirnames: list[str]) -> list[str]:
    """The folders under `rel_here` that a test walk enters: no dot folder, none of `SKIP_DIRS`
    and none of `KIT_DIRS`. `adopt.detect_tests` and `doctor.py` both call it (brief #997)."""
    return [
        d
        for d in dirnames
        if not d.startswith(".")
        and d not in SKIP_DIRS
        and not any(
            f"{rel_here}/{d}".lstrip("/") == k or f"{rel_here}/{d}".lstrip("/").startswith(k + "/")
            for k in KIT_DIRS
        )
    ]
