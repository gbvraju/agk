"""Tests of the work-type declaration (SPEC-0038 rule 5; REQ-045 AC2; brief #650, ADR-0312).

A project declares its work type in one line of `agk.toml`, `[delivery] work_type = "<work type>"`.
`playbook_format.declaration` reads it; `check_playbooks.py` and `doctor.py` fail an unknown value,
or one whose playbook is missing, naming the setting `work_type` and never its value; with no
declaration nothing reads a playbook, `check_playbooks.py` prints what it printed before, and
`doctor.py` adds only the one line `work type: none (no playbook)`. No reader writes `agk.toml`.
Fixtures in `tmp_path` only: invented data, no network.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import doctor
import playbook_format
import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
CHECK = SCRIPTS / "check_playbooks.py"
DOCTOR = SCRIPTS / "doctor.py"
FIXTURES = Path(__file__).parent / "fixtures" / "doctor" / "ok"
NONE_LINE = "work type: none (no playbook)"
BASE_TOML = 'mode = "init"\nversion = "9.9.9"\ninstalled = "2020-01-02"\ndefault_branch = "main"\n'
UNKNOWN = "zz-unknown-type"


def full_playbook() -> str:
    """The full fixture playbook of the format's own tests (one source of the format)."""
    spec = importlib.util.spec_from_file_location(
        "format_tests", Path(__file__).parent / "test_check_playbooks.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FULL


def clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}


def project(root: Path, delivery: str = "", playbook: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "agk.toml").write_text(BASE_TOML + delivery, encoding="utf-8")
    if playbook:
        path = root / "config" / "playbooks" / "web-app.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(full_playbook(), encoding="utf-8")
        runs = root / "docs" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "2026-11-01-example.md").write_text("# a run record\n", encoding="utf-8")
    return root


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(CHECK), "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
    )


def doctor_target(tmp_path: Path, delivery: str = "", playbook: bool = False) -> dict[str, Path]:
    """The doctor's `ok` fixture (a git work tree, its api and kit folders) and a declaration."""
    dirs = {name: tmp_path / name for name in ("tree", "api", "kit")}
    for name, target in dirs.items():
        shutil.copytree(FIXTURES / name, target, dirs_exist_ok=True)
    root = dirs["tree"]
    with (root / "agk.toml").open("a", encoding="utf-8") as handle:
        handle.write(delivery)
    if playbook:
        path = root / "config" / "playbooks" / "web-app.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(full_playbook(), encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed list
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        [
            "git",
            "-C",
            str(root),
            "symbolic-ref",
            "refs/remotes/origin/HEAD",
            "refs/remotes/origin/main",
        ],
        check=True,
    )
    return dirs


def run_doctor(dirs: dict[str, Path], *extra: str) -> subprocess.CompletedProcess[str]:
    stub = dirs["tree"].parent / "bin"
    stub.mkdir(exist_ok=True)
    gh = stub / "gh"
    gh.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    gh.chmod(0o755)
    env = clean_env()
    env["PATH"] = f"{stub}{os.pathsep}{os.environ['PATH']}"
    args = ["--api-dir", str(dirs["api"]), "--repo", "example-owner/example-repo"]
    args += ["--kit-root", str(dirs["kit"]), *extra, str(dirs["tree"])]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(DOCTOR), *args], capture_output=True, text=True, env=env, check=False
    )


# --- the reader --------------------------------------------------------------------------------


def test_ac2_a_declared_shipped_playbook_is_selected(tmp_path):
    """REQ-045 AC2: SPEC-0038 rule 5 (a work type that names a present playbook is selected)."""
    root = project(tmp_path, '\n[delivery]\nwork_type = "web-app"\n', playbook=True)
    assert playbook_format.declaration(root) == ("web-app", [])
    assert playbook_format.selected(root) == root / "config" / "playbooks" / "web-app.toml"
    result = check(root)
    # SPEC-0072 rule 3 (brief #1586): the selected playbook's check gates then run; the stub's
    # steps have no module, so each is refused naming its gate id
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "ok playbooks (1 playbooks)", result.stdout + result.stderr
    fails = [ln for ln in lines[1:] if not ln.startswith("not run ")]  # pins: brief #1776
    assert fails and all(line.startswith("FAIL gates: ") for line in fails)


@pytest.mark.parametrize(
    ("delivery", "setting", "value"),
    [
        (f'\n[delivery]\nwork_type = "{UNKNOWN}"\n', "work_type", UNKNOWN),
        ('\n[delivery]\nwork_type = "rag-app"\n', "work_type", "rag-app"),
        ('\n[delivery]\nwork_type = ["web-app", "rag-app"]\n', "work_type", "rag-app"),
        ("\n[delivery]\nwork_type = 7\n", "work_type", "7"),
        ('\ndelivery = "web-app"\n', "delivery", "web-app"),
        (
            '\n[delivery]\nwork_type = "web-app"\nzz_extra = "zz-extra-value"\n',
            "delivery",
            "zz-extra",
        ),
    ],
    ids=["unknown", "playbook-missing", "two-types", "wrong-type", "not-a-table", "extra-key"],
)
def test_ac2_a_bad_declaration_fails_naming_the_setting(tmp_path, delivery, setting, value):
    """REQ-045 AC2: SPEC-0038 rule 5 and Q-S0038-1 (the setting is named, never the value)."""
    root = project(tmp_path, delivery, playbook=True)
    work_type, found = playbook_format.declaration(root)
    assert work_type is None and found
    assert all(line.startswith("rule 5: agk.toml: ") for line in found), found
    assert all(f"(setting: {setting})" in line for line in found), found
    assert playbook_format.selected(root) is None
    result = check(root)
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    fails = [ln for ln in out.splitlines() if ln.startswith("FAIL playbooks: rule 5: agk.toml")]
    assert fails and all(f"setting: {setting}" in ln for ln in fails), out
    assert value not in "\n".join(fails), out


def test_ac2_the_missing_playbook_and_the_unknown_value_read_differently(tmp_path):
    """REQ-045 AC2: SPEC-0038 rule 5 (an unknown value and a missing playbook are two failures)."""
    unknown = project(tmp_path / "a", f'\n[delivery]\nwork_type = "{UNKNOWN}"\n')
    missing = project(tmp_path / "b", '\n[delivery]\nwork_type = "rag-app"\n')
    assert playbook_format.declaration(unknown)[1] != playbook_format.declaration(missing)[1]
    assert "playbook" in playbook_format.declaration(missing)[1][0]


@pytest.mark.parametrize(
    "delivery",
    ["", "\n[delivery]\n", '\n# [delivery]\n# work_type = "web-app"\n'],
    ids=["no-table", "empty-table", "commented"],
)
def test_ac2_no_declaration_reads_no_playbook_and_prints_as_before(tmp_path, delivery):
    """REQ-045 AC2: SPEC-0038 rule 5 (with no work type nothing changes)."""
    root = project(tmp_path, delivery)
    assert playbook_format.declaration(root) == (None, [])
    assert playbook_format.selected(root) is None
    result = check(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "ok playbooks (none)\n"


def test_ac2_no_agk_toml_is_no_declaration(tmp_path):
    """REQ-045 AC2: SPEC-0038 rule 5 (a root without agk.toml declares nothing)."""
    assert playbook_format.declaration(tmp_path) == (None, [])
    assert check(tmp_path).stdout == "ok playbooks (none)\n"


def test_ac2_an_unreadable_agk_toml_fails_naming_the_path_class(tmp_path):
    """REQ-045 AC2: SPEC-0038 rule 5 (the declaration that cannot be read is not passed over)."""
    (tmp_path / "agk.toml").write_text("delivery = [unclosed\n", encoding="utf-8")
    work_type, found = playbook_format.declaration(tmp_path)
    assert work_type is None
    assert found == ["rule 5: agk.toml: the file is not TOML (setting: work_type)"]


def test_ac2_no_reader_writes_agk_toml(tmp_path):
    """REQ-045 AC2: SPEC-0038 rule 5 (a session never writes the line; no reader does either)."""
    dirs = doctor_target(tmp_path, '\n[delivery]\nwork_type = "web-app"\n', playbook=True)
    before = (dirs["tree"] / "agk.toml").read_bytes()
    playbook_format.declaration(dirs["tree"])
    check(dirs["tree"])
    run_doctor(dirs)
    run_doctor(dirs, "--json")
    assert (dirs["tree"] / "agk.toml").read_bytes() == before


# --- doctor ------------------------------------------------------------------------------------


def test_ac2_doctor_without_a_declaration_adds_only_the_none_line(tmp_path):
    """REQ-045 AC2: SPEC-0038 rule 5 (one line `work type: none (no playbook)`, nothing else)."""
    dirs = doctor_target(tmp_path)
    proc = run_doctor(dirs)
    lines = proc.stdout.splitlines()
    assert proc.returncode == 0, proc.stdout
    assert lines.count(NONE_LINE) == 1
    # ADR-0385, ADR-0525, ADR-0527, ADR-0528, ADR-0686, ADR-0801
    assert lines[-2:] == [NONE_LINE, "summary: 59 ok, 0 fail, 0 cannot-check"]
    # Without the line, the report is the one the default branch renders from the same checks
    # (with its secret scan line, ADR-0306),
    root = dirs["tree"].resolve()
    report, version = doctor.run_checks(
        root, "example-owner/example-repo", dirs["kit"], dirs["api"]
    )
    # and its licence grant line, ADR-0596
    licence = doctor.licence_lines(root)
    legacy = doctor.render_text(report, version, scan=doctor.secret_scan_line(), licence=licence)
    assert [ln for ln in lines if ln != NONE_LINE] == legacy.splitlines()


def test_ac2_doctor_json_carries_the_same_line(tmp_path):
    """REQ-045 AC2: SPEC-0038 rule 5 (text and JSON carry the same finding)."""
    proc = run_doctor(doctor_target(tmp_path), "--json")
    data = json.loads(proc.stdout)
    assert data["work_type"] == NONE_LINE
    assert proc.returncode == 0


def test_ac2_doctor_says_which_playbook_applies(tmp_path):
    """REQ-045 AC2: SPEC-0038 rule 5 (doctor names the declared playbook)."""
    dirs = doctor_target(tmp_path, '\n[delivery]\nwork_type = "web-app"\n', playbook=True)
    proc = run_doctor(dirs)
    assert proc.returncode == 0, proc.stdout
    assert "work type: web-app (playbook config/playbooks/web-app.toml)" in proc.stdout.splitlines()
    assert NONE_LINE not in proc.stdout


@pytest.mark.parametrize(
    ("value", "playbook"), [(UNKNOWN, True), ("rag-app", True)], ids=["unknown", "playbook-missing"]
)
def test_ac2_doctor_fails_a_bad_declaration_naming_the_setting(tmp_path, value, playbook):
    """REQ-045 AC2: SPEC-0038 rule 5 (doctor fails naming `work_type`, never the value)."""
    dirs = doctor_target(tmp_path, f'\n[delivery]\nwork_type = "{value}"\n', playbook=playbook)
    proc = run_doctor(dirs)
    assert proc.returncode == 1, proc.stdout
    fails = [ln for ln in proc.stdout.splitlines() if ln.startswith("FAIL work type: ")]
    assert len(fails) == 1 and "(setting: work_type)" in fails[0], proc.stdout
    assert value not in proc.stdout
    data = json.loads(run_doctor(dirs, "--json").stdout)
    assert data["work_type"] == fails[0]


# --- the templates ------------------------------------------------------------------------------


@pytest.mark.parametrize("rel", ["kit/templates/agk.toml", "agk.toml"])
def test_ac2_the_templates_carry_the_commented_table_and_declare_nothing(rel):
    """REQ-045 AC2: SPEC-0038 rules 5 and 12 (b) (the commented table; no type declared here)."""
    text = (KIT_ROOT / rel).read_text(encoding="utf-8")
    lines = text.splitlines()
    assert "# [delivery]" in lines
    assert any(ln.startswith("# work_type = ") for ln in lines)
    assert "delivery" not in tomllib.loads(text)
    assert playbook_format.declaration(KIT_ROOT) == (None, [])


def test_doctor_warns_a_stack_with_no_pack(tmp_path):
    """REQ-079: brief #1685 answer 2 (one warn line naming the setting; exit code unchanged)."""
    dirs = doctor_target(tmp_path, '\n[delivery]\nwork_type = "web-app"\n', playbook=True)
    line = "warn standards: no pack for this stack yet (setting: stack record)"
    assert line not in run_doctor(dirs).stdout.splitlines()
    adr = dirs["tree"] / "docs" / "adr"
    adr.mkdir(parents=True, exist_ok=True)
    (adr / "0003-stack-options.md").write_text(
        "# ADR-0003: Stack options\n\n- Status: Accepted\n\n1. **Options**:\n"
        "   - Option A — Parts: node 22.11.0 MIT. Why: invented.\n3. **Chosen**: Option A\n",
        encoding="utf-8",
    )
    proc = run_doctor(dirs)
    assert proc.returncode == 0, proc.stdout
    assert line in proc.stdout.splitlines()
    data = json.loads(run_doctor(dirs, "--json").stdout)
    assert line in data["skills"]


# --- a derived playbook named in the line (brief #1908, ADR-0790) -------------------------------

DERIVED = "orders"
FRONT_DOOR = SCRIPTS / "front_door.py"
DERIVED_LINE = "work type: orders (playbook config/playbooks/orders.toml)"
UNKNOWN_LINE = "rule 5: agk.toml: `work_type` is not one of the work types (setting: work_type)"
MISSING_LINE = (
    "rule 5: agk.toml: `work_type` names a work type whose playbook is missing under "
    "config/playbooks/ (setting: work_type)"
)


def research_text() -> str:
    """A research record of SPEC-0048 rule 6, from the derive tests (one source of its form)."""
    spec = importlib.util.spec_from_file_location(
        "derive_tests", Path(__file__).parent / "test_front_door_derive.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.record_text()


def stub_plugin(where: Path, books: dict[str, str] | None = None) -> Path:
    """A plugin folder `kit_root` accepts, holding only the playbooks named."""
    (where / ".claude-plugin").mkdir(parents=True)
    version = json.loads((KIT_ROOT / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    (where / ".claude-plugin" / "plugin.json").write_text(json.dumps(version), encoding="utf-8")
    (where / "scripts" / "agk").mkdir(parents=True)
    (where / "scripts" / "agk" / "kit_root.py").write_text("", encoding="utf-8")
    books_dir = where / "config" / "playbooks"
    books_dir.mkdir(parents=True)
    shutil.copy(KIT_ROOT / "config" / "playbooks" / "default.toml", books_dir / "default.toml")
    for name, text in (books or {}).items():
        (books_dir / f"{name}.toml").write_text(text, encoding="utf-8")
    return where


def derived_project(root: Path, layout: str, value: str = DERIVED, write: bool = True) -> Path:
    """An invented project with a research record and the skeleton `derive-write` writes, then
    the owner's line naming `value`; installed (the kit's playbooks copied in) or clean."""
    root.mkdir(parents=True, exist_ok=True)
    kit = ""
    if layout == "installed":
        shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    else:
        kit = '\n[kit]\nlayout = "plugin"\n'
    (root / "agk.toml").write_text(BASE_TOML + kit, encoding="utf-8")
    record = root / "docs" / "research" / f"{DERIVED}.md"
    record.parent.mkdir(parents=True)
    record.write_text(research_text(), encoding="utf-8")
    if write:
        proc = subprocess.run(  # nosec B603 - fixed argument list
            [sys.executable, str(FRONT_DOOR), "derive-write", "--slug", DERIVED]
            + ["--modules", "api-service", "--root", str(root)],
            capture_output=True,
            text=True,
            env=clean_env(),
            cwd=root,
            check=False,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
    with (root / "agk.toml").open("a", encoding="utf-8") as handle:
        handle.write(f'\n[delivery]\nwork_type = "{value}"\n')
    return root


@pytest.fixture
def plugin_env(monkeypatch: pytest.MonkeyPatch) -> Path:
    """The clean layout's plugin, the kit itself (which ships no derived file), by the variable."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(KIT_ROOT))
    return KIT_ROOT


@pytest.mark.parametrize("layout", ["installed", "plugin"])
def test_ac8_a_derived_playbook_named_in_the_line_is_selected(tmp_path, plugin_env, layout):
    """REQ-055 AC8: SPEC-0048 rule 22 (the owner's line selects the project's derived playbook)."""
    import check_playbooks
    import engines

    root = derived_project(tmp_path / "project", layout)
    own = root / "config" / "playbooks" / f"{DERIVED}.toml"
    assert playbook_format.declaration(root) == (DERIVED, [])
    assert playbook_format.selected(root) == own
    assert playbook_format.folder(root, DERIVED) == root / "config" / "playbooks"
    assert check_playbooks.findings(root, [own]) == []
    proc = check(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines()[0].startswith("ok playbooks (")
    asked = engines.playbook_questions(root, None)
    data = tomllib.loads(own.read_text(encoding="utf-8"))
    assert asked and [q for _, q in asked] == [row["text"] for row in data["discovery"]]


@pytest.mark.parametrize("layout", ["installed", "plugin"])
def test_ac8_doctor_line_names_the_derived_playbook(tmp_path, plugin_env, layout):
    """REQ-055 AC8: SPEC-0048 rule 22 (doctor's line names the derived playbook, both layouts)."""
    root = derived_project(tmp_path / "project", layout)
    assert doctor.work_type_line(root) == (DERIVED_LINE, False)


def test_ac8_doctor_run_names_the_derived_playbook(tmp_path):
    """REQ-055 AC8: SPEC-0048 rule 22 (a doctor run prints the line and fails no work type)."""
    made = derived_project(tmp_path / "scratch", "installed")
    dirs = doctor_target(tmp_path, f'\n[delivery]\nwork_type = "{DERIVED}"\n')
    root = dirs["tree"]
    for rel in (f"config/playbooks/{DERIVED}.toml", f"docs/research/{DERIVED}.md"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(made / rel, root / rel)
    proc = run_doctor(dirs)
    lines = proc.stdout.splitlines()
    assert DERIVED_LINE in lines, proc.stdout
    assert not [ln for ln in lines if ln.startswith("FAIL work type")], proc.stdout


@pytest.mark.parametrize("layout", ["installed", "plugin"])
@pytest.mark.parametrize(
    ("case", "line"),
    [
        ("file-missing", MISSING_LINE),
        ("record-missing", UNKNOWN_LINE),
        ("default", UNKNOWN_LINE),
        ("Orders", UNKNOWN_LINE),
        ("ord_ers", UNKNOWN_LINE),
        ("ord ers", UNKNOWN_LINE),
        ("../x", UNKNOWN_LINE),
        ("web-ap", UNKNOWN_LINE),
    ],
)
def test_ac8_a_bad_derived_declaration_is_refused_naming_the_setting(
    tmp_path, plugin_env, layout, case, line
):
    """REQ-055 AC8: SPEC-0038 rule 5 and SPEC-0048 rules 21 and 22 (refused, never the value)."""
    value = DERIVED if case in ("file-missing", "record-missing") else case
    root = derived_project(tmp_path / "project", layout, value, write=case != "file-missing")
    if case == "record-missing":
        (root / "docs" / "research" / f"{DERIVED}.md").unlink()
    assert playbook_format.declaration(root) == (None, [line])
    assert playbook_format.selected(root) is None
    proc = check(root)
    assert proc.returncode == 1
    assert f"FAIL playbooks: {line}" in proc.stdout.splitlines(), proc.stdout
    # the declaration's line never names the value (a playbook file's own line names its path)
    assert all(value not in ln for ln in proc.stdout.splitlines() if "agk.toml" in ln)


def test_ac8_a_clean_project_never_reads_a_derived_name_from_the_plugin(tmp_path, monkeypatch):
    """REQ-055 AC8: SPEC-0048 rule 22 and Q-DP-2 (a derived playbook is the project's alone)."""
    made = derived_project(tmp_path / "scratch", "installed")
    text = (made / "config" / "playbooks" / f"{DERIVED}.toml").read_text(encoding="utf-8")
    plugin = stub_plugin(tmp_path / "plugin", {DERIVED: text})
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin))
    root = derived_project(tmp_path / "project", "plugin", write=False)
    assert playbook_format.declaration(root) == (None, [MISSING_LINE])
    assert playbook_format.folder(root, DERIVED) == root / "config" / "playbooks"


def test_ac8_the_check_and_the_selection_accept_the_same_names(tmp_path, plugin_env):
    """REQ-055 AC8: brief #1908 answer 8 (`problems` and `declaration` cannot disagree)."""
    root = derived_project(tmp_path / "project", "installed")
    books = root / "config" / "playbooks"
    for name in ("web-app", DERIVED, "default", "web-ap"):
        text = (books / f"{name if name != 'web-ap' else 'web-app'}.toml").read_text("utf-8")
        target = books / f"{name}.toml"
        if name == "web-ap":
            target.write_text(
                text.replace('work_type = "web-app"', 'work_type = "web-ap"'), "utf-8"
            )
        agk = (root / "agk.toml").read_text(encoding="utf-8").split("\n[delivery]")[0]
        (root / "agk.toml").write_text(agk + f'\n[delivery]\nwork_type = "{name}"\n', "utf-8")
        checked = not any(
            "is not one of the work types" in p for p in playbook_format.problems(target, root)
        )
        selected = playbook_format.declaration(root)[0] == name
        assert checked == selected or name == "default", name
        assert selected == (name in ("web-app", DERIVED)), name
