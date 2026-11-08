"""Tests of the shipped voice-agent playbook (SPEC-0038 rules 1, 10 and 12 build (m)).

REQ-045 AC6. `config/playbooks/voice-agent.toml` passes the playbook check, and
`check_playbooks.py` passes with ten playbooks. It holds exactly the voice-agent gates of rule
10: a latency budget, `check` that it is declared and `judgement` that a recorded run meets it; an
ASR/TTS evaluation set, `check` (the set exists with a version line); and barge-in and fallback
scenarios, `check` (each scenario is listed and the map names its tests). Each check gate names
the step a later build adds; this build adds none (brief #786 answer 2). Nothing beyond the gates
is invented, every speed claim is `expected`, and the file names no vendor, product or tool (brief
#786 answer 1). It is shipped verbatim. Reads committed files only: no network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
REL = "config/playbooks/voice-agent.toml"
PLAYBOOK = KIT_ROOT / REL
SCRIPTS = KIT_ROOT / "scripts" / "agk"
CHECKS = {"latency-budget", "asr-tts-evaluation-set", "barge-in-fallback-scenarios"}
JUDGEMENTS = {"latency-budget-met"}


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def gates() -> dict[str, dict]:
    return {g["id"]: g for g in data()["gates"]}


def test_the_playbook_passes_the_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "voice-agent" == PLAYBOOK.stem
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


def test_exactly_the_voice_agent_gates_of_rule_10() -> None:
    by_id = gates()
    assert set(by_id) == CHECKS | JUDGEMENTS
    assert {gid for gid, g in by_id.items() if g["kind"] == "check"} == CHECKS
    assert {gid for gid, g in by_id.items() if g["kind"] == "judgement"} == JUDGEMENTS
    budget = by_id["latency-budget"]["text"].lower()
    for word in ("latency budget", "declared"):
        assert word in budget, word
    met = by_id["latency-budget-met"]["text"].lower()
    for word in ("recorded run", "meets", "latency budget"):
        assert word in met, word
    evaluation = by_id["asr-tts-evaluation-set"]["text"].lower()
    for word in ("asr/tts evaluation set", "exists", "version line"):
        assert word in evaluation, word
    scenarios = by_id["barge-in-fallback-scenarios"]["text"].lower()
    for word in ("barge-in", "fallback", "scenario", "listed", "map names", "tests"):
        assert word in scenarios, word


def test_every_check_gate_names_its_step_and_no_judgement_gate_does() -> None:
    by_id = gates()
    assert {gid: by_id[gid]["step"] for gid in CHECKS} == {gid: gid for gid in CHECKS}
    assert all("step" not in by_id[gid] for gid in JUDGEMENTS)


def test_no_gate_is_owner_only() -> None:
    # rule 10 marks no voice-agent gate as the owner's action
    assert all(g["owner_only"] is False for g in gates().values())


def test_no_governance_step_is_added_for_the_check_gates() -> None:
    # until a build adds each step, the gate is read as judgement (Q-651-2, brief #786 answer 2)
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
    assert any("declared" in item and "latency budget" in item for item in evidence)
    assert any("recorded run" in item and "latency budget" in item for item in evidence)
    assert any("evaluation set" in item and "version line" in item for item in evidence)
    assert any("barge-in" in i and "fallback" in i and "test glob" in i for i in evidence)


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
                 "whisper", "deepgram", "elevenlabs", "twilio", "webrtc", "livekit", "polly",
                 "alexa", "siri", "sdk", "secret"):
        assert not re.search(rf"\b{re.escape(word)}s?\b", lowered), word
    assert "reviewed" not in data(), "rule 2 allows no key outside the format (Q-651-1)"


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
