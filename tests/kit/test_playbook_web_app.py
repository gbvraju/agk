"""Tests of the shipped web-app playbook (SPEC-0038 rules 1, 10 and 11; REQ-045 AC5).

`config/playbooks/web-app.toml` passes the playbook check; it orders `contract`, `mocks`, the two
sides in two parallel lanes, then `joins` ordered by demo value; its `[testing]` profile is
`balanced` with a per-module map and `always_full` for the contract folder; the end-to-end smoke
run is its heavy step; its milestone shape is `per-batch`; it holds the four web-app gates of
rule 10; and every speed claim is `expected`, since no measured record exists. It names the shape
of the work and its gates, never a tool, a vendor or a URL (brief #651 answer 3). It is shipped
verbatim. Reads committed files only: no network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
REL = "config/playbooks/web-app.toml"
PLAYBOOK = KIT_ROOT / REL
SCRIPTS = KIT_ROOT / "scripts" / "agk"


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def phases() -> dict[str, dict]:
    return {p["name"]: p for p in data()["phases"]}


def test_the_playbook_passes_the_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "web-app" == PLAYBOOK.stem
    assert data()["format"] == playbook_format.FORMAT


def test_check_playbooks_passes_on_the_repository() -> None:
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert out.returncode == 0, out.stdout
    assert re.fullmatch(r"ok playbooks \(\d+ playbooks\)\n", out.stdout)


def test_phases_contract_then_mocks_then_two_sides_then_joins() -> None:
    by_name = phases()
    assert list(by_name) == ["contract", "mocks", "front-end", "back-end", "joins"]
    assert by_name["contract"]["after"] == []
    assert by_name["mocks"]["after"] == ["contract"]
    assert by_name["front-end"]["after"] == ["mocks"]
    assert by_name["back-end"]["after"] == ["mocks"]
    assert sorted(by_name["joins"]["after"]) == ["back-end", "front-end"]
    order = {name: p["order"] for name, p in by_name.items()}
    assert order["contract"] < order["mocks"] < order["front-end"] == order["back-end"]
    assert order["back-end"] < order["joins"]


def test_the_two_sides_run_in_two_parallel_lanes() -> None:
    playbook = data()
    lanes = {lane["name"]: lane["kinds"] for lane in playbook["lanes"]}
    assert lanes == {"front-end": ["front-end"], "back-end": ["back-end"]}
    split = playbook["split"]
    assert split["brief_order"] == ["contract", "mock", "front-end", "back-end", "join"]
    pairs = {tuple(p) for p in split["depends_on"]}
    assert pairs == {
        ("mock", "contract"),
        ("front-end", "mock"),
        ("back-end", "mock"),
        ("join", "front-end"),
        ("join", "back-end"),
    }
    # the two sides never depend on each other, so they can run together
    assert ("front-end", "back-end") not in pairs and ("back-end", "front-end") not in pairs


def test_testing_profile_map_and_contract_folder() -> None:
    testing = data()["testing"]
    assert testing["profile"] == "balanced"
    contract = [g for g in testing["always_full"] if g.startswith("contracts/")]
    assert contract, "always_full holds the contract folder"
    codes = [entry["code"] for entry in testing["map"]]
    assert len(codes) >= 2 and len(set(codes)) == len(codes), "a per-module map"
    assert all(entry["tests"] for entry in testing["map"])
    # the contract-tests gate of rule 10: the map names a test glob for every contract path
    assert any(code.startswith("contracts/") for code in codes)


def test_heavy_step_and_milestone_shape() -> None:
    playbook = data()
    assert playbook["heavy_steps"] == ["e2e smoke run"]
    assert playbook["milestones"]["shape"] == "per-batch"
    assert "demo value" in playbook["milestones"]["batch_by"]


def test_the_four_web_app_gates_of_rule_10() -> None:
    gates = {g["id"]: g for g in data()["gates"]}
    assert set(gates) == {"contract-tests", "mock-parity", "e2e-smoke", "accessibility"}
    assert gates["contract-tests"]["kind"] == "check"
    assert gates["mock-parity"]["kind"] == "check"
    assert gates["e2e-smoke"]["kind"] == "judgement"
    assert gates["accessibility"]["kind"] == "judgement"
    assert all(g["step"] for g in gates.values() if g["kind"] == "check")
    assert all("step" not in g for g in gates.values() if g["kind"] == "judgement")
    assert "SPEC-0037" in gates["accessibility"]["text"]
    assert all(g["owner_only"] is False for g in gates.values())
    assert data()["evidence"], "the items a verdict cites"


def test_every_claim_is_expected() -> None:
    claims = data()["claims"]
    assert claims
    assert all(c["basis"] == "expected" and "record" not in c for c in claims)


def test_the_playbook_holds_the_shape_never_a_tool() -> None:
    text = PLAYBOOK.read_text(encoding="utf-8")
    assert "://" not in text and "www." not in text
    assert all(host.endswith("example.com") for host in re.findall(r"@([\w.-]+)", text))
    assert "reviewed" not in data(), "rule 2 allows no key outside the format"


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
