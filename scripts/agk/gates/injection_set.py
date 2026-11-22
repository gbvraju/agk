# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `injection-set` step of the mcp-server `prompt-injection-set` gate (SPEC-0072 rule 3;
brief #1712, ADR-0717; REQ-079).

The set is the folder `injection/` directly under a `test_dirs` entry (`tests/injection/` by
default), in any stack. Offline, on the project's files, the step fails when no entry holds such a
folder, when the folders hold no file but a README, or when no `[testing] map` entry of `agk.toml`
has a `tests` glob that matches a file of the set (a generated map file does not count, Q-1712-2).
Not run while the architecture record `docs/architecture.md` is absent (`no foundation yet`, as the
tests floor). A `test_dirs` value that is not a list of folders is refused naming `test_dirs`; a
malformed `[testing]` setting is refused naming it (`impact.testing_table`). Each failure names the
rule and the path class, never a file (principle 8). Files only: no network.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

from common import CheckError, load_config  # noqa: E402
from impact import _folder_ok, matches, testing_table  # noqa: E402

from gates import layers  # noqa: E402

RULE = "SPEC-0072 rule 3: the prompt-injection test set"
NO_SET = "SPEC-0072 rule 3: the prompt-injection test set is missing"
NO_FILE = "SPEC-0072 rule 3: the prompt-injection test set holds no test file"
UNMAPPED = "SPEC-0072 rule 3: the testing map names no test of the prompt-injection test set"
BAD_DIRS = "test_dirs is a list of folder paths inside the repository (setting: test_dirs)"
FOLDER = "injection"


def skipped(root: Path) -> str | None:
    return None if (root / layers.RECORD).is_file() else "no foundation yet"


def folders(root: Path) -> list[str]:
    """The `test_dirs` entries, forward slash, no trailing `/`; a bad value is refused."""
    raw = load_config(root)["test_dirs"]
    if not isinstance(raw, list) or not raw or not all(_folder_ok(t) for t in raw):
        raise CheckError(BAD_DIRS)
    return [t.rstrip("/").removeprefix("./") for t in raw]


def set_files(root: Path, tests: list[str]) -> tuple[bool, list[str]]:
    """Whether a set folder exists, and its files other than a README, relative to the root."""
    found, files = False, []
    for t in tests:
        base = root / t / FOLDER
        if not base.is_dir():
            continue
        found = True
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(root).as_posix()
            hidden = any(p.startswith(".") or p == "__pycache__" for p in rel.split("/"))
            if path.is_file() and not hidden and not path.name.lower().startswith("readme"):
                files.append(rel)
    return found, files


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """The runner's interface: (rule, path class) of each failure, none when the step passes."""
    tests = folders(root)
    table = testing_table(root)  # refuses a malformed `[testing]` setting, naming it
    where = f"{tests[0]}/{FOLDER}/"
    found, files = set_files(root, tests)
    if not found:
        return [(NO_SET, f"{where}; setting: test_dirs")]
    if not files:
        return [(NO_FILE, f"{where}; setting: test_dirs")]
    globs = [g for entry in (table or {}).get("map", []) for g in entry["tests"]]
    if not any(matches(rel, g) for rel in files for g in globs):
        return [(UNMAPPED, f"{where}; setting: testing.map")]
    return []
