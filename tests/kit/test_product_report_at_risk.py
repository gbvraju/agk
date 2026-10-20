"""Tests of the At risk section by kind (SPEC-0016, REQ-023). No network, no model, no `gh`.

A kind with two or more pull requests is one line that names every number, each its own link;
a kind with one keeps today's line. The facts are the report fixture `kinds` with pull request
rows added or removed, so the dates are those of that fixture (today 2026-10-14, week 2026-W41).
"""

from __future__ import annotations

import ast
import copy
import json
import re
from pathlib import Path

from product_report import main

REPORT = Path(__file__).parent / "fixtures" / "report"
SOURCE = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "product_report.py"
URL = "https://github.com/demo-org/demo-repo/pull/"
PR = "PR " + "#"
HEAD = "a" * 40
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


def link(number: int) -> str:
    return f"[#{number}]({URL}{number})"


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


def at_risk(doc: dict, tmp_path: Path, capsys) -> list[str]:
    return section(render_doc(doc, tmp_path, capsys), "## At risk")


def only(doc: dict, keep: set[int]) -> dict:
    """The facts with only the pull requests numbered in `keep`."""
    doc["pull_requests"] = [p for p in doc["pull_requests"] if p["number"] in keep]
    return doc


def merged_row(doc: dict, number: int, verdicts: list, head: str = HEAD) -> None:
    row = copy.deepcopy(next(p for p in doc["pull_requests"] if p["number"] == 5))
    row.update({"number": number, "title": f"Change number {number}", "verdicts": verdicts})
    row.update({"head": head, "state": "merged", "merged_at": "2026-10-08T10:00:00Z"})
    doc["pull_requests"].append(row)


def unreviewed(doc: dict, numbers: list[int]) -> dict:
    for number in numbers:
        merged_row(doc, number, [])
    return only(doc, set(numbers))


def test_ac1_pull_requests_merged_with_no_verdict_are_one_line_in_ascending_order(tmp_path, capsys):
    """REQ-023 AC1: SPEC-0016 rules 3 and 4 (ascending, each number its own link, never a range)."""
    doc = unreviewed(kinds(), [12, 5, 6, 20])
    lines = [ln for ln in at_risk(doc, tmp_path, capsys) if "merged" in ln]
    expected = f"- PRs {link(5)}, {link(6)}, {link(12)} and {link(20)} were merged with no verdict"
    assert lines == [expected]


def test_ac1_two_pull_requests_merged_before_their_last_commit_was_cleared(tmp_path, capsys):
    """REQ-023 AC1: SPEC-0016 rule 4 (two numbers joined by `and`, no trailing link)."""
    doc = kinds()
    for number in (5, 12):
        merged_row(
            doc, number, [{"at": "2026-10-08T09:00:00Z", "kind": "cleared", "sha": "ccccccc"}]
        )
    only(doc, {5, 12})
    lines = [ln for ln in at_risk(doc, tmp_path, capsys) if "merged" in ln]
    expected = f"- PRs {link(5)} and {link(12)} were merged before their last commit was cleared"
    assert lines == [expected]


def test_ac1_ac3_open_too_long_and_sent_back_keep_their_value_in_brackets(tmp_path, capsys):
    """REQ-023 AC1, AC3: SPEC-0016 rules 3 and 4 (the value of the single line, no title)."""
    lines = at_risk(kinds(), tmp_path, capsys)
    assert f"- PRs {link(9)} (13 days) and {link(13)} (12 days) have been open" in lines
    assert f"- PRs {link(6)} (2 times) and {link(12)} (1 time) were sent back" in lines


def test_ac3_a_grouped_line_prints_no_title(tmp_path, capsys):
    """REQ-023 AC3: SPEC-0016 rule 4 (a grouped line prints no title)."""
    grouped = [ln for ln in at_risk(kinds(), tmp_path, capsys) if ln.startswith("- PRs ")]
    assert len(grouped) == 2
    assert not [ln for ln in grouped if "Change number" in ln or PR in ln]


def test_ac2_a_kind_with_one_pull_request_is_the_line_printed_before(tmp_path, capsys):
    """REQ-023 AC2: SPEC-0016 rule 2 (title, value and trailing link)."""
    lines = at_risk(only(kinds(), {9, 8}), tmp_path, capsys)
    assert f'- {PR}9 "Change number 9" has been open for 13 days — {URL}9' in lines
    assert f"- {PR}8 was merged before its last commit was cleared — {URL}8" in lines
    assert not [ln for ln in lines if ln.startswith("- PRs ")]


def test_ac2_no_kind_with_two_pull_requests_leaves_the_section_as_before(tmp_path, capsys):
    """REQ-023 AC2: SPEC-0016 rules 2 and 6 (the whole section, in today's order)."""
    lines = at_risk(only(kinds(), {9, 6, 8}), tmp_path, capsys)
    assert [ln.split(" — ")[0] for ln in lines] == [
        "- Residual overdue since 2026-09-01 (43 days): 2026-08-01: an old item",
        lines[1].split(" — ")[0],
        f'- {PR}9 "Change number 9" has been open for 13 days',
        f'- {PR}6 "Change number 6" was sent back 2 times',
        "- drift audit: 4 findings (D1 0, D2 0, D3 2, D4 1, D5 0, D6 0, D7 1)",
        f"- {PR}8 was merged before its last commit was cleared",
    ]


def test_ac4_every_pull_request_at_risk_before_is_named_after(tmp_path, capsys):
    """REQ-023 AC4: SPEC-0016 rule 5 (33 of one kind are all named, no count)."""
    numbers = list(range(100, 133))
    doc = unreviewed(kinds(), numbers)
    lines = [ln for ln in at_risk(doc, tmp_path, capsys) if "merged" in ln]
    assert len(lines) == 1
    named = [int(n) for n in re.findall(r"\[#(\d+)\]\(", lines[0])]
    assert named == numbers
    assert lines[0].endswith("were merged with no verdict")


def test_ac4_the_numbers_of_the_section_are_those_of_the_section_before(tmp_path, capsys):
    """REQ-023 AC4: SPEC-0016 rule 5 (the committed golden of `kinds` names the same numbers)."""
    golden = (REPORT / "golden" / "kinds" / "report.md").read_text(encoding="utf-8")
    old = {int(n) for ln in section(golden, "## At risk") for n in re.findall(r"<pr>(\d+)", ln)}
    new = {int(n) for ln in at_risk(kinds(), tmp_path, capsys) for n in re.findall(r"#(\d+)", ln)}
    assert old and old <= new


def test_ac5_overdue_residuals_and_the_drift_line_are_never_grouped(tmp_path, capsys):
    """REQ-023 AC5: SPEC-0016 rule 1."""
    lines = at_risk(kinds(), tmp_path, capsys)
    residuals = [ln for ln in lines if ln.startswith("- Residual overdue since")]
    assert len(residuals) == 2
    drift = [ln for ln in lines if ln.startswith("- drift audit:")]
    assert len(drift) == 1 and drift[0].endswith("/issues/4")


def test_ac5_a_grouped_line_takes_the_place_of_its_lowest_numbered_pull_request(tmp_path, capsys):
    """REQ-023 AC5: SPEC-0016 rule 6 (residuals, open, sent back, the drift line, then merged)."""
    lines = at_risk(kinds(), tmp_path, capsys)
    order = [
        "- Residual overdue since 2026-09-01",
        "- Residual overdue since 2026-10-13",
        f"- PRs {link(9)}",
        f"- PRs {link(6)}",
        "- drift audit:",
        f"- {PR}8 was merged before",
    ]
    assert [next(i for i, ln in enumerate(lines) if ln.startswith(p)) for p in order] == list(
        range(6)
    )


def test_ac6_the_renderer_still_imports_only_what_the_facts_rule_allows():
    """REQ-023 AC6: SPEC-0016 rule 8 (SPEC-0011 rule 13: the facts file and nothing else)."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= ALLOWED_IMPORTS, sorted(imported - ALLOWED_IMPORTS)


def test_ac7_unknown_pull_requests_print_todays_unknown_line_and_do_not_group(tmp_path, capsys):
    """REQ-023 AC7: SPEC-0016 rule 9."""
    doc = kinds()
    doc["pull_requests"] = "unknown"
    lines = at_risk(doc, tmp_path, capsys)
    assert any(ln.startswith("- unknown: pull requests could not be read") for ln in lines)
    assert not [ln for ln in lines if ln.startswith("- PRs ")]


def test_ac8_the_other_sections_and_the_footer_equal_the_golden_of_before(tmp_path, capsys):
    """REQ-023 AC8: SPEC-0016 rule 7 (only At risk differs from the report of the same facts)."""
    golden = (REPORT / "golden" / "kinds" / "report.md").read_text(encoding="utf-8")
    golden = golden.replace("<pr>", PR)
    out = render_doc(kinds(), tmp_path, capsys)
    for heading in ("## Proven", "## Needs you", "## Cost"):  # Delivered is REQ-024's
        assert section(out, heading) == section(golden, heading), heading
    assert (
        out.splitlines()[out.splitlines().index("---") :]
        == (golden.splitlines()[golden.splitlines().index("---") :])
    )
