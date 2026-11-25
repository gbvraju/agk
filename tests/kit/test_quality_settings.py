"""Tests of the optional `[quality]` table of `agk.toml` (SPEC-0073 rule 11; REQ-080 AC7; brief
#1933).

`config.quality_settings` reads five keys in the form of `steward_settings`: each set, absent, out
of form, or a `bool` given for a number. A refusal names `quality.<key>` and never the value. A
declared `pilot` makes `grill` light and `designs` 1. A `[quality]` key in another table is
reported by `misplaced_settings` and never read. `uninstall.py` removes the table through
`KIT_SETTINGS`, and `doctor.py` prints the line. Fixtures in `tmp_path` only: invented data, no
network.
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

DEFAULTS = {
    "grill": "standard",
    "grill_hold": True,
    "glossary_terms": 40,
    "designs": 2,
    "survey_days": 7,
}


def settings(root: Path, text: str) -> dict:
    (root / "agk.toml").write_text(text, encoding="utf-8")
    return config.quality_settings(root)


def refused(root: Path, text: str) -> str:
    (root / "agk.toml").write_text(text, encoding="utf-8")
    with pytest.raises(config.QualitySettingError) as caught:
        config.quality_settings(root)
    return str(caught.value)


def test_ac7_no_agk_toml_and_no_table_hold_every_default(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (with no table every default holds)."""
    assert config.quality_settings(tmp_path) == DEFAULTS
    assert settings(tmp_path, '[flow]\nassign = "next"\n') == DEFAULTS


@pytest.mark.parametrize(
    ("line", "key", "want"),
    [
        ('grill = "light"', "grill", "light"),
        ('grill = "standard"', "grill", "standard"),
        ('grill = "deep"', "grill", "deep"),
        ("grill_hold = false", "grill_hold", False),
        ("grill_hold = true", "grill_hold", True),
        ("glossary_terms = 10", "glossary_terms", 10),
        ("glossary_terms = 200", "glossary_terms", 200),
        ("designs = 1", "designs", 1),
        ("designs = 2", "designs", 2),
        ("survey_days = 0", "survey_days", 0),
        ("survey_days = 30", "survey_days", 30),
    ],
)
def test_ac7_each_setting_in_form_is_read(tmp_path, line, key, want):
    """REQ-080 AC7: SPEC-0073 rule 11 (each row of the settings table, set)."""
    found = settings(tmp_path, f"[quality]\n{line}\n")
    assert found == {**DEFAULTS, key: want}


@pytest.mark.parametrize(
    ("line", "key"),
    [
        ('grill = "zz-extreme"', "grill"),
        ("grill = 3", "grill"),
        ("grill = true", "grill"),
        ('grill_hold = "zz-yes"', "grill_hold"),
        ("grill_hold = 1", "grill_hold"),
        ("glossary_terms = 9", "glossary_terms"),
        ("glossary_terms = 201", "glossary_terms"),
        ("glossary_terms = true", "glossary_terms"),
        ('glossary_terms = "40"', "glossary_terms"),
        ("glossary_terms = 40.5", "glossary_terms"),
        ("designs = 3", "designs"),
        ("designs = 0", "designs"),
        ("designs = true", "designs"),
        ("survey_days = 31", "survey_days"),
        ("survey_days = -1", "survey_days"),
        ("survey_days = false", "survey_days"),
        ('zz_unknown = "zz-value"', "zz_unknown"),
    ],
)
def test_ac7_a_setting_out_of_form_is_refused_naming_the_key_never_the_value(tmp_path, line, key):
    """REQ-080 AC7: SPEC-0073 rule 11 (out of form, an unknown key, a `bool` for a number)."""
    message = refused(tmp_path, f"[quality]\n{line}\n")
    assert message == f"the [quality] table is refused (setting: quality.{key})"
    assert "zz-" not in message and line.split(" = ")[1] not in message


def test_ac7_a_quality_that_is_not_a_table_is_refused(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (the table is refused, naming the setting)."""
    assert refused(tmp_path, 'quality = "zz-light"\n') == (
        "the [quality] table is refused (setting: quality)"
    )


def test_ac7_a_declared_pilot_defaults_to_the_light_grill_and_one_design(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (the pilot defaults)."""
    pilot = '[delivery]\nwork_type = "pilot"\n'
    assert settings(tmp_path, pilot) == {**DEFAULTS, "grill": "light", "designs": 1}
    found = settings(tmp_path, pilot + '[quality]\ngrill = "deep"\ndesigns = 2\n')
    assert found["grill"] == "deep" and found["designs"] == 2
    other = settings(tmp_path, '[delivery]\nwork_type = "web-app"\n')
    assert other == DEFAULTS


def test_ac7_the_five_keys_are_a_table_of_table_keys():
    """REQ-080 AC7: SPEC-0073 rule 11 (listed in `config.TABLE_KEYS`)."""
    assert config.TABLE_KEYS["quality"] == frozenset(DEFAULTS)
    assert "quality" in config.KIT_SETTINGS


def test_ac7_a_quality_key_in_another_table_is_reported_and_never_read(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (a misplaced key, by `misplaced_settings`)."""
    text = '[flow]\ngrill = "deep"\n'
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    found = config.misplaced_settings(config.config_source(tmp_path))
    assert found == [("grill", "flow", ("quality",))]
    assert config.quality_settings(tmp_path) == DEFAULTS
    top = config.misplaced_settings({"designs": 1})
    assert top == [("designs", config.TOP_LEVEL, ("quality",))]


def test_ac7_uninstall_removes_the_quality_table_as_a_kit_setting():
    """REQ-080 AC7: SPEC-0073 rule 11 (`uninstall.py` removes it through `KIT_SETTINGS`)."""
    assert "quality" in uninstall.kit_settings()
    assert uninstall.foreign_settings({"quality": dict(DEFAULTS)}) == []
    assert uninstall.foreign_settings({"quality": {"zz_unknown": 1}}) == ["quality.zz_unknown"]


def test_ac7_doctor_prints_the_quality_settings_in_the_kit_s_own_words(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (`doctor.py` prints the table)."""
    found = doctor.quality_settings_result(tmp_path)
    assert found.status == "ok"
    assert found.message == "grill standard, hold on, glossary 40, designs 2, survey 7 days"
    settings(tmp_path, "[quality]\ngrill_hold = false\nsurvey_days = 0\n")
    found = doctor.quality_settings_result(tmp_path)
    assert found.message == "grill standard, hold off, glossary 40, designs 2, survey off"
    severity, ok_text, fail_text, fix = doctor.CHECKS["quality-settings"]
    assert severity == "warn" and "agk.toml" in fail_text and fix


def test_ac7_doctor_names_the_refused_key_never_the_value(tmp_path):
    """REQ-080 AC7: SPEC-0073 rule 11 (a refusal names the setting and no value)."""
    settings_text = '[quality]\ngrill = "zz-extreme"\n'
    (tmp_path / "agk.toml").write_text(settings_text, encoding="utf-8")
    found = doctor.quality_settings_result(tmp_path)
    assert found.status == "fail"
    assert found.message == "the [quality] table is refused (setting: quality.grill)"
