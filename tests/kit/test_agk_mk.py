"""Tests of agk.mk and of how kit tests are collected (SPEC-0002 rules 5, 6, 10)."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def env_without_flag() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != "AGK_KIT_TESTS"}


def make_n(target: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-f", "agk.mk", "-n", target], cwd=ROOT, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_ac1_agk_governance_runs_every_check():
    """REQ-010 AC1: rule 5."""
    out = make_n("agk-governance")
    for script in sorted((ROOT / "scripts" / "agk").glob("check_*.py")):
        if script.name in ("check_pr_body.py", "check_review_report.py"):
            continue  # these take a PR body or a report as input; not part of the local target
        if script.name == "check_release.py":
            continue  # kit-only: the workflow step `Release check` runs it where kit/agk-kit.mk is
        if script.name == "check_design.py":
            continue  # kit-only until a governance step is decided (ADR-0104 residual)
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
    paths = subprocess.run(  # nosec B603 - fixed argument list, no shell
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
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
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
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
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
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
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
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env_without_flag(),
    )
    assert "tests/test_own.py::test_own" in proc.stdout
    assert "tests/kit/" not in proc.stdout


def project_with(tmp_path: Path, toml: str) -> Path:
    shutil.copytree(
        ROOT / "scripts" / "agk",
        tmp_path / "scripts" / "agk",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copy(ROOT / "agk.mk", tmp_path / "agk.mk")
    (tmp_path / "agk.toml").write_text(toml)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)  # nosec B603 B607 - fixed argument list, no shell
    return tmp_path


def run_target(project: Path, target: str):
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-f", "agk.mk", target], cwd=project, capture_output=True, text=True
    )


def test_ac1_project_test_target_runs_the_configured_command(tmp_path):
    """REQ-010 AC1: rule 5. project_tests is run, and its exit code is the target's."""
    proj = project_with(tmp_path, 'project_tests = "echo RAN_PROJECT_TESTS; exit 7"\n')
    proc = run_target(proj, "agk-project-test")
    assert proc.returncode != 0
    assert "RAN_PROJECT_TESTS" in proc.stdout
    ok = project_with(tmp_path / "ok", 'project_tests = "echo FINE"\n')
    assert run_target(ok, "agk-project-test").returncode == 0


def test_ac1_project_test_target_prints_a_notice_when_empty(tmp_path):
    """REQ-010 AC1: rule 5 (adopt: empty)."""
    proj = project_with(tmp_path, "default_branch = 'main'\n")
    proc = run_target(proj, "agk-project-test")
    assert proc.returncode == 0
    assert "no project_tests configured" in proc.stdout


def project(tmp_path: Path, with_tests: bool, lint_paths: str) -> Path:
    """A project with agk.mk, a scripts/agk, an agk.toml and, maybe, the kit's tests folder."""
    root = tmp_path / ("with" if with_tests else "without")
    (root / "scripts" / "agk").mkdir(parents=True)
    shutil.copy(ROOT / "agk.mk", root / "agk.mk")
    shutil.copy(ROOT / "scripts" / "agk" / "config.py", root / "scripts" / "agk" / "config.py")
    shutil.copy(ROOT / "scripts" / "agk" / "common.py", root / "scripts" / "agk" / "common.py")
    (root / "agk.toml").write_text(f"lint_paths = {lint_paths}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)  # nosec B603 B607 - fixed list
    if with_tests:  # the kit repository: kit/agk-kit.mk defines agk-test
        (root / "kit").mkdir()
        shutil.copy(ROOT / "kit" / "agk-kit.mk", root / "kit" / "agk-kit.mk")
        (root / "tests" / "kit").mkdir(parents=True)
        (root / "tests" / "kit" / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    return root


def test_ac1_agk_test_without_the_kit_tests_says_so_and_succeeds(tmp_path):
    """REQ-009 AC2: lean install (ADR-0052): a project has no tests/kit/, agk-test is a notice."""
    root = project(tmp_path, with_tests=False, lint_paths='["scripts/agk"]')
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-f", "agk.mk", "agk-test"],
        cwd=root,
        capture_output=True,
        text=True,
        env=env_without_flag(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "not installed in this repository" in proc.stdout and "-m pytest" not in proc.stdout


def test_ac1_agk_test_with_the_kit_tests_runs_them(tmp_path):
    """REQ-009 AC2: the kit repository keeps running its tests through the same target."""
    root = project(tmp_path, with_tests=True, lint_paths='["scripts/agk"]')
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-f", "agk.mk", "-n", "agk-test"],
        cwd=root,
        capture_output=True,
        text=True,
        env=env_without_flag(),
    )
    assert "AGK_KIT_TESTS=1" in proc.stdout and "-c tests/kit/pytest.ini" in proc.stdout


def test_ac1_agk_lint_skips_a_lint_path_that_is_not_there(tmp_path):
    """REQ-009 AC2: an older agk.toml still lists tests/kit; lint must not fail on its absence."""
    root = project(tmp_path, with_tests=False, lint_paths='["scripts/agk", "tests/kit"]')
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-f", "agk.mk", "-n", "agk-lint"], cwd=root, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert "scripts/agk" in proc.stdout and "tests/kit" not in proc.stdout


def test_ac1_agk_test_with_only_a_kept_leftover_of_the_kit_tests_is_still_a_notice(tmp_path):
    """REQ-009 AC2: an upgrade keeps an edited tests/kit file; that is not a suite to run."""
    root = project(tmp_path, with_tests=False, lint_paths='["scripts/agk"]')
    (root / "tests" / "kit").mkdir(parents=True)
    (root / "tests" / "kit" / "test_facts.py").write_text("# edited here\n", encoding="utf-8")
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-f", "agk.mk", "agk-test"],
        cwd=root,
        capture_output=True,
        text=True,
        env=env_without_flag(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "not installed in this repository" in proc.stdout and "Traceback" not in proc.stderr
