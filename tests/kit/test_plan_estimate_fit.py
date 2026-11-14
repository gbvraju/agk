"""Tests of `plan_estimate.py --deadline D --builders N[,N...]` (brief #1220, ADR-0519; REQ-050).

REQ-050 AC4.

Before any history exists (SPEC-0043 rule 14, uncalibrated), the estimator fits a deadline by
builder count: from the brief files' `Expected:` mid points, `Depends-on` and `Touches`, a list
schedule that never runs two briefs whose `Touches` overlap and never starts a brief before its
dependencies prints, per builder count, the finish date, the buffer in working days and the briefs
of the latest milestones that would have to move. Invented plans only (example.com); no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import plan_estimate
import pytest

TODAY = "2026-11-04"  # a Wednesday: the first working day is Thursday 2026-11-05
LIMITS = (
    "Estimates are ranges from this project's own history, not promises; AGK drafts from the "
    "sources and the person owns scope."
)


def brief_file(plan: Path, milestone: str, key: str, expected="4-8 hours", touches=None, deps=(),
               size="M"):  # fmt: skip
    folder = plan / "briefs" / milestone
    folder.mkdir(parents=True, exist_ok=True)
    lines = [f"# {key} for example.com", "", f'Sentence: "{key} for example.com"', ""]
    lines += ["Advances: REQ-001", f"Touches: {', '.join(touches or [f'src/{key}/'])}"]
    lines += [f"Size: {size}"] + ([f"Expected: {expected}"] if expected else [])
    lines += [f"Milestone: {milestone}", *(f"Depends-on: {d}" for d in deps)]
    (folder / f"{key}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def setup(tmp_path, briefs, milestones=("M1 Orders", "M2 Payments", "M3 Reports"), pulls=None):
    doc = {"schema": 1, "today": TODAY, "pull_requests": pulls or [], "flow": {"briefs": []}}
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps(doc), encoding="utf-8")
    plan = tmp_path / "docs" / "plan"
    plan.mkdir(parents=True, exist_ok=True)
    text = "# Milestones\n" + "".join(f"\n### {m}\n\nTarget: 2026-12-18\n" for m in milestones)
    (plan / "milestones.md").write_text(text, encoding="utf-8")
    for args, kwargs in briefs:
        brief_file(plan, *args, **kwargs)
    return facts


def fit(tmp_path, monkeypatch, capsys, briefs, *args, **kwargs):
    monkeypatch.chdir(tmp_path)
    facts = setup(tmp_path, briefs, **kwargs)
    code = plan_estimate.main(["--facts", str(facts), *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def row(out: str, n: int) -> str:
    return next(x for x in out.splitlines() if x.startswith(f"builders {n}: "))


def b(milestone, key, **kwargs):
    return ((milestone, key), kwargs)


THREE = [b("M1", "a"), b("M1", "b"), b("M1", "c")]  # 6 h each at the mid point of 4-8 hours
FAR = "2026-12-31"


# --- answer 1: the schedule ---------------------------------------------------------------------


def test_one_lane_finishes_at_the_summed_hours(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: 3 briefs of 6 h and no review, 6 h a day: 3 working days from Thursday."""
    args = ["--deadline", FAR, "--builders", "1", "--review-hours", "0"]
    code, out, err = fit(tmp_path, monkeypatch, capsys, THREE, *args)
    assert code == 0, err
    assert row(out, 1).startswith("builders 1: finish 2026-11-09, buffer ")


def test_the_review_hours_and_hours_per_day_are_counted(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: (6 + 2) * 3 = 24 h at 8 h a day is 3 working days."""
    args = ["--deadline", FAR, "--builders", "1", "--review-hours", "2", "--hours-per-day", "8"]
    _, out, _ = fit(tmp_path, monkeypatch, capsys, THREE, *args)
    assert row(out, 1).startswith("builders 1: finish 2026-11-09,")


def test_independent_briefs_run_side_by_side(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: three builders, three disjoint briefs: one working day."""
    args = ["--deadline", FAR, "--builders", "3", "--review-hours", "0"]
    _, out, _ = fit(tmp_path, monkeypatch, capsys, THREE, *args)
    assert row(out, 3).startswith("builders 3: finish 2026-11-05,")


def test_dependencies_serialise(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: c depends on b, b on a: three builders still take three working days."""
    chain = [b("M1", "a"), b("M1", "b", deps=["a"]), b("M1", "c", deps=["b"])]
    args = ["--deadline", FAR, "--builders", "3", "--review-hours", "0"]
    _, out, _ = fit(tmp_path, monkeypatch, capsys, chain, *args)
    assert row(out, 3).startswith("builders 3: finish 2026-11-09,")


def test_overlapping_touches_serialise_and_shared_paths_do_not(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: `src/app/` and `src/app/x.py` overlap; `changelog.d/*` is shared."""
    briefs = [
        b("M1", "a", touches=["src/app/", "changelog.d/*"]),
        b("M1", "b", touches=["src/app/x.py", "changelog.d/*"]),
        b("M1", "c", touches=["src/other.py", "changelog.d/*"]),
    ]
    args = ["--deadline", FAR, "--builders", "3", "--review-hours", "0"]
    _, out, _ = fit(tmp_path, monkeypatch, capsys, briefs, *args)
    assert row(out, 3).startswith("builders 3: finish 2026-11-06,")


def test_more_builders_never_finish_later(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: an invented plan with dependencies, overlaps and uneven sizes."""
    briefs = [
        b("M1", "a", expected="10-14 hours"),
        b("M1", "b", expected="2-4 hours", touches=["src/a/"]),
        b("M1", "c", expected="20-30 hours", deps=["a"]),
        b("M2", "d", expected="6-10 hours", deps=["b"]),
        b("M2", "e", expected="1-3 hours", touches=["src/a/b.py"]),
        b("M2", "f", expected="8-12 hours"),
        b("M3", "g", expected="4-6 hours", deps=["c", "f"]),
        b("M3", "h", expected="12-18 hours"),
        b("M3", "i", expected="3-5 hours", deps=["e"]),
    ]
    args = ["--deadline", FAR, "--builders", "1,2,3,4,5,6,7,8"]
    _, out, _ = fit(tmp_path, monkeypatch, capsys, briefs, *args)
    finishes = [row(out, n).split("finish ")[1][:10] for n in range(1, 9)]
    assert finishes == sorted(finishes, reverse=True)
    assert finishes[0] > finishes[-1]


def test_a_deadline_miss_lists_the_briefs_of_the_latest_milestones(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: one builder, 5 briefs of 6 h, a deadline of 3 working days: M3 and one of
    M2 move, latest first, printed in plan order."""
    briefs = [b("M1", "a"), b("M1", "b"), b("M2", "c"), b("M2", "d"), b("M3", "e")]
    args = ["--deadline", "2026-11-09", "--builders", "1,2", "--review-hours", "0"]
    _, out, _ = fit(tmp_path, monkeypatch, capsys, briefs, *args)
    assert row(out, 1) == (
        "builders 1: finish 2026-11-11, buffer -2 working days; to meet the deadline move "
        "M2/d, M3/e"
    )
    assert row(out, 2) == "builders 2: finish 2026-11-09, buffer 0 working days; meets the deadline"


def test_a_moved_brief_takes_its_dependents_with_it(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: moving M2/c also moves M1/z, an earlier brief that depends on it."""
    briefs = [b("M1", "a"), b("M1", "z", expected="0-0 hours", deps=["c"]), b("M2", "c")]
    args = ["--deadline", "2026-11-05", "--builders", "1", "--review-hours", "0"]
    _, out, _ = fit(tmp_path, monkeypatch, capsys, briefs, *args)
    assert row(out, 1).endswith("; to meet the deadline move M1/z, M2/c")


# --- answer 2: the output -----------------------------------------------------------------------


def test_the_output_starts_internal_estimate_names_assumptions_and_ends_with_limits(
    tmp_path, monkeypatch, capsys
):
    """REQ-050 AC4: one row per builder count, in ascending order."""
    briefs = THREE + [b("M2", "d", expected=None, size="L")]
    code, out, _ = fit(tmp_path, monkeypatch, capsys, briefs, "--deadline", FAR, "--builders",
                       "8,4,6")  # fmt: skip
    lines = out.splitlines()
    assert code == 0
    assert lines[0] == "internal estimate: deadline 2026-12-31 for builders 4, 6, 8 from 2026-11-04"
    assumptions = [x for x in lines if x.startswith("assumptions:")]
    assert len(assumptions) == 1 and lines[1] == assumptions[0]
    for words in ("mid point", "0.25 h of review", "6 h a working day", "Monday to Friday",
                  "Depends-on", "Touches", "1 briefs without an estimate count 0 h"):  # fmt: skip
        assert words in assumptions[0]
    assert [x.split(":")[0] for x in lines[2:5]] == ["builders 4", "builders 6", "builders 8"]
    assert lines[-1] == LIMITS and len(lines) == 6


def test_the_owner_default_is_used_and_named(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: `[plan] default_hours` gives a brief without `Expected:` its range."""
    (tmp_path / "agk.toml").write_text('[plan]\ndefault_hours = { L = "10-14" }\n', "utf-8")
    briefs = [b("M1", "a", expected=None, size="L")]
    args = ["--deadline", FAR, "--builders", "1", "--review-hours", "0"]
    _, out, _ = fit(tmp_path, monkeypatch, capsys, briefs, *args)
    assert row(out, 1).startswith("builders 1: finish 2026-11-06,")  # 12 h
    assert "1 owner default" in out


def test_the_same_inputs_print_the_same_bytes_and_write_nothing(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: deterministic, and nothing is written into the tree."""
    args = ["--deadline", "2026-11-06", "--builders", "1,2"]
    first = fit(tmp_path, monkeypatch, capsys, THREE, *args)
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    code = plan_estimate.main(["--facts", str(tmp_path / "facts.json"), *args])
    second = capsys.readouterr()
    assert code == 0 and first[1] == second.out
    assert sorted(str(p) for p in tmp_path.rglob("*")) == before


# --- refusals -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "args, option",
    [
        (["--deadline", FAR], "--builders"),
        (["--builders", "4"], "--deadline"),
        (["--deadline", "2026-13-01", "--builders", "4"], "--deadline"),
        (["--deadline", FAR, "--builders", "0"], "--builders"),
        (["--deadline", FAR, "--builders", "4,x"], "--builders"),
        (["--deadline", FAR, "--builders", "4", "--hours-per-day", "0"], "--hours-per-day"),
        (["--deadline", FAR, "--builders", "4", "--hours-per-day", "25"], "--hours-per-day"),
        (["--deadline", FAR, "--builders", "4", "--review-hours", "-1"], "--review-hours"),
        (["--hours-per-day", "6"], "--deadline"),
        (["--deadline", FAR, "--builders", "4", "--with", "SC-1"], "--with"),
    ],
)
def test_a_bad_fit_option_exits_2_naming_it(tmp_path, monkeypatch, capsys, args, option):
    """REQ-050 AC4: the refusal names the option, never its value."""
    code, out, err = fit(tmp_path, monkeypatch, capsys, THREE, *args)
    assert code == 2 and option in err and out == ""


def test_a_dependency_cycle_exits_2(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: briefs that wait for each other can never start."""
    briefs = [b("M1", "a", deps=["b"]), b("M1", "b", deps=["a"])]
    code, out, err = fit(
        tmp_path, monkeypatch, capsys, briefs, "--deadline", FAR, "--builders", "2"
    )
    assert code == 2 and "--plan" in err and out == ""


def test_a_calibrated_history_is_refused(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: the fit is the uncalibrated path only (rule 14)."""
    pulls, closed = [], []
    for i in range(12):
        merged = f"2026-10-{10 + i:02d}T12:00:00Z"
        pulls.append({"number": 100 + i, "state": "merged", "merged_at": merged,
                      "estimated_size": "M", "actual_hours": "6.0", "flow": {}})  # fmt: skip
    for i, day in enumerate(["2026-10-13", "2026-10-20", "2026-10-27", "2026-11-03"]):
        closed.append({"number": 50 + i, "state": "closed", "closed_at": f"{day}T10:00:00Z",
                       "state_reason": "completed", "milestone": "M0"})  # fmt: skip
    monkeypatch.chdir(tmp_path)
    facts = setup(tmp_path, THREE, pulls=pulls)
    doc = json.loads(facts.read_text(encoding="utf-8"))
    doc["flow"]["briefs"] = closed
    facts.write_text(json.dumps(doc), encoding="utf-8")
    code = plan_estimate.main(["--facts", str(facts), "--deadline", FAR, "--builders", "4"])
    err = capsys.readouterr().err
    assert code == 2 and "--deadline" in err


def test_an_unknown_dependency_is_taken_as_done_and_named(tmp_path, monkeypatch, capsys):
    """REQ-050 AC4: a `Depends-on: #12` outside the plan's files does not hold a brief back."""
    briefs = [b("M1", "a", deps=["#12"])]
    args = ["--deadline", FAR, "--builders", "1", "--review-hours", "0"]
    _, out, _ = fit(tmp_path, monkeypatch, capsys, briefs, *args)
    assert row(out, 1).startswith("builders 1: finish 2026-11-05,")
    assert "1 Depends-on outside the plan's brief files taken as done" in out
