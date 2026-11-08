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


# --- the freshness readers (rules 1 and 8, brief #719, build (c)) -------------------------------

FRESH = (
    "verify_marks verify_oldest_days residuals_past_due pins_behind pins_oldest_gap_days "
    "kit_releases_behind stale_guides"
).split()
SHA = "0123456789abcdef0123456789abcdef01234567"
WORKFLOW = f"""jobs:
  one:
    steps:
      - uses: acme/alpha@{SHA}   # v1.0.0
      - uses: acme/alpha/sub@{SHA} # v1.0.0
      - uses: acme/beta@{SHA}  # v2.0.0
      - uses: acme/gamma@{SHA}  # v3.0.0
      - uses: acme/delta@v1
      - uses: ./local-action
"""


def release(tag: str, day: str, **extra) -> dict:
    return {"tag_name": tag, "published_at": f"{day}T12:00:00Z", **extra}


RELEASES = {
    "releases-acme-alpha": [
        release("v1.3.0-rc1", "2026-07-15", prerelease=True),
        release("v1.2.0", "2026-06-30"),
        release("v1.1.0", "2026-03-01"),
        release("v1.0.0", "2026-01-01"),
    ],
    "releases-acme-beta": [release("v2.0.0", "2026-05-01")],
    "kit-releases": [
        release("v0.8.0", "2026-11-01", draft=True),
        release("v0.7.0", "2026-10-20"),
        release("v0.6.0", "2026-10-10"),
        release("v0.5.0", "2026-10-01"),
        release("v0.4.0", "2026-09-01"),
    ],
}  # acme/gamma has no saved response: its upstream answers 404


def dated(repo, files: dict[str, str], day: str) -> None:
    for rel, text in files.items():
        repo.write(rel, text)
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "change", "--date", f"{day}T12:00:00Z")


def fresh_project(repo, plugin: bool = True) -> None:
    project(repo, 'default_branch = "main"\nversion = "0.5.0"\n')
    approved = (
        "# SPEC-0001: a\n\n- Status: Approved\n\nThe route (verify).\n\n## Residual\n\n"
        "- 2026-01-01: a thing (due 2026-02-01).\n- 2026-01-01: later (due 2027-02-01).\n"
    )
    files = {
        "docs/specs/0001-a.md": approved,
        "docs/specs/0002-b.md": "# SPEC-0002: b\n\n- Status: Draft\n\nA guess (verify).\n",
        ".github/workflows/ci.yml": WORKFLOW,
        "pyproject.toml": '[project]\nname = "x"\ndependencies = ["examplepkg==1.0.0", "o>=2"]\n',
        "scripts/agk/tool.py": "# one\n",
        "docs/guides/old.md": "Run `python3 scripts/agk/tool.py --x` and `missing.py`.\n",
        "docs/runs/residuals.md": "# Register\n\n## Open\n\n"
        "- docs/adr/0001-a.md 2026-01-01 | a line | (due 2026-03-01) | open\n",
    }
    if plugin:
        files[".claude-plugin/plugin.json"] = json.dumps(
            {"repository": "https://github.com/kit-owner/kit"}
        )
    dated(repo, files, "2026-08-09")
    spec = approved.replace("The route (verify).", "The route (verify).\nA fact (verify: why).")
    dated(repo, {"docs/specs/0001-a.md": spec, "scripts/agk/tool.py": "# two\n"}, "2026-10-08")
    dated(repo, {"docs/guides/new.md": "See `tool.py`.\n"}, "2026-10-09")


def fresh_rows(stdout: str) -> dict[str, tuple[str, str]]:
    found = {}
    for line in stdout.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] in FRESH:
            found[cells[0]] = (cells[1], cells[2])
    return found


def test_ac5_saved_releases_give_each_freshness_metric(repo, tmp_path):
    """REQ-054 AC5: rules 1 and 8, every freshness metric, in order after the level ones."""
    fresh_project(repo)
    proc = repo.run(
        "scorecard.py", "--today", TODAY, "--api-dir", str(saved(tmp_path, {**WEEK, **RELEASES}))
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    got = fresh_rows(proc.stdout)
    assert list(got) == FRESH
    assert {k: v for k, (v, _) in got.items()} == {
        "verify_marks": "2",  # the Draft spec's mark is not counted
        "verify_oldest_days": "90",  # 2026-08-09 to 2026-11-07, by git blame
        "residuals_past_due": "2",  # one residual bullet and one register line
        "pins_behind": "1",  # alpha two releases behind; beta at the newest; gamma unknown
        "pins_oldest_gap_days": "180",  # 2026-01-01 to 2026-06-30, the prerelease skipped
        "kit_releases_behind": "2",  # v0.6.0 and v0.7.0; the draft skipped
        "stale_guides": "1",  # old.md is older than tool.py; new.md is newer
    }
    assert got["verify_oldest_days"][1] == "90" and got["pins_behind"][1] == "-"
    assert "pins unknown: 2" in proc.stdout  # gamma's 404 and the Python package (verify)
    table = [line.split("|")[1].strip() for line in proc.stdout.splitlines() if "|" in line]
    assert table[2:] == LEVEL + FRESH


def test_ac5_a_newer_release_of_the_same_day_counts_the_pin_as_behind(repo, tmp_path):
    """REQ-054 AC5: rule 8, a pin is behind on its tag; a gap of 0 days is still behind."""
    fresh_project(repo)
    same_day = {
        **RELEASES,
        "releases-acme-beta": [
            {"tag_name": "v2.0.1", "published_at": "2026-05-01T18:00:00Z"},
            release("v2.0.0", "2026-05-01"),
        ],
    }
    proc = repo.run(
        "scorecard.py", "--today", TODAY, "--api-dir", str(saved(tmp_path, {**WEEK, **same_day}))
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    got = fresh_rows(proc.stdout)
    assert got["pins_behind"][0] == "2"  # alpha by 180 days, beta by v2.0.1 of the same day
    assert got["pins_oldest_gap_days"][0] == "180"
    assert scorecard.pin_gap(same_day["releases-acme-beta"], "v2.0.0") == (True, 0)
    assert scorecard.pin_gap(same_day["releases-acme-beta"], "v2.0.1") == (False, 0)


def test_ac5_unreadable_upstreams_are_unknown_never_zero(repo, tmp_path):
    """REQ-054 AC5: rule 8, no readable upstream and no kit repository give `unknown`, never 0."""
    fresh_project(repo, plugin=False)
    proc = repo.run("scorecard.py", "--today", TODAY, "--api-dir", str(saved(tmp_path, WEEK)))
    got = fresh_rows(proc.stdout)
    for metric in ("pins_behind", "pins_oldest_gap_days", "kit_releases_behind"):
        assert got[metric][0] == "unknown", metric
    assert got["verify_marks"][0] == "2" and got["stale_guides"][0] == "1"


def test_ac5_no_default_branch_ref_makes_the_git_readers_unknown(tmp_path):
    """REQ-054 AC5: rule 1, outside a repository the blame and log readers give `unknown`."""
    assert scorecard.default_ref(tmp_path, "main") is None
    assert scorecard.verify_metrics(tmp_path, None, scorecard.date(2026, 11, 7)) == (
        "unknown",
        "unknown",
    )
    assert scorecard.stale_guides(tmp_path, None) == "unknown"


def test_ac5_the_pins_are_the_sha_pinned_uses_lines_and_the_exact_python_pins(repo):
    """REQ-054 AC5: Q-S0047-11, only SHA-pinned `uses:` lines and `==` pins are pins."""
    fresh_project(repo)
    assert scorecard.action_pins(repo.root) == [
        ("acme/alpha", "v1.0.0"),
        ("acme/beta", "v2.0.0"),
    ] + [("acme/gamma", "v3.0.0")]
    assert scorecard.python_pins(repo.root) == ["examplepkg"]


RELEASE_STUB = """#!{python}
import json, sys
with open({log!r}, "a", encoding="utf-8") as out:
    out.write(" ".join(sys.argv[1:]) + "\\n")
endpoint = sys.argv[-1]
saved = {saved!r}
for name, data in saved.items():
    if endpoint.startswith(name):
        print(json.dumps(data))
        sys.exit(0)
if "/releases" in endpoint:
    sys.exit(1)  # a 404
if "actions/runs" in endpoint and "/jobs" not in endpoint:
    print(json.dumps({{"total_count": 0, "workflow_runs": []}}))
elif endpoint.rstrip("/").count("/") == 2:
    print(json.dumps({{"private": True}}))
else:
    print("[]")
"""


def test_ac5_ac7_live_reads_are_one_get_per_upstream_and_nowhere_else(repo, tmp_path_factory):
    """REQ-054 AC5 and AC7: rules 8 and 10, at most one GET per pin, only the project's own
    repository and the upstream release lists are read, and no file changes."""
    fresh_project(repo)
    outside = tmp_path_factory.mktemp("stub")
    bin_dir, log = outside / "bin", outside / "gh.log"
    bin_dir.mkdir()
    answers = {
        "repos/acme/alpha/releases": RELEASES["releases-acme-alpha"],
        "repos/acme/beta/releases": RELEASES["releases-acme-beta"],
        "repos/kit-owner/kit/releases": RELEASES["kit-releases"],
    }
    stub = bin_dir / "gh"
    stub.write_text(
        RELEASE_STUB.format(python=sys.executable, log=str(log), saved=answers), encoding="utf-8"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    before = snapshot(repo.root)
    path = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
    proc = repo.run("scorecard.py", "--today", TODAY, "--repo", "owner/name", PATH=path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert snapshot(repo.root) == before
    calls = log.read_text(encoding="utf-8").splitlines()
    assert all(c.startswith("api --method GET repos/") for c in calls), calls
    upstream = [c for c in calls if "owner/name" not in c]
    assert sorted(c.split()[3].split("?")[0] for c in upstream) == [
        "repos/acme/alpha/releases",
        "repos/acme/beta/releases",
        "repos/acme/gamma/releases",
        "repos/kit-owner/kit/releases",
    ]
    got = fresh_rows(proc.stdout)
    assert got["pins_behind"][0] == "1" and got["kit_releases_behind"][0] == "2"


def test_ac5_a_shallow_clone_dates_nothing(repo, tmp_path_factory):
    """REQ-054 AC5: rule 2, a shallow history cannot date a line, so the ages are `unknown`."""
    fresh_project(repo)
    clone = tmp_path_factory.mktemp("shallow") / "c"
    repo.git("clone", "-q", "--depth", "1", f"file://{repo.root}", str(clone))
    ref = scorecard.default_ref(clone, "main")
    assert ref == "origin/main"
    assert scorecard.verify_metrics(clone, ref, scorecard.date(2026, 11, 7)) == ("2", "unknown")
    assert scorecard.stale_guides(clone, ref) == "unknown"


# --- findings, trends and the issue writer (rules 4, 5 and 7, brief #723, build (d)) -----------

D = scorecard.Decimal
WEEKS_START, WEEKS_END = "<!-- scorecard weeks -->", "<!-- /scorecard weeks -->"


def previous_body(columns: list[str], values: dict[str, list[str]]) -> str:
    """An audit body whose scorecard section holds the earlier weeks (rule 7)."""
    head = "| metric | line | " + " | ".join(columns) + " |"
    rule = "| --- | --- | " + " | ".join("---" for _ in columns) + " |"
    body = [f"| {m} | 3 | " + " | ".join(v) + " |" for m, v in values.items()]
    return "\n".join(["# Drift audit", "", WEEKS_START, head, rule, *body, WEEKS_END, ""])


WRITE_STUB = """#!{python}
import json, sys
with open({log!r}, "a", encoding="utf-8") as out:
    out.write(json.dumps(sys.argv[1:]) + "\\n")
if "POST" in sys.argv:
    print(json.dumps({{"number": 900}}))
else:
    print(json.dumps({{"name": "agk-scorecard"}}))
"""


def quiet_week(scorecard_issues: list[dict]) -> dict:
    """A week with nothing past the kit lines: rule_words 3 at its budget line 3."""
    return {"issues-open": [], "issues-closed": [], "issues-scorecard": scorecard_issues}


def writer(repo, tmp_path_factory, *args: str, toml: str = "", issues=(), previous=None):
    """Run `scorecard.py issues` over saved reads with a `gh` stub that logs every call."""
    project(repo, 'default_branch = "main"\n' + toml)
    outside = tmp_path_factory.mktemp("stub")
    bin_dir, log = outside / "bin", outside / "gh.log"
    bin_dir.mkdir()
    stub = bin_dir / "gh"
    stub.write_text(WRITE_STUB.format(python=sys.executable, log=str(log)), encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    api = outside / "api"
    api.mkdir()
    for name, data in quiet_week(list(issues)).items():
        (api / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    extra = []
    if previous is not None:
        (outside / "previous.md").write_text(previous, encoding="utf-8")
        extra = ["--previous", str(outside / "previous.md")]
    before = snapshot(repo.root)
    path = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
    proc = repo.run(
        "scorecard.py",
        *args,
        "--today",
        TODAY,
        "--repo",
        "owner/name",
        "--api-dir",
        str(api),
        *extra,
        PATH=path,
    )
    assert snapshot(repo.root) == before  # no tracked or untracked file changes
    calls = (
        [json.loads(c) for c in log.read_text(encoding="utf-8").splitlines()]
        if log.exists()
        else []
    )
    return proc, calls


def writes(calls: list[list[str]]) -> list[list[str]]:
    return [c for c in calls if "GET" not in c]


def field(call: list[str], key: str) -> str:
    return next(a.split("=", 1)[1] for a in call if a.startswith(key + "="))


def test_ac3_a_level_finding_is_above_the_line_and_a_trend_is_three_rising_weeks():
    """REQ-054 AC3: rule 4, a level finding above the line; three rising weeks below it are a
    trend finding; an `unknown` week breaks the run; fewer than three known weeks give none."""
    assert scorecard.judge(["5", "25"], D("20")) == "level"
    assert scorecard.judge(["20"], D("20")) is None  # at the line is inside it
    assert scorecard.judge(["1", "2", "3"], D("10")) == "trend"
    assert scorecard.judge(["9", "1", "2", "3"], None) == "trend"  # no line: trend only
    assert scorecard.judge(["1", "unknown", "3"], D("10")) is None
    assert scorecard.judge(["1", "2", "unknown"], D("10")) is None
    assert scorecard.judge(["2", "3"], D("10")) is None
    assert scorecard.judge(["1", "2", "2"], D("10")) is None  # level, not rising
    assert (
        scorecard.judge(["unknown"], D("0")) is None
        and scorecard.judge(["not applicable"], D("0")) is None
    )
    assert scorecard.judge(["1", "2", "3"], D("10"), trend_weeks=2) is None  # outside the window


def test_ac3_two_weeks_inside_the_line_close_and_an_unknown_week_resets_nothing():
    """REQ-054 AC3: rule 5, `close_weeks` known weeks with no finding close the issue."""
    assert scorecard.closable(["30", "5", "6"], D("20"), 2)
    assert not scorecard.closable(["30", "5"], D("20"), 2)
    assert scorecard.closable(["30", "5", "unknown", "6"], D("20"), 2)
    assert scorecard.closable(["5", "6", "unknown"], D("20"), 2)
    assert not scorecard.closable(["1", "2", "3"], D("20"), 2)  # still a trend finding
    assert not scorecard.closable(["unknown", "unknown"], D("20"), 2)


def test_ac3_the_issue_decision_is_one_issue_per_metric():
    """REQ-054 AC3: rule 5, as `drift_audit.choose_action` keeps the decision in the script."""
    assert scorecard.choose_issue([], finding=True, close=False) == "create"
    assert scorecard.choose_issue([44, 41], finding=True, close=False) == "comment 41"
    assert scorecard.choose_issue([41], finding=False, close=True) == "close 41"
    assert scorecard.choose_issue([41], finding=False, close=False) == "none"
    assert scorecard.choose_issue([], finding=False, close=True) == "none"


def test_ac3_a_level_finding_opens_one_labelled_issue_of_numbers(repo, tmp_path_factory):
    """REQ-054 AC3: rules 4 and 5, a value above its line opens one `agk-scorecard` issue."""
    proc, calls = writer(repo, tmp_path_factory, "issues", toml="[scorecard]\nrule_words = 2\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    made = writes(calls)
    issues = [c for c in made if "repos/owner/name/issues" in c]
    assert len(issues) == 1, made
    assert field(issues[0], "title") == "scorecard: rule_words"
    assert field(issues[0], "labels[]") == "agk-scorecard"
    body = field(issues[0], "body")
    assert "kind: level" in body and "value: 3" in body and "scorecard.rule_words" in body
    assert "builder" not in body and "reviewer" not in body and "@" not in body
    assert "POST" in issues[0] and "issue: create rule_words" in proc.stdout


def test_ac3_a_second_week_comments_and_opens_no_second_issue(repo, tmp_path_factory):
    """REQ-054 AC3: rule 5, an open issue of the metric gets one comment, never a twin."""
    open_one = [
        {"number": 41, "title": "scorecard: rule_words", "labels": [{"name": "agk-scorecard"}]}
    ]
    proc, calls = writer(
        repo, tmp_path_factory, "issues", toml="[scorecard]\nrule_words = 2\n", issues=open_one
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    made = writes(calls)
    assert [c for c in made if "repos/owner/name/issues/41/comments" in c] and len(made) == 1, made
    assert "issue: comment 41 rule_words" in proc.stdout


def test_ac3_ac6_a_trend_below_the_line_is_read_from_the_previous_body(repo, tmp_path_factory):
    """REQ-054 AC3 and AC6: rule 7, two earlier weeks from the audit body and this week rise."""
    previous = previous_body(["2026-10-24", "2026-10-31"], {"rule_words": ["1", "2"]})
    proc, calls = writer(repo, tmp_path_factory, "issues", previous=previous)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    created = [c for c in writes(calls) if "repos/owner/name/issues" in c]
    assert len(created) == 1 and "kind: trend" in field(created[0], "body")


def test_ac3_two_quiet_weeks_close_the_open_issue(repo, tmp_path_factory):
    """REQ-054 AC3: rule 5, two weeks inside the line close the metric's issue as completed."""
    open_one = [
        {"number": 41, "title": "scorecard: rule_words", "labels": [{"name": "agk-scorecard"}]}
    ]
    previous = previous_body(["2026-10-31"], {"rule_words": ["3"]})
    proc, calls = writer(repo, tmp_path_factory, "issues", issues=open_one, previous=previous)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    made = writes(calls)
    assert len(made) == 1 and "PATCH" in made[0] and "repos/owner/name/issues/41" in made[0], made
    assert field(made[0], "state") == "closed" and field(made[0], "state_reason") == "completed"


def test_ac3_a_planted_token_is_withheld_with_counts_only():
    """REQ-054 AC3: rule 5, the guard scan withholds a text that holds anything but numbers."""
    plain = "scorecard: rule_words\nkind: level\nvalue: 3\n"
    assert scorecard.guarded(plain) == (plain, "")
    text, note = scorecard.guarded(plain + "planted someone@corp.invalid\n")
    assert text is None and note == "withheld: EMAIL 1"
    assert "someone" not in note


def test_ac3_a_previous_body_gives_numbers_only(tmp_path):
    """REQ-054 AC3 and AC6: rule 5, a cell of the previous body that is not a number is
    `unknown`, so no text of the body reaches an issue."""
    previous = previous_body(["2026-10-31"], {"rule_words": ["someone@corp.invalid"]})
    got = scorecard.history(previous, scorecard.date(2026, 11, 7), 4)
    assert got["rule_words"] == ["unknown", "unknown", "unknown"]


def test_ac4_a_clean_week_writes_nothing(repo, tmp_path_factory):
    """REQ-054 AC4: rules 4 and 5, every metric inside its line and no run of three: no
    finding, no writing call of the stub and no file."""
    proc, calls = writer(repo, tmp_path_factory, "issues")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert writes(calls) == []
    assert "findings: 0" in proc.stdout


def test_ac4_findings_prints_and_calls_nothing(repo, tmp_path_factory):
    """REQ-054 AC4: `findings` prints the section and the findings and runs no `gh` at all."""
    proc, calls = writer(repo, tmp_path_factory, "findings", toml="[scorecard]\nrule_words = 2\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls == []
    assert (
        "findings: 1" in proc.stdout and "finding: rule_words level value 3 line 2" in proc.stdout
    )


def test_ac6_the_new_section_keeps_four_weeks_and_drops_the_oldest(tmp_path):
    """REQ-054 AC6: rule 7, a previous body with four weeks gives a section of the last four."""
    columns = ["2026-10-10", "2026-10-17", "2026-10-24", "2026-10-31"]
    previous = previous_body(columns, {"rule_words": ["9", "1", "2", "3"]})
    today = scorecard.date(2026, 11, 7)
    earlier = scorecard.history(previous, today, 4)
    assert earlier["rule_words"] == ["1", "2", "3"]
    assert earlier["full_check_minutes"] == ["unknown"] * 3  # a row that is missing
    section = scorecard.weeks_section(
        today, {"rule_words": "3"}, {"rule_words": [*earlier["rule_words"], "4"]}
    )
    lines = section.splitlines()
    assert lines[0] == WEEKS_START and lines[-1] == WEEKS_END
    assert lines[1] == "| metric | line | 2026-10-17 | 2026-10-24 | 2026-10-31 | 2026-11-07 |"
    assert "| rule_words | 3 | 1 | 2 | 3 | 4 |" in lines
    again = scorecard.history(section, scorecard.date(2026, 11, 14), 4)
    assert again["rule_words"] == ["2", "3", "4"]  # the next week drops 2026-10-17


def test_ac6_a_missing_previous_body_gives_unknown_weeks_and_no_trend():
    """REQ-054 AC6: rule 7, no previous body: every earlier week is `unknown`."""
    got = scorecard.history(None, scorecard.date(2026, 11, 7), 4)
    assert set(map(tuple, got.values())) == {("unknown",) * 3}
    assert scorecard.judge([*got["rule_words"], "3"], D("10")) is None


def test_ac7_the_writer_calls_only_the_project_repository(repo, tmp_path_factory):
    """REQ-054 AC7: rule 10, every call of the writer names the project's own repository."""
    proc, calls = writer(repo, tmp_path_factory, "issues", toml="[scorecard]\nrule_words = 2\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    endpoints = [next(a for a in c if a.startswith("repos/")) for c in calls]
    assert endpoints and all(e.startswith("repos/owner/name/") for e in endpoints), endpoints
