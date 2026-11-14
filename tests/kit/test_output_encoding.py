"""Every installed check writes UTF-8 (brief #1233, ADR-0524, REQ-014).

On a Windows console Python writes stdout in the console's code page (cp1252), so the first
non-ASCII character a check prints (`check_plan.py` names a design heading with an arrow) stopped
governance with `UnicodeEncodeError`. `common.utf8_output` reconfigures stdout and stderr to UTF-8,
and every installed script that prints calls it first. Here the console is simulated with
`PYTHONIOENCODING=cp1252` and `PYTHONUTF8=0`; the data is invented.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGK = ROOT / "scripts" / "agk"
ARROW = "→"
HELPER = "utf8_output"
# Imported by other scripts only; they print under the caller's main, which calls the helper.
LIBRARIES = frozenset({"scripts/agk/common.py", "scripts/agk/session_plan.py"})


def console_env(cp1252: bool) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        env.pop(name, None)
    if cp1252:
        env.update({"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"})
    else:
        env.update({"PYTHONIOENCODING": "utf-8"})
    return env


def run(args: list[str], cwd: Path, cp1252: bool) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, *args], cwd=cwd, capture_output=True, env=console_env(cp1252), timeout=60
    )


def printing_scripts() -> list[str]:
    """The installed scripts under scripts/agk/ that print and run as a program."""
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    found = []
    for key in ("verbatim", "experimental"):
        for rel in manifest.get(key) or []:
            if not (rel.startswith("scripts/agk/") and rel.endswith(".py")) or rel in LIBRARIES:
                continue
            text = (ROOT / rel).read_text(encoding="utf-8")
            prints = "print(" in text or "sys.stdout.write" in text or "sys.stderr.write" in text
            if prints and "__main__" in text:
                found.append(rel)
    return sorted(set(found))


PROBE = """
import sys
sys.path.insert(0, sys.argv[1])
import common
if sys.argv[2] == "call":
    common.utf8_output()
print("a \\u2192 b")
print("err \\u2192", file=sys.stderr)
"""


def test_the_helper_makes_a_cp1252_console_write_utf8(tmp_path):
    """REQ-014: without the call the simulated console fails at the arrow; with it, UTF-8."""
    without = run(["-c", PROBE, str(AGK), "no"], tmp_path, cp1252=True)
    assert without.returncode == 1 and b"UnicodeEncodeError" in without.stderr
    called = run(["-c", PROBE, str(AGK), "call"], tmp_path, cp1252=True)
    assert called.returncode == 0, called.stderr.decode("utf-8", "replace")
    assert called.stdout.decode("utf-8") == f"a {ARROW} b\n"
    assert called.stderr.decode("utf-8") == f"err {ARROW}\n"


def test_the_helper_leaves_a_utf8_stream_and_a_stream_without_reconfigure(monkeypatch):
    """REQ-014: a stream that is already UTF-8, or not a text stream, is left as it is."""
    import io

    import common

    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", raw)
    wrapped = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="strict")
    monkeypatch.setattr(sys, "stderr", wrapped)
    common.utf8_output()
    assert sys.stdout is raw
    assert sys.stderr is wrapped and wrapped.errors == "strict"


def plan_tree(root: Path) -> None:
    (root / "docs" / "plan").mkdir(parents=True)
    (root / "docs" / "sources").mkdir(parents=True)
    (root / "docs" / "sources" / "screens.md").write_text(
        f"Source: Screens\nKind: design\nVersion: 1\nDate: 2026-11-01\n\n"
        f"## Login {ARROW} Home/empty\n\nAn invented screen of example.com.\n",
        encoding="utf-8",
    )


def test_check_plan_names_a_heading_with_an_arrow_on_a_cp1252_console(tmp_path):
    """REQ-014, the reported case: the plan check prints the heading and exits as on UTF-8."""
    plan_tree(tmp_path)
    args = [str(AGK / "check_plan.py"), "--root", str(tmp_path)]
    utf8, console = run(args, tmp_path, cp1252=False), run(args, tmp_path, cp1252=True)
    assert ARROW.encode("utf-8") in utf8.stdout
    assert b"UnicodeEncodeError" not in console.stderr, console.stderr.decode("utf-8", "replace")
    assert (console.returncode, console.stdout) == (utf8.returncode, utf8.stdout)


def test_config_names_an_unknown_key_with_an_arrow_on_a_cp1252_console(tmp_path):
    """REQ-014: `config.py` echoes the key it does not know, here one with an arrow."""
    args = [str(AGK / "config.py"), f"no-such-key-{ARROW}"]
    utf8, console = run(args, tmp_path, cp1252=False), run(args, tmp_path, cp1252=True)
    assert ARROW.encode("utf-8") in utf8.stdout + utf8.stderr
    assert b"UnicodeEncodeError" not in console.stderr, console.stderr.decode("utf-8", "replace")
    assert (console.returncode, console.stdout, console.stderr) == (
        utf8.returncode,
        utf8.stdout,
        utf8.stderr,
    )


RUNNER = """
import runpy, sys
script = sys.argv[1]
sys.path.insert(0, sys.argv[2])
sys.argv = [script, "--agk-no-such-option-\\u2192"]
code = 0
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as exc:
    code = exc.code
sys.stdout.write("after \\u2192\\n")
sys.stdout.flush()
sys.exit(code if isinstance(code, int) else 1)
"""


@pytest.mark.parametrize("rel", printing_scripts())
def test_every_printing_script_writes_utf8_on_a_cp1252_console(rel, tmp_path):
    """REQ-014: each script, given an option it refuses, exits as it does on a UTF-8 console,
    and the arrow written after its start reaches the console instead of stopping it."""
    args = ["-c", RUNNER, str(ROOT / rel), str(AGK)]
    utf8, console = run(args, tmp_path, cp1252=False), run(args, tmp_path, cp1252=True)
    assert b"UnicodeEncodeError" not in console.stderr, console.stderr.decode("utf-8", "replace")
    assert console.returncode == utf8.returncode
    assert console.stdout.endswith(f"after {ARROW}\n".encode())


def calls_helper_first(tree: ast.Module) -> bool:
    def is_call(stmt: ast.stmt) -> bool:
        if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
            return False
        func = stmt.value.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        return name == HELPER

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                body = body[1:]
            return bool(body) and is_call(body[0])
    return any(is_call(stmt) for stmt in tree.body)


def test_every_installed_script_that_prints_calls_the_helper_first():
    """REQ-014: the first statement of `main` (after its docstring), or a module-level call for a
    script without `main`, is `utf8_output()`."""
    assert len(printing_scripts()) > 50
    missing = [
        rel
        for rel in printing_scripts()
        if not calls_helper_first(ast.parse((ROOT / rel).read_text(encoding="utf-8")))
    ]
    assert missing == []
