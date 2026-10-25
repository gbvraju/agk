"""The report group "Ready to merge" (SPEC-0030 rule 8; REQ-037 AC7). No network, no model.

The facts carry `head_cleared` for open pull requests; the decisions section gains the group
`ready`, the first, with one `pull-request-ready` item (`number`, `title`) for each open pull
request whose head is cleared. The markdown prints `PR #<n> "<title>" is ready to merge`, linked,
and `report.json` takes schema number 4.
"""

from __future__ import annotations

import copy

from test_report_counts import KINDS, build, items, load, pull

LINK = "https://github.com/demo-org/demo-repo/pull/"


def open_pull(doc: dict, number: int, **fields) -> dict:
    """An open pull request of the fixture (no verdict yet) with the given fields set."""
    p = pull(doc, number)
    assert p["state"] == "open"
    p.update(fields)
    return p


def ready_group(structure: dict) -> dict | None:
    return next((g for g in structure["sections"]["needs_you"] if g["group"] == "ready"), None)


def test_ac7_an_open_pull_request_with_a_cleared_head_is_listed_in_the_first_group():
    """REQ-037 AC7"""
    doc = load(KINDS)
    open_pull(doc, 9, head_cleared="yes")
    open_pull(doc, 10, head_cleared="no")
    open_pull(doc, 11, head_cleared="unknown")
    structure = build(doc)
    groups = structure["sections"]["needs_you"]
    assert groups[0]["group"] == "ready" and groups[0]["count"] == 1
    entry = groups[0]["items"][0]
    assert entry["kind"] == "pull-request-ready"
    assert entry["number"] == 9 and entry["title"] == "Change number 9"
    assert entry["links"] == [{"to": "pull-request", "url": f"{LINK}9"}]
    assert set(entry) == {"kind", "number", "title", "links"}


def test_ac7_several_are_listed_in_the_order_of_their_numbers():
    """REQ-037 AC7"""
    doc = load(KINDS)
    for number in (11, 9, 10):
        open_pull(doc, number, head_cleared="yes")
    group = ready_group(build(doc))
    assert [i["number"] for i in group["items"]] == [9, 10, 11] and group["count"] == 3


def test_ac7_no_cleared_open_pull_request_means_no_group():
    """REQ-037 AC7"""
    assert ready_group(build(load(KINDS))) is None
    doc = load(KINDS)
    for p in doc["pull_requests"]:
        if p["state"] == "merged":
            p["head_cleared"] = "yes"  # a merged pull request is never "ready to merge"
    assert ready_group(build(doc)) is None


def test_ac7_a_closed_pull_request_is_not_listed():
    """REQ-037 AC7"""
    doc = load(KINDS)
    p = open_pull(doc, 9, head_cleared="yes")
    p["state"] = "closed"
    assert ready_group(build(doc)) is None


def test_ac7_an_open_pull_request_whose_clearance_cannot_be_read_adds_the_unknown_item():
    """REQ-037 AC7 (SPEC-0026 rule 5): not listed; the count is unknown, never a number."""
    doc = load(KINDS)
    open_pull(doc, 9, head_cleared="yes")
    open_pull(doc, 10, verdicts="unknown", head_cleared="unknown")
    structure = build(doc)
    group = ready_group(structure)
    assert [i["kind"] for i in group["items"]] == ["pull-request-ready", "unknown"]
    assert group["count"] == "unknown" and structure["counts"]["needs_you"] == "unknown"
    unknown = group["items"][1]
    assert unknown["what"] == "the clearance of 1 open pull request"
    assert unknown["links"] == [{"to": "pull-request", "url": f"{LINK}10"}]


def test_ac7_the_counts_include_the_group():
    """REQ-037 AC7 (SPEC-0026): the needs-you count counts the ready items by meaning."""
    doc = load(KINDS)
    before = build(copy.deepcopy(doc))["counts"]["needs_you"]
    open_pull(doc, 9, head_cleared="yes")
    after = build(doc)["counts"]["needs_you"]
    assert isinstance(before, int) and after == before + 1


def test_ac7_the_markdown_prints_the_item_linked_under_needs_you():
    """REQ-037 AC7"""
    import product_report as pr

    doc = load(KINDS)
    open_pull(doc, 9, head_cleared="yes")
    text = pr.render_markdown(build(doc))
    needs = text.split("## Needs you", 1)[1].split("\n## ", 1)[0]
    assert "### Ready to merge (1)" in needs
    assert 'PR #9 "Change number 9" is ready to merge' in needs and f"{LINK}9" in needs
    assert needs.index("### Ready to merge") < needs.index("###", needs.index("Ready to merge") + 5)


def test_ac7_the_report_schema_is_4_and_the_facts_schema_stays_1():
    """REQ-037 AC7"""
    import product_report as pr

    assert pr.REPORT_SCHEMA == 5 and pr.SCHEMA == 1
    assert build(load(KINDS))["schema"] == 5
    assert "pull-request-ready" in pr.ITEM_KINDS
    assert pr.ITEM_KINDS["pull-request-ready"] == ("number", "title")


def test_ac7_items_of_other_groups_do_not_change():
    """REQ-037 AC7: the other markdown and the goldens change only under Needs you."""
    doc = load(KINDS)
    base = [g for g in build(copy.deepcopy(doc))["sections"]["needs_you"]]
    open_pull(doc, 9, head_cleared="yes")
    with_ready = build(doc)["sections"]["needs_you"]
    assert with_ready[1:] == base and items(build(doc), "at_risk") == items(
        build(copy.deepcopy(doc)), "at_risk"
    )
