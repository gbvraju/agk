"""A test under the pinned clock reads no live clock (brief #1791, ADR-0750; REQ-053).

The `clock` fixture of `conftest.py` pins the clock `session.py` reads. A test module that opts in to it
(`usefixtures("clock")`, or a test that takes `clock`), and each helper it imports from `test_session` or
`test_session_flow`, builds its times from that pin: a live read there (`datetime.now(`, `datetime.utcnow(`,
`date.today(`, `time.time(`) outside `iso` and `Day`, which follow the pin, makes an age or a day the test
asserts differ from the one the code printed on a slow runner or across midnight UTC. Reads files only."""

from __future__ import annotations

import ast
from pathlib import Path

KIT = Path(__file__).resolve().parent
LIVE = ("datetime.now", "datetime.utcnow", "date.today", "time.time")
FOLLOW = {"iso", "Day"}  # they read the pin when it is set
HELPERS = ("test_session", "test_session_flow")
RULE = "a test under the pinned clock reads no live clock; build times with iso or Day (brief #1791)"


def _reads(node: ast.AST) -> list[int]:
    return sorted(
        call.lineno
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and any(ast.unparse(call.func).endswith(name) for name in LIVE)
    )


def _defs(tree: ast.Module) -> dict[str, ast.AST]:
    kinds = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    return {node.name: node for node in tree.body if isinstance(node, kinds)}


def _pinned(tree: ast.Module) -> tuple[bool, list[ast.AST]]:
    """Whether the whole module opts in, and the tests that take `clock` one by one."""
    defs = _defs(tree)
    if "clock" in defs:  # its own `clock` fixture, not the pin
        return False, []
    whole = any(
        isinstance(n, ast.Call) and ast.unparse(n).endswith("usefixtures('clock')")
        for n in ast.walk(tree)
    )
    takes = [
        d
        for d in defs.values()
        if isinstance(d, ast.FunctionDef) and "clock" in [a.arg for a in d.args.args]
    ]
    return whole, takes


def findings(root: Path = KIT) -> list[str]:
    trees = {p.stem: (p, ast.parse(p.read_text(encoding="utf-8"))) for p in sorted(root.glob("test_*.py"))}
    seen: set[tuple[Path, int]] = set()
    for path, tree in list(trees.values()):
        whole, takes = _pinned(tree)
        scope: list[tuple[Path, ast.AST]] = [(path, d) for d in takes]
        if whole:
            scope = [(path, n) for name, n in _defs(tree).items() if name not in FOLLOW]
            scope += [(path, n) for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.ClassDef))]
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in HELPERS and node.module in trees:
                    src, other = trees[node.module]
                    helpers = _defs(other)
                    scope += [(src, helpers[a.name]) for a in node.names if a.name in helpers and a.name not in FOLLOW]
        for src, node in scope:
            seen.update((src, line) for line in _reads(node))
    return [f"{p.relative_to(root.parent.parent) if root == KIT else p.name}:{n}: {RULE}" for p, n in sorted(seen)]


def _module(tmp_path: Path, name: str, text: str) -> Path:
    (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


HEAD = "import pytest\nfrom datetime import UTC, datetime\n"


def test_a_live_read_under_the_pin_fails_naming_the_file_the_line_and_the_rule(tmp_path):
    """REQ-053"""
    body = HEAD + 'pytestmark = pytest.mark.usefixtures("clock")\n\ndef test_x():\n    datetime.now(UTC)\n'
    root = _module(tmp_path, "test_a.py", body)
    assert findings(root) == [f"test_a.py:6: {RULE}"]


def test_only_iso_under_the_pin_passes_and_a_test_taking_clock_is_checked(tmp_path):
    """REQ-053"""
    ok = HEAD + "def iso():\n    return datetime.now(UTC)\n\n"
    ok += 'pytestmark = pytest.mark.usefixtures("clock")\n\ndef test_x():\n    iso()\n'
    root = _module(tmp_path, "test_a.py", ok)
    _module(tmp_path, "test_b.py", HEAD + "def test_y(clock):\n    datetime.now(UTC)\n")
    assert findings(root) == [f"test_b.py:4: {RULE}"]


def test_a_helper_imported_into_a_pinned_module_is_checked(tmp_path):
    """REQ-053"""
    root = _module(tmp_path, "test_session.py", HEAD + "def take():\n    return datetime.now(UTC)\n")
    pinned = 'import pytest\nfrom test_session import take\npytestmark = pytest.mark.usefixtures("clock")\n'
    _module(tmp_path, "test_c.py", pinned)
    assert findings(root) == [f"test_session.py:4: {RULE}"]


def test_a_module_without_the_pin_or_with_its_own_clock_is_not_checked(tmp_path):
    """REQ-053"""
    root = _module(tmp_path, "test_a.py", HEAD + "def test_x():\n    datetime.now(UTC)\n")
    own = HEAD + "@pytest.fixture\ndef clock():\n    return 0\n\ndef test_y(clock):\n    datetime.now(UTC)\n"
    _module(tmp_path, "test_b.py", own)
    assert findings(root) == []


def test_the_kit_tests_read_no_live_clock_under_the_pin():
    """REQ-053"""
    assert findings() == []
