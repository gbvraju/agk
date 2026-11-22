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
IMPLEMENTED.add("tests-floor")  # brief #1590 (ADR-0670)
IMPLEMENTED.add("injection-set")  # brief #1712 (ADR-0717)
# a sample with no architecture record has no merged foundation (brief #1590, Q-1590-3)
NOT_FOUNDED = "not run tests-first: no foundation yet\n"
FOUNDATION_STEPS = ("tests-first", "prompt-injection-set")  # brief #1712 (ADR-0717)


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
        unfounded = f"not run {gid}: no foundation yet\n"  # tests-first; brief #1712's set too
        assert f"ok {gid}\n" in out or (gid in FOUNDATION_STEPS and unfounded in out), gid
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
    # brief #1593 made 4 checks, brief #1597 three (ADR-0677), brief #1712 one (ADR-0717)
    assert restated == 20


def test_the_kit_without_a_work_type_runs_default_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC2."""
    root = _project(tmp_path, None)
    assert run_gates.main(["--root", str(root)]) == 0
    out = "not run tests-first: no work type\nok secrets\nok environment-settings\n"
    out += "ok gates (3 check gates; not run: tests-first)\n"  # briefs #1593 and #1590
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
    gates = NOT_FOUNDED + "ok secrets\nok environment-settings\nok cut-over-order\n"
    gates += "ok gates (4 check gates; not run: tests-first)\n"  # brief #1590
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


# brief #1685 (ADR-0702): a chosen runtime that no standards pack serves is told so, never silent.
NO_PACK = "not run standards: no pack for node\n"


def _record(root: Path, runtime: str) -> None:
    (root / "docs" / "adr").mkdir(parents=True, exist_ok=True)
    (root / "docs/adr/0003-stack-options.md").write_text(
        "# ADR-0003: Stack options\n\n- Status: Accepted\n\n1. **Options**:\n"
        f"   - Option A — Parts: {runtime} 22.11.0 MIT. Why: invented.\n3. **Chosen**: Option A\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("work_type", WORK_TYPES)
def test_a_node_record_prints_no_pack_and_lists_standards(
    work_type: str, tmp_path: Path, no_network: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1685 answers 1 and 3 (every work type; the exit code is unchanged)."""
    root = _project(tmp_path, work_type)
    _record(root, "node")
    assert run_gates.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert NO_PACK in out and "ok standards" not in out
    last = out.rstrip().splitlines()[-1]
    assert last.startswith("ok gates (") and "standards" in last.split("not run:", 1)[1]


@pytest.mark.parametrize("runtime", ["python", None])
def test_a_python_record_or_none_prints_nothing_new(
    runtime: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-079: brief #1685 answer 3 (a Python stack, or no stack chosen: unchanged)."""
    root = _project(tmp_path, "web-app")
    if runtime:
        _record(root, runtime)
    monkeypatch.setattr(run_gates, "pack_results", lambda *_a, **_k: [])
    assert run_gates.no_pack(root) is None
    assert not any("no pack" in line for _, line in run_gates.results(root))


def test_no_work_type_prints_nothing_new(tmp_path: Path) -> None:
    """REQ-079: brief #1685 answer 3 (no work type: nothing new)."""
    root = _project(tmp_path, None)
    _record(root, "node")
    assert run_gates.no_pack(root) is None


def test_a_stack_outside_the_signal_table_prints_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-079: brief #1685 answer 4 (a name outside `config/stack-signals.toml`: `unknown`)."""
    from gates import pins

    row = ("zz-invented", *pins.STACKS["node"][1:])
    monkeypatch.setitem(pins.STACKS, "node", row)
    root = _project(tmp_path, "web-app")
    _record(root, "node")
    assert run_gates.no_pack(root) == "unknown"


def _settings() -> list[str]:
    from common import GOVERNANCE_LEVELS

    rows = ['project_lint_paths = ["src/**"]']
    rows += [f'governance = {{ level = "{level}" }}' for level in GOVERNANCE_LEVELS]
    rows += [f'[kit]\nlayout = "{x}"' for x in ("plugin", "installed")]
    rows += [f'execution = "{x}"' for x in ("hosted", "local")]
    rows += [f'review_mode = "{x}"' for x in ("solo", "team")]
    return [*rows, '[personal]\nforge = "files"']  # personal mode (SPEC-0041)


@pytest.mark.parametrize("setting", _settings())
def test_each_setting_leaves_the_no_pack_line_and_the_exit_code(
    setting: str, tmp_path: Path, no_network: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1685 answer 3 (each setting: the same line; the exit code unchanged)."""
    root = _project(tmp_path, "web-app")
    text = (root / "agk.toml").read_text(encoding="utf-8")
    top, _, delivery = text.partition("\n[delivery]")
    (root / "agk.toml").write_text(
        f"{top}\n[delivery]{delivery}\n{setting}\n"
        if setting.startswith("[")
        else f"{top}\n{setting}\n\n[delivery]{delivery}",
        encoding="utf-8",
    )
    if setting.startswith("[personal]"):
        from common import personal_table

        assert personal_table(root) is not None  # personal mode, not team mode
    before = run_gates.main(["--root", str(root)])
    assert NO_PACK not in capsys.readouterr().out
    _record(root, "node")
    assert run_gates.main(["--root", str(root)]) == before
    assert NO_PACK in capsys.readouterr().out
