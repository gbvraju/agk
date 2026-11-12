"""Tests of `plan_status.py` and its lines in the weekly report (SPEC-0043 rules 17 to 19 and 26;
REQ-050).

REQ-050 AC5.

Each milestone of `docs/plan/milestones.md` shows its done and open briefs, its hours spent against
the P50 and P85 of `plan_estimate.py`, its forecast, target, status, trend and cause; the weekly
report lists a milestone at risk or late under At risk and a plan or scope change waiting for the
person under Needs you, and a project without a plan gets the report it had. Saved facts of
invented pull requests and briefs only (example.com); no network.
"""

from __future__ import annotations

import copy
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import plan_estimate
import plan_status
import product_report
import pytest
from test_plan_estimate import LIMITS, brief, history, pull

TODAY = "2026-11-04"  # a Wednesday; the report's week is 2026-10-26 to 2026-11-01
KIT = Path(__file__).resolve().parents[2]
REPORT_FACTS = Path(__file__).parent / "fixtures" / "report" / "quiet" / "facts.json"
PARTS = ("briefs ", "hours ", "forecast ", "target ", "status ", "trend ", "cause ")


def closes(until="2026-11-03"):
    """One brief of M0 closed as completed each Tuesday from 2026-08-25 to `until`."""
    out, day, number = [], datetime(2026, 8, 25, 10, tzinfo=UTC), 50
    while day.date().isoformat() <= until:
        out.append(brief(number, "M0", state="closed", closed=day.strftime("%Y-%m-%dT%H:%M:%SZ")))
        day += timedelta(days=7)
        number += 1
    return out


def plan_briefs():
    done = brief(10, "M1", "S", "2-4 hours", state="closed", closed="2026-10-29T10:00:00Z")
    return [done, brief(1, "M1", "S", "2-4 hours"), brief(2, "M1", "M"), brief(3, "M2", "L")]


def done_pull(**extra):
    """The merged pull request of brief 10 (M1): 5.0 hours against 2-4, verdict in the week."""
    p = pull(201, "S", "5.0", "2026-10-30T12:00:00Z", waits=("3.0", "1.0", "0.5"))
    p |= {"brief": 10, "estimated_hours": "2-4", "verdicts": [{"kind": "cleared", "sha": None}]}
    p["verdicts"][0]["at"] = "2026-10-28T09:00:00Z"
    return p | extra


def write(tmp_path, pulls=None, briefs=None, targets=None, changes=None, baseline=True):
    doc = {"schema": 1, "today": TODAY}
    doc["pull_requests"] = (history() + [done_pull()]) if pulls is None else pulls
    doc["flow"] = {"briefs": (plan_briefs() + closes()) if briefs is None else briefs}
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    plan = tmp_path / "docs" / "plan"
    plan.mkdir(parents=True, exist_ok=True)
    targets = {"M1": "2027-06-30", "M2": "2027-06-30"} if targets is None else targets
    text = "# Milestones\n"
    for mid, title in (("M1", "Orders"), ("M2", "Payments")):
        text += f"\n### {mid} {title}\n\nExit: exit: all 3 screens pass\n"
        text += f"Target: {targets.get(mid) or '(verify)'}\n"
    (plan / "milestones.md").write_text(text, encoding="utf-8")
    if baseline:
        (plan / "baseline.json").write_text('{"schema": 1}\n', encoding="utf-8")
    if changes is not None:
        (plan / "scope-changes.md").write_text(changes, encoding="utf-8")
    return path


def run(tmp_path, monkeypatch, capsys, *args, **kwargs):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, **kwargs)
    code = plan_status.main(["--facts", str(path), *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def data(tmp_path, monkeypatch, capsys, **kwargs):
    code, out, err = run(tmp_path, monkeypatch, capsys, "--json", **kwargs)
    assert (code, err) == (0, ""), err
    return {m["id"]: m for m in json.loads(out)["milestones"]} | {"all": json.loads(out)}


def block(out, milestone):
    lines = out.splitlines()
    start = lines.index(next(x for x in lines if x.startswith(f"{milestone} ")))
    return lines[start : start + 8]


# --- rule 17: the seven parts -------------------------------------------------------------------


def test_rule17_each_milestone_prints_the_seven_parts_in_order(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 17."""
    code, out, err = run(tmp_path, monkeypatch, capsys)
    assert (code, err) == (0, "")
    for mid, title in (("M1", "Orders"), ("M2", "Payments")):
        lines = block(out, mid)
        assert lines[0] == f"{mid} {title}"
        assert [x.strip().split(" ")[0] + " " for x in lines[1:]] == list(PARTS)
    m1 = block(out, "M1")
    assert m1[1] == "  briefs 1 done, 2 open"
    assert m1[2].startswith("  hours 5.0 spent of P50 ") and " P85 " in m1[2]
    assert m1[4] == "  target 2027-06-30"


def test_rule17_hours_spent_and_the_estimate_are_plan_estimate_s(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 17 (the P50 and P85 are the estimator's, not computed again)."""
    _, out, _ = run(tmp_path, monkeypatch, capsys)
    capsys.readouterr()
    assert plan_estimate.main(["--facts", str(tmp_path / "facts.json")]) == 0
    first = capsys.readouterr().out.splitlines()[0]
    hours = first.split("hours ")[1].split(";")[0]  # "P50 x P85 y"
    finish = first.split("finish ")[1]
    assert block(out, "M1")[2] == f"  hours 5.0 spent of {hours}"
    assert block(out, "M1")[3] == f"  forecast {finish}"


def test_rule17_unreadable_pull_requests_print_unknown_never_zero(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 17 (`pull_requests` `"unknown"`)."""
    code, out, _ = run(tmp_path, monkeypatch, capsys, pulls="unknown")
    m1 = block(out, "M1")
    assert code == 0 and m1[2].startswith("  hours unknown spent of ")
    assert m1[7] == "  cause unknown" and " 0.0 spent" not in out


def test_rule17_unreadable_briefs_print_unknown_never_zero(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 17 (`flow.briefs` `"unknown"`)."""
    _, out, _ = run(tmp_path, monkeypatch, capsys, briefs="unknown")
    m1 = block(out, "M1")
    assert m1[1] == "  briefs unknown done, unknown open"
    assert m1[3] == "  forecast P50 unknown P85 unknown" and m1[5] == "  status unknown"


def test_rule17_before_publish_the_brief_files_are_the_open_briefs(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 17 (a brief is the milestone's by its `Milestone:` line)."""
    monkeypatch.chdir(tmp_path)
    write(tmp_path, briefs=closes())
    folder = tmp_path / "docs" / "plan" / "briefs" / "M1"
    folder.mkdir(parents=True)
    for key in ("a-orders", "b-export"):
        body = "Milestone: M1\nSize: S\nExpected: 2-4 hours\n"
        (folder / f"{key}.md").write_text(body, encoding="utf-8")
    assert plan_status.main(["--facts", "facts.json"]) == 0
    out = capsys.readouterr().out
    assert block(out, "M1")[1] == "  briefs 0 done, 2 open"
    assert block(out, "M2")[1] == "  briefs 0 done, 0 open"
    assert block(out, "M2")[3] == "  forecast P50 done P85 done"


@pytest.mark.parametrize(
    "args", [["--weeks", "3"], ["--today", "2026-02-30"], ["--base", "x.json"], ["--into", "y"]]
)
def test_rule17_an_unreadable_option_exits_2_naming_it(tmp_path, monkeypatch, capsys, args):
    """REQ-050 AC5: rule 17 (a refusal names the option, never the value)."""
    code, out, err = run(tmp_path, monkeypatch, capsys, *args)
    assert code == 2 and out == "" and err.startswith("plan_status: ")
    assert "2026-02-30" not in err


def test_rule26_the_limits_line_ends_the_text_and_is_in_the_data(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 26."""
    _, out, _ = run(tmp_path, monkeypatch, capsys)
    assert out.splitlines()[-1] == LIMITS
    assert data(tmp_path, monkeypatch, capsys)["all"]["limits"] == LIMITS


def test_rule17_two_runs_are_byte_identical(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 17 (the estimate is seeded)."""
    assert run(tmp_path, monkeypatch, capsys) == run(tmp_path, monkeypatch, capsys)


# --- rule 18: the status, the trend and the cause -----------------------------------------------


def forecast(tmp_path, monkeypatch, capsys):
    return data(tmp_path, monkeypatch, capsys)["M1"]["forecast"]["p85"]


def test_rule18_on_track_when_p85_is_not_after_the_target(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 18."""
    p85 = forecast(tmp_path, monkeypatch, capsys)
    got = data(tmp_path, monkeypatch, capsys, targets={"M1": p85, "M2": "2027-06-30"})
    assert got["M1"]["status"] == "on track"


def test_rule18_at_risk_when_p85_is_after_the_target(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 18."""
    p85 = forecast(tmp_path, monkeypatch, capsys)
    target = (datetime.fromisoformat(p85) - timedelta(days=1)).date()
    got = data(tmp_path, monkeypatch, capsys, targets={"M1": target.isoformat()})
    assert got["M1"]["status"] == "at risk"


def test_rule18_late_after_the_target_with_a_brief_open(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 18 (late comes first, even when uncalibrated)."""
    got = data(tmp_path, monkeypatch, capsys, pulls=[], targets={"M1": "2026-11-03"})
    assert got["M1"]["estimate"] == "uncalibrated" and got["M1"]["status"] == "late"


def test_rule18_unknown_without_a_target_or_when_uncalibrated(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 18."""
    got = data(tmp_path, monkeypatch, capsys, targets={"M1": None, "M2": "2027-06-30"})
    assert got["M1"]["target"] == "none" and got["M1"]["status"] == "unknown"
    got = data(tmp_path, monkeypatch, capsys, pulls=history()[:9])
    assert got["M1"]["status"] == "unknown" and "history 9 of 10" in got["M1"]["reasons"]
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls=history()[:9])
    assert block(out, "M1")[3] == "  forecast uncalibrated" and "P85" not in block(out, "M1")[2]


@pytest.mark.parametrize(
    ("now", "then", "text"),
    [
        ("2026-12-18", "2026-12-11", "P85 7 days later"),
        ("2026-12-04", "2026-12-18", "P85 14 days earlier"),
        ("2026-12-18", "2026-12-18", "same"),
        ("2026-12-18", "unknown", "unknown"),
        ("done", "2026-12-18", "unknown"),
    ],
)
def test_rule18_the_trend_text(now, then, text):
    """REQ-050 AC5: rule 18 (earlier, later, the same or unknown)."""
    assert plan_status.trend_of(now, then) == text


def test_rule18_the_trend_is_the_estimate_from_the_week_s_start(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 18 (the same estimate made from the facts as they were on 2026-10-26)."""
    extra = brief(4, "M1", "M")
    extra["created_at"] = "2026-10-27T09:00:00Z"  # scope that grew in the week
    got = data(tmp_path, monkeypatch, capsys, briefs=plan_briefs() + [extra] + closes())
    doc = json.loads((tmp_path / "facts.json").read_text(encoding="utf-8"))
    then = plan_status.as_of(doc, datetime(2026, 10, 26, tzinfo=UTC))
    assert [b["number"] for b in then["flow"]["briefs"] if b["milestone"] == "M1"] == [10, 1, 2]
    assert next(b for b in then["flow"]["briefs"] if b["number"] == 10)["state"] == "open"
    assert all(p["merged_at"] < "2026-10-26" for p in then["pull_requests"])
    (tmp_path / "then.json").write_text(json.dumps(then), encoding="utf-8")
    capsys.readouterr()
    assert plan_estimate.main(["--facts", "then.json", "--today", "2026-10-25"]) == 0
    first = capsys.readouterr().out.splitlines()[0]
    then_p85 = first.rsplit("P85 ", 1)[1]
    assert got["M1"]["trend"] == plan_status.trend_of(got["M1"]["forecast"]["p85"], then_p85)
    assert got["M1"]["trend"] != "unknown"


CHANGES = """# Scope changes

Scope change: SC-1
What: add brief orders-export to M1
Why: the person asked for it
Source: person 2026-10-27
Effect: P85 hours 10.0 to 14.0
Status: proposed
Approved: 2026-10-28 https://example.com/c/1

Scope change: SC-2
What: add brief refunds to M2
Why: the person asked for it
Source: person 2026-10-29
Effect: P85 hours 20.0 to 26.0
Status: proposed
"""


def test_rule18_each_cause_phrase_with_its_count_in_order(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 18 (review, scope, missed; at most three, in this order)."""
    got = data(tmp_path, monkeypatch, capsys, changes=CHANGES)
    assert got["M1"]["cause"] == [
        "waiting on review 3.0 h this week",
        "scope grew by 1 briefs",
        "1 of 1 estimates missed",
    ]
    stalled = pull(202, "M", None, None) | {"state": "open", "brief": 1, "stalled": True}
    pulls = history() + [done_pull(), stalled]
    got = data(tmp_path, monkeypatch, capsys, pulls=pulls, changes=CHANGES)
    assert got["M1"]["cause"][2] == "1 briefs stalled (builder)" and len(got["M1"]["cause"]) == 3


def test_rule18_none_measured_when_no_count_is_above_zero(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 18."""
    quiet = done_pull(actual_hours="3.0", verdicts=[])
    got = data(tmp_path, monkeypatch, capsys, pulls=history() + [quiet])
    assert got["M1"]["cause"] == ["none measured"] and got["M2"]["cause"] == ["none measured"]


# --- rule 19: into the facts and the report -----------------------------------------------------


def report_facts(tmp_path, monkeypatch, capsys, **kwargs):
    """The report's facts `IN` and the copy `OUT` that `--base IN --into OUT` writes."""
    base = tmp_path / "in.json"
    base.write_text(REPORT_FACTS.read_text(encoding="utf-8"), encoding="utf-8")
    code, out, err = run(
        tmp_path, monkeypatch, capsys, "--base", str(base), "--into", "out.json", **kwargs
    )
    assert (code, out, err) == (0, "", "")
    return json.loads(base.read_text("utf-8")), json.loads(
        (tmp_path / "out.json").read_text("utf-8")
    )


def test_rule19_into_writes_the_base_and_one_key_plan(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 19 (`OUT` is `IN` plus `plan`, the `--json` output)."""
    base, into = report_facts(tmp_path, monkeypatch, capsys)
    assert {k: v for k, v in into.items() if k != "plan"} == base and "plan" not in base
    _, out, _ = run(tmp_path, monkeypatch, capsys, "--json")
    assert into["plan"] == json.loads(out)


def test_rule19_the_copy_validates_against_the_facts_schema(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 19 (the optional top-level `plan`, amendment 115 item 1)."""
    sys.path.insert(0, str(KIT / "tests" / "kit_dev"))
    from jsonschema_lite import errors

    schema = json.loads((KIT / "kit" / "facts-schema.json").read_text(encoding="utf-8"))
    base, into = report_facts(tmp_path, monkeypatch, capsys, changes=CHANGES, baseline=False)
    assert errors(base, schema) == [] and errors(into, schema) == []
    assert errors({**into, "plan": {"milestones": []}}, schema)
    assert "plan" not in schema["required"]


def report_of(doc):
    today = product_report.day_of(doc["today"])
    structure = product_report.build_report(doc, today, None)
    return structure, product_report.render_markdown(structure)


def test_rule19_no_plan_key_gives_the_report_it_had(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 19 (a plan with nothing at risk or waiting adds no line, and the
    schema number of every report is 9, SPEC-0011 rule 72, amendment 115 item 2)."""
    base, into = report_facts(tmp_path, monkeypatch, capsys)
    assert report_of(into)[1] == report_of(base)[1]
    assert report_of(base)[0]["schema"] == 9 == product_report.REPORT_SCHEMA


def test_rule19_a_milestone_at_risk_is_one_at_risk_line(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 19 (`Milestone M<n> "<title>" is <status>: ...; <cause>`)."""
    _, into = report_facts(tmp_path, monkeypatch, capsys, targets={"M1": "2026-11-20"})
    m1 = next(m for m in into["plan"]["milestones"] if m["id"] == "M1")
    assert m1["status"] == "at risk"
    structure, text = report_of(into)
    risky = [i for i in structure["sections"]["at_risk"] if i["kind"] == "milestone-at-risk"]
    assert len(risky) == 1 and risky[0]["id"] == "M1"
    line = (
        f'- Milestone M1 "Orders" is at risk: P85 {m1["forecast"]["p85"]} after target '
        f"2026-11-20; waiting on review 3.0 h this week; 1 of 1 estimates missed"
    )
    assert sum(1 for x in text.splitlines() if x.startswith("- Milestone M")) == 1
    assert any(x.startswith(line + " — https://github.com/") for x in text.splitlines())


def test_rule19_a_waiting_scope_change_and_plan_are_inbox_items(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 19 (Needs you and the inbox, Q-S0043-15)."""
    _, into = report_facts(tmp_path, monkeypatch, capsys, changes=CHANGES, baseline=False)
    assert into["plan"]["waiting"] == {"plan": True, "scope_changes": ["SC-2"]}
    structure, text = report_of(into)
    groups = {g["group"]: g for g in structure["sections"]["needs_you"]}
    assert groups["scope-change"]["count"] == 1 and groups["plan"]["count"] == 1
    assert groups["scope-change"]["items"][0]["id"] == "SC-2"
    assert "- Scope change SC-2 waits for approval — https://github.com/" in text
    assert "- The plan waits for its confirmation (Approve: plan) — https://github.com/" in text
    inbox = product_report.render_inbox(into, product_report.day_of(into["today"]))
    assert "### Scope changes waiting for approval (1)" in inbox
    assert "### Plans waiting for confirmation (1)" in inbox


def test_rule19_an_unreadable_plan_key_is_one_unknown_item(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 19 (an input that cannot be read is `unknown`, never a missing line)."""
    doc = json.loads(REPORT_FACTS.read_text(encoding="utf-8")) | {"plan": "unknown"}
    structure, text = report_of(doc)
    assert "- unknown: the plan could not be read — https://github.com/" in text
    assert structure["counts"]["at_risk"] == "unknown"


def test_rule19_the_report_still_reads_one_file(tmp_path, monkeypatch, capsys):
    """REQ-050 AC5: rule 19 (SPEC-0011 rule 2: the renderer is a function of `OUT` alone)."""
    _, into = report_facts(tmp_path, monkeypatch, capsys, targets={"M1": "2026-11-20"})
    (tmp_path / "docs").rename(tmp_path / "gone")
    again = copy.deepcopy(into)
    assert report_of(again) == report_of(into)
