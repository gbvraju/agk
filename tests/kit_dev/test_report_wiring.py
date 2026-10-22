"""Kit-only tests of the report.json schema: file, validator, goldens, table (SPEC-0022)."""

from __future__ import annotations

import copy
import json
import sys

from conftest import KIT_ROOT, manifest
from jsonschema_lite import KEYWORDS, errors

SCHEMA = KIT_ROOT / "kit" / "report-schema.json"
GOLDENS = KIT_ROOT / "tests" / "kit" / "fixtures" / "report" / "golden"
NAMES = ("dashboard", "slack", "website", "portal", "cloudflare", "chat message")


def schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def goldens() -> list[tuple[str, dict]]:
    found = sorted(GOLDENS.glob("*/report.json"))
    return [(p.parent.name, json.loads(p.read_text(encoding="utf-8"))) for p in found]


def kind_schemas(node) -> list[dict]:
    """Every schema in the file that fixes a `kind` constant (one per kind and place)."""
    found: list[dict] = []
    if isinstance(node, dict):
        kind = node.get("properties", {}).get("kind")
        if isinstance(kind, dict) and "const" in kind:
            found.append(node)
        for value in node.values():
            found += kind_schemas(value)
    elif isinstance(node, list):
        for value in node:
            found += kind_schemas(value)
    return found


def keywords_used(node) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            if key == "properties":
                for sub in value.values():
                    found |= keywords_used(sub)
            elif key in ("items", "additionalProperties", "oneOf"):
                for sub in value if isinstance(value, list) else [value]:
                    found |= keywords_used(sub)
    return found


def test_ac4_the_schema_is_kit_only_and_uses_only_the_validators_keywords():
    """REQ-029 AC4: rule 7 (not installed, like the facts schema; hand-written)."""
    assert SCHEMA.is_file() and "kit/report-schema.json" not in manifest()["verbatim"]
    assert keywords_used(schema()) - {"$schema", "title", "description"} <= KEYWORDS


def test_ac4_the_schema_const_equals_the_documents_schema_number():
    """REQ-029 AC4: rule 7."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import product_report

    assert schema()["properties"]["schema"] == {"const": product_report.REPORT_SCHEMA}


def test_ac4_every_golden_validates():
    """REQ-029 AC4: rule 7 (a report.json for every golden facts)."""
    found = goldens()
    assert len(found) >= 14
    for name, document in found:
        assert errors(document, schema()) == [], name


def mutate(document: dict, change) -> dict:
    changed = copy.deepcopy(document)
    change(changed)
    return changed


def test_ac4_a_broken_document_does_not_validate():
    """REQ-029 AC4: rule 7 (an extra key, an extra kind, an extra field, a missing field, ...)."""
    document = dict(goldens())["facts-ok"]
    rules = {
        "an extra top-level key": lambda d: d.update(extra=1),
        "a missing top-level key": lambda d: d.pop("notices"),
        "another schema number": lambda d: d.update(schema=2),
        "an extra section": lambda d: d["sections"].update(trend=[]),
        "an extra opening key": lambda d: d["opening"].update(extra="x"),
        "an unknown kind": lambda d: d["notices"][0].update(kind="made-up"),
        "an extra field": lambda d: d["notices"][0].update(extra="x"),
        "a missing field": lambda d: d["notices"][0].pop("commit"),
        "a missing links": lambda d: d["notices"][0].pop("links"),
        "a link target outside the list": lambda d: d["sections"]["delivered"][0]["links"][
            0
        ].update(to="page"),
        "a null": lambda d: d["notices"][0].update(commit=None),
        "a float": lambda d: d["sections"]["cost"][-1].update(merged=1.5),
        "a kind in another section": lambda d: d["sections"]["delivered"].append(d["notices"][0]),
        "a group without a count": lambda d: d["sections"]["needs_you"][0].pop("count"),
    }
    for label, change in rules.items():
        assert errors(mutate(document, change), schema()), label


def test_ac4_the_schema_has_exactly_the_kinds_and_fields_of_the_table():
    """REQ-029 AC4: rules 5 and 7 (the table of product_report.py and the schema agree)."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import product_report as pr

    found: dict[str, list[dict]] = {}
    for node in kind_schemas(schema()):
        found.setdefault(node["properties"]["kind"]["const"], []).append(node)
    assert set(found) == set(pr.ITEM_KINDS)
    for kind, nodes in found.items():
        required = {"kind", "links", *pr.ITEM_KINDS[kind]}
        allowed = required | set(pr.OPTIONAL_FIELDS.get(kind, ()))
        for node in nodes:
            assert set(node["required"]) == required, kind
            assert set(node["properties"]) == allowed, kind
            assert node.get("additionalProperties") is False, kind


def test_ac8_the_schema_and_the_script_name_no_project_and_no_reader():
    """REQ-029 AC8: rule 10 (generic: no project, no dashboard, no chat)."""
    for path in (SCHEMA, KIT_ROOT / "scripts" / "agk" / "product_report.py"):
        text = path.read_text(encoding="utf-8").lower()
        for word in NAMES:
            assert word not in text, (path.name, word)
