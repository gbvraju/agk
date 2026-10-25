"""The Flow section and its At risk lines in the weekly report (schema 6; SPEC-0034 rule 10,
SPEC-0033 rule 5, SPEC-0032 rule 11). The report reads a facts document and nothing else; a
figure that cannot be read is `unknown`, never 0. Fixture: the facts of the `flow` case. REQ-041
AC8, REQ-040 AC5, REQ-039."""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

import product_report as pr
import pytest

FACTS = Path(__file__).parent / "fixtures" / "facts" / "flow" / "facts.json"
TODAY, WEEK = date(2026, 10, 14), "2026-W42"


def doc() -> dict:
    return json.loads(FACTS.read_text(encoding="utf-8"))


def report(d: dict | None = None) -> dict:
    return pr.build_report(d or doc(), TODAY, WEEK)


def kinds(structure: dict, section: str, kind: str) -> list[dict]:
    return [i for i in structure["sections"][section] if i["kind"] == kind]


def test_ac8_the_schema_is_6_and_the_report_has_a_sixth_section_after_cost():
    """REQ-041 AC8: a new section is a new schema number."""
    structure = report()
    assert structure["schema"] == 6 and pr.REPORT_SCHEMA == 6
    assert list(structure["sections"]) == [
        "delivered",
        "proven",
        "needs_you",
        "at_risk",
        "cost",
        "flow",
    ]
    assert pr.SECTIONS[-1] == "Flow"
    assert [ln for ln in pr.render_markdown(structure).splitlines() if ln.startswith("## ")][
        -1
    ] == "## Flow"


def test_ac8_the_flow_figures_are_the_medians_of_the_pull_requests_merged_in_the_week():
    """REQ-041 AC8: rule 10 (open against max, four medians, conflicts, renumbers, retakes)."""
    (figures,) = report()["sections"]["flow"]
    assert figures["kind"] == "flow-figures"
    assert (figures["open_builders"], figures["max_builders"]) == (2, 2)
    assert figures["taken_to_pull_request"] == "3.0" and figures["to_first_verdict"] == "15.0"
    assert figures["verdict_to_cleared"] == "24.0" and figures["cleared_to_merge"] == "30.0"
    assert (figures["conflicts"], figures["renumbers"], figures["retakes"]) == (1, 1, 1)


def test_ac8_the_flow_text_names_each_figure():
    """REQ-041 AC8"""
    text = pr.render_markdown(report())
    line = next(ln for ln in text.splitlines() if ln.startswith("- Builders:"))
    assert "2 of 2 pull requests open" in line and "taken to pull request 3.0" in line
    assert "cleared to merge 30.0" in line and "conflicts 1" in line and "retakes 1" in line


def test_ac8_a_median_with_an_unknown_step_is_unknown_and_no_step_is_none():
    """REQ-041 AC8: never 0 for what cannot be read, and no pull request is not a median."""
    d = doc()
    for p in d["pull_requests"]:
        if p["number"] == 21:
            p["flow"]["to_first_verdict"] = "unknown"
            p["conflicts"] = "unknown"
    (figures,) = report(d)["sections"]["flow"]
    assert figures["to_first_verdict"] == "unknown" and figures["conflicts"] == "unknown"
    assert figures["taken_to_pull_request"] == "3.0"
    d["pull_requests"] = [p for p in d["pull_requests"] if p["state"] != "merged"]
    (figures,) = report(d)["sections"]["flow"]
    assert figures["cleared_to_merge"] == "none" and figures["conflicts"] == 0


def test_ac8_without_the_flow_in_the_facts_or_the_pull_requests_the_section_is_unknown():
    """REQ-041 AC8"""
    d = doc()
    del d["flow"]
    (entry,) = report(d)["sections"]["flow"]
    assert entry["kind"] == "unknown" and entry["what"] == "the flow"
    d = doc()
    d["pull_requests"] = "unknown"
    assert report(d)["sections"]["flow"][0]["kind"] == "unknown"
    d = doc()
    d["flow"]["retakes"] = "unknown"
    assert report(d)["sections"]["flow"][0]["retakes"] == "unknown"


def test_ac8_an_open_brief_with_no_pull_request_for_7_days_is_an_at_risk_line():
    """REQ-041 AC8: rule 10 (the open briefs with no pull request for 7 days)."""
    (idle,) = kinds(report(), "at_risk", "briefs-idle")
    assert idle["count"] == 1
    assert idle["entries"] == [{"number": 33, "title": "Brief 33", "days": 12}]
    assert idle["links"][0]["url"].endswith("/issues/33")


def test_ac8_a_requirement_that_no_open_brief_advances_is_an_at_risk_line():
    """REQ-041 AC8: rule 10 (the requirements with no open brief; done ones are not listed)."""
    (found,) = kinds(report(), "at_risk", "requirements-without-brief")
    assert found["entries"] == [{"id": "REQ-002"}] and found["count"] == 1
    assert [b["advances"] for b in doc()["flow"]["briefs"]][-1] == []  # the red-branch brief
    assert not [i for i in report()["sections"]["at_risk"] if i["kind"] == "unknown"]
    d = doc()
    d["flow"]["briefs"][0]["advances"] = ["REQ-001", "REQ-002"]
    assert kinds(report(d), "at_risk", "requirements-without-brief") == []


def test_ac5_a_stalled_pull_request_is_an_at_risk_line_and_an_unknown_one_is_named():
    """REQ-040 AC5: rule 5 (stalled on its builder)."""
    (stalled,) = kinds(report(), "at_risk", "pull-requests-stalled")
    assert stalled["entries"] == [{"number": 22, "title": "Change number 22"}]
    d = doc()
    next(p for p in d["pull_requests"] if p["number"] == 22)["stalled"] = "unknown"
    structure = report(d)
    assert kinds(structure, "at_risk", "pull-requests-stalled") == []
    assert any(i["what"] == "stalled pull requests" for i in kinds(structure, "at_risk", "unknown"))
    assert structure["counts"]["at_risk"] == "unknown"


def test_ac8_the_at_risk_lines_are_counted_with_the_other_at_risk_items():
    """REQ-041 AC8"""
    structure = report()
    assert structure["counts"]["at_risk"] == len(structure["sections"]["at_risk"])


def test_rule11_corrections_of_the_week_are_printed_next_to_the_verdicts():
    """REQ-039: rule 11 (the conductor's corrections, from the dated comments)."""
    (totals,) = kinds(report(), "cost", "week-totals")
    assert totals["corrections"] == 1
    assert "fix verdicts in total: 1; corrections: 1;" in pr.render_markdown(report())
    d = doc()
    d["flow"]["corrections"] = "unknown"
    assert kinds(report(d), "cost", "week-totals")[0]["corrections"] == "unknown"
    d = copy.deepcopy(doc())
    del d["flow"]
    assert kinds(report(d), "cost", "week-totals")[0]["corrections"] == "unknown"


@pytest.mark.parametrize("name", ["report-schema"])
def test_ac8_the_published_schema_is_6_and_names_the_new_kinds(name):
    """REQ-041 AC8: kit/report-schema.json is changed by hand with the script (SPEC-0022 rule 7)."""
    schema = json.loads((Path(__file__).parents[2] / "kit" / f"{name}.json").read_text("utf-8"))
    assert schema["properties"]["schema"] == {"const": 6}
    text = json.dumps(schema)
    for kind in (
        "flow-figures",
        "briefs-idle",
        "requirements-without-brief",
        "pull-requests-stalled",
    ):
        assert f'"const": "{kind}"' in text, kind
    assert "flow" in schema["properties"]["sections"]["required"]
