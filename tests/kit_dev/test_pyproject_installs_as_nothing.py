# ruff: noqa: F811 - the fixtures and helpers of test_upgrade are imported by name
"""The kit's root pyproject.toml installs as nothing (brief 236; the residual of 2026-10-22).

A host that runs `pip install .` at the root must succeed and install nothing, in a new project
(the template) and after `agk upgrade` (the two tables are added to an init install that lacks
them, once, and every other byte stays). No network: setuptools' own metadata call, no isolation."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest
from conftest import KIT_ROOT
from test_upgrade import PROTECTED, init_target, kit, run  # noqa: F401

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import upgrade  # noqa: E402

TEMPLATE = (KIT_ROOT / "kit" / "templates" / "pyproject.toml").read_text(encoding="utf-8")
OLD = TEMPLATE.split("[build-system]")[0] + TEMPLATE.split("packages = []\n\n", 1)[1]
OLD_FILE = OLD.replace("{{project}}", "demo")


# Building needs setuptools in the test interpreter; the tests make no network call, so they cannot
# fetch it (a CI interpreter of Python 3.12 or later ships without it). The tables themselves are
# also checked below as data, and those cases always run.
needs_setuptools = pytest.mark.skipif(
    importlib.util.find_spec("setuptools") is None,
    reason="setuptools is not installed in this interpreter (no network in tests)",
)


def builds(root: Path) -> subprocess.CompletedProcess:
    """What a package install does first: setuptools' metadata for the root, no isolation."""
    (root / "out").mkdir(exist_ok=True)
    code = "import setuptools.build_meta as b; print(b.prepare_metadata_for_build_wheel('out'))"
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-c", code], cwd=root, capture_output=True, text=True, timeout=120
    )


def flat_layout(root: Path) -> None:
    """The top-level folders of a project the kit installs: the cause of the measured failure."""
    for name in ("scripts", "tests", "docs", "config", "constitution"):
        (root / name).mkdir(parents=True, exist_ok=True)
        (root / name / "x.py").write_text("x = 1\n", encoding="utf-8")


# --- the template (answer 1) ----------------------------------------------------------------


@needs_setuptools
def test_the_old_file_fails_the_way_the_build_log_showed(tmp_path):
    (tmp_path / "pyproject.toml").write_text(OLD_FILE, encoding="utf-8")
    flat_layout(tmp_path)
    proc = builds(tmp_path)
    assert proc.returncode != 0 and "Multiple top-level packages" in proc.stderr + proc.stdout


@needs_setuptools
def test_a_new_projects_file_builds_and_installs_nothing(tmp_path):
    (tmp_path / "pyproject.toml").write_text(TEMPLATE.replace("{{project}}", "demo"), "utf-8")
    flat_layout(tmp_path)
    proc = builds(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().endswith(".dist-info")


def test_the_template_names_a_setuptools_build_that_packages_nothing():
    data = tomllib.loads(TEMPLATE.replace("{{project}}", "demo"))
    assert data["build-system"] == {
        "requires": ["setuptools>=61"],
        "build-backend": "setuptools.build_meta",
    }
    assert data["tool"]["setuptools"] == {"packages": []}
    assert OLD_FILE and "build-system" not in tomllib.loads(OLD_FILE)


def test_the_upgraded_file_parses_with_the_two_tables_and_the_projects_own_lines(
    tmp_path, kit, capsys
):
    target = init_target(tmp_path, **{"pyproject.toml": OLD_FILE})
    run(capsys, target)
    data = tomllib.loads((target / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["build-system"]["build-backend"] == "setuptools.build_meta"
    assert data["tool"]["setuptools"] == {"packages": []}
    assert data["project"]["name"] == "demo" and data["tool"]["ruff"]["line-length"] == 100


def test_the_template_keeps_project_pytest_and_ruff_and_carries_the_upgrades_tables():
    assert upgrade.INSTALLS_AS_NOTHING in TEMPLATE
    for table in ("[project]", "[tool.pytest.ini_options]", "[tool.ruff]", "[tool.ruff.lint]"):
        assert table in TEMPLATE
    assert 'requires = ["setuptools>=61"]' in TEMPLATE
    assert 'build-backend = "setuptools.build_meta"' in TEMPLATE


# --- the upgrade (answer 2) -----------------------------------------------------------------


@needs_setuptools
def test_upgrade_adds_the_two_tables_to_a_file_without_them_and_keeps_every_other_byte(
    tmp_path, kit, capsys
):
    protected = {"config/protected-paths.txt": PROTECTED + "pyproject.toml\n"}
    target = init_target(tmp_path, **{"pyproject.toml": OLD_FILE}, **protected)
    code, out = run(capsys, target)
    assert code == 0
    assert any(ln.startswith("replace pyproject.toml") for ln in out)
    assert any("Protected classes:" in ln and "pyproject.toml" in ln for ln in out)
    text = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert text == OLD_FILE + "\n" + upgrade.INSTALLS_AS_NOTHING
    flat_layout(target)
    assert builds(target).returncode == 0


def test_a_second_upgrade_changes_nothing(tmp_path, kit, capsys):
    target = init_target(tmp_path, **{"pyproject.toml": OLD_FILE})
    run(capsys, target)
    after_first = (target / "pyproject.toml").read_bytes()
    code, out = run(capsys, target)
    assert code == 0 and (target / "pyproject.toml").read_bytes() == after_first
    assert not any("pyproject.toml" in ln for ln in out)


def test_a_file_with_the_tables_is_unchanged_byte_for_byte(tmp_path, kit, capsys):
    mine = TEMPLATE.replace("{{project}}", "demo") + "\n# mine\n"
    target = init_target(tmp_path, **{"pyproject.toml": mine})
    before = (target / "pyproject.toml").read_bytes()
    code, out = run(capsys, target)
    assert code == 0 and (target / "pyproject.toml").read_bytes() == before
    assert not any("pyproject.toml" in ln for ln in out)


def test_a_custom_tool_setuptools_is_left_alone_and_the_note_says_so(tmp_path, kit, capsys):
    mine = OLD_FILE + '\n[tool.setuptools.packages.find]\ninclude = ["app*"]\n'
    target = init_target(tmp_path, **{"pyproject.toml": mine})
    before = (target / "pyproject.toml").read_bytes()
    code, out = run(capsys, target)
    assert code == 0 and (target / "pyproject.toml").read_bytes() == before
    assert any(ln.startswith("pyproject-unchanged pyproject.toml") for ln in out)
    assert not any(ln.startswith("replace pyproject.toml") for ln in out)


def test_a_file_with_its_own_build_system_is_left_alone(tmp_path, kit, capsys):
    mine = (
        OLD_FILE + '\n[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n'
    )
    target = init_target(tmp_path, **{"pyproject.toml": mine})
    before = (target / "pyproject.toml").read_bytes()
    assert run(capsys, target)[0] == 0 and (target / "pyproject.toml").read_bytes() == before


def test_a_file_without_a_project_table_or_not_toml_is_left_alone(tmp_path, kit, capsys):
    for text in ("[tool.ruff]\nline-length = 100\n", "this is = = not toml\n"):
        target = init_target(tmp_path / text[:4].strip("[ "), **{"pyproject.toml": text})
        assert run(capsys, target)[0] == 0
        assert (target / "pyproject.toml").read_text(encoding="utf-8") == text


def test_a_file_without_a_final_newline_gets_one_blank_line_between(tmp_path, kit, capsys):
    mine = OLD_FILE.rstrip("\n")
    target = init_target(tmp_path, **{"pyproject.toml": mine})
    run(capsys, target)
    text = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert text == mine + "\n\n" + upgrade.INSTALLS_AS_NOTHING


def test_dry_run_prints_the_change_and_writes_nothing(tmp_path, kit, capsys):
    target = init_target(tmp_path, **{"pyproject.toml": OLD_FILE})
    code, out = run(capsys, target, "--dry-run")
    assert code == 0 and any(ln.startswith("replace pyproject.toml") for ln in out)
    assert (target / "pyproject.toml").read_text(encoding="utf-8") == OLD_FILE


def test_an_adopted_projects_file_is_the_projects_own_and_is_left_alone(tmp_path, kit, capsys):
    from test_upgrade import adopt_target

    target = adopt_target(tmp_path, **{"pyproject.toml": OLD_FILE})
    before = (target / "pyproject.toml").read_bytes()
    assert run(capsys, target)[0] == 0 and (target / "pyproject.toml").read_bytes() == before


def test_a_symlinked_pyproject_is_never_followed(tmp_path, kit, capsys):
    target = init_target(tmp_path)
    real = tmp_path / "elsewhere.toml"
    real.write_text(textwrap.dedent(OLD_FILE), encoding="utf-8")
    (target / "pyproject.toml").symlink_to(real)
    assert run(capsys, target)[0] == 0 and real.read_text(encoding="utf-8") == OLD_FILE


def test_a_legacy_install_whose_pyproject_holds_the_stamp_is_never_written(tmp_path, kit, capsys):
    from test_upgrade import legacy_target

    target = legacy_target(tmp_path)
    before = (target / "pyproject.toml").read_bytes()
    assert run(capsys, target)[0] == 0 and (target / "pyproject.toml").read_bytes() == before
