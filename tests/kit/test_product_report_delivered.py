"""Tests of Delivered by week (SPEC-0017, REQ-024). No network, no model, no `gh`.

The facts are the report fixture `kinds` (week 2026-W41, Monday 2026-10-05 to Sunday 2026-10-11)
with a `done_on` set on each requirement row, or left out.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from product_report import main

ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).parent / "fixtures" / "report"
SOURCE = ROOT / "scripts" / "agk" / "product_report.py"
WORKFLOW = ROOT / ".github" / "workflows" / "product-report.yml"
NOTE = " (week it became done: unknown)"
ALLOWED_IMPORTS = {
    "argparse",
    "json",
    "re",
    "sys",
    "datetime",
    "decimal",
    "collections",
    "pathlib",
    "__future__",
}


def kinds() -> dict:
    return json.loads((REPORT / "kinds" / "facts.json").read_text(encoding="utf-8"))


def dated(dates: dict) -> dict:
    """The `kinds` facts with `done_on` as given on the rows named (the rest have none)."""
    doc = kinds()
    for row in doc["requirements"]:
        if row["id"] in dates:
            row["done_on"] = dates[row["id"]]
    return doc


def section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), None)
    if end is None:
        end = lines.index("---")
    return [ln for ln in lines[start:end] if ln]


def render_doc(doc: dict, tmp_path: Path, capsys) -> str:
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert main(["--facts", str(path)]) == 0
    return capsys.readouterr().out


def listed(doc: dict, tmp_path: Path, capsys) -> list[str]:
    """The requirement ids that Delivered lists."""
    lines = section(render_doc(doc, tmp_path, capsys), "## Delivered")
    return [ln.split(" ")[1] for ln in lines if ln.startswith("- REQ-")]


ALL_DONE = ["REQ-001", "REQ-002", "REQ-005", "REQ-006", "REQ-009"]


def test_ac1_a_requirement_that_became_done_in_the_week_is_listed(tmp_path, capsys):
    """REQ-024 AC1: SPEC-0017 rule 3 (inside the week, both ends: Monday and Sunday)."""
    dates = {"REQ-001": "2026-10-08", "REQ-002": "2026-10-05", "REQ-005": "2026-10-11"}
    doc = dated(dates | {"REQ-006": "2026-09-01", "REQ-009": "2026-09-02"})
    assert listed(doc, tmp_path, capsys) == ["REQ-001", "REQ-002", "REQ-005"]


def test_ac1_the_listed_line_is_the_usual_line(tmp_path, capsys):
    """REQ-024 AC1: SPEC-0017 rule 3 (the line printed before this change, with no note)."""
    doc = dated({"REQ-001": "2026-10-08"})
    out = render_doc(doc, tmp_path, capsys)
    golden = (REPORT / "golden" / "kinds" / "report.md").read_text(encoding="utf-8")
    line = next(
        ln for ln in golden.splitlines() if ln.startswith('- REQ-001 "Alpha thing" is done')
    )
    usual = line.replace(NOTE, "")  # the golden's facts have no `done_on`: its line holds the note
    assert usual in out.splitlines() and usual != line


def test_ac2_a_requirement_done_before_or_after_the_week_is_not_listed(tmp_path, capsys):
    """REQ-024 AC2: SPEC-0017 rule 3 (the day before Monday, and the Monday after Sunday)."""
    dates = {"REQ-001": "2026-10-04", "REQ-002": "2026-10-12"}
    doc = dated(dates | {"REQ-005": "2026-08-01", "REQ-006": "2026-10-20", "REQ-009": "2026-01-01"})
    assert listed(doc, tmp_path, capsys) == []


def test_ac4_an_unknown_week_is_listed_with_a_note_before_the_link(tmp_path, capsys):
    """REQ-024 AC4: SPEC-0017 rule 4 (never dropped: the usual line, the note, then the link)."""
    doc = dated({"REQ-001": "unknown", "REQ-002": "2026-10-08"})
    lines = section(render_doc(doc, tmp_path, capsys), "## Delivered")
    one = next(ln for ln in lines if ln.startswith("- REQ-001 "))
    assert one.startswith(
        '- REQ-001 "Alpha thing" is done: 2 acceptance criteria (AC1, AC2)' + NOTE
    )
    assert one.endswith("/docs/requirements.md#L3")
    assert one.index(NOTE) < one.index(" — https://")
    assert NOTE not in next(ln for ln in lines if ln.startswith("- REQ-002 "))


def test_ac4_ac6_a_row_without_the_field_reads_as_unknown(tmp_path, capsys):
    """REQ-024 AC4, AC6: SPEC-0017 rule 2 (a facts document written before this change is valid)."""
    doc = dated({"REQ-002": "2026-10-08"})
    lines = section(render_doc(doc, tmp_path, capsys), "## Delivered")
    noted = [ln.split(" ")[1] for ln in lines if ln.startswith("- REQ-") and NOTE in ln]
    assert noted == ["REQ-001", "REQ-005", "REQ-006", "REQ-009"]


def test_ac4_a_value_that_is_not_a_date_reads_as_unknown(tmp_path, capsys):
    """REQ-024 AC4: SPEC-0017 rule 4 (null, a number, a garbled string: unknown, not dropped)."""
    doc = dated({"REQ-001": None, "REQ-002": 5, "REQ-005": "last week", "REQ-006": "2026-13-45"})
    lines = section(render_doc(doc, tmp_path, capsys), "## Delivered")
    assert [ln.split(" ")[1] for ln in lines if ln.startswith("- REQ-") and NOTE in ln] == [
        "REQ-001",
        "REQ-002",
        "REQ-005",
        "REQ-006",
        "REQ-009",
    ]


def test_ac5_a_week_with_nothing_newly_done_prints_no_requirement_line(tmp_path, capsys):
    """REQ-024 AC5: SPEC-0017 rule 5 (the pull request lines are unchanged)."""
    doc = dated({r: "2026-09-01" for r in ALL_DONE})
    lines = section(render_doc(doc, tmp_path, capsys), "## Delivered")
    golden = (REPORT / "golden" / "kinds" / "report.md").read_text(encoding="utf-8")
    old = [
        ln
        for ln in section(golden.replace("<pr>", "PR #"), "## Delivered")
        if "was merged on" in ln
    ]
    assert lines == old and len(lines) == 4


def test_ac5_a_requirement_that_is_not_done_is_never_listed(tmp_path, capsys):
    """REQ-024 AC5: SPEC-0017 rule 5 (planned and in-progress stay out, with any date)."""
    doc = dated({"REQ-003": "2026-10-08", "REQ-007": "2026-10-08"})
    assert "REQ-003" not in listed(doc, tmp_path, capsys)
    assert "REQ-007" not in listed(doc, tmp_path, capsys)


def test_ac5_a_busy_week_keeps_its_single_line(tmp_path, capsys):
    """REQ-024 AC5: SPEC-0017 rule 5 (SPEC-0015: the requirements, then the one busy-week line)."""
    doc = json.loads((REPORT / "busy" / "facts.json").read_text(encoding="utf-8"))
    for row in doc["requirements"]:
        row["done_on"] = "2026-01-01"
    lines = section(render_doc(doc, tmp_path, capsys), "## Delivered")
    assert len(lines) == 1 and "pull requests were merged this week" in lines[0]


def test_ac6_the_facts_keep_schema_1_and_the_renderer_accepts_it(tmp_path, capsys):
    """REQ-024 AC6: SPEC-0017 rule 2 (schema 1 in the fixture; the field is optional)."""
    doc = dated({"REQ-001": "2026-10-08"})
    assert doc["schema"] == 1
    assert render_doc(doc, tmp_path, capsys).startswith("<!-- agk-product-report: 2026-W41 -->")


def test_ac7_the_workflow_checks_out_the_full_history(capsys):
    """REQ-024 AC7: SPEC-0017 rule 6 (a shallow checkout would make every week unknown)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    step = re.search(r"uses: actions/checkout@\S+[^\n]*\n(\s+with:\n(?:\s+[^\n]+\n)+)", text)
    assert step, "the workflow has a checkout step with a `with:` block"
    assert re.search(r"fetch-depth:\s*0\s*$", step.group(1), re.MULTILINE), step.group(1)


def test_ac8_the_other_sections_and_the_footer_equal_the_golden_of_before(tmp_path, capsys):
    """REQ-024 AC8: SPEC-0017 rule 7 (only Delivered differs from the report of the same facts)."""
    golden = (REPORT / "golden" / "kinds" / "report.md").read_text(encoding="utf-8")
    golden = golden.replace("<pr>", "PR #")
    out = render_doc(dated({"REQ-001": "2026-10-08"}), tmp_path, capsys)
    for heading in ("## Proven", "## Needs you", "## At risk", "## Cost"):
        assert section(out, heading) == section(golden, heading), heading
    assert (
        out.splitlines()[out.splitlines().index("---") :]
        == (golden.splitlines()[golden.splitlines().index("---") :])
    )


def test_ac8_the_renderer_still_imports_only_what_the_facts_rule_allows():
    """REQ-024 AC8: SPEC-0017 rule 8 (SPEC-0011 rule 13: the facts file and nothing else)."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= ALLOWED_IMPORTS, sorted(imported - ALLOWED_IMPORTS)


def test_ac8_unknown_requirements_print_todays_unknown_line(tmp_path, capsys):
    """REQ-024 AC8: SPEC-0017 rule 9 (`requirements` unknown: Delivered is as before)."""
    doc = kinds()
    doc["requirements"] = "unknown"
    lines = section(render_doc(doc, tmp_path, capsys), "## Delivered")
    assert lines[0].startswith("- unknown: requirements could not be read")
