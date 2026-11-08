"""Tests of the gate modules (SPEC-0048 rules 21 and 23, build (j); SPEC-0038 rules 2 and 4 as
amendment 130 widens them).

REQ-055 AC8. A playbook may name shipped playbooks in `modules` and takes their gates and evidence
whole: the composed gates are `default`, then each module, then its own, each id once. A playbook
that restates a gate as `judgement` where it is `check`, sets an `owner_only` gate to `false`, or
names a module that is not shipped fails `check_playbooks.py`, naming the rule and the key and never
a value. Fixtures in `tmp_path` only: invented data, no network.
"""

from __future__ import annotations

import subprocess  # nosec B603 B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
SCRIPT = SCRIPTS / "check_playbooks.py"
FOLDER = "config/playbooks"

sys.path.insert(0, str(SCRIPTS))
import check_playbooks  # noqa: E402
import playbook_format  # noqa: E402

DISCOVERY = "".join(
    f'\n[[discovery]]\nid = "{i}"\ntext = "An invented question about {i}?"\n'
    for i in playbook_format.DISCOVERY_IDS
)
BASE_GATE = ("base-gate", "check", True)
MODULE_GATE = ("module-gate", "judgement", True)
OWN_GATE = ("own-gate", "judgement", False)
SECRET_ID = "zz-invented-gate-id"


def gate(gate_id: str, kind: str, owner: bool) -> str:
    step = 'step = "invented_step"\n' if kind == "check" else ""
    return (
        f'\n[[gates]]\nid = "{gate_id}"\nkind = "{kind}"\ntext = "An invented gate."\n'
        f"owner_only = {'true' if owner else 'false'}\n{step}"
    )


def playbook(
    name: str,
    gates: tuple[tuple[str, str, bool], ...] = (),
    modules: str = "",
    evidence: tuple[str, ...] = (),
) -> str:
    listed = ", ".join(f'"{e}"' for e in evidence)
    return (
        f'format = 1\nwork_type = "{name}"\ntitle = "An invented playbook"\n'
        f"{modules}\nheavy_steps = []\nevidence = [{listed}]\nphases = []\nlanes = []\nclaims = []\n"
        "\n[split]\nbrief_order = []\ndepends_on = []\n"
        '\n[testing]\nprofile = "balanced"\nalways_full = []\nmap = []\n'
        '\n[milestones]\nshape = "per-brief"\nbatch_by = "not batched"\n'
        + "".join(gate(*g) for g in gates)
        + DISCOVERY
    )


def project(tmp_path: Path, files: dict[str, str]) -> Path:
    (tmp_path / FOLDER).mkdir(parents=True)
    for name, text in files.items():
        (tmp_path / FOLDER / f"{name}.toml").write_text(text, encoding="utf-8")
    return tmp_path


def base_files(own: str) -> dict[str, str]:
    return {
        "default": playbook("default", (BASE_GATE,), evidence=("base evidence",)),
        "web-app": playbook("web-app", (MODULE_GATE,), evidence=("module evidence",)),
        "mobile": own,
    }


def run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def composed(root: Path, name: str = "mobile") -> tuple[list[dict], list[str], list[str]]:
    return check_playbooks.composed(root / FOLDER / f"{name}.toml", root)


NAMED = 'modules = ["web-app"]'


def test_a_playbook_with_a_module_passes(tmp_path: Path) -> None:
    root = project(tmp_path, base_files(playbook("mobile", (OWN_GATE,), NAMED)))
    done = run(root)
    assert done.returncode == 0, done.stdout
    assert done.stdout.strip() == "ok playbooks (3 playbooks)"


def test_modules_must_be_a_list_of_names(tmp_path: Path) -> None:
    root = project(tmp_path, base_files(playbook("mobile", (OWN_GATE,), 'modules = "web-app"')))
    done = run(root)
    assert done.returncode == 1
    assert "`modules` has the wrong type" in done.stdout


def test_the_composed_gates_are_default_then_modules_then_own(tmp_path: Path) -> None:
    root = project(tmp_path, base_files(playbook("mobile", (OWN_GATE,), NAMED)))
    gates, _, found = composed(root)
    assert [g["id"] for g in gates] == ["base-gate", "module-gate", "own-gate"]
    assert found == []


def test_the_order_of_modules_is_the_order_named(tmp_path: Path) -> None:
    files = base_files(playbook("mobile", (OWN_GATE,), 'modules = ["pilot", "web-app"]'))
    files["pilot"] = playbook("pilot", (("pilot-gate", "judgement", False),))
    gates, _, found = composed(project(tmp_path, files))
    assert [g["id"] for g in gates] == ["base-gate", "pilot-gate", "module-gate", "own-gate"]
    assert found == []


def test_the_evidence_is_taken_whole_each_item_once(tmp_path: Path) -> None:
    own = playbook("mobile", (OWN_GATE,), NAMED, ("own evidence", "base evidence"))
    _, evidence, _ = composed(project(tmp_path, base_files(own)))
    assert evidence == ["base evidence", "module evidence", "own evidence"]


def test_each_id_appears_once_at_its_first_place(tmp_path: Path) -> None:
    own = playbook("mobile", (OWN_GATE, ("module-gate", "judgement", True), BASE_GATE), NAMED)
    gates, _, found = composed(project(tmp_path, base_files(own)))
    assert [g["id"] for g in gates] == ["base-gate", "module-gate", "own-gate"]
    assert found == []


def test_a_playbook_without_modules_still_takes_default(tmp_path: Path) -> None:
    gates, _, found = composed(project(tmp_path, base_files(playbook("mobile", (OWN_GATE,)))))
    assert [g["id"] for g in gates] == ["base-gate", "own-gate"]
    assert found == []


def test_default_composes_only_itself(tmp_path: Path) -> None:
    gates, _, found = composed(project(tmp_path, base_files(playbook("mobile"))), "default")
    assert [g["id"] for g in gates] == ["base-gate"]
    assert found == []


def test_a_project_without_default_has_no_base_layer(tmp_path: Path) -> None:
    files = {"mobile": playbook("mobile", (OWN_GATE,))}
    gates, _, found = composed(project(tmp_path, files))
    assert [g["id"] for g in gates] == ["own-gate"]
    assert found == []


def test_a_stronger_restatement_replaces_the_gate_in_place(tmp_path: Path) -> None:
    files = base_files(playbook("mobile", (("module-gate", "check", True),), NAMED))
    gates, _, found = composed(project(tmp_path, files))
    assert [(g["id"], g["kind"]) for g in gates] == [
        ("base-gate", "check"),
        ("module-gate", "check"),
    ]
    assert found == []
    assert run(tmp_path).returncode == 0


def test_owner_only_may_be_raised(tmp_path: Path) -> None:
    files = base_files(playbook("mobile"))
    files["default"] = playbook("default", (("raised", "judgement", False),))
    files["mobile"] = playbook("mobile", (("raised", "judgement", True),))
    gates, _, found = composed(project(tmp_path, files))
    assert gates[0]["owner_only"] is True
    assert found == []


def test_restating_a_default_check_as_judgement_fails(tmp_path: Path) -> None:
    own = playbook("mobile", (("base-gate", "judgement", True),))
    done = run(project(tmp_path, base_files(own)))
    assert done.returncode == 1
    assert done.stdout.count("FAIL playbooks:") == 1
    assert "rule 21" in done.stdout and "key: kind" in done.stdout
    assert "config/playbooks/mobile.toml" in done.stdout


def test_turning_a_default_owner_only_gate_off_fails(tmp_path: Path) -> None:
    own = playbook("mobile", (("base-gate", "check", False),))
    done = run(project(tmp_path, base_files(own)))
    assert done.returncode == 1
    assert "rule 21" in done.stdout and "key: owner_only" in done.stdout


def test_weakening_a_module_gate_fails_naming_owner_only(tmp_path: Path) -> None:
    own = playbook("mobile", (("module-gate", "judgement", False),), NAMED)
    done = run(project(tmp_path, base_files(own)))
    assert done.returncode == 1
    assert "key: owner_only" in done.stdout


def test_weakening_both_names_both_keys(tmp_path: Path) -> None:
    own = playbook("mobile", (("base-gate", "judgement", False),))
    done = run(project(tmp_path, base_files(own)))
    assert done.stdout.count("FAIL playbooks:") == 2
    assert "key: kind" in done.stdout and "key: owner_only" in done.stdout


def test_a_weakened_gate_keeps_the_stronger_form(tmp_path: Path) -> None:
    own = playbook("mobile", (("base-gate", "judgement", False),))
    gates, _, found = composed(project(tmp_path, base_files(own)))
    assert (gates[0]["kind"], gates[0]["owner_only"]) == ("check", True)
    assert len(found) == 2


def test_a_module_that_weakens_an_earlier_module_fails(tmp_path: Path) -> None:
    files = base_files(playbook("mobile", (), 'modules = ["web-app", "pilot"]'))
    files["pilot"] = playbook("pilot", (("module-gate", "judgement", False),))
    done = run(project(tmp_path, files))
    assert done.returncode == 1
    assert "key: owner_only" in done.stdout
    assert "config/playbooks/mobile.toml" in done.stdout


@pytest.mark.parametrize("name", ["no-such-kind", "default", "../web-app", ""])
def test_a_module_outside_the_work_types_fails(tmp_path: Path, name: str) -> None:
    own = playbook("mobile", (OWN_GATE,), f'modules = ["{name}"]')
    done = run(project(tmp_path, base_files(own)))
    assert done.returncode == 1
    assert "rule 23" in done.stdout and "key: modules" in done.stdout
    if name:
        assert f'"{name}"' not in done.stdout


def test_a_work_type_without_its_file_is_not_shipped(tmp_path: Path) -> None:
    own = playbook("mobile", (OWN_GATE,), 'modules = ["rag-app"]')
    done = run(project(tmp_path, base_files(own)))
    assert done.returncode == 1
    assert "rule 23" in done.stdout and "key: modules" in done.stdout
    assert "rag-app" not in done.stdout


def test_an_unshipped_module_adds_no_gates(tmp_path: Path) -> None:
    own = playbook("mobile", (OWN_GATE,), 'modules = ["rag-app"]')
    gates, _, _ = composed(project(tmp_path, base_files(own)))
    assert [g["id"] for g in gates] == ["base-gate", "own-gate"]


def test_a_module_that_names_modules_fails(tmp_path: Path) -> None:
    files = base_files(playbook("mobile", (OWN_GATE,), NAMED))
    files["web-app"] = playbook("web-app", (MODULE_GATE,), 'modules = ["pilot"]')
    files["pilot"] = playbook("pilot")
    done = run(project(tmp_path, files))
    assert done.returncode == 1
    assert "rule 23" in done.stdout and "key: modules" in done.stdout


def test_a_playbook_that_names_itself_fails(tmp_path: Path) -> None:
    done = run(
        project(tmp_path, base_files(playbook("mobile", (OWN_GATE,), 'modules = ["mobile"]')))
    )
    assert done.returncode == 1
    assert "key: modules" in done.stdout


def test_no_failure_prints_a_value(tmp_path: Path) -> None:
    files = base_files(
        playbook("mobile", ((SECRET_ID, "judgement", False),), 'modules = ["rag-app"]')
    )
    files["default"] = playbook("default", ((SECRET_ID, "check", True),))
    done = run(project(tmp_path, files))
    assert done.returncode == 1
    assert SECRET_ID not in done.stdout and "rag-app" not in done.stdout


def test_a_module_that_is_not_toml_does_not_stop_the_check(tmp_path: Path) -> None:
    files = base_files(playbook("mobile", (OWN_GATE,), NAMED))
    files["web-app"] = "not toml ["
    done = run(project(tmp_path, files))
    assert done.returncode == 1
    assert "Traceback" not in done.stderr
    assert "rule 1: config/playbooks/web-app.toml: the file is not TOML" in done.stdout


@pytest.mark.parametrize(
    "bad",
    [
        "gates = 3\n",
        'gates = ["a"]\n',
        "[[gates]]\nkind = 1\n",
        '[[gates]]\nid = 1\nkind = "check"\n',
    ],
)
def test_a_malformed_gate_list_does_not_stop_the_check(tmp_path: Path, bad: str) -> None:
    files = base_files(f'format = 1\nwork_type = "mobile"\n{bad}')
    done = run(project(tmp_path, files))
    assert done.returncode == 1
    assert "Traceback" not in done.stderr
    assert "FAIL playbooks:" in done.stdout


def test_every_shipped_playbook_takes_default_and_is_not_weakened() -> None:
    assert check_playbooks.main(["--root", str(KIT_ROOT)]) == 0
    base = check_playbooks.composed(KIT_ROOT / FOLDER / "default.toml", KIT_ROOT)[0]
    five = [g["id"] for g in base]
    assert len(five) == 5
    for path in playbook_format.playbooks(KIT_ROOT):
        gates, _, found = check_playbooks.composed(path, KIT_ROOT)
        assert found == []
        assert [g["id"] for g in gates][:5] == five
