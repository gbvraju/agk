"""The `[models]` table of agk.toml: kinds, tiers, efforts and their refusals (SPEC-0045 rules 1-3).

REQ-052 AC1, brief #623 (build (b) of SPEC-0045, ADR-0289). `config.model_settings` reads the
optional table; a kind absent from it gets the defaults of rule 2, and a malformed kind, tier,
effort or value is refused naming the setting (`setting: models.<kind>`), never the value.
`config.model_names` reads the optional `[models.names]` table, which the kit never ships.
Fixtures in `tmp_path`, invented values, no network. The tests were written first (answer 4)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

import config

KIT = Path(__file__).resolve().parents[2]
ODD = "turbo-x"  # an invented value that a refusal must never echo

DEFAULTS = {
    "design": {"tier": "strongest", "effort": "high"},
    "review": {"tier": "strongest", "effort": "high"},
    "build": {"tier": "strongest", "effort": "medium"},
    "small": {"tier": "mid", "effort": "low"},
    "mechanical": {"tier": "mid", "effort": "low"},
}


def project(tmp_path: Path, text: str | None) -> Path:
    if text is not None:
        (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def test_no_agk_toml_gives_every_default(tmp_path):
    """REQ-052 AC1: rules 1 and 2, no agk.toml at all."""
    assert config.model_settings(project(tmp_path, None)) == DEFAULTS
    assert config.model_names(tmp_path) == {}


def test_no_models_table_gives_every_default(tmp_path):
    """REQ-052 AC1: rules 1 and 2, an agk.toml without the table."""
    root = project(tmp_path, 'default_branch = "main"\n')
    assert config.model_settings(root) == DEFAULTS
    assert config.model_names(root) == {}


def test_a_table_setting_one_kind_keeps_the_defaults_of_the_others(tmp_path):
    """REQ-052 AC1: rule 2, a kind absent from the table gets its default."""
    root = project(tmp_path, '[models]\nbuild = { tier = "mid", effort = "high" }\n')
    assert config.model_settings(root) == {**DEFAULTS, "build": {"tier": "mid", "effort": "high"}}


def test_every_kind_tier_and_effort_is_accepted(tmp_path):
    """REQ-052 AC1: rule 2, the five kinds, three tiers and three efforts."""
    lines = [
        'design = { tier = "strongest", effort = "medium" }',
        'review = { tier = "strongest", effort = "high" }',
        'build = { tier = "fast", effort = "low" }',
        'small = { tier = "fast", effort = "medium" }',
        'mechanical = { tier = "strongest", effort = "high" }',
    ]
    got = config.model_settings(project(tmp_path, "[models]\n" + "\n".join(lines) + "\n"))
    assert got["build"] == {"tier": "fast", "effort": "low"}
    assert got["mechanical"] == {"tier": "strongest", "effort": "high"}
    assert set(got) == set(DEFAULTS)


@pytest.mark.parametrize(
    ("text", "setting"),
    [
        (f'[models]\n{ODD} = {{ tier = "mid", effort = "low" }}\n', ODD),  # unknown kind
        (f'[models]\nbuild = {{ tier = "{ODD}", effort = "low" }}\n', "build"),
        (f'[models]\nsmall = {{ tier = "mid", effort = "{ODD}" }}\n', "small"),
        ('[models]\nbuild = { tier = 3, effort = "low" }\n', "build"),  # not a string
        ('[models]\ndesign = { tier = "strongest", effort = true }\n', "design"),
        (f'[models]\nbuild = "{ODD}"\n', "build"),  # not a table
        ('[models]\nbuild = { tier = "mid" }\n', "build"),  # no effort
        (f'[models]\nbuild = {{ tier = "mid", effort = "low", x = "{ODD}" }}\n', "build"),
        (f'models = "{ODD}"\n', "models"),  # the table itself is not a table
    ],
)
def test_a_malformed_entry_is_refused_naming_the_setting_never_the_value(tmp_path, text, setting):
    """REQ-052 AC1: rule 2, each malformed kind, tier, effort and non-string value."""
    root = project(tmp_path, text)
    with pytest.raises(config.ModelSettingError) as caught:
        config.model_settings(root)
    message = str(caught.value)
    assert message.endswith(
        f"(setting: {'models' if setting == 'models' else 'models.' + setting})"
    )
    if setting != ODD:  # an unknown kind is the setting's own name
        assert ODD not in message


@pytest.mark.parametrize("tier", ["mid", "fast"])
def test_review_below_strongest_is_refused(tmp_path, tier):
    """REQ-052 AC1: rules 2 and 6, a reviewer is never below `strongest`."""
    root = project(tmp_path, f'[models]\nreview = {{ tier = "{tier}", effort = "high" }}\n')
    with pytest.raises(config.ModelSettingError) as caught:
        config.model_settings(root)
    assert "setting: models.review" in str(caught.value)
    assert tier not in str(caught.value)


@pytest.mark.parametrize("effort", ["low", "medium"])
def test_review_below_high_effort_is_refused(tmp_path, effort):
    """REQ-052 AC1: rule 6, a first review runs at an effort no lower than `high` (Q-623-1)."""
    root = project(tmp_path, f'[models]\nreview = {{ tier = "strongest", effort = "{effort}" }}\n')
    with pytest.raises(config.ModelSettingError) as caught:
        config.model_settings(root)
    assert "setting: models.review" in str(caught.value)


def test_an_unreadable_agk_toml_is_refused_naming_the_table(tmp_path):
    """REQ-052 AC1: a malformed file lowers nothing; it is refused."""
    root = project(tmp_path, "[models\n")
    with pytest.raises(config.ModelSettingError) as caught:
        config.model_settings(root)
    assert "setting: models" in str(caught.value)


def test_the_names_table_maps_a_tier_to_a_project_model_name(tmp_path):
    """REQ-052 AC1: rule 3, one optional `[models.names]` table; it is not a kind."""
    text = (
        '[models]\nsmall = { tier = "fast", effort = "low" }\n'
        '[models.names]\nfast = "example-fast-1"\n'
    )
    root = project(tmp_path, text)
    assert config.model_names(root) == {"fast": "example-fast-1"}
    assert config.model_settings(root)["small"] == {"tier": "fast", "effort": "low"}


@pytest.mark.parametrize(
    ("text", "setting"),
    [
        (f'[models.names]\n{ODD} = "example-1"\n', f"models.names.{ODD}"),  # not a tier
        ("[models.names]\nmid = 7\n", "models.names.mid"),  # not a string
        ('[models.names]\nmid = ""\n', "models.names.mid"),  # empty
        (f'[models]\nnames = "{ODD}"\n', "models.names"),  # not a table
    ],
)
def test_a_malformed_names_table_is_refused(tmp_path, text, setting):
    """REQ-052 AC1: rule 3, refused naming the setting, never the value."""
    root = project(tmp_path, text)
    for read in (config.model_names, config.model_settings):
        with pytest.raises(config.ModelSettingError) as caught:
            read(root)
        assert f"setting: {setting}" in str(caught.value)
        if ODD not in setting:
            assert ODD not in str(caught.value)


def kit_tomls() -> list[Path]:
    found = [KIT / "agk.toml"]
    found += sorted((KIT / "kit" / "templates").rglob("*.toml"))
    return [p for p in found if p.is_file()]


def test_the_kit_ships_no_model_name():
    """REQ-052 AC1: rule 3, the kit's agk.toml and templates carry no `[models.names]`."""
    paths = kit_tomls()
    assert KIT / "agk.toml" in paths and len(paths) > 1
    for path in paths:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        data = data.get("tool", {}).get("agk", data) if path.name == "pyproject.toml" else data
        models = data.get("models", {})
        assert "names" not in models, path
        assert "[models.names]" not in path.read_text(encoding="utf-8"), path


def test_the_kit_own_table_is_valid():
    """REQ-052 AC1: rule 1, the kit's own agk.toml reads without a refusal."""
    assert set(config.model_settings(KIT)) == set(DEFAULTS)
