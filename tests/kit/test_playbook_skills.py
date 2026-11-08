"""Tests of the `skills` key of the playbook format (SPEC-0048 rule 12, SPEC-0038 rule 2 as
amendment 130 widens it; REQ-055 AC6; brief #691).

A playbook may name, in the optional list `skills`, the skills a session should have on. Each name
matches doctor's `ENGINE_NAME`; a name outside the pattern, or one holding a token of
`config/neutrality.txt`, fails naming the rule, the file and the key and never the value. The kit
ships none of the skills a playbook names. Fixtures in `tmp_path` only: invented data, no network.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest
from test_check_playbooks import FULL, assert_fails, check, write

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import doctor  # noqa: E402
import playbook_format  # noqa: E402

HEAD = 'title = "Contract first, then mocks, then both sides in parallel, then joins"\n'


def with_skills(value: str) -> str:
    """The full fixture playbook with one top-level `skills = <value>` line."""
    assert HEAD in FULL
    return FULL.replace(HEAD, f"{HEAD}skills = {value}\n", 1)


def neutrality(root: Path, text: str) -> None:
    path = root / "config" / "neutrality.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_ac6_the_key_is_optional_and_two_names_pass(tmp_path):
    """REQ-055 AC6: SPEC-0048 rule 12 (a playbook may name skills; the key is not required)."""
    write(tmp_path)
    assert check(tmp_path).returncode == 0
    write(tmp_path, with_skills('["front-end-design", "a11y-review"]'))
    result = check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_ac6_an_empty_list_passes(tmp_path):
    """REQ-055 AC6: SPEC-0048 rule 12 (a list of no names is a list)."""
    write(tmp_path, with_skills("[]"))
    assert check(tmp_path).returncode == 0


@pytest.mark.parametrize("value", ['"zz-one-name"', "7", '["zz-ok", 7]', "true"])
def test_ac6_a_key_of_the_wrong_type_fails_naming_the_key(tmp_path, value):
    """REQ-055 AC6: SPEC-0038 rule 2 as amended (`skills` is a list of strings)."""
    write(tmp_path, with_skills(value))
    out = assert_fails(tmp_path, 2, "zz-one-name")
    assert "`skills`" in out


@pytest.mark.parametrize(
    "name",
    ["Zz-Upper", "zz under", "../zz-up", "1zz", "plugin:zz", "zz_snake", "zz.name", "zz-name\n"],
)
def test_ac6_a_name_outside_the_pattern_is_refused_naming_the_key(tmp_path, name):
    """REQ-055 AC6: SPEC-0048 rule 12's test (refused naming the key, never the value)."""
    write(tmp_path, with_skills(json.dumps([name])))
    out = assert_fails(tmp_path, 12, name.strip())
    assert "`skills`" in out


def test_ac6_an_empty_name_is_refused(tmp_path):
    """REQ-055 AC6: SPEC-0048 rule 12 (the empty string does not match the pattern)."""
    write(tmp_path, with_skills('[""]'))
    assert "`skills`" in assert_fails(tmp_path, 12)


def test_ac6_the_pattern_is_the_one_doctor_uses():
    """REQ-055 AC6: SPEC-0048 rule 12 (each name matches doctor's `ENGINE_NAME`)."""
    assert playbook_format.SLUG.pattern == doctor.ENGINE_NAME.pattern


@pytest.mark.parametrize("token", ["zzvendor", "ZZVENDOR"])
def test_ac6_a_name_with_a_neutrality_token_is_refused(tmp_path, token):
    """REQ-055 AC6: Q-S0048-16 (`config/neutrality.txt` applies; case-insensitive, no value shown)."""
    write(tmp_path, with_skills('["zzvendor-design"]'))
    neutrality(tmp_path, f"# a comment\n\n{token}\n")
    out = assert_fails(tmp_path, 12, "zzvendor")
    assert "`skills`" in out and "config/neutrality.txt" in out
    assert token not in out


def test_ac6_a_comment_of_the_token_list_refuses_nothing(tmp_path):
    """REQ-055 AC6: Q-S0048-16 (only the tokens of the list count)."""
    write(tmp_path, with_skills('["comment-reader"]'))
    neutrality(tmp_path, "# comment\n")
    assert check(tmp_path).returncode == 0


def test_ac6_no_token_list_refuses_nothing(tmp_path):
    """REQ-055 AC6: Q-S0048-16 (a project without the file has no token to apply)."""
    write(tmp_path, with_skills('["front-end-design"]'))
    assert not (tmp_path / "config" / "neutrality.txt").exists()
    assert check(tmp_path).returncode == 0


def test_ac6_the_reader_returns_the_names_in_order(tmp_path):
    """REQ-055 AC6: SPEC-0048 rule 12 (`skills` gives doctor each name, in the playbook's order)."""
    path = write(tmp_path, with_skills('["zeta-skill", "alpha-skill"]'))
    assert playbook_format.skills(path, tmp_path) == ["zeta-skill", "alpha-skill"]


def test_ac6_the_reader_gives_no_refused_name(tmp_path):
    """REQ-055 AC6: principle 8 (a refused name is never handed to a line that prints it)."""
    neutrality(tmp_path, "zzvendor\n")
    path = write(tmp_path, with_skills('["Zz-Upper", "good-name", "zzvendor-design"]'))
    assert playbook_format.skills(path, tmp_path) == ["good-name"]


@pytest.mark.parametrize("text", ["not = [toml", 'skills = "zz-one"\n', "format = 1\n"])
def test_ac6_the_reader_gives_nothing_from_a_broken_or_silent_playbook(tmp_path, text):
    """REQ-055 AC6: SPEC-0048 rule 12 (no name to report blocks nothing and raises nothing)."""
    path = write(tmp_path, text)
    assert playbook_format.skills(path, tmp_path) == []


def test_ac6_the_kit_ships_no_skill_a_playbook_names():
    """REQ-055 AC6: SPEC-0048 rule 12's test (the kit's file list holds no skill of a playbook)."""
    manifest = (KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8")
    for path in playbook_format.playbooks(KIT_ROOT):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        for name in data.get("skills", []):
            assert not (KIT_ROOT / "skills" / name).exists(), path.name
            assert f"skills/{name}/" not in manifest, path.name
