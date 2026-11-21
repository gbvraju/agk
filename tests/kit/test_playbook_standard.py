"""Tests of the playbook standard part (SPEC-0072 rules 1 and 2, build (a); brief #1585, ADR-0665).

REQ-079 AC1. Each shipped playbook, composed with `default.toml`, holds an `[architecture]` and the
eight enterprise gate ids, each a check with a step or a judgement with a reason of at least 20
characters. A playbook's own `[architecture]` puts every `[testing] map` code in exactly one layer
and names no layer path outside the map. A stub that restates an enterprise check as judgement,
drops a pack rule code or adds an `allow` entry without an ADR in the project is refused, naming the
fixed gate id or the key and never a value. A stack with no `[[standards]]` entry is a warning,
never a failure. Fixtures in `tmp_path` only: invented data, no network.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
FOLDER = "config/playbooks"
ENTERPRISE = (
    "sign-in-permissions",
    "secrets",
    "input-validation",
    "logging-tracing",
    "environment-settings",
    "migrations",
    "accessibility",
    "performance",
)
NO_UI = ("cloud-migration", "data-pipeline", "mcp-server", "multi-agent")
PACK = (
    '\n[[standards]]\nstack = "go-modules"\nlint = "pack-lint"\nformat = "pack-format"\n'
    'type = "pack-type"\nconfig = "invented.cfg"\n'
    'rules = {{ tool = "invented-tool", version = "1", codes = [{codes}] }}\n'
)

sys.path.insert(0, str(SCRIPTS))
import check_playbooks  # noqa: E402
import playbook_format  # noqa: E402


def shipped() -> list[Path]:
    return playbook_format.playbooks(KIT_ROOT)


def kit_copy(tmp_path: Path) -> Path:
    shutil.copytree(KIT_ROOT / FOLDER, tmp_path / FOLDER)
    shutil.copy(KIT_ROOT / "config" / "stack-signals.toml", tmp_path / "config")
    return tmp_path


def edit(root: Path, name: str, old: str, new: str) -> None:
    path = root / FOLDER / f"{name}.toml"
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_playbooks.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.mark.parametrize("path", shipped(), ids=lambda p: p.stem)
def test_each_shipped_playbook_composes_the_eight_gates_and_an_architecture(path: Path) -> None:
    """REQ-079 AC1."""
    gates, _, found = check_playbooks.composed(path, KIT_ROOT)
    architecture, _, more = check_playbooks.standard(path, KIT_ROOT)
    assert found == [] and more == []
    by_id = {g["id"]: g for g in gates}
    for gid in ENTERPRISE:
        gate = by_id[gid]
        if gate["kind"] == "check":
            assert gate["step"], gid
        else:
            assert len(gate["reason"].strip()) >= 20, gid
    assert architecture["layers"], path.stem


def test_the_base_holds_one_src_layer_and_the_eight_gates() -> None:
    """REQ-079 AC1: `secrets` and `environment-settings` are checks with their steps (brief #1593,
    ADR-0673) and the other six are judgement (SPEC-0072 rule 3, ADR-0666, brief #1586)."""
    base = KIT_ROOT / FOLDER / "default.toml"
    architecture, _, _ = check_playbooks.standard(base, KIT_ROOT)
    assert [layer["name"] for layer in architecture["layers"]] == ["src"]
    assert architecture.get("allow", []) == []
    gates = {g["id"]: g for g in check_playbooks.composed(base, KIT_ROOT)[0]}
    checks = {gid: gates[gid].get("step") for gid in ENTERPRISE if gates[gid]["kind"] == "check"}
    want = {"secrets": "committed-secrets", "environment-settings": "environment-settings"}
    assert checks == want


@pytest.mark.parametrize("path", shipped(), ids=lambda p: p.stem)
def test_every_map_code_falls_in_exactly_one_layer(path: Path) -> None:
    """REQ-079 AC1: a playbook with a map holds its own layers, one per map code (Q-1585-1)."""
    data = playbook_format.load(path)
    codes = [entry["code"] for entry in data["testing"]["map"]]
    if not codes:
        return
    layers = data["architecture"]["layers"]
    assert sorted(p for layer in layers for p in layer["paths"]) == sorted(codes)


def test_the_web_app_layers_and_allowed_directions() -> None:
    """REQ-079 AC1: brief #1585 answer 1, as written."""
    data = playbook_format.load(KIT_ROOT / FOLDER / "web-app.toml")
    names = [layer["name"] for layer in data["architecture"]["layers"]]
    assert names == ["contracts", "mocks", "frontend", "backend"]
    allow = {(a["from"], a["to"]) for a in data["architecture"]["allow"]}
    assert allow == {("frontend", "contracts"), ("backend", "contracts"), ("mocks", "contracts")}


@pytest.mark.parametrize("name", NO_UI)
def test_a_playbook_with_no_ui_sets_accessibility_to_judgement(name: str) -> None:
    """REQ-079 AC1."""
    data = playbook_format.load(KIT_ROOT / FOLDER / f"{name}.toml")
    gate = {g["id"]: g for g in data["gates"]}["accessibility"]
    assert gate["kind"] == "judgement" and len(gate["reason"]) >= 20


def test_the_kit_copy_passes_and_warns_of_stacks_with_no_pack(tmp_path: Path) -> None:
    """REQ-079 AC1: brief #1585 answer 3, a warning and never a failure."""
    done = check(kit_copy(tmp_path))
    assert done.returncode == 0, done.stdout
    gates = "ok secrets\nok environment-settings\nok gates (2 check gates)\n"
    assert done.stdout == "ok playbooks (11 playbooks)\n" + gates
    assert done.stderr.startswith("warn playbooks: 6 stacks have no [[standards]] entry")


def test_an_enterprise_check_restated_as_judgement_is_refused_naming_the_gate(
    tmp_path: Path,
) -> None:
    """REQ-079 AC1."""
    root = kit_copy(tmp_path)
    # the base holds `secrets` as a check (brief #1593, ADR-0673)
    own = (
        '\n[[gates]]\nid = "secrets"\nkind = "judgement"\ntext = "An invented gate."\n'
        'owner_only = false\nreason = "An invented reason that is long enough."\n'
    )
    edit(root, "mobile", "[milestones]", own + "\n[milestones]")
    done = check(root)
    assert done.returncode == 1
    assert "a gate is restated weaker (gate: secrets, key: kind)" in done.stdout
    assert "invented reason" not in done.stdout


def test_an_enterprise_judgement_without_a_reason_is_refused(tmp_path: Path) -> None:
    """REQ-079 AC1: a reason of at least 20 characters."""
    root = kit_copy(tmp_path)
    edit(root, "default", 'reason = "No step can yet tell which code paths', 'reason = "Short"\n#')
    done = check(root)
    assert done.returncode == 1
    assert "(gate: input-validation, key: reason)" in done.stdout
    assert "Short" not in done.stdout


def test_a_map_code_in_no_layer_and_a_layer_path_outside_the_map_are_refused(
    tmp_path: Path,
) -> None:
    """REQ-079 AC1."""
    root = kit_copy(tmp_path)
    edit(root, "web-app", 'paths = ["mocks/**"]', 'paths = ["zz-invented/**"]')
    done = check(root)
    assert done.returncode == 1
    assert "a `[testing] map` code is in no layer (key: architecture.layers)" in done.stdout
    assert "a layer path is no `[testing] map` code (key: architecture.layers)" in done.stdout
    assert "zz-invented" not in done.stdout


def test_an_allow_entry_must_name_known_layers(tmp_path: Path) -> None:
    root = kit_copy(tmp_path)
    edit(root, "web-app", 'from = "mocks"', 'from = "zz-invented"')
    done = check(root)
    assert done.returncode == 1
    assert "an `allow` entry names an unknown layer (key: architecture.allow)" in done.stdout
    assert "zz-invented" not in done.stdout


def derived(root: Path, allow: str) -> Path:
    """A project's own playbook built on `web-app` (SPEC-0048 rule 22), with its own layers."""
    (root / "docs" / "research").mkdir(parents=True)
    (root / "docs" / "research" / "clinic-bookings.md").write_text("# Invented\n", encoding="utf-8")
    web = playbook_format.load(root / FOLDER / "web-app.toml")
    text = (root / FOLDER / "web-app.toml").read_text(encoding="utf-8")
    own = 'work_type = "clinic-bookings"\nmodules = ["web-app"]'
    text = text.replace('work_type = "web-app"', own)
    text = text.replace("owner_only = false\n", 'owner_only = false\nbasis = "expected"\n')
    old = "allow = [\n"
    assert old in text and web["architecture"]["allow"]
    path = root / FOLDER / "clinic-bookings.toml"
    path.write_text(text.replace(old, old + allow, 1), encoding="utf-8")
    return path


def test_an_allow_entry_added_without_an_adr_in_the_project_is_refused(tmp_path: Path) -> None:
    """REQ-079 AC1: principle 11, an added direction loosens the architecture."""
    root = kit_copy(tmp_path)
    derived(root, '  { from = "backend", to = "frontend" },\n')
    done = check(root)
    assert done.returncode == 1
    assert "an `allow` entry is added without an ADR in the project (key: allow)" in done.stdout


def test_an_allow_entry_added_with_an_adr_in_the_project_passes(tmp_path: Path) -> None:
    """REQ-079 AC1."""
    root = kit_copy(tmp_path)
    derived(root, '  { from = "backend", to = "frontend", adr = "ADR-0001" },\n')
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "adr" / "0001-invented.md").write_text("# ADR-0001\n", encoding="utf-8")
    done = check(root)
    assert done.returncode == 0, done.stdout


def test_a_pack_that_drops_a_rule_code_is_refused_and_one_that_adds_passes(
    tmp_path: Path,
) -> None:
    """REQ-079 AC1: a later layer may tighten a pack's rules, never drop one."""
    root = kit_copy(tmp_path)
    edit(root, "default", "[milestones]", PACK.format(codes='"A1", "B2"') + "\n[milestones]")
    edit(root, "mobile", "[milestones]", PACK.format(codes='"A1", "B2", "C3"') + "\n[milestones]")
    assert check(root).returncode == 0
    edit(root, "mobile", '"A1", "B2", "C3"', '"A1"')
    done = check(root)
    assert done.returncode == 1
    assert "a pack's `rules` drops a rule code (key: standards.rules)" in done.stdout
    assert "B2" not in done.stdout and "go-modules" not in done.stdout


def test_a_pack_for_a_stack_the_kit_cannot_name_is_refused(tmp_path: Path) -> None:
    """REQ-079 AC1: `stack` is a `[[stack]]` name of config/stack-signals.toml."""
    root = kit_copy(tmp_path)
    pack = PACK.format(codes='"A1"').replace("go-modules", "zz-invented")
    edit(root, "mobile", "[milestones]", pack + "\n[milestones]")
    done = check(root)
    assert done.returncode == 1
    assert "a `[[standards]]` stack is not a stack of config/stack-signals.toml" in done.stdout
    assert "zz-invented" not in done.stdout


def test_the_other_gates_are_still_not_named(tmp_path: Path) -> None:
    """SPEC-0048 rule 21 is unchanged: only the eight fixed ids are named in a refusal."""
    root = kit_copy(tmp_path)
    own = (
        '\n[[gates]]\nid = "cut-over-order"\nkind = "judgement"\ntext = "Invented."\n'
        "owner_only = false\n"
    )
    edit(root, "cloud-migration", "[milestones]", own + "\n[milestones]")
    done = check(root)
    assert done.returncode == 1
    assert "a gate is restated weaker (key: kind)" in done.stdout
    assert "cut-over-order" not in done.stdout
