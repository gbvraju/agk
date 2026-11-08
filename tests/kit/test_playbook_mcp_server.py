"""Tests of the shipped mcp-server playbook (SPEC-0038 rules 1, 10 and 12 build (k)).

REQ-045 AC6. `config/playbooks/mcp-server.toml` passes the playbook check, and
`check_playbooks.py` passes with eight playbooks. It holds exactly the mcp-server gates of rule 10:
tool schema contract tests, `check` (the testing map names a test glob for every schema file);
permission scopes, `check` (every tool declares its scopes and none is a wildcard); and a
prompt-injection test set, `check` (the set exists and the map names its tests). Each check gate
names the step a later build adds; this build adds none (brief #757 answer 2). Nothing beyond the
gates is invented, every speed claim is `expected`, and the file names no vendor, product or tool
(brief #757 answer 1). It is shipped verbatim. Reads committed files only: no network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
REL = "config/playbooks/mcp-server.toml"
PLAYBOOK = KIT_ROOT / REL
SCRIPTS = KIT_ROOT / "scripts" / "agk"
GATES = {"tool-schema-contract-tests", "permission-scopes", "prompt-injection-set"}


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def gates() -> dict[str, dict]:
    return {g["id"]: g for g in data()["gates"]}


def test_the_playbook_passes_the_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "mcp-server" == PLAYBOOK.stem
    assert data()["format"] == playbook_format.FORMAT


def test_check_playbooks_passes_with_eight_playbooks() -> None:
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert out.returncode == 0, out.stdout
    assert out.stdout == "ok playbooks (8 playbooks)\n"


def test_exactly_the_mcp_server_gates_of_rule_10() -> None:
    by_id = gates()
    assert set(by_id) == GATES
    assert all(g["kind"] == "check" for g in by_id.values())
    schema = by_id["tool-schema-contract-tests"]["text"].lower()
    for word in ("tool schema", "contract tests", "testing map", "test glob", "every schema file"):
        assert word in schema, word
    scopes = by_id["permission-scopes"]["text"].lower()
    for word in ("permission scopes", "every tool declares its scopes", "wildcard"):
        assert word in scopes, word
    injection = by_id["prompt-injection-set"]["text"].lower()
    for word in ("prompt-injection test set", "exists", "map names its tests"):
        assert word in injection, word


def test_every_check_gate_names_its_step() -> None:
    assert {gid: g["step"] for gid, g in gates().items()} == {gid: gid for gid in GATES}


def test_no_gate_is_owner_only() -> None:
    # rule 10 marks no mcp-server gate as the owner's action
    assert all(g["owner_only"] is False for g in gates().values())


def test_no_governance_step_is_added_for_the_check_gates() -> None:
    # until a build adds each step, the gate is read as judgement (Q-651-2, brief #757 answer 2)
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    for gid in GATES:
        assert gid not in mk, gid
    workflows = KIT_ROOT / ".github" / "workflows"
    for wf in sorted(workflows.glob("*.yml")) if workflows.is_dir() else []:
        text = wf.read_text(encoding="utf-8")
        assert all(gid not in text for gid in GATES), wf.name


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
    assert len(evidence) == 3
    assert any("schema" in item and "contract test" in item for item in evidence)
    assert any("scopes" in item for item in evidence)
    assert any("prompt-injection" in item for item in evidence)


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
                 "json schema", "openapi", "sdk", "secret"):
        assert not re.search(rf"\b{re.escape(word)}s?\b", lowered), word
    assert "reviewed" not in data(), "rule 2 allows no key outside the format (Q-651-1)"


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
