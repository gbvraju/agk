"""Tests of the optional `[packs]` table of `agk.toml` (SPEC-0077 rule 12; REQ-084 AC5; brief
#2031, ADR-0838).

`config.packs_settings` reads `use`, `trust`, `stale_months` and `mcp` in the form of
`steward_settings`: each set, absent, unknown or of the wrong type (a `bool` is never a number). A
refusal is `the [packs] table is refused (setting: packs.<key>)` and never the value. A `[packs]`
key in another table is reported by `misplaced_settings` and never read. `doctor.py` prints the
line; `uninstall.py` removes the table through `KIT_SETTINGS` and names `config/packs/` as kept.
Fixtures in `tmp_path` only: invented data (`example.com`), no network.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import doctor  # noqa: E402
import uninstall  # noqa: E402

import config  # noqa: E402

DEFAULTS = {"use": [], "trust": "curated", "stale_months": 12, "mcp": []}
MANIFEST = """format = 1
id = "zz-shop"
version = "1.2.0"
publisher = "Example Org"
tier = "curated"
licence = "MIT"
source = "https://example.com/packs/zz-shop"
kit = ">=0.60.0,<1.0.0"
as_of = "2026-11-20"
reviewed = "2026-11-21 by maintainers"
kinds = ["skills"]
files = {}

[permissions]
mcp = ["zz-docs"]
"""


def pack(root: Path, name: str = "zz-shop") -> str:
    """A stub pack under `config/packs/<name>/`; returns its manifest's SHA-256."""
    base = root / "config" / "packs" / name
    base.mkdir(parents=True, exist_ok=True)
    text = MANIFEST.replace('id = "zz-shop"', f'id = "{name}"')
    (base / "agk-pack.toml").write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def entry(name: str, digest: str, version: str = "1.2.0") -> str:
    return f'{{ id = "{name}", version = "{version}", sha256 = "{digest}" }}'


def settings(root: Path, text: str) -> dict:
    (root / "agk.toml").write_text(text, encoding="utf-8")
    return config.packs_settings(root)


def refused(root: Path, text: str) -> str:
    (root / "agk.toml").write_text(text, encoding="utf-8")
    with pytest.raises(config.PacksSettingError) as caught:
        config.packs_settings(root)
    return str(caught.value)


def test_ac5_no_agk_toml_no_table_and_an_empty_use_hold_the_defaults(tmp_path):
    """REQ-084 AC5: SPEC-0077 rule 12 (with no table only `agk-core` is read)."""
    assert config.packs_settings(tmp_path) == DEFAULTS
    assert settings(tmp_path, '[flow]\nassign = "next"\n') == DEFAULTS
    assert settings(tmp_path, "[packs]\nuse = []\n") == DEFAULTS


def test_ac5_every_key_set_is_read(tmp_path):
    """REQ-084 AC5: SPEC-0077 rule 12 (`use`, `trust`, `stale_months`, `mcp`)."""
    digest = pack(tmp_path)
    text = f'[packs]\nuse = [{entry("zz-shop", digest)}]\ntrust = "community"\n'
    text += 'stale_months = 60\nmcp = ["zz-docs"]\n'
    found = settings(tmp_path, text)
    assert found == {
        "use": [{"id": "zz-shop", "version": "1.2.0", "sha256": digest}],
        "trust": "community",
        "stale_months": 60,
        "mcp": ["zz-docs"],
    }
    for tier in ("official", "curated"):
        assert settings(tmp_path, f'[packs]\ntrust = "{tier}"\n')["trust"] == tier
    assert settings(tmp_path, "[packs]\nstale_months = 1\n")["stale_months"] == 1


@pytest.mark.parametrize(
    ("line", "key"),
    [
        ('use = "zz-shop"', "use"),
        ('use = [{ id = "zz-shop" }]', "use"),
        ("use = [1]", "use"),
        ('use = [{ id = "zz-none", version = "1.2.0", sha256 = "DIGEST" }]', "use"),
        ('use = [{ id = "zz-shop", version = "1.2.0", sha256 = "' + "0" * 64 + '" }]', "use"),
        ('use = [{ id = "zz-shop", version = "1.3.0", sha256 = "DIGEST" }]', "use"),
        ('use = [{ id = "zz-shop", version = ">=1", sha256 = "DIGEST" }]', "use"),
        ('use = [{ id = "agk-core", version = "1.2.0", sha256 = "DIGEST" }]', "use"),
        ('use = [{ id = "zz-shop", version = "1.2.0", sha256 = "DIGEST", zz = 1 }]', "use"),
        (
            'use = [{ id = "zz-shop", version = "1.2.0", sha256 = "DIGEST" }, '
            '{ id = "zz-shop", version = "1.2.0", sha256 = "DIGEST" }]',
            "use",
        ),
        ('trust = "zz-gold"', "trust"),
        ("trust = 1", "trust"),
        ("stale_months = 0", "stale_months"),
        ("stale_months = 61", "stale_months"),
        ("stale_months = true", "stale_months"),
        ('stale_months = "12"', "stale_months"),
        ('mcp = "zz-docs"', "mcp"),
        ("mcp = [1]", "mcp"),
        ('mcp = ["zz-docs"]', "mcp"),  # no pack in use declares it
        ('zz_unknown = "zz-x"', "zz_unknown"),
    ],
)
def test_ac5_a_value_out_of_form_is_refused_naming_the_setting(tmp_path, line, key):
    """REQ-084 AC5: SPEC-0077 rule 12 (a refusal names `packs.<key>`, never the value)."""
    digest = pack(tmp_path)
    message = refused(tmp_path, f"[packs]\n{line.replace('DIGEST', digest)}\n")
    assert message == f"the [packs] table is refused (setting: packs.{key})"
    assert digest not in message and "zz-gold" not in message and "zz-x" not in message


def test_ac5_a_packs_that_is_not_a_table_is_refused(tmp_path):
    """REQ-084 AC5: SPEC-0077 rule 12 (the table is refused, naming the setting)."""
    assert refused(tmp_path, 'packs = "zz-shop"\n') == (
        "the [packs] table is refused (setting: packs)"
    )


def test_ac5_a_packs_key_in_another_table_is_reported_and_never_read(tmp_path):
    """REQ-084 AC5: SPEC-0077 rule 12 (a misplaced key, by `misplaced_settings`)."""
    (tmp_path / "agk.toml").write_text('[flow]\ntrust = "community"\n', encoding="utf-8")
    found = config.misplaced_settings(config.config_source(tmp_path))
    assert found == [("trust", "flow", ("packs",))]
    assert config.packs_settings(tmp_path) == DEFAULTS


def test_ac5_the_domain_table_stays_independent(tmp_path):
    """REQ-084 AC5: SPEC-0077 rule 12 (`[domain] packs` unchanged; amendment 262 is build (j))."""
    text = "[domain]\npacks = []\nstale_months = 3\n"
    assert settings(tmp_path, text) == DEFAULTS
    assert config.domain_settings(tmp_path) == {"packs": [], "stale_months": 3}
    assert config.misplaced_settings(config.config_source(tmp_path)) == []


@pytest.mark.parametrize(
    "extra",
    [
        'review_mode = "solo"\n',
        'review_mode = "team"\n',
        'execution = "hosted"\n',
        'execution = "local"\n',
        '[kit]\nlayout = "plugin"\n',
        '[personal]\nforge = "files"\n',
    ],
)
def test_ac5_modes_and_layouts_read_the_table_the_same(tmp_path, extra):
    """REQ-084 AC5: SPEC-0077 rule 12 (file-only: the same result in every mode)."""
    digest = pack(tmp_path)
    found = settings(tmp_path, f"{extra}\n[packs]\nuse = [{entry('zz-shop', digest)}]\n")
    assert [e["id"] for e in found["use"]] == ["zz-shop"]


def test_ac5_the_class_stays_closed_packs_is_a_kit_table():
    """REQ-084 AC5: SPEC-0077 rule 12 (`TABLE_KEYS`, `KIT_SETTINGS`, doctor and uninstall)."""
    assert config.TABLE_KEYS["packs"] == frozenset(DEFAULTS)
    assert "packs" in config.KIT_SETTINGS
    assert uninstall.kit_settings() is config.KIT_SETTINGS
    assert uninstall.KEYED_TABLES["packs"] == config.TABLE_KEYS["packs"]
    assert "packs-settings" in doctor.CHECKS


def test_ac5_uninstall_removes_the_table_and_keeps_the_packs_folder(tmp_path):
    """REQ-084 AC5: SPEC-0077 rule 12 (removed as a kit setting; `config/packs/` named, kept)."""
    assert uninstall.foreign_settings({"packs": dict(DEFAULTS)}) == []
    assert uninstall.foreign_settings({"packs": {"zz_unknown": 1}}) == ["packs.zz_unknown"]
    pack(tmp_path)
    plan = uninstall.Plan()
    uninstall.packs_item(tmp_path, plan)
    kept = [i for i in plan.items if i.rel == uninstall.PACKS]
    assert uninstall.PACKS == "config/packs/" and [i.action for i in kept] == ["kept"]
    empty = uninstall.Plan()
    uninstall.packs_item(tmp_path / "zz-none", empty)
    assert empty.items == []
    assert "zz-shop" not in uninstall.PACKS_DETAIL


def test_ac5_doctor_prints_the_packs_settings(tmp_path):
    """REQ-084 AC5: SPEC-0077 rule 12 (`doctor.py` prints the table)."""
    found = doctor.packs_settings_result(tmp_path)
    assert found.status == "ok" and found.message == "(0 packs, trust curated, servers 0)"
    digest = pack(tmp_path)
    settings(tmp_path, f'[packs]\nuse = [{entry("zz-shop", digest)}]\ntrust = "official"\n')
    found = doctor.packs_settings_result(tmp_path)
    assert found.message == "(1 packs, trust official, servers 0)"
    severity, ok_text, fail_text, fix = doctor.CHECKS["packs-settings"]
    assert severity == "warn" and ok_text == "ok " and "agk.toml" in fail_text and fix


def test_ac5_doctor_names_the_refused_key_never_the_value(tmp_path):
    """REQ-084 AC5: SPEC-0077 rule 12 (a refusal names the setting and no value)."""
    (tmp_path / "agk.toml").write_text("[packs]\nstale_months = 0\n", encoding="utf-8")
    found = doctor.packs_settings_result(tmp_path)
    assert found.status == "fail"
    assert found.message == "the [packs] table is refused (setting: packs.stale_months)"


def test_ac5_the_kit_itself_has_no_packs_table():
    """REQ-084 AC5: SPEC-0077 rule 12 (the kit's own repository: `agk-core` only)."""
    assert "packs" not in config.config_source(KIT_ROOT)
    assert config.packs_settings(KIT_ROOT) == DEFAULTS
