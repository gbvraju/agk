"""Results from any runner, per level: timing, a rerun alone and a strike (SPEC-0055 rules 8 and 9).

REQ-062 AC5, brief #806, build (f). A level's `junit` (a path or a glob, relative to its `cwd`) or
else `[testing] junit` is the one report read. It feeds `impact.run_timing`, `failures.failed_tests`
and a level's `rerun`, a command with `{id}`, under `[testing] rerun_alone`. Saved reports and
invented data only (example.com); no network, no install, and the fixture runners are `sh` scripts.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import failures
import impact
import prepush

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
LEDGER = "docs/runs/flakes.md"
PLAIN = "shop.example.com.Cart::adds an item"

PYTEST_REPORT = """<?xml version="1.0"?><testsuites><testsuite name="pytest">
<testcase classname="tests.test_shop.TestPay" name="test_card[2]" time="0.2">
<failure message="AssertionError: assert 3 == 4">trace</failure></testcase>
</testsuite></testsuites>"""


def report(classname: str, name: str, seconds: str = "0.5", failed: bool = True) -> str:
    """A saved report in the form a runner other than pytest writes."""
    body = '<failure message="expected 3 to be 4">trace</failure>' if failed else ""
    return (
        '<?xml version="1.0"?><testsuites><testsuite name="vitest">'
        f'<testcase classname="{classname}" name="{name}" time="{seconds}">{body}</testcase>'
        "</testsuite></testsuites>"
    )


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# Rule 8: the report feeds timing.


def test_a_glob_of_reports_gives_the_timing_of_all(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 8 (a folder of reports, hence the glob)."""
    write(tmp_path / "out/a.xml", report("shop.Cart", "adds", "1.5"))
    write(tmp_path / "out/b.xml", report("shop.Cart", "drops", "0.5"))
    write(tmp_path / "out/c.xml", report("shop.Pay", "pays", "2"))
    timing, note = impact.run_timing("", tmp_path, "out/*.xml", 0)
    assert note is None
    assert timing["source"] == "junit"
    assert timing["total_seconds"] == 4.0
    assert {f["path"]: f["seconds"] for f in timing["files"]} == {"shop.Cart": 2.0, "shop.Pay": 2.0}


def test_a_report_older_than_the_run_is_not_read_through_a_glob(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 8 (SPEC-0044 rule 2 holds for a glob)."""
    old = write(tmp_path / "out/a.xml", report("shop.Cart", "adds"))
    os.utime(old, (1_000_000, 1_000_000))
    timing, note = impact.run_timing("", tmp_path, "out/*.xml", 2_000_000)
    assert timing["source"] == "unknown"
    assert note == impact.JUNIT_MISSING


def test_a_level_with_no_report_has_timing_unknown_and_nothing_fails(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 8 (no report, no second line, no refusal)."""
    timing, note = impact.run_timing("all green\n", tmp_path, None, 0)
    assert (timing["source"], timing["total_seconds"], timing["files"]) == ("unknown", None, [])
    assert note is None


def areas() -> list[dict]:
    return [
        {
            "name": "web",
            "levels": [
                {"name": "unit", "junit": "out/*.xml"},
                {"name": "e2e", "junit": None},
            ],
        }
    ]


def test_the_report_of_a_run_is_its_level_s_or_else_the_setting(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 8 (a level's `junit`, else `[testing] junit`)."""
    assert impact.report_of(areas(), "web:unit", "all.xml") == "out/*.xml"
    assert impact.report_of(areas(), "web:e2e", "all.xml") == "all.xml"
    assert impact.report_of(areas(), "web:e2e", None) is None
    assert impact.report_of(areas(), "other", "all.xml") == "all.xml"
    assert impact.report_of(None, "web:unit", "all.xml") == "all.xml"


def test_the_prepush_record_reads_the_report_of_the_level(tmp_path, monkeypatch):
    """REQ-062 AC5: SPEC-0055 rule 8 (`impact.run_timing` is fed a level's report in a real run)."""
    write(tmp_path / "agk.toml", 'default_branch = "main"\n')
    level = {
        "name": "unit",
        "command": "run {files}",
        "when": ["pr", "main"],
        "env": [],
        "dirs": ["web"],
        "patterns": ["*.test.js"],
        "cwd": ".",
        "junit": "out/*.xml",
        "rerun": None,
    }
    area = {
        "name": "web",
        "dirs": ["web"],
        "patterns": ["*.test.js"],
        "command": "run {files}",
        "cwd": ".",
        "levels": [level],
    }

    def execute(command, folder, limit, env=None):
        write(folder / "out/a.xml", report("shop.Cart", "adds", "1.5", failed=False))
        return 0, "", False

    monkeypatch.setattr(prepush, "execute", execute)
    found = impact.Impact(
        table=True,
        profile="balanced",
        full=False,
        reason=None,
        selected=[impact.Selected("web/a.test.js", "src/a.js", "src/**", ["web/*"])],
    )
    ran = prepush.Ran([], tmp_path, 0, "")
    step = prepush.gate(tmp_path, [], found, [area], 60, ran)
    assert [r["name"] for r in step.runs] == ["web:unit"]
    assert step.runs[0]["timing"]["source"] == "junit"
    assert step.runs[0]["timing"]["total_seconds"] == 1.5


# Rule 8: the report feeds the failed-test ids and the signature.


def test_a_report_of_another_runner_gives_classname_and_name():
    """REQ-062 AC5: SPEC-0055 rule 8 (`<classname>::<name>`, Q-S0055-9)."""
    data = report("shop.example.com.Cart", "adds an item").encode()
    assert failures.junit_failures(data) == [(PLAIN, "expected 3 to be 4")]


def test_a_report_of_pytest_keeps_pytest_s_id():
    """REQ-062 AC5: SPEC-0055 rule 8 (pytest's own form, Q-S0055-9)."""
    assert failures.junit_failures(PYTEST_REPORT.encode())[0][0] == (
        "tests/test_shop.py::TestPay::test_card[2]"
    )


def test_pytest_s_id_can_be_asked_for_whatever_the_suite_is_called():
    """REQ-062 AC5: SPEC-0055 rule 9 (a pytest rerun as today, under a renamed suite)."""
    data = PYTEST_REPORT.replace('name="pytest"', 'name="shop"').encode()
    assert failures.junit_failures(data)[0][0] == "tests.test_shop.TestPay::test_card[2]"
    assert failures.junit_failures(data, pytest=True)[0][0] == (
        "tests/test_shop.py::TestPay::test_card[2]"
    )


def test_failed_tests_reads_every_report_of_a_list(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 8 (`failures.failed_tests` over a glob's reports)."""
    first = write(tmp_path / "a.xml", report("shop.Cart", "adds"))
    second = write(tmp_path / "b.xml", report("shop.Pay", "pays"))
    found = failures.failed_tests("", [first, second])
    assert [t for t, _ in found] == ["shop.Cart::adds", "shop.Pay::pays"]


def test_an_empty_list_of_reports_falls_back_to_the_output():
    """REQ-062 AC5: SPEC-0055 rule 8 (a run with no report reads as it does today)."""
    assert failures.failed_tests("FAILED a.py::b - boom\n", []) == [("a.py::b", "boom")]


def test_the_signature_command_reads_a_glob(tmp_path, monkeypatch, capsys):
    """REQ-062 AC5: SPEC-0055 rule 8 (the failure signature needs no pytest)."""
    write(tmp_path / "agk.toml", 'default_branch = "main"\n[testing]\njunit = "out/*.xml"\n')
    write(tmp_path / "out/a.xml", report("shop.Cart", "adds"))
    write(tmp_path / "output.txt", "1 failed\n")
    monkeypatch.chdir(tmp_path)
    assert failures.main(["signature", "--output", "output.txt"]) == 0
    expected = failures.signature("shop.Cart::adds", "expected 3 to be 4")
    assert capsys.readouterr().out.split("\n")[0] == f"{expected} shop.Cart::adds"


# Rule 9: a level's `rerun`, end to end through project_tests.py.

RUN = """#!/bin/sh
mkdir -p out
{report}exit 1
"""
AGAIN = """#!/bin/sh
printf '%s\\n' "$1" >> again.txt
exit {code}
"""


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )


def level_project(
    tmp_path: Path,
    reports: dict[str, str] | None,
    rerun: bool = True,
    alone_code: int = 0,
    switch: str = "true",
    junit: str = 'junit = "out/*.xml"\n',
    setting: str = "",
) -> Path:
    root = tmp_path / "proj"
    made = "".join(
        f"cat > out/{name} <<'XML'\n{text}\nXML\n" for name, text in (reports or {}).items()
    )
    write(root / "run.sh", RUN.format(report=made))
    write(root / "again.sh", AGAIN.format(code=alone_code))
    write(root / "src/a.js", "export const a = 1;\n")
    write(root / "web/a.test.js", "// names src/a.js\n")
    write(root / ".gitignore", "out/\nagain.txt\ndocs/runs/\n")
    level_rerun = 'rerun = "sh again.sh {id}"\n' if rerun else ""
    write(
        root / "agk.toml",
        'default_branch = "main"\nproject_tests = "sh run.sh"\n'
        'test_dirs = ["web"]\ntest_patterns = ["*.test.js"]\n'
        f'[testing]\npr_tests = "selected"\nrerun_alone = {switch}\n{setting}'
        'map = [{ code = "src/**", tests = ["web/*.test.js"] }]\n'
        '[proof.web]\ndirs = ["web"]\npatterns = ["*.test.js"]\n'
        'command = "sh run.sh {files}"\ncwd = "."\n'
        '[proof.web.levels.unit]\ncommand = "sh run.sh {files}"\nwhen = ["pr", "main"]\n'
        f"{junit}{level_rerun}",
    )
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "checkout", "-q", "-b", "change")
    write(root / "src/a.js", "export const a = 2;\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change")
    return root


def run_tests(root: Path, *args: str):
    env = {k: v for k, v in os.environ.items() if k not in ("AGK_SESSION", "GITHUB_STEP_SUMMARY")}
    env.update(EVENT="pull_request", AGK_BASE="main")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "project_tests.py"), *args],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def again(root: Path) -> list[str]:
    path = root / "again.txt"
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def ledger(root: Path) -> str:
    path = root / LEDGER
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def test_a_level_s_rerun_passes_alone_and_writes_one_strike(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 9 (a pass alone is one strike, with no pytest)."""
    root = level_project(tmp_path, {"a.xml": report("shop.Cart", "adds")})
    proc = run_tests(root)
    assert proc.returncode == 0, proc.stdout
    assert again(root) == ["shop.Cart::adds"]
    assert "shop.Cart::adds" in ledger(root)
    expected = failures.signature("shop.Cart::adds", "expected 3 to be 4")
    assert f"project tests: failure signature {expected} shop.Cart::adds" in proc.stdout


def test_a_level_s_rerun_that_fails_alone_is_a_real_failure(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 9 (a failure alone is a real failure; no strike)."""
    root = level_project(tmp_path, {"a.xml": report("shop.Cart", "adds")}, alone_code=1)
    proc = run_tests(root)
    assert proc.returncode == 1
    assert "rerun alone: shop.Cart::adds failed again" in proc.stdout
    assert ledger(root) == ""


def test_a_level_without_rerun_exits_as_today(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 9 (without `rerun`, any other runner exits as today)."""
    root = level_project(tmp_path, {"a.xml": report("shop.Cart", "adds")}, rerun=False)
    proc = run_tests(root)
    assert proc.returncode == 1
    assert again(root) == []
    assert ledger(root) == ""
    assert "rerun alone" not in proc.stdout


def test_a_level_with_no_report_has_no_rerun_and_no_strike(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 8 (no report: no rerun, no strike, its own exit code)."""
    root = level_project(tmp_path, None)
    proc = run_tests(root)
    assert proc.returncode == 1
    assert again(root) == []
    assert ledger(root) == ""


def test_a_level_s_failed_lines_in_the_output_are_not_a_report(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 8 (a level's ids come from its report alone)."""
    root = level_project(tmp_path, None)
    script = (root / "run.sh").read_text(encoding="utf-8")
    write(root / "run.sh", script.replace("exit 1", "echo 'FAILED shop.Cart::adds - x'\nexit 1"))
    proc = run_tests(root)
    assert proc.returncode == 1
    assert again(root) == []


def test_the_rerun_needs_the_setting(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 9 (`rerun` works under `[testing] rerun_alone` only)."""
    root = level_project(tmp_path, {"a.xml": report("shop.Cart", "adds")}, switch="false")
    proc = run_tests(root)
    assert proc.returncode == 1
    assert again(root) == []


def test_more_than_ten_failed_tests_exits_as_today(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 9 (the limit of ten holds for a level)."""
    reports = {f"r{n}.xml": report("shop.Cart", f"case{n}") for n in range(11)}
    root = level_project(tmp_path, reports)
    proc = run_tests(root)
    assert proc.returncode == 1
    assert again(root) == []
    assert "11 failed tests, more than 10" in proc.stdout


def test_a_test_id_reaches_the_rerun_as_one_word(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 9 (an id from a report is never read as shell syntax)."""
    name = "adds; touch injected"
    root = level_project(tmp_path, {"a.xml": report("shop.Cart", name)})
    proc = run_tests(root)
    assert proc.returncode == 0, proc.stdout
    assert again(root) == [f"shop.Cart::{name}"]
    assert not (root / "injected").exists()


def test_the_level_falls_back_to_the_testing_junit_setting(tmp_path):
    """REQ-062 AC5: SPEC-0055 rule 8 (else `[testing] junit`)."""
    root = level_project(
        tmp_path,
        {"a.xml": report("shop.Cart", "adds")},
        junit="",
        setting='junit = "out/*.xml"\n',
    )
    proc = run_tests(root)
    assert proc.returncode == 0, proc.stdout
    assert again(root) == ["shop.Cart::adds"]
