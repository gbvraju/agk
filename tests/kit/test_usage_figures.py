"""The usage figure of a pull request in the facts and the cost lines (SPEC-0033 rule 8).

A builder's `Report:` comment may end its first line with `Usage: <n> tokens`. The facts carry
`usage` for each pull request: the sum of those figures in the comments of the pull request's
author, `not-reported` when there is none, `unknown` when the comments cannot be read. The cost
lines of the weekly report print the figure or `usage not reported`, never zero; `report.json`
takes schema number 5. No network, no model.
"""

from __future__ import annotations

import json

import pytest
from test_product_report import FIXTURES

KINDS = FIXTURES / "report" / "kinds" / "facts.json"


# --- the facts ----------------------------------------------------------------------------------


class Src:
    def __init__(self, comments):
        self.comments = comments

    def get(self, name, endpoint, until=None):
        if name == "comments-7":
            return self.comments
        return [] if name in ("files-7", "commits-7") else None


def record(comments, login="builder"):
    import facts

    item = {"number": 7, "head": {"sha": "d" * 40}, "created_at": "2026-10-06T09:00:00Z"}
    item |= {"state": "open", "title": "t", "body": "", "merged_at": None, "user": {"login": login}}
    return facts.pull_record(Src(comments), item, ["reviewer"])


def report(body: str, login: str = "builder", cid: int = 1) -> dict:
    return {"id": cid, "body": body, "user": {"login": login}, "created_at": "2026-10-06T10:00:00Z"}


def test_ac8_the_figures_of_the_authors_report_comments_are_summed():
    """REQ-040 AC8"""
    comments = [
        report("Report: abc1234 the first part; CI pending. Usage: 1200 tokens", cid=1),
        report("Report: def5678 the second part; CI green. Usage: 300 tokens", cid=2),
    ]
    assert record(comments)["usage"] == 1500


@pytest.mark.parametrize(
    "body",
    [
        "Report: abc1234 done; CI pending",
        "Report: abc1234 done\nUsage: 500 tokens",
        "Usage: 500 tokens",
        "Report: abc1234 done. Usage: five tokens",
        "Report: abc1234 done. Usage: 5.5 tokens",
        "Report: abc1234 done. Usage: 500 bytes",
        "Report: abc1234 done. Usage: -5 tokens",
        "Progress: abc1234 done 1/2; next: x. Usage: 500 tokens",
    ],
)
def test_ac8_a_comment_that_is_not_a_report_with_a_whole_number_of_tokens_counts_nothing(body):
    """REQ-040 AC8"""
    assert record([report(body)])["usage"] == "not-reported"


def test_ac8_a_figure_in_a_comment_of_another_author_counts_nothing():
    """REQ-040 AC8"""
    other = [report("Report: abc1234 done. Usage: 500 tokens", login="stranger")]
    assert record(other)["usage"] == "not-reported"
    assert record(other, login="stranger")["usage"] == 500


def test_ac8_no_comment_is_not_reported_and_unreadable_comments_are_unknown():
    """REQ-040 AC8: never zero."""
    assert record([])["usage"] == "not-reported"
    assert record(None)["usage"] == "unknown"


def test_ac8_a_report_with_a_figure_of_zero_is_reported_as_zero_not_as_missing():
    """REQ-040 AC8"""
    assert record([report("Report: abc1234 done. Usage: 0 tokens")])["usage"] == 0


def test_ac8_the_facts_keep_schema_1():
    """REQ-040 AC8"""
    import facts

    assert facts.SCHEMA == 1


# --- the cost lines -------------------------------------------------------------------------------


def build(doc):
    import product_report as pr

    return pr.build_report(doc, pr.day_of(doc["today"]), None)


def load():
    return json.loads(KINDS.read_text(encoding="utf-8"))


def cost_items(structure):
    return [i for i in structure["sections"]["cost"] if i["kind"] == "pull-request-cost"]


def totals(structure):
    return next(i for i in structure["sections"]["cost"] if i["kind"] == "week-totals")


def merged(doc):
    return [p for p in doc["pull_requests"] if p["number"] in (5, 6, 7, 8)]


def test_ac8_the_report_schema_is_6_and_the_fields_are_in_the_tables():
    """REQ-040 AC8"""
    import product_report as pr

    assert pr.REPORT_SCHEMA == 6 and build(load())["schema"] == 6
    assert pr.ITEM_KINDS["pull-request-cost"][-1] == "usage"
    assert pr.ITEM_KINDS["week-totals"][-3:-1] == ("usage", "usage_reported")


def test_ac8_each_cost_item_carries_the_figure_or_not_reported_never_zero():
    """REQ-040 AC8"""
    doc = load()
    first, second, third = merged(doc)[:3]
    first["usage"], second["usage"], third["usage"] = 1500, "not-reported", "unknown"
    by = {i["number"]: i["usage"] for i in cost_items(build(doc))}
    assert by[first["number"]] == 1500
    assert by[second["number"]] == "not-reported" and by[third["number"]] == "unknown"


def test_ac8_facts_without_the_field_read_unknown_not_not_reported():
    """REQ-040 AC8: an older facts file cannot say that nothing was reported."""
    doc = load()
    for p in doc["pull_requests"]:
        p.pop("usage", None)
    assert {i["usage"] for i in cost_items(build(doc))} == {"unknown"}


def test_ac8_the_totals_sum_the_reported_figures_and_count_how_many_reported():
    """REQ-040 AC8"""
    doc = load()
    a, b, c, d = merged(doc)
    a["usage"], b["usage"], c["usage"], d["usage"] = 1000, 250, "not-reported", "not-reported"
    entry = totals(build(doc))
    assert entry["usage"] == 1250 and entry["usage_reported"] == 2


def test_ac8_the_totals_say_not_reported_when_no_pull_request_reported_and_unknown_when_unread():
    """REQ-040 AC8"""
    doc = load()
    for p in merged(doc):
        p["usage"] = "not-reported"
    entry = totals(build(doc))
    assert entry["usage"] == "not-reported" and entry["usage_reported"] == 0
    merged(doc)[0]["usage"] = "unknown"
    assert totals(build(doc))["usage"] == "unknown"


def test_ac8_the_markdown_prints_the_figure_and_never_a_zero_for_a_missing_one():
    """REQ-040 AC8"""
    import product_report as pr

    doc = load()
    a, b, c, d = merged(doc)
    a["usage"], b["usage"], c["usage"], d["usage"] = 1000, "not-reported", "unknown", 0
    text = pr.render_markdown(build(doc))
    cost = text.split("## Cost", 1)[1]
    assert f'PR #{a["number"]} "{a["title"]}": ' in cost and "usage 1000 tokens" in cost
    assert "usage not reported" in cost and "usage unknown" in cost and "usage 0 tokens" in cost
    assert "usage in total: unknown;" in cost  # one pull request's figure could not be read
    c["usage"] = "not-reported"
    cost = pr.render_markdown(build(doc)).split("## Cost", 1)[1]
    assert "usage in total: 1000 tokens (2 of 4 pull requests reported);" in cost


def test_ac8_the_markdown_totals_say_not_reported_when_there_is_no_figure():
    """REQ-040 AC8"""
    import product_report as pr

    doc = load()
    for p in merged(doc):
        p["usage"] = "not-reported"
    cost = pr.render_markdown(build(doc)).split("## Cost", 1)[1]
    assert "usage in total: not reported" in cost and "0 tokens" not in cost


def test_ac8_a_busy_week_sums_every_merged_pull_request_and_lists_none():
    """REQ-040 AC8"""
    doc = json.loads((FIXTURES / "report" / "busy" / "facts.json").read_text(encoding="utf-8"))
    for p in doc["pull_requests"]:
        if p.get("merged_at"):
            p["usage"] = 100
    structure = build(doc)
    entry = totals(structure)
    assert entry["busy"] is True and not cost_items(structure)
    assert entry["usage"] == 100 * entry["merged"] and entry["usage_reported"] == entry["merged"]


def test_ac8_the_rules_file_and_the_amendment_say_the_figure_is_since_the_previous_report():
    """REQ-040 AC8 (the verdict on the first head: a running total would be summed twice)"""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    rules = (root / "config" / "session-rules.md").read_text(encoding="utf-8")
    for phrase in (
        "Usage: <n> tokens",
        "since the previous `Report:` of the same pull request",
        "never a running total",
        "subtracts the total it reported last",
    ):
        assert phrase in rules, phrase
    amendment = (root / "docs" / "runs" / "proposed-spec-amendments-58.md").read_text("utf-8")
    assert "since the previous `Report:` of the same pull request" in amendment
