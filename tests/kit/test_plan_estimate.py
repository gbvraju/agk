"""Tests of `plan_estimate.py` and the facts it reads (SPEC-0043 rules 12 to 16 and 26; REQ-050).

REQ-050 AC4.

Each milestone of `docs/plan/milestones.md` is estimated from the project's own merged pull
requests and its weekly throughput of closed briefs, by a seeded simulation whose inputs are
printed, and is `uncalibrated`, never a single number, when the history is too short. The facts
list every brief issue open or closed in the window with its state, close and plan lines
(amendment 115 item 1). Saved facts of invented pull requests and briefs only; no network.
"""

from __future__ import annotations

import json
import math
import random
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

import common
import facts
import plan_estimate
import pytest

TODAY = "2026-11-04"  # a Wednesday; the 12-week window starts on Monday 2026-08-17
LIMITS = (
    "Estimates are ranges from this project's own history, not promises; AGK drafts from the "
    "sources and the person owns scope."
)
SIZES = {"S": ["2.0", "3.5", "4.0", "5.5"], "M": ["6.0", "8.5", "9.0", "12.0"]}
SIZES |= {"L": ["15.0", "20.5", "24.0", "30.0"]}


def pull(number, size, hours, merged, waits=("1.0", "2.0", "0.5")):
    flow = {"taken_to_pull_request": None, "to_first_verdict": waits[0]}
    flow |= {"verdict_to_cleared": waits[1], "cleared_to_merge": waits[2]}
    return {
        "number": number,
        "state": "merged",
        "merged_at": merged,
        "estimated_size": size,
        "actual_hours": hours,
        "flow": flow,
    }


def history(waits=("1.0", "2.0", "0.5")):
    """Twelve merged pull requests, four of each size, all in October 2026."""
    out, number = [], 100
    for size in ("S", "M", "L"):
        for i, hours in enumerate(SIZES[size]):
            number += 1
            merged = f"2026-10-{10 + i + 4 * 'SML'.index(size):02d}T12:00:00Z"
            out.append(pull(number, size, hours, merged, waits))
    return out


def brief(number, milestone, size="M", expected="4-8 hours", state="open", closed=None):
    return {
        "number": number,
        "title": f"Brief {number} for example.com",
        "created_at": "2026-09-01T09:00:00Z",
        "advances": ["REQ-001"],
        "state": state,
        "closed_at": closed,
        "state_reason": None if state == "open" else "completed",
        "milestone": milestone,
        "size": size,
        "expected": expected,
    }


def closes():
    """Briefs closed as completed in the weeks of 2026-10-12, 10-19 and 11-02: weeks 2, 1, 0, 3."""
    when = ["2026-10-13", "2026-10-14", "2026-10-20", "2026-11-02", "2026-11-03", "2026-11-03"]
    return [
        brief(50 + i, "M0", state="closed", closed=f"{d}T10:00:00Z") for i, d in enumerate(when)
    ]


def open_briefs():
    return [brief(1, "M1", "S", "2-4 hours"), brief(2, "M1", "M"), brief(3, "M2", "L", "10-20 hours")]


def write(tmp_path, pulls=None, briefs=None, milestones=("M1 Orders", "M2 Payments"), **extra):
    doc = {"schema": 1, "today": TODAY, "pull_requests": history() if pulls is None else pulls}
    doc["flow"] = {"briefs": (open_briefs() + closes()) if briefs is None else briefs}
    doc |= extra
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    plan = tmp_path / "docs" / "plan"
    plan.mkdir(parents=True, exist_ok=True)
    text = "# Milestones\n" + "".join(
        f"\n### {m}\n\nExit: exit: all 3 screens pass\nTarget: 2026-12-18\n" for m in milestones
    )
    (plan / "milestones.md").write_text(text, encoding="utf-8")
    return path


def run(tmp_path, monkeypatch, capsys, *args, **kwargs):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, **kwargs)
    code = plan_estimate.main(["--facts", str(path), *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def block(out, milestone):
    lines = out.splitlines()
    start = next(i for i, x in enumerate(lines) if x.startswith(f"{milestone} "))
    return lines[start : start + 3]


def percentiles(values):
    ordered = sorted(values)
    return [ordered[math.ceil(p / 100 * 10000) - 1] for p in (50, 85)]


def expected_hours(milestone, sizes):
    pools = {s: sorted((p for p in history() if p["estimated_size"] == s), key=_order) for s in SIZES}
    rng = random.Random(f"hours:{milestone}")
    sums = [
        sum((Decimal(rng.choice(pools[s])["actual_hours"]) for s in sizes), Decimal(0))
        for _ in range(10000)
    ]
    return [str(v.quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)) for v in percentiles(sums)]


def _order(p):
    return (p["merged_at"], p["number"])


def expected_weeks(milestone, need, weeks=(2, 1, 0, 3)):
    rng = random.Random(f"weeks:{milestone}")
    ks = []
    for _ in range(10000):
        got = k = 0
        while got < need:
            got += rng.choice(weeks)
            k += 1
        ks.append(k)
    return percentiles(ks)


# --- rule 12: the window, the history and the minimum -------------------------------------------


@pytest.mark.parametrize("weeks", ["3", "53", "ten"])
def test_rule12_weeks_outside_4_to_52_exit_2_naming_the_option(tmp_path, monkeypatch, capsys, weeks):
    """REQ-050 AC4: rule 12."""
    code, out, err = run(tmp_path, monkeypatch, capsys, "--weeks", weeks)
    assert code == 2 and "--weeks" in err and out == ""


def test_rule12_a_merge_before_the_first_monday_is_not_history(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 12."""
    pulls = history() + [pull(99, "S", "1.0", "2026-08-16T23:00:00Z")]
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls=pulls)
    assert "window 2026-08-17 to 2026-11-04 (12 ISO weeks), history S 4 M 4 L 4 " in out


def test_rule12_nine_items_are_uncalibrated(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 12, the minimum `[plan] calibration_min` of 10."""
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls=history()[:9])
    assert "uncalibrated" in block(out, "M1")[0] and "history 9 of 10" in block(out, "M1")[0]


def test_rule12_two_of_a_size_the_milestone_uses_are_uncalibrated(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 12, at least 3 of each size among the milestone's open briefs."""
    pulls = [p for p in history() if p["number"] not in (111, 112)]  # two of the four L
    pulls += [pull(120, "S", "3.0", "2026-10-30T12:00:00Z")]
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls=pulls)
    assert "P50" in block(out, "M1")[0]  # M1 uses S and M only
    assert "uncalibrated" in block(out, "M2")[0] and "size L 2 of 3" in block(out, "M2")[0]


def test_rule12_three_weeks_of_throughput_are_uncalibrated(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 12, throughput from the week of the first close to today's week."""
    later = [b for b in closes() if b["closed_at"] >= "2026-10-19"]  # weeks 10-19 to 11-02
    _, out, _ = run(tmp_path, monkeypatch, capsys, briefs=open_briefs() + later)
    assert "throughput 3 of 4 weeks" in block(out, "M1")[0]


def test_rule12_a_brief_closed_as_not_planned_is_no_throughput(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 12, only briefs closed as completed count."""
    dropped = brief(70, "M0", state="closed", closed="2026-10-05T10:00:00Z")
    dropped["state_reason"] = "not_planned"
    _, out, _ = run(tmp_path, monkeypatch, capsys, briefs=open_briefs() + closes() + [dropped])
    assert "throughput 4 weeks median 1.5 a week" in out


# --- rule 13: the simulation ---------------------------------------------------------------------


def test_rule13_hours_and_dates_equal_an_independent_computation(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 13, seeds, pool order, positions 5000 and 8500, earlier milestones."""
    _, out, _ = run(tmp_path, monkeypatch, capsys)
    p50, p85 = expected_hours("M1", ["S", "M"])
    k50, k85 = expected_weeks("M1", 2)
    first = plan_estimate.friday_of(date(2026, 11, 4), k50)
    last = plan_estimate.friday_of(date(2026, 11, 4), k85)
    assert block(out, "M1")[0] == (
        f"M1 Orders: hours P50 {p50} P85 {p85}; finish P50 {first} P85 {last}"
    )
    q50, q85 = expected_hours("M2", ["L"])
    k50, k85 = expected_weeks("M2", 3)  # M2's one open brief after M1's two
    first = plan_estimate.friday_of(date(2026, 11, 4), k50)
    last = plan_estimate.friday_of(date(2026, 11, 4), k85)
    assert block(out, "M2")[0] == (
        f"M2 Payments: hours P50 {q50} P85 {q85}; finish P50 {first} P85 {last}"
    )


def test_rule13_a_count_of_weeks_is_the_friday_of_that_full_week():
    """REQ-050 AC4: rule 13, the Monday after --today plus 7k - 3 days."""
    today = date(2026, 11, 4)
    assert plan_estimate.friday_of(today, 1).isoformat() == "2026-11-13"
    assert plan_estimate.friday_of(today, 2).isoformat() == "2026-11-20"
    assert plan_estimate.friday_of(date(2026, 11, 9), 1).isoformat() == "2026-11-20"


def test_rule13_a_throughput_that_cannot_reach_in_520_weeks_is_unknown(
    tmp_path, monkeypatch, capsys
):
    """REQ-050 AC4: rule 13."""
    one = [brief(50, "M0", state="closed", closed="2026-10-13T10:00:00Z")]
    many = [brief(200 + i, "M1", "S", "2-4 hours") for i in range(200)]
    _, out, _ = run(tmp_path, monkeypatch, capsys, briefs=many + one, milestones=("M1 Orders",))
    assert block(out, "M1")[0].endswith("; finish P50 unknown P85 unknown")


def test_rule13_two_runs_are_byte_identical(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 13."""
    first = run(tmp_path, monkeypatch, capsys)
    assert first == run(tmp_path, monkeypatch, capsys) and first[0] == 0


def test_rule13_a_milestone_with_no_open_brief_is_done(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 13."""
    shut = brief(3, "M2", "L", state="closed", closed="2026-10-28T10:00:00Z")
    briefs = open_briefs()[:2] + [shut] + closes()
    _, out, _ = run(tmp_path, monkeypatch, capsys, briefs=briefs)
    assert block(out, "M2")[0] == "M2 Payments: hours done; finish P50 done P85 done"


def test_rule13_today_defaults_to_the_facts_and_can_be_given(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 13, `--today` (`Q-S0043-17`)."""
    _, out, _ = run(tmp_path, monkeypatch, capsys, "--today", "2026-11-09")
    assert "window 2026-08-24 to 2026-11-09 (12 ISO weeks)" in out
    code, _, err = run(tmp_path, monkeypatch, capsys, "--today", "2026-02-30")
    assert code == 2 and "--today" in err


def test_rule13_unpublished_briefs_are_the_plan_files_by_key(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 13, before publish the milestone's briefs are its rendered brief files."""
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, briefs=closes(), milestones=("M1 Orders",))
    folder = tmp_path / "docs" / "plan" / "briefs" / "M1"
    folder.mkdir(parents=True)
    (folder / "B2.md").write_text("# Two\n\nSize: M\nExpected: 4-8 hours\nMilestone: M1\n")
    (folder / "B1.md").write_text("# One\n\nSize: S\nExpected: 2-4 hours\nMilestone: M1\n")
    assert plan_estimate.main(["--facts", str(path)]) == 0
    p50, p85 = expected_hours("M1", ["S", "M"])
    assert capsys.readouterr().out.startswith(f"M1 Orders: hours P50 {p50} P85 {p85}; ")


# --- rule 14: uncalibrated, shown as such ---------------------------------------------------------


def test_rule14_uncalibrated_prints_the_declared_sums_and_no_percentile(
    tmp_path, monkeypatch, capsys
):
    """REQ-050 AC4: rule 14."""
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls=history()[:9])
    head = block(out, "M1")[0]
    assert head == "M1 Orders: uncalibrated (history 9 of 10); declared 6-12 hours; finish unknown"
    assert "P50" not in out and "P85" not in out


def test_rule14_a_brief_without_expected_takes_the_owner_default(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 14, `[plan] default_hours` printed as `owner default` (`Q-S0043-10`)."""
    briefs = [brief(1, "M1", "S", "unknown"), brief(2, "M1", "M")] + closes()
    (tmp_path / "agk.toml").write_text('[plan]\ndefault_hours = { S = "2-4" }\n')
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls=history()[:9], briefs=briefs)
    assert "declared 6-12 hours (1 owner default)" in block(out, "M1")[0]


def test_rule14_without_the_setting_a_brief_has_no_estimate(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 14."""
    briefs = [brief(1, "M1", "S", "unknown"), brief(2, "M1", "M")] + closes()
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls=history()[:9], briefs=briefs)
    assert "declared 4-8 hours; 1 briefs without an estimate; finish unknown" in block(out, "M1")[0]


def test_rule14_a_history_that_cannot_be_read_is_unknown_never_zero(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 14, an input that cannot be read is never counted as 0."""
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls="unknown")
    assert "uncalibrated (history unknown)" in block(out, "M1")[0]
    assert "history unknown" in block(out, "M1")[2]


@pytest.mark.parametrize(
    ("table", "setting"),
    [
        ("calibration_min = 0", "[plan] calibration_min"),
        ('calibration_min = "ten"', "[plan] calibration_min"),
        ("iteration_days = 31", "[plan] iteration_days"),
        ('default_hours = { S = "4-2" }', "[plan] default_hours"),
        ('default_hours = { XL = "1-2" }', "[plan] default_hours"),
        ("buffer = 2", "[plan] buffer"),
    ],
)
def test_rule14_a_bad_plan_setting_is_refused_naming_it(tmp_path, monkeypatch, capsys, table, setting):
    """REQ-050 AC4: rules 14 and 25, the `[plan]` table holds three settings."""
    (tmp_path / "agk.toml").write_text(f"[plan]\n{table}\n")
    code, out, err = run(tmp_path, monkeypatch, capsys)
    assert code == 2 and setting in err and out == ""
    assert "4-2" not in err and "ten" not in err


def test_rule14_the_plan_settings_default_without_the_table(tmp_path):
    """REQ-050 AC4: rule 14 (`Q-S0043-3`, `Q-S0043-5`)."""
    expected = {"iteration_days": 10, "calibration_min": 10, "default_hours": {}}
    assert common.plan_settings(tmp_path) == expected
    (tmp_path / "agk.toml").write_text('[plan]\ncalibration_min = 4\ndefault_hours = { L = "8-16" }\n')
    assert common.plan_settings(tmp_path)["calibration_min"] == 4
    assert common.plan_settings(tmp_path)["default_hours"] == {"L": "8-16"}


# --- rule 15: the waits are inside the lead time --------------------------------------------------


def test_rule15_large_waits_add_nothing_to_the_hours(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 15 (`Q-S0043-12`)."""
    _, small, _ = run(tmp_path, monkeypatch, capsys)
    _, large, _ = run(tmp_path, monkeypatch, capsys, pulls=history(("90.0", "80.0", "70.0")))
    assert block(small, "M1")[0] == block(large, "M1")[0]


def test_rule15_the_breakdown_prints_three_medians_and_the_queue_unknown(
    tmp_path, monkeypatch, capsys
):
    """REQ-050 AC4: rule 15 (`Q-S0043-8`)."""
    pulls = history()
    pulls[0]["flow"]["to_first_verdict"] = "unknown"
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls=pulls)
    assert block(out, "M1")[1] == (
        "waits inside the hours, never added: to first verdict 1.0 h, verdict to cleared 2.0 h, "
        "cleared to merge 0.5 h, queue unknown"
    )
    _, out, _ = run(tmp_path, monkeypatch, capsys, pulls=[])
    assert "to first verdict unknown, verdict to cleared unknown" in block(out, "M1")[1]


# --- rule 16: every estimate prints its inputs ----------------------------------------------------


def test_rule16_every_estimate_is_followed_by_its_inputs(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 16, and rule 26's limits line ends the output."""
    _, out, _ = run(tmp_path, monkeypatch, capsys)
    for n in (1, 2):
        assert block(out, f"M{n}")[2] == (
            "inputs: window 2026-08-17 to 2026-11-04 (12 ISO weeks), history S 4 M 4 L 4 "
            "(2026-10-10 to 2026-10-21), throughput 4 weeks median 1.5 a week, "
            f"waits review 1.0 h merge 0.5 h queue unknown, trials 10000 seeds hours:M{n} weeks:M{n}"
        )
    assert out.splitlines()[-1] == LIMITS


def test_rule16_a_short_window_is_shown(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rules 12 and 16 (`Q-S0043-19`)."""
    _, out, _ = run(tmp_path, monkeypatch, capsys, "--weeks", "4")
    assert "inputs: window 2026-10-12 to 2026-11-04 (4 ISO weeks), history S 4 M 4 L 4 " in out


def test_rule16_input_problems_exit_2_naming_the_option(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: rule 16, a facts or plan that cannot be read is refused, never guessed."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bad.json").write_text("not json")
    assert plan_estimate.main(["--facts", "bad.json"]) == 2
    assert "--facts" in capsys.readouterr().err
    path = write(tmp_path)
    assert plan_estimate.main(["--facts", str(path), "--plan", "nowhere"]) == 2
    assert "--plan" in capsys.readouterr().err


# --- amendment 115 item 1: the facts list every brief ---------------------------------------------


class Saved:
    def __init__(self, issues):
        self.issues = issues

    def get(self, name, endpoint):
        return self.issues if name == "issues-agk-brief" else []


def issue(number, state, body, closed=None, reason=None):
    return {
        "number": number,
        "title": f"Brief {number}",
        "state": state,
        "created_at": "2026-09-01T09:00:00Z",
        "closed_at": closed,
        "state_reason": reason,
        "body": body,
    }


def test_amendment115_the_facts_list_closed_briefs_of_the_window_with_their_lines():
    """REQ-050 AC4: rule 12 and amendment 115 item 1."""
    body = "Advances: REQ-001\nSize: M\nExpected: 4-8 hours\nMilestone: M1\n"
    issues = [
        issue(1, "open", body),
        issue(2, "closed", body, "2026-10-13T10:00:00Z", "completed"),
        issue(3, "closed", body, "2026-08-16T10:00:00Z", "completed"),  # before the window
        issue(4, "closed", "Advances: none\nSize: XL\n", "2026-10-20T10:00:00Z", "not_planned"),
        issue(5, "closed", body, "2026-10-21T10:00:00Z", "reopened"),
    ]
    start = facts.window_start(date(2026, 11, 4), 12)
    listed = facts.flow_section(Saved(issues), {}, None, start=start)["briefs"]
    assert [b["number"] for b in listed] == [1, 2, 4, 5]
    first, second, third, fifth = listed
    assert (first["state"], first["closed_at"], first["state_reason"]) == ("open", None, None)
    assert (first["milestone"], first["size"], first["expected"]) == ("M1", "M", "4-8 hours")
    assert (second["state"], second["state_reason"]) == ("closed", "completed")
    assert second["closed_at"] == "2026-10-13T10:00:00Z"
    assert (third["state_reason"], third["milestone"]) == ("not_planned", None)
    assert (third["size"], third["expected"]) == ("unknown", "unknown")
    assert fifth["state_reason"] == "unknown"


def test_amendment115_open_briefs_alone_without_a_window():
    """REQ-050 AC4: amendment 115 item 1, the existing callers see the open briefs as before."""
    issues = [issue(1, "open", "Advances: new\n"), issue(2, "closed", "", "2026-10-13T10:00:00Z")]
    listed = facts.flow_section(Saved(issues), {}, None)["briefs"]
    assert [(b["number"], b["advances"], b["state"]) for b in listed] == [(1, "new", "open")]


def test_amendment115_size_and_expected_are_read_apart():
    """REQ-050 AC4: amendment 115 item 1, each line by SPEC-0018 rule 2's pattern, imported."""
    assert common.estimate_parts("Size: S\n") == ("S", "unknown")
    assert common.estimate_parts("Expected: 5-2 hours\nSize: L\n") == ("L", "unknown")
    assert common.estimate_parts("Size: M\nSize: S\nExpected: 1-2 hours") == ("unknown", "1-2 hours")
    assert common.estimate_parts(None) == ("unknown", "unknown")
    assert plan_estimate.ESTIMATE_LINES is common.ESTIMATE_LINES
    assert plan_estimate.window_start is facts.window_start


def test_amendment115_the_report_counts_only_open_briefs():
    """REQ-050 AC4: amendment 115 item 1, a reader of open briefs filters on `state` `open`."""
    import product_report

    assert 'get("state", "open") == "open"' in Path(product_report.__file__).read_text()
