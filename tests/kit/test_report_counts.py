"""Tests of the counts in the report (SPEC-0026; REQ-033 AC1 to AC8). No network, no model.

`report.json` states how many each section, group and unknown total holds, so a reader can show
totals without counting; what the facts could not read is not left out. Schema number 3.
"""

from __future__ import annotations

import copy
import json

from test_product_report import FIXTURES

KINDS = FIXTURES / "report" / "kinds" / "facts.json"
QUIET = FIXTURES / "report" / "quiet" / "facts.json"
URL = "https://github.com/demo-org/demo-repo/pull/"
ENTRY_KINDS = (
    "pull-requests-open-long",
    "pull-requests-sent-back",
    "pull-requests-merged-no-verdict",
    "pull-requests-merged-not-cleared",
)


def build(doc):
    import product_report as pr

    return pr.build_report(doc, pr.day_of(doc["today"]), None)


def load(path):
    return copy.deepcopy(json.loads(path.read_text(encoding="utf-8")))


def items(structure, section):
    entries = structure["sections"][section]
    if section == "needs_you":
        return [i for g in entries for i in g["items"]]
    return entries


def kinds_of(structure, section, kind):
    return [i for i in items(structure, section) if i["kind"] == kind]


def pull(doc, number):
    return next(p for p in doc["pull_requests"] if p["number"] == number)


# --- the section counts (rule 1) -------------------------------------------------------------


def test_ac1_counts_have_exactly_the_four_section_keys_as_whole_numbers():
    """REQ-033 AC1: rule 1 (the keys are the section keys; there is no count for cost)."""
    counts = build(load(KINDS))["counts"]
    assert list(counts) == ["delivered", "proven", "needs_you", "at_risk"]
    assert all(isinstance(v, int) and not isinstance(v, bool) for v in counts.values())


def test_ac1_each_count_is_the_number_of_the_items_of_its_kind():
    """REQ-033 AC1: rule 1 (by meaning: unknown items are not counted)."""
    structure = build(load(KINDS))
    counts = structure["counts"]
    assert counts["delivered"] == len(kinds_of(structure, "delivered", "requirement-done"))
    assert counts["proven"] == len(kinds_of(structure, "proven", "requirement-proven"))
    assert counts["needs_you"] == len(items(structure, "needs_you"))
    assert counts["at_risk"] == len(items(structure, "at_risk"))
    assert counts["delivered"] and counts["proven"] and counts["needs_you"] and counts["at_risk"]


def test_ac1_a_busy_week_gives_the_same_delivered_count_for_the_same_requirements():
    """REQ-033 AC1: rule 1 (the busy-week summary item is not a delivered requirement)."""
    quiet = load(KINDS)
    busy = load(KINDS)
    template = pull(busy, 5)
    for n in range(100, 112):
        extra = copy.deepcopy(template)
        extra["number"] = n
        busy["pull_requests"].append(extra)
    one, two = build(quiet), build(busy)
    assert len(items(one, "delivered")) != len(items(two, "delivered"))
    assert one["counts"]["delivered"] == two["counts"]["delivered"]
    assert any(i["kind"] == "pull-requests-merged" for i in items(two, "delivered"))


def test_ac1_an_empty_section_counts_zero():
    """REQ-033 AC1: rule 1."""
    counts = build(load(QUIET))["counts"]
    assert counts["delivered"] == 0 and counts["needs_you"] == 0


def test_ac1_a_section_that_holds_an_unknown_item_counts_unknown_never_a_number():
    """REQ-033 AC1: rule 1 (unknown is not shown as a count)."""
    doc = load(KINDS)
    doc["pull_requests"] = "unknown"
    structure = build(doc)
    assert kinds_of(structure, "at_risk", "unknown")
    assert structure["counts"]["at_risk"] == "unknown"
    assert structure["counts"]["needs_you"] == "unknown"
    assert isinstance(structure["counts"]["proven"], int | str)


# --- the group counts (rule 2) ---------------------------------------------------------------


def test_ac2_every_entries_kind_carries_count_equal_to_its_entries():
    """REQ-033 AC2: rule 2 (always present, after `entries` in the table)."""
    import product_report as pr

    structure = build(load(KINDS))
    seen = {i["kind"] for i in items(structure, "at_risk")}
    assert seen & set(ENTRY_KINDS)
    for kind in ENTRY_KINDS:
        assert pr.ITEM_KINDS[kind] == ("entries", "count")
    for entry in items(structure, "at_risk"):
        if entry["kind"] in ENTRY_KINDS:
            assert entry["count"] == len(entry["entries"])
            assert list(entry) == ["kind", "entries", "count", "links"]


def test_ac2_a_group_of_several_pull_requests_counts_them_all():
    """REQ-033 AC2: rule 2."""
    doc = load(KINDS)
    for n in (9, 13):
        pull(doc, n)["created_at"] = "2026-09-01T10:00:00Z"
    entries = kinds_of(build(doc), "at_risk", "pull-requests-open-long")
    assert [e["count"] for e in entries] == [len(e["entries"]) for e in entries]
    assert max(e["count"] for e in entries) >= 2


# --- the unknown fix verdicts (rule 3) -------------------------------------------------------


def totals(structure):
    return next(i for i in structure["sections"]["cost"] if i["kind"] == "week-totals")


def test_ac3_merged_pull_requests_with_unknown_verdicts_are_counted():
    """REQ-033 AC3: rule 3 (the same set as `merged`)."""
    doc = load(KINDS)
    pull(doc, 5)["verdicts"] = "unknown"
    pull(doc, 6)["verdicts"] = "unknown"
    entry = totals(build(doc))
    assert entry["fix_verdicts_unknown"] == 2
    assert entry["fix_verdicts"] == "unknown" and entry["merged"] == 4


def test_ac3_the_field_is_zero_and_present_when_every_verdict_is_known():
    """REQ-033 AC3: rule 3 (never omitted, never the string)."""
    import product_report as pr

    entry = totals(build(load(KINDS)))
    assert entry["fix_verdicts_unknown"] == 0 and isinstance(entry["fix_verdicts_unknown"], int)
    fields = list(pr.ITEM_KINDS["week-totals"])
    assert fields[fields.index("fix_verdicts") + 1] == "fix_verdicts_unknown"


def test_ac3_a_busy_week_counts_every_merged_pull_request():
    """REQ-033 AC3: rule 3 (the cost lines are left out, the count is not)."""
    doc = load(KINDS)
    template = pull(doc, 5)
    for n in range(100, 112):
        extra = copy.deepcopy(template)
        extra["number"] = n
        extra["verdicts"] = "unknown"
        doc["pull_requests"].append(extra)
    entry = totals(build(doc))
    assert entry["busy"] is True and entry["fix_verdicts_unknown"] == 12


# --- the schema number (rule 7) --------------------------------------------------------------


def test_ac4_the_schema_number_is_4_and_the_kinds_are_the_same():
    """REQ-033 AC4: rule 7 (the kinds list is unchanged; only fields are added)."""
    import product_report as pr

    assert pr.REPORT_SCHEMA == 7 and build(load(KINDS))["schema"] == 7
    assert list(build(load(KINDS))) == [
        "schema",
        "week",
        "opening",
        "sections",
        "counts",
        "notices",
    ]
    assert len(pr.ITEM_KINDS) == 31


# --- open pull requests with unknown verdicts (rule 5) ---------------------------------------


def unreadable(doc, *numbers):
    for n in numbers:
        pull(doc, n)["verdicts"] = "unknown"
    return build(doc)


def test_ac5_open_pull_requests_with_unknown_verdicts_become_one_item_in_each_place():
    """REQ-033 AC5: rule 5 (the number in `what`, a link to each)."""
    structure = unreadable(load(KINDS), 9, 13)
    group = next(g for g in structure["sections"]["needs_you"] if g["group"] == "pull-request")
    for found in (
        [i for i in group["items"] if i["kind"] == "unknown"],
        kinds_of(structure, "at_risk", "unknown"),
    ):
        assert len(found) == 1
        assert "2 open pull requests" in found[0]["what"]
        assert [x["url"] for x in found[0]["links"]] == [URL + "9", URL + "13"]
        assert {x["to"] for x in found[0]["links"]} == {"pull-request"}
    assert group["count"] == "unknown"


def test_ac5_one_unreadable_pull_request_is_named_in_the_singular():
    """REQ-033 AC5: rule 5."""
    structure = unreadable(load(KINDS), 9)
    found = kinds_of(structure, "at_risk", "unknown")
    assert len(found) == 1 and "1 open pull request" in found[0]["what"]
    assert "pull requests" not in found[0]["what"]


def test_ac5_no_unreadable_open_pull_request_adds_nothing():
    """REQ-033 AC5: rule 5 (and a merged or closed one is not an open one)."""
    structure = build(load(KINDS))
    assert not kinds_of(structure, "at_risk", "unknown")
    assert not [i for i in items(structure, "needs_you") if i["kind"] == "unknown"]
    closed = unreadable(load(KINDS), 5, 12)
    assert not kinds_of(closed, "at_risk", "unknown")


def test_ac5_the_markdown_names_how_many_and_links_each(capsys):
    """REQ-033 AC5: rule 5 (the unknown line)."""
    import product_report as pr

    doc = load(KINDS)
    for n in (9, 13):
        pull(doc, n)["verdicts"] = "unknown"
    text = pr.render_markdown(build(doc))
    line = next(ln for ln in text.splitlines() if "the verdicts of 2 open pull requests" in ln)
    assert f"({URL}9)" in line and f"({URL}13)" in line


# --- the drift-audit line (rule 6) -----------------------------------------------------------


def drift(doc, total, open_issue):
    zero = {k: 0 for k in doc["drift"]["counts"]}
    doc["drift"] = {"counts": zero, "total": total}
    if total:
        doc["drift"]["counts"]["D1"] = total
    if not open_issue:
        doc["issues"] = [i for i in doc["issues"] if i.get("label") != "agk-drift-audit"]
    return kinds_of(build(doc), "at_risk", "drift-audit")


def test_ac6_a_total_of_zero_with_no_open_issue_is_left_out():
    """REQ-033 AC6: rule 6."""
    assert drift(load(KINDS), 0, open_issue=False) == []


def test_ac6_a_total_of_zero_with_an_open_issue_stays():
    """REQ-033 AC6: rule 6 (the open issue is itself a thing to look at)."""
    assert len(drift(load(KINDS), 0, open_issue=True)) == 1


def test_ac6_a_total_above_zero_stays_with_or_without_an_issue():
    """REQ-033 AC6: rule 6."""
    assert len(drift(load(KINDS), 3, open_issue=False)) == 1
    assert len(drift(load(KINDS), 3, open_issue=True)) == 1


def test_ac6_an_unreadable_drift_total_stays_as_an_unknown_item():
    """REQ-033 AC6: rule 6."""
    doc = load(KINDS)
    doc["drift"] = "unknown"
    assert kinds_of(build(doc), "at_risk", "unknown")


def test_ac6_a_total_of_zero_with_issues_that_cannot_be_read_stays():
    """REQ-033 AC6: rule 6 (no open issue cannot be told)."""
    doc = load(KINDS)
    doc["issues"] = "unknown"
    zero = {k: 0 for k in doc["drift"]["counts"]}
    doc["drift"] = {"counts": zero, "total": 0}
    assert len(kinds_of(build(doc), "at_risk", "drift-audit")) == 1


# --- what stays not known yet (rule 4) -------------------------------------------------------


def test_ac7_an_unreadable_group_and_the_drift_total_carry_no_unknown_count():
    """REQ-033 AC7: rule 4 (the group keeps its fields and `unknown`)."""
    doc = load(KINDS)
    doc["pull_requests"] = "unknown"
    structure = build(doc)
    group = next(g for g in structure["sections"]["needs_you"] if g["group"] == "pull-request")
    assert list(group) == ["group", "count", "items"]
    assert group["count"] == "unknown" and [i["kind"] for i in group["items"]] == ["unknown"]
    assert list(kinds_of(structure, "at_risk", "unknown")[0]) == ["kind", "what", "links"]
    doc = load(KINDS)
    doc["drift"] = "unknown"
    assert list(kinds_of(build(doc), "at_risk", "unknown")[0]) == ["kind", "what", "links"]


# --- the markdown (rule 7) -------------------------------------------------------------------


def test_ac8_the_markdown_rendered_from_the_json_equals_the_printed_markdown():
    """REQ-033 AC8: rule 7 (SPEC-0022 rule 2) with the new items present."""
    import product_report as pr

    doc = load(KINDS)
    for n in (9, 13):
        pull(doc, n)["verdicts"] = "unknown"
    structure = build(doc)
    assert pr.render_markdown(json.loads(json.dumps(structure))) == pr.render_report(
        doc, pr.day_of(doc["today"]), None
    )


def test_ac8_the_markdown_does_not_print_the_counts_or_the_new_fields():
    """REQ-033 AC8: rule 7 (data only: the counts are not in the text)."""
    import product_report as pr

    text = pr.render_markdown(build(load(KINDS)))
    assert "fix_verdicts_unknown" not in text and "counts" not in text
