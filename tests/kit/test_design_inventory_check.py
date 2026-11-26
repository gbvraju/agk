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


# Brief #1756 (amendment 217 to SPEC-0037 rule 3, ADR-0734): an empty screen list is refused when
# a discovery document says the work has screens; a milestone section of the idea path is checked.

KIT_ONLY = """# Design inventory

## Requirements

### REQ-001 — A reader keeps a list of books

- Specs: none
- Screens: no screen: a rule of the kit

### REQ-002 — A nightly job tidies the list

- Specs: none
- Screens: no screen: a rule of the kit

## Screens
"""

EMPTY_LIST = "SPEC-0037 rule 3: docs/design/: the inventory lists no screen"


def discovery(root: Path, name: str, screens: str) -> None:
    folder = root / "docs" / "discovery"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.md").write_text(
        f"# Discovery: {name}\n\n- Problem: in session 2026-11-22\n- Screens: {screens}\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("screens", ["yes", "open"])
def test_ac2_no_screen_with_discovery_screens_fails_naming_the_rule(tmp_path, screens):
    """REQ-044 AC2: SPEC-0037 rule 3 as amendment 217 proposes (brief #1756 answer 2)."""
    project(tmp_path, KIT_ONLY)
    discovery(tmp_path, "nightly", "no")
    discovery(tmp_path, "booking", screens)
    assert any(p.startswith(EMPTY_LIST) for p in problems(tmp_path)), problems(tmp_path)
    proc = check(tmp_path)
    assert proc.returncode == 1, proc.stdout
    assert f"FAIL design: {EMPTY_LIST}" in proc.stdout


def test_ac2_no_screen_passes_when_discovery_says_no_or_is_absent(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1756 answer 2: `Screens: no`, or none, as today)."""
    project(tmp_path, KIT_ONLY)
    assert problems(tmp_path) == []
    discovery(tmp_path, "nightly", "no")
    assert problems(tmp_path) == []
    assert check(tmp_path).returncode == 0


def test_ac2_a_quoted_screens_line_is_not_read(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (a person's quoted words are never the discovery answer)."""
    project(tmp_path, KIT_ONLY)
    folder = tmp_path / "docs" / "discovery"
    folder.mkdir(parents=True)
    (folder / "nightly.md").write_text(
        "# Discovery: nightly\n\n<!-- agk:problem sha256=" + "0" * 64 + " -->\n- Screens: yes\n"
        "<!-- agk:problem-end -->\n- Screens: no\n",
        encoding="utf-8",
    )
    assert problems(tmp_path) == []


def test_ac2_a_filled_milestone_section_passes_and_an_empty_one_fails(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1756 answer 1: a milestone section's slots)."""
    milestone = (
        "### M1 — a reader keeps a list. exit: 3 books are kept\n\n"
        "- Sources: docs/adr/0002-project-charter.md, docs/discovery/books.md\n"
        "- Screens: books, book-detail\n\n"
    )
    text = INVENTORY_TEXT.replace("## Screens\n", milestone + "## Screens\n", 1)
    project(tmp_path, text)
    discovery(tmp_path, "books", "yes")
    assert problems(tmp_path) == []
    project_empty = text.replace("- Screens: books, book-detail\n", "- Screens:\n")
    (tmp_path / INVENTORY).write_text(project_empty, encoding="utf-8")
    assert f"{WHERE}: M1: the slot Screens is empty" in problems(tmp_path)


# Brief #1779 (amendment 219 to SPEC-0037 rule 15, ADR-0745): a map that marks every page of an
# imported version `out` while the inventory has no screen is refused.


def imported_all_out(root: Path, pages=("home.html", "about.html")) -> None:
    import design_import

    files = root / "docs" / "design" / "imported" / "i1" / "files"
    files.mkdir(parents=True)
    for page in pages:
        (files / page).write_text(f"<html><body><p>{page} on example.com</p></body></html>")
    folder = files.parent
    (folder / "manifest.json").write_text(json.dumps(design_import.manifest(files)))
    (folder / "external.txt").write_text(design_import.external(design_import._files(files)))
    (folder / "map.md").write_text("".join(f"{p} -> out: not a screen\n" for p in pages))


NO_SCREEN_INVENTORY = """# Design inventory

## Requirements

### REQ-001 — A reader keeps a list of books

- Specs: SPEC-0001
- Screens: no screen: the kit's own rule

### REQ-002 — A nightly job tidies the list

- Specs: SPEC-0002
- Screens: no screen: the job runs without a person and shows nothing

## Screens
"""


@pytest.mark.parametrize("inventory", [True, False])
def test_ac2_an_all_out_map_with_no_screen_fails_naming_rule_15(tmp_path, inventory):
    """REQ-044 AC2: SPEC-0037 rule 15 as amendment 219 proposes (brief #1779 answer 2)."""
    if inventory:
        project(tmp_path, NO_SCREEN_INVENTORY)
    imported_all_out(tmp_path)
    proc = check(tmp_path)
    assert proc.returncode == 1, proc.stdout
    line = (
        "FAIL design: SPEC-0037 rule 15: docs/design/imported/: every page of i1 is mapped out"
        " while the inventory lists no screen"
    )
    assert line in proc.stdout.splitlines()


def test_ac2_an_all_out_map_in_a_project_with_screens_passes(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 15 (brief #1779 answer 6: with screens, out rows may stand)."""
    project(tmp_path)
    imported_all_out(tmp_path)
    proc = check(tmp_path)
    assert "every page of i1 is mapped out" not in proc.stdout, proc.stdout


# Brief #1889 (ADR-0783): the discovery Screens line is read past the quoted problem. Every
# discovery document here is written by `front_door.py discovery-write` itself, from a vision with
# its own `## ` headings or an issue whose problem holds one, so a reader that stops inside a quote
# fails at once.

VISION = (
    "# Vision\n\n## The idea\n\nA reader at example.com keeps a list of books.\n\n"
    "## Who it serves\n\nInvented readers of example.com."
)
TOMLS = {
    "installed": '[kit]\nlayout = "installed"\n',
    "plugin": '[kit]\nlayout = "plugin"\n',
    "personal": '[personal]\nforge = "files"\n',
}


def written_discovery(root: Path, screens: str | None, problem: str = VISION, issue: bool = False):
    """Run the kit's writer on an invented vision (or saved issue); return the written document."""
    import front_door

    inputs = root.parent / f"in-{root.name}"
    inputs.mkdir(exist_ok=True)
    data = {} if screens is None else {"screens": screens}
    data["answers"] = []
    answers = inputs / f"answers-{len(list(inputs.iterdir()))}.json"
    answers.write_text(json.dumps(data), encoding="utf-8")
    source = inputs / f"problem-{len(list(inputs.iterdir()))}"
    if issue:
        body = {
            "number": 7,
            "title": f"Books are lost {len(list(inputs.iterdir()))}",
            "html_url": "https://github.com/example/books/issues/7",
            "body": f"Problem: {problem}",
            "labels": [{"name": "agk-problem"}],
        }
        source.write_text(json.dumps(body), encoding="utf-8")
        args = ["discovery-write", "--issue", str(source)]
    else:
        source.write_text(problem, encoding="utf-8")
        args = ["discovery-write", "--vision", str(source)]
    folder = root / "docs" / "discovery"
    before = set(folder.glob("*.md")) if folder.is_dir() else set()
    assert front_door.main([*args, "--answers", str(answers), "--root", str(root)]) == 0
    (new,) = set(folder.glob("*.md")) - before
    return new


def layout_root(tmp_path: Path, layout: str) -> Path:
    root = tmp_path / layout
    root.mkdir()
    (root / "agk.toml").write_text(TOMLS[layout], encoding="utf-8")
    return root


@pytest.mark.parametrize("layout", sorted(TOMLS))
@pytest.mark.parametrize("screens", ["yes", "no", "open", None])
def test_ac2_the_written_screens_value_is_read_past_the_quoted_vision(tmp_path, layout, screens):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1889 answers 1 and 6: yes, no, open, the default)."""
    root = layout_root(tmp_path, layout)
    doc = written_discovery(root, screens)
    assert "\n## The idea\n" in doc.read_text(encoding="utf-8")
    expected = screens or "open"
    assert di.discovery_screens(root) == [(f"docs/discovery/{doc.name}", expected)]


@pytest.mark.parametrize("layout", sorted(TOMLS))
@pytest.mark.parametrize("screens,fails", [("yes", True), ("open", True), ("no", False)])
def test_ac2_a_screenless_inventory_is_refused_for_a_written_yes_or_open(
    tmp_path, layout, screens, fails
):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1889 answer 3: the refusal, unchanged, now reached)."""
    root = layout_root(tmp_path, layout)
    project(root, KIT_ONLY)
    written_discovery(root, screens)
    assert any(p.startswith(EMPTY_LIST) for p in problems(root)) is fails, problems(root)
    proc = check(root)
    assert proc.returncode == (1 if fails else 0), proc.stdout + proc.stderr
    assert (f"FAIL design: {EMPTY_LIST}" in proc.stdout) is fails
    assert "The idea" not in proc.stdout and "example.com" not in proc.stdout


@pytest.mark.parametrize("layout", sorted(TOMLS))
def test_ac2_any_written_yes_among_several_documents_refuses(tmp_path, layout):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1889 answer 6: several documents, one says yes)."""
    root = layout_root(tmp_path, layout)
    project(root, KIT_ONLY)
    written_discovery(root, "no", VISION.replace("books", "maps"))
    assert problems(root) == []
    written_discovery(root, "yes")
    assert sorted(v for _, v in di.discovery_screens(root)) == ["no", "yes"]
    assert any(p.startswith(EMPTY_LIST) for p in problems(root))
    assert check(root).returncode == 1


@pytest.mark.parametrize("layout", sorted(TOMLS))
def test_ac2_a_quote_ends_only_at_its_own_end_marker(tmp_path, layout):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1889 answer 2, Q-DS-2: an answer's end marker and a
    Screens line quoted in the problem are the person's words)."""
    root = layout_root(tmp_path, layout)
    project(root, KIT_ONLY)
    vision = VISION + "\n<!-- agk:answer-end -->\n- Screens: no\n\n## More\n\nInvented."
    doc = written_discovery(root, "yes", vision)
    assert "<!-- agk:answer-end -->\n- Screens: no" in doc.read_text(encoding="utf-8")
    assert di.discovery_screens(root) == [(f"docs/discovery/{doc.name}", "yes")]
    assert check(root).returncode == 1


@pytest.mark.parametrize("layout", ["installed", "plugin"])
def test_ac2_an_issue_problem_holding_a_heading_no_longer_hides_the_line(tmp_path, layout):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1889 answer 6: the brief path, an issue problem; a
    sidecar has no issue door, SPEC-0048 rule 13, so the personal root takes the vision tests)."""
    root = layout_root(tmp_path, layout)
    project(root, KIT_ONLY)
    doc = written_discovery(
        root, "yes", "Books at example.com are lost.\n## Steps\nInvented steps.", issue=True
    )
    assert "\n## Steps\n" in doc.read_text(encoding="utf-8")
    assert di.discovery_screens(root) == [(f"docs/discovery/{doc.name}", "yes")]
    assert any(p.startswith(EMPTY_LIST) for p in problems(root))
    assert check(root).returncode == 1


CHARTER = """# ADR-0002: Project charter

- Status: Accepted
- Date: 2026-11-24

## Context

A list of books on example.com.

## Decision

1. **Milestones**
   - M1: a reader keeps a list. exit: 3 books are kept.
2. **Non-goals**
   - Payments.

## Consequences

None.
"""


@pytest.mark.parametrize("layout", sorted(TOMLS))
@pytest.mark.parametrize("screens,named", [("yes", True), ("open", True), ("no", False)])
def test_ac2_design_inventory_names_a_written_yes_or_open_in_sources(
    tmp_path, layout, screens, named
):
    """REQ-044 AC2: SPEC-0037 rule 3 as amendment 217 (brief #1889 answer 3: `design.py
    inventory` names the writer-made document in each milestone's `- Sources:`)."""
    import design

    root = layout_root(tmp_path, layout)
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "adr" / "0002-project-charter.md").write_text(CHARTER, encoding="utf-8")
    doc = written_discovery(root, screens)
    text = design.milestone_sections(root, [])
    sources = [ln for ln in text.splitlines() if ln.startswith("- Sources:")]
    assert len(sources) == 1, text
    assert (f"docs/discovery/{doc.name}" in sources[0]) is named, sources
    assert "docs/adr/0002-project-charter.md" in sources[0]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# Discovery: x\n\n- Screens: no\r\n\n## Answers\n", "no"),
        ("# Discovery: x\n\n## Answers\n\n- Screens: yes\n", None),
        ("# Discovery: x\n\n<!-- agk:problem sha256=" + "0" * 64 + " -->\n- Screens: yes\n", None),
        ("# Discovery: x\n\n- Problem: vision\n", None),
    ],
)
def test_ac2_screens_line_reads_only_the_writer_s_place(text, expected):
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1889 answer 7: CRLF, below `## Answers` (Q-DS-4),
    an unclosed quote, no line)."""
    assert di.screens_line(text.split("\n")) == expected


def test_ac2_the_discovery_screens_line_has_one_reader():
    """REQ-044 AC2: SPEC-0037 rule 3 (brief #1889 answer 9: a third reader must call
    `screens_line`; the writer's own check-discovery test is the one other match)."""
    import re

    pattern = re.compile(r"- Screens: \(")  # any regex of the discovery line, whatever it captures
    found = {
        path.name: len(pattern.findall(path.read_text(encoding="utf-8")))
        for path in sorted((KIT_ROOT / "scripts" / "agk").glob("*.py"))
        if pattern.search(path.read_text(encoding="utf-8"))
    }
    assert found == {"design_inventory.py": 1, "front_door.py": 1}, found


# --- a signed inventory waits for its own pull request (brief #1930, ADR-0798, amendment 243) ---

LINK = "https://example.com/review/1"
SIGNOFF_HEAD = "a" * 40
NEW_REQ = "\n### REQ-003 — A reader exports the list\n\n- Acceptance: AC1 x\n- Status: planned\n"
WAITING = "design: rule 3: REQ-003 waits for an inventory pull request"


def sign(root: Path, digest: str | None = None) -> None:
    """An `inventory` row for DIGEST (the inventory's current digest when None)."""
    import design_signoff

    digest = digest or design_signoff.inventory_digest(root)
    (root / "docs/design/signoffs.md").write_text(
        "# Design sign-offs\n\n| kind | version | digest | head | date | comment |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        f"| inventory | - | {digest} | {SIGNOFF_HEAD} | 2026-11-25 | {LINK} |\n",
        encoding="utf-8",
    )


def add_requirement(root: Path, text: str = NEW_REQ) -> None:
    with open(root / "docs/requirements.md", "a", encoding="utf-8") as fh:
        fh.write(text)


def test_ac2_a_signed_inventory_lists_a_new_requirement_as_waiting(tmp_path):
    """REQ-044 AC2: SPEC-0037 rule 3, amendment 243 (a signed inventory waits, it does not fail)."""
    project(tmp_path)
    sign(tmp_path)
    add_requirement(tmp_path)
    assert problems(tmp_path) == []
    assert di.waiting_requirements(tmp_path) == ["REQ-003"]
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout
    usability = "design: usability not applicable (work type)"  # brief #1953: no work type
    assert proc.stdout.splitlines() == [WAITING, usability, "ok design"]


def test_ac2_two_new_requirements_give_two_waiting_lines(tmp_path):
    """REQ-044 AC2: amendment 243 (one line per waiting requirement)."""
    project(tmp_path)
    sign(tmp_path)
    add_requirement(tmp_path)
    add_requirement(tmp_path, NEW_REQ.replace("REQ-003", "REQ-004"))
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert [ln for ln in proc.stdout.splitlines() if "waits" in ln] == [
        WAITING,
        WAITING.replace("REQ-003", "REQ-004"),
    ]


@pytest.mark.parametrize("row", ["none", "other digest"])
def test_ac2_an_unsigned_inventory_is_checked_in_full(tmp_path, row):
    """REQ-044 AC2: rule 3 (no row, or a row for another digest: every requirement needs one)."""
    project(tmp_path)
    if row == "other digest":
        sign(tmp_path, "b" * 64)
    add_requirement(tmp_path)
    assert problems(tmp_path) == [f"{WHERE}: REQ-003: the requirement has no section"]
    assert di.waiting_requirements(tmp_path) == []
    proc = check(tmp_path)
    assert proc.returncode == 1
    assert "waits" not in proc.stdout


def test_ac2_a_changed_signed_inventory_is_checked_in_full(tmp_path):
    """REQ-044 AC2: rule 3 (the inventory changed since its sign-off: the digest has no row)."""
    project(tmp_path)
    sign(tmp_path)
    add_requirement(tmp_path, NEW_REQ.replace("REQ-003", "REQ-004") + NEW_REQ)
    path = tmp_path / INVENTORY
    text = path.read_text(encoding="utf-8").replace(
        "## Screens", "### REQ-003\n\n- Specs: SPEC-0003\n- Screens: no screen: x\n\n## Screens"
    )
    path.write_text(text, encoding="utf-8")
    assert problems(tmp_path) == [f"{WHERE}: REQ-004: the requirement has no section"]


def test_ac2_a_signed_inventory_with_an_empty_slot_still_fails(tmp_path):
    """REQ-044 AC2: rule 3 (every other problem fails a signed inventory as today)."""
    project(tmp_path, INVENTORY_TEXT.replace("- Flow: keep a list", "- Flow:", 1))
    sign(tmp_path)
    add_requirement(tmp_path)
    assert problems(tmp_path) == [f"{WHERE}: books: the slot Flow is empty"]
    assert check(tmp_path).returncode == 1


def test_ac2_a_malformed_signoffs_table_is_refused_never_read_as_signed(tmp_path):
    """REQ-044 AC2: rule 9 (a table of another shape is refused, as `parse_rows` does)."""
    project(tmp_path)
    (tmp_path / "docs/design/signoffs.md").write_text("# Design sign-offs\n", encoding="utf-8")
    add_requirement(tmp_path)
    proc = check(tmp_path)
    assert proc.returncode != 0
    assert "rule 9: docs/design/signoffs.md" in proc.stdout + proc.stderr
    assert "waits" not in proc.stdout


def test_ac2_only_a_product_requirement_waits_in_a_project(tmp_path):
    """REQ-044 AC2: amendment 243 (in a project only REQ-101 up waits; a kit one still fails)."""
    project(tmp_path)
    (tmp_path / "agk.toml").write_text('mode = "init"\n', encoding="utf-8")
    sign(tmp_path)
    add_requirement(tmp_path)
    add_requirement(tmp_path, NEW_REQ.replace("REQ-003", "REQ-101"))
    assert problems(tmp_path) == [f"{WHERE}: REQ-003: the requirement has no section"]
    assert di.waiting_requirements(tmp_path) == ["REQ-101"]


def test_ac2_the_prototype_draws_from_a_signed_inventory_with_a_waiting_requirement(tmp_path):
    """REQ-044 AC2: rule 3 (`design_prototype.agreed` calls `inventory_problems`, unchanged)."""
    import design_prototype

    project(tmp_path)
    sign(tmp_path)
    add_requirement(tmp_path)
    design_prototype.agreed(tmp_path)  # raises CheckError when it refuses


SPEC = """# SPEC-0003: Export

- Status: Draft
- Owner: reviewer group
- Requirements: REQ-003

## Rules

1. The export lists every item.
2. An empty list exports no file.

## Tests

- Rule 1: test, marker REQ@3 AC1.
- Rule 2: test, marker REQ@3 AC2.

## Proof

Rules 1 to 2.

## Residual

- 2026-11-25: later (due 2027-01-31).

## Open questions

none
""".replace("@", "-00")

INTAKE_REQ = (
    "\n### REQ-003 — Export\n\n- Acceptance: AC1 Given a saved list, when the reader exports it,"
    " then a file with every book is downloaded; AC2 Given an empty list, when the reader exports"
    " it, then the export is no file and shows an error message\n- Status: planned\n"
)


def test_ac2_a_requirement_intake_passes_beside_a_signed_inventory(repo):
    """REQ-044 AC2: SPEC-0037 rule 3 with SPEC-0012 rule 11 C2 (one change passes both checks)."""
    root = project(repo.root)
    repo.write("docs/specs/0001-books.md", "# SPEC-0001: Books\n")
    repo.write("docs/specs/0002-tidy.md", "# SPEC-0002: Tidy\n")
    repo.write("docs/adr/0001-books.md", "# ADR-0001: Books\n")
    repo.write("docs/runs/decisions-log.md", "# Decisions log\n\n| Date | Decision |\n|---|---|\n")
    repo.write("docs/runs/residuals.md", "# Residuals\n\n## Open\n\n## Closed (not findings)\n")
    sign(root)
    repo.commit({}, "base")
    repo.branch("intake/req-003-export")
    add_requirement(root, INTAKE_REQ)
    repo.write("docs/specs/0003-export.md", SPEC)
    stub = repo.run(
        "intake.py", "stub", "--req", "REQ-003", "--title", "Export", "--sentence",
        "Let a reader export the list as a file.", "--ref", "main", "--root", str(root),
        "--date", "2026-11-25",
    )  # fmt: skip
    assert stub.returncode == 0, stub.stdout + stub.stderr
    intake = repo.run(
        "intake.py", "check", "--base", "main", "--root", str(root), "--date", "2026-11-25"
    )
    assert intake.returncode == 0, intake.stdout
    design = check(root)
    assert design.returncode == 0, design.stdout
    assert WAITING in design.stdout.splitlines()
