"""The installed `plan_intake.py render` works without the plugin (brief #1184, ADR-0503; REQ-050).

REQ-050 AC2.

A fresh `init.py --unreleased` project holds `scripts/agk/new_spec.py` beside `plan_intake.py`, so
the project's own copy of `render` (the command of `docs/guides/planning.md` step 6) finds it and
writes the Draft spec, in a cloud session that does not load the plugin as on a laptop. Invented
sources only (example.com); the render runs in a child process from the project's copy, no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import init
import pytest
from test_plan_intake import PRD, PRD_TEXT, SOW, SOW_TEXT, write
from test_plan_render import LISTED, proposals

NEW_SPEC = "scripts/agk/new_spec.py"
KIT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def project(tmp_path: Path, capsys) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    assert init.main([str(root), "--unreleased"]) == 0
    capsys.readouterr()
    write(root, SOW, SOW_TEXT)
    write(root, PRD, PRD_TEXT)
    return root


def test_ac2_a_fresh_project_holds_new_spec_beside_plan_intake(project: Path) -> None:
    """REQ-050 AC2: (a) init installs `new_spec.py`, which `render` imports from beside itself."""
    assert (project / NEW_SPEC).is_file()
    assert (project / "scripts/agk/plan_intake.py").is_file()
    assert (project / "docs/specs/TEMPLATE.md").is_file()


def test_ac2_the_manifest_installs_new_spec_verbatim() -> None:
    """REQ-050 AC2: (c) `kit/manifest.json` lists `new_spec.py` in `verbatim`."""
    manifest = json.loads((KIT_ROOT / "kit/manifest.json").read_text(encoding="utf-8"))
    assert NEW_SPEC in manifest["verbatim"]


def test_ac2_the_installed_render_writes_the_plan_and_the_draft_spec(project: Path) -> None:
    """REQ-050 AC2: (b) the project's own `render` exits 0 and writes the Draft spec."""
    path = project.parent / "proposals.json"
    path.write_text(json.dumps(proposals()), encoding="utf-8")
    script = project / "scripts/agk/plan_intake.py"
    proc = subprocess.run(  # nosec B603 - a fixed argument list of the project's own copy
        [sys.executable, str(script), "render", "--proposals", str(path), "--root", "."],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "render needs new_spec.py" not in out
    for rel in LISTED:
        assert f"created {rel}" in out, out
        assert (project / rel).is_file(), rel
    spec = (project / "docs/specs/0001-orders.md").read_text(encoding="utf-8")
    assert spec.startswith("# SPEC-0001: Orders\n") and "- Status: Draft" in spec
