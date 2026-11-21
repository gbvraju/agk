"""Tests of the interface contract, the data model and their two checks (SPEC-0072 rules 3 and 5
as amendment 207 proposes; REQ-079 AC2, REQ-055; brief #1597, ADR-0677).

On a sample web-app project the `contract-tests` step fails an operation no test names and a
contract that does not parse, the `mock-parity` step fails a missing mock and a mock with other
response keys, each naming the gate id and the path class and never an operation; a sample with
every test and mock passes; a project with no contract, or (in `mode = "adopt"`) a contract in
another format, prints `not run`, never `ok` and never red; `check_plan.py` refuses a back-end
brief that may merge before the contract and the data model; and the templates are the kit's
format with invented entities only. Fixtures in `tmp_path` only: no network.
"""

from __future__ import annotations

import json
import shutil
import socket
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import check_plan  # noqa: E402
import run_gates  # noqa: E402

PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
TEMPLATES = KIT_ROOT / "kit" / "templates"
BOOKING = {"id": {"type": "string"}, "studio": {"type": "string"}, "starts_at": {"type": "string"}}


def _contract(version: str = "3.1.0") -> dict:
    ok = {"description": "ok", "content": {"application/json": {"schema": {}}}}
    listed = json.loads(json.dumps(ok))
    listed["content"]["application/json"]["schema"] = {"$ref": "#/components/schemas/Booking"}
    made = json.loads(json.dumps(ok))
    made["content"]["application/json"]["schema"] = {"properties": {"id": {"type": "string"}}}
    return {
        "openapi": version,
        "info": {"title": "Studio bookings at example.com", "version": "0.1.0"},
        "paths": {
            "/bookings": {
                "get": {"operationId": "listBookings", "responses": {"200": listed}},
                "post": {"operationId": "createBooking", "responses": {"201": made}},
            }
        },
        "components": {"schemas": {"Booking": {"type": "object", "properties": BOOKING}}},
    }


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def _project(tmp_path: Path, mode: str = "init", work_type: str = "web-app") -> Path:
    root = tmp_path / "proj"
    shutil.copytree(PLAYBOOKS, root / "config" / "playbooks")
    _write(root, "agk.toml", f'mode = "{mode}"\n\n[delivery]\nwork_type = "{work_type}"\n')
    _write(root, "contracts/openapi.json", json.dumps(_contract(), indent=2).replace("\n", "\r\n"))
    _write(root, "tests/contract/test_bookings.py", "# listBookings\n# createBooking\n")
    _write(
        root,
        "mocks/list.json",
        json.dumps(
            {
                "operationId": "listBookings",
                "response": {"id": "b-1", "studio": "s-1", "starts_at": "2026-01-01T10:00:00Z"},
            }
        ),
    )
    _write(
        root,
        "mocks/create.json",
        json.dumps({"operationId": "createBooking", "response": {"id": "b-2"}}),
    )
    return root


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a contract step opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _gates(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = run_gates.main(["--root", str(root)])
    return code, capsys.readouterr().out


def _quiet(out: str) -> None:
    """Principle 8: a failure names the gate and the path class, never an operation."""
    for value in ("listBookings", "createBooking", "/bookings", "b-1"):
        assert value not in out


def test_req079_ac2_a_sample_with_tests_and_mocks_passes(tmp_path, capsys):
    """REQ-079 AC2: both steps run as checks and pass on a complete sample."""
    code, out = _gates(_project(tmp_path), capsys)
    assert code == 0, out
    assert "ok contract-tests" in out and "ok mock-parity" in out


def test_req079_ac2_an_untested_operation_is_red(tmp_path, capsys):
    """REQ-079 AC2: an operationId that no file under `test_dirs` names fails contract-tests."""
    root = _project(tmp_path)
    _write(root, "tests/contract/test_bookings.py", "# listBookings only\n")
    code, out = _gates(root, capsys)
    assert code == 1
    assert "FAIL gates: contract-tests: SPEC-0072 rule 3: an operation" in out
    assert "(path class: contracts/openapi.json; setting: test_dirs)" in out
    _quiet(out)


def test_req079_ac2_a_missing_mock_and_other_response_keys_are_red(tmp_path, capsys):
    """REQ-079 AC2: mock-parity fails a missing mock and a mock whose keys differ."""
    root = _project(tmp_path)
    (root / "mocks" / "create.json").unlink()
    code, out = _gates(root, capsys)
    assert (
        code == 1 and "FAIL gates: mock-parity: SPEC-0072 rule 3: an operation has no mock" in out
    )
    _quiet(out)
    root = _project(tmp_path / "other")
    _write(
        root,
        "mocks/list.json",
        json.dumps({"operationId": "listBookings", "response": {"id": "b-1"}}),
    )
    code, out = _gates(root, capsys)
    assert code == 1 and "mock-parity: SPEC-0072 rule 3: a mock's response keys" in out
    assert "(path class: mocks/)" in out
    _quiet(out)


def test_req079_ac2_an_unparsable_contract_is_red_naming_the_path_class(tmp_path, capsys):
    """REQ-079 AC2: a contract that does not parse fails both steps, naming the path class."""
    root = _project(tmp_path)
    _write(root, "contracts/openapi.json", '{"openapi": "3.1.0", "paths": ')
    code, out = _gates(root, capsys)
    assert code == 1
    for gate in ("contract-tests", "mock-parity"):
        assert f"FAIL gates: {gate}: SPEC-0072 rule 3: the contract does not parse" in out
    assert "(path class: contracts/openapi.json)" in out


def test_req079_ac2_no_contract_yet_is_not_run_never_ok(tmp_path, capsys):
    """REQ-079 AC2: before the contract brief the steps are `not run`, so nothing is red."""
    root = _project(tmp_path)
    (root / "contracts" / "openapi.json").unlink()
    code, out = _gates(root, capsys)
    assert code == 0, out
    assert "not run contract-tests: no contract in the kit's format" in out
    assert "ok contract-tests" not in out and "ok mock-parity" not in out


def test_req055_an_adopted_contract_in_another_format_is_green(tmp_path, capsys):
    """REQ-055: `mode = "adopt"` keeps a contract in another format; nothing existing is red."""
    root = _project(tmp_path, mode="adopt")
    (root / "contracts" / "openapi.json").unlink()
    _write(root, "contracts/openapi.yaml", "openapi: 3.0.0\ninfo:\n  title: Studio bookings\n")
    code, out = _gates(root, capsys)
    assert code == 0, out
    assert "not run contract-tests" in out and "not run mock-parity" in out
    root = _project(tmp_path / "old", mode="adopt")
    _write(root, "contracts/openapi.json", json.dumps(_contract("3.0.3")))
    code, out = _gates(root, capsys)
    assert code == 0 and "not run contract-tests: a contract in another format" in out, out


def test_req079_ac2_another_openapi_version_outside_adopt_is_red(tmp_path, capsys):
    """REQ-079 AC2: a new project's contract is OpenAPI 3.1 (amendment 207)."""
    root = _project(tmp_path)
    _write(root, "contracts/openapi.json", json.dumps(_contract("3.0.3")))
    code, out = _gates(root, capsys)
    assert code == 1 and "contract-tests: SPEC-0072 rule 3: the contract is not OpenAPI 3.1" in out


def test_req079_ac2_the_playbooks_restore_both_gates_as_checks():
    """REQ-079 AC2: SPEC-0072 rule 2, the stronger kind, with a step and no reason."""
    for name, ids in (
        ("web-app", ("contract-tests", "mock-parity")),
        ("api-service", ("contract-tests",)),
    ):
        gates = {
            g["id"]: g for g in tomllib.loads((PLAYBOOKS / f"{name}.toml").read_text())["gates"]
        }
        for gid in ids:
            assert gates[gid]["kind"] == "check" and gates[gid]["step"] == gid
            assert "reason" not in gates[gid]
            assert (AGK / "gates" / f"{gid.replace('-', '_')}.py").is_file()


def _plan(tmp_path: Path, contract: bool, model: bool) -> Path:
    root = _project(tmp_path)
    if not contract:
        (root / "contracts" / "openapi.json").unlink()
    if model:
        _write(root, "docs/data-model.md", "# Data model\n")
    _write(
        root, "docs/plan/milestones.md", "# Milestones\n\n### M1 Foundation\n\n### M2 Bookings\n"
    )
    return root


def _brief(root: Path, key: str, milestone: str, *lines: str) -> None:
    body = "\n".join([f"# {key}", "", f"Milestone: {milestone}", *lines]) + "\n"
    _write(root, f"docs/plan/briefs/{milestone}/{key}.md", body)


def test_req079_ac2_check_plan_refuses_a_back_end_brief_before_the_contract(tmp_path):
    """REQ-079 AC2: a back-end brief with no Depends-on the contract brief, while the contract or
    the data model is missing, is refused naming the rule and the key, never a value."""
    root = _plan(tmp_path, contract=False, model=False)
    _brief(root, "B1", "M1", "Kind: foundation")
    _brief(root, "B2", "M1", "Kind: contract", "Depends-on: B1")
    _brief(root, "B3", "M2", "Kind: back-end", "Depends-on: B1")
    assert check_plan.contract_problems(root) == [
        "SPEC-0072 rule 5: B3: a back-end brief before the contract and the data model "
        "(no Depends-on: B2; path class: contracts/openapi.json, docs/data-model.md)"
    ]
    _brief(root, "B3", "M2", "Kind: back-end", "Depends-on: B1, B2")
    assert check_plan.contract_problems(root) == []
    (root / "docs/plan/briefs/M1/B2.md").unlink()
    assert check_plan.contract_problems(root)[0].endswith(
        "(no contract brief; path class: contracts/openapi.json, docs/data-model.md)"
    )


def test_req079_ac2_check_plan_holds_nothing_once_both_exist_or_without_the_contract_kind(tmp_path):
    """REQ-079 AC2: on the default branch with both files, or a work type without `contract`."""
    root = _plan(tmp_path, contract=True, model=True)
    _brief(root, "B3", "M2", "Kind: back-end")
    assert check_plan.contract_problems(root) == []
    root = _plan(tmp_path / "pipe", contract=False, model=False)
    _write(root, "agk.toml", 'mode = "init"\n\n[delivery]\nwork_type = "data-pipeline"\n')
    _brief(root, "B3", "M2", "Kind: back-end")
    assert check_plan.contract_problems(root) == []


def test_req079_ac2_the_templates_are_the_kits_format_with_invented_entities(tmp_path, capsys):
    """REQ-079 AC2: amendment 207's formats; the template contract itself passes contract-tests."""
    contract = json.loads((TEMPLATES / "contract-openapi.json").read_text(encoding="utf-8"))
    assert contract["openapi"].startswith("3.1.")
    text = (TEMPLATES / "contract-openapi.json").read_text(encoding="utf-8")
    assert "example.com" in text and "Booking" in text and "Studio" in text
    model = (TEMPLATES / "data-model.md").read_text(encoding="utf-8")
    header = "| Entity | Keys | Personal data | Kept for | Who may see it |"
    assert header in model and "Booking" in model and "Studio" in model
    assert "contracts/openapi.json" in (TEMPLATES / "architecture.md").read_text(encoding="utf-8")
    assert "docs/data-model.md" in (TEMPLATES / "architecture.md").read_text(encoding="utf-8")
    root = _project(tmp_path)
    shutil.copyfile(TEMPLATES / "contract-openapi.json", root / "contracts" / "openapi.json")
    shutil.rmtree(root / "mocks")
    code, out = _gates(root, capsys)
    assert "FAIL gates: mock-parity" in out and code == 1
