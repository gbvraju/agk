"""Tests of the pull request test lines of scripts/agk/metrics.py (brief #773 answer 4, ADR-0359).

Saved API responses and saved job logs written to `tmp_path`; no network, no model, no `gh`.
"""

from __future__ import annotations

import json

from test_metrics_testing import HEAD, Api, authors, line, run, step


def log(*lines: str) -> str:
    return "".join(f"2026-10-06T09:01:{i:02d}.0000000Z {x}\n" for i, x in enumerate(lines))


def ran_job(
    jid: int, seconds: int = 120, name: str = "Tests of the checks", conclusion: str = "success"
) -> dict:
    m, s = divmod(seconds, 60)
    return {
        "id": jid,
        "name": "governance",
        "started_at": "2026-10-06T09:00:30Z",
        "completed_at": "2026-10-06T09:30:00Z",
        "conclusion": "success",
        "steps": [step(name, "09:00:00", f"09:{m:02d}:{s:02d}", conclusion)],
    }


def saved(
    api: Api, runs: list[tuple[int, str, int]], sha: str = HEAD, name: str = "Tests of the checks"
) -> None:
    """Each run: its id, its job log and the seconds of its test step."""
    api.runs(
        sha, [run(rid, "governance full", f"09:0{i}:00") for i, (rid, _, _) in enumerate(runs)]
    )
    for rid, text, seconds in runs:
        api.jobs(rid, [ran_job(rid * 10, seconds, name)])
        (api.path / f"job-log-{rid * 10}.json").write_text(json.dumps(text))


def report(repo, api: Api) -> str:
    authors(repo)
    proc = repo.run("metrics.py", "--api-dir", str(api.path), "--today", "2026-10-14")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


SELECTED = log("tests: mode selected, 3 test files (event pull_request)")
ALWAYS = log(
    "regression: full (always_full .github/workflows/** matches .github/workflows/x.yml)",
    "tests: mode full (always_full .github/workflows/** matches .github/workflows/x.yml)",
)
UNMAPPED = log(
    "regression: full (profile balanced: 2 unmapped files)",
    "unmapped: kit/new.json -> 0 tests that name it",
    "unmapped (no [testing] map entry covers it): app/stale.py",
    "unmapped: data/named.json -> 2 tests that name it",
    "tests: unmapped: kit/new.json -> 0 tests that name it",
    "tests: mode full (profile balanced: 2 unmapped files)",
)
THOROUGH = log("tests: mode full (profile thorough)")
OTHER = log("tests: mode full (event push)")


def test_the_share_the_minutes_and_each_reason(repo, tmp_path):
    """REQ-051: brief #773 answer 4 (the share, the minutes, the reason of each full run)."""
    api = Api(tmp_path)
    saved(
        api,
        [
            (1, SELECTED, 60),
            (2, ALWAYS, 240),
            (3, UNMAPPED, 300),
            (4, THOROUGH, 60),
            (5, OTHER, 60),
        ],
    )
    assert line(report(repo, api), "pr tests:") == (
        "pr tests: 5 runs; selected 1 of 5 (20%); test step 12.0 minutes; "
        "full: always_full 1, unmapped 1, thorough 1, other 1; unknown: 0"
    )


def test_the_paths_that_most_often_made_a_run_full(repo, tmp_path):
    """REQ-051: brief #773 answer 4 (the report names the paths, most often first)."""
    api = Api(tmp_path)
    saved(api, [(1, UNMAPPED, 60), (2, ALWAYS, 60), (3, UNMAPPED, 60)])
    assert line(report(repo, api), "pr tests full most often:") == (
        "pr tests full most often: app/stale.py (2), kit/new.json (2), .github/workflows/x.yml (1)"
    )


def test_a_project_run_is_read_from_its_own_lines(repo, tmp_path):
    """REQ-051: brief #773 answer 4 (the `Project tests` step and its `project tests:` lines)."""
    api = Api(tmp_path)
    picked = log(
        "project tests: pr_tests selected, event pull_request", "project tests: will run app in ."
    )
    full = log(
        "project tests: pr_tests selected, event pull_request",
        "project tests: full (profile thorough)",
    )
    saved(api, [(1, picked, 60), (2, full, 60)], name="Project tests")
    assert line(report(repo, api), "pr tests:").startswith(
        "pr tests: 2 runs; selected 1 of 2 (50%);"
    )


def test_a_run_of_a_push_is_not_counted(repo, tmp_path):
    """REQ-051: brief #773 answer 4 (pull request runs only)."""
    api = Api(tmp_path)
    api.runs(HEAD, [run(1, "governance full", event="push")])
    api.jobs(1, [ran_job(10)])
    assert line(report(repo, api), "pr tests:").startswith("pr tests: 0 runs; selected 0 of 0 (-);")


def test_a_skipped_step_is_not_a_run(repo, tmp_path):
    """REQ-051: brief #773 answer 4 (a step that did not run has no mode)."""
    api = Api(tmp_path)
    api.runs(HEAD, [run(1, "governance full")])
    api.jobs(1, [ran_job(10, conclusion="skipped")])
    assert line(report(repo, api), "pr tests:").startswith("pr tests: 0 runs;")


def test_a_log_that_cannot_be_read_is_unknown(repo, tmp_path):
    """REQ-051: SPEC-0007 rule 10 (a missing input is `unknown`, never a mode)."""
    api = Api(tmp_path)
    api.runs(HEAD, [run(1, "governance full")])
    api.jobs(1, [ran_job(10)])
    assert line(report(repo, api), "pr tests:").endswith("unknown: 1")


def test_a_log_with_no_mode_line_is_unknown(repo, tmp_path):
    """REQ-051: SPEC-0007 rule 10 (a log that states no mode is `unknown`, never a mode)."""
    api = Api(tmp_path)
    saved(api, [(1, log("nothing about tests"), 60)])
    assert line(report(repo, api), "pr tests:").endswith("unknown: 1")


def test_no_full_run_names_no_path(repo, tmp_path):
    """REQ-051: brief #773 answer 4 (the line is present and says none)."""
    api = Api(tmp_path)
    saved(api, [(1, SELECTED, 60)])
    assert line(report(repo, api), "pr tests full most often:") == "pr tests full most often: none"
