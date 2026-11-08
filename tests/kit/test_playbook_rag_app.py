"""Tests of the shipped rag-app playbook (SPEC-0038 rules 1, 10 and 11; REQ-045 AC5).

`config/playbooks/rag-app.toml` passes the playbook check; it orders `corpus` (with the privacy
review), `evaluation-set`, `retrieval`, `answers` and `joins`, with the evaluation set before any
retrieval or answer brief; the evaluation run is its heavy step; it holds the four rag-app gates of
rule 10 (the versioned evaluation set and the version pinning `check`, the quality bars `check` that
they are declared and `judgement` that the recorded run meets them, the privacy review of the corpus
`judgement`); and every speed claim is `expected`, since no run has measured it. It names the shape
of the work and its gates, never a tool, a vendor, a model or a URL (brief #662 answer 1). It is
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
REL = "config/playbooks/rag-app.toml"
PLAYBOOK = KIT_ROOT / REL
WEB_APP = KIT_ROOT / "config" / "playbooks" / "web-app.toml"
SCRIPTS = KIT_ROOT / "scripts" / "agk"


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def phases() -> dict[str, dict]:
    return {p["name"]: p for p in data()["phases"]}


def test_the_playbook_passes_the_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "rag-app" == PLAYBOOK.stem
    assert data()["format"] == playbook_format.FORMAT


def test_check_playbooks_passes_with_three_playbooks() -> None:
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert out.returncode == 0, out.stdout
    assert WEB_APP.is_file(), "the web-app playbook of build (c) is on the default branch"
    assert out.stdout == "ok playbooks (3 playbooks)\n"


def test_phases_corpus_evaluation_set_retrieval_answers_joins() -> None:
    by_name = phases()
    assert list(by_name) == ["corpus", "evaluation-set", "retrieval", "answers", "joins"]
    assert by_name["corpus"]["after"] == []
    assert by_name["evaluation-set"]["after"] == ["corpus"]
    assert by_name["retrieval"]["after"] == ["evaluation-set"]
    assert by_name["answers"]["after"] == ["retrieval"]
    assert by_name["joins"]["after"] == ["answers"]
    order = {name: p["order"] for name, p in by_name.items()}
    assert (
        order["corpus"]
        < order["evaluation-set"]
        < order["retrieval"]
        < order["answers"]
        < order["joins"]
    )


def test_the_evaluation_set_comes_before_any_retrieval_or_answer_brief() -> None:
    playbook = data()
    split = playbook["split"]
    assert split["brief_order"] == ["corpus", "evaluation-set", "retrieval", "answer", "join"]
    pairs = {tuple(p) for p in split["depends_on"]}
    assert ("retrieval", "evaluation-set") in pairs
    assert ("answer", "evaluation-set") in pairs
    assert pairs == {
        ("evaluation-set", "corpus"),
        ("retrieval", "evaluation-set"),
        ("answer", "evaluation-set"),
        ("answer", "retrieval"),
        ("join", "retrieval"),
        ("join", "answer"),
    }
    # rule 11 lists retrieval before answers; no lane runs the two kinds together (Q-662-2)
    lanes = {lane["name"]: lane["kinds"] for lane in playbook["lanes"]}
    assert lanes == {"retrieval": ["retrieval"], "answers": ["answer"]}
    assert all(kind in split["brief_order"] for kinds in lanes.values() for kind in kinds)


def test_testing_profile_map_and_evaluation_set_folder() -> None:
    testing = data()["testing"]
    assert testing["profile"] == "balanced"
    assert testing["always_full"] == ["evaluation/**"], "the evaluation set is always run in full"
    codes = [entry["code"] for entry in testing["map"]]
    assert len(codes) >= 2 and len(set(codes)) == len(codes), "a per-module map"
    assert all(entry["tests"] for entry in testing["map"])
    assert any(code.startswith("evaluation/") for code in codes)


def test_heavy_step_and_milestone_shape() -> None:
    playbook = data()
    assert playbook["heavy_steps"] == ["evaluation run"]
    # rule 11 gives rag-app no milestone shape: per-brief is one pull request per brief, as today
    assert playbook["milestones"]["shape"] == "per-brief"
    assert playbook["milestones"]["batch_by"]


def test_the_four_rag_app_gates_of_rule_10() -> None:
    gates = {g["id"]: g for g in data()["gates"]}
    assert set(gates) == {
        "evaluation-set",
        "quality-bars",
        "quality-bars-met",
        "version-pinning",
        "privacy-review",
    }
    # a versioned evaluation set: check (a version line and invented data only)
    assert gates["evaluation-set"]["kind"] == "check"
    assert "version" in gates["evaluation-set"]["text"]
    assert "invented" in gates["evaluation-set"]["text"]
    # a quality bar for retrieval and for answers: check that both are declared as numbers,
    # judgement that the recorded run meets them
    assert gates["quality-bars"]["kind"] == "check"
    assert "retrieval" in gates["quality-bars"]["text"]
    assert "answers" in gates["quality-bars"]["text"]
    assert "numbers" in gates["quality-bars"]["text"]
    assert gates["quality-bars-met"]["kind"] == "judgement"
    assert "run" in gates["quality-bars-met"]["text"]
    # prompt and model version pinning: check (exact versions, no floating alias)
    assert gates["version-pinning"]["kind"] == "check"
    assert "exact" in gates["version-pinning"]["text"]
    assert "alias" in gates["version-pinning"]["text"]
    # a privacy review of the corpus: judgement
    assert gates["privacy-review"]["kind"] == "judgement"
    assert "corpus" in gates["privacy-review"]["text"]
    assert all(g["step"] for g in gates.values() if g["kind"] == "check")
    assert all("step" not in g for g in gates.values() if g["kind"] == "judgement")
    assert all(g["owner_only"] is False for g in gates.values())
    assert data()["evidence"], "the items a verdict cites"


def test_the_corpus_phase_carries_the_privacy_review() -> None:
    # rule 11: `corpus` (with the privacy review); the review is the judgement gate of the corpus
    # phase and an evidence item, so a verdict on a corpus brief cites it
    playbook = data()
    assert any("privacy review" in item for item in playbook["evidence"])
    gate = {g["id"]: g for g in playbook["gates"]}["privacy-review"]
    assert "corpus" in gate["text"] and gate["kind"] == "judgement"
    assert "privacy review" in playbook["title"]


def test_every_claim_is_expected() -> None:
    claims = data()["claims"]
    assert claims
    assert all(c["basis"] == "expected" and "record" not in c for c in claims)


def test_the_playbook_holds_the_shape_never_a_tool_vendor_or_model() -> None:
    text = PLAYBOOK.read_text(encoding="utf-8")
    assert "://" not in text and "www." not in text
    assert all(host.endswith("example.com") for host in re.findall(r"@([\w.-]+)", text))
    # a version pin names exact versions, but the playbook itself names no version of anything
    assert not re.search(r"\b\d+\.\d+(\.\d+)?\b", text.replace("format = 1", ""))
    assert "reviewed" not in data(), "rule 2 allows no key outside the format (Q-651-1)"


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert "config/playbooks/web-app.toml" in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
