"""Kit-only tests of the metrics wiring: manifest, version, installed layout, the printed note."""

from __future__ import annotations

import subprocess
import sys

from conftest import (
    KIT_ROOT,
    assert_lean,
    clean_env,
    kit_fixture_files,
    manifest,
    run_init,
)

INSTALLED = {
    ".github/workflows/metrics.yml",
    "scripts/agk/metrics.py",
    "tests/kit/test_metrics.py",
    "tests/kit/test_metrics_workflow.py",
}


def test_ac1_metrics_files_and_fixtures_are_installed_by_init_and_adopt():
    """REQ-012 AC1: SPEC-0007 rule 19."""
    assert_lean(INSTALLED)
    fixtures = kit_fixture_files("tests/kit/fixtures/metrics")
    assert len(fixtures) > 100 and not fixtures & set(manifest()["verbatim"])


def test_ac1_kit_version_is_at_least_0_7_0():
    """REQ-012 AC1: the metrics item bumps the minor version."""
    version = tuple(int(part) for part in manifest()["kit_version"].split("."))
    assert version >= (0, 7, 0)


def test_ac1_installed_repository_gets_the_workflow_and_can_print_a_title(installed):
    """REQ-012 AC1: rule 19. The installed script runs in an installed repository."""
    assert (installed / ".github" / "workflows" / "metrics.yml").is_file()
    proc = subprocess.run(
        [sys.executable, "scripts/agk/metrics.py", "--today", "2026-10-14", "--print-title"],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == "agk metrics 2026-W41\n"


def test_ac1_init_prints_the_issues_write_note(tmp_path):
    """REQ-012 AC1: rule 19 (init and adopt print that the workflows need `issues: write`)."""
    target = tmp_path / "t"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    proc = run_init(target, "--dry-run")
    assert "(`issues: write`)" in proc.stdout
    assert "metrics.yml" in proc.stdout


def test_ac1_adopt_prints_the_issues_write_note(tmp_path):
    """REQ-012 AC1: rule 19."""
    target = tmp_path / "t"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    proc = subprocess.run(
        [
            sys.executable,
            str(KIT_ROOT / "scripts" / "agk" / "adopt.py"),
            str(target),
            "--dry-run",
            "--unreleased",
        ],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert "(`issues: write`)" in proc.stdout
