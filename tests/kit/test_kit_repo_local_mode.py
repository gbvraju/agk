"""Brief #1471 (REQ-039, ADR-0626): the kit's own repository runs in local mode, gates recorded.

The kit's agk.toml sets `execution = "local"`; the doctor's `local-mode-switch` line warns while
the switch-over is unfinished (a workflow still active, no open record issue, the ruleset still
requiring checks from Actions), naming the setting, never a value; a cloud session without
gitleaks is told the one setup line the owner adds, never running it; the local-mode guide gains
the owner's six steps. Saved GitHub answers only (example names), no network, no model. REQ-039
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import doctor
import merge_cleared
import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
GUIDE = KIT_ROOT / "docs" / "guides" / "local-mode.md"
SECTION = "## A kit's own repository goes private"
LOCAL = {"execution": "local", "required_checks": ["proof", "governance"]}
RULESET = {
    "id": 7,
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "rules": [{"type": "deletion"}],
}
CHECKS_RULE = {
    "type": "required_status_checks",
    "parameters": {"required_status_checks": [{"context": "proof"}, {"context": "governance"}]},
}
RECORD = {"number": 41, "title": "Local mode since 2026-11-20"}


def answers(tmp_path: Path, **over) -> doctor.Reads:
    """Recorded answers of a switched-over repository, with OVER replacing any of them."""
    api = tmp_path / "api"
    api.mkdir()
    data = {
        "repo": {"default_branch": "main", "permissions": {"admin": True}},
        "workflows": {"workflows": [{"name": "governance", "state": "disabled_manually"}]},
        "issues-open": [RECORD],
        "rulesets": [{"id": 7, "target": "branch"}],
        "ruleset-7": RULESET,
        **over,
    }
    for name, value in data.items():
        (api / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
    return doctor.Reads("example-owner/example-repo", api)


# --- answer 1: the setting ----------------------------------------------------------------------


def test_the_kits_own_repository_sets_local_execution():
    """REQ-039: brief #1471 answer 1 (execution local; required_checks still names both)."""
    text = (KIT_ROOT / "agk.toml").read_text(encoding="utf-8")
    data = tomllib.loads(text)
    assert data["execution"] == "local"
    assert data["required_checks"] == ["proof", "governance"]
    before = text.split('execution = "local"')[0].splitlines()[-1]
    assert before.startswith("#") and "ADR-0626" in before


# --- answers 6 and 8: the doctor's line ---------------------------------------------------------


def test_not_local_is_not_applicable_and_reads_nothing(tmp_path):
    """REQ-039: brief #1471 answer 7 (hosted and hybrid projects unchanged)."""
    reads = answers(tmp_path)
    for config in ({}, {"execution": "hosted"}, {"execution": "hybrid"}):
        res = doctor.local_switch_result(reads, config)
        assert res.status == "ok" and "not applicable" in res.message
    assert reads.seen == {}


def test_a_finished_switch_over_is_ok(tmp_path):
    """REQ-039: brief #1471 answer 6."""
    assert doctor.local_switch_result(answers(tmp_path), LOCAL).status == "ok"


@pytest.mark.parametrize(
    ("over", "words"),
    [
        (
            {"workflows": {"workflows": [{"name": "proof-x", "state": "active"}]}},
            "1 workflow still active",
        ),
        ({"issues-open": [{"number": 3, "title": "Another title"}]}, "no open record issue"),
        (
            {"issues-open": [{**RECORD, "pull_request": {}}]},
            "no open record issue",
        ),
        (
            {"ruleset-7": {**RULESET, "rules": [*RULESET["rules"], CHECKS_RULE]}},
            "the ruleset still requires 2 checks of required_checks",
        ),
    ],
    ids=["workflow enabled", "no record issue", "a pull request is no record", "ruleset checks"],
)
def test_each_unfinished_step_warns_naming_the_setting(tmp_path, over, words):
    """REQ-039: brief #1471 answer 8 (a workflow still enabled; no record issue; the ruleset)."""
    res = doctor.local_switch_result(answers(tmp_path, **over), LOCAL)
    assert res.status == "fail"
    assert words in res.message
    for value in ("proof-x", "Another title", "Local mode since", "governance", "example-owner"):
        assert value not in res.message
    assert doctor.CHECKS["local-mode-switch"][0] == "warn"
    assert "setting: execution" in doctor.CHECKS["local-mode-switch"][2]


def test_a_read_that_fails_is_cannot_check_never_ok(tmp_path):
    """REQ-039: brief #1471 answer 6 (GET calls only; an unread answer is never ok)."""
    reads = answers(tmp_path)
    (reads.api_dir / "workflows.json").unlink()
    res = doctor.local_switch_result(reads, LOCAL)
    assert res.status == "cannot-check" and res.reason == "bad-response"


def test_the_line_is_in_the_report(tmp_path):
    """REQ-039: brief #1471 answer 6 (one check of the doctor's report)."""
    assert "local-mode-switch" in doctor.CHECKS
    fix = doctor.CHECKS["local-mode-switch"][3]
    assert "local_mode.py enter --write" in fix and "docs/guides/local-mode.md" in fix


# --- answer 4: gitleaks in a cloud session ------------------------------------------------------


def test_a_cloud_session_without_gitleaks_is_told_the_setup_line(monkeypatch):
    """REQ-039: brief #1471 answers 4 and 8 (named with the pin; never downloaded here)."""
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)

    def refuse(*_args, **_kwargs):
        raise AssertionError("the doctor runs nothing for a missing gitleaks")

    monkeypatch.setattr(doctor.subprocess, "run", refuse)
    line = doctor.secret_scan_line(in_wsl=False, in_cloud=True)
    assert "(tool: gitleaks)" in line and doctor.GITLEAKS_PIN in line
    assert doctor.GITLEAKS_SETUP in line and "(verify" in line
    assert doctor.GITLEAKS_SHA256 in doctor.GITLEAKS_SETUP
    assert "sha256sum --check" in doctor.GITLEAKS_SETUP
    outside = doctor.secret_scan_line(in_wsl=False, in_cloud=False)
    assert doctor.GITLEAKS_SETUP not in outside and "(tool: gitleaks)" in outside


def test_the_setup_line_names_the_workflows_pin_and_digest():
    """REQ-039: brief #1471 answer 4 (the same version and digest the governance workflow pins)."""
    workflow = (KIT_ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    assert f"GITLEAKS_SHA256: {doctor.GITLEAKS_SHA256}" in workflow
    assert re.search(rf"GITLEAKS_VERSION: \"?{re.escape(doctor.GITLEAKS_PIN)}\"?", workflow)


def test_the_cloud_is_read_from_the_runtime_variable(monkeypatch):
    """REQ-039: brief #1471 answer 4 (`CLAUDE_CODE_REMOTE`, the variable common.py reads)."""
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    assert doctor.GITLEAKS_SETUP in doctor.secret_scan_line(in_wsl=False)
    monkeypatch.delenv("CLAUDE_CODE_REMOTE")
    assert doctor.GITLEAKS_SETUP not in doctor.secret_scan_line(in_wsl=False)


# --- answer 5: the guide ------------------------------------------------------------------------


def test_the_guide_has_the_owners_six_steps_in_order():
    """REQ-039: brief #1471 answer 5."""
    text = GUIDE.read_text(encoding="utf-8")
    assert SECTION in text
    part = text.split(SECTION, 1)[1].split("\n## ", 1)[0]
    steps = re.findall(r"^(\d)\. ", part, re.M)
    assert steps == ["1", "2", "3", "4", "5", "6"]
    order = [
        "#1447",
        "local_mode.py enter --write",
        "required checks",
        "minutes.py --line",
        "read access",
        "local_mode.py leave",
    ]
    places = [part.find(x) for x in order]
    assert -1 not in places and places == sorted(places)
    assert "never run by a session" in part and "doctor.py" in part


# --- answer 2 and edge case 8: the merge still needs both evidence lines ------------------------


def test_a_verdict_without_evidence_check_agrees_is_held():
    """REQ-039: brief #1471 answer 8 (the merge refuses, as today)."""
    sha = "a" * 40
    verdict = {"body": f"Verdict: clear\nLocal evidence: {sha[:12]}\n"}
    with pytest.raises(merge_cleared.Held, match="no local evidence"):
        merge_cleared.local_evidence(verdict, [], sha, [])
    agrees = {"body": verdict["body"] + f"Evidence check: agrees, head {sha[:12]}\n"}
    merge_cleared.local_evidence(agrees, [], sha, [])


def test_the_doctor_only_reads():
    """REQ-039: brief #1471 answer 6 (GET only; no workflow, ruleset or visibility is changed)."""
    source = (KIT_ROOT / "scripts" / "agk" / "doctor.py").read_text(encoding="utf-8")
    assert '"--method", "GET"' in source
    for verb in ('"PUT"', '"PATCH"', '"POST"', '"DELETE"', "--write"):
        assert verb not in source.split("def local_switch_result", 1)[1].split("\ndef ", 1)[0]
