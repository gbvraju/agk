"""Tests of the full suite's budget and the medians in the weekly report (brief #878 answers 4, 5).

Saved API responses and saved job logs written to `tmp_path`; no network, no model, no `gh`.
"""

from __future__ import annotations

import json

from test_metrics_pr_tests import ALWAYS, SELECTED, UNMAPPED, log, ran_job, report, saved
from test_metrics_testing import Api, line, run

MERGE = "c" * 40
MODE = "tests: mode full (event push)"
TIMED = log(
    MODE,
    "4 workers [9000 items]",
    "=== slowest durations ===",
    "30.00s call     tests/kit/test_slow.py::test_a",
    "10.00s setup    tests/kit/test_slow.py::test_a",
    "20.00s call     tests/kit/test_mid.py::test_b",
    "=== short test summary info ===",
)
THOROUGH = log("tests: mode full (profile thorough)")


def pushed(api: Api, runs: list[tuple[int, str, int]]) -> None:
    """Each run on the merge commit: its id, its job log and the seconds of its test step."""
    api.edit(121, merge_commit_sha=MERGE)
    api.runs(MERGE, [run(rid, "governance full", event="push") for rid, _, _ in runs])
    for rid, text, seconds in runs:
        api.jobs(rid, [ran_job(rid * 10, seconds)])
        (api.path / f"job-log-{rid * 10}.json").write_text(json.dumps(text))


def full_line(repo, api: Api) -> str:
    return line(report(repo, api), "full suite:")


def test_the_median_against_the_budget(repo, tmp_path):
    """REQ-051: brief #878 answer 4 (the median of the default branch's runs, the budget)."""
    api = Api(tmp_path)
    pushed(api, [(1, TIMED, 100), (2, log(MODE), 200), (3, log(MODE), 400)])
    assert full_line(repo, api).startswith("full suite: median 200s; budget_seconds 300; 3 runs;")


def test_over_budget_says_what_to_do_and_never_fails(repo, tmp_path):
    """REQ-051: brief #878 answer 4 (a report, not a failure; split or speed up, never remove)."""
    api = Api(tmp_path)
    pushed(api, [(1, log(MODE), 500)])
    got = full_line(repo, api)  # `report` asserts exit 0
    assert "over budget: one brief to split or speed up the slowest files" in got
    assert "never to remove a test" in got


def test_inside_the_budget_asks_nothing(repo, tmp_path):
    """REQ-051: brief #878 answer 4."""
    api = Api(tmp_path)
    pushed(api, [(1, log(MODE), 300)])
    assert "over budget" not in full_line(repo, api)


def test_the_budget_is_read_from_the_setting(repo, tmp_path):
    """REQ-051: brief #878 answer 4 (`[testing] budget_seconds`)."""
    repo.write("agk.toml", "[testing]\nbudget_seconds = 60\n")
    api = Api(tmp_path)
    pushed(api, [(1, log(MODE), 61)])
    got = full_line(repo, api)
    assert "budget_seconds 60;" in got and "over budget" in got


def test_the_slowest_files_and_the_balance_come_from_the_log(repo, tmp_path):
    """REQ-051: brief #878 answer 4 (slowest files; the workers' share of the step's time)."""
    api = Api(tmp_path)
    pushed(api, [(1, TIMED, 30)])
    got = full_line(repo, api)
    assert "slowest: tests/kit/test_slow.py 40s, tests/kit/test_mid.py 20s;" in got
    assert "workers: 4, balance 50%;" in got  # 60 s of tests over 4 x 30 s


def test_at_most_ten_files_are_named(repo, tmp_path):
    """REQ-051: brief #878 answer 4 (the slowest 10)."""
    rows = [f"{50 - i}.00s call     tests/kit/test_{i}.py::test_a" for i in range(12)]
    text = log(MODE, "=== slowest durations ===", *rows, "=== end ===")
    api = Api(tmp_path)
    pushed(api, [(1, text, 30)])
    named = full_line(repo, api).split("slowest: ", 1)[1].split(";", 1)[0]
    assert len(named.split(", ")) == 10 and "test_11.py" not in named


def test_a_number_that_cannot_be_read_is_unknown(repo, tmp_path):
    """REQ-051: SPEC-0007 rule 10 (no durations printed: `unknown`, never 0)."""
    api = Api(tmp_path)
    pushed(api, [(1, log(MODE), 30)])
    got = full_line(repo, api)
    assert "slowest: unknown;" in got and "workers: unknown" in got


def test_no_run_of_the_default_branch_is_unknown(repo, tmp_path):
    """REQ-051: SPEC-0007 rule 10."""
    assert full_line(repo, Api(tmp_path)).startswith(
        "full suite: median unknown; budget_seconds 300; 0 runs;"
    )


def test_a_pull_request_run_is_not_a_full_suite_run(repo, tmp_path):
    """REQ-051: brief #878 answer 4 (the default branch's runs; a pull request has its own line)."""
    api = Api(tmp_path)
    saved(api, [(1, ALWAYS, 900)])
    assert "; 0 runs;" in full_line(repo, api)


def test_the_median_minutes_of_each_mode(repo, tmp_path):
    """REQ-051: brief #878 answer 5 (the median selected and full test minutes)."""
    api = Api(tmp_path)
    saved(api, [(1, SELECTED, 60), (2, SELECTED, 180), (3, ALWAYS, 600)])
    assert line(report(repo, api), "pr tests median:") == (
        "pr tests median: selected 2.0 minutes (2 runs); full 10.0 minutes (1 runs)"
    )


def test_a_mode_with_no_run_is_unknown(repo, tmp_path):
    """REQ-051: SPEC-0007 rule 10 (no run of a mode has no median)."""
    api = Api(tmp_path)
    saved(api, [(1, SELECTED, 60)])
    assert line(report(repo, api), "pr tests median:") == (
        "pr tests median: selected 1.0 minutes (1 runs); full unknown (0 runs)"
    )


def test_the_reason_of_each_full_run(repo, tmp_path):
    """REQ-051: brief #878 answer 5 (`always_full <entry>`, `unmapped`, `thorough`)."""
    api = Api(tmp_path)
    saved(api, [(1, ALWAYS, 60), (2, ALWAYS, 60), (3, UNMAPPED, 60), (4, THOROUGH, 60)])
    assert line(report(repo, api), "pr tests full reasons:") == (
        "pr tests full reasons: always_full .github/workflows/** (2), thorough (1), unmapped (1)"
    )


def test_no_full_run_has_no_reason(repo, tmp_path):
    """REQ-051: brief #878 answer 5."""
    api = Api(tmp_path)
    saved(api, [(1, SELECTED, 60)])
    assert line(report(repo, api), "pr tests full reasons:") == "pr tests full reasons: none"
