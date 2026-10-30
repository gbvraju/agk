"""Tests of the minutes, waits and re-runs of each pull request in scripts/agk/metrics.py.

Brief 376, ADR-0209. Saved API responses written to `tmp_path`; no network, no model, no `gh`."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import metrics as metrics_mod
import minutes as minutes_mod
import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "metrics"
TODAY = "2026-10-14"  # the window is 2026-10-05 to 2026-10-12
SHA = "0079000000000000000000000000000000000000"
CI = ("minutes", "pool_minutes", "wait_minutes", "reruns")


def authors(repo) -> None:
    if not (repo.root / "config" / "reviewers.yaml").exists():
        repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [reviewer, r]\n")


def table(body: str) -> dict[int, dict[str, str]]:
    lines = [ln for ln in body.splitlines() if ln.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = {}
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows[int(cells[0])] = dict(zip(header, cells, strict=True))
    return rows


def job(start: str, end: str | None, *labels: str, conclusion: str = "success") -> dict:
    return {
        "started_at": f"2026-10-06T{start}Z",
        "completed_at": f"2026-10-06T{end}Z" if end else None,
        "conclusion": conclusion if end else None,
        "labels": list(labels or ["ubuntu-latest"]),
    }


def run(rid: int, name: str, created: str, attempt: int = 1) -> dict:
    return {
        "id": rid,
        "name": name,
        "created_at": f"2026-10-06T{created}Z",
        "run_attempt": attempt,
    }


def case(tmp_path: Path, runs: list[dict] | None, jobs: dict[int, list[dict] | None]) -> Path:
    """The `files` fixture (pull request 121, one commit) with saved run and job responses.

    `runs` None leaves the run list of the commit unreadable; a job list None leaves that list
    unreadable."""
    api = tmp_path / "api"
    shutil.copytree(FIXTURES / "files", api)
    if runs is not None:
        data = {"total_count": len(runs), "workflow_runs": runs}
        (api / f"runs-{SHA}.json").write_text(json.dumps(data))
    for rid, listed in jobs.items():
        if listed is not None:
            data = {"total_count": len(listed), "jobs": listed}
            (api / f"run-jobs-{rid}.json").write_text(json.dumps(data))
    return api


def row_of(repo, api: Path) -> dict[str, str]:
    authors(repo)
    proc = repo.run("metrics.py", "--api-dir", str(api), "--today", TODAY)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return table(proc.stdout)[121]


TWO_WORKFLOWS = (
    [run(1, "governance", "09:00:00"), run(2, "proof", "09:00:00")],
    {
        1: [job("09:00:30", "09:02:10")],  # 100 s: 2 minutes
        2: [
            job("09:01:00", "09:04:00"),  # 3 minutes
            job("09:01:30", "09:01:30", conclusion="skipped"),  # bills none
        ],
    },
)


def test_ac2_one_pull_request_with_two_workflows(repo, tmp_path):
    """REQ-012 AC2: answer 1 (minutes per workflow and in total, the wait summed per run)."""
    row = row_of(repo, case(tmp_path, *TWO_WORKFLOWS))
    assert row["minutes"] == "5 (governance 2, proof 3)"
    assert row["pool_minutes"] == "0"
    assert row["wait_minutes"] == "1.5"  # 0.5 for run 1, 1.0 for run 2 (its first job)
    assert row["reruns"] == "0"


def test_ac2_the_new_fields_close_the_table_header(repo, tmp_path):
    """REQ-012 AC2: answer 1 (the four fields are columns of the record, after the old ones)."""
    authors(repo)
    proc = repo.run(
        "metrics.py", "--api-dir", str(case(tmp_path, *TWO_WORKFLOWS)), "--today", TODAY
    )
    header = next(ln for ln in proc.stdout.splitlines() if ln.startswith("|"))
    cells = [c.strip() for c in header.strip("|").split("|")]
    assert cells[-4:] == list(CI)
    assert cells[:-4] == metrics_mod.COLUMNS[:-4]


def test_ac2_a_rerun_counts_its_run_and_bills_every_attempt(repo, tmp_path):
    """REQ-012 AC2: answer 1 (`reruns` counts runs whose attempt is above 1)."""
    runs = [run(1, "governance", "09:00:00", attempt=2), run(2, "proof", "09:00:00")]
    jobs = {
        1: [job("09:00:30", "09:02:10"), job("10:00:00", "10:01:00")],  # attempt 1 and 2
        2: [job("09:00:00", "09:00:50")],
    }
    row = row_of(repo, case(tmp_path, runs, jobs))
    assert row["reruns"] == "1"
    assert row["minutes"] == "4 (governance 3, proof 1)"
    assert row["wait_minutes"] == "0.5"  # the first job of run 1 started 30 s after its creation


def test_ac2_a_self_hosted_job_is_pool_minutes_not_billed(repo, tmp_path):
    """REQ-012 AC2: answer 1 (`pool_minutes`)."""
    runs = [run(1, "proof", "09:00:00")]
    jobs = {1: [job("09:00:06", "09:04:07", "self-hosted", "linux"), job("09:00:12", "09:01:12")]}
    row = row_of(repo, case(tmp_path, runs, jobs))
    assert row["pool_minutes"] == "5"
    assert row["minutes"] == "1 (proof 1)"
    assert row["wait_minutes"] == "0.1"


def test_ac2_runs_whose_jobs_cannot_be_read_are_unknown_never_zero(repo, tmp_path):
    """REQ-012 AC2: answer 2 and SPEC-0007 rule 10."""
    runs = [run(1, "governance", "09:00:00"), run(2, "proof", "09:00:00", attempt=3)]
    row = row_of(repo, case(tmp_path, runs, {1: [job("09:00:30", "09:02:10")], 2: None}))
    assert row["minutes"] == "unknown"
    assert row["pool_minutes"] == "unknown"
    assert row["wait_minutes"] == "unknown"
    assert row["reruns"] == "1"  # read from the run list, which answered


def test_ac2_an_unreadable_run_list_or_commit_list_is_unknown(repo, tmp_path):
    """REQ-012 AC2: answer 2."""
    row = row_of(repo, case(tmp_path, None, {}))
    assert [row[f] for f in CI] == ["unknown"] * 4
    api = case(tmp_path / "b", *TWO_WORKFLOWS)
    (api / "commits-121.json").unlink()
    row = row_of(repo, api)
    assert [row[f] for f in CI] == ["unknown"] * 4


def test_ac2_a_job_still_running_leaves_minutes_unknown(repo, tmp_path):
    """REQ-012 AC2: answer 2 (`job_minutes` gives None for a job without both times)."""
    runs = [run(1, "proof", "09:00:00")]
    row = row_of(repo, case(tmp_path, runs, {1: [job("09:00:30", None)]}))
    assert row["minutes"] == "unknown"
    assert row["pool_minutes"] == "0"
    assert row["wait_minutes"] == "0.5"


def test_ac2_no_run_is_zero_measured(repo, tmp_path):
    """REQ-012 AC2: a pull request whose head commits started no run used no minutes."""
    row = row_of(repo, case(tmp_path, [], {}))
    assert [row[f] for f in CI] == ["0", "0", "0.0", "0"]


def test_ac2_the_billing_rule_is_the_minutes_function(monkeypatch):
    """REQ-012 AC2: answer 3 (`minutes.py`'s `job_minutes`, imported, so the numbers agree)."""

    class Src:
        def get(self, name, endpoint, until=None):
            if name == f"runs-{SHA}":
                return {"total_count": 1, "workflow_runs": [run(1, "proof", "09:00:00")]}
            if name == "run-jobs-1":
                return {"jobs": [job("09:00:00", "09:00:01"), job("09:00:00", "09:00:02")]}
            return None

    monkeypatch.setattr(minutes_mod, "job_minutes", lambda j: 7)
    fields = metrics_mod.ci_fields(Src(), [SHA])
    assert fields["minutes"] == "14 (proof 7)"
    assert fields["pool_minutes"] == "0"


def test_ac2_each_run_is_counted_once_across_head_commits():
    """REQ-012 AC2: a run listed under two commits of the pull request is one run."""

    class Src:
        def get(self, name, endpoint, until=None):
            if name.startswith("runs-"):
                return {"total_count": 1, "workflow_runs": [run(1, "proof", "09:00:00", 2)]}
            if name == "run-jobs-1":
                return {"jobs": [job("09:00:30", "09:01:30")]}
            return None

    fields = metrics_mod.ci_fields(Src(), ["a" * 40, "b" * 40])
    assert fields == {
        "minutes": "1 (proof 1)",
        "pool_minutes": "0",
        "wait_minutes": "0.5",
        "reruns": "1",
    }
    assert metrics_mod.ci_fields(Src(), None) == dict.fromkeys(CI, "unknown")


@pytest.mark.parametrize(
    ("cells", "expected"),
    [
        (
            [
                ("5 (governance 2, proof 3)", "0", "1.5", "0"),
                ("2 (proof 2)", "4", "0.2", "1"),
                ("unknown", "unknown", "unknown", "2"),
            ],
            "ci totals: minutes median=3.5 largest=5 unknown=1; "
            "pool_minutes median=2 largest=4 unknown=1; "
            "wait_minutes median=0.9 largest=1.5 unknown=1; "
            "reruns median=1 largest=2 unknown=0",
        ),
        (
            [("unknown", "unknown", "unknown", "unknown")],
            "ci totals: minutes median=unknown largest=unknown unknown=1; "
            "pool_minutes median=unknown largest=unknown unknown=1; "
            "wait_minutes median=unknown largest=unknown unknown=1; "
            "reruns median=unknown largest=unknown unknown=1",
        ),
        (
            [],
            "ci totals: minutes median=- largest=- unknown=0; "
            "pool_minutes median=- largest=- unknown=0; "
            "wait_minutes median=- largest=- unknown=0; "
            "reruns median=- largest=- unknown=0",
        ),
    ],
)
def test_ac3_the_weekly_totals_show_the_median_and_the_largest(cells, expected):
    """REQ-012 AC3: answer 2 (median and largest of each; unknown stays unknown, never 0)."""
    records = [dict(zip(CI, c, strict=True)) for c in cells]
    assert metrics_mod.ci_totals(records) == expected


def test_ac3_the_weekly_body_carries_the_ci_totals_after_the_totals_line(repo, tmp_path):
    """REQ-012 AC3: answer 2."""
    authors(repo)
    proc = repo.run(
        "metrics.py", "--api-dir", str(case(tmp_path, *TWO_WORKFLOWS)), "--today", TODAY
    )
    lines = proc.stdout.splitlines()
    at = next(i for i, ln in enumerate(lines) if ln.startswith("totals: "))
    assert lines[at + 1] == (
        "ci totals: minutes median=5 largest=5 unknown=0; "
        "pool_minutes median=0 largest=0 unknown=0; "
        "wait_minutes median=1.5 largest=1.5 unknown=0; "
        "reruns median=0 largest=0 unknown=0"
    )
    assert lines[at + 2].startswith("closed in window: 1; recorded: 1; unknown cells: ")


def test_ac2_minutes_py_is_unchanged_by_the_import(repo, tmp_path):
    """REQ-012 AC2: answer 3 (both scripts still run on their own, with no import cycle)."""
    api = tmp_path / "m"
    api.mkdir()
    proc = repo.run("minutes.py", "--api-dir", str(api), "--today", TODAY)
    assert "repository cannot be read" in proc.stdout + proc.stderr
    authors(repo)
    proc = repo.run("metrics.py", "--api-dir", str(FIXTURES / "empty-week"), "--today", TODAY)
    assert proc.returncode == 0, proc.stderr
    assert "ci totals: minutes median=- largest=-" in proc.stdout
