"""Tests of the parts catalogue check (SPEC-0076 rules 4 and 5; REQ-083 AC1; brief #2068,
ADR-0858).

`check_parts_catalogue.findings(root, files, stacks)` checks the needs catalogue
(`config/parts/needs.toml`) and each stack catalogue (`config/parts/<stack>.toml`) of the layers it
is given, kit first, then each pack in use, then the project's own. Each problem is one line,
`rule 4|5: <path class>: <what> (key: <key>)`, never a value; `check_playbooks.findings` adds the
lines, so the `playbooks` step prints them as `FAIL playbooks:`. Fixtures in `tmp_path` only:
invented data (`example.com`), no network, no model.
"""

from __future__ import annotations

import ast
import subprocess  # nosec B404 - the check run alone, fixed argument lists
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_parts_catalogue as cpc  # noqa: E402
import check_playbooks  # noqa: E402
import packs  # noqa: E402
import playbook_format  # noqa: E402

RULE4 = "rule 4: config/parts/needs.toml"
RULE5 = "rule 5: config/parts/node.toml"
STACKS = ["node", "python-pyproject"]
SPEC_IDS = (
    "web-api http-client validation data-access migrations auth config secrets logging telemetry "
    "jobs email payments files cache time money i18n ui-components routing state forms "
    "accessibility unit-tests contract-tests e2e-tests lint format"
).split()
NEEDS = """format = 1

[[needs]]
id = "web-api"
text = "Serve requests over HTTP"
signals = ["an app others call"]

[[needs]]
id = "forms"
text = "Take input from people"
signals = ["a sign-up page"]
"""
ROW = """
[[parts]]
need = "web-api"
name = "zz-server"
pick = "recommended"
when = "a small service"
trade_offs = "few features"
licence = "MIT"
source = "https://example.com/zz-server (accessed 2026-11-20)"
reviewed = "2026-11-21"
"""
STACK = "format = 1\n" + ROW


def tree(root: Path, needs: str = NEEDS, stack: str | None = STACK, name: str = "node") -> Path:
    parts = root / "config" / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    (parts / "needs.toml").write_text(needs, encoding="utf-8")
    if stack is not None:
        (parts / f"{name}.toml").write_text(stack, encoding="utf-8")
    return parts


def check(root: Path, stacks: list[str] | None = STACKS) -> list[str]:
    parts = root / "config" / "parts"
    files = [(packs.CORE, path) for path in sorted(parts.glob("*.toml"))]
    return cpc.findings(root, files, stacks)


def row(**change: str | None) -> str:
    """ROW with each key of CHANGE set to its (TOML) text, or removed when None."""
    lines = []
    for line in ROW.strip().splitlines():
        key = line.split(" = ")[0]
        if key in change:
            if change[key] is not None:
                lines.append(f"{key} = {change.pop(key)}")
            else:
                change.pop(key)
            continue
        lines.append(line)
    lines += [f"{k} = {v}" for k, v in change.items() if v is not None]
    return "\n" + "\n".join(lines) + "\n"


# --- the shipped needs catalogue -----------------------------------------------------------------


def test_ac1_the_shipped_needs_catalogue_passes_and_holds_the_spec_ids():
    """REQ-083 AC1: SPEC-0076 rule 4 (the 28 needs, no library, no version)."""
    path = KIT_ROOT / "config" / "parts" / "needs.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    ids = [n["id"] for n in data["needs"]]
    assert set(SPEC_IDS) <= set(ids) and len(ids) == len(set(ids))
    assert all(set(n) == {"id", "text", "signals"} and n["signals"] for n in data["needs"])
    assert cpc.findings(KIT_ROOT, [(packs.CORE, path)], STACKS) == []
    assert packs.files(KIT_ROOT, "parts") == [(packs.CORE, path)]


def test_ac1_the_kit_tree_passes_the_playbooks_step():
    """REQ-083 AC1: SPEC-0076 rule 5 (the kit's own catalogue passes inside the step)."""
    assert not [line for line in check_playbooks.findings(KIT_ROOT) if "config/parts" in line]


def test_ac1_a_good_tree_has_no_finding_and_no_folder_none(tmp_path):
    """REQ-083 AC1: SPEC-0076 rule 5 (a good catalogue, an empty one and no folder)."""
    assert cpc.findings(tmp_path, [], STACKS) == []
    tree(tmp_path)
    assert check(tmp_path) == []
    tree(tmp_path, stack="format = 1\n")
    assert check(tmp_path) == []  # a stack catalogue with no rows


# --- the needs catalogue (rule 4) ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("needs", "line"),
    [
        ("format = [", "the file is not TOML (key: file)"),
        ('format = 2\n[[needs]]\nid = "a"\ntext = "t"\nsignals = ["s"]\n', "format is not 1 (key: format)"),
        ('format = true\n', "format is not 1 (key: format)"),
        ('[[needs]]\nid = "a"\ntext = "t"\nsignals = ["s"]\n', "a key is missing (key: format)"),
        ("format = 1\nzz_extra = 1\n", "a key is unknown (key: zz_extra)"),
        ('format = 1\nneeds = "zz"\n', "a value has the wrong type (key: needs)"),
        ('format = 1\n[[needs]]\nid = "a"\ntext = "t"\n', "a key is missing (key: needs.signals)"),
        (
            'format = 1\n[[needs]]\nid = "a"\ntext = "t"\nsignals = ["s"]\nzz = 1\n',
            "a key is unknown (key: needs.zz)",
        ),
        ('format = 1\n[[needs]]\nid = "Zz A"\ntext = "t"\nsignals = ["s"]\n', "a value is out of form (key: needs.id)"),
        ('format = 1\n[[needs]]\nid = "a"\ntext = 1\nsignals = ["s"]\n', "a value has the wrong type (key: needs.text)"),
        ('format = 1\n[[needs]]\nid = "a"\ntext = "t\\nu"\nsignals = ["s"]\n', "a value is out of form (key: needs.text)"),
        ('format = 1\n[[needs]]\nid = "a"\ntext = "t"\nsignals = []\n', "a value has the wrong type (key: needs.signals)"),
        ('format = 1\n[[needs]]\nid = "a"\ntext = "t"\nsignals = [true]\n', "a value has the wrong type (key: needs.signals)"),
        (
            'format = 1\n[[needs]]\nid = "a"\ntext = "t"\nsignals = ["s"]\n'
            '[[needs]]\nid = "a"\ntext = "u"\nsignals = ["v"]\n',
            "a need id is used twice (key: needs.id)",
        ),
    ],
)
def test_ac1_a_needs_catalogue_out_of_form_fails_naming_the_key(tmp_path, needs, line):
    """REQ-083 AC1: SPEC-0076 rule 4 (each problem names the rule, the file and the key)."""
    tree(tmp_path, needs=needs, stack=None)
    assert f"{RULE4}: {line}" in check(tmp_path)


def test_ac1_a_need_id_repeated_by_another_layer_fails(tmp_path):
    """REQ-083 AC1: SPEC-0076 rule 4 (a project's or a pack's needs join the kit's)."""
    kit = tree(tmp_path / "kit", stack=None) / "needs.toml"
    own = tree(tmp_path / "own", stack=None) / "needs.toml"
    found = cpc.findings(tmp_path, [(packs.CORE, kit), (packs.PROJECT, own)], STACKS)
    assert found == [f"{RULE4}: a need id is used twice (key: needs.id)"]
    found = cpc.findings(tmp_path, [(packs.CORE, kit), ("zz-shop", own)], STACKS)
    assert found == ["rule 4: config/packs/zz-shop: a need id is used twice (key: needs.id)"]


# --- the stack catalogues (rule 5) ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("stack", "line"),
    [
        ("format = [", "the file is not TOML (key: file)"),
        ("format = 2\n", "format is not 1 (key: format)"),
        (ROW, "a key is missing (key: format)"),
        ("format = 1\nzz_extra = 1\n", "a key is unknown (key: zz_extra)"),
        ('format = 1\nparts = "zz"\n', "a value has the wrong type (key: parts)"),
        ("format = 1\n" + row(version='"1.2.3"'), "a row holds a version (key: parts.version)"),
        ("format = 1\n" + row(zz_other='"x"'), "a key is unknown (key: parts.zz_other)"),
        ("format = 1\n" + row(need='"zz-nothing"'), "a row names a need no needs id names (key: parts.need)"),
        ("format = 1\n" + row(pick='"zz-best"'), "a value is out of form (key: parts.pick)"),
        ("format = 1\n" + row(name="true"), "a value has the wrong type (key: parts.name)"),
        ("format = 1\n" + row(when="1"), "a value has the wrong type (key: parts.when)"),
        ("format = 1\n" + row(licence=None), "a key is missing (key: parts.licence)"),
        ("format = 1\n" + row(licence='"MIT OR zz bad"'), "a value is out of form (key: parts.licence)"),
        ("format = 1\n" + row(source=None), "a key is missing (key: parts.source)"),
        ("format = 1\n" + row(source='"https://example.com/zz"'), "a value is out of form (key: parts.source)"),
        (
            "format = 1\n" + row(source='"https://example.com/zz (accessed 2026-13-40)"'),
            "a value is out of form (key: parts.source)",
        ),
        ("format = 1\n" + row(reviewed=None), "a key is missing (key: parts.reviewed)"),
        ("format = 1\n" + row(reviewed='"2026-11"'), "a value is out of form (key: parts.reviewed)"),
        ("format = 1\n" + row(trade_offs=None), "a key is missing (key: parts.trade_offs)"),
        ("format = 1\n" + ROW + ROW.replace("zz-server", "zz-other"), "a need has more than one recommended row (key: parts.pick)"),
        (
            "format = 1\n"
            + ROW
            + "".join(row(name=f'"zz-alt-{n}"', pick='"alternative"') for n in range(3)),
            "a need has more than two alternative rows (key: parts.pick)",
        ),
        ("format = 1\n" + ROW + row(pick='"alternative"'), "a name is used twice for one need (key: parts.name)"),
    ],
)
def test_ac1_a_stack_catalogue_out_of_form_fails_naming_the_key(tmp_path, stack, line):
    """REQ-083 AC1: SPEC-0076 rule 5 (each problem names the rule, the file and the key)."""
    tree(tmp_path, stack=stack)
    found = check(tmp_path)
    assert f"{RULE5}: {line}" in found
    for value in ("zz-nothing", "zz-best", "1.2.3", "MIT OR", "2026-13-40", "example.com/zz"):
        assert all(value not in f for f in found)


def test_ac1_two_alternatives_and_a_stdlib_row_pass(tmp_path):
    """REQ-083 AC1: SPEC-0076 rules 4 and 5 (one recommended, two alternatives; `stdlib`)."""
    alts = "".join(row(name=f'"zz-alt-{n}"', pick='"alternative"') for n in range(2))
    stdlib = row(need='"forms"', name='"stdlib"', licence='"PSF-2.0"')
    tree(tmp_path, stack="format = 1\n" + ROW + alts + stdlib)
    assert check(tmp_path) == []


def test_ac1_a_file_naming_no_stack_fails_and_other_files_are_not_read(tmp_path):
    """REQ-083 AC1: SPEC-0076 rule 5 (one stack catalogue per stack name)."""
    tree(tmp_path, name="zz-cobol")
    assert check(tmp_path) == [
        "rule 5: config/parts/zz-cobol.toml: the file names no stack (key: file)"
    ]
    assert check(tmp_path, None) == check(tmp_path)  # no stack list: no name is known
    (tmp_path / "config" / "parts" / "notes.md").write_text("zz\n", encoding="utf-8")
    assert len(check(tmp_path)) == 1


def test_ac1_the_source_pattern_is_the_gates_one():
    """REQ-083 AC1: SPEC-0076 rule 5 (a URL and access date, as `playbook_format.GATE_SOURCE`)."""
    assert cpc.SOURCE.pattern == playbook_format.GATE_SOURCE.pattern


def test_ac1_the_script_imports_only_the_standard_library_and_common():
    """REQ-083 AC1: SPEC-0076 rule 5 (standard library and `common.py` only; `Q-PA-4`)."""
    text = (KIT_ROOT / "scripts" / "agk" / "check_parts_catalogue.py").read_text(encoding="utf-8")
    names = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
    assert names - set(sys.stdlib_module_names) == {"common"}


# --- the reading order and the playbooks step ----------------------------------------------------


def test_ac1_the_project_folder_is_read_after_the_kit_in_the_clean_layout(tmp_path, monkeypatch):
    """REQ-083 AC1: SPEC-0076 rule 5 with SPEC-0077 rule 5 (kit first, the project's last)."""
    kit = tree(tmp_path / "kit", stack=None) / "needs.toml"
    own = tree(tmp_path / "own") / "node.toml"
    monkeypatch.setattr(packs.kit_root, "kit_file", lambda root, rel: kit.parent)
    found = packs.files(tmp_path / "own", "parts")
    assert found[0] == (packs.CORE, kit)
    assert (packs.PROJECT, own) in found and found.index((packs.PROJECT, own)) > 0


def test_ac1_the_playbooks_step_carries_a_catalogue_problem(tmp_path):
    """REQ-083 AC1: SPEC-0076 rule 5 (`check_playbooks.findings` runs the check)."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "stack-signals.toml").write_text(
        '[[stack]]\nname = "node"\nfiles = ["package.json"]\n', encoding="utf-8"
    )
    tree(tmp_path, stack="format = 1\n" + row(version='"1.2.3"'))
    line = f"{RULE5}: a row holds a version (key: parts.version)"
    assert line in check_playbooks.findings(tmp_path)
    assert check_playbooks.findings(tmp_path, []) == []  # a named playbook alone reads no catalogue
    proc = subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(KIT_ROOT / "scripts/agk/check_playbooks.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1 and f"FAIL playbooks: {line}" in proc.stdout


def test_ac1_run_alone_the_check_counts_needs_and_catalogues(tmp_path):
    """REQ-083 AC1: SPEC-0076 rule 5 (`--root DIR` reads `DIR/config/parts/` only)."""
    script = str(KIT_ROOT / "scripts/agk/check_parts_catalogue.py")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "stack-signals.toml").write_text(
        '[[stack]]\nname = "node"\n', encoding="utf-8"
    )
    tree(tmp_path)

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(  # nosec B603 - fixed argument list
            [sys.executable, script, *args], capture_output=True, text=True, check=False
        )

    proc = run("--root", str(tmp_path))
    assert proc.returncode == 0 and proc.stdout == "ok parts-catalogue (2 needs, 1 stack catalogues)\n"
    tree(tmp_path, stack="format = 1\n" + row(version='"1.2.3"'))
    proc = run("--root", str(tmp_path))
    assert proc.returncode == 1
    assert proc.stdout == f"FAIL parts-catalogue: {RULE5}: a row holds a version (key: parts.version)\n"
    assert run("--zz").returncode == 2


def test_ac1_the_class_stays_closed():
    """REQ-083 AC1: SPEC-0076 rule 17 (the step calls the check; no kit row holds a version)."""
    text = (KIT_ROOT / "scripts" / "agk" / "check_playbooks.py").read_text(encoding="utf-8")
    assert "check_parts_catalogue.findings(" in text
    assert packs.KIT["parts"] == "config/parts"
    for path in (KIT_ROOT / "config" / "parts").glob("*.toml"):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        assert all("version" not in r for r in data.get("parts", []))
