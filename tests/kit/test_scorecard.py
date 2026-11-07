"""The scorecard table from the readers that exist, and the `[scorecard]` setting (SPEC-0047
rules 1 to 3, brief #713, build (b), ADR-0311).

REQ-054 AC1 and AC2. `scorecard.py` reads one week of saved responses (`--api-dir`) or `gh api`
GET calls through a `gh` stub, prints one table and writes no file; `config.scorecard_settings`
reads the optional `[scorecard]` table. Fixtures in `tmp_path`, invented data (`example.com`
logins), no network. The tests were written first (answer 3).
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path

import pytest
import scorecard

import config

KIT = Path(__file__).resolve().parents[2]
TODAY = "2026-11-07"  # the week is 2026-10-31T00:00Z to 2026-11-07T00:00Z
ODD = "odd-value-example"
LEVEL = (
    "full_check_minutes prepush_seconds red_hours flaky_rate fix_list_rate lead_time_hours "
    "restore_hours ci_minutes_per_merge rule_words rule_lines old_failure_issues"
).split()


def full_run(rid: int, start: str, minutes: int, conclusion: str, attempt: int) -> dict:
    return {
        "id": rid,
        "name": "governance",
        "display_title": "governance full",
        "event": "push",
        "head_branch": "main",
        "created_at": start,
        "run_started_at": start,
        "updated_at": start.replace("T10:00", f"T10:{minutes:02d}"),
        "conclusion": conclusion,
        "run_attempt": attempt,
    }


def job(start: str, minutes: int, test_seconds: int | None = None) -> dict:
    end = start.replace("T10:00", f"T10:{minutes:02d}")
    steps = []
    if test_seconds is not None:
        steps = [
            {
                "name": "Project tests",
                "conclusion": "success",
                "started_at": start,
                "completed_at": start.replace(":00:00Z", f":00:{test_seconds % 60:02d}Z").replace(
                    "T10:00", f"T10:{test_seconds // 60:02d}"
                ),
            }
        ]
    return {
        "started_at": start,
        "completed_at": end,
        "conclusion": "success",
        "labels": ["ubuntu-latest"],
        "steps": steps,
    }


def comment(login: str, body: str, at: str = "2026-11-01T12:00:00Z") -> dict:
    return {"user": {"login": login}, "body": body, "created_at": at}


def issue(number: int, title: str, created: str, closed: str | None = None, **extra) -> dict:
    return {
        "number": number,
        "title": title,
        "created_at": created,
        "closed_at": closed,
        "body": extra.pop("body", ""),
        "labels": [{"name": n} for n in extra.pop("labels", [])],
        **extra,
    }


RED = "The default branch is red"
WEEK = {
    "runs-week": {
        "total_count": 6,
        "workflow_runs": [
            full_run(1, "2026-11-02T10:00:00Z", 10, "success", 1),
            full_run(2, "2026-11-03T10:00:00Z", 20, "success", 2),
            full_run(3, "2026-11-04T10:00:00Z", 30, "failure", 2),
            {
                **full_run(4, "2026-11-05T10:00:00Z", 5, "success", 1),
                "display_title": "governance edited",
                "event": "pull_request",
                "head_branch": "feature",
            },
            {**full_run(5, "2026-11-05T10:00:00Z", 5, "success", 1), "name": "proof"},
            full_run(6, "2026-10-25T10:00:00Z", 10, "success", 1),
        ],
    },
    "run-jobs-1": {"jobs": [job("2026-11-02T10:00:00Z", 10, 100)]},
    "run-jobs-2": {"jobs": [job("2026-11-03T10:00:00Z", 20, 200)]},
    "run-jobs-3": {"jobs": [job("2026-11-04T10:00:00Z", 30, 300)]},
    "run-jobs-4": {"jobs": [job("2026-11-05T10:00:00Z", 5)]},
    "run-jobs-5": {"jobs": [job("2026-11-05T10:00:00Z", 5)]},
    "repo": {"private": True},
    "pulls": [
        {
            "number": 11,
            "created_at": "2026-11-03T00:00:00Z",
            "merged_at": "2026-11-05T00:00:00Z",
            "updated_at": "2026-11-05T00:00:00Z",
            "user": {"login": "builder"},
        },
        {
            "number": 10,
            "created_at": "2026-11-01T00:00:00Z",
            "merged_at": "2026-11-02T00:00:00Z",
            "updated_at": "2026-11-02T00:00:00Z",
            "user": {"login": "builder"},
        },
        {
            "number": 13,
            "created_at": "2026-11-01T00:00:00Z",
            "merged_at": None,
            "updated_at": "2026-11-01T00:00:00Z",
        },
        {
            "number": 12,
            "created_at": "2026-10-19T00:00:00Z",
            "merged_at": "2026-10-20T00:00:00Z",
            "updated_at": "2026-10-20T00:00:00Z",
        },
    ],
    "comments-10": [
        comment("reviewer", "Verdict: fix list 1234abcd\n1. a thing"),
        comment("someone", "Verdict: fix list 1234abcd", "2026-11-01T12:30:00Z"),
        comment("reviewer", "Verdict: cleared 5678abcd", "2026-11-01T13:00:00Z"),
    ],
    "comments-11": [comment("reviewer", "Verdict: cleared 9abc1234")],
    "issues-open": [
        issue(20, RED, "2026-11-06T00:00:00Z"),
        issue(
            21,
            "a failure",
            "2026-10-01T00:00:00Z",
            labels=["found-bug"],
            body="Failure-signature: ab12",
        ),
        issue(
            22,
            "a failure",
            "2026-11-05T00:00:00Z",
            labels=["found-bug"],
            body="Failure-signature: cd34",
        ),
        issue(23, "a bug", "2026-10-01T00:00:00Z", labels=["found-bug"], body="no signature"),
        issue(24, RED, "2026-11-01T00:00:00Z", pull_request={"url": "https://example.com/p"}),
    ],
    "issues-closed": [
        issue(25, RED, "2026-11-01T00:00:00Z", "2026-11-01T06:00:00Z"),
        issue(26, RED, "2026-10-30T22:00:00Z", "2026-10-31T02:00:00Z"),
        issue(27, RED, "2026-10-20T00:00:00Z", "2026-10-21T00:00:00Z"),
    ],
}
EXPECTED = {
    "full_check_minutes": "20.0",
    "prepush_seconds": "200",
    "red_hours": "32.0",
    "flaky_rate": "25.0",
    "fix_list_rate": "50.0",
    "lead_time_hours": "36.0",
    "restore_hours": "5.0",
    "ci_minutes_per_merge": "35.0",
    "rule_words": "3",
    "rule_lines": "1",
    "old_failure_issues": "1",
}


def project(repo, toml: str = 'default_branch = "main"\n') -> None:
    repo.commit(
        {
            "agk.toml": toml,
            "config/reviewers.yaml": "version: 1\nverdict_authors: [reviewer, r]\n",
            "CLAUDE.md": "- one rule\n",
            "config/rule-budget.txt": "CLAUDE.md 3 1\n",
        }
    )


def saved(tmp_path: Path, responses: dict) -> Path:
    folder = tmp_path / "api"
    folder.mkdir()
    for name, data in responses.items():
        (folder / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    return folder


def rows(stdout: str) -> dict[str, tuple[str, str]]:
    found = {}
    for line in stdout.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] in LEVEL:
            found[cells[0]] = (cells[1], cells[2])
    return found


def snapshot(root: Path) -> dict[str, float]:
    return {
        str(p.relative_to(root)): p.stat().st_mtime
        for p in root.rglob("*")
        if ".git" not in p.parts
    }


def test_ac1_a_saved_week_gives_each_level_metric_in_order(repo, tmp_path):
    """REQ-054 AC1: rules 1 and 2, every level metric of one week from saved responses."""
    project(repo)
    api = saved(tmp_path, WEEK)
    proc = repo.run("scorecard.py", "--today", TODAY, "--api-dir", str(api))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    got = rows(proc.stdout)
    assert list(got) == LEVEL  # one row per metric, in rule 1's order
    assert {k: v for k, (v, _) in got.items()} == EXPECTED
    assert got["full_check_minutes"][1] == "20"  # the kit default line
    assert got["rule_words"][1] == "3" and got["rule_lines"][1] == "1"  # the budget totals
    assert "2026-10-31" in proc.stdout and "2026-11-06" in proc.stdout


def test_ac1_unreadable_responses_are_unknown_never_zero(repo, tmp_path):
    """REQ-054 AC1: rule 2, a value whose inputs cannot be read is `unknown`, never 0."""
    repo.commit({"agk.toml": 'default_branch = "main"\n'})
    api = saved(tmp_path, {"runs-week": {"workflow_runs": "not a list"}, "pulls": {"x": 1}})
    proc = repo.run("scorecard.py", "--today", TODAY, "--api-dir", str(api))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    got = rows(proc.stdout)
    assert list(got) == LEVEL
    for metric, (value, _) in got.items():
        assert value == "unknown", metric
    assert got["rule_words"][1] == "-"  # no budget file: no line, never 0


def test_ac1_one_unreadable_job_list_makes_the_step_unknown(repo, tmp_path):
    """REQ-054 AC1: rule 2, a missing job list is unknown for the metrics that read it."""
    project(repo)
    week = {k: v for k, v in WEEK.items() if k != "run-jobs-2"}
    proc = repo.run("scorecard.py", "--today", TODAY, "--api-dir", str(saved(tmp_path, week)))
    got = rows(proc.stdout)
    assert got["prepush_seconds"][0] == "unknown"
    assert got["ci_minutes_per_merge"][0] == "unknown"
    assert got["full_check_minutes"][0] == "20.0"


def test_ac1_rule_counts_are_not_applicable_without_the_kit_only_reader(tmp_path):
    """REQ-054 AC1: Q-S0047-14, where `rules.py` is absent the rule counts are not applicable."""
    (tmp_path / "CLAUDE.md").write_text("- one rule\n", encoding="utf-8")
    assert scorecard.rule_counts(tmp_path, available=False) == ("not applicable",) * 2
    assert scorecard.rule_counts(tmp_path, available=True) == ("3", "1")
    assert scorecard.rule_counts(tmp_path / "none", available=True) == ("unknown",) * 2


STUB = """#!{python}
import json, sys
with open({log!r}, "a", encoding="utf-8") as out:
    out.write(" ".join(sys.argv[1:]) + "\\n")
endpoint = sys.argv[-1]
if "actions/runs" in endpoint and "/jobs" not in endpoint:
    print(json.dumps({{"total_count": 0, "workflow_runs": []}}))
elif "/jobs" in endpoint:
    print(json.dumps({{"total_count": 0, "jobs": []}}))
elif endpoint.rstrip("/").count("/") == 2:
    print(json.dumps({{"private": True}}))
else:
    print("[]")
"""


def test_ac1_live_reads_are_get_only_and_write_no_file(repo, tmp_path_factory):
    """REQ-054 AC1: rule 2, through a `gh` stub every call is a GET and no file changes."""
    project(repo)
    outside = tmp_path_factory.mktemp("stub")
    bin_dir, log = outside / "bin", outside / "gh.log"
    bin_dir.mkdir()
    stub = bin_dir / "gh"
    stub.write_text(STUB.format(python=sys.executable, log=str(log)), encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    before = snapshot(repo.root)
    path = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
    proc = repo.run("scorecard.py", "--today", TODAY, "--repo", "owner/name", PATH=path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert snapshot(repo.root) == before
    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls and all(c.startswith("api --method GET repos/owner/name") for c in calls), calls
    assert all("owner/name" in c for c in calls)  # the project's own repository only
    assert rows(proc.stdout)["lead_time_hours"][0] == "unknown"  # no pull request: no median


def test_ac1_no_check_gate_or_prepush_step_runs_the_scorecard():
    """REQ-054 AC1: rule 2, no governance check, `make governance` or `prepush.py` step uses it."""
    importer = re.compile(r"^\s*(?:import scorecard|from scorecard import)", re.MULTILINE)
    for path in (KIT / "scripts/agk").glob("*.py"):
        if path.name != "scorecard.py":
            assert not importer.search(path.read_text(encoding="utf-8")), path.name
    named = [KIT / "Makefile", KIT / "agk.mk", KIT / "scripts/agk/prepush.py"]
    named += sorted((KIT / ".github/workflows").glob("*.yml"))
    for path in named:
        assert "scorecard.py" not in path.read_text(encoding="utf-8"), path.name


# --- the [scorecard] setting (rule 3) ----------------------------------------------------------


def root_with(tmp_path: Path, toml: str) -> Path:
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n' + toml, encoding="utf-8")
    return tmp_path


def test_ac2_no_table_gives_the_kit_defaults(tmp_path):
    """REQ-054 AC2: rule 3, without the table every line and window is the kit default."""
    settings = config.scorecard_settings(root_with(tmp_path, ""))
    assert settings["trend_weeks"] == 4 and settings["close_weeks"] == 2
    lines = settings["lines"]
    assert lines["full_check_minutes"] == 20 and lines["prepush_seconds"] == 300
    assert lines["red_hours"] == 4 and lines["flaky_rate"] == 2
    assert lines["fix_list_rate"] == 50 and lines["lead_time_hours"] == 48
    assert lines["restore_hours"] == 4 and lines["ci_minutes_per_merge"] == 30
    assert lines["old_failure_issues"] == 0 and lines["verify_oldest_days"] == 90
    assert lines["residuals_past_due"] == 0 and lines["pins_oldest_gap_days"] == 180
    assert lines["kit_releases_behind"] == 3 and lines["stale_guides"] == 0
    for none in ("rule_words", "rule_lines", "verify_marks", "pins_behind"):
        assert lines[none] is None


def test_ac2_a_table_sets_lines_and_windows(tmp_path):
    """REQ-054 AC2: rule 3, the table's numbers replace the defaults they name."""
    text = "[scorecard]\nred_hours = 6\nflaky_rate = 1.5\ntrend_weeks = 5\nclose_weeks = 3\n"
    settings = config.scorecard_settings(root_with(tmp_path, text))
    assert settings["lines"]["red_hours"] == 6 and settings["lines"]["flaky_rate"] == 1.5
    assert settings["lines"]["lead_time_hours"] == 48
    assert (settings["trend_weeks"], settings["close_weeks"]) == (5, 3)


def test_ac2_the_table_line_reaches_the_printed_table(repo, tmp_path):
    """REQ-054 AC2: rule 3, the printed line is the setting's."""
    project(repo, 'default_branch = "main"\n[scorecard]\nlead_time_hours = 72\n')
    proc = repo.run("scorecard.py", "--today", TODAY, "--api-dir", str(saved(tmp_path, WEEK)))
    assert rows(proc.stdout)["lead_time_hours"] == ("36.0", "72")


@pytest.mark.parametrize(
    ("toml", "setting"),
    [
        (f'scorecard = "{ODD}"\n', "scorecard"),
        (f"[scorecard]\n{ODD.replace('-', '_')} = 1\n", "scorecard"),
        (f'[scorecard]\nred_hours = "{ODD}"\n', "scorecard.red_hours"),
        ("[scorecard]\nred_hours = -7\n", "scorecard.red_hours"),
        ("[scorecard]\nflaky_rate = true\n", "scorecard.flaky_rate"),
        ("[scorecard]\ntrend_weeks = 2.5\n", "scorecard.trend_weeks"),
        ("[scorecard]\nclose_weeks = 0\n", "scorecard.close_weeks"),
    ],
)
def test_ac2_a_bad_table_is_refused_naming_the_setting(tmp_path, toml, setting):
    """REQ-054 AC2: rule 3, refused naming `setting: scorecard.<key>`, never the value."""
    with pytest.raises(config.ScorecardSettingError) as exc:
        config.scorecard_settings(root_with(tmp_path, toml))
    message = str(exc.value)
    assert f"(setting: {setting})" in message
    for value in (ODD, ODD.replace("-", "_"), "-7", "2.5", "true"):
        assert value not in message


def test_ac2_the_script_refuses_a_bad_table_without_the_value(repo, tmp_path):
    """REQ-054 AC2: rule 3, the script prints the refusal and no table."""
    project(repo, 'default_branch = "main"\n[scorecard]\nred_hours = -7\n')
    proc = repo.run("scorecard.py", "--today", TODAY, "--api-dir", str(saved(tmp_path, WEEK)))
    assert proc.returncode == 1
    assert "setting: scorecard.red_hours" in proc.stdout and "-7" not in proc.stdout
    assert rows(proc.stdout) == {}
