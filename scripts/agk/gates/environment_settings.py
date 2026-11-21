# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `environment-settings` step (SPEC-0072 rules 2 and 12 build (f); REQ-079 AC4; brief #1593,
ADR-0673).

Reads, offline and with `ast`, the setting names the project's tracked Python code reads by
literal name (`os.environ[...]`, `os.getenv(...)`, `os.environ.get(...)`, and `environ` or
`getenv` imported from `os`), and fails on a name that the example settings file (`.env.example`,
Q-1593-1) does not list, and on a required name (one read somewhere with no default) that the
code reads with a default elsewhere (Q-1593-2). A project with no example file fails only when
its code reads a setting. The kit's installed folders (`scripts/agk/`, `.claude/`) and the
`test_dirs` folders are not the project's code. Other stacks' readers come with their packs. Each
failure is one path class, never a name or a value (principle 8); `mode = "adopt"` holds them
until brief #1600's baseline.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

from common import load_config  # noqa: E402

from . import committed_secrets as secrets  # noqa: E402

RULE = "SPEC-0072 rule 2: a setting the code reads is not named or not required as the example says"
KIT_FOLDERS = ("scripts/agk/", ".claude/")


def _is(node: ast.AST, name: str) -> bool:
    """`os.<name>` or a bare `<name>` imported from `os`."""
    if isinstance(node, ast.Attribute):
        return node.attr == name and isinstance(node.value, ast.Name) and node.value.id == "os"
    return isinstance(node, ast.Name) and node.id == name


def reads(tree: ast.AST) -> list[tuple[str, bool]]:
    """(name, has a default) for each literal setting name the tree reads."""
    out = []
    for node in ast.walk(tree):
        key, default = None, False
        if isinstance(node, ast.Subscript) and _is(node.value, "environ"):
            key = node.slice
        elif isinstance(node, ast.Call) and node.args:
            func = node.func
            attr = func if isinstance(func, ast.Attribute) and func.attr == "get" else None
            env_get = attr is not None and _is(attr.value, "environ")
            if _is(func, "getenv") or env_get:
                key, default = node.args[0], len(node.args) > 1 or bool(node.keywords)
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            out.append((key.value, default))
    return out


def project_code(root: Path, rel: str, tests: list[str]) -> bool:
    folders = rel.split("/")[:-1]
    kit = rel.startswith(KIT_FOLDERS)
    return rel.endswith(".py") and not kit and not any(t.strip("/") in folders for t in tests)


def problems(root: Path) -> list[str]:
    tests = list(load_config(root)["test_dirs"])
    found: list[tuple[str, bool]] = []
    for rel in secrets.files(root):
        if project_code(root, rel, tests) and (root / rel).is_file():
            try:
                found += reads(ast.parse((root / rel).read_bytes()))
            except (SyntaxError, ValueError):
                continue  # the lint step's finding, not this one's
    example = root / secrets.EXAMPLE
    text = example.read_text(encoding="utf-8", errors="replace") if example.is_file() else ""
    listed = {name for name, _ in secrets.example_values(text)}
    required = {name for name, default in found if not default}
    out = []
    if any(name not in listed for name, _ in found):
        out.append("settings read in code (not in the example file)")
    if any(default and name in required for name, default in found):
        out.append("settings read in code (a required one with a default)")
    return out


def check(root: Path, playbook: dict[str, Any]) -> list[str]:
    """The runner's interface: the path classes that fail, none when the step passes."""
    found = problems(root)
    return [] if load_config(root)["mode"] == "adopt" else found
