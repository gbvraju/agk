"""Tests of the estimate in the Cost totals (SPEC-0018 rule 6, REQ-025). No network, no model.

The facts are the report fixture `kinds` (week 2026-W41; merged in it: #5, #6, #7, #8) with
`estimated_hours` and `actual_hours` set on the pull request rows, or left out.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from product_report import main

ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).parent / "fixtures" / "report"
SOURCE = ROOT / "scripts" / "agk" / "product_report.py"
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


def facts(name: str = "kinds") -> dict:
    return json.loads((REPORT / name / "facts.json").read_text(encoding="utf-8"))


def declared(doc: dict, rows: dict) -> dict:
    """Set `estimated_hours` and `actual_hours` on the pull requests named (the rest have none)."""
    for p in doc["pull_requests"]:
        if p["number"] in rows:
            p["estimated_hours"], p["actual_hours"] = rows[p["number"]]
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


def totals(doc: dict, tmp_path: Path, capsys) -> str:
    """The text of the Cost totals line, without its link."""
    line = next(
        ln for ln in section(render_doc(doc, tmp_path, capsys), "## Cost") if "This week:" in ln
    )
    return line.split(" — ")[0]


def test_ac5_the_totals_line_counts_the_pull_requests_within_range(tmp_path, capsys):
    """REQ-025 AC5: SPEC-0018 rule 6 (inclusive at both ends; above and below are out)."""
    rows = {5: ("2-4", "2.0"), 6: ("2-4", "4.0"), 7: ("2-4", "4.1"), 8: ("2-4", "1.9")}
    assert totals(declared(facts(), rows), tmp_path, capsys).endswith(
        "; estimate: 2 of 4 within range"
    )


def test_ac5_an_unknown_value_is_in_neither_count(tmp_path, capsys):
    """REQ-025 AC5: SPEC-0018 rule 6 (not a miss)."""
    rows = {5: ("2-4", "3.0"), 6: ("unknown", "3.0"), 7: ("2-4", "unknown"), 8: ("9-12", "3.0")}
    assert totals(declared(facts(), rows), tmp_path, capsys).endswith(
        "; estimate: 1 of 2 within range"
    )


def test_ac5_a_week_with_no_estimate_says_so(tmp_path, capsys):
    """REQ-025 AC5: SPEC-0018 rule 6 (M is 0)."""
    assert totals(facts(), tmp_path, capsys).endswith("; estimate: none declared this week")


def test_ac5_only_the_pull_requests_merged_in_the_week_are_counted(tmp_path, capsys):
    """REQ-025 AC5: SPEC-0018 rule 6 (an open pull request and an earlier merge are not)."""
    rows = {5: ("2-4", "3.0"), 9: ("2-4", "3.0"), 14: ("2-4", "3.0")}
    assert totals(declared(facts(), rows), tmp_path, capsys).endswith(
        "; estimate: 1 of 1 within range"
    )


def test_ac5_the_ending_is_on_the_same_line_before_the_link_in_a_busy_week(tmp_path, capsys):
    """REQ-025 AC5: SPEC-0018 rule 6 (SPEC-0015: the totals line is the section's only line)."""
    doc = facts("busy")
    merged = [p["number"] for p in doc["pull_requests"] if p["state"] == "merged"]
    lines = section(
        render_doc(declared(doc, {merged[0]: ("1-9", "5.0")}), tmp_path, capsys), "## Cost"
    )
    assert len(lines) == 1
    text, _, link = lines[0].partition(" — ")
    assert text.endswith("; estimate: 1 of 1 within range") and "merged%3A" in link


def test_ac6_a_report_of_facts_without_the_fields_differs_only_by_the_ending(tmp_path, capsys):
    """REQ-025 AC6: SPEC-0018 rule 6 (the report before this change, line by line)."""
    golden = (REPORT / "golden" / "kinds" / "report.md").read_text(encoding="utf-8")
    golden = golden.replace("<pr>", "PR #")
    out = render_doc(facts(), tmp_path, capsys)
    ending = "; estimate: none declared this week"
    assert out.replace(ending, "") == golden.replace(ending, "")
    assert out.count(ending) == 1


def test_ac7_the_kit_estimates_nothing(tmp_path, capsys):
    """REQ-025 AC7: SPEC-0018 rule 7 (a declared range is only counted: no number is made up)."""
    rows = {5: ("2-4", "3.0")}
    one = totals(declared(facts(), rows), tmp_path, capsys)
    two = totals(declared(facts(), rows | {6: ("unknown", "unknown")}), tmp_path, capsys)
    assert one == two
    source = SOURCE.read_text(encoding="utf-8")
    assert "buffer" not in source and "model" not in source.lower()


def test_ac8_the_renderer_still_imports_only_what_the_facts_rule_allows():
    """REQ-025 AC8: SPEC-0018 rule 8 (SPEC-0011 rule 13: the facts file and nothing else)."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= ALLOWED_IMPORTS, sorted(imported - ALLOWED_IMPORTS)
