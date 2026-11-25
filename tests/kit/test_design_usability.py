"""Tests of the usability record (SPEC-0073 rule 8; SPEC-0038 rule 10 and SPEC-0037 rule 7 by
amendment 237; REQ-080 AC5; brief #1953, ADR-0809).

`scripts/agk/design_usability.py` (installed, imported by `check_design.py`) reads
`docs/design/usability.md` when the declared `[delivery] work_type` is `web-app` or `mobile`: each
screen of the inventory lists the ten usability heuristics for the newest prototype or imported
version, each `pass`, `finding: <text>` or `not applicable: <reason>`. A missing record, section,
screen or heuristic fails naming `SPEC-0038 rule 10`, the version and the screen, never a finding's
text; any other work type reads `design: usability not applicable (work type)`. Invented data only,
in `tmp_path`; files only, no network.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

try:
    import design_usability as du  # noqa: E402
except ImportError:  # before the module exists every test fails, not the collection
    du = None

CHECK = KIT_ROOT / "scripts" / "agk" / "check_design.py"
RECORD = "docs/design/usability.md"
TEMPLATE = KIT_ROOT / "kit" / "templates" / "usability.md"
TEN = (
    "status",
    "real-world",
    "control",
    "consistency",
    "error-prevention",
    "recognition",
    "flexibility",
    "minimal",
    "error-recovery",
    "help",
)
FINDING = "the-checkout-button-hides-under-the-fold-example"

INVENTORY = """# Design inventory

## Requirements

### REQ-001 — A reader keeps a list of books

- Specs: SPEC-0001
- Screens: books, book-detail

## Screens

### books

- Flow: keep a list
- Pattern: list with filter and sort
- Links to: book-detail
- State default: yes

### book-detail

- Flow: keep a list
- Pattern: detail
- Links to: books
- State default: yes
"""


def lines(values: dict[str, str] | None = None) -> str:
    values = values or {}
    return "\n".join(f"- {h}: {values.get(h, 'pass')}" for h in TEN if values.get(h) != "-")


def record(sections: dict[str, dict[str, str]], version: str = "v1") -> str:
    body = "\n\n".join(f"### {screen}\n\n{text}" for screen, text in sections.items())
    return f"# Usability\n\n## {version}\n\n{body}\n"


FULL = record({"books": lines(), "book-detail": lines({"help": f"finding: {FINDING}"})})


def project(root: Path, work_type: str | None = "web-app", usability: str | None = FULL) -> Path:
    (root / "docs" / "design" / "prototype" / "v1").mkdir(parents=True)
    (root / "docs" / "design" / "prototype" / "v1" / "README.md").write_text("# v1\n", "utf-8")
    (root / "docs" / "design" / "inventory.md").write_text(INVENTORY, encoding="utf-8")
    if work_type is not None:
        (root / "agk.toml").write_text(f'[delivery]\nwork_type = "{work_type}"\n', "utf-8")
        shipped = KIT_ROOT / "config" / "playbooks" / f"{work_type}.toml"
        if shipped.is_file():
            (root / "config" / "playbooks").mkdir(parents=True)
            shutil.copy(shipped, root / "config" / "playbooks" / shipped.name)
    if usability is not None:
        (root / RECORD).write_text(usability, encoding="utf-8")
    return root


def problems(root: Path) -> list[str]:
    assert du is not None, "scripts/agk/design_usability.py is missing"
    return du.problems(root)


def run_check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list
        [sys.executable, str(CHECK), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_ac5_the_ten_heuristics_are_one_tuple_the_template_lists():
    """REQ-080 AC5: brief #1953 answers 1 and 9 (one tuple, read by the template test)."""
    assert du is not None
    assert du.HEURISTICS == TEN
    text = TEMPLATE.read_text(encoding="utf-8")
    assert re.findall(r"(?m)^- ([a-z-]+): ", text) == list(TEN)


def test_ac5_the_screen_work_types_are_the_playbooks_that_hold_a_design():
    """REQ-080 AC5: brief #1953 answer 9 (a new screen work type without the record fails here):
    the work types whose playbook names the screen inventory or SPEC-0037's design checks."""
    assert du is not None
    found = []
    for path in sorted((KIT_ROOT / "config" / "playbooks").glob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        text = " ".join([*data.get("evidence", [])] + [g["text"] for g in data.get("gates", [])])
        if "screen inventory" in text or "SPEC-0037" in text:
            found.append(data["work_type"])
    assert sorted(found) == sorted(du.SCREEN_WORK_TYPES) == ["mobile", "web-app"]


@pytest.mark.parametrize("work_type", ["web-app", "mobile"])
def test_ac5_a_full_record_passes(tmp_path, work_type):
    """REQ-080 AC5: all ten lines per screen pass; a `finding:` never fails by itself."""
    assert problems(project(tmp_path, work_type)) == []


@pytest.mark.parametrize("work_type", ["web-app", "mobile"])
def test_ac5_no_record_fails(tmp_path, work_type):
    """REQ-080 AC5: SPEC-0038 rule 10 (a web or mobile screen with no usability record)."""
    found = problems(project(tmp_path, work_type, usability=None))
    assert found == [f"SPEC-0038 rule 10: {RECORD}: v1: the usability record is missing"]


def test_ac5_a_missing_version_section_fails(tmp_path):
    """REQ-080 AC5: the newest version needs its section; an older one is read for form only."""
    found = problems(project(tmp_path, usability=FULL.replace("## v1", "## v0")))
    assert f"SPEC-0038 rule 10: {RECORD}: v1: the version has no section" in found


def test_ac5_a_missing_screen_fails(tmp_path):
    """REQ-080 AC5: a screen of the inventory with no `###` section fails naming it."""
    found = problems(project(tmp_path, usability=record({"books": lines()})))
    assert found == [f"SPEC-0038 rule 10: {RECORD}: v1: book-detail: the screen has no section"]


def test_ac5_a_missing_or_twice_heuristic_fails(tmp_path):
    """REQ-080 AC5: a heuristic missing, twice or not one of the ten fails naming the screen."""
    missing = record({"books": lines({"help": "-"}), "book-detail": lines()})
    assert problems(project(tmp_path / "a", usability=missing)) == [
        f"SPEC-0038 rule 10: {RECORD}: v1: books: the heuristic help is missing"
    ]
    twice = record({"books": lines() + "\n- help: pass", "book-detail": lines()})
    assert problems(project(tmp_path / "b", usability=twice)) == [
        f"SPEC-0038 rule 10: {RECORD}: v1: books: the heuristic help is listed twice"
    ]
    extra = record({"books": lines() + "\n- delight: pass", "book-detail": lines()})
    assert problems(project(tmp_path / "c", usability=extra)) == [
        f"SPEC-0038 rule 10: {RECORD}: v1: books: a line is not one of the ten heuristics"
    ]


def test_ac5_a_value_outside_the_three_forms_or_with_no_text_fails(tmp_path):
    """REQ-080 AC5: `finding:` or `not applicable:` with no text, or another value, fails."""
    for name, value in (("a", "finding:"), ("b", "not applicable:"), ("c", "fine")):
        text = record({"books": lines({"status": value}), "book-detail": lines()})
        assert problems(project(tmp_path / name, usability=text)) == [
            f"SPEC-0038 rule 10: {RECORD}: v1: books: status is not pass, finding: <text> or"
            " not applicable: <reason>"
        ], value


def test_ac5_a_screen_the_inventory_does_not_hold_fails(tmp_path):
    """REQ-080 AC5: brief #1953 answer 2 (a screen id the inventory does not hold)."""
    text = record({"books": lines(), "book-detail": lines(), "basket": lines()})
    assert problems(project(tmp_path, usability=text)) == [
        f"SPEC-0038 rule 10: {RECORD}: v1: basket: the screen is not in the inventory"
    ]


def test_ac5_an_older_section_is_read_for_its_form_only(tmp_path):
    """REQ-080 AC5: Q-73I-1 (an older section missing a screen passes; a bad line in it fails)."""
    older = "## i1\n\n### books\n\n" + lines() + "\n\n"
    assert problems(project(tmp_path / "a", usability=FULL + "\n" + older)) == []
    bad = "## i1\n\n### books\n\n" + lines({"status": "fine"}) + "\n"
    assert problems(project(tmp_path / "b", usability=FULL + "\n" + bad)) == [
        f"SPEC-0038 rule 10: {RECORD}: i1: books: status is not pass, finding: <text> or"
        " not applicable: <reason>"
    ]


def test_ac5_crlf_is_read_the_same(tmp_path):
    """REQ-080 AC5: brief #1953 answer 7 (CRLF records read the same)."""
    root = project(tmp_path, usability=None)
    (root / RECORD).write_bytes(FULL.replace("\n", "\r\n").encode("utf-8"))
    assert problems(root) == []


@pytest.mark.parametrize("work_type", ["api-service", "pilot", None])
def test_ac5_a_screen_free_type_is_not_applicable(tmp_path, work_type):
    """REQ-080 AC5: SPEC-0073 rule 8 (a work type without screens, or none, is not checked)."""
    root = project(tmp_path, work_type, usability=None)
    assert problems(root) == []
    assert du.note(root) == "design: usability not applicable (work type)"
    result = run_check(root)
    assert result.stdout.count("design: usability not applicable (work type)") == 1
    assert "SPEC-0038 rule 10" not in result.stdout


def test_ac5_a_refused_work_type_fails_naming_the_setting(tmp_path):
    """REQ-080 AC5: brief #1953 answer 6 (refused as `playbook_format.declaration` refuses it)."""
    root = project(tmp_path, "desktop-app", usability=None)
    found = problems(root)
    assert len(found) == 1 and found[0].endswith("(setting: work_type)"), found
    assert "desktop-app" not in found[0]


def test_ac5_no_version_waits_for_a_prototype(tmp_path):
    """REQ-080 AC5: brief #1953 answer 7 (an inventory with no version needs no record yet)."""
    root = project(tmp_path, usability=None)
    shutil.rmtree(root / "docs" / "design" / "prototype")
    assert problems(root) == []
    assert du.note(root) == "design: usability waits for a prototype version"


def test_ac5_the_newest_version_is_the_kit_version_over_an_import(tmp_path):
    """REQ-080 AC5: brief #1953 answer 7 (an imported `i1` and a later `v1`: `v1` is checked)."""
    root = project(tmp_path, usability=None)
    (root / "docs" / "design" / "imported" / "i1").mkdir(parents=True)
    (root / "docs" / "design" / "imported" / "i1" / "map.md").write_text("# map\n", "utf-8")
    assert du.newest(root) == "v1"
    shutil.rmtree(root / "docs" / "design" / "prototype")
    assert du.newest(root) == "i1"


def test_ac5_the_design_check_fails_and_never_prints_a_finding(tmp_path):
    """REQ-080 AC5: `check_design.py` runs the check in its inventory branch; no line holds a
    finding's text (principle 8)."""
    missing = record({"books": lines(), "book-detail": lines({"help": f"finding: {FINDING}"})})
    root = project(tmp_path, usability=missing.replace("### books", "### basket"))
    result = run_check(root)
    assert result.returncode == 1
    assert f"FAIL design: SPEC-0038 rule 10: {RECORD}: v1: books: the screen has no section" in (
        result.stdout
    )
    assert FINDING not in result.stdout + result.stderr


# --- fix list 7175465393 (items 1 to 3) ---------------------------------------------------------


@pytest.mark.parametrize("work_type", ["web-app", "mobile"])
def test_ac5_each_screen_type_fails_a_missing_screen_heuristic_or_finding(tmp_path, work_type):
    """REQ-080 AC5: brief #1953 answer 8 (the mobile fixture as the web-app one): a missing
    screen, a missing heuristic and an empty `finding:` each fail naming the screen."""
    where = f"SPEC-0038 rule 10: {RECORD}: v1"
    cases = (
        (record({"books": lines()}), f"{where}: book-detail: the screen has no section"),
        (
            record({"books": lines({"help": "-"}), "book-detail": lines()}),
            f"{where}: books: the heuristic help is missing",
        ),
        (
            record({"books": lines({"status": "finding:"}), "book-detail": lines()}),
            f"{where}: books: status is not pass, finding: <text> or not applicable: <reason>",
        ),
    )
    for n, (text, line) in enumerate(cases):
        assert problems(project(tmp_path / str(n), work_type, usability=text)) == [line]


def test_ac5_a_record_that_is_not_utf8_fails_naming_the_path_class(tmp_path):
    """REQ-080 AC5: fix list item 1 (no traceback: the rule and the path class, never a value)."""
    root = project(tmp_path, usability=None)
    (root / RECORD).write_bytes(b"# Usability\n\n## v1\n\n\xff\xfe broken\n")
    assert problems(root) == [
        f"SPEC-0038 rule 10: {RECORD}: the record cannot be read as UTF-8 text"
        " (path class: docs/design/)"
    ]
    result = run_check(root)
    assert result.returncode == 1 and "Traceback" not in result.stderr, result.stderr
    assert "the record cannot be read as UTF-8 text" in result.stdout


def test_ac5_a_derived_playbook_is_not_applicable(tmp_path):
    """REQ-080 AC5: brief #1953 answer 6 (a derived playbook, SPEC-0048 rule 22, is not checked)."""
    root = project(tmp_path, "web-app", usability=None)
    (root / "agk.toml").write_text('[delivery]\nwork_type = "shop-pilot"\n', "utf-8")
    (root / "docs" / "research").mkdir(parents=True)
    (root / "docs" / "research" / "shop-pilot.md").write_text("# Research\n", "utf-8")
    shutil.copy(
        root / "config" / "playbooks" / "web-app.toml",
        root / "config" / "playbooks" / "shop-pilot.toml",
    )
    assert problems(root) == []
    assert du.note(root) == "design: usability not applicable (work type)"


def test_ac5_the_plugin_layout_reads_the_kit_roots_template(tmp_path, monkeypatch):
    """REQ-080 AC5: brief #1953 answer 6 (`[kit] layout = "plugin"`: the template from the kit
    root, the playbook from the plugin; installed: the project's own path), the check the same."""
    assert du is not None
    installed = project(tmp_path / "installed", usability=None)
    assert du.template(installed) == installed / "kit" / "templates" / "usability.md"
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(KIT_ROOT))
    root = project(tmp_path / "plugin", usability=None)
    shutil.rmtree(root / "config")
    (root / "agk.toml").write_text(
        '[kit]\nlayout = "plugin"\n\n[delivery]\nwork_type = "web-app"\n', "utf-8"
    )
    assert du.template(root) == TEMPLATE.resolve()
    assert problems(root) == [f"SPEC-0038 rule 10: {RECORD}: v1: the usability record is missing"]
    (root / RECORD).write_text(FULL, encoding="utf-8")
    assert problems(root) == []


def test_ac5_the_settings_it_does_not_read_change_nothing(tmp_path):
    """REQ-080 AC5: brief #1953 answer 6 (`execution`, `review_mode`, `pr_mode`, `[flow]`,
    `[steward]`, `[personal]` and `[quality]` are not read: the same result either way)."""
    plain = project(tmp_path / "plain", usability=record({"books": lines()}))
    other = project(tmp_path / "other", usability=record({"books": lines()}))
    (other / "agk.toml").write_text(
        'execution = "local"\nreview_mode = "solo"\npr_mode = "flow"\n\n'
        '[delivery]\nwork_type = "web-app"\n\n[flow]\nassign = "conductor"\n\n'
        "[steward]\nauto_file = 0\n\n[personal]\nforge = \"files\"\n\n"
        "[quality]\ngrill_hold = false\n",
        "utf-8",
    )
    assert problems(other) == problems(plain) != []
    assert du.note(other) == du.note(plain) is None
