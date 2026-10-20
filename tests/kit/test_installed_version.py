"""Tests of `common.installed_version`, the one reader of the installed kit version (SPEC-0014).

The version is the `version` of `agk.toml` or, when `agk.toml` is absent, the `version` of the
legacy `[tool.agk]` table of `pyproject.toml` (rule 2). Anything else gives None: nothing falls back
to a constant, to the kit's manifest or to another file (rule 3). No network, no model, no `gh`.
"""

from __future__ import annotations

from pathlib import Path

import common
import pytest

LEGACY = '[tool.agk]\nversion = "0.2.0"\n'


def put(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_ac1_the_version_is_the_version_of_agk_toml(tmp_path):
    """REQ-021 AC1: rule 2."""
    put(tmp_path, {"agk.toml": 'mode = "init"\nversion = "1.2.3"\n'})
    assert common.installed_version(tmp_path) == "1.2.3"


def test_ac1_agk_toml_wins_over_the_legacy_table(tmp_path):
    """REQ-021 AC1: rule 2 (the legacy table is read only when agk.toml is absent)."""
    put(tmp_path, {"agk.toml": 'version = "1.2.3"\n', "pyproject.toml": LEGACY})
    assert common.installed_version(tmp_path) == "1.2.3"


@pytest.mark.parametrize(
    "files",
    [
        pytest.param({}, id="no-file"),
        pytest.param({"agk.toml": 'mode = "init"\n'}, id="no-version-key"),
        pytest.param({"agk.toml": "version = 3\n"}, id="version-not-a-string"),
        pytest.param({"agk.toml": 'version = ["1"]\n'}, id="version-a-list"),
        pytest.param({"agk.toml": "version = [\n"}, id="unreadable-toml"),
        pytest.param({"agk.toml": 'mode = "init"\n', "pyproject.toml": LEGACY}, id="no-fallback"),
        pytest.param({"pyproject.toml": "[tool.other]\nx = 1\n"}, id="no-agk-table"),
        pytest.param({"pyproject.toml": "[tool.agk]\nversion = 2\n"}, id="legacy-not-a-string"),
        pytest.param({"pyproject.toml": "[tool.agk\n"}, id="legacy-unreadable"),
        pytest.param(
            {"kit/manifest.json": '{"kit_version": "9.9.9"}\n', "VERSION": "9.9.9\n"},
            id="never-the-manifest-or-another-file",
        ),
    ],
)
def test_ac2_an_unreadable_version_is_none_and_never_guessed(tmp_path, files):
    """REQ-021 AC2: rule 3."""
    put(tmp_path, files)
    assert common.installed_version(tmp_path) is None


def test_ac2_agk_toml_that_is_not_a_file_gives_none(tmp_path):
    """REQ-021 AC2: rule 3."""
    (tmp_path / "agk.toml").mkdir()
    assert common.installed_version(tmp_path) is None


def test_ac3_without_agk_toml_the_legacy_table_gives_the_version(tmp_path):
    """REQ-021 AC3: rule 2 (the stamp of kits 0.1.0 and 0.2.0)."""
    put(tmp_path, {"pyproject.toml": LEGACY})
    assert common.installed_version(tmp_path) == "0.2.0"
