"""Tests of the test time, backstop escapes and suites over budget in scripts/agk/metrics.py.

Brief 427, ADR-0232. Saved API responses written to `tmp_path`; no network, no model, no `gh`."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import metrics as metrics_mod

FIXTURES = Path(__file__).parent / "fixtures" / "metrics"
TODAY = "2026-10-14"  # the window is 2026-10-05 to 2026-10-12
HEAD = "0079000000000000000000000000000000000000"
MERGE = "0079ffffffffffffffffffffffffffffffffffff"
HEAD2 = "0080000000000000000000000000000000000000"
MERGE2 = "0080ffffffffffffffffffffffffffffffffffff"
NEW = ("project_test_seconds", "proof_seconds")
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


def line(body: str, prefix: str) -> str:
    found = [ln for ln in body.splitlines() if ln.startswith(prefix)]
    assert len(found) == 1, body
    return found[0]


def step(name: str, start: str, end: str | None, conclusion: str = "success") -> dict:
    return {
        "name": name,
        "status": "completed" if end else "in_progress",
        "conclusion": conclusion if end else None,
        "started_at": f"2026-10-06T{start}Z" if start else None,
        "completed_at": f"2026-10-06T{end}Z" if end else None,
    }


def job(name: str, start: str, end: str | None, *steps: dict, conclusion: str = "success") -> dict:
    return {
        "name": name,
        "started_at": f"2026-10-06T{start}Z",
        "completed_at": f"2026-10-06T{end}Z" if end else None,
        "conclusion": conclusion if end else None,
        "labels": ["ubuntu-latest"],
        "steps": list(steps),
    }


def governance_job(seconds: int | None, conclusion: str = "success") -> dict:
    """A governance job whose `Project tests` step took `seconds` (None: the step was skipped)."""
    if seconds is None:
        tests = step("Project tests", "09:01:00", "09:01:00", conclusion="skipped")
    else:
        m, s = divmod(60 + seconds, 60)
        h, m = divmod(9 * 60 + m, 60)
        tests = step("Project tests", "09:01:00", f"{h:02d}:{m:02d}:{s:02d}", conclusion)
    return job(
        "governance",
        "09:00:30",
        "09:30:00",
        step("check_adrs", "09:00:40", "09:00:50"),
        tests,
        conclusion=conclusion,
    )


def proof_job(outcome: str | None, start: str = "09:00:10", end: str = "09:03:10") -> dict:
    """A proof job whose outcome step `outcome` ended success (None: the job was skipped)."""
    if outcome is None:
        return job("proof", start, start, conclusion="skipped")
    steps = [step("Run proof", start, end)]
    for name in ("proven", "not-proven (red-on-head)", "skipped"):
        won = name.split(" ")[0] == outcome
        steps.append(step(f"outcome: {name}", end, end, "success" if won else "skipped"))
    return job("proof", start, end, *steps)


def run(
    rid: int, name: str, created: str = "09:00:00", event: str = "pull_request", **more
) -> dict:
    return {
        "id": rid,
        "name": name,
        "event": event,
        "head_branch": more.pop("branch", "feature" if event == "pull_request" else "main"),
        "created_at": f"2026-10-06T{created}Z",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": more.pop("conclusion", "success"),
        **more,
    }


class Api:
    """The `files` fixture (pull request 121, one commit, merged) and saved run responses."""

    def __init__(self, tmp_path: Path) -> None:
        self.path = tmp_path / "api"
        shutil.copytree(FIXTURES / "files", self.path)
        self.edit(121, base={"sha": "b" * 40, "ref": "main"})

    def edit(self, number: int, **fields) -> None:
        file = self.path / f"pull-{number}.json"
        data = json.loads(file.read_text())
        data.update(fields)
        file.write_text(json.dumps(data))

    def second(self, merged: bool = True) -> None:
        """Pull request 122, a copy of 121 with its own head and merge commit."""
        for name in ("comments", "files"):
            shutil.copy(self.path / f"{name}-121.json", self.path / f"{name}-122.json")
        (self.path / "commits-122.json").write_text(json.dumps([{"sha": HEAD2}]))
        data = json.loads((self.path / "pull-121.json").read_text())
        data.update(number=122, head={"sha": HEAD2}, merge_commit_sha=MERGE2 if merged else None)
        if not merged:
            data.update(merged=False, merged_at=None)
        (self.path / "pull-122.json").write_text(json.dumps(data))
        pulls = json.loads((self.path / "pulls.json").read_text())
        pulls.append({**pulls[0], "number": 122, "merged_at": data["merged_at"]})
        (self.path / "pulls.json").write_text(json.dumps(pulls))
        (self.path / f"checks-{HEAD2}.json").write_text(json.dumps({"check_runs": []}))

    def runs(self, sha: str, runs: list[dict] | None) -> None:
        if runs is not None:
            data = {"total_count": len(runs), "workflow_runs": runs}
            (self.path / f"runs-{sha}.json").write_text(json.dumps(data))

    def jobs(self, rid: int, jobs: list[dict] | None) -> None:
        if jobs is not None:
            data = {"total_count": len(jobs), "jobs": jobs}
            (self.path / f"run-jobs-{rid}.json").write_text(json.dumps(data))


def report(repo, api: Api) -> str:
    authors(repo)
    proc = repo.run("metrics.py", "--api-dir", str(api.path), "--today", TODAY)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


def proven_head(api: Api, sha: str = HEAD, rid: int = 1, tests: int | None = 125) -> None:
    """The head `sha` with a governance run (Project tests `tests` seconds) and a proven proof."""
    api.runs(sha, [run(rid, "governance"), run(rid + 1, "proof")])
    api.jobs(rid, [governance_job(tests)])
    api.jobs(rid + 1, [proof_job("proven")])


# --- answer 1: the seconds of each merged pull request ----------------------------------------


def test_ac2_step_seconds_are_read_from_the_last_runs(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 1 (the Project tests step and the proof job, in seconds)."""
    api = Api(tmp_path)
    proven_head(api)
    row = table(report(repo, api))[121]
    assert row["project_test_seconds"] == "125"
    assert row["proof_seconds"] == "180"


def test_ac2_the_new_columns_come_before_the_ci_fields(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 1 (two columns of the record, before the four CI fields)."""
    api = Api(tmp_path)
    proven_head(api)
    header = next(ln for ln in report(repo, api).splitlines() if ln.startswith("|"))
    cells = [c.strip() for c in header.strip("|").split("|")]
    assert cells[-6:] == [*NEW, *CI]
    assert cells == metrics_mod.COLUMNS


def test_ac2_the_last_run_that_ran_the_step_counts(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 1 (the latest run that ran the step; a later run for an
    edited description skips it and a later skipped proof job runs nothing)."""
    api = Api(tmp_path)
    api.runs(
        HEAD,
        [
            run(1, "governance", "09:00:00"),
            run(2, "governance", "10:00:00"),
            run(3, "governance", "11:00:00"),
            run(4, "proof", "09:00:00"),
            run(5, "proof", "10:00:00"),
            run(6, "proof", "11:00:00"),
        ],
    )
    api.jobs(1, [governance_job(400)])
    api.jobs(2, [governance_job(90)])
    api.jobs(3, [governance_job(None)])  # an edited description: the step is skipped
    api.jobs(4, [proof_job("proven", "09:00:00", "09:10:00")])
    api.jobs(5, [proof_job("proven", "10:00:00", "10:01:40")])
    api.jobs(6, [proof_job(None, "11:00:00")])
    row = table(report(repo, api))[121]
    assert row["project_test_seconds"] == "90"
    assert row["proof_seconds"] == "100"


def test_ac2_a_step_that_cannot_be_read_is_unknown(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 1 and SPEC-0007 rule 10 (unknown, never 0)."""
    api = Api(tmp_path)
    api.runs(HEAD, [run(1, "governance"), run(2, "proof")])
    api.jobs(1, None)  # the governance jobs cannot be read
    api.jobs(2, [job("proof", "09:00:00", None)])
    row = table(report(repo, api))[121]
    assert row["project_test_seconds"] == "unknown"
    assert row["proof_seconds"] == "unknown"  # the job has no end time


def test_ac2_a_step_that_never_ran_or_unreadable_runs_are_unknown(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 1 (a skipped step, no proof run, no readable run list)."""
    api = Api(tmp_path)
    api.runs(HEAD, [run(1, "governance")])
    api.jobs(1, [governance_job(None)])
    row = table(report(repo, api))[121]
    assert row["project_test_seconds"] == "unknown"
    assert row["proof_seconds"] == "unknown"

    api2 = Api(tmp_path / "two")
    row = table(report(repo, api2))[121]  # no runs-<head>.json at all
    assert (row["project_test_seconds"], row["proof_seconds"]) == ("unknown", "unknown")


def test_ac2_a_closed_pull_request_has_no_seconds(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 1 (per merged pull request: a closed one shows `-`)."""
    api = Api(tmp_path)
    proven_head(api)
    api.second(merged=False)
    proven_head(api, HEAD2, rid=11)
    row = table(report(repo, api))[122]
    assert (row["project_test_seconds"], row["proof_seconds"]) == ("-", "-")


# --- answer 2: backstop escapes ----------------------------------------------------------------


def red_push(api: Api, sha: str, rid: int, conclusion: str = "failure") -> None:
    api.runs(sha, [run(rid, "governance", "12:00:00", event="push", conclusion=conclusion)])
    api.jobs(rid, [governance_job(130, "failure" if conclusion == "failure" else "success")])


def test_ac2_one_escape_and_one_red_push_that_is_not_one(repo, tmp_path):
    """REQ-012 AC2: brief 427 answers 2 and 5 (a red push after a proven merge is an escape; a
    red push whose proof was not proven is not)."""
    api = Api(tmp_path)
    proven_head(api)
    red_push(api, MERGE, 21)
    api.second()
    api.runs(HEAD2, [run(11, "governance"), run(12, "proof")])
    api.jobs(11, [governance_job(125)])
    api.jobs(12, [proof_job("not-proven")])
    red_push(api, MERGE2, 22)
    body = report(repo, api)
    assert line(body, "backstop escapes:") == (
        f"backstop escapes: 1 (#121 {MERGE}); red pushes not escapes: 1 (#122 {MERGE2}); unknown: 0"
    )


def test_ac2_a_red_push_after_failed_governance_is_not_an_escape(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 2 (the pull request's governance must have passed)."""
    api = Api(tmp_path)
    api.runs(HEAD, [run(1, "governance", conclusion="failure"), run(2, "proof")])
    api.jobs(1, [governance_job(125, "failure")])
    api.jobs(2, [proof_job("proven")])
    red_push(api, MERGE, 21)
    assert line(report(repo, api), "backstop escapes:") == (
        f"backstop escapes: 0; red pushes not escapes: 1 (#121 {MERGE}); unknown: 0"
    )


def test_ac2_a_green_push_is_no_escape(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 2 (only a failed governance run on the push counts)."""
    api = Api(tmp_path)
    proven_head(api)
    red_push(api, MERGE, 21, conclusion="success")
    assert line(report(repo, api), "backstop escapes:") == (
        "backstop escapes: 0; red pushes not escapes: 0; unknown: 0"
    )


def test_ac2_an_escape_that_cannot_be_read_is_unknown(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 2 and SPEC-0007 rule 10 (no push run read; a red push whose
    proof cannot be read)."""
    api = Api(tmp_path)
    proven_head(api)  # no runs-<merge>.json: the push run cannot be read
    api.second()
    api.runs(HEAD2, [run(11, "governance")])  # no proof run
    api.jobs(11, [governance_job(125)])
    red_push(api, MERGE2, 22)
    assert line(report(repo, api), "backstop escapes:") == (
        "backstop escapes: 0; red pushes not escapes: 0; unknown: 2 (#121, #122)"
    )


def test_ac2_a_red_run_of_another_branch_or_event_is_not_a_push(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 2 (a governance run on a push to the default branch)."""
    api = Api(tmp_path)
    proven_head(api)
    api.runs(
        MERGE,
        [
            run(21, "governance", event="push", branch="other", conclusion="failure"),
            run(22, "governance", event="push", conclusion="success"),
            run(23, "proof", event="push", conclusion="failure"),
        ],
    )
    for rid in (21, 22, 23):
        api.jobs(rid, [governance_job(130)])
    assert line(report(repo, api), "backstop escapes:") == (
        "backstop escapes: 0; red pushes not escapes: 0; unknown: 0"
    )


# --- answer 3: suites over budget --------------------------------------------------------------


def test_ac2_a_run_over_the_default_budget_is_listed(repo, tmp_path):
    """REQ-012 AC2: brief 427 answers 3 and 5 (longer than 300 seconds when unset)."""
    api = Api(tmp_path)
    api.runs(HEAD, [run(1, "governance"), run(2, "governance", "10:00:00"), run(3, "proof")])
    api.jobs(1, [governance_job(301)])
    api.jobs(2, [governance_job(300)])  # exactly the budget: not over it
    api.jobs(3, [proof_job("proven")])
    red_push(api, MERGE, 21, conclusion="success")  # 130 s
    assert line(report(repo, api), "over budget") == (
        "over budget (budget_seconds 300): 1 (#121 run 1 301s); unknown: 0"
    )


def test_ac2_the_budget_is_read_from_the_testing_table(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 3 (`[testing] budget_seconds`, the push run included)."""
    repo.write("agk.toml", "[testing]\nbudget_seconds = 120\n")
    api = Api(tmp_path)
    proven_head(api, tests=110)
    red_push(api, MERGE, 21, conclusion="success")  # 130 s
    assert line(report(repo, api), "over budget") == (
        "over budget (budget_seconds 120): 1 (#121 run 21 130s); unknown: 0"
    )


def test_ac2_runs_whose_steps_cannot_be_read_are_counted_unknown(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 3 and SPEC-0007 rule 10."""
    api = Api(tmp_path)
    api.runs(HEAD, [run(1, "governance"), run(2, "governance", "10:00:00")])
    api.jobs(1, None)
    api.jobs(2, [governance_job(None)])  # skipped: no time to compare, not unknown
    red_push(api, MERGE, 21, conclusion="success")
    assert line(report(repo, api), "over budget") == (
        "over budget (budget_seconds 300): 0; unknown: 1"
    )


def test_ac2_a_bad_budget_setting_is_named_not_guessed(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 3 and principle 8 (the setting is named)."""
    repo.write("agk.toml", "[testing]\nbudget_seconds = 0\n")
    api = Api(tmp_path)
    proven_head(api)
    got = line(report(repo, api), "over budget")
    assert got.startswith("over budget: unknown (")
    assert "setting: testing.budget_seconds" in got


def test_ac2_nothing_blocks(repo, tmp_path):
    """REQ-012 AC2: brief 427 answer 4 (an escape and a run over budget leave the exit at 0)."""
    api = Api(tmp_path)
    proven_head(api, tests=500)
    red_push(api, MERGE, 21)
    authors(repo)
    proc = repo.run("metrics.py", "--api-dir", str(api.path), "--today", TODAY)
    assert proc.returncode == 0
    assert "backstop escapes: 1" in proc.stdout
    assert "over budget (budget_seconds 300): 1 (#121 run 1 500s)" in proc.stdout
