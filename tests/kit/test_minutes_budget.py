"""Tests of the GitHub calls the minutes readers make (brief #2011, ADR-0832): the doctor's
`actions-minutes` check reads billing only; the estimate reads no job list of a skipped run, keeps
each finished day's sums and stays inside the hourly allowance. Recorded or generated answers
(invented, example.com), no network, no `gh`. REQ-020"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import doctor as doctor_script  # noqa: E402
import facts  # noqa: E402
import minutes  # noqa: E402
import scorecard  # noqa: E402

TODAY = date(2026, 10, 30)
REPO = {"full_name": "example/app", "private": True, "owner": {"login": "example", "type": "User"}}
BILLED = {"total_minutes_used": 100, "included_minutes": 2000}


def at(day: date, hour: int = 10, minute: int = 0) -> str:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def a_run(rid: int, day: date, conclusion: str = "success") -> dict:
    return {"id": rid, "name": "proof", "created_at": at(day), "conclusion": conclusion}


def two_minutes(day: date) -> dict:
    """One job of 2 minutes on a GitHub-hosted runner that started on DAY."""
    job = {
        "conclusion": "success",
        "started_at": at(day, 10, 1),
        "completed_at": at(day, 10, 3),
        "labels": ["ubuntu-latest"],
    }
    return {"total_count": 1, "jobs": [job]}


class Source:
    """A source as `minutes.estimate` reads it, counting each call by its name."""

    reads_allowance = True

    def __init__(self, runs: list[dict], keep: Path | None = None, rate: dict | None = None):
        self.runs, self.keep, self.rate = runs, keep, rate
        self.calls: list[str] = []
        self.jobs: dict[int, dict] = {}

    def get(self, name: str, endpoint: str, until=None):
        self.calls.append(name)
        if name == "runs":
            return 200, {"total_count": len(self.runs), "workflow_runs": list(self.runs)}
        if name == "rate_limit":
            return (200, self.rate) if self.rate is not None else (404, None)
        if name == "repo":
            return 200, REPO
        if name.startswith("jobs-"):
            rid = int(name.removeprefix("jobs-"))
            run = next(r for r in self.runs if r["id"] == rid)
            day = date.fromisoformat(run["created_at"][:10])
            return 200, self.jobs.get(rid, two_minutes(day))
        return 404, None

    def job_calls(self) -> list[str]:
        return [c for c in self.calls if c.startswith("jobs-")]


def week() -> tuple[datetime, datetime]:
    """The window the tests read: 25 to 30 October, so the runs list from 24 October."""
    start = datetime(2026, 10, 25, tzinfo=UTC)
    return start, datetime(2026, 10, 31, tzinfo=UTC)


def runs_per_day(count: int) -> list[dict]:
    """COUNT runs a day from 24 to 30 October (30 October is today)."""
    out, rid = [], 1
    for offset in range(7):
        for _ in range(count):
            out.append(a_run(rid, date(2026, 10, 24) + timedelta(days=offset)))
            rid += 1
    return out


def rate(remaining: int) -> dict:
    reset = int(datetime(2026, 10, 30, 17, 51, tzinfo=UTC).timestamp())
    return {"resources": {"core": {"limit": 15000, "remaining": remaining, "reset": reset}}}


# --- answer 1: the doctor reads billing only -----------------------------------------------------


def a_big_month(api: Path) -> None:
    """A recorded month of 40,000 runs, with billing refused."""
    api.mkdir(parents=True, exist_ok=True)
    (api / "repo.json").write_text(json.dumps(REPO), encoding="utf-8")
    (api / "billing.status").write_text("403\n", encoding="utf-8")
    runs = [a_run(i, date(2026, 10, 1 + i % 29)) for i in range(1, 40001)]
    body = {"total_count": len(runs), "workflow_runs": runs}
    (api / "runs.json").write_text(json.dumps(body), encoding="utf-8")


def test_the_doctor_makes_at_most_two_calls_over_a_month_of_40000_runs(tmp_path, monkeypatch):
    """REQ-020: brief #2011 answer 1 (billing refused: the repository and billing, nothing more,
    and `minutes-unknown` pointing to minutes.py)."""
    api = tmp_path / "api"
    a_big_month(api)
    calls: list[str] = []
    real_get, real_read = minutes.ApiDir.get, doctor_script.Reads.read

    def counted_get(self, name, endpoint, until=None):
        calls.append(name)
        return real_get(self, name, endpoint, until)

    def counted_read(self, name, path, not_found=None):
        calls.append(name)
        return real_read(self, name, path, not_found)

    monkeypatch.setattr(minutes.ApiDir, "get", counted_get)
    monkeypatch.setattr(doctor_script.Reads, "read", counted_read)
    root = tmp_path / "root"
    root.mkdir()
    (root / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    reads = doctor_script.Reads(None, api)
    result = doctor_script.minutes_result(root, reads, TODAY)
    assert len(calls) <= 2, calls
    assert (result.status, result.reason) == ("cannot-check", "minutes-unknown")
    assert "python3 scripts/agk/minutes.py" in doctor_script.HINTS["minutes-unknown"]
    assert "run history" not in doctor_script.HINTS["minutes-unknown"]


def test_the_line_with_billing_is_todays_line_byte_for_byte():
    """REQ-020: brief #2011 answer 1 (billing answers: the line and the levels are today's)."""
    src = Source([])
    src.get = lambda name, endpoint, until=None: (200, BILLED) if name == "billing" else (404, None)
    level, line = minutes.outlook(src, REPO, date(2026, 10, 19), 80)
    assert (level, line) == (
        "ok",
        "actions minutes: 100 of 2000 used (5%), level ok; runs out not this month",
    )


def test_the_line_without_billing_names_the_reason_and_minutes_py():
    """REQ-020: brief #2011 answer 1 (billing refused: no estimate, the reason class named)."""
    src = Source(runs_per_day(3))
    real = src.get
    src.get = lambda name, endpoint, until=None: (
        (403, None) if name == "billing" else real(name, endpoint, until)
    )
    level, line = minutes.outlook(src, REPO, TODAY, 80)
    assert level == "unknown"
    assert line == (
        "actions minutes: unknown (the token cannot read billing: refused); "
        "run python3 scripts/agk/minutes.py for the estimate"
    )
    assert src.calls == []  # billing went through the lambda; no run list, no job list


# --- answer 2: runs that cost nothing are not read -----------------------------------------------


def test_a_skipped_run_gets_no_job_call_and_a_cancelled_run_does():
    """REQ-020: brief #2011 answer 2 and Q-DM-4 (skipped: counted, not read; cancelled: read)."""
    day = date(2026, 10, 30)
    runs = [a_run(1, day, "skipped"), a_run(2, day, "cancelled"), a_run(3, day)]
    src = Source(runs, rate=rate(5000))
    est = minutes.estimate(src, *week(), today=TODAY)
    assert sorted(src.job_calls()) == ["jobs-2", "jobs-3"]
    assert est.skipped_runs == 1
    assert est.minutes == 4 and est.complete


# --- answer 3: finished days are kept ------------------------------------------------------------


def test_a_second_reading_reads_no_job_list_of_a_kept_day(tmp_path):
    """REQ-020: brief #2011 answer 3 (finished days from their files; today read again)."""
    keep = tmp_path / "keep"
    runs = runs_per_day(2)
    first = Source(runs, keep=keep, rate=rate(5000))
    one = minutes.estimate(first, *week(), True, week(), today=TODAY)
    assert len(first.job_calls()) == 14
    kept = sorted(p.name for p in keep.glob("*.json"))
    assert kept == [f"2026-10-{d}.json" for d in range(24, 30)]  # today is never kept
    second = Source(runs, keep=keep, rate=rate(5000))
    two = minutes.estimate(second, *week(), True, week(), today=TODAY)
    assert sorted(second.job_calls()) == ["jobs-13", "jobs-14"]  # today's two runs only
    assert (two.minutes, two.week_minutes, two.workflows, two.runs) == (
        one.minutes,
        one.week_minutes,
        one.workflows,
        one.runs,
    )
    assert one.minutes == 24  # 25 to 30 October, 2 runs of 2 minutes a day


def test_a_corrupt_or_other_day_file_is_read_again(tmp_path):
    """REQ-020: brief #2011 answer 3 (a file that cannot be parsed, or of another schema)."""
    keep = tmp_path / "keep"
    runs = runs_per_day(1)
    minutes.estimate(Source(runs, keep=keep, rate=rate(5000)), *week(), today=TODAY)
    (keep / "2026-10-26.json").write_text("{not json", encoding="utf-8")
    other = json.loads((keep / "2026-10-27.json").read_text(encoding="utf-8"))
    other["schema"] = 99
    (keep / "2026-10-27.json").write_text(json.dumps(other), encoding="utf-8")
    src = Source(runs, keep=keep, rate=rate(5000))
    est = minutes.estimate(src, *week(), today=TODAY)
    assert sorted(src.job_calls()) == ["jobs-3", "jobs-4", "jobs-7"]
    assert est.minutes == 12
    assert json.loads((keep / "2026-10-26.json").read_text(encoding="utf-8"))["schema"] == 1


def test_a_kept_day_stores_minutes_after_the_rates(tmp_path):
    """REQ-020: brief #2011 answer 6 (a private repository: a Windows job counts twice; a file
    kept for the other rate is not used)."""
    keep = tmp_path / "keep"
    day = date(2026, 10, 28)
    src = Source([a_run(1, day)], keep=keep, rate=rate(5000))
    src.jobs[1] = two_minutes(day)
    src.jobs[1]["jobs"][0]["labels"] = ["windows-latest"]
    assert minutes.estimate(src, *week(), True, today=TODAY).minutes == 4
    public = Source([a_run(1, day)], keep=keep, rate=rate(5000))
    public.jobs[1] = src.jobs[1]
    assert minutes.estimate(public, *week(), False, today=TODAY).minutes == 2
    assert public.job_calls() == ["jobs-1"]


def test_a_day_with_a_job_still_running_or_a_list_refused_is_not_kept(tmp_path):
    """REQ-020: brief #2011 answer 3 (written only for a day whose every job list answered 200)."""
    keep = tmp_path / "keep"
    src = Source([a_run(1, date(2026, 10, 27)), a_run(2, date(2026, 10, 28))], keep, rate(5000))
    src.jobs[1] = {"total_count": 1, "jobs": [{"started_at": at(date(2026, 10, 27))}]}
    real = src.get
    src.get = lambda n, e, u=None: (500, None) if n == "jobs-2" else real(n, e, u)
    minutes.estimate(src, *week(), today=TODAY)
    kept = sorted(p.name for p in keep.glob("*.json"))
    assert kept == [f"2026-10-{d}.json" for d in (24, 25, 26, 29)]  # a day without runs is kept


def test_the_recorded_mode_writes_no_day_file(repo, tmp_path):
    """REQ-020: brief #2011 answer 3 (`--api-dir` reads and writes no file)."""
    repo.write("agk.toml", 'default_branch = "main"\n')
    api = tmp_path / "api"
    api.mkdir()
    (api / "repo.json").write_text(json.dumps(REPO), encoding="utf-8")
    runs = runs_per_day(1)
    (api / "runs.json").write_text(json.dumps({"total_count": 7, "workflow_runs": runs}))
    for run in runs:
        day = date.fromisoformat(run["created_at"][:10])
        (api / f"jobs-{run['id']}.json").write_text(json.dumps(two_minutes(day)))
    proc = repo.run("minutes.py", "--api-dir", str(api), "--today", "2026-10-30", "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["estimate"]["minutes"] == 14  # 7 runs of 2 minutes in October
    assert not list(repo.root.rglob("agk-minutes"))


# --- answer 4: it stays inside the allowance -----------------------------------------------------


def test_a_reading_stops_at_the_allowance_margin_and_keeps_the_days_it_finished(tmp_path):
    """REQ-020: brief #2011 answer 4 (remaining 2,500: at most 500 job lists, oldest day first)."""
    keep = tmp_path / "keep"
    src = Source(runs_per_day(100), keep=keep, rate=rate(2500))
    est = minutes.estimate(src, *week(), today=TODAY)
    assert len(src.job_calls()) == 500
    assert src.calls.index("rate_limit") < min(src.calls.index(c) for c in src.job_calls())
    assert not est.complete
    assert (est.days_read, est.days) == (5, 7)
    assert sorted(p.name for p in keep.glob("*.json")) == [
        f"2026-10-{d}.json" for d in range(24, 29)
    ]
    assert minutes.stopped_line(est) == (
        f"actions minutes: at least {est.minutes} used this month (5 of 7 days read; run again "
        "after the GitHub allowance resets at 17:51 UTC)"
    )
    again = Source(runs_per_day(100), keep=keep, rate=rate(2500))
    minutes.estimate(again, *week(), today=TODAY)
    assert {int(c.removeprefix("jobs-")) for c in again.job_calls()} == set(range(501, 701))


def test_an_unreadable_allowance_reads_at_most_1000_job_lists():
    """REQ-020: brief #2011 answer 4 (no `/rate_limit`: UNREAD_LIMIT, said the same way)."""
    src = Source(runs_per_day(200))
    est = minutes.estimate(src, *week(), today=TODAY)
    assert len(src.job_calls()) == minutes.UNREAD_LIMIT == 1000
    assert not est.complete
    assert minutes.stopped_line(est) == (
        f"actions minutes: at least {est.minutes} used this month (5 of 7 days read; run again "
        "after the GitHub allowance resets, at a time that cannot be read)"
    )
    assert minutes.ALLOWANCE_MARGIN == 2000


def test_a_complete_reading_has_no_stopped_line():
    """REQ-020: brief #2011 answer 4 (inside the allowance: no `at least` line)."""
    est = minutes.estimate(Source(runs_per_day(1), rate=rate(5000)), *week(), today=TODAY)
    assert est.complete and minutes.stopped_line(est) is None


# --- answer 6: settings ---------------------------------------------------------------------------


def test_an_invalid_minutes_warn_is_refused_by_name(repo, tmp_path):
    """REQ-020: brief #2011 answer 6 (`minutes_warn` out of range: refused, the setting named)."""
    repo.write("agk.toml", 'default_branch = "main"\nminutes_warn = 0\n')
    api = tmp_path / "api"
    api.mkdir()
    (api / "repo.json").write_text(json.dumps(REPO), encoding="utf-8")
    proc = repo.run("minutes.py", "--api-dir", str(api), "--line")
    assert proc.returncode == 1
    out = proc.stdout + proc.stderr
    assert "(setting: minutes_warn in agk.toml)" in out and "= 0" not in out


@pytest.mark.parametrize("mode", ["local", "hosted", "hybrid", "pool"])
def test_the_doctor_check_is_information_in_every_execution_mode(tmp_path, mode):
    """REQ-020: brief #2011 answer 6 (`execution` changes nothing in the line)."""
    api = tmp_path / "api"
    api.mkdir()
    (api / "repo.json").write_text(json.dumps(REPO), encoding="utf-8")
    (api / "billing.json").write_text(json.dumps(BILLED), encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    (root / "agk.toml").write_text(
        f'default_branch = "main"\nexecution = "{mode}"\n', encoding="utf-8"
    )
    result = doctor_script.minutes_result(root, doctor_script.Reads(None, api), date(2026, 10, 19))
    assert result.status == "ok"
    assert result.message == (
        " (actions minutes: 100 of 2000 used (5%), level ok; runs out not this month)"
    )


# --- the first fix list ------------------------------------------------------------------------


def test_a_day_is_finished_by_the_real_clock_not_by_today(tmp_path, monkeypatch):
    """REQ-020: brief #2011 answer 3, fix list item 1 (`--today` tomorrow keeps no file of the real
    today, and a later reading reads that day again)."""
    monkeypatch.setattr(minutes, "utc_today", lambda: date(2026, 10, 30))
    keep = tmp_path / "keep"
    runs = runs_per_day(1)
    minutes.estimate(Source(runs, keep, rate(5000)), *week(), today=date(2026, 10, 31))
    assert not (keep / "2026-10-30.json").exists() and (keep / "2026-10-29.json").exists()
    again = Source(runs, keep, rate(5000))
    minutes.estimate(again, *week(), today=date(2026, 10, 31))
    assert again.job_calls() == ["jobs-7"]


class Answers:
    """A metrics-style source (data or None) of 1,500 runs' job lists and the allowance."""

    def __init__(self, remaining: int | None) -> None:
        self.remaining, self.calls = remaining, 0

    def get(self, name: str, endpoint: str, until=None):
        if name == "rate_limit":
            return None if self.remaining is None else rate(self.remaining)
        self.calls += 1
        return two_minutes(date(2026, 10, 28))


def fifteen_hundred() -> dict:
    runs = [a_run(i, date(2026, 10, 28)) for i in range(1, 1501)]
    return {"total_count": len(runs), "workflow_runs": runs}


@pytest.mark.parametrize("adapter", [facts.WeekRuns, scorecard.Paired])
def test_the_week_readers_read_the_allowance_too(adapter):
    """REQ-020: brief #2011 answers 4 and 9, fix list item 2 (14,000 calls left: all 1,500 job
    lists read and the estimate complete; no allowance read: 1,000 and incomplete)."""
    src = Answers(14000)
    est = minutes.estimate(adapter(src, fifteen_hundred()), *week(), today=TODAY)
    assert (src.calls, est.complete, est.minutes) == (1500, True, 3000)
    unread = Answers(None)
    est = minutes.estimate(adapter(unread, fifteen_hundred()), *week(), today=TODAY)
    assert (unread.calls, est.complete) == (1000, False)


def test_a_stopped_report_says_at_least_and_unknown_when_nothing_was_read():
    """REQ-020: brief #2011 answer 4, fix list item 3 (never an exact figure, never 0)."""
    text = minutes.render(minutes.read(Source(runs_per_day(100), rate=rate(2500)), TODAY, 80, None))
    assert "minutes used this month: at least 1000 (estimate from run history)" in text
    assert "estimate from run history: at least 1000 " in text
    assert "(29 of 31 days read; run again after the GitHub allowance resets at 17:51 UTC)" in text
    spent = minutes.render(minutes.read(Source(runs_per_day(1), rate=rate(1500)), TODAY, 80, None))
    assert "minutes used this month: unknown" in spent
    assert "estimate from run history: unknown (the GitHub allowance is spent)" in spent
    assert (
        "actions minutes: unknown (24 of 31 days read; run again after" in spent
    )  # 30 Sep-23 Oct: no runs
    assert ": 0 (" not in spent


def test_the_day_files_live_in_the_repository_roots_common_dir(repo, tmp_path_factory, monkeypatch):
    """REQ-020: brief #2011 answers 3, 6 and 7, fix list items 4 and 6 (the real path, no injected
    folder: from a subfolder, shared by a linked worktree, none outside a git checkout)."""
    repo.write("sub/a.txt", "a\n")
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "first")
    expected = (repo.root / ".git").resolve() / "agk-minutes" / "example-app"
    monkeypatch.chdir(repo.root / "sub")
    assert minutes.Gh("example/app").keep == expected
    linked = tmp_path_factory.mktemp("linked") / "wt"
    repo.git("worktree", "add", "-q", str(linked))
    monkeypatch.chdir(linked)
    assert minutes.Gh("example/app").keep == expected
    monkeypatch.chdir(tmp_path_factory.mktemp("plain"))
    assert minutes.Gh("example/app").keep is None


@pytest.mark.parametrize("mode", ["local", "hosted", "hybrid", "pool"])
@pytest.mark.parametrize("used", [1000, 1600, 1900])
def test_the_check_warns_and_never_fails_above_half_in_every_mode(tmp_path, mode, used):
    """REQ-020: brief #2011 answer 6, fix list item 5 (from the 50% level the check is a warning,
    the `warn` severity, never an error, in every execution mode)."""
    api = tmp_path / "api"
    api.mkdir()
    (api / "repo.json").write_text(json.dumps(REPO), encoding="utf-8")
    billed = {"total_minutes_used": used, "included_minutes": 2000}
    (api / "billing.json").write_text(json.dumps(billed), encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    (root / "agk.toml").write_text(
        f'default_branch = "main"\nexecution = "{mode}"\n', encoding="utf-8"
    )
    result = doctor_script.minutes_result(root, doctor_script.Reads(None, api), date(2026, 10, 19))
    assert result.status == "fail"
    assert doctor_script.CHECKS["actions-minutes"][0] == "warn"


def test_personal_mode_reads_no_forge(tmp_path):
    """REQ-020: brief #2011 answer 6 (`[personal]`: no forge, `not-github`, no minutes read)."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    result = doctor_script.minutes_result(root, doctor_script.Reads(None, None), TODAY)
    assert (result.status, result.reason) == ("cannot-check", "not-github")


def test_paused_prints_the_one_line_before_any_minutes_read(repo):
    """REQ-020: brief #2011 answer 6 (`paused = true`: the `--paused` path is unchanged)."""
    repo.write("agk.toml", 'default_branch = "main"\npaused = true\n')
    proc = repo.run("doctor.py", "--paused")
    assert (proc.returncode, proc.stdout) == (0, "agk paused\n"), proc.stdout + proc.stderr


def test_a_day_file_is_written_whole_by_rename(tmp_path, monkeypatch):
    """REQ-020: brief #2011 answer 7 (two sessions: each writes a whole file by rename)."""
    keep = tmp_path / "keep"
    moves: list[tuple[Path, Path]] = []
    real = minutes.os.replace

    def recorded(a, b):
        moves.append((Path(a), Path(b)))
        real(a, b)

    monkeypatch.setattr(minutes.os, "replace", recorded)
    minutes.estimate(Source([a_run(1, date(2026, 10, 28))], keep, rate(5000)), *week(), today=TODAY)
    assert (keep / "2026-10-28.json") in [b for _, b in moves]
    assert all(a.parent == keep and a.name.endswith(".tmp") for a, _ in moves)
    assert not list(keep.glob("*.tmp")) and not list(keep.glob(".*.tmp"))


def test_a_day_file_of_the_month_before_is_read_only_inside_the_window(tmp_path):
    """REQ-020: brief #2011 answer 7 (a week that starts in the month before reads its kept day;
    a month reading leaves it out of the month's sums)."""
    keep = tmp_path / "keep"
    nov = (datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 12, 1, tzinfo=UTC))
    seven = (datetime(2026, 10, 28, tzinfo=UTC), datetime(2026, 11, 4, tzinfo=UTC))
    runs = [a_run(1, date(2026, 10, 29)), a_run(2, date(2026, 11, 2))]
    today = date(2026, 11, 3)
    first = minutes.estimate(Source(runs, keep, rate(5000)), *nov, True, seven, today=today)
    assert (keep / "2026-10-29.json").exists()
    src = Source(runs, keep, rate(5000))
    again = minutes.estimate(src, *nov, True, seven, today=today)
    assert src.job_calls() == []  # both days kept
    assert (again.minutes, again.week_minutes) == (first.minutes, first.week_minutes) == (2, 4)


def test_each_rate_set_keeps_its_own_file(tmp_path):
    """REQ-020: brief #2011 answer 6, fix list item 7 (a reading at the runner rates and one
    counted once do not rewrite each other's day files)."""
    keep = tmp_path / "keep"
    day = date(2026, 10, 28)
    for rates in (True, False):
        minutes.estimate(Source([a_run(1, day)], keep, rate(5000)), *week(), rates, today=TODAY)
    assert (keep / "2026-10-28.json").exists() and (keep / "2026-10-28.plain.json").exists()
    for rates in (True, False):
        src = Source([a_run(1, day)], keep, rate(5000))
        minutes.estimate(src, *week(), rates, today=TODAY)
        assert src.job_calls() == []
