"""The catch-rate line of the weekly report, report schema 7 (SPEC-0035 rule 5; build (c) of
REQ-042). The report reads a facts document and nothing else; the item `week-totals` carries
`shadow`: the counts of the week and in total with the catch rate, or `not-running`, or `unknown`.
A rate that cannot be computed is `none` or `unknown`, never 0. REQ-042."""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

import product_report as pr
import pytest

ROOT = Path(__file__).resolve().parents[2]
FACTS = Path(__file__).parent / "fixtures" / "facts" / "flow" / "facts.json"
TODAY, WEEK = date(2026, 10, 14), "2026-W42"
COUNTS = {
    "heads": 4,
    "right_conductor_only": 3,
    "right_shadow_only": 1,
    "right_both": 2,
    "wrong_conductor": 1,
    "wrong_shadow": 2,
    "unmarked_heads": 1,
    "unmarked_findings": 0,
}
EMPTY = dict.fromkeys(COUNTS, 0)


def doc(shadow=None) -> dict:
    d = json.loads(FACTS.read_text(encoding="utf-8"))
    d["shadow"] = (
        shadow
        if shadow is not None
        else {
            "issue": 40,
            "unpaired": 1,
            "unread": 0,
            "weeks": {"2026-W41": EMPTY, "2026-W42": COUNTS},
            "total": {k: v + 1 for k, v in COUNTS.items()},
        }
    )
    return d


def totals(d: dict | None = None) -> dict:
    structure = pr.build_report(d or doc(), TODAY, WEEK)
    (item,) = [i for i in structure["sections"]["cost"] if i["kind"] == "week-totals"]
    return item


def test_the_schema_is_7_in_the_code_and_in_the_schema_file():
    schema = json.loads((ROOT / "kit" / "report-schema.json").read_text(encoding="utf-8"))
    assert pr.REPORT_SCHEMA == 7 and schema["properties"]["schema"] == {"const": 7}
    assert schema["title"].endswith("schema 7")
    assert pr.build_report(doc(), TODAY, WEEK)["schema"] == 7


def test_the_item_week_totals_carries_the_counts_of_the_week_and_in_total():
    shadow = totals()["shadow"]
    assert shadow["week"] == {**COUNTS, "catch_rate": "5/6 (83.3%)"}  # (3 + 2) / (3 + 2 + 1)
    assert shadow["total"]["heads"] == 5 and shadow["total"]["catch_rate"] == "7/9 (77.8%)"
    assert (shadow["unpaired"], shadow["unread"]) == (1, 0)
    assert "shadow" in pr.ITEM_KINDS["week-totals"]


def test_a_week_without_shadow_reviews_has_zero_counts_and_no_rate_never_zero():
    shadow = totals(doc({"issue": 40, "unpaired": 0, "unread": 0, "weeks": {}, "total": EMPTY}))[
        "shadow"
    ]
    assert shadow["week"] == {**EMPTY, "catch_rate": "none"}
    assert shadow["total"]["catch_rate"] == "none"


def test_a_shadow_review_that_is_not_running_is_said_so():
    assert totals(doc({"issue": None}))["shadow"] == "not-running"


@pytest.mark.parametrize(
    "bad",
    ["unknown", {"issue": 40}, {"issue": 40, "weeks": [], "total": {}}, 7, ["x"]],
)
def test_what_cannot_be_read_is_unknown(bad):
    assert totals(doc(bad))["shadow"] == "unknown"


def test_facts_without_the_section_say_unknown():
    d = doc()
    del d["shadow"]
    assert totals(d)["shadow"] == "unknown"


def test_the_markdown_names_the_catch_rate_and_the_counts():
    text = pr.render_markdown(pr.build_report(doc(), TODAY, WEEK))
    line = next(ln for ln in text.splitlines() if "shadow review" in ln)
    assert "catch rate 5/6 (83.3%)" in line and "all time 7/9 (77.8%)" in line
    assert "heads reviewed by both 4" in line and "right: conductor only 3" in line
    assert "shadow only 1" in line and "both 2" in line and "wrong: conductor 1" in line
    assert "unmarked heads 1" in line


@pytest.mark.parametrize(
    ("shadow", "words"),
    [({"issue": None}, "shadow review: not running"), ("unknown", "shadow review: unknown")],
)
def test_the_markdown_says_when_the_review_is_not_running_or_unknown(shadow, words):
    text = pr.render_markdown(pr.build_report(doc(shadow), TODAY, WEEK))
    assert words in text


def test_the_report_json_is_the_same_bytes_twice_and_the_schema_requires_the_field(tmp_path):
    out = [tmp_path / "a.json", tmp_path / "b.json"]
    for path in out:
        pr.write_json(pr.build_report(copy.deepcopy(doc()), TODAY, WEEK), str(path))
    assert out[0].read_bytes() == out[1].read_bytes()
    schema = json.loads((ROOT / "kit" / "report-schema.json").read_text(encoding="utf-8"))
    cost = schema["properties"]["sections"]["properties"]["cost"]["items"]["oneOf"]
    props = next(o for o in cost if o["properties"]["kind"] == {"const": "week-totals"})
    assert "shadow" in props["required"] and "shadow" in props["properties"]


def test_a_count_that_is_not_an_integer_makes_the_whole_line_unknown():
    d = doc()
    d["shadow"]["weeks"]["2026-W42"]["heads"] = "four"
    assert totals(d)["shadow"] == "unknown"
