"""Tests of the `hours_unknown` field of the cost totals item (SPEC-0024; REQ-031 AC1 to AC5).

The field counts the week's merged pull requests whose hours are `unknown`. It is data only: the
markdown and the inbox do not print it, and `report.json` carries the schema number 3. No network,
no model.
"""

from __future__ import annotations

import json

from test_product_report import FIXTURES

KINDS = FIXTURES / "report" / "kinds" / "facts.json"
BUSY = FIXTURES / "report" / "busy" / "facts.json"


def build(doc):
    import product_report as pr

    return pr.build_report(doc, pr.day_of(doc["today"]), None)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def totals(structure):
    found = [i for i in structure["sections"]["cost"] if i["kind"] == "week-totals"]
    assert len(found) == 1
    return found[0]


def merged_in_week(doc):
    return [p for p in doc["pull_requests"] if p["number"] in (5, 6, 7, 8)]


def test_ac1_the_count_is_the_number_of_merged_pull_requests_without_hours():
    """REQ-031 AC1: rule 1 (a missing or empty created time makes the hours unknown)."""
    doc = load(KINDS)
    first, second = merged_in_week(doc)[:2]
    first["created_at"], second["created_at"] = None, ""
    entry = totals(build(doc))
    assert entry["hours_unknown"] == 2
    assert entry["merged"] == 4 and entry["hours"] == "unknown"


def test_ac1_a_time_that_cannot_be_read_counts_too():
    """REQ-031 AC1: rule 1 (the same condition as the hours of the item)."""
    doc = load(KINDS)
    merged_in_week(doc)[0]["created_at"] = "not a time"
    assert totals(build(doc))["hours_unknown"] == 1


def test_ac2_the_field_is_present_and_zero_when_every_hours_is_known():
    """REQ-031 AC2: rule 1 (never omitted)."""
    entry = totals(build(load(KINDS)))
    assert entry["hours_unknown"] == 0 and entry["hours"] != "unknown"
    assert isinstance(entry["hours_unknown"], int) and not isinstance(entry["hours_unknown"], bool)


def test_ac2_the_field_follows_the_hours_in_the_kind_table():
    """REQ-031 AC2: rule 1 (the key order of the file is the order of the table)."""
    import product_report as pr

    fields = list(pr.ITEM_KINDS["week-totals"])
    assert fields[fields.index("hours") + 1] == "hours_unknown"
    assert list(totals(build(load(KINDS)))) == ["kind", *fields, "links"]


def test_ac3_a_busy_week_counts_every_merged_pull_request_not_only_the_listed():
    """REQ-031 AC3: rule 2 (the same set as `merged`, with no cost lines printed)."""
    doc = load(BUSY)
    week = [
        p for p in doc["pull_requests"] if p.get("merged_at", "") and "2026-10-0" in p["merged_at"]
    ]
    assert week
    structure = build(doc)
    entry = totals(structure)
    assert entry["busy"] is True and entry["hours_unknown"] == 0
    assert not [i for i in structure["sections"]["cost"] if i["kind"] == "pull-request-cost"]
    for pull in doc["pull_requests"][:3]:
        pull["created_at"] = None
    changed = totals(build(doc))
    blank = sum(1 for p in doc["pull_requests"][:3] if p.get("merged_at"))
    assert changed["merged"] == entry["merged"] and 0 < changed["hours_unknown"] <= blank


def test_ac4_the_markdown_does_not_print_the_field():
    """REQ-031 AC4: rule 3 (the line of the totals is as before)."""
    import product_report as pr

    doc = load(KINDS)
    merged_in_week(doc)[0]["created_at"] = None
    printed = pr.render_markdown(build(doc))
    assert "hours_unknown" not in printed and "hours in total: unknown" in printed


def test_ac5_the_report_schema_is_3_and_the_facts_schema_stays_1():
    """REQ-031 AC5: rule 4 (adding a field raises the number of report.json only)."""
    import product_report as pr

    assert pr.REPORT_SCHEMA == 3 and pr.SCHEMA == 1
    assert build(load(KINDS))["schema"] == 3
