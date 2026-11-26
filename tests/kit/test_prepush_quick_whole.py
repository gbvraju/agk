"""A quick prepush runs the whole tests (brief #1971, ADR-0825, REQ-062).

`prepush.py --quick` no longer skips every test: with a `[testing] whole_tests` list and a change
that is not documentation only, the `tests` step runs only the listed files of the head, through
the `[proof]` area each lies in, in one run named `whole` under the heavy-step lock, and prints
`prepush: tests whole ok|FAIL (<s>s): listed in testing.whole_tests`. Proof's own runs, the mapped
and named tests and the full suite stay skipped. Without the table, without the key or with a
documentation-only change the step is `skipped`, naming the reason. `test_plan.py` prints the
`quick:` line and its JSON the `quick_whole` files, and `evidence.py check` replays a quick record.

The fixture repositories are those of `test_prepush_regression.py`: a stand-in `agk.mk`,
`Makefile` and `gitleaks`, the lock folder and the log of what ran outside the work tree.
Invented data only (example.com); no network.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from test_prepush import path_with, scanner
from test_prepush_regression import MAP, RUN_LINE, held, prepush, ran, toml, wide_project

WHOLE = 'whole_tests = ["tests/test_a.py"]\n'
EVIDENCE = re.compile(r"^Evidence check: (agrees|differs)", re.M)


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("outside")


def steps(stdout: str) -> dict[str, str]:
    found = re.findall(r"^prepush: (\S+) (ok|FAIL|skipped) \(", stdout, re.M)
    return dict(found)


def test_quick_runs_only_the_whole_tests_as_one_run_named_whole(repo, outside):
    """REQ-062: brief #1971 answer 1 (only the listed files; a mapped test is not run)."""
    wide_project(repo, toml(outside, testing='profile = "fast"\n' + WHOLE + MAP))
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["kit tests/test_a.py"]
    assert RUN_LINE.findall(proc.stdout) == [("whole", "ok", "listed in testing.whole_tests")]
    assert "--quick: the whole tests only" in proc.stdout
    assert "prepush: all steps passed" in proc.stdout


@pytest.mark.parametrize(
    "testing", ['profile = "thorough"\n', 'profile = "fast"\npr_tests = "full"\n']
)
def test_a_full_selection_still_runs_only_the_list(repo, outside, testing):
    """REQ-062: brief #1971 answer 5 (`profile`, `pr_tests`: a full run is never quick's)."""
    wide_project(repo, toml(outside, testing=testing + WHOLE + MAP))
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["kit tests/test_a.py"]
    assert [r[0] for r in RUN_LINE.findall(proc.stdout)] == ["whole"]


def test_a_documentation_only_change_skips_naming_the_reason(repo, outside):
    """REQ-062: brief #1971 answers 1 and 6 (a change of only `docs/` runs nothing)."""
    text = toml(outside, testing='profile = "fast"\n' + WHOLE + MAP)
    wide_project(repo, text, {"docs/note.md": "# invented\n"})
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == []
    assert steps(proc.stdout)["tests"] == "skipped"
    assert "--quick: only documentation changed" in proc.stdout


def test_no_testing_table_skips_naming_the_table(repo, outside):
    """REQ-062: brief #1971 answer 5 (`[testing]` absent: skipped as today, the reason named)."""
    wide_project(repo, toml(outside, testing=None))
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == []
    assert "--quick: no [testing] table" in proc.stdout
    assert not (outside / "locks").exists()


def test_no_whole_tests_skips_naming_the_setting(repo, outside):
    """REQ-062: brief #1971 answer 5 (`whole_tests` absent: skipped as today)."""
    wide_project(repo, toml(outside))
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == []
    assert steps(proc.stdout)["tests"] == "skipped"
    assert "--quick: testing.whole_tests is not set" in proc.stdout


def test_a_bad_whole_tests_value_is_refused_naming_the_setting(repo, outside):
    """REQ-062: brief #1971 answer 5 (refused before anything runs, never the value)."""
    wide_project(repo, toml(outside, testing='profile = "fast"\nwhole_tests = []\n' + MAP))
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert steps(proc.stdout)["tests"] == "FAIL"
    assert "setting: testing.whole_tests" in proc.stdout
    assert ran(outside) == []


def test_a_failing_whole_test_fails_the_step(repo, outside):
    """REQ-062: brief #1971 answer 6 (a failed whole test stops the run with its output)."""
    area = "echo kit {files} >> LOG; echo INVENTED_FAILURE; exit 1"
    wide_project(repo, toml(outside, area_cmd=area, testing='profile = "fast"\n' + WHOLE + MAP))
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert RUN_LINE.findall(proc.stdout)[0][:2] == ("whole", "FAIL")
    assert "INVENTED_FAILURE" in proc.stdout
    assert "prepush: stopped at tests" in proc.stdout


def test_a_whole_file_in_no_area_is_not_run(repo, outside):
    """REQ-062: brief #1971 answer 6 (in no `[proof]` area: `not run`, as rule 6a)."""
    text = toml(outside, dirs='["tests/billing"]', testing='profile = "fast"\n' + WHOLE + MAP)
    wide_project(repo, text)
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == []
    assert "tests: not run (in no [proof] area): tests/test_a.py" in proc.stdout
    assert "prepush: passed; not run: tests" in proc.stdout


@pytest.mark.parametrize(("args", "seen"), [((), "HELD"), (("--no-lock",), "FREE")])
def test_the_quick_run_holds_the_heavy_lock_unless_no_lock(repo, outside, args, seen):
    """REQ-062: brief #1971 answer 1 (under the heavy-step lock; `--no-lock` as today)."""
    probe = f": {{files}}; test -d {held(outside)} && echo HELD >> LOG || echo FREE >> LOG"
    text = toml(outside, area_cmd=probe, testing='profile = "fast"\n' + WHOLE + MAP)
    wide_project(repo, text)
    proc = prepush(repo, outside, "--quick", *args)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == [seen]


FAKE_PYTHON = """#!/bin/sh
if [ "$1" = "-c" ]; then exit 0; fi
echo "$*" >> {log}
exit 0
"""


def test_workers_give_the_whole_run_n_where_xdist_imports(repo, outside):
    """REQ-062: brief #1971 answer 5 (`workers = 2`: `-n 2`, as `selected_workers` reads it)."""
    python = outside / "fake" / "python3"
    python.parent.mkdir()
    python.write_text(FAKE_PYTHON.replace("{log}", str(outside / "ran.log")), encoding="utf-8")
    python.chmod(0o755)
    area = f"{python} -m pytest {{files}}"
    testing = 'profile = "fast"\nworkers = 2\n' + WHOLE + MAP
    wide_project(repo, toml(outside, area_cmd=area, testing=testing))
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["-m pytest tests/test_a.py -n 2"]


def test_the_plan_names_the_quick_whole_tests(repo, outside):
    """REQ-062: brief #1971 answer 3 (`quick:` in the text, `quick_whole` in the JSON)."""
    wide_project(repo, toml(outside, testing='profile = "fast"\n' + WHOLE + MAP))
    text = repo.run("test_plan.py", "--base", "main")
    assert text.returncode == 0, text.stdout + text.stderr
    lines = text.stdout.splitlines()
    assert "quick: prepush --quick runs these 1 whole test" in lines
    assert lines.index("quick: prepush --quick runs these 1 whole test") > lines.index(
        "whole: tests/test_a.py"
    )
    shown = json.loads(repo.run("test_plan.py", "--json", "--base", "main").stdout)
    assert shown["quick_whole"] == ["tests/test_a.py"]


def test_without_the_list_the_plan_prints_no_quick_line(repo, outside):
    """REQ-062: brief #1971 answer 3 (with none, nothing is printed)."""
    wide_project(repo, toml(outside))
    text = repo.run("test_plan.py", "--base", "main")
    assert text.returncode == 0, text.stdout + text.stderr
    assert "quick:" not in text.stdout
    assert "quick_whole" not in json.loads(
        repo.run("test_plan.py", "--json", "--base", "main").stdout
    )


def check(repo, outside: Path, record: Path, scan: Path):
    temp = outside / "tmp"
    temp.mkdir(exist_ok=True)
    return repo.run(
        "evidence.py",
        "check",
        str(record),
        "--sample",
        "10",
        PATH=path_with(scan),
        TMPDIR=str(temp),
        TMP=str(temp),
    )


def test_a_quick_record_agrees_and_a_changed_whole_run_differs(repo, outside):
    """REQ-062: brief #1971 answer 3 (a quick record is checked as any other run)."""
    wide_project(repo, toml(outside, testing='profile = "fast"\n' + WHOLE + MAP))
    record = outside / "record.json"
    scan = scanner(outside / "bin", 0)
    made = repo.run("prepush.py", "--quick", "--record", str(record), PATH=path_with(scan))
    assert made.returncode == 0, made.stdout + made.stderr
    data = json.loads(record.read_text(encoding="utf-8"))
    tests = next(s for s in data["steps"] if s["name"] == "tests")
    assert [(r["set"], r["name"]) for r in tests["runs"]] == [("whole", "whole")]
    proc = check(repo, outside, record, scan)
    found = EVIDENCE.search(proc.stdout)
    assert found and found.group(1) == "agrees", proc.stdout + proc.stderr
    assert "tests/whole/whole" in proc.stdout
    tests["runs"][0]["command"] = "echo invented"
    record.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    proc = check(repo, outside, record, scan)
    found = EVIDENCE.search(proc.stdout)
    assert found and found.group(1) == "differs", proc.stdout + proc.stderr
    assert "not what prepush runs: tests/whole/whole (field: command)" in proc.stdout
