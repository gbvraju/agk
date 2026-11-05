"""Per-file test timing in the record, the manifest and the readers (SPEC-0044 rules 1 to 3,
brief #560, build (a) of REQ-051).

The kit adds no flag to a project's test command. For a pytest run it reads the durations table
that pytest prints when the project's command passes `--durations=0`; for any runner it reads the
JUnit XML report at the path `[testing] junit` names, relative to the run's folder. With neither,
the timing is `unknown`; a report that cannot be read is `unknown` with one line naming the
setting. `prepush.py --record` writes a `timing` object on each run of the tests step, which
`evidence.py` accepts and never compares; `proof.py --manifest` gives one timing line per run;
`lock.py status --ticket` prints one separate `timing` line after a result whose record holds a
total, leaving the `result` line and the estimate unchanged. Saved outputs and files in
`tmp_path` only: no network, no install, invented data.
"""

from __future__ import annotations

import json
import os
import sys
import types
from datetime import UTC, datetime
from pathlib import Path

import heavy_queue
import impact
import prepush
import proof
import pytest
from common import CheckError
from test_prepush import path_with, project, scanner

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import evidence  # noqa: E402

DURATIONS = """\
tests/test_a.py ..s
tests/test_b.py .
============================== slowest durations ===============================
2.00s call     tests/test_a.py::test_slow
0.50s setup    tests/test_a.py::test_slow
0.25s teardown tests/test_a.py::test_slow
1.25s call     tests/test_b.py::TestThing::test_one
0.01s call     tests/test_a.py::test_quick

(3 durations < 0.005s hidden.  Use -vv to show these durations.)
========================= 3 passed, 1 skipped in 4.20s =========================
"""
NO_DURATIONS = "tests/test_a.py ..\n=== 2 passed in 0.10s ===\n"
JUNIT_FILE = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="3">
<testcase classname="tests.test_a" name="test_x" file="tests/test_a.py" time="1.5"/>
<testcase classname="tests.test_a" name="test_y" file="tests/test_a.py" time="0.5"/>
<testcase classname="tests.test_b" name="test_z" file="tests/test_b.py" time="3"/>
</testsuite></testsuites>
"""
JUNIT_CLASSNAME = """<testsuite name="spec">
<testcase classname="checkout flow" name="pays" time="0.75"/>
<testcase classname="checkout flow" name="refunds" time="0.25"/>
<testcase classname="login" name="signs in" time="2.0"/>
</testsuite>
"""
JUNIT_DOCTYPE = """<?xml version="1.0"?>
<!DOCTYPE t [<!ENTITY e "x">]>
<testsuite><testcase classname="a" file="t.py" time="1"/></testsuite>
"""
SINCE = 0.0  # a report written by the fixture is always newer than this


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- rule 2: where per-file timing comes from --------------------------------------------------


def test_the_durations_table_sums_call_setup_and_teardown_by_file():
    """REQ-051 AC1: SPEC-0044 rule 2 (a saved pytest output with the durations table)."""
    timing, note = impact.run_timing(DURATIONS, Path("."), None, SINCE)
    assert note is None
    assert timing == {
        "source": "durations",
        "total_seconds": 4.01,
        "files": [
            {"path": "tests/test_a.py", "seconds": 2.76},
            {"path": "tests/test_b.py", "seconds": 1.25},
        ],
    }


def test_without_a_durations_table_or_a_report_the_timing_is_unknown():
    """REQ-051 AC1: SPEC-0044 rule 2 (neither source: unknown, with no line)."""
    timing, note = impact.run_timing(NO_DURATIONS, Path("."), None, SINCE)
    assert timing == {"source": "unknown", "total_seconds": None, "files": []}
    assert note is None


def test_a_junit_report_sums_by_its_file_attribute(tmp_path):
    """REQ-051 AC1: SPEC-0044 rule 2 (a JUnit report with `file`, read before durations)."""
    write(tmp_path, "reports/junit.xml", JUNIT_FILE)
    timing, note = impact.run_timing(DURATIONS, tmp_path, "reports/junit.xml", SINCE)
    assert note is None
    assert timing == {
        "source": "junit",
        "total_seconds": 5.0,
        "files": [
            {"path": "tests/test_b.py", "seconds": 3.0},
            {"path": "tests/test_a.py", "seconds": 2.0},
        ],
    }


def test_a_junit_report_without_file_sums_by_classname(tmp_path):
    """REQ-051 AC1: SPEC-0044 rule 2 (a JUnit report with only `classname`)."""
    write(tmp_path, "junit.xml", JUNIT_CLASSNAME)
    timing, _ = impact.run_timing("", tmp_path, "junit.xml", SINCE)
    assert timing["source"] == "junit"
    assert timing["files"] == [
        {"path": "login", "seconds": 2.0},
        {"path": "checkout flow", "seconds": 1.0},
    ]
    assert timing["total_seconds"] == 3.0


@pytest.mark.parametrize(
    "text",
    ["<testsuite><testcase time='1'", "<testsuite><testcase time='soon'/></testsuite>", JUNIT_DOCTYPE],
    ids=["truncated", "bad-time", "doctype"],
)
def test_a_report_that_cannot_be_parsed_is_unknown_with_one_line(tmp_path, text):
    """REQ-051 AC1: SPEC-0044 rule 2 (a malformed report: unknown, one line naming the setting;
    a document type declaration is refused, never expanded)."""
    write(tmp_path, "junit.xml", text)
    timing, note = impact.run_timing(DURATIONS, tmp_path, "junit.xml", SINCE)
    assert timing == {"source": "unknown", "total_seconds": None, "files": []}
    assert note == impact.JUNIT_UNREADABLE
    assert "setting: testing.junit" in note and "junit.xml" not in note


def test_a_missing_report_falls_back_to_durations_or_is_unknown_with_one_line(tmp_path):
    """REQ-051 AC1: SPEC-0044 rule 2 (a missing report; a report older than the run counts as
    missing, so a stale file never gives a run's timing)."""
    timing, note = impact.run_timing(DURATIONS, tmp_path, "junit.xml", SINCE)
    assert timing["source"] == "durations" and note is None
    timing, note = impact.run_timing(NO_DURATIONS, tmp_path, "junit.xml", SINCE)
    assert timing["source"] == "unknown" and note == impact.JUNIT_MISSING
    old = write(tmp_path, "junit.xml", JUNIT_FILE)
    os.utime(old, (1_000_000, 1_000_000))
    timing, note = impact.run_timing(NO_DURATIONS, tmp_path, "junit.xml", 2_000_000.0)
    assert timing["source"] == "unknown" and note == impact.JUNIT_MISSING


def test_at_most_fifty_files_are_kept_slowest_first_and_the_total_counts_all():
    """REQ-051 AC1: SPEC-0044 rule 3 (`files`: slowest first, at most 50)."""
    lines = [f"{n / 100:.2f}s call     tests/test_{n:02d}.py::test_x" for n in range(1, 61)]
    output = "==== slowest durations ====\n" + "\n".join(lines) + "\n==== 60 passed ====\n"
    timing, _ = impact.run_timing(output, Path("."), None, SINCE)
    assert len(timing["files"]) == 50
    assert timing["files"][0] == {"path": "tests/test_60.py", "seconds": 0.6}
    assert timing["files"][-1]["path"] == "tests/test_11.py"
    assert timing["total_seconds"] == round(sum(n / 100 for n in range(1, 61)), 3)


# --- rule 1: the junit key is optional and a bad one is refused --------------------------------


def with_testing(repo, extra: str) -> None:
    repo.commit({"agk.toml": f'default_branch = "main"\n[testing]\n{extra}'}, "base")


@pytest.mark.parametrize("value", ["5", '""', '"/abs/junit.xml"', '"../junit.xml"', "true"])
def test_a_malformed_junit_setting_is_refused_naming_the_setting(repo, value):
    """REQ-051 AC2: SPEC-0044 rule 1 (a malformed key names the setting, never the value)."""
    with_testing(repo, f"junit = {value}\n")
    with pytest.raises(CheckError) as caught:
        impact.testing_table(repo.root)
    assert "(setting: testing.junit)" in str(caught.value)
    assert "abs" not in str(caught.value)


def test_the_junit_setting_is_optional_and_leaves_the_table_unchanged(repo):
    """REQ-051 AC2: SPEC-0044 rule 1 (with the key absent nothing changes)."""
    with_testing(repo, 'profile = "fast"\n')
    before = impact.testing_table(repo.root)
    assert impact.junit_setting(repo.root) is None
    with_testing(repo, 'profile = "fast"\njunit = "reports/junit.xml"\n')
    assert impact.testing_table(repo.root) == before
    assert impact.junit_setting(repo.root) == "reports/junit.xml"


def test_without_the_key_prepush_prints_nothing_new_and_records_unknown(repo, tmp_path):
    """REQ-051 AC2: SPEC-0044 rules 1 and 3 (no new key: the same lines; the record says
    unknown, and nothing fails because timing is missing)."""
    project(repo)
    record = tmp_path / "record.json"
    proc = repo.run(
        "prepush.py", "--record", str(record), PATH=path_with(scanner(tmp_path / "bin", 0))
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "timing" not in proc.stdout and "junit" not in proc.stdout.lower()
    tests = next(s for s in json.loads(record.read_text())["steps"] if s["name"] == "tests")
    assert [r["timing"] for r in tests["runs"]] == [
        {"source": "unknown", "total_seconds": None, "files": []}
    ]


# --- rule 3: the record ------------------------------------------------------------------------


def test_each_regression_run_of_the_record_carries_its_timing(repo, monkeypatch, tmp_path):
    """REQ-051 AC1: SPEC-0044 rule 3 (the `timing` object on a run of the tests step, from the
    run's durations table and from its JUnit report)."""
    repo.commit(
        {
            "agk.toml": (
                'default_branch = "main"\nproject_tests = "FULL"\n'
                '[testing]\nprofile = "thorough"\njunit = "out/junit.xml"\n'
            )
        },
        "base",
    )

    def execute(command, cwd, timeout, env=None):
        write(cwd, "out/junit.xml", JUNIT_FILE)
        return 0, DURATIONS, 1

    monkeypatch.setattr(prepush, "execute", execute)
    found = impact.Impact(table=True, profile="thorough", full=True, reason="profile thorough")
    step = prepush.gate(repo.root, [], found, None, 900, prepush.Ran([], Path("."), 0, "{}"))
    assert step.outcome == "ok"
    (made,) = step.runs
    assert made["timing"]["source"] == "junit"
    assert made["timing"]["total_seconds"] == 5.0


def test_an_unreadable_report_prints_one_line_and_changes_no_outcome(
    repo, monkeypatch, capsys
):
    """REQ-051 AC1: SPEC-0044 rules 2 and 3 (one line naming the setting; the run stays ok)."""
    repo.commit(
        {"agk.toml": 'project_tests = "FULL"\n[testing]\nprofile = "thorough"\njunit = "j.xml"\n'}
    )

    def execute(command, cwd, timeout, env=None):
        write(cwd, "j.xml", "<not xml")
        return 0, "", 1

    monkeypatch.setattr(prepush, "execute", execute)
    monkeypatch.setattr(prepush, "time", types.SimpleNamespace(monotonic=lambda: 1.0))
    found = impact.Impact(table=True, profile="thorough", full=True, reason="profile thorough")
    step = prepush.gate(repo.root, [], found, None, 900, prepush.Ran([], Path("."), 0, "{}"))
    out = capsys.readouterr().out
    assert step.outcome == "ok"
    assert out.count(impact.JUNIT_UNREADABLE) == 1
    assert step.runs[0]["timing"]["source"] == "unknown"


def evidence_record(path: Path, repo, timing: dict | None) -> Path:
    run = {"name": "full", "command": "FULL", "cwd": ".", "exit": 0}
    if timing is not None:
        run["timing"] = timing
    tests = {
        "name": "tests", "outcome": "ok", "not_run": False, "argv": ["python3"], "cwd": ".",
        "exit": 0, "seconds": 1.0, "output_sha256": "0" * 64, "output_bytes": 0, "runs": [run],
    }
    record = {
        "schema": 1, "head": repo.git("rev-parse", "HEAD").strip(),
        "base": repo.git("rev-parse", "HEAD").strip(), "started": "2026-11-05T00:00:00Z",
        "tree_clean": True, "steps": [tests], "not_run": [], "result": "passed",
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "timing",
    [
        None,
        {"source": "unknown", "total_seconds": None, "files": []},
        {"source": "durations", "total_seconds": 2.5, "files": [{"path": "t.py", "seconds": 2.5}]},
    ],
    ids=["without", "unknown", "durations"],
)
def test_evidence_accepts_a_record_with_and_without_timing(repo, tmp_path, timing):
    """REQ-051 AC1: SPEC-0044 rule 3 (a record without `timing` and one with it both load)."""
    repo.commit({"a.txt": "a\n"})
    record, _ = evidence.load(evidence_record(tmp_path / "r.json", repo, timing))
    assert record["schema"] == 1


@pytest.mark.parametrize(
    "timing",
    [
        "fast",
        {"source": "guess", "total_seconds": 1, "files": []},
        {"source": "junit", "total_seconds": "1", "files": []},
        {"source": "junit", "total_seconds": 1, "files": [{"path": 3, "seconds": 1}]},
    ],
)
def test_evidence_refuses_a_malformed_timing_naming_the_field(repo, tmp_path, timing):
    """REQ-051 AC1: SPEC-0044 rule 3 (the one optional field has one form; never its value)."""
    repo.commit({"a.txt": "a\n"})
    with pytest.raises(evidence.Usage) as caught:
        evidence.load(evidence_record(tmp_path / "r.json", repo, timing))
    assert "(field: steps)" in str(caught.value)


# --- rule 3: the manifest ----------------------------------------------------------------------


def test_the_manifest_has_one_timing_line_per_run_in_both_forms():
    """REQ-051 AC1: SPEC-0044 rule 3 (`- timing: <total> s over <n> files (<source>)` or
    `- per-file timing: unknown`)."""
    known = proof.Run("backend", ["tests/test_a.py"], "pytest", ".", seconds=[1, 4])
    known.timing = {"source": "durations", "total_seconds": 4.01, "count": 2}
    unknown = proof.Run("frontend", ["a.test.ts"], "npm test", "fe", seconds=[1, 2])
    third = proof.Run("kit", ["tests/test_b.py"], "pytest", ".", seconds=[None, 3])
    third.outcome = "passed"
    third.timing = {"source": "junit", "total_seconds": 3.0, "count": 1}
    assert "- timing: 4.0 s over 2 files (durations)" in proof.ran_lines(known)
    assert "- per-file timing: unknown" in proof.ran_lines(unknown)
    assert "- timing: 3.0 s over 1 files (junit)" in proof.regression_lines(third)
    for lines in (proof.ran_lines(known), proof.ran_lines(unknown)):
        assert sum("timing" in line for line in lines) == 1


def test_proof_times_the_head_run_from_its_output(monkeypatch, tmp_path):
    """REQ-051 AC1: SPEC-0044 rule 3 (proof reads the head run's output, never adds a flag)."""
    outputs = iter([(1, NO_DURATIONS, 1), (0, DURATIONS, 2)])
    commands: list[str] = []

    def execute(command, cwd, timeout, env=None):
        commands.append(command)
        return next(outputs)

    monkeypatch.setattr(proof, "execute", execute)
    monkeypatch.setattr(proof, "show", lambda label, out: None)
    run = proof.Run("project_tests", ["tests/test_a.py"], "pytest -q", ".")
    trees = [tmp_path / "base", tmp_path / "head"]
    for tree in trees:
        tree.mkdir()
    proof.run_pair(trees, run, 60)
    assert commands == ["pytest -q", "pytest -q"]
    assert run.timing == {"source": "durations", "total_seconds": 4.01, "count": 2}


# --- rule 3: the status line, with the result line and the estimate unchanged -------------------


def queue_with(folder: Path, result: dict) -> Path:
    box = folder / "q"
    for sub in ("jobs", "results"):
        (box / sub).mkdir(parents=True, exist_ok=True)
    (box / "results" / f"{result['ticket']}.json").write_text(json.dumps(result), encoding="utf-8")
    return box


def prepush_record(path: Path, totals: list[float | None]) -> Path:
    runs = [
        {"name": f"r{n}", "timing": {"source": "durations" if t else "unknown",
                                      "total_seconds": t, "files": []}}
        for n, t in enumerate(totals)
    ]
    path.write_text(json.dumps({"schema": 1, "steps": [{"name": "tests", "runs": runs}]}))
    return path


SETTINGS = {"queue_order": "fifo", "queue_max_wait": 120}
TICKET = "heavy-000001-beef"


def a_result(**extra) -> dict:
    return {"schema": 1, "ticket": TICKET, "head": "e" * 40, "kind": "prepush",
            "outcome": "passed", "run_seconds": 61, **extra}


def test_status_prints_a_separate_timing_line_after_a_result_whose_record_holds_a_total(
    tmp_path,
):
    """REQ-051 AC1: SPEC-0044 rule 3 (`  timing <total> s (<source>)` on its own line, after the
    result line, which stays byte for byte SPEC-0040 rule 7's)."""
    record = prepush_record(tmp_path / "record.json", [30.5, None, 12.25])
    box = queue_with(tmp_path, a_result(record=str(record)))
    plain = queue_with(tmp_path / "plain", a_result())
    lines, code = heavy_queue.status_lines(box, SETTINGS, 1, datetime.now(UTC), TICKET)
    (only,), _ = heavy_queue.status_lines(plain, SETTINGS, 1, datetime.now(UTC), TICKET)
    assert code == 0
    assert lines == [f"result {TICKET} passed head {'e' * 12} in 61s", "  timing 42.8 s (durations)"]
    assert only == lines[0]


@pytest.mark.parametrize("record", [None, "missing.json", "unknown.json", "broken.json"])
def test_status_prints_nothing_more_without_a_total(tmp_path, record):
    """REQ-051 AC1: SPEC-0044 rule 3 (no record, a missing or broken one, or one with no total:
    the result line alone; nothing fails)."""
    prepush_record(tmp_path / "unknown.json", [None])
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    extra = {} if record is None else {"record": str(tmp_path / record)}
    box = queue_with(tmp_path, a_result(**extra))
    lines, code = heavy_queue.status_lines(box, SETTINGS, 1, datetime.now(UTC), TICKET)
    assert code == 0 and lines == [f"result {TICKET} passed head {'e' * 12} in 61s"]


def test_the_estimate_ignores_timing_and_stays_the_median_of_run_seconds(tmp_path):
    """REQ-051 AC1: SPEC-0044 rule 3 and `Q-S0044-9` (the estimate is unchanged)."""
    record = prepush_record(tmp_path / "record.json", [9999.0])
    past = [a_result(ticket=f"heavy-00000{n}-beef", run_seconds=60 * n, record=str(record))
            for n in range(1, 4)]
    bare = [{k: v for k, v in r.items() if k != "record"} for r in past]
    job = {"ticket": "heavy-000009-beef", "kind": "prepush", "seq": 9}
    now = datetime.now(UTC)
    assert heavy_queue.estimate([job], past, 1, now) == heavy_queue.estimate([job], bare, 1, now)
    assert heavy_queue.estimate([job], past, 1, now) == 2
