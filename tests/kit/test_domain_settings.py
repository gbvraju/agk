"""Tests of the optional `[domain]` table of `agk.toml` (SPEC-0074 rule 12; REQ-081 AC7; brief
#1935).

`config.domain_settings` reads `packs` and `stale_months` in the form of `steward_settings`: each
set, absent, out of form, or a `bool` given for a number. A refusal is `the [domain] table is
refused (setting: domain.<key>)` and never the value. A `[domain]` key in another table is
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

DEFAULTS = {"packs": [], "stale_months": 12}
PACK = """format = 1
domain = "zz-shop"
title = "An invented shop"
as_of = "2026-11-25"

[[terms]]
term = "basket"
meaning = "The items a buyer holds"
synonyms = []
"""


def settings(root: Path, text: str) -> dict:
    (root / "agk.toml").write_text(text, encoding="utf-8")
    return config.domain_settings(root)


def refused(root: Path, text: str) -> str:
    (root / "agk.toml").write_text(text, encoding="utf-8")
    with pytest.raises(config.DomainSettingError) as caught:
        config.domain_settings(root)
    return str(caught.value)


def pack(root: Path, text: str = PACK, name: str = "zz-shop") -> None:
    folder = root / "config" / "domains"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.toml").write_text(text, encoding="utf-8")


def test_ac7_no_agk_toml_and_no_table_hold_the_defaults(tmp_path):
    """REQ-081 AC7: SPEC-0074 rule 12 (with no table no pack applies)."""
    assert config.domain_settings(tmp_path) == DEFAULTS
    assert settings(tmp_path, '[flow]\nassign = "next"\n') == DEFAULTS
    assert settings(tmp_path, "[domain]\npacks = []\n") == DEFAULTS


def test_ac7_a_named_pack_that_passes_is_read(tmp_path):
    """REQ-081 AC7: SPEC-0074 rule 12 (`packs`, each a pack under `config/domains/`)."""
    pack(tmp_path)
    found = settings(tmp_path, '[domain]\npacks = ["zz-shop"]\nstale_months = 60\n')
    assert found == {"packs": ["zz-shop"], "stale_months": 60}
    assert settings(tmp_path, "[domain]\nstale_months = 1\n")["stale_months"] == 1


@pytest.mark.parametrize(
    ("line", "key"),
    [
        ('packs = ["zz-none"]', "packs"),
        ('packs = "zz-shop"', "packs"),
        ("packs = [1]", "packs"),
        ('packs = ["zz-bad"]', "packs"),
        ('packs = ["../zz-shop"]', "packs"),
        ("stale_months = 0", "stale_months"),
        ("stale_months = 61", "stale_months"),
        ("stale_months = true", "stale_months"),
        ("stale_months = 12.0", "stale_months"),
        ('stale_months = "12"', "stale_months"),
        ('zz_unknown = "zz-x"', "zz_unknown"),
    ],
)
def test_ac7_a_value_out_of_form_is_refused_naming_the_setting(tmp_path, line, key):
    """REQ-081 AC7: SPEC-0074 rule 12 (a refusal names `domain.<key>`, never the value)."""
    pack(tmp_path)
    pack(tmp_path, PACK.replace("format = 1", "format = 2"), "zz-bad")
    message = refused(tmp_path, f"[domain]\n{line}\n")
    assert message == f"the [domain] table is refused (setting: domain.{key})"
    assert "zz-none" not in message and "zz-x" not in message


def test_ac7_a_domain_that_is_not_a_table_is_refused(tmp_path):
    """REQ-081 AC7: SPEC-0074 rule 12 (the table is refused, naming the setting)."""
    assert refused(tmp_path, 'domain = "zz-shop"\n') == (
        "the [domain] table is refused (setting: domain)"
    )


def test_ac7_the_two_keys_are_a_table_of_table_keys():
    """REQ-081 AC7: SPEC-0074 rule 12 (listed in `config.TABLE_KEYS`)."""
    assert config.TABLE_KEYS["domain"] == frozenset(DEFAULTS)
    assert "domain" in config.KIT_SETTINGS


def test_ac7_a_domain_key_in_another_table_is_reported_and_never_read(tmp_path):
    """REQ-081 AC7: SPEC-0074 rule 12 (a misplaced key, by `misplaced_settings`)."""
    (tmp_path / "agk.toml").write_text("[flow]\nstale_months = 3\n", encoding="utf-8")
    found = config.misplaced_settings(config.config_source(tmp_path))
    assert found == [("stale_months", "flow", ("domain",))]
    assert config.domain_settings(tmp_path) == DEFAULTS
    assert config.misplaced_settings({"packs": []}) == [("packs", config.TOP_LEVEL, ("domain",))]


def test_ac7_uninstall_removes_the_domain_table_as_a_kit_setting():
    """REQ-081 AC7: SPEC-0074 rule 12 (`uninstall.py` removes it through `KIT_SETTINGS`)."""
    assert "domain" in uninstall.kit_settings()
    assert uninstall.foreign_settings({"domain": dict(DEFAULTS)}) == []
    assert uninstall.foreign_settings({"domain": {"zz_unknown": 1}}) == ["domain.zz_unknown"]


def test_ac7_doctor_prints_the_domain_settings(tmp_path):
    """REQ-081 AC7: SPEC-0074 rule 12 (`doctor.py` prints the table)."""
    found = doctor.domain_settings_result(tmp_path)
    assert found.status == "ok" and found.message == "packs none, stale after 12 months"
    pack(tmp_path)
    settings(tmp_path, '[domain]\npacks = ["zz-shop"]\nstale_months = 6\n')
    found = doctor.domain_settings_result(tmp_path)
    assert found.message == "packs zz-shop, stale after 6 months"
    severity, ok_text, fail_text, fix = doctor.CHECKS["domain-settings"]
    assert severity == "warn" and ok_text == "domain: " and "agk.toml" in fail_text and fix


def test_ac7_doctor_names_the_refused_key_never_the_value(tmp_path):
    """REQ-081 AC7: SPEC-0074 rule 12 (a refusal names the setting and no value)."""
    settings_text = '[domain]\npacks = ["zz-none"]\n'
    (tmp_path / "agk.toml").write_text(settings_text, encoding="utf-8")
    found = doctor.domain_settings_result(tmp_path)
    assert found.status == "fail"
    assert found.message == "the [domain] table is refused (setting: domain.packs)"


def test_ac7_the_kit_itself_has_no_domain_table():
    """REQ-081 AC7: SPEC-0074 rule 12 (the kit's own repository has no domain)."""
    assert "domain" not in config.config_source(KIT_ROOT)
