"""Tests of `plan_intake.py openspec-import` and `openspec` (SPEC-0043 amendment 166 items 2 to 4,
ADR-0472, ADR-0473, brief #1109; REQ-050).

REQ-050 AC1 and AC2.

`openspec-import` copies an OpenSpec file, combined or as an `openspec/` folder, under
`docs/sources/openspec-<slug>/`, each file's original bytes unchanged after the rule 1 header, only
after the data guard passed every file. `openspec` reads the imported files, by a script and not a
model, into a proposals file that `validate` accepts: each capability one area, each `Requirement:`
heading one requirement with its statement exactly, each `Scenario:` heading one criterion ending
with its location; what the file leaves open is an open question, never a value. Invented files
only (a lending library at example.com), written in `tmp_path`; no network.
"""

from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path

import check_plan
import plan_intake
import pytest

SLUG = "lib"
FOLDER = f"docs/sources/openspec-{SLUG}"
BRD = "docs/sources/brd.md"
BRD_TEXT = (
    "Source: Example lending rules for example.com\nKind: brd\nVersion: 1\nDate: 2026-10-01\n\n"
    "# Lending rules\n\n## 2.1 Loan limits\n\nA member holds five loans at most.\n"
)
COMBINED = (
    "# Example library functional file\n\n"
    "Invented for the tests; the library is at example.com.\n\n"
    "### Book loans\n\n"
    "*Capability `book-loans`. Defined by: `loan-intake-rules` (open, 12/30 tasks done).*\n\n"
    "#### Requirement: Loan limit\n\n"
    "The system SHALL refuse a sixth loan for one member\n"
    "(BRD 2.1, design option a).\n\n"
    "##### Scenario: Sixth loan refused\n\n"
    "- **GIVEN** a member with five loans\n"
    "- **WHEN** a librarian records a sixth loan\n"
    "- **THEN** the loan is refused\n"
    "- **AND** the member sees the limit\n\n"
    "#### Requirement: No loan without a card\n\n"
    "The system SHALL NOT record a loan for a member without a card.\n\n"
    "##### Scenario: Card missing\n\n"
    "- WHEN a librarian records a loan for a member without a card\n"
    "- THEN the loan is not recorded\n\n"
    "#### Notes for the team\n\n"
    "- WHEN this bullet is under an unknown heading it is no step\n\n"
    "### Book returns\n\n"
    "*Capability `book-returns`. Defined by: `returns-rules` (done, 8/8 tasks done).*\n\n"
    "#### Requirement: Return receipt\n\n"
    "The system SHALL print a receipt for every return.\n"
)
SPEC_LOANS = (
    "# Book loans Specification\n\n## Purpose\n\nLoans of the example.com library.\n\n"
    "## Requirements\n\n"
    "### Requirement: Loan limit\n\nThe system SHALL refuse a sixth loan.\n\n"
    "#### Scenario: Sixth loan refused\n\n"
    "- **WHEN** a librarian records a sixth loan\n- **THEN** the loan is refused\n"
)
SPEC_RETURNS = (
    "# Book returns Specification\n\n## Requirements\n\n"
    "### Requirement: Return receipt\n\nThe system SHALL print a receipt.\n\n"
    "#### Scenario: Receipt printed\n\n"
    "- GIVEN a returned book\n- WHEN a member hands it in\n- THEN a receipt is printed\n"
)
DELTA = "## ADDED Requirements\n\n### Requirement: Late fines\n\nThe system SHALL charge fines.\n"
LAYOUT = {
    "specs/book-loans/spec.md": SPEC_LOANS,
    "specs/book-returns/spec.md": SPEC_RETURNS,
    "changes/add-fines/proposal.md": "# Add fines\n\nWhy fines.\n",
    "changes/add-fines/tasks.md": "# Tasks\n\n- [ ] 1.1 Add the fine table\n",
    "changes/add-fines/specs/book-loans/spec.md": DELTA,
    "changes/archive/old-receipts/specs/book-returns/spec.md": DELTA,
    "project.md": "# Project\n\nThe example.com library.\n",
}


def write(root: Path, rel: str, text: str | bytes) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write(root, "scripts/agk/guard.py", "# the data guard (a placeholder of the fixture)\n")
    write(root, ".claude/hooks/data_guard.py", "# the read hook (a placeholder of the fixture)\n")
    write(root, BRD, BRD_TEXT)
    return root


@pytest.fixture
def combined(tmp_path: Path) -> Path:
    return write(tmp_path / "given", "library.md", COMBINED)


@pytest.fixture
def layout(tmp_path: Path) -> Path:
    base = tmp_path / "given" / "openspec"
    for rel, text in LAYOUT.items():
        write(base, rel, text)
    write(base, "logo.png", b"\x89PNG\r\n\x1a\n")
    return base


def call(capsys, *args: str) -> tuple[int, str]:
    code = plan_intake.main(list(args))
    out = capsys.readouterr()
    return code, out.out + out.err


def do_import(repo: Path, path: Path, capsys, slug: str = SLUG) -> tuple[int, str]:
    return call(capsys, "openspec-import", str(path), "--slug", slug, "--root", str(repo))


def draft(repo: Path, capsys) -> tuple[int, str, dict]:
    out_file = repo.parent / "proposals.json"
    code, out = call(
        capsys, "openspec", "--slug", SLUG, "--out", str(out_file), "--root", str(repo)
    )
    data = json.loads(out_file.read_text(encoding="utf-8")) if out_file.is_file() else {}
    return code, out, data


def validate(repo: Path, data: dict, capsys) -> tuple[int, str]:
    path = repo.parent / "edited.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return call(capsys, "validate", "--proposals", str(path), "--root", str(repo))


# --- item 2: the import -------------------------------------------------------------------------


def test_ac1_a_combined_file_is_copied_byte_for_byte_under_its_header(
    repo: Path, combined: Path, capsys
) -> None:
    """REQ-050 AC1: rule 2b, the header (`Version:` the SHA-256 of the original), a blank line,
    then the original bytes unchanged; `check_plan.py` passes `Kind: openspec`."""
    code, out = do_import(repo, combined, capsys)
    assert code == 0, out
    written = (repo / FOLDER / "library.md").read_bytes()
    original = combined.read_bytes()
    head, _, rest = written.partition(b"\n\n")
    assert rest == original
    lines = head.decode("utf-8").splitlines()
    assert lines[0] == "Source: OpenSpec library.md"
    assert lines[1] == "Kind: openspec"
    assert lines[2] == "Version: sha256:" + hashlib.sha256(original).hexdigest()
    assert check_plan.real_date(lines[3].removeprefix("Date: "))
    assert "openspec" in check_plan.KINDS
    assert check_plan.main(["--root", str(repo)]) == 0
    assert "ok plan" in capsys.readouterr().out


def test_ac1_a_folder_is_copied_at_its_paths_and_other_files_are_skipped(
    repo: Path, layout: Path, capsys
) -> None:
    """REQ-050 AC1: rule 2b, every `.md` and `.txt` at its relative path; another file printed."""
    code, out = do_import(repo, layout, capsys)
    assert code == 0, out
    for rel, text in LAYOUT.items():
        written = (repo / FOLDER / rel).read_text(encoding="utf-8")
        assert written.startswith(f"Source: OpenSpec {rel}\nKind: openspec\n")
        assert written.endswith("\n\n" + text) or written.split("\n\n", 1)[1] == text
    assert not (repo / FOLDER / "logo.png").exists()
    assert "skipped: logo.png (rule 1: .md or .txt only)" in out


def test_ac1_an_existing_slug_is_never_overwritten(repo: Path, combined: Path, capsys) -> None:
    """REQ-050 AC1: rule 2b, exit 2 and the folder left byte for byte."""
    assert do_import(repo, combined, capsys)[0] == 0
    before = (repo / FOLDER / "library.md").read_bytes()
    combined.write_text(COMBINED + "\nMore.\n", encoding="utf-8")
    code, out = do_import(repo, combined, capsys)
    assert code == 2 and FOLDER in out, out
    assert (repo / FOLDER / "library.md").read_bytes() == before


@pytest.mark.parametrize("slug", ["", "Lib", "-lib", "lib/x", "lib x"])
def test_ac1_a_bad_slug_is_refused(repo: Path, combined: Path, capsys, slug: str) -> None:
    """REQ-050 AC1: rule 2b, the refusal names the setting, never a value."""
    code, out = do_import(repo, combined, capsys, slug)
    assert code == 2, out
    assert not (repo / "docs/sources").joinpath(f"openspec-{slug}").exists() or slug == ""
    assert not any((repo / "docs/sources").glob("openspec-*"))


def test_ac1_a_missing_slug_and_a_path_without_specs_are_refused(
    repo: Path, tmp_path: Path, capsys
) -> None:
    """REQ-050 AC1: rule 2b, a path that is neither a `.md` file nor a folder with `specs/`."""
    empty = tmp_path / "nothing"
    empty.mkdir()
    assert call(capsys, "openspec-import", str(empty), "--root", str(repo))[0] == 2
    code, out = do_import(repo, empty, capsys)
    assert code == 2 and "specs/" in out, out
    text = write(tmp_path, "notes.txt", "plain\n")
    assert do_import(repo, text, capsys)[0] == 2
    assert not any((repo / "docs/sources").glob("openspec-*"))


def test_ac1_a_file_that_is_not_utf8_is_refused(repo: Path, layout: Path, capsys) -> None:
    """REQ-050 AC1: rule 2b, exit 2 naming the path, writing nothing."""
    write(layout, "specs/book-loans/notes.md", b"\xff\xfe broken\n")
    code, out = do_import(repo, layout, capsys)
    assert code == 2 and "specs/book-loans/notes.md" in out, out
    assert not (repo / FOLDER).exists()


def test_ac1_a_guard_finding_refuses_the_whole_import_naming_place_never_value(
    repo: Path, layout: Path, capsys
) -> None:
    """REQ-050 AC1: rule 3, `guard.scan_text` on every file first; the value is built here."""
    value = "ghp_" + "a1B2c3D4" * 4 + "a1B2"
    write(layout, "project.md", f"# Project\n\nThe token {value}.\n")
    code, out = do_import(repo, layout, capsys)
    assert code == 1, out
    assert "project.md" in out and "line 3, column " in out
    assert value not in out and "ghp_" not in out
    assert not (repo / FOLDER).exists()


def test_ac1_the_import_needs_the_guard(repo: Path, combined: Path, capsys) -> None:
    """REQ-050 AC1: rule 3, exit 2 without the data guard."""
    (repo / "scripts/agk/guard.py").unlink()
    code, out = do_import(repo, combined, capsys)
    assert code == 2 and "data guard not installed: scripts/agk/guard.py" in out


# --- items 3 and 4: the reading -----------------------------------------------------------------


def test_ac2_the_combined_file_reads_into_areas_requirements_and_criteria(
    repo: Path, combined: Path, capsys
) -> None:
    """REQ-050 AC2: rule 4b, `###`/`####`/`#####` headings, bold and plain steps, `SHALL NOT`."""
    assert do_import(repo, combined, capsys)[0] == 0
    code, out, data = draft(repo, capsys)
    assert code == 0, out
    loc = f"{FOLDER}/library.md"
    assert data["areas"] == [
        {"name": "Book loans", "requirements": ["R1", "R2"]},
        {"name": "Book returns", "requirements": ["R3"]},
    ]
    r1, r2, r3 = data["requirements"]
    assert (r1["title"], r2["title"], r3["title"]) == (
        "Loan limit",
        "No loan without a card",
        "Return receipt",
    )
    assert r1["statement"] == (
        "The system SHALL refuse a sixth loan for one member (BRD 2.1, design option a)."
    )
    assert r2["statement"] == "The system SHALL NOT record a loan for a member without a card."
    assert r1["criteria"] == [
        "Given a member with five loans, when a librarian records a sixth loan, then the loan is"
        f" refused and the member sees the limit ({loc}#Scenario: Sixth loan refused)"
    ]
    assert r2["criteria"] == [
        "When a librarian records a loan for a member without a card, then the loan is not"
        f" recorded ({loc}#Scenario: Card missing)"
    ]
    assert r1["sources"][0] == f"{loc}#Requirement: Loan limit"
    assert all(r["milestone"] is None for r in data["requirements"])
    assert (data["milestones"], data["briefs"], data["conflicts"]) == ([], [], [])


def test_ac2_change_status_cross_references_and_a_requirement_without_scenario(
    repo: Path, combined: Path, capsys
) -> None:
    """REQ-050 AC2: rule 6, `(open, ...)` marks `changing`; `BRD 2.1` resolves exactly; `design
    option a` and a missing scenario are open questions with `(verify)`, never values."""
    do_import(repo, combined, capsys)
    _, out, data = draft(repo, capsys)
    r1, r2, r3 = data["requirements"]
    assert (r1["changing"], r2["changing"], r3["changing"]) == (True, True, False)
    assert r1["sources"] == [
        f"{FOLDER}/library.md#Requirement: Loan limit",
        f"{BRD}#2.1 Loan limits",
    ]
    assert r3["criteria"] == ["(verify)"]
    questions = data["scope"]["open_questions"]
    assert all("(verify)" in q["text"] for q in questions)
    texts = " ".join(q["text"] for q in questions)
    assert "R1" in texts and "cross-reference 2" in texts and "design option a" not in texts
    assert any(
        "R3" in q["text"] and q["sources"] == [f"{FOLDER}/library.md#Requirement: Return receipt"]
        for q in questions
    )


def test_ac2_a_second_source_of_the_kind_as_txt_makes_the_reference_a_question(
    repo: Path, combined: Path, capsys
) -> None:
    """REQ-050 AC2: rule 6 (`Q-1108-9`), `BRD 2.1` links only when exactly one file under
    `docs/sources/` has `Kind: brd`, `.md` or `.txt`; a second one makes it an open question."""
    write(repo, "docs/sources/brd-two.txt", BRD_TEXT.replace("Loan limits", "Other limits"))
    do_import(repo, combined, capsys)
    _, _, data = draft(repo, capsys)
    r1 = data["requirements"][0]
    assert r1["sources"] == [f"{FOLDER}/library.md#Requirement: Loan limit"]
    texts = [q["text"] for q in data["scope"]["open_questions"]]
    assert any("R1" in t and "cross-reference 1" in t for t in texts), texts
    assert any("R1" in t and "cross-reference 2" in t for t in texts), texts


def test_ac2_persona_candidates_come_from_the_steps(repo: Path, combined: Path, capsys) -> None:
    """REQ-050 AC2: amendment 164 item 2 is on the default branch, so actors are `personas`
    (brief answer 2): the `a <word>` or `an <word>` that starts a `WHEN` step, each cited to its
    first scenario; a requirement without one has a `(verify)` persona, and every story is the
    form with `(verify)` for the person."""
    do_import(repo, combined, capsys)
    _, _, data = draft(repo, capsys)
    names = [p["name"] for p in data["personas"]]
    assert names == ["a librarian", "(verify)"]
    assert [p["key"] for p in data["personas"]] == ["P1", "P2"]
    assert data["personas"][0]["sources"] == [f"{FOLDER}/library.md#Scenario: Sixth loan refused"]
    assert data["personas"][0]["goals"] == ["(verify)"]
    r1, _, r3 = data["requirements"]
    assert r1["persona"] == "P1" and r3["persona"] == "P2"
    assert r1["story"] == "As a librarian, I want (verify), so that (verify)"


def test_ac2_an_unknown_heading_is_ignored_with_a_warning(
    repo: Path, combined: Path, capsys
) -> None:
    """REQ-050 AC2: rule 4b, a heading that is no capability, requirement or scenario: its
    bullets are no steps, and the warning names its line, never its text."""
    do_import(repo, combined, capsys)
    _, out, data = draft(repo, capsys)
    line = 5 + COMBINED.splitlines().index("#### Notes for the team") + 1
    assert f"ignored: {FOLDER}/library.md:{line}: heading is not a capability" in out
    assert "Notes for the team" not in out
    assert "unknown heading" not in json.dumps(data)


def test_ac2_the_output_passes_validate(repo: Path, combined: Path, capsys) -> None:
    """REQ-050 AC2: the brief's sentence, `validate` accepts the draft; no network."""
    do_import(repo, combined, capsys)
    _, _, data = draft(repo, capsys)
    code, out = validate(repo, data, capsys)
    assert code == 0 and out.strip() == "ok proposals", out


def test_ac2_the_folder_layout_reads_and_changes_are_never_requirements(
    repo: Path, layout: Path, capsys, monkeypatch
) -> None:
    """REQ-050 AC2: rule 4b and 6, `specs/<slug>/spec.md` with `###`/`####`; a delta spec under
    `changes/` outside `archive/` marks its capability `changing` and is one open question."""
    do_import(repo, layout, capsys)
    monkeypatch.setattr(socket, "socket", None)
    code, out, data = draft(repo, capsys)
    assert code == 0, out
    assert [a["name"] for a in data["areas"]] == ["book-loans", "book-returns"]
    titles = [r["title"] for r in data["requirements"]]
    assert titles == ["Loan limit", "Return receipt"] and "Late fines" not in json.dumps(data)
    loans, returns = data["requirements"]
    assert (loans["changing"], returns["changing"]) == (True, False)
    assert returns["criteria"] == [
        "Given a returned book, when a member hands it in, then a receipt is printed"
        f" ({FOLDER}/specs/book-returns/spec.md#Scenario: Receipt printed)"
    ]
    assert any(
        q["sources"] == [f"{FOLDER}/changes/add-fines/proposal.md#Add fines"]
        for q in data["scope"]["open_questions"]
    )
    code, out = validate(repo, data, capsys)
    assert code == 0, out


def test_ac2_a_repeated_heading_is_cited_by_its_line(repo: Path, tmp_path: Path, capsys) -> None:
    """REQ-050 AC2: `Q-1108-3`, a scenario name that repeats in its file is `<file>:<line>`."""
    text = COMBINED.replace("Scenario: Card missing", "Scenario: Sixth loan refused")
    given = write(tmp_path / "given", "library.md", text)
    do_import(repo, given, capsys)
    _, _, data = draft(repo, capsys)
    line = 5 + text.splitlines().index("##### Scenario: Sixth loan refused") + 1
    assert data["requirements"][0]["criteria"][0].endswith(f"({FOLDER}/library.md:{line})")
    assert validate(repo, data, capsys)[0] == 0


def test_ac2_the_draft_needs_an_import_and_never_overwrites(
    repo: Path, combined: Path, capsys
) -> None:
    """REQ-050 AC2: rule 4b, exit 2 without the folder, over an existing file or inside docs/."""
    assert draft(repo, capsys)[0] == 2
    do_import(repo, combined, capsys)
    out_file = repo.parent / "proposals.json"
    out_file.write_text("{}", encoding="utf-8")
    assert draft(repo, capsys)[0] == 2 and out_file.read_text(encoding="utf-8") == "{}"
    inside = repo / "docs" / "p.json"
    code, _ = call(capsys, "openspec", "--slug", SLUG, "--out", str(inside), "--root", str(repo))
    assert code == 2 and not inside.exists()


# --- validate and render of the new fields ------------------------------------------------------


def test_ac2_validate_refuses_what_the_reading_must_keep(
    repo: Path, combined: Path, capsys
) -> None:
    """REQ-050 AC2: rule 5, a null statement of an openspec requirement, a criterion's location
    that does not resolve, and a `changing` requirement in `M1` without an open question."""
    do_import(repo, combined, capsys)
    _, _, data = draft(repo, capsys)
    data["requirements"][2]["statement"] = None
    data["requirements"][1]["criteria"][0] = "When a, then b (docs/sources/none.md#Scenario: x)"
    milestone = {"id": "M1", "title": "Loans", "exit": "all 2 rules pass", "acceptance": "ok"}
    milestone |= {"target": None, "sources": [f"{BRD}#2.1 Loan limits"]}
    brief = {"key": "B1", "milestone": "M1", "title": "Loans", "size": "M", "expected": "1-2 hours"}
    brief |= {"advances": ["R1"], "touches": ["src/loans.py"], "depends_on": []}
    brief |= {"sources": [f"{FOLDER}/library.md#Requirement: Loan limit"]}
    data["milestones"], data["briefs"] = [milestone], [brief]
    data["requirements"][0]["milestone"] = "M1"
    data["scope"]["open_questions"] = [
        q for q in data["scope"]["open_questions"] if "R1" not in q["text"]
    ]
    code, out = validate(repo, data, capsys)
    assert code == 1, out
    assert "rule 5: requirements R3: statement is null for a Kind: openspec source" in out
    assert "rule 5: requirements R2: criterion 1 ends with a location that does not resolve" in out
    assert "rule 5: requirements R1: changing in M1 without an open question citing it" in out


def test_ac2_render_writes_statement_and_changing_and_refuses_an_unset_milestone(
    repo: Path, combined: Path, capsys
) -> None:
    """REQ-050 AC2: rule 7, `Statement:` and `Changing: yes` lines; a draft whose milestones the
    skill has not set renders nothing."""
    do_import(repo, combined, capsys)
    _, _, data = draft(repo, capsys)
    assert "rule 7: requirements R1: milestone is not set" in plan_intake.render_problems(data)
    for r in data["requirements"]:
        r["milestone"] = "M1"
    text = plan_intake.requirements_text(data)
    assert "Statement: The system SHALL NOT record a loan for a member without a card." in text
    block = text.split("### R1 ")[1].split("### R2 ")[0]
    assert "Changing: yes" in block
    assert "Changing: yes" not in text.split("### R3 ")[1]
