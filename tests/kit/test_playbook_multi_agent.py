"""Tests of the shipped multi-agent playbook (SPEC-0038 rules 1, 10 and 12 build (l)).

REQ-045 AC6. `config/playbooks/multi-agent.toml` passes the playbook check, and
`check_playbooks.py` passes with seven playbooks. It holds exactly the multi-agent gates of rule
10: role and handoff contracts, `check` (a contract file for each role and handoff, with tests
mapped); trace-based evaluation, `judgement`; and cost and latency budgets, `check` that they are
declared as numbers and `judgement` that a recorded run meets them. Each check gate names the step
a later build adds; this build adds none (brief #780 answer 2). Nothing beyond the gates is
invented, every speed claim is `expected`, and the file names no vendor, product or tool (brief
#780 answer 1). It is shipped verbatim. Reads committed files only: no network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
REL = "config/playbooks/multi-agent.toml"
PLAYBOOK = KIT_ROOT / REL
SCRIPTS = KIT_ROOT / "scripts" / "agk"
CHECKS = {"role-handoff-contracts", "cost-latency-budgets"}
JUDGEMENTS = {"trace-based-evaluation", "cost-latency-budgets-met"}


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def gates() -> dict[str, dict]:
    return {g["id"]: g for g in data()["gates"]}


def test_the_playbook_passes_the_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "multi-agent" == PLAYBOOK.stem
    assert data()["format"] == playbook_format.FORMAT


def test_check_playbooks_passes_with_seven_playbooks() -> None:
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert out.returncode == 0, out.stdout
    assert out.stdout == "ok playbooks (7 playbooks)\n"


def test_exactly_the_multi_agent_gates_of_rule_10() -> None:
    by_id = gates()
    assert set(by_id) == CHECKS | JUDGEMENTS
    assert {gid for gid, g in by_id.items() if g["kind"] == "check"} == CHECKS
    assert {gid for gid, g in by_id.items() if g["kind"] == "judgement"} == JUDGEMENTS
    contracts = by_id["role-handoff-contracts"]["text"].lower()
    for word in ("role and handoff contracts", "contract file", "each role", "handoff", "mapped"):
        assert word in contracts, word
    assert "trace-based evaluation" in by_id["trace-based-evaluation"]["text"].lower()
    budgets = by_id["cost-latency-budgets"]["text"].lower()
    for word in ("cost", "latency", "budgets", "declared as numbers"):
        assert word in budgets, word
    met = by_id["cost-latency-budgets-met"]["text"].lower()
    for word in ("recorded run", "meets", "cost", "latency"):
        assert word in met, word


def test_every_check_gate_names_its_step_and_no_judgement_gate_does() -> None:
    by_id = gates()
    assert {gid: by_id[gid]["step"] for gid in CHECKS} == {gid: gid for gid in CHECKS}
    assert all("step" not in by_id[gid] for gid in JUDGEMENTS)


def test_no_gate_is_owner_only() -> None:
    # rule 10 marks no multi-agent gate as the owner's action
    assert all(g["owner_only"] is False for g in gates().values())


def test_no_governance_step_is_added_for_the_check_gates() -> None:
    # until a build adds each step, the gate is read as judgement (Q-651-2, brief #780 answer 2)
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    for gid in CHECKS:
        assert gid not in mk, gid
    workflows = KIT_ROOT / ".github" / "workflows"
    for wf in sorted(workflows.glob("*.yml")) if workflows.is_dir() else []:
        text = wf.read_text(encoding="utf-8")
        assert all(gid not in text for gid in CHECKS), wf.name


def test_nothing_beyond_rule_10_is_invented() -> None:
    # rule 10 gives the gates only: no order, lane, test map, heavy step or batching is invented
    playbook = data()
    assert [p["name"] for p in playbook["phases"]] == ["build"]
    assert playbook["split"] == {"brief_order": ["build"], "depends_on": []}
    assert playbook["lanes"] == []
    assert playbook["heavy_steps"] == []
    assert playbook["milestones"]["shape"] == "per-brief"
    testing = playbook["testing"]
    assert testing["profile"] == "balanced"
    assert testing["always_full"] == [] and testing["map"] == []


def test_the_evidence_names_the_gates_records() -> None:
    evidence = data()["evidence"]
    assert len(evidence) == 4
    assert any("contract file" in item and "test glob" in item for item in evidence)
    assert any("trace" in item for item in evidence)
    assert any("declared" in item and "budgets" in item for item in evidence)
    assert any("recorded run" in item and "budgets" in item for item in evidence)


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
                 "langchain", "langgraph", "autogen", "crewai", "opentelemetry", "sdk", "secret"):
        assert not re.search(rf"\b{re.escape(word)}s?\b", lowered), word
    assert "reviewed" not in data(), "rule 2 allows no key outside the format (Q-651-1)"


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
