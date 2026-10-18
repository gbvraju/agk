"""Installed fixtures must be invisible to a project's own test runners.

An adopted repository gets `tests/kit/fixtures/` verbatim. A language toolchain's default test
discovery must not find a file there, or adopting the kit would break the product's own tests.
Go ignores any directory named `testdata`; Python's runner is told to ignore `tests/kit` unless the
kit's own targets set `AGK_KIT_TESTS`, and no fixture is named as a Python test; JavaScript runners
match `*.test.*`, `*.spec.*` and `__tests__` only, and no fixture is named so.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists, no shell
import tempfile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
PYTHON_TEST = re.compile(r"^(test.*|.*_test)\.py$")
JS_TEST = re.compile(r"^.*\.(test|spec)\.(js|jsx|ts|tsx|mjs|cjs)$")


def files() -> list[Path]:
    return sorted(p for p in FIXTURES.rglob("*") if p.is_file())


def hidden(path: Path) -> bool:
    """True when a path segment is `testdata`, which Go does not descend into."""
    return "testdata" in path.relative_to(FIXTURES).parts


def rel(paths: list[Path]) -> list[str]:
    return [p.relative_to(FIXTURES).as_posix() for p in paths]


def test_ac1_no_go_file_is_visible_to_go_test():
    """REQ-010 AC1: a `.go` fixture sits below a directory named testdata."""
    seen = [p for p in files() if p.suffix == ".go" and not hidden(p)]
    assert rel(seen) == []


def test_ac1_no_fixture_is_named_as_a_python_or_javascript_test():
    """REQ-010 AC1: no `test*.py`, `*_test.py`, `*.test.js`, `*.spec.ts` or `__tests__` fixture."""
    seen = [
        p
        for p in files()
        if not hidden(p)
        and (
            PYTHON_TEST.match(p.name)
            or JS_TEST.match(p.name)
            or "__tests__" in p.relative_to(FIXTURES).parts
        )
    ]
    assert rel(seen) == []


def test_ac1_the_go_fixtures_still_exist_so_the_rule_is_not_vacuous():
    """REQ-010 AC1: the go-style case keeps its Go tests, under testdata."""
    found = [p for p in files() if p.suffix == ".go"]
    assert found
    assert all(hidden(p) for p in found)


@pytest.mark.skipif(shutil.which("go") is None, reason="go is not installed")
def test_ac1_go_test_over_the_fixtures_finds_nothing_to_fail():
    """REQ-010 AC1: `go test ./...` in a module that holds the fixtures passes, offline."""
    with tempfile.TemporaryDirectory() as tmp:
        module = Path(tmp) / "mod"
        shutil.copytree(FIXTURES, module / "fixtures")
        (module / "go.mod").write_text("module x\n\ngo 1.21\n", encoding="utf-8")
        (module / "ok_test.go").write_text(
            'package x\n\nimport "testing"\n\nfunc TestOk(t *testing.T) {}\n', encoding="utf-8"
        )
        env = {**os.environ, "GOFLAGS": "-mod=mod", "GOTOOLCHAIN": "local", "GOPROXY": "off"}
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["go", "test", "./..."],
            cwd=module,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok" in proc.stdout
