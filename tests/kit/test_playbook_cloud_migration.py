"""Tests of the shipped cloud-migration playbook (SPEC-0038 rules 1, 10 and 12 build (j)).

REQ-045 AC6. `config/playbooks/cloud-migration.toml` passes the playbook check, and
`check_playbooks.py` passes with five playbooks. It holds exactly the cloud-migration gates of rule
10: inventory, then wave plan, then cut-over, `check` that each cut-over brief depends on its wave
plan brief, which depends on the inventory brief; a rollback rehearsal as evidence, `judgement`;
plan diffs as evidence, `judgement`, a committed plan output with no credential in it; and any
apply, `judgement` and `owner_only`. Every speed claim is `expected`, since no run has measured it.
It names the shape of the work and its gates, never a vendor, a cloud, a region, an account or a
tool (brief #724 answer 1). It is shipped verbatim. Reads committed files only: no network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
REL = "config/playbooks/cloud-migration.toml"
PLAYBOOK = KIT_ROOT / REL
SCRIPTS = KIT_ROOT / "scripts" / "agk"
ORDER = ["inventory", "wave-plan", "cut-over"]


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def gates() -> dict[str, dict]:
    return {g["id"]: g for g in data()["gates"]}


def test_the_playbook_passes_the_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "cloud-migration" == PLAYBOOK.stem
    assert data()["format"] == playbook_format.FORMAT


def test_check_playbooks_passes_with_five_playbooks() -> None:
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert out.returncode == 0, out.stdout
    assert out.stdout == "ok playbooks (5 playbooks)\n"


def test_phases_inventory_then_wave_plan_then_cut_over() -> None:
    phases = data()["phases"]
    assert [p["name"] for p in phases] == ORDER
    assert [p["order"] for p in phases] == [1, 2, 3]
    assert [p["after"] for p in phases] == [[], ["inventory"], ["wave-plan"]]


def test_each_cut_over_brief_depends_on_its_wave_plan_which_depends_on_the_inventory() -> None:
    split = data()["split"]
    assert split["brief_order"] == ORDER
    assert sorted(map(tuple, split["depends_on"])) == [
        ("cut-over", "wave-plan"),
        ("wave-plan", "inventory"),
    ]


def test_nothing_beyond_rule_10_is_invented() -> None:
    # rule 10 gives the order and the gates; no lane, test map, heavy step or batching is invented
    playbook = data()
    assert playbook["lanes"] == []
    assert playbook["heavy_steps"] == []
    assert playbook["milestones"]["shape"] == "per-brief"
    testing = playbook["testing"]
    assert testing["profile"] == "balanced"
    assert testing["always_full"] == [] and testing["map"] == []


def test_exactly_the_cloud_migration_gates_of_rule_10() -> None:
    by_id = gates()
    assert set(by_id) == {"cut-over-order", "rollback-rehearsal", "plan-diffs", "apply"}
    order = by_id["cut-over-order"]
    assert order["kind"] == "check"
    for word in ("inventory", "wave plan", "cut-over", "depends on"):
        assert word in order["text"], word
    rehearsal = by_id["rollback-rehearsal"]
    assert rehearsal["kind"] == "judgement"
    assert "rollback rehearsal" in rehearsal["text"] and "evidence" in rehearsal["text"]
    diffs = by_id["plan-diffs"]
    assert diffs["kind"] == "judgement"
    assert "plan" in diffs["text"] and "committed" in diffs["text"]
    assert "no credential" in diffs["text"]
    apply = by_id["apply"]
    assert apply["kind"] == "judgement"
    assert "apply" in apply["text"].lower() and "owner" in apply["text"]
    assert apply["owner_only"] is True


def test_owner_only_is_the_apply_gate_alone() -> None:
    assert [gid for gid, g in gates().items() if g["owner_only"]] == ["apply"]


def test_the_check_gate_names_a_step_and_judgement_gates_none() -> None:
    # the check gate names the step a later build adds; until then it is read as judgement
    # (Q-651-2, brief #724 answer 2), and this build adds no governance step
    by_id = gates()
    checks = {gid: g for gid, g in by_id.items() if g["kind"] == "check"}
    assert set(checks) == {"cut-over-order"}
    assert checks["cut-over-order"]["step"] == "cut-over-order"
    assert all("step" not in g for g in by_id.values() if g["kind"] == "judgement")


def test_no_governance_step_is_added_for_the_check_gate() -> None:
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    assert "cut-over-order" not in mk


def test_the_evidence_names_the_gates_records() -> None:
    evidence = data()["evidence"]
    assert any("inventory" in item and "cut-over" in item for item in evidence)
    assert any("rollback rehearsal" in item for item in evidence)
    assert any("plan" in item and "committed" in item for item in evidence)
    assert any("apply" in item and "owner" in item for item in evidence)


def test_every_claim_is_expected() -> None:
    claims = data()["claims"]
    assert claims
    assert all(c["basis"] == "expected" and "record" not in c for c in claims)


def test_the_playbook_names_no_vendor_cloud_region_account_or_tool() -> None:
    text = PLAYBOOK.read_text(encoding="utf-8")
    assert "://" not in text and "www." not in text
    assert all(host.endswith("example.com") for host in re.findall(r"@([\w.-]+)", text))
    assert not re.search(r"\b\d+\.\d+(\.\d+)?\b", text.replace("format = 1", ""))
    lowered = text.lower()
    for word in ("aws", "amazon", "azure", "gcp", "google", "oracle", "ibm", "alibaba",
                 "terraform", "pulumi", "ansible", "kubernetes", "cloudformation", "helm",
                 "region", "account", "subscription", "tenant", "zone", "secret"):
        assert not re.search(rf"\b{re.escape(word)}s?\b", lowered), word
    assert "reviewed" not in data(), "rule 2 allows no key outside the format (Q-651-1)"


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
