"""Tests of `run_gates.py` and its step registry (SPEC-0072 rule 3; REQ-079 AC2; brief #1586).

Every check gate of every shipped playbook, composed with `default.toml`, has a step module under
`scripts/agk/gates/` and runs on a sample project with the network stubbed off; a stub playbook
naming a step with no module fails naming the gate id; a failure names the gate id, the rule and
the path class and never a value; the 28 restated gates are judgement with a reason; and no test
changes `required_checks` or a workflow. Fixtures in `tmp_path` only: invented data, no network.
"""

from __future__ import annotations

import shutil
import socket
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import run_gates  # noqa: E402

PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
WORK_TYPES = sorted(p.stem for p in PLAYBOOKS.glob("*.toml") if p.stem != "default")
IMPLEMENTED = {"cut-over-order", "rollback-order", "committed-secrets", "environment-settings"}
IMPLEMENTED |= {"contract-tests", "mock-parity"}  # brief #1597


def _project(tmp_path: Path, work_type: str | None) -> Path:
    shutil.copytree(PLAYBOOKS, tmp_path / "config" / "playbooks")
    text = 'mode = "init"\n'
    if work_type:
        text += f'\n[delivery]\nwork_type = "{work_type}"\n'
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    # brief #1597 (ADR-0677): a contract with no operation, so the contract steps run and pass
    (tmp_path / "contracts").mkdir()
    (tmp_path / "contracts" / "openapi.json").write_text('{"openapi": "3.1.0", "paths": {}}')
    return tmp_path


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a gate step opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _checks(name: str) -> dict[str, dict]:
    data = tomllib.loads((PLAYBOOKS / f"{name}.toml").read_text(encoding="utf-8"))
    return {g["id"]: g for g in data["gates"] if g["kind"] == "check"}


@pytest.mark.parametrize("work_type", WORK_TYPES)
def test_every_check_gate_of_a_playbook_runs_offline(
    work_type: str, tmp_path: Path, no_network: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC2."""
    root = _project(tmp_path, work_type)
    assert run_gates.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    for gid in {**_checks("default"), **_checks(work_type)}:
        assert f"ok {gid}\n" in out, gid
    assert out.rstrip().splitlines()[-1].startswith("ok gates (")


def test_the_registry_has_a_module_for_every_shipped_check_step() -> None:
    steps = {g["step"] for name in ["default", *WORK_TYPES] for g in _checks(name).values()}
    assert steps == IMPLEMENTED
    assert all(run_gates.step_module(step) is not None for step in steps)


def test_the_restated_gates_are_judgement_with_a_reason_and_no_step() -> None:
    """REQ-079 AC2."""
    restated = 0
    for path in PLAYBOOKS.glob("*.toml"):
        for gate in tomllib.loads(path.read_text(encoding="utf-8"))["gates"]:
            reason = gate.get("reason", "")  # brief #1597 restates one with ADR-0677
            if gate["kind"] == "judgement" and ("(ADR-0666)" in reason or "(ADR-0677)" in reason):
                restated += 1
                assert len(gate["reason"]) >= 20, gate["id"]
            if gate["kind"] == "judgement":
                assert "step" not in gate, gate["id"]
    assert restated == 21  # brief #1593 made 4 checks, brief #1597 three (ADR-0677)


def test_the_kit_without_a_work_type_runs_default_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC2."""
    root = _project(tmp_path, None)
    assert run_gates.main(["--root", str(root)]) == 0
    out = "ok secrets\nok environment-settings\nok gates (2 check gates)\n"
    assert capsys.readouterr().out == out


def test_a_step_with_no_module_is_refused_naming_the_gate_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC2."""
    root = _project(tmp_path, "web-app")
    path = root / "config" / "playbooks" / "web-app.toml"
    stub = '\n[[gates]]\nid = "invented-gate"\nkind = "check"\ntext = "Invented."\n'
    path.write_text(
        path.read_text(encoding="utf-8") + stub + 'step = "no-such-step"\nowner_only = false\n',
        encoding="utf-8",
    )
    assert run_gates.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "FAIL gates: invented-gate: SPEC-0072 rule 3: the step has no implementation" in out
    assert "no-such-step" not in out


@pytest.mark.parametrize(
    ("work_type", "gate", "pair"),
    [
        ("cloud-migration", "cut-over-order", '["cut-over", "wave-plan"]'),
        ("data-pipeline", "rollback-order", '["cut-over", "rollback"]'),
    ],
)
def test_a_split_that_drops_the_order_fails_naming_gate_rule_and_path_class(
    work_type: str, gate: str, pair: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC2."""
    root = _project(tmp_path, work_type)
    path = root / "config" / "playbooks" / f"{work_type}.toml"
    text = path.read_text(encoding="utf-8")
    assert pair in text
    path.write_text(text.replace(pair, '["cut-over", "build"]'), encoding="utf-8")
    assert run_gates.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert f"FAIL gates: {gate}: " in out
    assert "(path class: config/playbooks/)" in out
    assert "wave-plan" not in out and '"build"' not in out


def test_the_playbook_check_runs_the_gates_and_nothing_else_changes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC2: the runner runs inside the step `check_playbooks` (Q-1586-3)."""
    import check_playbooks

    root = _project(tmp_path, "cloud-migration")
    assert check_playbooks.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    count = len(WORK_TYPES) + 1
    gates = "ok secrets\nok environment-settings\nok cut-over-order\nok gates (3 check gates)\n"
    assert f"ok playbooks ({count} playbooks)\n{gates}" in out
    path = root / "config" / "playbooks" / "cloud-migration.toml"
    text = path.read_text(encoding="utf-8")
    text = text.replace('["cut-over", "wave-plan"]', '["cut-over", "x"]')
    path.write_text(text, encoding="utf-8")
    assert check_playbooks.main(["--root", str(root)]) == 1
    for name in ("agk.mk", "Makefile"):
        assert "run_gates" not in (KIT_ROOT / name).read_text(encoding="utf-8"), name
    for flow in (KIT_ROOT / ".github" / "workflows").glob("*.yml"):
        assert "run_gates" not in flow.read_text(encoding="utf-8"), flow.name
    config = tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))
    assert config.get("required_checks", ["proof", "governance"]) == ["proof", "governance"]
