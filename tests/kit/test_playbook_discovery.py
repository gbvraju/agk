"""Tests of the `[[discovery]]` section of the playbook format (SPEC-0048 rule 4, SPEC-0038 rule 2
as amendment 130 widens it; REQ-055 AC2; brief #686).

Every playbook holds `[[discovery]]` entries (`id`, a lower-case slug, and `text`, one plain
question) with at least the five ids `constraints`, `success`, `data-rules`, `environments` and
`non-functional`, each id once. A missing section, a missing required id, a repeated id, an id that
is not a slug, an empty or multi-line question and a key outside the entry each fail, naming the
rule and the file and never a value. The shipped playbooks carry the five. Fixtures in `tmp_path`
only: invented data, no network.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import pytest
from test_check_playbooks import FULL, REL, assert_fails, check, replace, write

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import playbook_format  # noqa: E402

FIVE = ("constraints", "success", "data-rules", "environments", "non-functional")
SUCCESS = '[[discovery]]\nid = "success"\ntext = "How will we know the work succeeded?"\n\n'


def test_ac2_a_playbook_with_the_five_ids_passes(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 4 (the five ids, each once, pass the check)."""
    write(tmp_path)
    result = check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_ac2_the_format_module_names_the_five_required_ids():
    """REQ-055 AC2: SPEC-0048 rule 4 (one constant of the five ids, in the brief's order)."""
    assert tuple(playbook_format.DISCOVERY_IDS) == FIVE
    assert "discovery" in playbook_format.TOP


def test_ac2_a_playbook_without_discovery_fails(tmp_path):
    """REQ-055 AC2: SPEC-0038 rule 2 as amended (`[[discovery]]` is required in every playbook)."""
    text = re.sub(r"\[\[discovery\]\]\nid = \"[a-z-]+\"\ntext = \"[^\"]+\"\n\n", "", FULL)
    assert "[[discovery]]" not in text
    write(tmp_path, text)
    out = assert_fails(tmp_path, 2)
    assert "`discovery`" in out


def test_ac2_a_missing_required_id_fails_naming_the_rule_never_the_value(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 4 (at least the five ids)."""
    write(tmp_path, replace(SUCCESS, ""))
    out = assert_fails(tmp_path, 2)
    assert "required id" in out and "succeeded" not in out


def test_ac2_a_repeated_id_fails(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 4 (each question once)."""
    write(tmp_path, replace(SUCCESS, SUCCESS + SUCCESS.replace("succeeded", "zz-worked")))
    out = assert_fails(tmp_path, 2, "zz-worked")
    assert "twice" in out


def test_ac2_a_playbook_may_add_its_own_question(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 4 (a playbook may add its own ids)."""
    extra = '[[discovery]]\nid = "offline"\ntext = "Must it work without a network?"\n\n'
    write(tmp_path, replace(SUCCESS, SUCCESS + extra))
    result = check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("new", "value"),
    [
        ('[[discovery]]\nid = "Zz_Bad"\ntext = "Is it a slug?"\n\n', "Zz_Bad"),
        ('[[discovery]]\nid = "zz-empty"\ntext = ""\n\n', "zz-empty"),
        ('[[discovery]]\nid = "zz-lines"\ntext = "One?\\nTwo?"\n\n', "zz-lines"),
        ('[[discovery]]\nid = "zz-key"\ntext = "Why?"\nzz_extra = "zz-x"\n\n', "zz-x"),
        ('[[discovery]]\nid = "zz-notext"\n\n', "zz-notext"),
        ('[[discovery]]\nid = 7\ntext = "A number?"\n\n', "A number"),
    ],
    ids=["not-a-slug", "empty-text", "two-lines", "extra-key", "no-text", "wrong-type"],
)
def test_ac2_a_bad_entry_fails_naming_the_rule_never_the_value(tmp_path, new, value):
    """REQ-055 AC2: SPEC-0048 rule 4 (`id` a lower-case slug, `text` one plain question)."""
    write(tmp_path, replace(SUCCESS, SUCCESS + new))
    assert_fails(tmp_path, 2, value)


def test_ac2_discovery_as_a_table_not_a_list_fails(tmp_path):
    """REQ-055 AC2: SPEC-0038 rule 2 (`[[discovery]]` is a list of tables)."""
    text = re.sub(r"\[\[discovery\]\]\nid = \"[a-z-]+\"\ntext = \"[^\"]+\"\n\n", "", FULL)
    text = text.replace("[[claims]]", '[discovery]\nid = "success"\ntext = "Why?"\n\n[[claims]]', 1)
    write(tmp_path, text)
    assert_fails(tmp_path, 2)


@pytest.mark.parametrize("name", ["web-app", "rag-app", "mobile", "cloud-migration"])
def test_ac2_each_shipped_playbook_carries_the_five_ids_once(name):
    """REQ-055 AC2: SPEC-0048 rule 4 (the shipped playbooks gain the five; data only)."""
    path = KIT_ROOT / "config" / "playbooks" / f"{name}.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    ids = [entry["id"] for entry in data["discovery"]]
    assert ids[: len(FIVE)] == list(FIVE)
    assert len(ids) == len(set(ids))
    assert all(entry["text"].endswith("?") for entry in data["discovery"])
    assert playbook_format.problems(path, KIT_ROOT) == []


def test_ac2_the_fixture_relative_path_is_the_web_app_playbook():
    """The shared fixture is the web-app playbook path (guards the imports above)."""
    assert REL == "config/playbooks/web-app.toml"
