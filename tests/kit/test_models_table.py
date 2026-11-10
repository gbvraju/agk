"""The `[models]` table of agk.toml: kinds, tiers, efforts and their refusals (SPEC-0045 rules 1-3).

REQ-052 AC1, brief #623 (build (b) of SPEC-0045, ADR-0289). `config.model_settings` reads the
optional table; a kind absent from it gets the defaults of rule 2, and a malformed kind, tier,
effort or value is refused naming the setting (`setting: models.<kind>`), never the value.
`config.model_names` reads the optional `[models.names]` table, which the kit never ships.
Fixtures in `tmp_path`, invented values, no network. The tests were written first (answer 4).

REQ-060, brief #763 (build (b) of SPEC-0053, ADR-0344): `config.model_providers` reads the optional
`[models.providers]` table, a tier to an ordered list of plain labels. The tests of the command
that reads it are in `test_session_kind.py`, which the test map already selects."""

from __future__ import annotations

import re
import subprocess  # nosec B404 - the tests stub it or list the tracked files, no shell
import tomllib
from pathlib import Path

import pytest

import config

KIT = Path(__file__).resolve().parents[2]
PLACEHOLDER = re.compile(r"\{\{[a-z_]+\}\}")
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
        text = PLACEHOLDER.sub("[]", path.read_text(encoding="utf-8"))  # an install fills them
        data = tomllib.loads(text)
        data = data.get("tool", {}).get("agk", data) if path.name == "pyproject.toml" else data
        models = data.get("models", {})
        assert "names" not in models, path
        assert "[models.names]" not in text, path


def test_the_kit_own_table_is_valid():
    """REQ-052 AC1: rule 1, the kit's own agk.toml reads without a refusal."""
    assert set(config.model_settings(KIT)) == set(DEFAULTS)


# --- the provider lists (SPEC-0053 rule 3, REQ-060, brief #763) ------------------------------

ALPHA, BETA, GAMMA = "alpha-1", "beta-2", "gamma-3"
LISTS = f'[models.providers]\nstrongest = ["{ALPHA}", "{BETA}"]\nmid = ["{GAMMA}"]\n'
ENDPOINT = "https://alpha.example.com"
LONG = "a" * 65


def test_no_provider_table_changes_nothing(tmp_path):
    """REQ-060 AC1: rules 1 and 3, no table reads as today and lists no provider."""
    root = project(tmp_path, '[models]\nbuild = { tier = "mid", effort = "high" }\n')
    assert config.model_providers(root) == {}
    assert config.model_names(root) == {}
    assert config.model_settings(root) == {**DEFAULTS, "build": {"tier": "mid", "effort": "high"}}
    assert config.model_providers(project(tmp_path, None)) == {}


def test_the_lists_read_in_order_for_each_tier(tmp_path):
    """REQ-060 AC2: rule 3, each tier keeps its own list in the order of trial."""
    root = project(tmp_path, LISTS)
    assert config.model_providers(root) == {"strongest": [ALPHA, BETA], "mid": [GAMMA]}
    assert config.model_settings(root) == DEFAULTS


def test_a_first_entry_equal_to_the_names_table_is_accepted(tmp_path):
    """REQ-060 AC2: rule 3, `[models.names]` stays and equals the first label where it is set."""
    root = project(tmp_path, f'[models.names]\nstrongest = "{ALPHA}"\n{LISTS}')
    assert config.model_providers(root)["strongest"] == [ALPHA, BETA]
    assert config.model_names(root) == {"strongest": ALPHA}


@pytest.mark.parametrize("label", ["a", "7", "a" * 64, "Alpha.2_b-c", "0-x"])
def test_a_plain_label_is_accepted(tmp_path, label):
    """REQ-060 AC2: rule 3, 1 to 64 letters, digits, `.`, `_`, `-`, from a letter or a digit."""
    root = project(tmp_path, f'[models.providers]\nfast = ["{label}"]\n')
    assert config.model_providers(root) == {"fast": [label]}


@pytest.mark.parametrize(
    ("body", "setting", "value"),
    [
        (f'mid = ["{ENDPOINT}"]', "models.providers.mid", ENDPOINT),
        ('mid = ["team@example.com"]', "models.providers.mid", "team@example.com"),
        ('mid = ["alpha/one"]', "models.providers.mid", "alpha/one"),
        ('mid = ["alpha one"]', "models.providers.mid", "alpha one"),
        ('mid = ["alpha:1"]', "models.providers.mid", "alpha:1"),
        ('mid = [".alpha"]', "models.providers.mid", ".alpha"),
        ('mid = ["-alpha"]', "models.providers.mid", "-alpha"),
        ('mid = [""]', "models.providers.mid", None),
        (f'mid = ["{LONG}"]', "models.providers.mid", LONG),
        ("mid = []", "models.providers.mid", None),
        (f'mid = ["{ALPHA}", "{ALPHA}"]', "models.providers.mid", ALPHA),
        (f'mid = "{ALPHA}"', "models.providers.mid", ALPHA),
        ("mid = [7]", "models.providers.mid", None),
        (f'{ODD} = ["{ALPHA}"]', "models.providers", ODD),
    ],
)
def test_a_refused_list_names_the_setting_never_the_value(tmp_path, body, setting, value):
    """REQ-060 AC2: rule 3, each refused shape, read by both readers of the table."""
    root = project(tmp_path, f"[models.providers]\n{body}\n")
    for read in (config.model_providers, config.model_settings):
        with pytest.raises(config.ModelSettingError) as caught:
            read(root)
        assert str(caught.value).endswith(f"(setting: {setting})")
        if value is not None:
            assert value not in str(caught.value)


def test_a_label_under_two_tiers_is_refused(tmp_path):
    """REQ-060 AC2: rule 3, a label belongs to one tier."""
    root = project(tmp_path, f'[models.providers]\nmid = ["{ALPHA}"]\nfast = ["{ALPHA}"]\n')
    with pytest.raises(config.ModelSettingError) as caught:
        config.model_providers(root)
    assert "setting: models.providers" in str(caught.value)
    assert ALPHA not in str(caught.value)


def test_a_first_entry_that_differs_from_the_names_table_is_refused(tmp_path):
    """REQ-060 AC2: rule 3, the first label is the tier's named model where one is set."""
    text = f'[models.names]\nstrongest = "{GAMMA}"\n[models.providers]\nstrongest = ["{ALPHA}"]\n'
    with pytest.raises(config.ModelSettingError) as caught:
        config.model_providers(project(tmp_path, text))
    assert str(caught.value).endswith("(setting: models.providers.strongest)")
    assert ALPHA not in str(caught.value) and GAMMA not in str(caught.value)


def test_a_providers_value_that_is_not_a_table_is_refused(tmp_path):
    """REQ-060 AC2: rule 3, `[models].providers` must be a table."""
    root = project(tmp_path, f'[models]\nproviders = "{ALPHA}"\n')
    with pytest.raises(config.ModelSettingError) as caught:
        config.model_providers(root)
    assert str(caught.value).endswith("(setting: models.providers)")
    assert ALPHA not in str(caught.value)


def test_no_tracked_toml_or_template_carries_a_provider_list():
    """REQ-060 AC7: rule 3 and rule 9, the kit ships no provider list."""
    tracked = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "ls-files", "*.toml"],
        cwd=KIT,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout.split()
    assert "agk.toml" in tracked
    templates = [p for p in (KIT / "kit" / "templates").rglob("*") if p.is_file()]
    assert templates
    for path in [KIT / name for name in tracked] + templates:
        assert "[models.providers]" not in path.read_text(encoding="utf-8", errors="ignore"), path
    assert config.model_providers(KIT) == {}
