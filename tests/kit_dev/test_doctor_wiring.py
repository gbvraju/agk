"""Kit-only tests of the doctor wiring: manifest, version, a real install compared with this kit."""

from __future__ import annotations

import json
import subprocess
import sys

from conftest import KIT_ROOT, clean_env, expected_files, manifest

INSTALLED = {"scripts/agk/doctor.py", "tests/kit/test_doctor.py"}
OK_API = KIT_ROOT / "tests" / "kit" / "fixtures" / "doctor" / "ok" / "api"


def doctor(root, *extra):
    proc = subprocess.run(
        [
            sys.executable,
            str(KIT_ROOT / "scripts" / "agk" / "doctor.py"),
            "--api-dir", str(OK_API),
            "--kit-root", str(KIT_ROOT),
            "--repo", "example-owner/example-repo",
            "--json", *extra, str(root),
        ],
        capture_output=True,
        text=True,
        env=clean_env(),
    )  # fmt: skip
    return proc, {c["id"]: c for c in json.loads(proc.stdout)["checks"]}


def test_ac1_doctor_files_and_fixtures_are_installed_by_init_and_adopt():
    """REQ-002 AC1: SPEC-0006 rule 19."""
    assert INSTALLED <= set(manifest()["verbatim"])
    assert INSTALLED <= expected_files()
    fixtures = {p for p in manifest()["verbatim"] if p.startswith("tests/kit/fixtures/doctor/")}
    on_disk = {
        p.relative_to(KIT_ROOT).as_posix()
        for p in (KIT_ROOT / "tests/kit/fixtures/doctor").rglob("*")
        if p.is_file()
    }
    assert on_disk == fixtures and len(fixtures) > 50


def test_ac1_kit_version_is_at_least_0_8_0():
    """REQ-002 AC1: the doctor item bumps the minor version."""
    version = tuple(int(part) for part in manifest()["kit_version"].split("."))
    assert version >= (0, 8, 0)


def test_ac1_a_fresh_install_equals_this_kit_and_names_the_placeholder_team(installed):
    """REQ-002 AC1: SPEC-0006 rules 5, 8 (and SPEC-0001's residual: the placeholder is reported)."""
    proc, report = doctor(installed)
    assert report["kit-version"]["status"] == "ok"
    assert report["vendored-missing"]["status"] == "ok", report["vendored-missing"]["message"]
    assert report["vendored-differs"]["status"] == "ok", report["vendored-differs"]["message"]
    assert report["placeholder-team-reviewers"]["status"] == "fail"
    assert report["placeholder-team-codeowners"]["status"] == "fail"
    assert report["drift-workflow-file"]["status"] == "ok"
    assert proc.returncode == 1


def test_ac1_an_edited_or_deleted_vendored_file_is_reported(installed):
    """REQ-002 AC1: SPEC-0006 rule 8 against the real kit."""
    (installed / "scripts" / "agk" / "check_adrs.py").write_text("# weakened\n", encoding="utf-8")
    (installed / ".claude" / "hooks" / "stop_check.py").unlink()
    _, report = doctor(installed)
    assert "scripts/agk/check_adrs.py" in report["vendored-differs"]["message"]
    assert ".claude/hooks/stop_check.py" in report["vendored-missing"]["message"]


def test_ac1_a_weakened_settings_file_shows_as_vendored_differs(installed):
    """REQ-002 AC2: SPEC-0006 rule 8 (the deny list is covered by the vendored comparison)."""
    path = installed / ".claude" / "settings.json"
    path.write_text(path.read_text(encoding="utf-8").replace("deny", "denied"), encoding="utf-8")
    _, report = doctor(installed)
    assert ".claude/settings.json" in report["vendored-differs"]["message"]


def test_ac1_a_stale_agk_toml_version_is_a_kit_version_finding(installed):
    """REQ-002 AC1: SPEC-0006 rule 8 (version mismatch, no comparison)."""
    toml = installed / "agk.toml"
    text = toml.read_text(encoding="utf-8")
    toml.write_text(text.replace(manifest()["kit_version"], "0.1.0"), encoding="utf-8")
    _, report = doctor(installed)
    assert report["kit-version"]["status"] == "fail"
    assert report["vendored-differs"]["reason"] == "version-mismatch"
