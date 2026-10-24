"""Kit-only tests of the schema file for the group `ready` and the number 4 (SPEC-0030 rule 8)."""

from __future__ import annotations

import copy
import json

from jsonschema_lite import errors
from test_report_wiring import goldens, kind_schemas, schema


def ready_schema() -> dict:
    found = [
        s
        for s in kind_schemas(schema())
        if s["properties"]["kind"] == {"const": "pull-request-ready"}
    ]
    assert len(found) == 1
    return found[0]


def test_ac7_the_schema_file_requires_the_number_4_and_allows_the_group():
    """REQ-037 AC7"""
    document = schema()
    assert document["properties"]["schema"] == {"const": 4}
    assert "ready" in json.dumps(document["properties"]["sections"]["properties"]["needs_you"])
    node = ready_schema()
    assert node["required"] == ["kind", "number", "title", "links"]
    assert node["properties"]["number"] == {"type": "integer"}


def test_ac7_every_golden_has_the_number_4_and_validates():
    """REQ-037 AC7"""
    for name, document in goldens():
        assert document["schema"] == 4, name
        assert errors(document, schema()) == [], name


def test_ac7_a_ready_item_validates_and_a_malformed_one_does_not():
    """REQ-037 AC7"""
    name, document = next((n, d) for n, d in goldens() if d["sections"]["needs_you"])
    link = {"to": "pull-request", "url": "https://example.test/pull/9"}
    item = {"kind": "pull-request-ready", "number": 9, "title": "t", "links": [link]}
    good = copy.deepcopy(document)
    good["sections"]["needs_you"].insert(0, {"group": "ready", "count": 1, "items": [item]})
    assert errors(good, schema()) == [], name
    for bad_item in (
        {**item, "number": "9"},
        {k: v for k, v in item.items() if k != "title"},
        {**item, "extra": 1},
    ):
        bad = copy.deepcopy(good)
        bad["sections"]["needs_you"][0]["items"] = [bad_item]
        assert errors(bad, schema()) != [], bad_item
