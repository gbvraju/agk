"""Tests of the report structure and its renderer (SPEC-0022 rules 2 to 6 and 10, R1 and R2).

The opening, every section and the notices are built as items of the fixed kinds, Needs you as
groups of items, and the markdown and the inbox are rendered from the items alone. The existing
goldens are the proof that the printed report and the inbox did not change. No network, no model.
"""

from __future__ import annotations

import inspect
import json

import pytest
from test_product_report import CASES, FIXTURES

SECTIONS = ("delivered", "proven", "needs_you", "at_risk", "cost")
LINK_TARGETS = {"pull-request", "file", "directory", "issue", "search"}
ALL_KINDS = {
    "draft-spec",
    "proposed-adr",
    "question",
    "pull-request-ready",
    "pull-request-no-verdict",
    "overdue-residual",
    "unspecced-requirement",
    "residual-overdue",
    "pull-requests-open-long",
    "pull-requests-sent-back",
    "pull-requests-merged-no-verdict",
    "pull-requests-merged-not-cleared",
    "drift-audit",
    "requirement-done",
    "pull-request-merged",
    "pull-requests-merged",
    "requirement-proven",
    "requirement-not-proven",
    "planned-not-counted",
    "pull-request-cost",
    "week-totals",
    "unknown",
    "facts-commit",
    "working-tree-modified",
    "kit-version",
    "metrics-issue",
    "drift-audit-issue",
}


def structure_of(facts_path, week=None):
    import product_report as pr

    doc = json.loads(facts_path.read_text(encoding="utf-8"))
    today = pr.day_of(doc["today"])
    return doc, today, pr.build_report(doc, today, week)


def items_of(structure):
    for name in SECTIONS:
        if name == "needs_you":
            for group in structure["sections"][name]:
                yield from group["items"]
        else:
            yield from structure["sections"][name]
    yield from structure["notices"]


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac2_the_markdown_is_rendered_from_the_structure_alone(name, facts):
    """REQ-029 AC2: rule 2 (also from the structure after a trip through JSON)."""
    import product_report as pr

    doc, today, structure = structure_of(facts)
    printed = pr.render_report(doc, today, None)
    assert pr.render_markdown(structure) == printed
    assert pr.render_markdown(json.loads(json.dumps(structure))) == printed


def test_ac2_the_renderer_takes_the_structure_and_nothing_else():
    """REQ-029 AC2: rule 2 (a function of the structure: no facts, no day, no week)."""
    import product_report as pr

    assert list(inspect.signature(pr.render_markdown).parameters) == ["structure"]


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac1_the_structure_has_the_document_keys_and_items_of_the_fixed_kinds(name, facts):
    """REQ-029 AC1: rules 3 to 5 (keys, kinds, exactly the fields of a kind, links)."""
    import product_report as pr

    _, _, structure = structure_of(facts)
    assert list(structure) == ["schema", "week", "opening", "sections", "counts", "notices"]
    assert structure["schema"] == 5
    assert list(structure["opening"]) == ["first", "last", "as_of"]
    assert list(structure["sections"]) == ["delivered", "proven", "needs_you", "at_risk", "cost"]
    for item in items_of(structure):
        assert item["kind"] in pr.ITEM_KINDS, item
        required = {"kind", "links", *pr.ITEM_KINDS[item["kind"]]}
        allowed = required | set(pr.OPTIONAL_FIELDS.get(item["kind"], ()))
        assert required <= set(item) <= allowed, item
        for link in item["links"]:
            assert set(link) == {"to", "url"} and link["to"] in LINK_TARGETS, link
            assert link["url"].startswith("https://"), link


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac3_a_value_is_a_string_a_number_a_boolean_a_list_or_an_object_never_null(name, facts):
    """REQ-029 AC3: rule 6 (unknown stays the string `unknown`; no null, no float)."""

    def leaves(value):
        if isinstance(value, dict):
            for inner in value.values():
                yield from leaves(inner)
        elif isinstance(value, list):
            for inner in value:
                yield from leaves(inner)
        else:
            yield value

    _, _, structure = structure_of(facts)
    for leaf in leaves(structure):
        assert isinstance(leaf, str | int | bool) and not isinstance(leaf, float), leaf


def test_ac3_facts_that_could_not_be_read_give_unknown_items_and_strings():
    """REQ-029 AC3: rule 6 (the `unknown` item stands where the markdown prints unknown)."""
    _, _, structure = structure_of(FIXTURES / "report" / "dirty-unknown" / "facts.json")
    kinds = {item["kind"] for item in items_of(structure)}
    assert "unknown" in kinds
    unknown = [i for i in items_of(structure) if i["kind"] == "unknown"]
    assert all(isinstance(i["what"], str) and i["links"] for i in unknown)


def test_ac1_every_kind_of_the_covered_sections_is_built_by_some_golden_facts():
    """REQ-029 AC1: rule 5 (the kinds exist: a busy week, a dirty tree, unknowns, proofs)."""
    seen = set()
    for _, facts in CASES:
        _, _, structure = structure_of(facts)
        seen |= {item["kind"] for item in items_of(structure)}
    assert seen == ALL_KINDS, seen ^ ALL_KINDS


def test_ac1_the_kinds_of_the_table_are_all_the_kinds_built_and_the_line_kind_is_gone():
    """REQ-029 AC1: rule 5 (the table is closed; the transitional kind of part R1 is removed)."""
    import product_report as pr

    assert set(pr.ITEM_KINDS) == ALL_KINDS
    assert "line" not in pr.RENDER and "line" not in pr.ITEM_KINDS
    assert set(pr.RENDER) == set(pr.ITEM_KINDS)


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac1_needs_you_is_a_list_of_groups_with_a_count(name, facts):
    """REQ-029 AC1: rule 3 (`{"group", "count", "items"}`; `unknown` for an unknown item)."""
    _, _, structure = structure_of(facts)
    for group in structure["sections"]["needs_you"]:
        assert list(group) == ["group", "count", "items"] and group["items"], group
        assert group["group"] in {
            "ready",
            "spec",
            "adr",
            "question",
            "pull-request",
            "residual",
            "requirement",
        }
        unknown = any(i["kind"] == "unknown" for i in group["items"])
        assert group["count"] == ("unknown" if unknown else len(group["items"])), group


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac1_a_title_stands_only_in_a_single_entry_of_the_two_kinds_that_print_it(name, facts):
    """REQ-029 AC1: rule 5 (grouped lines print no titles; merged-without-clearance prints none)."""
    _, _, structure = structure_of(facts)
    for entry in items_of(structure):
        if not entry["kind"].startswith("pull-requests-") or "entries" not in entry:
            continue
        titled = entry["kind"] in ("pull-requests-open-long", "pull-requests-sent-back")
        assert len(entry["links"]) == len(entry["entries"]), entry
        for each in entry["entries"]:
            assert ("title" in each) == (titled and len(entry["entries"]) == 1), entry


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_ac2_the_inbox_is_built_from_the_same_groups_as_needs_you(name, facts):
    """REQ-029 AC2: rule 2 (the inbox prints the groups of the report's Needs you)."""
    import product_report as pr

    doc, today, structure = structure_of(facts)
    groups = structure["sections"]["needs_you"]
    inbox = pr.render_inbox(doc, today)
    assert (pr.group_lines(groups) or ["nothing waits for you"]) == inbox.splitlines()[
        2 : 2 + max(1, len(pr.group_lines(groups)))
    ]
