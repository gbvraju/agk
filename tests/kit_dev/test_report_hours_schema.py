"""Kit-only tests of the schema file for `hours_unknown` and the number 4 (SPEC-0024 rule 4)."""

from __future__ import annotations

import json

from jsonschema_lite import errors
from test_report_wiring import GOLDENS, goldens, kind_schemas, mutate, schema


def totals_schema() -> dict:
    found = [
        s for s in kind_schemas(schema()) if s["properties"]["kind"] == {"const": "week-totals"}
    ]
    assert len(found) == 1
    return found[0]


def totals_item(document: dict) -> dict:
    return next(i for i in document["sections"]["cost"] if i["kind"] == "week-totals")


def with_totals() -> list[tuple[str, dict]]:
    return [
        (n, d)
        for n, d in goldens()
        if any(i["kind"] == "week-totals" for i in d["sections"]["cost"])
    ]


def test_ac5_the_schema_file_fixes_the_number_2():
    """REQ-031 AC5: rule 4."""
    assert schema()["properties"]["schema"] == {"const": 4}


def test_ac5_the_totals_item_requires_hours_unknown_as_a_whole_number():
    """REQ-031 AC5: rule 4 (an integer, required; the validator has no `minimum`, Q-K4-229)."""
    node = totals_schema()
    assert "hours_unknown" in node["required"]
    assert node["properties"]["hours_unknown"] == {"type": "integer"}


def test_ac5_every_golden_has_the_number_2_and_the_field_and_validates():
    """REQ-031 AC5: rule 4 (the goldens hold the number and the field)."""
    found = with_totals()
    assert len(found) >= 4
    for name, document in goldens():
        assert document["schema"] == 4, name
        assert errors(document, schema()) == [], name
    for _, document in found:
        entry = totals_item(document)
        assert (
            isinstance(entry["hours_unknown"], int)
            and 0 <= entry["hours_unknown"] <= entry["merged"]
        )


def test_ac5_a_missing_a_string_and_an_extra_field_fail():
    """REQ-031 AC5: rule 4 (the list of fields is closed)."""
    name, document = with_totals()[0]

    def drop(d):
        del totals_item(d)["hours_unknown"]

    def text(d):
        totals_item(d)["hours_unknown"] = "unknown"

    def extra(d):
        totals_item(d)["hours_known"] = 1

    def old(d):
        d["schema"] = 1

    for change in (drop, text, extra, old):
        assert errors(mutate(document, change), schema()), (name, change.__name__)
    assert GOLDENS.is_dir() and json.dumps(document)
