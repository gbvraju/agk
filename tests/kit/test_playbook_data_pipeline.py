"""Tests of the shipped data-pipeline playbook (SPEC-0048 rule 18, build (g)).

SPEC-0038 rules 1 and 10 as amendment 130 widens them.

REQ-055 AC8. `config/playbooks/data-pipeline.toml` passes the playbook check, and
`check_playbooks.py` passes with nine playbooks. It holds the exact data-pipeline gates of rule 18
(SPEC-0038 rule 10 as amendment 130 widens it): a data contract, `check` (a contract file names each
source and target field with its type, and the testing map names a test glob for it); row-count and
checksum reconciliation, `check` that one is declared for every table or stream the contract names
and `judgement` that a recorded run matches; a dry run on a sample, `judgement`; a rollback, `check`
that the split puts a rollback brief before every cut-over brief and `judgement` that a rehearsal
record exists; and any run against production data, `judgement` and `owner_only`. Each check gate
names the step a later build adds; this build adds none. Every claim is `expected`, and the file
names no vendor, product or tool (brief #690 answer 2). It is shipped verbatim. Reads committed
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
REL = "config/playbooks/data-pipeline.toml"
PLAYBOOK = KIT_ROOT / REL
SCRIPTS = KIT_ROOT / "scripts" / "agk"
CHECKS = {"data-contract", "reconciliation-declared", "rollback-order"}
JUDGEMENTS = {"reconciliation-matches", "dry-run-on-sample", "rollback-rehearsal", "production-run"}


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def gates() -> dict[str, dict]:
    return {g["id"]: g for g in data()["gates"]}


def test_data_pipeline_is_a_work_type() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.WORK_TYPES[-1] == "data-pipeline"
    assert len(playbook_format.WORK_TYPES) == len(set(playbook_format.WORK_TYPES)) == 9


def test_the_playbook_passes_the_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import playbook_format

    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "data-pipeline" == PLAYBOOK.stem
    assert data()["format"] == playbook_format.FORMAT


def test_check_playbooks_passes_with_nine_playbooks() -> None:
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert out.returncode == 0, out.stdout
    assert out.stdout == "ok playbooks (9 playbooks)\n"


def test_exactly_the_data_pipeline_gates_of_rule_18() -> None:
    by_id = gates()
    assert set(by_id) == CHECKS | JUDGEMENTS
    assert {gid for gid, g in by_id.items() if g["kind"] == "check"} == CHECKS
    assert {gid for gid, g in by_id.items() if g["kind"] == "judgement"} == JUDGEMENTS
    words = {
        "data-contract": ("data contract", "each source and target field", "type", "test glob"),
        "reconciliation-declared": ("row-count", "checksum", "every table or stream", "contract"),
        "reconciliation-matches": ("recorded", "run", "matches"),
        "dry-run-on-sample": ("dry run on a sample", "invented or anonymised", "run record"),
        "rollback-order": ("rollback brief before every cut-over brief",),
        "rollback-rehearsal": ("rehearsal record",),
        "production-run": ("production data", "owner"),
    }
    for gid, needed in words.items():
        text = by_id[gid]["text"].lower()
        for word in needed:
            assert word in text, (gid, word)


def test_every_check_gate_names_its_step() -> None:
    by_id = gates()
    assert {gid: by_id[gid]["step"] for gid in CHECKS} == {gid: gid for gid in CHECKS}
    assert all("step" not in by_id[gid] for gid in JUDGEMENTS)


def test_only_a_run_against_production_data_is_owner_only() -> None:
    assert {gid for gid, g in gates().items() if g["owner_only"]} == {"production-run"}


def test_no_governance_step_is_added_for_the_check_gates() -> None:
    # until a build adds each step, the gate is read as judgement (Q-651-2, as brief #757 read it)
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    for gid in CHECKS:
        assert gid not in mk, gid
    workflows = KIT_ROOT / ".github" / "workflows"
    for wf in sorted(workflows.glob("*.yml")) if workflows.is_dir() else []:
        text = wf.read_text(encoding="utf-8")
        assert all(gid not in text for gid in CHECKS), wf.name


def test_the_split_puts_the_rollback_brief_before_the_cut_over_brief() -> None:
    playbook = data()
    assert [p["name"] for p in playbook["phases"]] == ["build", "rollback", "cut-over"]
    order = playbook["split"]["brief_order"]
    assert order == ["build", "rollback", "cut-over"]
    assert order.index("rollback") < order.index("cut-over")
    assert ["cut-over", "rollback"] in playbook["split"]["depends_on"]


def test_nothing_beyond_rule_18_is_invented() -> None:
    playbook = data()
    assert playbook["lanes"] == []
    assert playbook["heavy_steps"] == []
    assert playbook["milestones"]["shape"] == "per-brief"
    testing = playbook["testing"]
    assert testing["profile"] == "balanced"
    assert testing["always_full"] == [] and testing["map"] == []


def test_the_evidence_names_the_gates_records() -> None:
    evidence = data()["evidence"]
    assert len(evidence) == 5
    assert any("contract" in item and "test glob" in item for item in evidence)
    assert any("reconciliation" in item for item in evidence)
    assert any("dry run" in item for item in evidence)
    assert any("rehearsal" in item for item in evidence)
    assert any("production data" in item and "owner" in item for item in evidence)


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
    for word in ("anthropic", "claude", "openai", "gpt", "google", "microsoft", "amazon", "aws",
                 "azure", "github", "python", "sql", "spark", "kafka", "airflow", "dbt",
                 "snowflake", "postgres", "oracle", "sdk", "secret"):
        assert not re.search(rf"\b{re.escape(word)}s?\b", lowered), word
    assert "reviewed" not in data(), "no amendment 129 key (SPEC-0048 rule 25)"


def test_the_playbook_is_shipped_verbatim() -> None:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert REL in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
