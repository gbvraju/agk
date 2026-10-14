"""Tests of agk.mk and of how kit tests are collected (SPEC-0002 rules 5, 6, 10)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def env_without_flag() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != "AGK_KIT_TESTS"}


def make_n(target: str) -> str:
    proc = subprocess.run(
        ["make", "-f", "agk.mk", "-n", target], cwd=ROOT, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_ac1_agk_governance_runs_every_check():
    """REQ-010 AC1: rule 5."""
    out = make_n("agk-governance")
    for script in sorted((ROOT / "scripts" / "agk").glob("check_*.py")):
        if script.name == "check_pr_body.py":
            continue  # runs in CI against the PR body, not in the local target
        assert f"scripts/agk/{script.name}" in out, script.name
    assert "reviewers.py --check" in out and "reviewers.py --check-codeowners" in out


def test_ac1_agk_test_sets_the_flag_and_selects_its_own_ini():
    """REQ-010 AC1: rule 6."""
    out = make_n("agk-test")
    assert "AGK_KIT_TESTS=1" in out
    assert "-c tests/kit/pytest.ini" in out and "tests/kit" in out


def test_ac1_agk_lint_is_isolated_and_limited_to_lint_paths():
    """REQ-010 AC1: rule 10."""
    out = make_n("agk-lint")
    assert "--isolated" in out
    paths = subprocess.run(
        [sys.executable, "scripts/agk/config.py", "lint_paths"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert paths
    for path in paths:
        assert path in out
    assert not out.rstrip().endswith(" .")


def test_ac1_kit_tests_are_not_collected_without_the_flag():
    """REQ-010 AC1: rule 6. A bare pytest run collects no tests/kit test."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/kit", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env_without_flag(),
    )
    assert "test_agk_mk.py" not in proc.stdout
    assert proc.returncode == 5


def test_ac1_kit_tests_are_collected_with_the_flag():
    """REQ-010 AC1: rule 6."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/kit", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "AGK_KIT_TESTS": "1"},
    )
    assert proc.returncode == 0
    assert "test_agk_mk.py" in proc.stdout


def copy_kit(dest: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache")
    shutil.copytree(ROOT / "scripts" / "agk", dest / "scripts" / "agk", ignore=ignore)
    shutil.copytree(ROOT / "tests" / "kit", dest / "tests" / "kit", ignore=ignore)


def test_ac1_project_pytest_config_is_neither_read_nor_needed(tmp_path):
    """REQ-010 AC1: rule 6. A hostile project pytest config does not affect the kit's own run."""
    copy_kit(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "--definitely-not-a-flag"\n'
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            "tests/kit/pytest.ini",
            "tests/kit",
            "--collect-only",
            "-q",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "AGK_KIT_TESTS": "1"},
    )
    assert proc.returncode == 0, proc.stdout[-500:] + proc.stderr[-500:]
    assert "test_agk_mk.py" in proc.stdout


def test_ac1_bare_pytest_in_a_project_collects_no_kit_test(tmp_path):
    """REQ-010 AC1: rule 6. The project's own run (no -c, no flag) ignores tests/kit."""
    copy_kit(tmp_path)
    (tmp_path / "tests" / "test_own.py").write_text("def test_own():\n    assert True\n")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env_without_flag(),
    )
    assert "tests/test_own.py::test_own" in proc.stdout
    assert "tests/kit/" not in proc.stdout
