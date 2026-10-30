"""The doctor after a removal (brief #348 build (b), answer 5; ADR-0203; REQ-009).

A git work tree with no `agk.toml` and none of the kit's files left is reported as "no kit
installed" (exit 0), not as a failure; a directory that is not a work tree, and a work tree that
still holds kit files without `agk.toml`, keep the refusal of SPEC-0006 rule 13. No `gh` call.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

DOCTOR = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "doctor.py"


@pytest.fixture
def gh_log(tmp_path: Path) -> tuple[Path, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh-calls"
    gh = bin_dir / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\nexit 1\n', encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    return log, f"{bin_dir}{os.pathsep}{os.environ['PATH']}"


def doctor(*args: str, path: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env["PATH"] = path
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(DOCTOR), *args], capture_output=True, text=True, env=env
    )


def removed(tmp_path: Path) -> Path:
    """A work tree after the removal: the project's own files only."""
    root = tmp_path / "proj"
    (root / "docs" / "adr").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607
    (root / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    (root / "docs" / "adr" / "0001-adopt-agk.md").write_text("# ADR-0001\n", encoding="utf-8")
    return root


def test_after_removal_the_doctor_reports_no_kit_installed(tmp_path, gh_log):
    """REQ-009: answer 5 (after removal: "no kit installed", exit 0, no `gh`)."""
    log, path = gh_log
    proc = doctor(str(removed(tmp_path)), path=path)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines() == [
        "agk doctor none",
        "no kit installed: agk.toml and the kit's files are gone; nothing to check",
        "summary: no kit installed",
    ]
    assert not log.exists()


def test_the_json_report_says_no_kit_installed(tmp_path, gh_log):
    """REQ-009: answer 5 (the same state in the JSON report)."""
    _, path = gh_log
    proc = doctor("--json", str(removed(tmp_path)), path=path)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["state"] == "no kit installed" and data["checks"] == []
    assert data["summary"] == {"ok": 0, "fail": 0, "cannot-check": 0}


def test_the_paused_query_reads_not_paused_after_removal(tmp_path, gh_log):
    """REQ-009: answers 1 and 5 (no agk.toml is not paused)."""
    _, path = gh_log
    proc = doctor("--paused", str(removed(tmp_path)), path=path)
    assert (proc.returncode, proc.stdout) == (0, "agk not paused\n")


@pytest.mark.parametrize("left", ["agk.mk", "scripts/agk/common.py", ".github/workflows/proof.yml"])
def test_kit_files_without_agk_toml_stay_a_refusal(tmp_path, gh_log, left):
    """REQ-009: answer 5 (a half-removed kit is not "no kit installed": SPEC-0006 rule 13)."""
    _, path = gh_log
    root = removed(tmp_path)
    (root / left).parent.mkdir(parents=True, exist_ok=True)
    (root / left).write_text("x\n", encoding="utf-8")
    proc = doctor(str(root), path=path)
    assert proc.returncode == 1
    assert proc.stdout.startswith("refused: agk.toml missing")


def test_a_directory_that_is_not_a_work_tree_stays_a_refusal(tmp_path, gh_log):
    """REQ-009: answer 5 (SPEC-0006 rule 13 unchanged for a directory that is not a project)."""
    _, path = gh_log
    proc = doctor(str(tmp_path), path=path)
    assert proc.returncode == 1
    assert proc.stdout.startswith("refused: agk.toml missing")
