"""Tests of the optional `[parts]` table of `agk.toml` (SPEC-0076 rule 9; REQ-083 AC6; brief
#2068, ADR-0858).

`config.parts_settings` reads `record`, `max_age_months` and `advisories` in the form of
`packs_settings`: each set, absent, unknown or of the wrong type (a `bool` is never a number or a
word). A refusal is `the [parts] table is refused (setting: parts.<key>)` and never the value. A
`[parts]` key in another table is reported by `misplaced_settings` and never read. `doctor.py`
prints the line; `uninstall.py` removes the table through `KIT_SETTINGS`. Fixtures in `tmp_path`
only: invented data (`example.com`), no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import doctor  # noqa: E402
import uninstall  # noqa: E402

import config  # noqa: E402

DEFAULTS = {"record": "optional", "max_age_months": 12, "advisories": "critical-high"}


def settings(root: Path, text: str) -> dict:
    (root / "agk.toml").write_text(text, encoding="utf-8")
    return config.parts_settings(root)


def refused(root: Path, text: str) -> str:
    (root / "agk.toml").write_text(text, encoding="utf-8")
    with pytest.raises(config.PartsSettingError) as caught:
        config.parts_settings(root)
    return str(caught.value)


def test_ac6_no_agk_toml_and_no_table_hold_the_defaults(tmp_path):
    """REQ-083 AC6: SPEC-0076 rule 9 (with no table every result is today's)."""
    assert config.parts_settings(tmp_path) == DEFAULTS
    assert settings(tmp_path, '[flow]\nassign = "next"\n') == DEFAULTS
    assert settings(tmp_path, "[parts]\n") == DEFAULTS


@pytest.mark.parametrize(
    ("line", "key", "value"),
    [
        ('record = "required"', "record", "required"),
        ('record = "optional"', "record", "optional"),
        ("max_age_months = 1", "max_age_months", 1),
        ("max_age_months = 60", "max_age_months", 60),
        ('advisories = "critical"', "advisories", "critical"),
        ('advisories = "any"', "advisories", "any"),
        ('advisories = "critical-high"', "advisories", "critical-high"),
    ],
)
def test_ac6_each_key_set_is_read(tmp_path, line, key, value):
    """REQ-083 AC6: SPEC-0076 rule 9 (`record`, `max_age_months`, `advisories`)."""
    assert settings(tmp_path, f"[parts]\n{line}\n") == {**DEFAULTS, key: value}


@pytest.mark.parametrize(
    ("line", "key"),
    [
        ('record = "zz-sometimes"', "record"),
        ("record = 1", "record"),
        ("record = true", "record"),
        ("max_age_months = 0", "max_age_months"),
        ("max_age_months = 61", "max_age_months"),
        ("max_age_months = 1.5", "max_age_months"),
        ("max_age_months = true", "max_age_months"),
        ('max_age_months = "12"', "max_age_months"),
        ('advisories = "zz-high"', "advisories"),
        ('advisories = ["critical"]', "advisories"),
        ("advisories = false", "advisories"),
        ('zz_unknown = "zz-x"', "zz_unknown"),
    ],
)
def test_ac6_a_value_out_of_form_is_refused_naming_the_setting(tmp_path, line, key):
    """REQ-083 AC6: SPEC-0076 rule 9 (a refusal names `parts.<key>`, never the value)."""
    message = refused(tmp_path, f"[parts]\n{line}\n")
    assert message == f"the [parts] table is refused (setting: parts.{key})"
    assert "zz-sometimes" not in message and "zz-high" not in message and "zz-x" not in message


def test_ac6_a_parts_that_is_not_a_table_or_an_unreadable_file_is_refused(tmp_path):
    """REQ-083 AC6: SPEC-0076 rule 9 (the table is refused, naming the setting)."""
    expected = "the [parts] table is refused (setting: parts)"
    assert refused(tmp_path, 'parts = "zz-all"\n') == expected
    assert refused(tmp_path, "[parts\nrecord = 1\n") == expected


def test_ac6_a_parts_key_in_another_table_is_reported_and_never_read(tmp_path):
    """REQ-083 AC6: SPEC-0076 rule 9 (a misplaced key, by `misplaced_settings`)."""
    (tmp_path / "agk.toml").write_text('[flow]\nrecord = "required"\n', encoding="utf-8")
    found = config.misplaced_settings(config.config_source(tmp_path))
    assert found == [("record", "flow", ("parts",))]
    assert config.parts_settings(tmp_path) == DEFAULTS


def test_ac6_the_pyproject_table_is_read_the_same(tmp_path):
    """REQ-083 AC6: SPEC-0076 rule 9 (`[tool.agk.parts]` with no `agk.toml`, `config_source`)."""
    (tmp_path / "pyproject.toml").write_text(
        '[tool.agk.parts]\nrecord = "required"\n', encoding="utf-8"
    )
    assert config.parts_settings(tmp_path) == {**DEFAULTS, "record": "required"}


@pytest.mark.parametrize(
    "extra",
    [
        'review_mode = "solo"\n',
        'review_mode = "team"\n',
        'execution = "hosted"\n',
        'execution = "local"\n',
        '[delivery]\nwork_type = "web-app"\n',
        '[domain]\npacks = []\n',
        '[kit]\nlayout = "plugin"\n',
        '[personal]\nforge = "files"\n',
    ],
)
def test_ac6_modes_and_layouts_read_the_table_the_same(tmp_path, extra):
    """REQ-083 AC6: SPEC-0076 rule 9 (file-only: the same result in every mode and layout)."""
    found = settings(tmp_path, f'{extra}\n[parts]\nrecord = "required"\n')
    assert found == {**DEFAULTS, "record": "required"}


def test_ac6_the_class_stays_closed_parts_is_a_kit_table():
    """REQ-083 AC6: SPEC-0076 rules 9 and 17 (`TABLE_KEYS`, `KIT_SETTINGS`, doctor, uninstall)."""
    assert config.TABLE_KEYS["parts"] == frozenset(DEFAULTS)
    assert "parts" in config.KIT_SETTINGS
    assert uninstall.kit_settings() is config.KIT_SETTINGS
    assert uninstall.KEYED_TABLES["parts"] == config.TABLE_KEYS["parts"]
    assert "parts-settings" in doctor.CHECKS


def test_ac6_uninstall_removes_the_table_as_a_kit_setting():
    """REQ-083 AC6: SPEC-0076 rule 9 (removed through `KIT_SETTINGS`; an unknown key is named)."""
    assert uninstall.foreign_settings({"parts": dict(DEFAULTS)}) == []
    assert uninstall.foreign_settings({"parts": {"zz_unknown": 1}}) == ["parts.zz_unknown"]


def test_ac6_doctor_prints_the_parts_settings(tmp_path):
    """REQ-083 AC6: SPEC-0076 rule 9 (`doctor.py` prints the table)."""
    found = doctor.parts_settings_result(tmp_path)
    assert found.status == "ok"
    assert found.message == "(record optional, max age 12 months, advisories critical-high)"
    settings(tmp_path, '[parts]\nrecord = "required"\nmax_age_months = 6\nadvisories = "any"\n')
    found = doctor.parts_settings_result(tmp_path)
    assert found.message == "(record required, max age 6 months, advisories any)"
    severity, ok_text, fail_text, fix = doctor.CHECKS["parts-settings"]
    assert severity == "warn" and ok_text == "ok " and "agk.toml" in fail_text
    assert "[parts]" in fix and "ADR" in fix


def test_ac6_doctor_names_the_refused_key_never_the_value(tmp_path):
    """REQ-083 AC6: SPEC-0076 rule 9 (a refusal names the setting and no value)."""
    (tmp_path / "agk.toml").write_text('[parts]\nrecord = "zz-sometimes"\n', encoding="utf-8")
    found = doctor.parts_settings_result(tmp_path)
    assert found.status == "fail"
    assert found.message == "the [parts] table is refused (setting: parts.record)"


def test_ac6_the_kit_itself_has_no_parts_table():
    """REQ-083 AC6: SPEC-0076 rule 9 (the kit's own repository: the defaults)."""
    assert "parts" not in config.config_source(KIT_ROOT)
    assert config.parts_settings(KIT_ROOT) == DEFAULTS
