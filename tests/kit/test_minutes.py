"""Tests of scripts/agk/minutes.py (brief #324, ADR-0184): the Actions minutes a project used this
month, the plan's included minutes, an estimate from run history and a warning. Saved API responses
(`--api-dir`), no network, no `gh`. REQ-020"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "minutes"
TODAY = "2026-10-30"


def case(tmp_path: Path, name: str = "month") -> Path:
    """A copy of a saved case that a test may change."""
    dest = tmp_path / "api"
    shutil.copytree(FIXTURES / name, dest)
    return dest


def save(api: Path, name: str, data) -> None:
    (api / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def refuse(api: Path, name: str, status: int) -> None:
    (api / f"{name}.json").unlink(missing_ok=True)
    (api / f"{name}.status").write_text(f"{status}\n", encoding="utf-8")


def minutes(repo, api: Path, *extra: str, today: str = TODAY):
    if not (repo.root / "agk.toml").exists():
        repo.write("agk.toml", 'default_branch = "main"\n')
    return repo.run("minutes.py", "--api-dir", str(api), "--today", today, *extra)


def report(repo, api: Path, *extra: str, today: str = TODAY) -> dict:
    proc = minutes(repo, api, "--json", *extra, today=today)
    assert proc.returncode in (0, 3), proc.stdout + proc.stderr
    return json.loads(proc.stdout)


# --- the billing API: readable, refused, missing -------------------------------------------------


def test_billing_readable_gives_used_and_included_minutes(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (the billing API answers)."""
    data = report(repo, case(tmp_path))
    assert data["month"] == "2026-10"
    assert data["used"] == {"minutes": 1700, "source": "billing"}
    assert data["included"] == {"minutes": 2000, "reason": None}


def test_billing_readable_text(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (the printed lines)."""
    out = minutes(repo, case(tmp_path)).stdout
    assert "minutes used this month: 1700 (billing, the whole account)" in out
    assert "included minutes: 2000" in out


@pytest.mark.parametrize("status", [401, 403])
def test_billing_refused_reads_unknown_with_the_reason_class(repo, tmp_path, status):
    """REQ-020: brief #324 answer 1 (refused: unknown, with the reason class)."""
    api = case(tmp_path)
    refuse(api, "billing", status)
    proc = minutes(repo, api)
    assert proc.returncode == 0, proc.stdout
    assert "included minutes: unknown (the token cannot read billing: refused)" in proc.stdout
    assert "minutes used this month: 17 (estimate from run history)" in proc.stdout
    data = report(repo, api)
    assert data["included"] == {"minutes": None, "reason": "refused"}
    assert data["used"] == {"minutes": 17, "source": "estimate"}


@pytest.mark.parametrize("status", [404, 410])
def test_billing_missing_reads_unknown_with_the_reason_class(repo, tmp_path, status):
    """REQ-020: brief #324 answer 1 (the endpoint is missing)."""
    api = case(tmp_path)
    refuse(api, "billing", status)
    out = minutes(repo, api).stdout
    assert "included minutes: unknown (the token cannot read billing: missing)" in out


def test_billing_without_a_file_is_missing(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (no recorded response reads as missing, never as zero)."""
    api = case(tmp_path)
    (api / "billing.json").unlink()
    assert report(repo, api)["included"] == {"minutes": None, "reason": "missing"}


def test_billing_of_an_unexpected_shape_is_unreadable(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (a body without the fields is not guessed)."""
    api = case(tmp_path)
    save(api, "billing", {"message": "something else"})
    data = report(repo, api)
    assert data["included"] == {"minutes": None, "reason": "unreadable"}
    assert data["used"]["source"] == "estimate"


def test_a_user_account_reads_the_user_billing(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (the endpoint follows the owner's type)."""
    api = case(tmp_path)
    save(
        api,
        "repo",
        {
            "full_name": "someone/app",
            "private": True,
            "owner": {"login": "someone", "type": "User"},
        },
    )
    assert report(repo, api)["billing_endpoint"] == "/users/someone/settings/billing/actions"
    data = report(repo, case(tmp_path / "b"))
    assert data["billing_endpoint"] == "/orgs/example/settings/billing/actions"


# --- run history: a month boundary and rounding per job ------------------------------------------


def test_estimate_rounds_each_job_up_and_keeps_to_the_month(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (per-job rounding; a job of the previous month is not counted,
    a run created on the last day of September whose job starts in October is)."""
    data = report(repo, case(tmp_path))
    est = data["estimate"]
    assert est["minutes"] == 17
    assert est["workflows"] == {"governance": 6, "agk-route": 1, "project": 10, "proof": 0}
    assert est["self_hosted_jobs"] == 1 and est["running_jobs"] == 1
    assert est["complete"] is True


def test_estimate_text_lists_each_workflow_largest_first(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (per workflow)."""
    out = minutes(repo, case(tmp_path)).stdout
    lines = out.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("estimate from run history: 17"))
    assert lines[start + 1 : start + 5] == [
        "  project: 10",
        "  governance: 6",
        "  agk-route: 1",
        "  proof: 0",
    ]


def test_a_job_of_one_second_bills_a_whole_minute_and_a_skipped_job_none(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (GitHub rounds each job up to a whole minute)."""
    from minutes import job_minutes

    assert (
        job_minutes(
            {
                "started_at": "2026-10-01T00:00:00Z",
                "completed_at": "2026-10-01T00:00:01Z",
                "conclusion": "success",
            }
        )
        == 1
    )
    assert (
        job_minutes(
            {
                "started_at": "2026-10-01T00:00:00Z",
                "completed_at": "2026-10-01T00:01:00Z",
                "conclusion": "success",
            }
        )
        == 1
    )
    assert (
        job_minutes(
            {
                "started_at": "2026-10-01T00:00:00Z",
                "completed_at": "2026-10-01T00:01:01Z",
                "conclusion": "failure",
            }
        )
        == 2
    )
    assert (
        job_minutes(
            {
                "started_at": "2026-10-01T00:00:00Z",
                "completed_at": "2026-10-01T00:00:00Z",
                "conclusion": "skipped",
            }
        )
        == 0
    )
    assert job_minutes({"started_at": "2026-10-01T00:00:00Z", "completed_at": None}) is None


def test_the_first_day_of_a_month_counts_only_that_month(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (run history over a month boundary, seen from November)."""
    data = report(repo, case(tmp_path), today="2026-11-01")
    assert data["month"] == "2026-11"
    assert data["estimate"]["minutes"] == 0
    assert data["merged_pulls"] == 0 and data["per_merged_pull"] is None


def test_a_capped_run_history_says_the_estimate_is_a_lower_bound(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (a capped run list: the estimate is a lower bound)."""
    api = case(tmp_path)
    runs = json.loads((api / "runs.json").read_text(encoding="utf-8"))
    runs["total_count"] = 1500
    save(api, "runs", runs)
    data = report(repo, api)
    assert data["estimate"]["complete"] is False
    out = minutes(repo, api).stdout
    assert "estimate from run history: at least 17" in out
    assert "minutes per merged pull request: at least 8.5 (2 merged this month)" in out


def test_a_run_whose_jobs_cannot_be_read_makes_the_estimate_a_lower_bound(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (a missing job list is not read as zero minutes)."""
    api = case(tmp_path)
    refuse(api, "jobs-104", 403)
    data = report(repo, api)
    assert data["estimate"]["minutes"] == 7 and data["estimate"]["complete"] is False


# --- minutes per merged pull request --------------------------------------------------------------


def test_minutes_per_merged_pull_request_over_the_month(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (two merged this month; one closed unmerged; one merged in
    September but updated in October)."""
    data = report(repo, case(tmp_path))
    assert data["merged_pulls"] == 2 and data["per_merged_pull"] == 8.5
    out = minutes(repo, case(tmp_path / "b")).stdout
    assert "minutes per merged pull request: 8.5 (2 merged this month)" in out
    assert "  (1 job on a self-hosted runner, not billed)" in out
    assert "  (1 job still running, not counted yet)" in out


# --- the warning threshold ------------------------------------------------------------------------


def test_warning_past_the_default_threshold(repo, tmp_path):
    """REQ-020: brief #324 answer 2 (1700 of 2000 is 85%, past the default 80)."""
    proc = minutes(repo, case(tmp_path))
    assert proc.returncode == 3
    warning = [ln for ln in proc.stdout.splitlines() if ln.startswith("warning:")]
    assert warning == [
        "warning: 1700 of 2000 included minutes used (85%), past minutes_warn (80%); "
        "when they run out, see local mode in docs/guides/project-ci.md"
    ]


def test_no_warning_under_a_raised_threshold(repo, tmp_path):
    """REQ-020: brief #324 answer 2 (minutes_warn is an optional agk.toml setting)."""
    repo.write("agk.toml", 'default_branch = "main"\nminutes_warn = 90\n')
    proc = minutes(repo, case(tmp_path))
    assert proc.returncode == 0
    assert "warning:" not in proc.stdout
    assert json.loads(minutes(repo, case(tmp_path / "b"), "--json").stdout)["warn_percent"] == 90


def test_warning_at_exactly_the_threshold(repo, tmp_path):
    """REQ-020: brief #324 answer 2 (1600 of 2000 is 80%)."""
    api = case(tmp_path)
    save(api, "billing", {"total_minutes_used": 1600, "included_minutes": 2000})
    assert minutes(repo, api).returncode == 3


def test_no_warning_below_the_threshold(repo, tmp_path):
    """REQ-020: brief #324 answer 2."""
    api = case(tmp_path)
    save(api, "billing", {"total_minutes_used": 1500, "included_minutes": 2000})
    proc = minutes(repo, api)
    assert proc.returncode == 0 and "warning:" not in proc.stdout
    assert report(repo, api)["warning"] is None


def test_the_estimate_warns_when_it_passes_the_billing_figure(repo, tmp_path):
    """REQ-020: brief #324 answer 2 (the warning reads the estimate as well)."""
    api = case(tmp_path)
    save(api, "billing", {"total_minutes_used": 1, "included_minutes": 20})
    proc = minutes(repo, api)
    assert proc.returncode == 3
    assert "warning: 17 of 20 included minutes used (85%)" in proc.stdout


def test_no_warning_without_included_minutes(repo, tmp_path):
    """REQ-020: brief #324 answer 2 (an unknown plan never warns and never guesses)."""
    api = case(tmp_path)
    refuse(api, "billing", 403)
    proc = minutes(repo, api)
    assert proc.returncode == 0 and "warning:" not in proc.stdout


@pytest.mark.parametrize("value", ["0", "101", "true", '"80"', "12.5"])
def test_an_invalid_threshold_is_refused_naming_the_setting(repo, tmp_path, value):
    """REQ-020: brief #324 answer 2 (refusals name the setting, never the value)."""
    repo.write("agk.toml", f'default_branch = "main"\nminutes_warn = {value}\n')
    proc = minutes(repo, case(tmp_path))
    assert proc.returncode == 1
    assert proc.stdout == (
        "FAIL minutes: minutes_warn must be a whole number from 1 to 100 "
        "(setting: minutes_warn in agk.toml)\n"
    )


def test_nothing_is_written(repo, tmp_path):
    """REQ-020: brief #324 answer 2 (nothing is written)."""
    api = case(tmp_path)
    before = sorted(p.name for p in api.iterdir())
    repo.write("agk.toml", 'default_branch = "main"\n')
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "start")
    minutes(repo, api)
    assert sorted(p.name for p in api.iterdir()) == before
    assert repo.git("status", "--porcelain") == ""


# --- no repository access -------------------------------------------------------------------------


@pytest.mark.parametrize("status", [403, 404])
def test_no_repository_access_fails_naming_the_path_class(repo, tmp_path, status):
    """REQ-020: brief #324 answer 4 (no repository access)."""
    api = case(tmp_path)
    refuse(api, "repo", status)
    proc = minutes(repo, api)
    assert proc.returncode == 1
    assert "path class: repository" in proc.stdout
    assert "example/app" not in proc.stdout


def test_run_history_refused_reads_unknown(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (the repository answers, its run history does not)."""
    api = case(tmp_path)
    refuse(api, "runs", 403)
    proc = minutes(repo, api)
    unknown = "estimate from run history: unknown (the token cannot read the run history: refused)"
    assert unknown in proc.stdout
    assert "minutes per merged pull request: unknown" in proc.stdout
    data = report(repo, api)
    assert data["estimate"]["minutes"] is None and data["estimate"]["reason"] == "refused"
    assert data["used"] == {"minutes": 1700, "source": "billing"}


# --- the command line -----------------------------------------------------------------------------


def test_a_public_repository_is_told_its_standard_runners_are_free(repo, tmp_path):
    """REQ-020: brief #324 answer 1 (a note, the figures unchanged)."""
    api = case(tmp_path)
    save(
        api,
        "repo",
        {
            "full_name": "example/app",
            "private": False,
            "owner": {"login": "example", "type": "Organization"},
        },
    )
    out = minutes(repo, api).stdout
    assert "note: a public repository's standard runners are not billed" in out


@pytest.mark.parametrize("args", [["--bogus"], ["--today"], ["--today", "30-10-2026"]])
def test_usage(repo, tmp_path, args):
    """REQ-020: brief #324 answer 1."""
    proc = repo.run("minutes.py", "--api-dir", str(case(tmp_path)), *args)
    assert proc.returncode == 2
    assert proc.stderr.startswith("usage: minutes.py")


def test_the_script_uses_get_only_and_the_standard_library():
    """REQ-020: brief #324 answer 1 (GET only, standard library, `gh` holds the credential)."""
    text = (Path(__file__).resolve().parents[2] / "scripts" / "agk" / "minutes.py").read_text(
        encoding="utf-8"
    )
    assert '"--method", "GET"' in text
    for verb in ("POST", "PATCH", "PUT", "DELETE"):
        assert f'"{verb}"' not in text
    for lib in ("requests", "urllib", "http.client", "httpx"):
        assert f"import {lib}" not in text


# --- the guide, the template and the kit ----------------------------------------------------------

KIT = Path(__file__).resolve().parents[2]


def test_the_guide_has_a_section_on_reading_the_minutes():
    """REQ-020: brief #324 answer 3 (a short section, pointing to local mode)."""
    text = (KIT / "docs" / "guides" / "project-ci.md").read_text(encoding="utf-8")
    section = text.split("## How many minutes are left", 1)[1].split("\n## ", 1)[0]
    for needle in (
        "python3 scripts/agk/minutes.py",
        "--json",
        "minutes_warn",
        "unknown",
        "at least",
        "local mode",
        "#322",
    ):
        assert needle in section, needle


def test_the_template_names_the_optional_setting():
    """REQ-020: brief #324 answer 2 (an optional agk.toml setting, off the default's way)."""
    text = (KIT / "kit" / "templates" / "agk.toml").read_text(encoding="utf-8")
    assert "# minutes_warn = 80" in text.splitlines()


def test_the_script_is_installed_in_a_project():
    """REQ-020: brief #324 answer 1 (a project runs the one command)."""
    data = json.loads((KIT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/minutes.py" in data["verbatim"]
