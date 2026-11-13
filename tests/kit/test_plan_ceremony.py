"""Tests of `plan_ceremony.py`: the iteration and the four ceremony outputs (SPEC-0043 rules 23, 24
and 26, amendment 164 item 4; REQ-050).

REQ-050 AC7.

The plan runs in time boxes of `[plan] iteration_days` working days numbered from the baseline's
date, and the planning, daily status, review and retrospective are text printed for the person from
measured facts: AGK runs no meeting, posts nothing and files nothing. Saved facts of invented pull
requests and briefs only (example.com); no network.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import plan_ceremony
import pytest
from test_plan_estimate import LIMITS, brief, history, pull

TODAY = "2026-11-04"  # a Wednesday; with the baseline below, iteration 2 is 2026-10-26 to 11-06
BASELINE = "2026-10-12"  # a Monday
REPO = "example/shop"
SCRIPT = Path(plan_ceremony.__file__)
DESIGN_ROW = (
    "| design | i1 | " + "a" * 64 + " | " + "b" * 40 + " | 2026-10-20 | https://example.com/c/1 |"
)


def weekly_closes(until="2026-11-03"):
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
    """The merged pull request of brief 10 (M1): 5.0 hours against 2-4, merged in iteration 2."""
    p = pull(201, "S", "5.0", "2026-10-30T12:00:00Z", waits=("3.0", "1.0", "0.5"))
    p |= {"brief": 10, "estimated_hours": "2-4", "proof": "proven", "title": "Orders list"}
    p["verdicts"] = [{"kind": "cleared", "sha": None, "at": "2026-10-30T09:00:00Z"}]
    return p | extra


def write(tmp_path, pulls=None, briefs=None, baseline=BASELINE, days=None, requirements=None):
    doc = {"schema": 1, "today": TODAY, "repo": REPO}
    doc["pull_requests"] = (history() + [done_pull()]) if pulls is None else pulls
    doc["flow"] = {"briefs": (plan_briefs() + weekly_closes()) if briefs is None else briefs}
    doc["requirements"] = (
        [{"id": "REQ-001", "title": "Orders", "status": "done"}]
        if requirements is None
        else requirements
    )
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    plan = tmp_path / "docs" / "plan"
    plan.mkdir(parents=True, exist_ok=True)
    text = "# Milestones\n"
    for mid, title, demo in (
        ("M1", "Orders", "orders/default, orders/empty"),
        ("M2", "Payments", "pay/default"),
    ):
        text += f"\n### {mid} {title}\n\nExit: every screen of {mid} reads match in "
        text += f"design_compare.py against i1\nDemo: {demo}\nTarget: 2027-06-30\n"
    (plan / "milestones.md").write_text(text, encoding="utf-8")
    if baseline is not None:
        doc = {"schema": 1, "head": "c" * 40, "date": baseline, "link": "https://example.com/b"}
        doc["milestones"] = []
        (plan / "baseline.json").write_text(json.dumps(doc), encoding="utf-8")
    if days is not None:
        (tmp_path / "agk.toml").write_text(f"[plan]\niteration_days = {days}\n", encoding="utf-8")
    return path


def run(tmp_path, monkeypatch, capsys, command, *args, **kwargs):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, **kwargs)
    code = plan_ceremony.main([command, "--facts", str(path), *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def stalls_file(tmp_path, stalls):
    path = tmp_path / "stalls.json"
    path.write_text(json.dumps({"stalls": stalls}), encoding="utf-8")
    return str(path)


def stall(number, kind="review", cause="no verdict for 30 hours"):
    return {"kind": kind, "number": number, "cause": cause, "fix": "ask the conductor"}


# --- rule 23: the iteration -----------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0", "31", '"ten"'])
def test_rule23_a_bad_iteration_days_is_refused_naming_the_setting(
    tmp_path, monkeypatch, capsys, value
):
    """REQ-050 AC7: rule 23, refused with exit 2 naming the setting, never the value."""
    for command in ("planning", "daily", "review", "retro"):
        code, out, err = run(tmp_path, monkeypatch, capsys, command, days=value)
        assert (code, out) == (2, "")
        assert "[plan] iteration_days" in err
        assert "31" not in err and "ten" not in err


@pytest.mark.parametrize(
    ("today", "days", "found"),
    [
        ("2026-10-12", 10, (1, "2026-10-12", "2026-10-23")),
        ("2026-10-23", 10, (1, "2026-10-12", "2026-10-23")),
        ("2026-10-24", 10, (2, "2026-10-26", "2026-11-06")),  # a Saturday: the next working day
        ("2026-10-26", 10, (2, "2026-10-26", "2026-11-06")),
        ("2026-11-06", 10, (2, "2026-10-26", "2026-11-06")),
        ("2026-11-09", 10, (3, "2026-11-09", "2026-11-20")),
        ("2026-10-15", 3, (2, "2026-10-15", "2026-10-19")),
        ("2026-10-12", 1, (1, "2026-10-12", "2026-10-12")),
        ("2026-10-13", 1, (2, "2026-10-13", "2026-10-13")),
    ],
)
def test_rule23_iterations_follow_working_days_from_the_baseline(today, days, found):
    """REQ-050 AC7: rule 23, Monday to Friday, numbered from 1 from the baseline's date."""
    got = plan_ceremony.iteration_of(date.fromisoformat(BASELINE), date.fromisoformat(today), days)
    assert (got[0], got[1].isoformat(), got[2].isoformat()) == found


def test_rule23_a_weekend_baseline_starts_on_the_next_working_day():
    """REQ-050 AC7: rule 23."""
    got = plan_ceremony.iteration_of(date(2026, 10, 10), date(2026, 10, 12), 10)
    assert (got[0], got[1].isoformat()) == (1, "2026-10-12")


def test_rule23_before_the_baseline_date_there_is_no_iteration():
    """REQ-050 AC7: rule 23."""
    assert plan_ceremony.iteration_of(date(2026, 10, 12), date(2026, 10, 9), 10) is None


def test_rule23_the_planning_header_names_the_iteration(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 23, with `iteration_days` read from agk.toml."""
    code, out, _ = run(tmp_path, monkeypatch, capsys, "planning")
    assert code == 0
    assert (
        out.splitlines()[0] == "Planning: iteration 2 (2026-10-26 to 2026-11-06), 10 working days"
    )
    code, out, _ = run(tmp_path, monkeypatch, capsys, "planning", days="5")
    assert out.splitlines()[0] == "Planning: iteration 4 (2026-11-02 to 2026-11-06), 5 working days"


def test_rule23_without_a_baseline_the_iteration_is_unknown(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 23; the review and the retrospective need an iteration."""
    code, out, _ = run(tmp_path, monkeypatch, capsys, "planning", baseline=None)
    assert code == 0 and "iteration unknown (no baseline)" in out.splitlines()[0]
    for command in ("review", "retro"):
        code, out, err = run(tmp_path, monkeypatch, capsys, command, baseline=None)
        assert (code, out) == (2, "") and "--plan" in err


# --- rule 24: planning --------------------------------------------------------------------------


def test_rule24_planning_stays_within_the_measured_capacity(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, two briefs closed in each full past iteration: capacity 2."""
    code, out, err = run(tmp_path, monkeypatch, capsys, "planning")
    assert (code, err) == (0, "")
    lines = out.splitlines()
    assert lines[1].startswith("capacity 2 briefs (P50 of 4 past iterations")
    head = lines.index("Proposed for the person to accept or change")
    proposed = [x for x in lines[head + 1 :] if x.startswith("  ")]
    assert [x.split()[1] for x in proposed] == ["#1", "#2"]  # M1 first, by issue number
    assert "not proposed (over capacity): 1 brief" in out
    assert lines[-1] == LIMITS


def test_rule24_capacity_is_the_p50_of_briefs_closed_per_iteration(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, counts 1, 3, 2 and 5 in the four past iterations: P50 is 2."""
    days = {
        "2026-09-01": 1,
        "2026-09-15": 3,
        "2026-09-29": 2,
        "2026-10-13": 5,
    }
    closed, number = [], 60
    first = brief(59, "M0", state="closed", closed="2026-08-25T10:00:00Z")  # the throughput start
    for day, count in days.items():
        for _ in range(count):
            closed.append(brief(number, "M0", state="closed", closed=f"{day}T10:00:00Z"))
            number += 1
    code, out, _ = run(
        tmp_path, monkeypatch, capsys, "planning", briefs=plan_briefs() + [first, *closed]
    )
    assert code == 0 and out.splitlines()[1].startswith("capacity 2 briefs")


def test_rule24_uncalibrated_capacity_is_unknown_and_cuts_nothing(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, `capacity unknown` while the throughput is under four weeks."""
    closed = [
        brief(70 + i, "M0", state="closed", closed=f"{d}T10:00:00Z")
        for i, d in enumerate(("2026-10-20", "2026-10-27", "2026-11-03"))
    ]
    code, out, _ = run(tmp_path, monkeypatch, capsys, "planning", briefs=plan_briefs() + closed)
    assert code == 0
    assert out.splitlines()[1] == "capacity unknown (throughput 3 of 4 weeks)"
    head = out.splitlines().index("Proposed for the person to accept or change")
    proposed = [x for x in out.splitlines()[head + 1 :] if x.startswith("  ")]
    assert [x.split()[1] for x in proposed] == ["#1", "#2", "#3"]
    assert "over capacity" not in out


def test_rule24_planning_prints_the_forecast_of_the_estimator(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24 with rule 13, the estimator's lines, unchanged."""
    import plan_estimate

    code, out, _ = run(tmp_path, monkeypatch, capsys, "planning")
    assert code == 0
    assert plan_estimate.main(["--facts", str(tmp_path / "facts.json")]) == 0
    estimate = capsys.readouterr().out.splitlines()
    assert "\n".join(estimate[:-1]) in out
    assert out.count(LIMITS) == 1


def test_rule24_brief_files_follow_depends_on_then_priority(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, before publish the brief files in Depends-on, then priority order."""
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, briefs=weekly_closes())
    folder = tmp_path / "docs" / "plan" / "briefs" / "M1"
    folder.mkdir(parents=True)
    files = {
        "a-list": "Size: S\nExpected: 2-4 hours\nPriority: 2\n",
        "b-detail": "Size: M\nExpected: 4-8 hours\nDepends-on: c-shell\nPriority: 1\n",
        "c-shell": "Size: S\nExpected: 2-4 hours\nPriority: 3\n",
    }
    for key, text in files.items():
        (folder / f"{key}.md").write_text(f"# {key}\n\n{text}Milestone: M1\n", encoding="utf-8")
    assert plan_ceremony.main(["planning", "--facts", str(path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    head = lines.index("Proposed for the person to accept or change")
    proposed = [x.split()[1] for x in lines[head + 1 :] if x.startswith("  ")]
    assert proposed == ["M1/a-list", "M1/c-shell"]  # c-shell before its dependent b-detail
    assert "not proposed (over capacity): 1 brief" in "\n".join(lines)


# --- rule 24: the daily status -------------------------------------------------------------------


def daily_pulls():
    opened = {"state": "open", "merged_at": None, "title": "Payments form"}
    return [
        *history(),
        done_pull(),
        pull(202, "M", "8.5", "2026-11-03T15:00:00Z") | {"title": "Orders filter"},
        pull(301, "M", None, None) | opened,
        pull(302, "S", None, None) | opened | {"title": "Refunds", "stalled": True},
    ]


def test_rule24_daily_names_what_finished_runs_and_is_blocked(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, the blocked cause is read from the saved stalls."""
    stalls = stalls_file(tmp_path, [stall(301)])
    code, out, err = run(
        tmp_path, monkeypatch, capsys, "daily", "--stalls", stalls, pulls=daily_pulls()
    )
    assert (code, err) == (0, "")
    lines = out.splitlines()
    assert len(lines) <= 10
    assert lines[0] == "Daily status 2026-11-04 (since 2026-11-03), iteration 2"
    assert lines[1].startswith("finished: #202 Orders filter")
    assert "brief #" in lines[1]  # the brief of M0 closed on 2026-11-03
    assert lines[2] == "in progress: #301 Payments form; #302 Refunds"
    assert "blocked: #301 review: no verdict for 30 hours" in lines
    assert "blocked: #302 stalled (facts)" in lines


def test_rule24_daily_has_at_most_ten_lines(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, twelve stalls still give ten lines, the last counting the rest."""
    stalls = stalls_file(tmp_path, [stall(400 + i) for i in range(12)])
    code, out, _ = run(
        tmp_path, monkeypatch, capsys, "daily", "--stalls", stalls, pulls=daily_pulls()
    )
    lines = out.splitlines()
    assert code == 0 and len(lines) == 10
    assert lines[-1] == "blocked: and 7 more"


@pytest.mark.parametrize("option", ["--stalls", "--matches"])
def test_rule24_an_unreadable_saved_file_is_refused_naming_the_option(
    tmp_path, monkeypatch, capsys, option
):
    """REQ-050 AC7: rule 24, exit 2 naming the option, never the value."""
    bad = tmp_path / "bad.json"
    bad.write_text("not json example.com", encoding="utf-8")
    command = "daily" if option == "--stalls" else "review"
    code, out, err = run(tmp_path, monkeypatch, capsys, command, option, str(bad))
    assert (code, out) == (2, "") and option in err and "example.com" not in err


# --- rule 24: the review -------------------------------------------------------------------------


def review_plan(tmp_path):
    plan = tmp_path / "docs" / "plan"
    folder = plan / "briefs" / "M1"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "orders.md").write_text(
        "# Orders\n\nAdvances: R1\nSize: S\nExpected: 2-4 hours\nMilestone: M1\n"
        "Screens: i1 orders/default, orders/empty\n",
        encoding="utf-8",
    )
    (plan / "requirements-proposed.md").write_text(
        "# Requirements proposed\n\n### R1 Orders list\n\nPersona: P1 Shop owner\n"
        "Story: As Shop owner, I want my orders, so that I ship them.\n",
        encoding="utf-8",
    )
    design = tmp_path / "docs" / "design"
    design.mkdir(parents=True, exist_ok=True)
    head = "| kind | version | digest | head | date | comment |\n"
    head += "| --- | --- | --- | --- | --- | --- |\n"
    (design / "signoffs.md").write_text(f"# Sign-offs\n\n{head}{DESIGN_ROW}\n", encoding="utf-8")
    matches = tmp_path / "matches.json"
    lines = {
        "201": ["Design match: orders/default match"],
        "301": ["Design match: orders/empty match"],
    }
    matches.write_text(json.dumps(lines), encoding="utf-8")
    return str(matches)


def review(tmp_path, monkeypatch, capsys, **kwargs):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, **kwargs)
    matches = review_plan(tmp_path)
    code = plan_ceremony.main(["review", "--facts", str(path), "--matches", matches])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_rule24_review_lists_evidence_per_touched_milestone(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, the merged pull requests, the requirements done and the proof."""
    pulls = [*history(), done_pull(), pull(301, "M", None, None) | {"state": "open", "brief": 1}]
    code, out, err = review(tmp_path, monkeypatch, capsys, pulls=pulls)
    assert (code, err) == (0, "")
    lines = out.splitlines()
    assert lines[0] == "Review: iteration 2 (2026-10-26 to 2026-11-06)"
    assert "M1 Orders" in lines and "M2 Payments" not in lines  # M2 was not touched
    assert "  exit: every screen of M1 reads match in design_compare.py against i1" in lines
    assert (
        f"    evidence: #201 https://github.com/{REPO}/pull/201 merged 2026-10-30 proof proven"
        in lines
    )
    assert "    evidence: requirement REQ-001 done" in lines


def test_rule24_review_prints_the_signed_off_design_version(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, the `design` row of docs/design/signoffs.md and its link."""
    code, out, _ = review(tmp_path, monkeypatch, capsys)
    assert code == 0 and "  design: i1 https://example.com/c/1" in out.splitlines()


def test_rule24_review_lists_each_demo_screen_with_its_match_and_persona(
    tmp_path, monkeypatch, capsys
):
    """REQ-050 AC7: rule 24, amendment 164 item 4; an open pull request's line is no evidence."""
    pulls = [*history(), done_pull(), pull(301, "M", None, None) | {"state": "open", "brief": 1}]
    code, out, _ = review(tmp_path, monkeypatch, capsys, pulls=pulls)
    lines = out.splitlines()
    assert code == 0
    assert "  demo orders/default: match (#201); persona P1 Shop owner" in lines
    assert "  demo orders/empty: no evidence yet; persona P1 Shop owner" in lines


def test_rule24_a_criterion_without_evidence_prints_no_evidence_yet(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, a touched milestone with nothing merged and nothing done."""
    requirements = [{"id": "REQ-001", "title": "Orders", "status": "planned"}]
    code, out, _ = review(tmp_path, monkeypatch, capsys, pulls=history(), requirements=requirements)
    lines = out.splitlines()
    assert code == 0 and "M1 Orders" in lines  # brief 10 closed in the iteration
    assert "    no evidence yet" in lines
    assert "  demo orders/default: no evidence yet; persona P1 Shop owner" in lines


def test_rule24_review_without_a_design_row_prints_none(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, no design row and no matches file."""
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path)
    assert plan_ceremony.main(["review", "--facts", str(path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "  design: no design sign-off" in lines
    assert "  demo orders/default: no evidence yet; persona unknown" in lines


# --- rule 24: the retrospective ------------------------------------------------------------------


def retro_pulls():
    rework = pull(202, "M", "8.5", "2026-11-02T12:00:00Z", waits=("5.0", "2.0", "1.5"))
    rework |= {"brief": 1, "estimated_hours": "6-10"}
    rework["verdicts"] = [
        {"kind": "fix", "sha": None, "at": "2026-10-31T09:00:00Z"},
        {"kind": "cleared", "sha": None, "at": "2026-11-01T09:00:00Z"},
    ]
    return [*history(), done_pull(), rework]


def test_rule24_retro_prints_measured_facts_only(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, estimates by size, median waits, rework and stalls by kind."""
    stalls = stalls_file(tmp_path, [stall(301), stall(302), stall(303, kind="ci-red")])
    code, out, err = run(
        tmp_path, monkeypatch, capsys, "retro", "--stalls", stalls, pulls=retro_pulls()
    )
    assert (code, err) == (0, "")
    lines = out.splitlines()
    assert lines[0] == "Retrospective: iteration 2 (2026-10-26 to 2026-11-06)"
    assert "estimates within range: S 0 of 1, M 1 of 1, L 0 of 0" in lines
    assert (
        "median waits: to first verdict 4.0 h, verdict to cleared 1.5 h, cleared to merge 1.0 h"
        in lines
    )
    assert "rework: 1 fix verdicts over 2 merged pull requests" in lines
    assert "stalls by kind: review 2, ci-red 1" in lines


def test_rule24_retro_has_at_most_three_improvements(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, four measured triggers give three candidate briefs."""
    stalls = stalls_file(tmp_path, [stall(301)])
    code, out, _ = run(
        tmp_path, monkeypatch, capsys, "retro", "--stalls", stalls, pulls=retro_pulls()
    )
    candidates = [x for x in out.splitlines() if x.startswith("Candidate brief ")]
    assert code == 0 and len(candidates) == 3
    assert all(x.endswith("(printed for the person; not filed)") for x in candidates)
    assert out.count('  Sentence: "') == 3 and out.count("  Measured: before: ") == 3


def test_rule24_retro_with_nothing_measured_proposes_nothing(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, no pull request merged in the iteration."""
    code, out, _ = run(tmp_path, monkeypatch, capsys, "retro", pulls=history())
    assert code == 0
    assert "none proposed (nothing measured to improve)" in out.splitlines()
    assert "Candidate brief" not in out


def test_rule24_nothing_is_posted_or_filed(tmp_path, monkeypatch, capsys):
    """REQ-050 AC7: rule 24, no program runs (a guard that fails on any call)."""

    def refuse(*args, **kwargs):
        raise AssertionError("plan_ceremony runs no command")

    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, refuse)
    monkeypatch.setattr(os, "system", refuse)
    stalls = stalls_file(tmp_path, [stall(301)])
    for command in ("planning", "daily", "review", "retro"):
        code, _, err = run(
            tmp_path, monkeypatch, capsys, command, "--stalls", stalls, pulls=retro_pulls()
        )
        assert (code, err) == (0, "")


def test_rule24_a_gh_on_path_is_never_called(tmp_path):
    """REQ-050 AC7: rule 24, a `gh` stub on PATH that records every call stays empty."""
    stub = tmp_path / "bin"
    stub.mkdir()
    calls = tmp_path / "calls.txt"
    (stub / "gh").write_text(f'#!/bin/sh\necho "$@" >> "{calls}"\nexit 1\n', encoding="utf-8")
    (stub / "gh").chmod(0o755)
    path = write(tmp_path, pulls=retro_pulls())
    env = dict(os.environ, PATH=f"{stub}:{os.environ.get('PATH', '')}")
    for command in ("planning", "daily", "review", "retro"):
        done = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(SCRIPT), command, "--facts", str(path)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, done.stderr
    assert not calls.exists()
    assert not (tmp_path / "docs" / "plan" / "iterations").exists()  # nothing written


# --- rule 26: the limits line ---------------------------------------------------------------------


def test_rule26_planning_ends_with_the_limits_line(tmp_path, monkeypatch, capsys):
    """REQ-050 AC8: rule 26 for `plan_ceremony.py planning`."""
    code, out, _ = run(tmp_path, monkeypatch, capsys, "planning", baseline=None)
    assert code == 0 and out.splitlines()[-1] == LIMITS


def test_rule26_the_guide_names_the_four_commands():
    """REQ-050 AC8: rule 26, the guide's `Sprints and ceremonies` section."""
    root = Path(__file__).resolve().parents[2]
    text = (root / "docs" / "guides" / "planning.md").read_text(encoding="utf-8")
    section = text.split("## Sprints and ceremonies", 1)[1].split("\n## ", 1)[0]
    for command in ("planning", "daily", "review", "retro"):
        assert f"plan_ceremony.py {command}" in section
    assert LIMITS in section
    assert "uncalibrated" in section and "never contacts the customer" in section
