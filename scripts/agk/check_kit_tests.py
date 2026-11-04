"""Fail when an installed check has no test in the kit repository.

Every `scripts/agk/check_*.py` in the verbatim set of `kit/manifest.json` needs at least one test
file in the folder the manifest names as `kit_tests` that imports it or runs it (names its file in
a string). The tests are not installed in projects (lean install): they run in the kit's own CI. A
mention in a docstring or a comment does not count. A repository without `kit/manifest.json` (an
installed one) has nothing to check.

Brief #483 (ADR-0276): a test never pins its own ADR's status. When a base ref resolves, every
`test_*.py` file that the pull request adds or changes is read beside every ADR under `docs/adr/`
that it adds. A test file fails when it names an added ADR outside a docstring (`ADR-NNNN`,
`adr/NNNN` or the ADR's file name in a string) and holds an assertion, or a comparison outside
one, with a status string (`Status: Proposed`, or `Proposed` alone) and no string naming
`Accepted`: the status-only `Final:` commit makes that ADR Accepted, and the test would then turn
the default branch red. ADRs already on the base and test files the pull request does not touch
are not read; without a base outside CI the rule is skipped.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    CheckError,
    base_arg,
    changed_files,
    merge_base,
    repo_root,
    resolve_base,
    run,
)

NAME = "kit-tests"
MANIFEST = "kit/manifest.json"
CHECK_PATH = re.compile(r"scripts/agk/(check_[^/]+)\.py")
TESTS_KEY = "kit_tests"
ADR_FILE = re.compile(r"docs/adr/((\d{4})-[a-z0-9][a-z0-9-]*)\.md")
TEST_FILE = re.compile(r"(?:.*/)?test_[^/]*\.py")
PROPOSED = re.compile(r"Status:\s*Proposed\b")
BARE_PROPOSED = re.compile(r"\s*Proposed\s*")
ACCEPTED = re.compile(r"\bAccepted\b")


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


def _docstrings(tree: ast.AST) -> set[ast.AST]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                found.add(first.value)
    return found


def _strings(node: ast.AST, skip: set[ast.AST] = frozenset()) -> list[str]:
    return [
        n.value
        for n in ast.walk(node)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n not in skip
    ]


def pinned_adrs(source: str, adrs: dict[str, str]) -> list[str]:
    """The numbers of the ADRs in `adrs` (number -> file stem) that this test pins to Proposed.

    The test names the ADR in a string that is not a docstring, and one of its assertions, or a
    comparison outside an assertion, holds a status string (`Status: Proposed`, or `Proposed`
    alone; a title such as "Proposed spec amendments" is not a status) and none naming Accepted.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    strings = _strings(tree, _docstrings(tree))
    named = [
        number
        for number, stem in sorted(adrs.items())
        if any(f"ADR-{number}" in t or f"adr/{number}" in t or stem in t for t in strings)
    ]
    if not named:
        return []
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    units: list[ast.AST] = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        top, up = node, node
        while up in parents and not isinstance(up, ast.stmt):
            up = parents[up]
            if isinstance(up, ast.expr):
                top = up
        if not isinstance(up, ast.Assert):
            units.append(top)
    for unit in units:
        texts = _strings(unit)
        pinned = any(PROPOSED.search(t) or BARE_PROPOSED.fullmatch(t) for t in texts)
        if pinned and not any(ACCEPTED.search(t) for t in texts):
            return named
    return []


def own_adr_problems(root: Path, argv: list[str] | None) -> list[str]:
    """Brief #483: test files changed here that pin an ADR added here to Proposed."""
    base = resolve_base(root, base_arg(argv))
    if base is None:
        print(f"{NAME}: no base ref available outside CI; own-ADR status rule skipped")
        return []
    changed = changed_files(root, merge_base(root, base))
    adrs = {
        m.group(2): m.group(1)
        for path, status in changed.items()
        if status == "A" and (m := ADR_FILE.fullmatch(path))
    }
    if not adrs:
        return []
    problems = []
    for path, status in sorted(changed.items()):
        if status not in ("A", "M") or not TEST_FILE.fullmatch(path):
            continue
        try:
            source = (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for number in pinned_adrs(source, adrs):
            problems.append(
                f"{path} pins ADR-{number}, which this pull request adds, to Proposed; "
                "a test never pins its own ADR's status (accept Proposed or Accepted)"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    path = root / MANIFEST
    if not path.is_file():
        print(f"ok {NAME} (no {MANIFEST} here; nothing to check)")
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        verbatim, folder = data["verbatim"], data[TESTS_KEY]
        if not isinstance(verbatim, list) or not all(isinstance(p, str) for p in verbatim):
            raise ValueError
        if not isinstance(folder, str) or not folder:
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CheckError(
            f"{MANIFEST} cannot be read or has no verbatim list or no {TESTS_KEY} folder"
        ) from exc
    checks = sorted((p, m.group(1)) for p in verbatim if (m := CHECK_PATH.fullmatch(p)))
    tests = sorted(p.relative_to(root).as_posix() for p in (root / folder).glob("test_*.py"))
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
                f"{check} has no test file in the {TESTS_KEY} folder that imports or runs it"
            )
    problems += own_adr_problems(root, argv)
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if not problems:
        print(f"ok {NAME} ({len(checks)} checks, {len(tests)} test files)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
