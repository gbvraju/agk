"""Tests of the estimate in the metrics (SPEC-0018 rules 1 to 4, REQ-025). No network, no model.

The brief templates, `common.parse_estimate` (the body of a pull request) and the metrics record
(`estimated_size`, `estimated_hours`, `actual_hours`). The facts and the report are tested in
`test_facts_estimate.py` and `test_product_report_estimate.py`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures" / "metrics"
TEMPLATES = (
    ROOT / "docs" / "briefs" / "TEMPLATE.md",
    ROOT / "kit" / "templates" / "playbook" / "brief-day.md",
    ROOT / "kit" / "templates" / "playbook" / "brief-overnight.md",
)
U = "unknown"


def parse_estimate(body):
    """`common.parse_estimate`, imported here so a missing one fails each test, not the file."""
    from common import parse_estimate as parse

    return parse(body)


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_ac1_an_item_of_each_brief_template_carries_size_and_expected(template):
    """REQ-025 AC1: SPEC-0018 rule 1 (the two lines, inside the item, before the report format)."""
    text = template.read_text(encoding="utf-8")
    item, _, report = text.partition("## Report format")
    assert "- Size: S|M|L" in item and "- Expected: <low>-<high> hours" in item
    assert "Size:" in report and "Expected:" in report and "Brief:" in report


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Size: M\nExpected: 2-4 hours\n", ("M", "2-4")),
        (
            "Brief: docs/briefs/a.md#item-1\n- Size: S\n- Expected: 0.5-1.5 hours\n",
            ("S", "0.5-1.5"),
        ),
        ("Advances: REQ-001\r\nSize: L\r\nExpected: 6-9 hours\r\n", ("L", "6-9")),
        ("Size: M\nExpected: 3-3 hours\n", ("M", "3-3")),
    ],
)
def test_ac2_a_body_with_both_lines_gives_the_size_and_the_hours(body, expected):
    """REQ-025 AC2: SPEC-0018 rule 2 (an optional list marker; a range of equal ends is valid)."""
    assert parse_estimate(body) == expected


@pytest.mark.parametrize(
    "body",
    [
        None,
        5,
        "",
        "Advances: REQ-001\n",
        "Size: M\n",
        "Expected: 2-4 hours\n",
        "Size: XL\nExpected: 2-4 hours\n",
        "Size: m\nExpected: 2-4 hours\n",
        "Size: M\nExpected: 5-2 hours\n",
        "Size: M\nExpected: two hours\n",
        "Size: M\nExpected: 2 - 4 hours\n",
        "Size: M\nExpected: 2–4 hours\n",
        "Size: M\nExpected: 2-4 h\n",
        "Size: M\nExpected: -2-4 hours\n",
        "Size: M\nSize: S\nExpected: 2-4 hours\n",
        "Size: M\nExpected: 2-4 hours\nExpected: 3-5 hours\n",
    ],
)
def test_ac3_a_missing_or_malformed_line_makes_both_unknown(body):
    """REQ-025 AC3: SPEC-0018 rule 2 (never a guess, never zero)."""
    assert parse_estimate(body) == (U, U)


def pull_case(tmp_path: Path, body, authored, merged="2026-10-07T06:00:00Z") -> Path:
    """The metrics fixture `fix-lists-cleared` with #102 body, commit dates and merge time."""
    case = tmp_path / "case"
    shutil.copytree(FIXTURES / "fix-lists-cleared", case)
    pull = json.loads((case / "pull-102.json").read_text())
    if body is not None:
        pull["body"] = body
    pull["merged_at"] = merged
    (case / "pull-102.json").write_text(json.dumps(pull))
    commits = json.loads((case / "commits-102.json").read_text())
    for commit, when in zip(commits, authored, strict=False):
        commit["commit"] = {"author": {"date": when}}
    (case / "commits-102.json").write_text(json.dumps(commits))
    return case


def row(repo, case: Path) -> dict[str, str]:
    from test_metrics import metrics, table

    proc = metrics(repo, case)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return table(proc.stdout)[102]


def test_ac2_the_record_reads_the_estimate_from_the_body_alone(repo, tmp_path):
    """REQ-025 AC2: SPEC-0018 rule 3 (the columns `estimated_size` and `estimated_hours`)."""
    case = pull_case(tmp_path, "Size: M\nExpected: 2-4 hours\n", [])
    record = row(repo, case)
    assert (record["estimated_size"], record["estimated_hours"]) == ("M", "2-4")


def test_ac3_a_body_without_the_lines_gives_unknown_in_the_record(repo, tmp_path):
    """REQ-025 AC3: SPEC-0018 rule 3."""
    for body in ("Advances: REQ-001\n", "Size: M\nExpected: nope\n"):
        record = row(repo, pull_case(tmp_path / body[:4], body, []))
        assert (record["estimated_size"], record["estimated_hours"]) == (U, U)


def test_ac4_actual_hours_runs_from_the_earliest_author_date_to_the_merge(repo, tmp_path):
    """REQ-025 AC4: SPEC-0018 rule 3 (not the first commit listed; `hours_open_to_merge` stays)."""
    dates = ["2026-10-06T10:00:00Z", "2026-10-05T20:30:00Z", "2026-10-06T08:15:00Z"]
    record = row(repo, pull_case(tmp_path, None, dates))
    assert record["actual_hours"] == "33.5"
    assert record["hours_open_to_merge"] == "30.0"  # 2026-10-06T00:00:00Z to 2026-10-07T06:00:00Z


def test_ac4_an_unreadable_commit_date_makes_actual_hours_unknown(repo, tmp_path):
    """REQ-025 AC4: SPEC-0018 rule 3 (a date that is not one is not skipped)."""
    for dates in (["2026-10-05T20:30:00Z", "yesterday"], []):
        assert row(repo, pull_case(tmp_path / str(len(dates)), None, dates))["actual_hours"] == U


def test_ac6_a_pull_request_without_the_lines_reads_unknown_and_is_not_rewritten(repo):
    """REQ-025 AC6: SPEC-0018 rule 4 (the fixture is one made before this change)."""
    record = row(repo, FIXTURES / "fix-lists-cleared")
    assert (record["estimated_size"], record["estimated_hours"], record["actual_hours"]) == (U,) * 3


def test_ac7_the_size_changes_no_other_column(repo, tmp_path):
    """REQ-025 AC7: SPEC-0018 rule 7 (`Size` is recorded and not compared with `cost_class`)."""
    small = row(repo, pull_case(tmp_path / "s", "Size: S\nExpected: 2-4 hours\n", []))
    large = row(repo, pull_case(tmp_path / "l", "Size: L\nExpected: 2-4 hours\n", []))
    for column in small:
        if column != "estimated_size":
            assert small[column] == large[column], column
    assert (small["estimated_size"], large["estimated_size"]) == ("S", "L")
