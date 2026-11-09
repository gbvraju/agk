"""The time to restore and the run minutes in the weekly report (SPEC-0056 rule 12, brief #889).

`facts.py` holds the figures in the section `measures` and `product_report.py` prints them in
`## Cost`. Saved GitHub responses only, no network, invented data (`example.com`). REQ-063.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import facts
import metrics
import product_report as pr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "kit_dev"))
OK = Path(__file__).parent / "fixtures" / "facts" / "ok" / "facts.json"
TODAY, WEEK = date(2026, 11, 9), "2026-W45"
RED, LOCAL = "The default branch is red", "Local mode since 2026-11-03"
LEAK = "agk-secret-leak"
RED_LINE = "restore red default branch: 2 closed, median 3.0 hours, 1 open"
BLOCKED_LINE = "restore actions blocked: 1 closed, median 6.0 hours, 0 open"
LEAK_LINE = "restore leaked secret: 1 closed, median 1.5 hours, 1 open"
UNKNOWN_LEAK = "restore leaked secret: unknown closed, median unknown hours, unknown open"
UNKNOWN_MINUTES = "run minutes: unknown this week, unknown per merged pull request"


def issue(title: str, opened: str, closed: str | None = None, **extra) -> dict:
    return {"title": title, "created_at": opened, "closed_at": closed, **extra}


def leak(body: str | None, closed: str | None = "2026-11-04T12:00:00Z", labelled=True) -> dict:
    labels = [{"name": LEAK}] if labelled else []
    return issue("A leaked secret was revoked", "2026-11-04T09:00:00Z", closed, body=body) | {
        "labels": labels
    }


GOOD_BODY = "Detected: 2026-11-04T09:00:00Z\nRevoked: 2026-11-04T10:30:00Z"
OPENED = [issue(RED, "2026-11-08T09:00:00Z")]
CLOSED = [
    issue(RED, "2026-11-03T08:00:00Z", "2026-11-03T10:00:00Z"),
    issue(RED, "2026-11-05T08:00:00Z", "2026-11-05T12:00:00Z"),
    issue(RED, "2026-10-20T08:00:00Z", "2026-10-20T09:00:00Z"),  # the week before: not counted
    issue(LOCAL, "2026-11-03T06:00:00Z", "2026-11-03T12:00:00Z"),
    issue(RED, "2026-11-05T08:00:00Z", "2026-11-05T09:00:00Z", pull_request={}),  # not an issue
]
LEAKS = [leak(GOOD_BODY), leak("Detected: x", closed=None)]
RUN = {"id": 1, "created_at": "2026-11-03T08:00:00Z", "name": "governance"}
JOB = {
    "started_at": "2026-11-03T08:00:00Z",
    "completed_at": "2026-11-03T08:10:30Z",
    "conclusion": "success",
    "labels": ["ubuntu-latest"],
}
MERGED = [
    {"merged_at": "2026-11-03T09:00:00Z"},
    {"merged_at": "2026-11-04T09:00:00Z"},
    {"merged_at": "2026-10-20T09:00:00Z"},
    {"merged_at": None},
]
ISSUES = {"issues-open": OPENED, "issues-closed": CLOSED, f"issues-{LEAK}": LEAKS}
RUNS = {
    "runs-week": {"total_count": 1, "workflow_runs": [RUN]},
    "run-jobs-1": {"total_count": 2, "jobs": [JOB, JOB]},
    "repo": {"private": True},
}


def section(tmp_path: Path, responses: dict, pulls=None):
    for name, data in responses.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    merged = MERGED if pulls is None else pulls
    return facts.measures_section(metrics.ApiDir(tmp_path), TODAY, merged)


def lines(measures, week: str | None = None, drop: bool = False) -> list[str]:
    doc = json.loads(OK.read_text(encoding="utf-8"))
    doc["measures"] = measures
    if drop:
        del doc["measures"]
    text = pr.render_markdown(pr.build_report(doc, TODAY, week))
    return [ln.split(" — ")[0].removeprefix("- ") for ln in text.splitlines()]


def test_ac7_the_three_restore_lines(tmp_path):
    """REQ-063 AC7: one line per kind, from each kind's own reader, in the week."""
    shown = lines(section(tmp_path, ISSUES))
    assert RED_LINE in shown and BLOCKED_LINE in shown and LEAK_LINE in shown


def test_ac7_the_lines_are_in_the_cost_section_and_the_headings_stay(tmp_path):
    """REQ-063 AC7: `## Cost` holds them, and SPEC-0011's headings stay."""
    shown = lines(section(tmp_path, {**ISSUES, **RUNS}))
    assert shown.index("## Cost") < shown.index(RED_LINE) < shown.index("## Flow")
    assert [ln for ln in shown if ln.startswith("## ")] == [f"## {name}" for name in pr.SECTIONS]


def test_ac7_the_run_minutes_for_a_week(tmp_path):
    """REQ-063 AC7: two jobs of 11 minutes and two pull requests merged in the week."""
    found = section(tmp_path, RUNS)
    assert found["week"] == WEEK
    assert found["run_minutes"] == {"minutes": 22, "per_merged": "11.0"}
    assert "run minutes: 22 this week, 11.0 per merged pull request" in lines(found)


def test_ac7_no_merge_leaves_the_rate_unknown_and_never_0(tmp_path):
    """REQ-063 AC7: the week's minutes are read, the rate has nothing to divide by."""
    found = section(tmp_path, RUNS, pulls=[])
    assert found["run_minutes"] == {"minutes": 22, "per_merged": "unknown"}


def test_ac7_pull_requests_that_cannot_be_read_leave_the_rate_unknown(tmp_path):
    """REQ-063 AC7: `pull_requests` unknown."""
    found = section(tmp_path, RUNS, pulls="unknown")
    assert found["run_minutes"] == {"minutes": 22, "per_merged": "unknown"}


def test_ac7_a_refused_read_is_printed_unknown(tmp_path):
    """REQ-063 AC7: nothing readable is the whole section, and four lines of `unknown`."""
    found = section(tmp_path, {})
    assert found == "unknown"
    shown = lines(found)
    assert UNKNOWN_MINUTES in shown and UNKNOWN_LEAK in shown
    assert sum(1 for ln in shown if ln.startswith("restore ")) == 3


def test_ac7_one_refused_read_leaves_the_other_figures(tmp_path):
    """REQ-063 AC7: the smallest level that fits (SPEC-0009 rule 5)."""
    shown = lines(section(tmp_path, {"issues-open": OPENED, "issues-closed": CLOSED}))
    assert RED_LINE in shown and UNKNOWN_LEAK in shown and UNKNOWN_MINUTES in shown


def test_ac7_an_incomplete_run_list_is_unknown(tmp_path):
    """REQ-063 AC7: a job list that cannot be read never counts as no minutes."""
    found = section(tmp_path, {"runs-week": RUNS["runs-week"]})
    assert found["run_minutes"]["minutes"] == "unknown"


def test_ac7_a_malformed_detected_line_is_printed_unknown(tmp_path):
    """REQ-063 AC7: counted as closed, and its time is `unknown`, never 0."""
    bad = {**ISSUES, f"issues-{LEAK}": [leak("Detected: yesterday\nRevoked: 2026-11-04T10:30:00Z")]}
    assert "restore leaked secret: 1 closed, median unknown hours, 0 open" in lines(
        section(tmp_path, bad)
    )


def test_ac7_the_facts_document_is_valid_against_its_schema(tmp_path):
    """REQ-063 AC7: a full section, the `unknown` section and an extra key."""
    from jsonschema_lite import errors  # noqa: PLC0415 - tests/kit_dev, on the path above

    schema = json.loads((ROOT / "kit" / "facts-schema.json").read_text(encoding="utf-8"))
    doc = json.loads(OK.read_text(encoding="utf-8"))
    full = section(tmp_path, {**ISSUES, **RUNS})
    for measures in (full, "unknown"):
        assert errors(doc | {"measures": measures}, schema) == []
    assert errors(doc | {"measures": {**full, "extra": 1}}, schema)


def test_ac6_a_stranger_s_unlabelled_issue_is_not_counted(tmp_path):
    """REQ-063 AC6: the label is what counts (SPEC-0056 rule 11)."""
    listed = {**ISSUES, f"issues-{LEAK}": [leak(GOOD_BODY), leak(GOOD_BODY, labelled=False)]}
    assert section(tmp_path, listed)["restore"]["leaked secret"]["closed"] == 1


def test_ac6_revoked_before_detected_and_a_repeated_line_are_unknown(tmp_path):
    """REQ-063 AC6: a time that cannot be right, and two lines where the record has one."""
    backwards = "Detected: 2026-11-04T10:30:00Z\nRevoked: 2026-11-04T09:00:00Z"
    twice = f"{GOOD_BODY}\nDetected: 2026-11-04T09:30:00Z"
    for body in (backwards, twice, "Detected: 2026-11-04T09:00:00\nRevoked: 2026-11-04T10:30:00"):
        listed = {**ISSUES, f"issues-{LEAK}": [leak(body)]}
        assert section(tmp_path, listed)["restore"]["leaked secret"]["median_hours"] == "unknown"


def test_ac6_no_closed_issue_is_no_median_and_never_0(tmp_path):
    """REQ-063 AC6: a kind with nothing closed in the week."""
    listed = {"issues-open": [], "issues-closed": [], f"issues-{LEAK}": []}
    assert section(tmp_path, listed)["restore"]["leaked secret"] == {
        "closed": 0,
        "median_hours": "none",
        "open": 0,
    }


def test_ac6_no_title_or_body_text_reaches_the_facts_or_the_report(tmp_path):
    """REQ-063 AC6: counts and timings only."""
    marker_text = "example-only-text.example.com"
    body = f"{GOOD_BODY}\n{marker_text}"
    listed = {
        "issues-open": OPENED,
        "issues-closed": [issue(LOCAL + " " + marker_text, "2026-11-03T06:00:00Z", None)],
        f"issues-{LEAK}": [leak(body)],
    }
    found = section(tmp_path, listed)
    assert marker_text not in json.dumps(found) and not any(marker_text in x for x in lines(found))


def test_ac7_another_week_or_older_facts_print_unknown(tmp_path):
    """REQ-063 AC7: the section holds one week, and a report of another week does not reuse it."""
    found = section(tmp_path, {**ISSUES, **RUNS})
    assert UNKNOWN_MINUTES in lines(found, week="2026-W44")
    assert UNKNOWN_MINUTES in lines(found, drop=True)
    assert UNKNOWN_MINUTES not in lines(found, week=WEEK)
