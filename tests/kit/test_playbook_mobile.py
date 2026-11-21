"""Tests of the shipped mobile playbook (SPEC-0038 rules 1, 10 and 12 build (i); REQ-045 AC6).

`config/playbooks/mobile.toml` passes the playbook check, and `check_playbooks.py` passes with four
playbooks. It holds exactly the mobile gates of rule 10: a device and simulator matrix, `check` that
the matrix file lists the playbook's minimum entries, with its results `judgement`; offline states,
`check` that each screen of the inventory lists an `offline` state; and store signing, `judgement`
and `owner_only`. Every speed claim is `expected`, since no run has measured it. It names the shape
of the work and its gates, never a vendor, a device, a store or a tool (brief #721 answer 1). It is
shipped verbatim. Reads committed files only: no network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
REL = "config/playbooks/mobile.toml"
PLAYBOOK = KIT_ROOT / REL
SCRIPTS = KIT_ROOT / "scripts" / "agk"


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def gates() -> dict[str, dict]:
    return {g["id"]: g for g in data()["gates"]}


def test_the_playbook_passes_the_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "mobile" == PLAYBOOK.stem
    assert data()["format"] == playbook_format.FORMAT


def test_check_playbooks_passes_with_eleven_playbooks() -> None:
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert out.returncode == 0, out.stdout
    gates = "not run tests-first: no work type\nok secrets\nok environment-settings\n"
    gates += "ok gates (3 check gates; not run: tests-first)\n"  # briefs #1593 and #1590
    assert out.stdout == "ok playbooks (11 playbooks)\n" + gates


def test_exactly_the_mobile_gates_of_rule_10() -> None:
    by_id = gates()
    assert set(by_id) == {
        "device-matrix",
        "device-matrix-results",
        "offline-states",
        "store-signing",
    }
    # a device and simulator matrix: judgement with a reason since ADR-0666 (brief #1586)
    matrix = by_id["device-matrix"]
    assert matrix["kind"] == "judgement"
    assert "matrix" in matrix["text"] and "minimum entries" in matrix["text"]
    assert "simulator" in matrix["text"]
    # ... with its results judgement
    results = by_id["device-matrix-results"]
    assert results["kind"] == "judgement"
    assert "results" in results["text"] and "matrix" in results["text"]
    # offline states: judgement with a reason since ADR-0666 (each screen lists an `offline` state)
    offline = by_id["offline-states"]
    assert offline["kind"] == "judgement"
    assert "screen" in offline["text"] and "inventory" in offline["text"]
    assert "offline" in offline["text"]
    # store signing: judgement and owner_only
    signing = by_id["store-signing"]
    assert signing["kind"] == "judgement"
    assert "signing" in signing["text"]
    assert signing["owner_only"] is True


def test_owner_only_is_the_store_signing_gate_alone() -> None:
    by_id = gates()
    assert [gid for gid, g in by_id.items() if g["owner_only"]] == ["store-signing"]


def test_check_gates_name_a_step_and_judgement_gates_none() -> None:
    # both check gates name the step a later build adds; until then they are read as judgement
    # (Q-651-2, brief #721 answer 2), and this build adds no governance step
    by_id = gates()
    # SPEC-0072 rule 3 (ADR-0666, brief #1586): both are restated as judgement with a reason
    assert {gid for gid, g in by_id.items() if g["kind"] == "check"} == set()
    assert all("(ADR-0666)" in by_id[gid]["reason"] for gid in ("device-matrix", "offline-states"))
    assert all("step" not in g for g in by_id.values() if g["kind"] == "judgement")


def test_no_governance_step_is_added_for_the_check_gates() -> None:
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    assert "device-matrix" not in mk and "offline-states" not in mk


def test_the_shape_is_one_brief_at_a_time() -> None:
    # rule 10 gives mobile gates only: no phase order, lane or milestone shape is invented
    playbook = data()
    assert [p["name"] for p in playbook["phases"]] == ["build"]
    assert playbook["phases"][0]["after"] == []
    assert playbook["split"]["brief_order"] == ["foundation", "build"]  # SPEC-0072 rule 4
    assert playbook["split"]["depends_on"] == []
    assert playbook["lanes"] == []
    assert playbook["milestones"]["shape"] == "per-brief"
    assert playbook["heavy_steps"] == []
    testing = playbook["testing"]
    assert testing["profile"] == "balanced"
    assert testing["always_full"] == [] and testing["map"] == []


def test_the_evidence_names_the_gates_records() -> None:
    evidence = data()["evidence"]
    assert any("matrix" in item for item in evidence)
    assert any("offline" in item for item in evidence)
    assert any("signing" in item for item in evidence)


def test_every_claim_is_expected() -> None:
    claims = data()["claims"]
    assert claims
    assert all(c["basis"] == "expected" and "record" not in c for c in claims)


def test_the_playbook_names_no_vendor_device_store_or_tool() -> None:
    text = PLAYBOOK.read_text(encoding="utf-8")
    assert "://" not in text and "www." not in text
    assert all(host.endswith("example.com") for host in re.findall(r"@([\w.-]+)", text))
    assert not re.search(r"\b\d+\.\d+(\.\d+)?\b", text.replace("format = 1", ""))
    lowered = text.lower()
    for word in ("android", "ios", "iphone", "ipad", "pixel", "galaxy", "xcode", "gradle",
                 "play store", "app store", "testflight", "emulator"):
        assert not re.search(rf"\b{re.escape(word)}\b", lowered), word
    assert "reviewed" not in data(), "rule 2 allows no key outside the format (Q-651-1)"


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
