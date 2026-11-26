"""Tests of the reads behind the weekly `pr tests:` lines (brief #2012, ADR-0833).

One job log per pull request, the `share` full kind, the class of a read that failed and the
hourly limit. Saved API responses written to `tmp_path`; no network, no model, no `gh`.
"""

from __future__ import annotations

import json
from pathlib import Path

import metrics as metrics_mod
import pytest
from test_metrics_pr_tests import SELECTED, log, ran_job, report
from test_metrics_testing import Api, line, run

SHARE = log("tests: mode full (selection 511 of 647 files)")
PR_FULL = log("tests: mode full (pr_tests full)")
RATE = {"message": "API rate limit exceeded for installation.", "status": "403"}
EXPIRED = {"message": "Not Found", "status": "404"}


def sha(number: int, head: int) -> str:
    return f"{number:04d}{head:036d}"


def pull(api: Api, number: int, merged_at: str = "2026-10-07T09:00:00Z") -> None:
    """Pull request NUMBER, a copy of 121 with two heads of its own (the second is the last)."""
    base = json.loads((api.path / "pull-121.json").read_text())
    heads = [sha(number, 1), sha(number, 2)]
    if number != 121:
        for name in ("comments", "files"):
            src = api.path / f"{name}-121.json"
            (api.path / f"{name}-{number}.json").write_text(src.read_text())
        pulls = json.loads((api.path / "pulls.json").read_text())
        pulls.append({**pulls[0], "number": number, "merged_at": merged_at, "closed_at": merged_at})
        (api.path / "pulls.json").write_text(json.dumps(pulls))
    base.update(number=number, head={"sha": heads[-1]}, merged_at=merged_at, closed_at=merged_at)
    (api.path / f"pull-{number}.json").write_text(json.dumps(base))
    (api.path / f"commits-{number}.json").write_text(json.dumps([{"sha": h} for h in heads]))
    for h in heads:
        (api.path / f"checks-{h}.json").write_text(json.dumps({"check_runs": []}))


def full_head(api: Api, head: str, rid: int, text: str | dict | None, seconds: int = 60) -> None:
    """HEAD with an edited run (its step skipped) and, after it, a full run whose log is TEXT."""
    api.runs(head, [run(rid, "governance edited", "09:00:00"), run(rid + 1, "governance full")])
    api.jobs(rid, [ran_job(rid * 10, conclusion="skipped")])
    api.jobs(rid + 1, [ran_job((rid + 1) * 10, seconds)])
    if text is not None:
        (api.path / f"job-log-{(rid + 1) * 10}.json").write_text(json.dumps(text))


def week(tmp_path: Path, logs: dict[int, str | dict | None]) -> Api:
    """A week of pull requests: each with two heads, each head an edited and a full run."""
    api = Api(tmp_path)
    for i, (number, text) in enumerate(sorted(logs.items())):
        pull(api, number, f"2026-10-0{7 + i % 3}T09:0{i}:00Z")
        full_head(api, sha(number, 1), number * 100, SELECTED)
        full_head(api, sha(number, 2), number * 100 + 10, text)
    return api


class Counted(metrics_mod.ApiDir):
    """The recorded answers, with every name read kept in order."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.names: list[str] = []

    def get(self, name: str, endpoint: str, until=None):
        self.names.append(name)
        return super().get(name, endpoint, until)


def section(repo, api: Api) -> tuple[tuple[str, ...], list[str]]:
    src = Counted(api.path)
    details = [
        json.loads(f.read_text())
        for f in sorted(api.path.glob("pull-*.json"), key=lambda f: int(f.stem[5:]))
    ]
    lines = metrics_mod.pr_tests_lines(metrics_mod.Context(src, repo.root, []), details)
    return lines, src.names


def test_one_log_per_pull_request(repo, tmp_path):
    """REQ-062: brief #2012 answer 1 (the last head's latest full run, one job log each)."""
    api = week(tmp_path, {121: SELECTED, 122: SELECTED, 123: PR_FULL})
    lines, names = section(repo, api)
    logs = [n for n in names if n.startswith("job-log-")]
    assert logs == ["job-log-121110", "job-log-122110", "job-log-123110"]
    assert not [n for n in names if n.startswith("run-jobs-") and n.endswith("0")]  # edited
    assert not [n for n in names if n.startswith("runs-") and n.endswith("1")]  # earlier heads
    assert lines[0] == (
        "pr tests: 3 pull requests; selected 2 of 3 (67%); test step 3.0 minutes; "
        "full: always_full 0, unmapped 0, share 0, thorough 0, other 1; unknown: 0"
    )


def test_the_weekly_issue_counts_pull_requests(repo, tmp_path):
    """REQ-062: brief #2012 answer 1 (the line says its counts are per pull request)."""
    api = week(tmp_path, {121: SELECTED, 122: SHARE, 123: SELECTED})
    body = report(repo, api)
    assert line(body, "pr tests:").startswith("pr tests: 3 pull requests; selected 2 of 3 (67%);")
    assert line(body, "pr tests median:") == (
        "pr tests median: selected 1.0 minutes (2 pull requests); "
        "full 1.0 minutes (1 pull requests)"
    )


def test_a_full_run_for_the_share_is_its_own_kind(repo, tmp_path):
    """REQ-062: brief #2012 answer 2 (`selection <n> of <m> files` is `share`)."""
    assert metrics_mod.full_kind("selection 511 of 647 files") == "share"
    assert metrics_mod.FULL_KINDS == ("always_full", "unmapped", "share", "thorough", "other")
    api = week(tmp_path, {121: SHARE})
    lines, _ = section(repo, api)
    assert "share 1," in lines[0]
    assert lines[3] == "pr tests full reasons: share (1)"


def test_a_rate_limited_read_names_its_class(repo, tmp_path):
    """REQ-062: brief #2012 answer 3 (a recorded 403 rate limit is `rate-limited`)."""
    api = week(tmp_path, {121: RATE, 122: SELECTED})
    lines, _ = section(repo, api)
    assert lines[0].endswith("unknown: 1 (rate-limited 1)")


def test_an_expired_log_is_refused(repo, tmp_path):
    """REQ-062: brief #2012 answer 6 (a log that has expired: `unknown (refused 1)`)."""
    api = week(tmp_path, {121: EXPIRED})
    lines, _ = section(repo, api)
    assert lines[0].endswith("unknown: 1 (refused 1)")


def test_a_live_failure_keeps_its_class(monkeypatch):
    """REQ-062: brief #2012 answer 3 (`Gh.raw` keeps the status class of a failed call)."""

    class Proc:
        def __init__(self, code: int, out: str, err: str) -> None:
            self.returncode, self.stdout, self.stderr = code, out, err

    answers = {
        "a": Proc(1, json.dumps(RATE), "gh: API rate limit exceeded (HTTP 403)"),
        "b": Proc(1, '{"message":"Too Many Requests"}', "gh: Too Many Requests (HTTP 429)"),
        "c": Proc(1, json.dumps(EXPIRED), "gh: Not Found (HTTP 404)"),
        "d": Proc(1, "", "error connecting to api.github.com"),
        "e": Proc(0, "[]", ""),
    }
    monkeypatch.setattr(metrics_mod.subprocess, "run", lambda args, **_: answers[args[-1]])
    gh = metrics_mod.Gh("example/repo")
    for name in "abcde":
        assert (gh.get(name, name) is None) == (name != "e")
    assert [gh.why(n) for n in "abcde"] == ["rate-limited", "refused", "refused", "failed", None]


def test_the_hourly_limit_reads_the_newest_that_fit(repo, tmp_path):
    """REQ-062: brief #2012 answer 3 (`remaining` below the need reads the newest that fit)."""
    api = week(tmp_path, {121: SELECTED, 122: SELECTED, 123: SELECTED})
    (api.path / "rate_limit.json").write_text(json.dumps({"resources": {"core": {"remaining": 9}}}))
    lines, names = section(repo, api)
    assert [n for n in names if n.startswith("job-log-")] == ["job-log-122110", "job-log-123110"]
    assert lines[0].startswith("pr tests: 2 pull requests;")
    assert lines[-1] == "pr tests: 2 of 3 pull requests read (hourly limit)"
    body = report(repo, api)
    assert "pr tests: 2 of 3 pull requests read (hourly limit)" in body.splitlines()


def test_no_rate_limit_answer_reads_as_unlimited(repo, tmp_path):
    """REQ-062: brief #2012 answer 5 (`--api-dir` without `rate_limit.json` is unlimited)."""
    api = week(tmp_path, {121: SELECTED, 122: SELECTED})
    lines, _ = section(repo, api)
    assert len(lines) == 4 and lines[0].startswith("pr tests: 2 pull requests;")


def test_an_earlier_head_is_read_when_the_last_ran_no_tests(repo, tmp_path):
    """REQ-062: brief #2012 answer 6 (no full run on the last head: the latest earlier one)."""
    api = week(tmp_path, {121: SELECTED})
    api.runs(sha(121, 2), [run(1, "governance edited")])
    api.jobs(1, [ran_job(10, conclusion="skipped")])
    lines, names = section(repo, api)
    assert [n for n in names if n.startswith("job-log-")] == ["job-log-121010"]
    assert lines[0].startswith("pr tests: 1 pull requests; selected 1 of 1 (100%);")


def test_an_empty_week_has_no_unknown(repo, tmp_path):
    """REQ-062: brief #2012 answer 6 (no merged pull request: `0 pull requests`)."""
    ctx = metrics_mod.Context(metrics_mod.ApiDir(tmp_path), repo.root, [])
    lines = metrics_mod.pr_tests_lines(ctx, [])
    assert lines[0] == (
        "pr tests: 0 pull requests; selected 0 of 0 (-); test step 0.0 minutes; "
        "full: always_full 0, unmapped 0, share 0, thorough 0, other 0; unknown: 0"
    )


@pytest.mark.parametrize("execution", ["local", "hosted"])
def test_a_pull_request_with_no_ci_run(repo, tmp_path, execution):
    """REQ-062: brief #2012 answer 5 (`execution = "local"`: `unknown (no CI run)`)."""
    repo.write("agk.toml", f'execution = "{execution}"\n')
    api = week(tmp_path, {121: SELECTED})
    pull(api, 122, "2026-10-09T09:00:00Z")
    lines, _ = section(repo, api)
    if execution == "local":
        assert lines[0].endswith("unknown: 1 (no CI run 1)")
    else:
        assert lines[0].startswith("pr tests: 1 pull requests;")
        assert lines[0].endswith("unknown: 0")


def test_a_project_run_still_counts(repo, tmp_path):
    """REQ-062: brief #2012 answer 5 (a project's `Project tests` lines, one log each)."""
    api = week(tmp_path, {121: None})
    picked = log("project tests: pr_tests selected, event pull_request")
    api.jobs(12111, [ran_job(121110, 60, name="Project tests")])
    (api.path / "job-log-121110.json").write_text(json.dumps(picked))
    lines, _ = section(repo, api)
    assert lines[0].startswith("pr tests: 1 pull requests; selected 1 of 1 (100%);")
