# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `tests-floor` step of the `tests-first` gate (brief #1590, ADR-0670; amendment 198 of
SPEC-0072 rules 2, 4 and 9; REQ-079).

Offline, on the project's files and the change's diff (`git diff` from the merge base with the base
that `common.resolve_base` gives: `AGK_BASE`, `GITHUB_BASE_REF`, then the default branch). In a
project with a `[delivery] work_type` whose foundation build has merged (its architecture record
`docs/architecture.md` exists, Q-1590-3) it fails when (a) the `test_dirs` hold no test file of
the stack, (b) the integration folder (`<first test_dirs entry>/integration/`, every stack until
its pack names one, Q-1590-2) holds none, or (c) the change adds or changes a code file of an
`[architecture]` layer and adds or changes no test file; a change that only deletes code is green
(Q-1590-1). With `mode = "adopt"` rules (a) and (b) are held until the person records today's
behaviour as tests; rule (c) applies. With no work type it is not run (`no work type`), so the
kit's own repository and an existing project keep today's reading. A stack with no reader yet is
not run, never `ok`. Each failure names the rule and the path class, never a file or a value
(principle 8). Paths compare by forward slash; no shell.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import playbook_format  # noqa: E402
from common import (  # noqa: E402
    CheckError,
    changed_files,
    changed_lines,
    load_config,
    merge_base,
    resolve_base,
)
from impact import matches  # noqa: E402

from gates import layers, pins  # noqa: E402

RULE = "SPEC-0072 rule 2 (amendment 198): the tests floor"
NO_TESTS = "SPEC-0072 rule 2 (amendment 198): the test folders hold no test file"
NO_INTEGRATION = "SPEC-0072 rule 2 (amendment 198): the integration folder holds no test file"
NO_TEST_CHANGE = "SPEC-0072 rule 2 (amendment 198): a layer's code changed with no test change"
NO_BASE = "SPEC-0072 rule 2 (amendment 198): the change's base cannot be read"
INTEGRATION = "integration"
KIT_FOLDERS = ("scripts/agk/", ".claude/")
# The test file and code file forms of each stack with a reader; another stack is not run.
TEST_FORMS = {"python": ("test_*.py", "*_test.py")}
CODE_FORMS = {"python": ("*.py",)}


def runtime(root: Path) -> str:
    """The chosen stack's runtime (`python` until a stack record names another)."""
    picked = pins.chosen(root)
    if picked is None:
        return "python"
    return next((p[0] for p in picked[1] if p[0] in pins.STACKS), "python")


def skipped(root: Path) -> str | None:
    """The reason the step is not run, or None when it reads the project."""
    if playbook_format.selected(root) is None:
        return "no work type"
    if not (root / layers.RECORD).is_file():
        return "no foundation yet"
    stack = runtime(root)
    return None if stack in TEST_FORMS else f"no reader for {stack}"


def folders(root: Path) -> list[str]:
    """The `test_dirs` entries as forward-slash folders with no leading `./` or trailing `/`."""
    out = []
    for raw in load_config(root)["test_dirs"]:
        rel = str(raw).replace("\\", "/").strip("/")
        while rel.startswith("./"):
            rel = rel[2:].strip("/")
        if rel and rel != ".":
            out.append(rel)
    return out


def named(rel: str, forms: tuple[str, ...]) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return any(matches(name, form) for form in forms)


def is_test(rel: str, tests: list[str], stack: str) -> bool:
    return any(rel.startswith(f"{t}/") for t in tests) and named(rel, TEST_FORMS[stack])


def holds_test(root: Path, folder: str, stack: str) -> bool:
    base = root / folder
    if not base.is_dir():
        return False
    for path in base.rglob("*"):
        if path.is_file() and named(path.name, TEST_FORMS[stack]):
            return True
    return False


def added(root: Path, mb: str, rel: str, status: str) -> bool:
    """True when the change adds or changes a line of the file (a deletion only is False)."""
    if status == "D":
        return False
    if status != "M":
        return True
    return any(line.startswith("+") for line in changed_lines(root, mb, rel))


def untested_layers(root: Path, tests: list[str], stack: str) -> list[tuple[str, str]]:
    """Rule (c): (rule, path class) of each layer whose code changed with no test change."""
    try:
        base = resolve_base(root)
        if base is None:
            return []  # outside CI with no base: nothing to compare (the check's usual reading)
        mb = merge_base(root, base)
        changed = changed_files(root, mb)
    except CheckError:
        return [(NO_BASE, "the change (setting: AGK_BASE)")]
    if any(is_test(rel, tests, stack) and added(root, mb, rel, s) for rel, s in changed.items()):
        return []
    arch = layers.architecture(root)[0]
    found: set[tuple[str, str]] = set()
    for rel, status in changed.items():
        if rel.startswith(KIT_FOLDERS) or any(rel.startswith(f"{t}/") for t in tests):
            continue
        if not named(rel, CODE_FORMS[stack]) or not added(root, mb, rel, status):
            continue
        layer = layers.layer_of(rel, arch)
        if layer:
            found.add((NO_TEST_CHANGE, f"{layer[1]}; layer: {layer[0]}"))
    return sorted(found)


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """The runner's interface: (rule, path class) of each failure, none when the step passes."""
    stack = runtime(root)
    tests = folders(root)
    out: list[tuple[str, str]] = []
    if load_config(root)["mode"] != "adopt":
        if not any(holds_test(root, t, stack) for t in tests):
            out.append((NO_TESTS, "test_dirs"))
        if tests and not holds_test(root, f"{tests[0]}/{INTEGRATION}", stack):
            out.append((NO_INTEGRATION, f"{tests[0]}/{INTEGRATION}/"))
    return out + untested_layers(root, tests, stack)
