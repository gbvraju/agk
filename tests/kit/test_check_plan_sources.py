"""Tests of `check_plan.py`, the sources (SPEC-0043 rules 1 and 2, rule 10; REQ-050 AC1).

A file under `docs/sources/` is `.md` or `.txt` and starts with `Source:`, `Kind:`, `Version:` and
`Date:` in this order, then one blank line; a design link is one row of
`docs/sources/design-links.md` with a name, an `https://` link, a version and frames. A failure
names the rule and the file, never a value. A project without `docs/plan/` passes with
`ok plan (no plan)`. Invented sources only (example.com); no network.
"""

from __future__ import annotations

import json
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import check_plan
import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_plan.py"

GOOD = "Source: Example statement of work\nKind: sow\nVersion: 1.2\nDate: 2026-10-01\n\n"
BODY = "# Scope\n\nThe portal at example.com lists orders.\n\n## Out of scope\n\nPayments.\n"
LINKS = (
    "Source: Example design links\nKind: design\nVersion: 3\nDate: 2026-10-02\n\n"
    "| Name | Link | Version | Frames |\n"
    "| --- | --- | --- | --- |\n"
    "| Orders | https://design.example.com/file/abc | 2026-10-02 | List, Detail |\n"
)
HEADER_TITLE = "Example statement of work"  # a header value; never printed


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def check(root: Path) -> tuple[int, str]:
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, proc.stdout + proc.stderr


def fails(root: Path, rule: str, rel: str) -> str:
    code, out = check(root)
    assert code == 1, out
    assert f"rule {rule}: {rel}" in out, out
    assert HEADER_TITLE not in out
    return out


# --- rule 10: the no-plan pass -----------------------------------------------------------------


def test_ac1_a_project_with_no_plan_passes(tmp_path):
    """REQ-050 AC1: rule 10, a project with no docs/plan/ and no sources sees no change."""
    assert check(tmp_path) == (0, "ok plan (no plan)\n")


def test_ac1_the_kit_itself_passes_with_no_plan():
    """REQ-050 AC1: the brief's Measured line, `ok plan (no plan)` on the kit itself."""
    code, out = check(KIT_ROOT)
    assert code == 0, out
    assert out.splitlines()[-1] == "ok plan (no plan)"


def test_ac1_good_sources_and_no_plan_pass(tmp_path):
    """REQ-050 AC1: rules 1 and 2, a well-formed .md, .txt and design-links file pass."""
    write(tmp_path, "docs/sources/sow.md", GOOD + BODY)
    write(tmp_path, "docs/sources/notes.txt", GOOD.replace("sow", "other") + "Plain text.\n")
    write(tmp_path, "docs/sources/design-links.md", LINKS)
    assert check(tmp_path) == (0, "ok plan (no plan)\n")


def test_ac1_sources_with_a_plan_folder_pass_as_sources_only(tmp_path):
    """REQ-050 AC1: with docs/plan/ the sources are checked, then build (d)'s coverage line."""
    write(tmp_path, "docs/sources/sow.md", GOOD + BODY)
    # brief #1217 (ADR-0516): a source no requirement cites is listed out of scope with a reason
    write(
        tmp_path,
        "docs/plan/scope.md",
        "## Out of scope\n\n- Not planned yet (`docs/sources/sow.md`)\n",
    )
    code, out = check(tmp_path)
    assert code == 0, out
    assert out.splitlines()[-1].startswith("ok plan: 0 of 0 in-scope source lines ")
    assert "(no plan)" not in out


# --- rule 1: the header -------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["Source", "Kind", "Version", "Date"])
def test_ac1_each_missing_header_line_fails(tmp_path, key):
    """REQ-050 AC1: rule 1, a source without one header line fails naming the rule and the file."""
    text = "".join(line + "\n" for line in GOOD.splitlines() if not line.startswith(f"{key}:"))
    write(tmp_path, "docs/sources/sow.md", text + BODY)
    out = fails(tmp_path, "1", "docs/sources/sow.md")
    assert f"{key}:" in out and "missing" in out


def test_ac1_an_empty_header_value_is_a_missing_line(tmp_path):
    """REQ-050 AC1: rule 1, `Version:` with no value lacks the header line."""
    write(tmp_path, "docs/sources/sow.md", GOOD.replace("Version: 1.2", "Version:") + BODY)
    out = fails(tmp_path, "1", "docs/sources/sow.md")
    assert "Version:" in out and "missing" in out


def test_ac1_header_lines_out_of_order_fail(tmp_path):
    """REQ-050 AC1: rule 1, the four lines in another order fail."""
    lines = GOOD.splitlines()
    swapped = "\n".join([lines[1], lines[0], lines[2], lines[3]]) + "\n\n"
    write(tmp_path, "docs/sources/sow.md", swapped + BODY)
    out = fails(tmp_path, "1", "docs/sources/sow.md")
    assert "out of order" in out


def test_ac1_a_kind_outside_the_list_fails_without_its_value(tmp_path):
    """REQ-050 AC1: rule 1, `Kind:` outside sow, brd, prd, design, charter, other."""
    write(tmp_path, "docs/sources/sow.md", GOOD.replace("Kind: sow", "Kind: zebrakind") + BODY)
    out = fails(tmp_path, "1", "docs/sources/sow.md")
    assert "Kind:" in out and "zebrakind" not in out


def test_ac1_a_date_that_is_not_a_real_date_fails(tmp_path):
    """REQ-050 AC1: rule 1, `Date: 2026-02-30` is not a real date."""
    write(tmp_path, "docs/sources/sow.md", GOOD.replace("2026-10-01", "2026-02-30") + BODY)
    out = fails(tmp_path, "1", "docs/sources/sow.md")
    assert "Date:" in out and "2026-02-30" not in out


def test_ac1_a_date_in_another_shape_fails(tmp_path):
    """REQ-050 AC1: rule 1, `Date:` must be YYYY-MM-DD."""
    write(tmp_path, "docs/sources/sow.md", GOOD.replace("2026-10-01", "1 October 2026") + BODY)
    fails(tmp_path, "1", "docs/sources/sow.md")


def test_ac1_no_blank_line_after_the_header_fails(tmp_path):
    """REQ-050 AC1: rule 1, the header is followed by one blank line, then the text."""
    write(tmp_path, "docs/sources/sow.md", GOOD.rstrip("\n") + "\n" + BODY)
    out = fails(tmp_path, "1", "docs/sources/sow.md")
    assert "blank line" in out


@pytest.mark.parametrize("name", ["sow.pdf", "sow.docx", "nested/plan.html"])
def test_ac1_a_file_that_is_not_md_or_txt_fails(tmp_path, name):
    """REQ-050 AC1: rule 1, a `.pdf` (or any other document) under docs/sources/ fails."""
    write(tmp_path, f"docs/sources/{name}", GOOD + BODY)
    out = fails(tmp_path, "1", f"docs/sources/{name}")
    assert ".md or .txt" in out


def test_ac1_a_source_that_is_not_utf8_fails(tmp_path):
    """REQ-050 AC1: rule 1, a source is text the person converted; bytes that are not UTF-8 fail."""
    path = tmp_path / "docs" / "sources" / "sow.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(GOOD.encode() + b"\xff\xfe broken\n")
    fails(tmp_path, "1", "docs/sources/sow.txt")


def test_ac1_every_bad_file_is_named(tmp_path):
    """REQ-050 AC1: rule 1, one line per problem, each naming its file."""
    write(tmp_path, "docs/sources/a.md", BODY)
    write(tmp_path, "docs/sources/b.pdf", "x")
    write(tmp_path, "docs/sources/c.md", GOOD + BODY)
    code, out = check(tmp_path)
    assert code == 1
    assert "docs/sources/a.md" in out and "docs/sources/b.pdf" in out
    assert "docs/sources/c.md" not in out
    assert all(line.startswith("FAIL plan: ") for line in out.splitlines())


def test_ac1_the_header_is_parsed_for_the_later_builds():
    """REQ-050 AC1: rule 1, one function returns the header that builds (c) and (d) import."""
    assert check_plan.header(GOOD + BODY) == {
        "Source": "Example statement of work",
        "Kind": "sow",
        "Version": "1.2",
        "Date": "2026-10-01",
    }
    assert check_plan.header(BODY) is None
    assert check_plan.HEADER == ("Source", "Kind", "Version", "Date")
    # amendment 166 item 2 (ADR-0473): `openspec` joins the list before `other`
    assert check_plan.KINDS == ("sow", "brd", "prd", "design", "charter", "openspec", "other")


# --- rule 1: a location -------------------------------------------------------------------------


def sources(root: Path) -> None:
    write(root, "docs/sources/sow.md", GOOD + BODY)
    write(root, "docs/sources/notes.txt", GOOD + "one\ntwo\n")


def test_ac1_a_line_location_resolves_within_the_file(tmp_path):
    """REQ-050 AC1: rule 1, `<file>:<line>` names an existing line of a source."""
    sources(tmp_path)
    lines = len((GOOD + BODY).splitlines())
    assert check_plan.location_problem(tmp_path, "docs/sources/sow.md:1") is None
    assert check_plan.location_problem(tmp_path, f"docs/sources/sow.md:{lines}") is None
    assert check_plan.location_problem(tmp_path, "docs/sources/notes.txt:7") is None
    for bad in (
        f"docs/sources/sow.md:{lines + 1}",
        "docs/sources/sow.md:0",
        "docs/sources/sow.md:x",
    ):
        problem = check_plan.location_problem(tmp_path, bad)
        assert problem and "rule 1" in problem


def test_ac1_a_heading_location_matches_a_heading_exactly(tmp_path):
    """REQ-050 AC1: rule 1, `<file>#<heading>` is the exact text of a Markdown heading."""
    sources(tmp_path)
    assert check_plan.location_problem(tmp_path, "docs/sources/sow.md#Scope") is None
    assert check_plan.location_problem(tmp_path, "docs/sources/sow.md#Out of scope") is None
    for bad in (
        "docs/sources/sow.md#scope",
        "docs/sources/sow.md#Payments",
        "docs/sources/sow.md#",
    ):
        assert check_plan.location_problem(tmp_path, bad)
    assert check_plan.location_problem(tmp_path, "docs/sources/notes.txt#one")


def test_ac1_a_heading_inside_a_code_fence_is_not_a_heading(tmp_path):
    """REQ-050 AC1: rule 1, a `#` line inside a fenced block is text, not a heading."""
    write(tmp_path, "docs/sources/sow.md", GOOD + "```\n# Not a heading\n```\n")
    assert check_plan.location_problem(tmp_path, "docs/sources/sow.md#Not a heading")


def test_ac1_a_location_outside_the_sources_folder_fails(tmp_path):
    """REQ-050 AC1: rule 1, a location's file is under docs/sources/ (or a charter's Milestones)."""
    sources(tmp_path)
    write(tmp_path, "README.md", "# Scope\n")
    for bad in (
        "README.md:1",
        "README.md#Scope",
        "docs/sources/../../README.md:1",
        "/etc/hosts:1",
        "docs/sources/missing.md:1",
        "docs/sources/sow.md",
    ):
        assert check_plan.location_problem(tmp_path, bad), bad


CHARTER = """# ADR-0002: Project charter

- Status: Accepted
- Date: 2026-10-01

## Context

An invented project at example.com.

## Decision

1. **Milestones**
   - M1 orders list; exit: 3 screens pass review
2. **Non-goals**
   - payments
3. **Done means**
   - all criteria met

## Consequences

None.
"""


def test_ac1_a_charter_milestones_location_resolves_without_a_copy(tmp_path):
    """REQ-050 AC1: rule 1, `docs/adr/<charter>#Milestones` cites the charter in place."""
    write(tmp_path, "docs/adr/0002-project-charter.md", CHARTER)
    assert (
        check_plan.location_problem(tmp_path, "docs/adr/0002-project-charter.md#Milestones") is None
    )
    assert check_plan.location_problem(tmp_path, "docs/adr/0002-project-charter.md#Non-goals")
    assert check_plan.location_problem(tmp_path, "docs/adr/0003-project-charter.md#Milestones")
    write(tmp_path, "docs/adr/0004-other.md", CHARTER)
    assert check_plan.location_problem(tmp_path, "docs/adr/0004-other.md#Milestones")
    write(
        tmp_path, "docs/adr/0005-project-charter.md", CHARTER.replace("**Milestones**", "**Goals**")
    )
    assert check_plan.location_problem(tmp_path, "docs/adr/0005-project-charter.md#Milestones")


def test_ac1_the_charter_name_is_the_playbook_s():
    """REQ-050 AC1: rule 1, a charter is the file name `playbook.py check-start` checks."""
    import playbook

    assert check_plan.CHARTER_NAME.pattern == playbook.CHARTER_NAME.pattern


# --- rule 2: design links -----------------------------------------------------------------------


def links(root: Path, text: str) -> None:
    write(root, "docs/sources/design-links.md", text)


@pytest.mark.parametrize(
    ("row", "word"),
    [
        ("| Orders | https://design.example.com/f | | List |", "Version"),
        ("| Orders | https://design.example.com/f | 3 | |", "Frames"),
        ("| | https://design.example.com/f | 3 | List |", "Name"),
        ("| Orders | | 3 | List |", "Link"),
        ("| Orders | https://design.example.com/f | 3 |", "Frames"),
    ],
)
def test_ac1_a_design_link_row_without_a_value_fails(tmp_path, row, word):
    """REQ-050 AC1: rule 2, each row has the four values."""
    links(tmp_path, LINKS + row + "\n")
    out = fails(tmp_path, "2", "docs/sources/design-links.md")
    assert "row 2" in out and word in out


def test_ac1_an_http_link_fails_without_its_value(tmp_path):
    """REQ-050 AC1: rule 2, `Link` starts with `https://`."""
    links(
        tmp_path,
        LINKS.replace("https://design.example.com/file/abc", "http://design.example.com/x"),
    )
    out = fails(tmp_path, "2", "docs/sources/design-links.md")
    assert "row 1" in out and "https://" in out and "design.example.com" not in out


def test_ac1_design_links_need_kind_design_and_the_four_columns(tmp_path):
    """REQ-050 AC1: rule 2, the file's header is `Kind: design` and its table has the columns."""
    links(tmp_path, LINKS.replace("Kind: design", "Kind: other"))
    assert "Kind:" in fails(tmp_path, "2", "docs/sources/design-links.md")
    links(tmp_path, LINKS.replace("| Frames |", "| Pages |", 1))
    assert "columns" in fails(tmp_path, "2", "docs/sources/design-links.md")
    links(tmp_path, LINKS.split("| Name")[0])
    assert "columns" in fails(tmp_path, "2", "docs/sources/design-links.md")


def test_ac1_design_links_also_carry_the_rule_1_header(tmp_path):
    """REQ-050 AC1: rules 1 and 2, the design-links file is a source with a header."""
    links(tmp_path, LINKS.split("\n\n", 1)[1])
    fails(tmp_path, "1", "docs/sources/design-links.md")


def test_ac1_the_check_opens_no_network_connection(tmp_path, monkeypatch, capsys):
    """REQ-050 AC1: rule 2, no check opens a link (a socket guard)."""
    links(tmp_path, LINKS)
    write(tmp_path, "docs/sources/sow.md", GOOD + "See https://portal.example.com/orders\n")

    def refuse(*args, **kwargs):
        raise AssertionError("the check opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    assert check_plan.cmd_check(tmp_path) == 0
    assert capsys.readouterr().out == "ok plan (no plan)\n"
    source = SCRIPT.read_text(encoding="utf-8")
    for module in ("socket", "urllib", "http", "requests", "ssl", "subprocess"):
        assert f"import {module}" not in source and f"from {module}" not in source


def test_ac1_the_check_writes_nothing(tmp_path):
    """REQ-050 AC1: rules 1 and 2, files only, nothing written."""
    links(tmp_path, LINKS)
    write(tmp_path, "docs/sources/bad.md", BODY)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    check(tmp_path)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


# --- wiring ---------------------------------------------------------------------------------------


def test_ac1_the_check_is_installed_and_in_the_governance_target():
    """REQ-050 AC1: brief answer 1, `verbatim` in the manifest and one line of `agk-governance`."""
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    recipe = mk.split("agk-governance:\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert "\t$(PY) scripts/agk/check_plan.py" in recipe
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/check_plan.py" in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])


def test_ac1_a_bad_argument_is_refused():
    """REQ-050 AC1: usage, exit 2."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--bogus"], capture_output=True, text=True
    )
    assert proc.returncode == 2
    assert "usage: check_plan.py" in proc.stderr
