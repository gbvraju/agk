"""Installed scripts import only installed modules (brief #1214, ADR-0514, REQ-039).

A project installed with `init.py` holds the manifest's installed list of `scripts/agk/`, never the
kit-only files (`init.py`, `adopt.py`, ...). A module-level import of a file the project does not
have stops every governance run at its first step (`doctor.py --paused`). Invented trees only
(example.com), no network.
"""

from __future__ import annotations

import ast
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import doctor

KIT = Path(__file__).resolve().parents[2]
KIT_ONLY_MARK = "kit-only"  # a function-level import of a kit-only module says so on its line


def installed_scripts(experimental: bool) -> list[str]:
    """The `scripts/agk/*.py` paths that an `init.py` install writes."""
    manifest = json.loads((KIT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    files, blocks = doctor.installed_files(manifest, "init", experimental)
    return sorted(
        p for p in [*files, *blocks] if p.startswith("scripts/agk/") and p.endswith(".py")
    )


def foreign_imports(path: Path, modules: set[str]) -> list[str]:
    """The imports in PATH of a module that is neither installed (MODULES) nor the standard
    library: every one at module level, and one inside a function unless its line is marked
    kit-only (it is guarded, or runs only in the kit repository)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text)
    nested = {
        id(n)
        for f in ast.walk(tree)
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
        for n in ast.walk(f)
    }
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module.split(".")[0]]
        else:
            continue
        for name in names:
            if name in modules or name in sys.stdlib_module_names or name == "__future__":
                continue
            in_function = id(node) in nested
            if in_function and KIT_ONLY_MARK in lines[node.lineno - 1]:
                continue
            where = "function" if in_function else "module"
            found.append(f"{path.name}:{node.lineno} imports {name} ({where} level)")
    return found


def test_a_every_installed_script_imports_only_installed_modules():
    """REQ-039: brief #1214 answer 2 (each installed script's imports name an installed module
    or the standard library)."""
    problems = []
    for experimental in (False, True):
        scripts = installed_scripts(experimental)
        modules = {Path(p).stem for p in scripts}
        for rel in scripts:
            problems += foreign_imports(KIT / rel, modules)
    assert sorted(set(problems)) == []


def test_b_the_check_finds_a_module_level_import_of_a_kit_only_file(tmp_path):
    """REQ-039: brief #1214 answer 2 (the test of the check: `import adopt` at module level is
    found, a marked function-level one is not)."""
    script = tmp_path / "example.py"
    script.write_text(
        "import json\nimport adopt\n\n\ndef f():\n"
        "    import init  # noqa: PLC0415 - kit-only\n    import impact\n",
        encoding="utf-8",
    )
    assert foreign_imports(script, {"common"}) == [
        "example.py:2 imports adopt (module level)",
        "example.py:7 imports impact (function level)",
    ]


def test_c_doctor_paused_runs_in_an_init_install(tmp_path):
    """REQ-039: brief #1214 answers 2 and 3 (in an `init.py` install, `python3 -I
    scripts/agk/doctor.py --paused` exits 0, not `No module named 'adopt'`)."""
    target = tmp_path / "project"
    target.mkdir()
    (target / "README.md").write_text("An example project, example.com.\n", encoding="utf-8")
    init = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT / "scripts/agk/init.py"), str(target), "--unreleased"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert init.returncode == 0, init.stdout + init.stderr
    assert not (target / "scripts/agk/adopt.py").exists()
    run = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", "scripts/agk/doctor.py", "--paused"],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "No module named" not in run.stderr
    assert (run.returncode, run.stdout.strip()) == (0, "agk not paused")
