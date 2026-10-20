"""Kit-only tests of the drift audit wiring: manifest, version, installed layout."""

from __future__ import annotations

import subprocess
import sys

from conftest import KIT_ROOT, assert_lean, clean_env, manifest

INSTALLED = {
    ".github/workflows/drift-audit.yml",
    "scripts/agk/drift_audit.py",
    "tests/kit/drift_fixtures.py",
    "tests/kit/test_drift_audit.py",
    "tests/kit/test_drift_workflow.py",
}


def test_ac1_drift_audit_files_are_installed_by_init_and_adopt():
    """REQ-011 AC1: rule 16."""
    assert_lean(INSTALLED)


def test_ac1_kit_version_is_at_least_0_6_0():
    """REQ-011 AC1: ADR-0012 shipped the drift audit in 0.6.0; later versions keep it."""
    version = tuple(int(part) for part in manifest()["kit_version"].split("."))
    assert version >= (0, 6, 0)


def test_ac1_requirement_011_is_unchanged_and_planned():
    """REQ-011 AC1: an agent never marks a requirement done."""
    text = (KIT_ROOT / "docs" / "requirements.md").read_text(encoding="utf-8")
    section = text.split("### REQ-011", 1)[1].split("\n### ", 1)[0]
    assert "AC1 weekly; AC2 one issue per run; AC3 read-only" in section
    assert "- Status: planned" in section


def test_ac1_installed_repository_gets_the_workflow_and_can_run_the_audit(installed):
    """REQ-011 AC1: rule 16. The installed script runs in an installed repository."""
    assert (installed / ".github" / "workflows" / "drift-audit.yml").is_file()
    proc = subprocess.run(
        [sys.executable, "scripts/agk/drift_audit.py", "--today", "2026-10-15"],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.startswith("agk drift audit 2026-10-15 (window 2026-10-08 to 2026-10-15)")
    assert proc.stdout.rstrip().endswith("<!-- agk-drift-audit -->")
