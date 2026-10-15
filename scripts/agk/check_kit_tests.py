"""Fail when an installed check ships without an installed test.

Every `scripts/agk/check_*.py` in the verbatim set of `kit/manifest.json` needs at least one test
file under `tests/kit/` in the same set that imports it or runs it (names its file in a string). A
mention in a docstring or a comment does not count. A repository without `kit/manifest.json` (an
installed one) has nothing to check.
"""

from __future__ import annotations

import ast
import json
import re
import sys

from common import CheckError, repo_root, run

NAME = "kit-tests"
MANIFEST = "kit/manifest.json"
CHECK_PATH = re.compile(r"scripts/agk/(check_[^/]+)\.py")
TEST_PATH = re.compile(r"tests/kit/test_[^/]+\.py")


def references(source: str, stem: str) -> bool:
    """True when the module imports `stem` or has a string naming `stem.py` outside a comparison.

    A docstring, a comment and a string inside a comparison (`name in ("check_x.py", ...)`, an
    exclusion list) do not count: they talk about the check, they do not run it.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docstrings.add(first.value)

    def in_comparison(node: ast.AST) -> bool:
        while node in parents:
            node = parents[node]
            if isinstance(node, ast.Compare):
                return True
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name.split(".")[-1] == stem for a in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[-1] == stem:
            return True
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node not in docstrings
            and f"{stem}.py" in node.value
            and not in_comparison(node)
        ):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    path = root / MANIFEST
    if not path.is_file():
        print(f"ok {NAME} (no {MANIFEST} here; nothing to check)")
        return 0
    try:
        verbatim = json.loads(path.read_text(encoding="utf-8"))["verbatim"]
        if not isinstance(verbatim, list) or not all(isinstance(p, str) for p in verbatim):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CheckError(f"{MANIFEST} cannot be read or has no verbatim list") from exc
    checks = sorted((p, m.group(1)) for p in verbatim if (m := CHECK_PATH.fullmatch(p)))
    tests = sorted(p for p in verbatim if TEST_PATH.fullmatch(p))
    sources = {}
    for rel in tests:
        try:
            sources[rel] = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    problems = []
    for check, stem in checks:
        if not any(references(text, stem) for text in sources.values()):
            problems.append(
                f"{check} has no test file under tests/kit/ in the verbatim set of {MANIFEST} "
                "that imports or runs it"
            )
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if not problems:
        print(f"ok {NAME} ({len(checks)} checks, {len(tests)} test files)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
