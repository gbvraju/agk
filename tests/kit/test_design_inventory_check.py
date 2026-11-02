"""Tests of the inventory check (SPEC-0037 rule 3; REQ-044 AC2, brief #456).

`scripts/agk/design_inventory.py` (installed, imported by `check_design.py`) holds
`inventory_problems(root)`: a filled `docs/design/inventory.md` passes, and an empty slot, a
requirement left out or with neither a screen nor a `no screen:` reason, a screen named with no
section, a pattern that is not the standard's, a link to an unknown screen and a screen without
`default` or a required state each fail as `rule 3: docs/design/inventory.md: <screen or REQ id>:
<what>`, naming the rule and the screen and never a value. `check_design.py` runs it when the file
exists. Invented data only, in `tmp_path`; files only, no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

try:
    import design_inventory as di  # noqa: E402
except ImportError:  # before the module exists every test fails, not the collection
    di = None

CHECK = KIT_ROOT / "scripts" / "agk" / "check_design.py"
MODULE = KIT_ROOT / "scripts" / "agk" / "design_inventory.py"
INVENTORY = "docs/design/inventory.md"
WHERE = f"rule 3: {INVENTORY}"

REQUIREMENTS = """# Requirements

### REQ-001 — A reader keeps a list of books

- Acceptance: AC1 a reader adds a book
- Status: planned

### REQ-002 — A nightly job tidies the list

- Acceptance: AC1 the job removes duplicates
- Status: planned
"""

STATES = """- State default: yes
- State empty: yes
- State loading: yes
- State error: yes
- State no-permission: n/a: every reader may see their own list
- State long-content: yes
- State success: yes"""

INVENTORY_TEXT = f"""# Design inventory

The screens and states of the product, from the requirements and specs only.

## Requirements

### REQ-001 — A reader keeps a list of books

- Specs: SPEC-0001
- Screens: books, book-detail

### REQ-002 — A nightly job tidies the list

- Specs: SPEC-0002
- Screens: no screen: the job runs without a person and shows nothing

## Screens

### books

- Flow: keep a list
- Pattern: list with filter and sort
- Links to: book-detail
{STATES}
- State archived: yes

### book-detail

- Flow: keep a list
- Pattern: detail
- Links to: books
{STATES}
"""


def project(root: Path, inventory: str = INVENTORY_TEXT) -> Path:
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "requirements.md").write_text(REQUIREMENTS, encoding="utf-8")
    (root / INVENTORY).write_text(inventory, encoding="utf-8")
    return root


def problems(root: Path) -> list[str]:
    assert di is not None, "scripts/agk/design_inventory.py is missing"
    return di.inventory_problems(root)


def check(root: Path):
    return subprocess.run(  # nosec B603 - a fixed argument list, no shell
        [sys.executable, str(CHECK), "--root", str(root)], capture_output=True, text=True
    )


def test_ac2_a_filled_inventory_passes(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (every requirement mapped, every screen with its states)."""
    project(tmp_path)
    assert problems(tmp_path) == []


def test_ac2_a_screen_that_links_nowhere_reads_none(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (Q-456-11: `- Links to: none`, never an empty slot)."""
    project(tmp_path, INVENTORY_TEXT.replace("- Links to: books\n", "- Links to: none\n", 1))
    assert problems(tmp_path) == []


def test_ac2_the_template_holds_every_field_the_check_reads():
    """REQ-044 AC2: SPEC-0037 rule 3 (the template and the installed check agree on the shape)."""
    assert di is not None, "scripts/agk/design_inventory.py is missing"
    text = (KIT_ROOT / "kit" / "templates" / "design-inventory.md").read_text(encoding="utf-8")
    for part in di.PARTS:
        assert f"\n## {part}\n" in text, part
    for field in (*di.REQ_FIELDS, *di.SCREEN_FIELDS, "State default"):
        assert f"- {field}:" in text, field


def test_ac2_check_design_passes_a_filled_inventory_with_no_theme(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (`check_design.py` reads the inventory when it exists)."""
    project(tmp_path)
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.strip().splitlines()[-1] == "ok design"


def test_ac2_check_design_without_an_inventory_is_unchanged(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (no inventory, no design record, as before)."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "requirements.md").write_text(REQUIREMENTS, encoding="utf-8")
    proc = check(tmp_path)
    assert proc.returncode == 0
    assert "ok design (no design record)" in proc.stdout


# (name, change to the filled inventory, the problem expected, a value that must not appear)
BROKEN = [
    (
        "empty-flow-slot",
        ("- Flow: keep a list\n- Pattern: detail", "- Flow:\n- Pattern: detail"),
        f"{WHERE}: book-detail: the slot Flow is empty",
        None,
    ),
    (
        "empty-specs-slot",
        ("- Specs: SPEC-0002", "- Specs:"),
        f"{WHERE}: REQ-002: the slot Specs is empty",
        None,
    ),
    (
        "empty-state-slot",
        ("- State archived: yes", "- State archived:"),
        f"{WHERE}: books: the slot State archived is empty",
        None,
    ),
    (
        "requirement-left-out",
        (
            "### REQ-002 — A nightly job tidies the list\n\n- Specs: SPEC-0002\n"
            "- Screens: no screen: the job runs without a person and shows nothing\n",
            "",
        ),
        f"{WHERE}: REQ-002: the requirement has no section",
        None,
    ),
    (
        "no-screen-without-reason",
        (
            "- Screens: no screen: the job runs without a person and shows nothing",
            "- Screens: no screen:",
        ),
        f"{WHERE}: REQ-002: the requirement has neither a screen nor a no-screen reason",
        None,
    ),
    (
        "screens-line-missing",
        ("- Screens: no screen: the job runs without a person and shows nothing\n", ""),
        f"{WHERE}: REQ-002: the requirement has neither a screen nor a no-screen reason",
        None,
    ),
    (
        "screen-without-section",
        ("- Screens: books, book-detail", "- Screens: books, book-detail, zz-hidden-screen"),
        f"{WHERE}: REQ-001: a screen it names has no section",
        "zz-hidden-screen",
    ),
    (
        "unknown-pattern",
        ("- Pattern: detail", "- Pattern: zz carousel of doom"),
        f"{WHERE}: book-detail: the pattern is not one of the standard's",
        "zz carousel",
    ),
    (
        "link-to-unknown-screen",
        ("- Links to: books\n", "- Links to: books, zz-nowhere\n"),
        f"{WHERE}: book-detail: a link names no screen of the inventory",
        "zz-nowhere",
    ),
    (
        "missing-default-state",
        (
            "### book-detail\n\n- Flow: keep a list\n- Pattern: detail\n- Links to: books\n"
            "- State default: yes\n",
            "### book-detail\n\n- Flow: keep a list\n- Pattern: detail\n- Links to: books\n",
        ),
        f"{WHERE}: book-detail: the state default is missing",
        None,
    ),
]


def _missing_required_state() -> str:
    """The filled inventory with `loading` taken out of the books screen only."""
    head, tail = INVENTORY_TEXT.split("### book-detail", 1)
    return head.replace("- State loading: yes\n", "", 1) + "### book-detail" + tail


@pytest.mark.parametrize("case", BROKEN, ids=lambda c: c[0])
def test_ac2_a_broken_inventory_fails_naming_the_rule_and_the_screen(tmp_path, case):
    """REQ-044 AC2: SPEC-0037 rule 3 (each failure names the rule and the screen, no value)."""
    _, (old, new), expected, value = case
    assert old in INVENTORY_TEXT, old
    project(tmp_path, INVENTORY_TEXT.replace(old, new, 1))
    found = problems(tmp_path)
    assert expected in found, found
    if value is not None:
        assert not any(value in p for p in found), found


def test_ac2_a_screen_missing_a_required_state_fails(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (a required state is listed or `n/a: <reason>`)."""
    project(tmp_path, _missing_required_state())
    assert problems(tmp_path) == [f"{WHERE}: books: the state loading is missing"]


@pytest.mark.parametrize(
    "line,expected",
    [
        ("- State error: maybe later", "books: the state error is not yes or n/a: <reason>"),
        ("- State error: n/a:", "books: the state error is not yes or n/a: <reason>"),
        ("- State zz-custom: perhaps", "books: a state is not yes or n/a: <reason>"),
    ],
)
def test_ac2_a_state_is_yes_or_not_applicable_with_a_reason(tmp_path, line, expected):
    """REQ-044 AC2: SPEC-0037 rule 3 (`n/a: <reason>`, never a bare n/a; no value named)."""
    head, tail = INVENTORY_TEXT.split("### book-detail", 1)
    old = "- State error: yes" if "State error" in line else "- State archived: yes"
    project(tmp_path, head.replace(old, line, 1) + "### book-detail" + tail)
    found = problems(tmp_path)
    assert f"{WHERE}: {expected}" in found, found
    assert not any("maybe later" in p or "perhaps" in p for p in found)


def test_ac2_a_section_for_no_requirement_fails(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (Q-456-9: a stale requirement section fails)."""
    text = INVENTORY_TEXT.replace(
        "## Screens", "### REQ-099 — Gone\n\n- Specs: none\n- Screens: books\n\n## Screens", 1
    )
    project(tmp_path, text)
    assert problems(tmp_path) == [f"{WHERE}: REQ-099: the section names no requirement"]


def test_ac2_a_screen_id_that_is_not_a_slug_fails_without_the_id(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (a screen id is a lower-case slug)."""
    text = INVENTORY_TEXT.replace("### book-detail", "### Book Detail ZZ", 1).replace(
        "book-detail", "Book Detail ZZ"
    )
    project(tmp_path, text)
    found = problems(tmp_path)
    assert f"{WHERE}: a screen id is not a lower-case slug" in found, found
    assert not any("ZZ" in p for p in found)


def test_ac2_a_screen_listed_twice_fails(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (one entry for each screen)."""
    tail = INVENTORY_TEXT.split("### book-detail", 1)[1]
    project(tmp_path, INVENTORY_TEXT + "\n### book-detail" + tail)
    assert f"{WHERE}: book-detail: the screen has more than one section" in problems(tmp_path)


def test_ac2_a_missing_part_fails(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (the inventory has its two parts)."""
    project(tmp_path, INVENTORY_TEXT.replace("## Screens", "## Pages", 1))
    found = problems(tmp_path)
    assert f"{WHERE}: the inventory has no Screens part" in found, found


def test_ac2_a_field_the_shape_does_not_have_fails(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (the template fixes the fields; Q-456-10)."""
    project(
        tmp_path, INVENTORY_TEXT.replace("- Pattern: detail", "- Pattern: detail\n- Mood: calm")
    )
    found = problems(tmp_path)
    assert f"{WHERE}: book-detail: a line is not a field of the inventory" in found, found
    assert not any("calm" in p for p in found)


def test_ac2_check_design_fails_a_broken_inventory_with_the_rule_and_the_screen(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (`check_design.py` fails it and names no value)."""
    project(tmp_path, INVENTORY_TEXT.replace("- Pattern: detail", "- Pattern: zz carousel", 1))
    proc = check(tmp_path)
    assert proc.returncode == 1
    assert (
        f"FAIL design: {WHERE}: book-detail: the pattern is not one of the standard's"
        in proc.stdout
    )
    assert "zz carousel" not in proc.stdout


def test_ac2_the_inventory_module_is_installed_in_sorted_order():
    """REQ-044 AC2: SPEC-0037 rule 14 (b) (a module the installed check imports is verbatim)."""
    verbatim = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text())["verbatim"]
    assert "scripts/agk/design_inventory.py" in verbatim
    assert verbatim == sorted(verbatim)


def test_ac2_the_inventory_check_reads_files_only():
    """REQ-044 AC2: SPEC-0037 rule 13 (no network from a design check; nothing written)."""
    source = MODULE.read_text(encoding="utf-8")
    for word in (
        "socket",
        "urllib",
        "http.client",
        "requests",
        "subprocess",
        "write_text",
        "open(",
    ):
        assert word not in source, word
