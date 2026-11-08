"""Tests of the shipped pilot playbook (SPEC-0038 rules 1, 10, 11 and 12 build (n)).

REQ-045 AC5. `config/playbooks/pilot.toml` passes the playbook check, and `check_playbooks.py`
passes with ten playbooks. It orders `intake`, `research`, `choice`, `contract`, `build` with its
three lanes, `demo` and `report`, with `research` and `choice` before `contract`. It holds the eight
pilot gates of rule 10 as ten entries, since the research record and the cost estimate each have a
`check` part and a `judgement` part. The choice and the credentials are `owner_only`. Each check
gate names the step a later build adds; this build adds none (brief #805 answer 2). The milestone
shape is `per-phase`, the demo smoke run is the heavy step, every claim is `expected`, and the file
names no vendor, product or tool (brief #805 answer 1). It is shipped verbatim. Reads committed
files only: no network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
REL = "config/playbooks/pilot.toml"
PLAYBOOK = KIT_ROOT / REL
SCRIPTS = KIT_ROOT / "scripts" / "agk"
CHECKS = {
    "research-record",
    "customer-data",
    "time-box",
    "demo-fallback",
    "cost-estimate",
    "pilot-report",
}
JUDGEMENTS = {"research-findings", "tool-choice", "credentials", "cost-estimate-holds"}
OWNER_ONLY = {"tool-choice", "credentials"}
PHASES = ["intake", "research", "choice", "contract", "build", "demo", "report"]
LANES = ["integration", "demo-surface", "evaluation"]


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def gates() -> dict[str, dict]:
    return {g["id"]: g for g in data()["gates"]}


def phases() -> dict[str, dict]:
    return {p["name"]: p for p in data()["phases"]}


def test_the_playbook_passes_the_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "pilot" == PLAYBOOK.stem
    assert data()["format"] == playbook_format.FORMAT


def test_check_playbooks_passes_with_ten_playbooks() -> None:
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert out.returncode == 0, out.stdout
    assert out.stdout == "ok playbooks (10 playbooks)\n"


def test_the_phases_run_in_the_order_of_rule_11() -> None:
    by_name = phases()
    assert list(by_name) == PHASES
    assert [by_name[name]["order"] for name in PHASES] == list(range(1, 8))
    assert by_name["intake"]["after"] == []
    for earlier, later in zip(PHASES, PHASES[1:]):
        assert by_name[later]["after"] == [earlier], later


def test_research_and_choice_come_before_the_contract() -> None:
    by_name = phases()
    contract = by_name["contract"]["order"]
    assert by_name["research"]["order"] < contract
    assert by_name["choice"]["order"] < contract
    assert data()["split"]["brief_order"].index("choice") < (
        data()["split"]["brief_order"].index("contract")
    )


def test_the_build_has_the_three_lanes_of_rule_11() -> None:
    lanes = data()["lanes"]
    assert [lane["name"] for lane in lanes] == LANES
    assert all(lane["kinds"] == [lane["name"]] for lane in lanes)


def test_the_split_follows_the_phases_and_the_lanes_run_together() -> None:
    split = data()["split"]
    assert split["brief_order"] == [
        "intake", "research", "choice", "contract", *LANES, "demo", "report",
    ]
    assert sorted(map(tuple, split["depends_on"])) == sorted(
        [
            ("research", "intake"),
            ("choice", "research"),
            ("contract", "choice"),
            *((lane, "contract") for lane in LANES),
            *(("demo", lane) for lane in LANES),
            ("report", "demo"),
        ]
    )


def test_exactly_the_pilot_gates_of_rule_10() -> None:
    by_id = gates()
    assert set(by_id) == CHECKS | JUDGEMENTS
    assert {gid for gid, g in by_id.items() if g["kind"] == "check"} == CHECKS
    assert {gid for gid, g in by_id.items() if g["kind"] == "judgement"} == JUDGEMENTS
    words = {
        "research-record": (
            "docs/research/", "at least two options", "criteria table", "capability fit",
            "success criteria", "cost", "licence", "data handling", "residency", "maturity",
            "integration effort", "lock-in", "source line", "url", "access date",
            "recommendation", "proposal",
        ),
        "research-findings": ("truth", "findings"),
        "tool-choice": ("choice", "owner or the customer", "never chooses", "terms"),
        "credentials": ("api keys", "accounts", "never handles", "environment the owner sets"),
        "customer-data": ("invented values only", "example.com", "real customer data", "out of"),
        "time-box": ("time box", "intake", "number of days"),
        "demo-fallback": ("demo script", "mock path", "live service is unavailable"),
        "cost-estimate": ("cost estimate", "declared"),
        "cost-estimate-holds": ("cost estimate", "holds"),
        "pilot-report": (
            "docs/runs/pilot-report.md", "what worked", "measured numbers", "cost estimate",
            "risks", "path to production",
        ),
    }
    for gid, expected in words.items():
        text = by_id[gid]["text"].lower()
        for word in expected:
            assert word in text, (gid, word)


def test_every_check_gate_names_its_step_and_no_judgement_gate_does() -> None:
    by_id = gates()
    assert {gid: by_id[gid]["step"] for gid in CHECKS} == {gid: gid for gid in CHECKS}
    assert all("step" not in by_id[gid] for gid in JUDGEMENTS)


def test_owner_only_is_the_choice_and_the_credentials_alone() -> None:
    assert {gid for gid, g in gates().items() if g["owner_only"] is True} == OWNER_ONLY
    assert all(isinstance(g["owner_only"], bool) for g in gates().values())


def test_no_governance_step_is_added_for_the_check_gates() -> None:
    # until a build adds each step, the gate is read as judgement (Q-651-2, brief #805 answer 2)
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    for gid in CHECKS:
        assert gid not in mk, gid
    workflows = KIT_ROOT / ".github" / "workflows"
    for wf in sorted(workflows.glob("*.yml")) if workflows.is_dir() else []:
        text = wf.read_text(encoding="utf-8")
        assert all(gid not in text for gid in CHECKS), wf.name


def test_the_delivery_shape_is_rule_11s_and_nothing_more() -> None:
    playbook = data()
    assert playbook["milestones"]["shape"] == "per-phase"
    assert playbook["heavy_steps"] == ["demo smoke run"]
    testing = playbook["testing"]
    assert testing["profile"] == "balanced"
    assert testing["always_full"] == [] and testing["map"] == []


def test_the_evidence_names_the_gates_records() -> None:
    evidence = data()["evidence"]
    assert len(evidence) == 5
    assert any("research record" in item and "sources" in item for item in evidence)
    assert any("owner's" in item and "choice" in item for item in evidence)
    assert any("demo script" in item and "mock path" in item for item in evidence)
    assert any("demo" in item and "run record" in item for item in evidence)
    assert any("pilot report" in item and "cost estimate" in item for item in evidence)


def test_every_claim_is_expected() -> None:
    claims = data()["claims"]
    assert claims
    assert all(c["basis"] == "expected" and "record" not in c for c in claims)


def test_the_playbook_names_no_vendor_product_or_tool() -> None:
    text = PLAYBOOK.read_text(encoding="utf-8")
    assert "://" not in text and "www." not in text
    assert all(host.endswith("example.com") for host in re.findall(r"@([\w.-]+)", text))
    assert not re.search(r"\b\d+\.\d+(\.\d+)?\b", text)
    lowered = text.lower()
    for word in ("anthropic", "claude", "openai", "gpt", "gemini", "google", "microsoft",
                 "github", "copilot", "cursor", "slack", "python", "typescript", "node",
                 "aws", "azure", "stripe", "salesforce", "langchain", "sdk", "secret"):
        assert not re.search(rf"\b{re.escape(word)}s?\b", lowered), word
    assert "reviewed" not in data(), "rule 2 allows no key outside the format (Q-651-1)"


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
