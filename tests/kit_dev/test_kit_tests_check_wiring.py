"""Kit-only tests of the installed-tests check: it passes on the kit itself and is wired in."""

from __future__ import annotations

import subprocess
import sys

from conftest import KIT_ROOT, assert_lean, clean_env, manifest

CHECK = KIT_ROOT / "scripts" / "agk" / "check_kit_tests.py"
INSTALLED = {"scripts/agk/check_kit_tests.py", "tests/kit/test_check_kit_tests.py"}


def test_ac1_the_check_passes_on_the_kit_itself():
    """REQ-009 AC2: every installed check has an installed test, in the real manifest."""
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=KIT_ROOT,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.startswith("ok kit-tests")


def test_ac1_the_check_and_its_test_are_installed():
    """REQ-009 AC2: the check ships with its own installed test."""
    assert_lean(INSTALLED)


def test_ac1_agk_governance_runs_the_check():
    """REQ-009 AC2."""
    text = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    assert "$(PY) scripts/agk/check_kit_tests.py" in text


def test_ac1_kit_version_is_at_least_0_6_2():
    """REQ-009 AC2: ADR-0014."""
    version = tuple(int(part) for part in manifest()["kit_version"].split("."))
    assert version >= (0, 6, 2)


def test_ac1_installed_repository_runs_the_check_as_a_no_op(installed):
    """REQ-009 AC2: an installed repository has no kit manifest."""
    proc = subprocess.run(
        [sys.executable, "scripts/agk/check_kit_tests.py"],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout
    assert "no kit/manifest.json" in proc.stdout
