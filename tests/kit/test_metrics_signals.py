"""Tests of the signals of use (brief #2054, ADR-0852; REQ-012).

Every shipped decision names one signal of use in `config/signals.toml`; the weekly metrics report
lists each built feature whose signal shows zero use in 14 days, `unknown` whenever a read it needs
was not answered, and the steward's Daily list carries the unused ones to the owner. Invented data
only (example.com); no network: saved answers under `tests/kit/fixtures/metrics/signals-*/` or
`tmp_path`, read through a stub source that records every call; no model.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from datetime import date
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / "scripts" / "agk"))

import brief_study  # noqa: E402
import metrics  # noqa: E402
import steward_daily  # noqa: E402

MIXED = KIT / "tests" / "kit" / "fixtures" / "metrics" / "signals-mixed"
END = date(2026, 12, 28)  # the window end of `--today 2026-12-28`
REGISTRY = KIT / "config" / "signals.toml"  # read by each test, never at collection
SHIPPED = object()  # `project`'s default: the shipped registry


def plugin_toml() -> str:
    """A clean project's settings that pin the running plugin's version (read per test)."""
    version = tomllib.loads((KIT / "agk.toml").read_text(encoding="utf-8"))["version"]
    return (
        f'version = "{version}"\n[flow]\nmerge_queue = false\n'
        f'[kit]\nlayout = "plugin"\nplugin_version = "{version}"\n'
    )


def shipped() -> str:
    return REGISTRY.read_text(encoding="utf-8")


HEAD = 'from = "2026-11-27"\n'


class Recorder:
    """Saved answers (`metrics.ApiDir`) that record every read by name."""

    def __init__(self, path: Path) -> None:
        self.api = metrics.ApiDir(path)
        self.calls: list[str] = []

    def get(self, name: str, endpoint: str, until=None):
        self.calls.append(name)
        return self.api.get(name, endpoint, until)

    def why(self, name: str):
        return self.api.why(name)


def project(tmp_path: Path, signals: object = SHIPPED, toml: str = "") -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "agk.toml").write_text(toml or "[flow]\nmerge_queue = false\n", encoding="utf-8")
    if signals is not None:
        text = shipped() if signals is SHIPPED else str(signals)
        (root / "config" / "signals.toml").write_text(text, encoding="utf-8")
    return root


def api(tmp_path: Path, answers: dict | None = None) -> Path:
    """A copy of the mixed fixture with ANSWERS (name: JSON, or None to remove) applied."""
    path = tmp_path / "api"
    shutil.copytree(MIXED, path)
    for name, data in (answers or {}).items():
        if data is None:
            (path / f"{name}.json").unlink()
        else:
            (path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    return path


def lines(root: Path, src, **kw) -> list[str]:
    return metrics.signal_lines(root, src, kw.pop("end", END), **kw)


def row(rid: str, kind: str, **fields: str) -> str:
    body = "".join(f"{k} = '{v}'\n" for k, v in fields.items())
    feature = fields.pop("feature", None) or "ADR-0001"
    since = "2026-11-01"
    text = f"[[signal]]\nid = '{rid}'\nkind = '{kind}'\n{body}"
    if "feature" not in body:
        text += f"feature = '{feature}'\n"
    if "since" not in body:
        text += f"since = '{since}'\n"
    return text


def comment(cid: int, issue: int, when: str, body: str) -> dict:
    url = f"https://api.github.com/repos/example/demo/issues/{issue}"
    return {"id": cid, "issue_url": url, "created_at": when, "body": body}


# --- the mixed fixture: each kind used, unused and unknown --------------------------------------


def test_req_012_the_mixed_fixture_reads_two_used_three_unused_one_unknown(tmp_path):
    src = Recorder(MIXED)
    out = lines(project(tmp_path), src)
    assert (
        out[0] == "signals: 9 declared; used 2; unused 5; new 0; unknown 1; no runtime use 1 "
        "(14 days to 2026-12-28)"
    )
    assert out[1:6] == [
        "unused: short-jobs (ADR-0586): 0 in 14 days (comment)",
        "unused: merge-queue (ADR-0417): 0 in 14 days (run); off by flow.merge_queue",
        "unused: unused-on-owner-list (ADR-0852): 0 in 14 days (comment)",
        "unused: ground-run (ADR-0875): 0 in 14 days (comment)",
        "unused: lesson-prevent (ADR-0873): 0 in 14 days (comment)",  # brief #2098
    ]
    assert out[6] == "unknown: tests-selected (ADR-0348): unknown (refused) (log)"
    assert out[7] == "signals: decisions since 2026-11-27 with no row: none"
    counted = [c for c in src.calls if c != "rate_limit"]
    assert len(counted) <= metrics.SIGNAL_CALLS
    assert counted == [
        "signal-runs-pull_request",
        "run-jobs-501",
        "job-log-5010",
        "comments-signals",
        "signal-runs-merge_group",
    ]


def test_req_012_a_matching_log_and_a_counted_run_are_used(tmp_path):
    stamp = "2026-12-20T09:01:00.0000000Z "
    path = api(
        tmp_path,
        {
            "job-log-5010": f"{stamp}tests: mode selected, 3 test files\n",
            "signal-runs-merge_group": {"total_count": 2, "workflow_runs": [{"id": 9}]},
        },
    )
    out = lines(project(tmp_path, toml="[flow]\nmerge_queue = true\n"), Recorder(path))
    assert out[0].startswith("signals: 9 declared; used 4; unused 4; new 0; unknown 0; ")
    assert not any("merge-queue" in x or "tests-selected" in x for x in out)


def test_req_012_a_log_whose_step_did_not_run_is_unknown(tmp_path):
    jobs = {
        "jobs": [{"id": 5010, "steps": [{"name": "Tests of the checks", "conclusion": "skipped"}]}]
    }
    out = lines(project(tmp_path), Recorder(api(tmp_path, {"run-jobs-501": jobs})))
    assert "unknown: tests-selected (ADR-0348): unknown (no step run) (log)" in out


def test_req_012_a_run_read_that_failed_is_unknown_never_zero(tmp_path):
    failed = {"message": "Not Found", "status": "404"}
    out = lines(project(tmp_path), Recorder(api(tmp_path, {"signal-runs-merge_group": failed})))
    assert "unknown: merge-queue (ADR-0417): unknown (refused) (run)" in out
    assert not any(x.startswith("unused: merge-queue") for x in out)


def test_req_012_the_hourly_limit_leaves_the_unread_rows_unknown(tmp_path):
    signals = (
        HEAD
        + row("a-comment", "comment", pattern="^Report: ")
        + row("b-run", "run", event="merge_group")
    )
    path = api(tmp_path, {"rate_limit": {"resources": {"core": {"remaining": 1}}}})
    src = Recorder(path)
    out = lines(project(tmp_path, signals), src)
    assert out[0].startswith("signals: 2 declared; used 1; unused 0; new 0; unknown 1 ")
    assert "unknown: b-run (ADR-0001): unknown (hourly limit) (run)" in out
    assert not any("0 in 14 days" in x for x in out)
    assert [c for c in src.calls if c != "rate_limit"] == ["comments-signals"]


def test_req_012_a_row_shipped_inside_the_window_or_after_it_is_new(tmp_path):
    signals = HEAD + row("inside", "run", event="merge_group", since="2026-12-20")
    signals += row("later", "run", event="merge_group", since="2027-01-05")
    src = Recorder(MIXED)
    out = lines(project(tmp_path, signals), src)
    assert out[0].startswith("signals: 2 declared; used 0; unused 0; new 2; unknown 0 ")
    assert [c for c in src.calls if c != "rate_limit"] == []


def test_req_012_then_counts_only_a_start_followed_on_its_own_issue(tmp_path):
    talk = [
        comment(
            1,
            1,
            "2026-12-15T09:00:00Z",
            "Started: cb1 2026-12-15T09:00:00Z by the supervisor (fix)",
        ),
        comment(2, 2, "2026-12-15T10:00:00Z", "Report: aaa ready for review"),  # another issue
        comment(3, 3, "2026-12-16T09:00:00Z", "Report: bbb ready for review"),  # before the start
        comment(
            4,
            3,
            "2026-12-16T10:00:00Z",
            "Started: cb3 2026-12-16T10:00:00Z by the supervisor (build)",
        ),
    ]
    path = api(tmp_path, {"comments-signals": talk})
    out = lines(project(tmp_path), Recorder(path))
    assert "unused: short-jobs (ADR-0586): 0 in 14 days (comment)" in out
    talk.append(comment(5, 3, "2026-12-16T11:00:00Z", "Report: ccc ready for review"))
    path = api(tmp_path / "again", {"comments-signals": talk})
    out = lines(project(tmp_path / "again"), Recorder(path))
    assert not any("short-jobs" in x for x in out)


def test_req_012_the_off_by_ending_names_the_setting_never_its_value(tmp_path):
    out = lines(project(tmp_path, toml="[review]\n"), Recorder(MIXED))
    unused = [x for x in out if x.startswith("unused: merge-queue")]
    assert unused == ["unused: merge-queue (ADR-0417): 0 in 14 days (run); off by flow.merge_queue"]
    assert not any("false" in x for x in out)


# --- the settings -------------------------------------------------------------------------------


def test_req_012_no_registry_prints_none_declared_and_reads_nothing(tmp_path):
    src = Recorder(MIXED)
    assert lines(project(tmp_path, None), src) == ["signals: none declared (path class: config/)"]
    assert src.calls == []


REFUSED = [
    ("not toml [", "file"),
    ('from = "soon"\n', "from"),
    (HEAD + row("x", "bell", pattern="a"), "kind"),
    (HEAD + row("x", "comment"), "pattern"),
    (HEAD + row("x", "log", pattern="a"), "step"),
    (HEAD + row("x", "run"), "event"),
    (HEAD + row("x", "none"), "reason"),
    (HEAD + row("x", "comment", pattern="(unclosed"), "pattern"),
    (HEAD + row("x", "comment", pattern="a" * 201), "pattern"),
    (HEAD + row("x", "comment", pattern="a", then="[z"), "then"),
    (HEAD + row("x", "comment", pattern="a") + row("x", "comment", pattern="b"), "id"),
    (HEAD + row("Bad_Id", "comment", pattern="a"), "id"),
    (HEAD + row("x", "comment", pattern="a", feature="spec 7"), "feature"),
    (HEAD + row("x", "comment", pattern="a", since="soon"), "since"),
    (HEAD + row("x", "comment", pattern="a", setting="flow.nope"), "setting"),
    (HEAD + row("x", "comment", pattern="a", setting="nope"), "setting"),
]


@pytest.mark.parametrize(("signals", "field"), REFUSED)
def test_req_012_a_broken_registry_is_refused_naming_the_field(tmp_path, signals, field):
    out = lines(project(tmp_path, signals), Recorder(MIXED))
    assert out == [f"signals: refused (field: {field})"]
    assert "spec 7" not in out[0] and "nope" not in out[0]


def test_req_012_a_known_setting_and_a_top_level_key_are_accepted(tmp_path):
    signals = HEAD + row("x", "none", reason="a wording decision", setting="execution")
    signals += row("y", "none", reason="a wording decision", setting="flow.merge_queue")
    out = lines(project(tmp_path, signals), Recorder(MIXED))
    assert out[0].startswith(
        "signals: 2 declared; used 0; unused 0; new 0; unknown 0; no runtime use 2 "
    )


def test_req_012_local_execution_leaves_log_and_run_rows_unknown(tmp_path):
    src = Recorder(MIXED)
    out = lines(project(tmp_path, toml='execution = "local"\n'), src)
    assert "unknown: tests-selected (ADR-0348): unknown (setting: execution) (log)" in out
    assert "unknown: merge-queue (ADR-0417): unknown (setting: execution) (run)" in out
    assert [c for c in src.calls if c != "rate_limit"] == ["comments-signals"]


def git(root: Path, *args: str, when: str = "2026-12-20T09:00:00Z") -> str:
    env = {"GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when, "PATH": "/usr/bin:/bin"}
    env |= {"GIT_CONFIG_GLOBAL": "/dev/null", "HOME": str(root)}
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return proc.stdout


def test_req_012_a_personal_forge_reads_commit_rows_only(tmp_path):
    signals = HEAD + row("tagged", "commit", pattern="^Signal-tag: yes")
    signals += row("quiet", "commit", pattern="^Never-written: ") + row(
        "talk", "comment", pattern="a"
    )
    root = project(tmp_path, signals, toml='[personal]\nforge = "files"\n')
    git(root, "init", "-q", "-b", "main")
    git(
        root,
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "old\n\nNever-written: x",
        when="2026-11-02T09:00:00Z",
    )
    git(root, "commit", "-q", "--allow-empty", "-m", "a change\n\nSignal-tag: yes")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    src = Recorder(MIXED)
    out = lines(root, src)
    assert out[0].startswith("signals: 3 declared; used 1; unused 1; new 0; unknown 1 ")
    assert "unused: quiet (ADR-0001): 0 in 14 days (commit)" in out
    assert "unknown: talk (ADR-0001): unknown (setting: forge) (comment)" in out
    assert src.calls == []


def test_req_012_a_saved_checklist_serves_comment_and_run_rows(tmp_path):
    saved = {
        "saved_at": "2026-12-28T00:00:00Z",
        "days": 14,
        "comments": json.loads((MIXED / "comments-signals.json").read_text()),
        "runs": [{"name": "merge", "event": "merge_group", "created_at": "2026-12-20T09:00:00Z"}],
    }
    signals = (
        HEAD
        + row("light", "comment", pattern=r"light re-prove")
        + row("queue", "run", event="merge_group")
    )
    src = Recorder(tmp_path / "none")
    out = lines(project(tmp_path, signals), src, saved=saved)
    assert out[0].startswith("signals: 2 declared; used 2; unused 0; new 0; unknown 0 ")
    assert [c for c in src.calls if c != "rate_limit"] == []
    out = lines(project(tmp_path / "short", signals), src, saved=saved | {"days": 7})
    assert "unknown: light (ADR-0001): unknown (saved window 7 days) (comment)" in out
    assert "unknown: queue (ADR-0001): unknown (saved window 7 days) (run)" in out


def test_req_012_decisions_since_from_with_no_row_are_listed(tmp_path):
    root = project(tmp_path, HEAD + row("x", "none", reason="r", feature="ADR-0901"))
    adr = root / "docs" / "adr"
    adr.mkdir(parents=True)
    for number, day in (
        (900, "2026-11-26"),
        (901, "2026-11-27"),
        (902, "2026-11-28"),
        (903, "2026-12-01"),
    ):
        (adr / f"{number:04d}-a-decision.md").write_text(
            f"# ADR-{number:04d}: x\n\n- Date: {day}\n"
        )
    (adr / "TEMPLATE.md").write_text("- Date: 2026-12-01\n")
    out = lines(root, Recorder(MIXED))
    assert out[-1] == "signals: decisions since 2026-11-27 with no row: ADR-0902, ADR-0903"


# --- the shipped registry and the closed class --------------------------------------------------


def test_req_012_the_shipped_registry_passes_and_names_real_decisions(tmp_path):
    out = lines(project(tmp_path), Recorder(MIXED))
    assert not out[0].startswith("signals: refused")
    data = tomllib.loads(shipped())
    for item in data["signal"]:
        feature = item["feature"]
        if feature.startswith("ADR-"):
            assert list((KIT / "docs" / "adr").glob(f"{feature[4:]}-*.md")), feature
        else:
            assert re.fullmatch(r"brief #\d+", feature), feature
    ids = {item["id"] for item in data["signal"]}
    assert {"tests-selected", "light-reprove", "short-jobs", "usage-figure", "merge-queue"} <= ids
    assert "unused-on-owner-list" in ids


def test_req_012_the_class_stays_closed():
    assert metrics.SIGNAL_KINDS == ("log", "comment", "run", "commit", "none")
    assert all(item["kind"] in metrics.SIGNAL_KINDS for item in tomllib.loads(shipped())["signal"])
    readers = {
        p.name
        for p in (KIT / "scripts").rglob("*.py")
        if re.search(r"(?<![\w-])signals\.toml", p.read_text(encoding="utf-8"))
    }
    assert readers == {"metrics.py"}


def test_req_012_the_weekly_report_carries_the_section_after_the_packs(tmp_path):
    text = (KIT / "scripts" / "agk" / "metrics.py").read_text(encoding="utf-8")
    packs = r"\*stale_pack_lines\(ctx\.root, today\),.*\n"
    assert re.search(packs + r"(?:\s*\*parts_report_lines\(.*\n)?\s*\*signal_lines\(", text)


# --- the command line and the plugin layout -----------------------------------------------------


def cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT / "scripts" / "agk" / "metrics.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_req_012_signals_runs_from_the_plugin_on_the_projects_registry(tmp_path):
    root = project(tmp_path, toml=plugin_toml())
    git(root, "init", "-q", "-b", "main")
    proc = cli(root, "--signals", "--today", "2026-12-28", "--api-dir", str(MIXED))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("signals: 9 declared; used 2; unused 5; new 0; unknown 1;")
    assert not list(root.rglob("*.json"))


def test_req_012_saved_goes_with_signals_only(tmp_path):
    assert cli(tmp_path, "--saved", str(tmp_path / "x.json")).returncode == 2
    assert cli(tmp_path, "--signals", "--print-title").returncode == 2


# --- the owner's Daily list ---------------------------------------------------------------------


def daily(issues: list[dict] | None) -> str:
    return steward_daily.daily_text(date(2026, 12, 29), [date(2026, 12, 28)], [], [], issues)


def weekly(number: int, week: str, *extra: str) -> dict:
    body = "\n".join(["agk metrics", *extra, f"<!-- agk-metrics {week} -->"])
    return {"number": number, "created_at": "2026-12-28T06:00:00Z", "body": body}


def test_req_012_the_daily_list_carries_each_unused_line():
    issues = [
        weekly(70, "2026-W51", "unused: old-one (ADR-0001): 0 in 14 days (run)"),
        weekly(
            81,
            "2026-W52",
            "unused: short-jobs (ADR-0586): 0 in 14 days (comment)",
            "unused: merge-queue (ADR-0417): 0 in 14 days (run); off by flow.merge_queue",
        ),
        weekly(80, "2026-W52", "unused: duplicate (ADR-0002): 0 in 14 days (run)"),
    ]
    text = daily(issues)
    assert "Built but unused: short-jobs (ADR-0586)" not in text
    assert "Built but unused: duplicate (ADR-0002)" in text  # the one choose_action updates
    assert "old-one" not in text
    text = daily(issues[:2])
    assert (
        "Built but unused: short-jobs (ADR-0586)\nBuilt but unused: merge-queue (ADR-0417)" in text
    )


def test_req_012_the_daily_list_says_none_or_unknown():
    assert "Built but unused: none (agk metrics 2026-W52)" in daily(
        [weekly(81, "2026-W52", "signals: 1 declared")]
    )
    assert "Built but unused: unknown" in daily(
        [{"number": 5, "created_at": "x", "body": "a brief"}]
    )
    assert "Built but unused: unknown" in daily(None)


# --- new briefs name their signal ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("measured", "warned"),
    [
        ("Measured: before: x fails; after: y passes", True),
        ("Measured: before: x; after: y. Signal: tests-selected", False),
        ("Measured: before: x; after: y; signal: none (a wording change)", False),
        ("Measured: before: signal: tests-selected; after: y passes", True),
    ],
)
def test_req_012_a_measured_line_with_no_signal_warns_and_never_fails(tmp_path, measured, warned):
    (tmp_path / "agk.toml").write_text('[flow]\nbrief_study_fails_from = "2026-01-01"\n')
    body = f"Sentence: x\n{measured}\n"
    text = "study: the Measured line names no signal (signal: <id> or signal: none (<reason>))"
    assert brief_study.signal_problems(body.splitlines()) == ([text] if warned else [])
    failures, warnings = brief_study.study_result(body, tmp_path, briefs=[], today="2026-12-01")
    assert text not in failures
    assert (text in warnings) is warned
