"""Tests of the shipped base playbook (SPEC-0048 rule 21, build (i)).

SPEC-0038 rules 1 and 4 as amendment 130 widens them.

REQ-055 AC8. `config/playbooks/default.toml` passes the playbook check and holds exactly the five
gates of rule 21: `tests-first`, `contract-first`, `evidence-per-gate`, `rollback` and
`definition-of-done`. By `Q-S0048-29` a gate is `check` only where an existing governance step
verifies it from committed files with no network; no step does for any of the five, so each is
`judgement` and none is left out. `default` is a playbook name and never a work type: a `[delivery]`
line that names it is refused, naming `work_type` and never the value, and the commands that take a
work type do not list it. The kit's `config/playbooks/` holds only `default` and kinds of SPEC-0038
rule 1's list. It is shipped verbatim. Reads committed files and temporary fixtures only: no
network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
REL = "config/playbooks/default.toml"
PLAYBOOK = KIT_ROOT / REL
SCRIPTS = KIT_ROOT / "scripts" / "agk"
GATES = ("tests-first", "contract-first", "evidence-per-gate", "rollback", "definition-of-done")

sys.path.insert(0, str(SCRIPTS))
import playbook_format  # noqa: E402


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def gates() -> dict[str, dict]:
    return {g["id"]: g for g in data()["gates"]}


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def declared(tmp_path: Path, value: str) -> Path:
    """A fixture project that ships the base playbook and declares `value`."""
    (tmp_path / "config" / "playbooks").mkdir(parents=True)
    (tmp_path / REL).write_text(PLAYBOOK.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "agk.toml").write_text(f'[delivery]\nwork_type = "{value}"\n', encoding="utf-8")
    return tmp_path


def test_the_playbook_passes_the_check() -> None:
    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "default" == PLAYBOOK.stem
    assert data()["format"] == playbook_format.FORMAT


def test_check_playbooks_passes_with_seven_playbooks() -> None:
    out = check(KIT_ROOT)
    assert out.returncode == 0, out.stdout
    assert out.stdout == "ok playbooks (7 playbooks)\n"


def test_exactly_the_five_gates_of_rule_21_in_its_order() -> None:
    assert tuple(g["id"] for g in data()["gates"]) == GATES


def test_each_gate_says_what_rule_21_says() -> None:
    by_id = gates()
    words = {
        "tests-first": ("tests of a brief", "before its code"),
        "contract-first": ("contract or interface file", "before the build", "test glob"),
        "evidence-per-gate": ("every gate", "evidence item", "verdict"),
        "rollback": ("every change that is applied", "rollback or undo path", "recorded"),
        "definition-of-done": ("every brief", "acceptance criteria", "tests"),
    }
    for gid, needed in words.items():
        text = by_id[gid]["text"].lower()
        for word in needed:
            assert word in text, (gid, word)


def test_no_gate_is_a_check_without_an_existing_governance_step() -> None:
    # Q-S0048-29: the existing steps of agk-governance verify none of the five from committed files
    by_id = gates()
    assert {g["kind"] for g in by_id.values()} == {"judgement"}
    assert all("step" not in g for g in by_id.values())


def test_no_gate_is_owner_only() -> None:
    assert not any(g["owner_only"] for g in gates().values())


def test_a_verdict_has_one_evidence_item_per_gate() -> None:
    evidence = data()["evidence"]
    assert len(evidence) == len(GATES)
    for needle in ("tests", "contract", "cites", "rollback", "acceptance criteria"):
        assert any(needle in item for item in evidence), needle


def test_the_base_invents_no_order_of_work_and_no_claim() -> None:
    playbook = data()
    assert playbook["phases"] == [] and playbook["lanes"] == []
    assert playbook["split"] == {"brief_order": [], "depends_on": []}
    assert playbook["heavy_steps"] == []
    assert playbook["claims"] == []
    assert playbook["testing"] == {"profile": "balanced", "always_full": [], "map": []}
    assert playbook["milestones"]["shape"] == "per-brief"
    assert "modules" not in playbook and "skills" not in playbook


def test_the_five_discovery_questions_are_there() -> None:
    assert tuple(i for i, _ in playbook_format.discovery(PLAYBOOK)) == playbook_format.DISCOVERY_IDS


def test_default_is_not_a_work_type() -> None:
    assert "default" not in playbook_format.WORK_TYPES
    assert playbook_format.BASE == "default"


def test_a_declaration_of_default_is_refused_naming_the_setting(tmp_path: Path) -> None:
    root = declared(tmp_path, "default")
    value, found = playbook_format.declaration(root)
    assert value is None
    assert len(found) == 1
    assert "(setting: work_type)" in found[0] and "rule 5" in found[0]
    assert '"default"' not in found[0] and " default " not in found[0]
    assert playbook_format.selected(root) is None


def test_check_playbooks_fails_a_declaration_of_default(tmp_path: Path) -> None:
    out = check(declared(tmp_path, "default"))
    assert out.returncode == 1
    assert out.stdout.startswith("FAIL playbooks: rule 5: agk.toml:")
    assert "(setting: work_type)" in out.stdout


@pytest.mark.parametrize("stem", ["web-app", "other"])
def test_the_name_default_belongs_to_the_base_file_alone(tmp_path: Path, stem: str) -> None:
    (tmp_path / "config" / "playbooks").mkdir(parents=True)
    path = tmp_path / "config" / "playbooks" / f"{stem}.toml"
    path.write_text(PLAYBOOK.read_text(encoding="utf-8"), encoding="utf-8")
    found = playbook_format.problems(path, tmp_path)
    assert found == [f"rule 1: config/playbooks/{stem}.toml: `work_type` is not the file's name"]


def test_any_other_unknown_work_type_is_still_refused(tmp_path: Path) -> None:
    (tmp_path / "config" / "playbooks").mkdir(parents=True)
    path = tmp_path / "config" / "playbooks" / "other.toml"
    text = PLAYBOOK.read_text(encoding="utf-8")
    path.write_text(text.replace('work_type = "default"', 'work_type = "other"'), encoding="utf-8")
    found = playbook_format.problems(path, tmp_path)
    assert found == [
        "rule 1: config/playbooks/other.toml: `work_type` is not one of the work types"
    ]


def test_the_kit_ships_only_default_and_kinds_of_the_list() -> None:
    stems = {p.stem for p in playbook_format.playbooks(KIT_ROOT)}
    assert "default" in stems
    assert stems <= set(playbook_format.WORK_TYPES) | {"default"}


def test_the_playbook_names_no_vendor_product_or_tool() -> None:
    text = PLAYBOOK.read_text(encoding="utf-8")
    assert "://" not in text and "www." not in text
    assert not re.search(r"\b\d+\.\d+(\.\d+)?\b", text)
    lowered = text.lower()
    for word in ("anthropic", "claude", "openai", "gpt", "google", "microsoft", "amazon", "aws",
                 "azure", "github", "python", "sql", "secret"):
        assert not re.search(rf"\b{re.escape(word)}s?\b", lowered), word


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
