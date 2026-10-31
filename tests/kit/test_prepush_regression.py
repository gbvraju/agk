"""The pre-push gate runs the selected regression tests too, under the heavy-step lock (brief #417,
ADR-0227).

With a `[testing]` table in `agk.toml`, the `tests` step of `scripts/agk/prepush.py` runs proof's
plan (the pull request's own test files) and then the regression set of `impact.py`: `project_tests`
once when the set is full, otherwise each selected file through the command of the `[proof]` area
it lies in. Each run prints `prepush: tests <area or full> ok|FAIL (<s>s): <reason>`; a selected
file in no area is listed as `not run (in no [proof] area)`. The step holds the heavy-step lock
(`lock.py`, name `heavy`) while it runs; `--no-lock` leaves it out. `--quick` skips every test, and
without a `[testing]` table the step runs exactly as before.

Each fixture repository keeps its lock folder (`lock_dir`) and the log of what ran outside the
work tree, so the tree stays clean and no real lock of the machine is touched.
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from pathlib import Path

import pytest
from test_prepush import LINT_OK, MK_OK, path_with, scanner

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
ROOT = Path(__file__).resolve().parents[2]
MAP = 'map = [ { code = "src/billing/**", tests = ["tests/billing/**"] } ]\n'
RUN_LINE = re.compile(r"^prepush: tests (\S+) (ok|FAIL) \(\d+\.\d+s\): (.+)$", re.M)


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("outside")


def toml(
    outside: Path,
    area_cmd: str = "echo kit {files} >> LOG",
    full_cmd: str = "echo full >> LOG",
    dirs: str = '["tests"]',
    testing: str | None = 'profile = "fast"\n' + MAP,
    proof: bool = True,
) -> str:
    log = str(outside / "ran.log")
    text = (
        'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
        f"project_tests = '{full_cmd.replace('LOG', log)}'\n"
        f"lock_dir = '{outside / 'locks'}'\n"
    )
    if proof:
        cmd = area_cmd.replace("LOG", log)
        area = f"dirs = {dirs}, patterns = [\"test_*.py\"], command = '{cmd}'"
        text += f"[proof]\nkit = {{ {area} }}\n"
    if testing is not None:
        text += "[testing]\n" + testing
    return text


def project(repo, text: str, change: dict[str, str] | None = None) -> None:
    repo.commit(
        {
            "agk.toml": text,
            "agk.mk": MK_OK,
            "Makefile": LINT_OK,
            "src/billing/pay.py": "base\n",
            "src/other.py": "base\n",
            "tests/billing/test_pay.py": "# guards pay\n",
        },
        "base",
    )
    repo.branch("feature")
    repo.commit(change or {"src/billing/pay.py": "change\n"}, "change")


def prepush(repo, outside: Path, *args: str, **env: str):
    return repo.run("prepush.py", *args, PATH=path_with(scanner(outside / "bin", 0)), **env)


def ran(outside: Path) -> list[str]:
    log = outside / "ran.log"
    return log.read_text(encoding="utf-8").splitlines() if log.is_file() else []


def held(outside: Path) -> Path:
    return outside / "locks" / "agk-lock-heavy"


def test_a_mapped_selection_runs_through_its_area_with_its_reason(repo, outside):
    """REQ-016: brief #417 answers 1 and 2 (a mapped selection runs through its [proof] area)."""
    project(repo, toml(outside))
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["kit tests/billing/test_pay.py"]
    runs = RUN_LINE.findall(proc.stdout)
    assert runs == [
        ("kit", "ok", "src/billing/pay.py matches code src/billing/**, tests tests/billing/**")
    ]
    assert "prepush: all steps passed" in proc.stdout


def test_the_pull_requests_own_tests_run_first_then_the_regression_set(repo, outside):
    """REQ-016: brief #417 answer 1 (after proof's runs, the regression set)."""
    change = {"src/billing/pay.py": "change\n", "tests/test_new.py": "# new\n"}
    project(repo, toml(outside), change)
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["kit tests/test_new.py", "kit tests/billing/test_pay.py"]
    reasons = [r[2] for r in RUN_LINE.findall(proc.stdout)]
    assert reasons[0] == "the pull request's own test files (the proof plan)"
    assert reasons[1].startswith("src/billing/pay.py matches code src/billing/**")


def test_a_full_selection_runs_project_tests_once(repo, outside):
    """REQ-016: brief #417 answers 1 and 2 (`full` runs `project_tests` once, with its reason)."""
    testing = 'profile = "balanced"\n' + MAP
    change = {"src/billing/pay.py": "change\n", "src/other.py": "change\n"}
    project(repo, toml(outside, testing=testing), change)
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full"]
    assert RUN_LINE.findall(proc.stdout) == [("full", "ok", "profile balanced: 1 unmapped file")]


def test_always_full_is_the_reason_of_a_full_run(repo, outside):
    """REQ-016: brief #417 answer 2 (the reason is the rule that selected the set)."""
    testing = 'always_full = ["src/billing/**"]\n'
    project(repo, toml(outside, testing=testing))
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full"]
    expected = ("full", "ok", "always_full src/billing/** matches src/billing/pay.py")
    assert RUN_LINE.findall(proc.stdout) == [expected]


def test_without_a_testing_table_the_step_runs_as_before(repo, outside):
    """REQ-016: brief #417 answer 4 (no [testing] table: the step runs exactly as today)."""
    project(repo, toml(outside, testing=None))
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == []  # no test file changed: proof's plan has nothing to run
    assert RUN_LINE.findall(proc.stdout) == []
    assert "tests: nothing to run (the test plan selects no test file)" in proc.stdout
    assert "lock heavy" not in proc.stdout
    assert not (outside / "locks").exists()


def test_a_selected_file_in_no_area_is_listed_never_dropped(repo, outside):
    """REQ-016: brief #417 answer 1 (a selected file in no [proof] area is listed as not run)."""
    project(repo, toml(outside, dirs='["tests/unit"]'))
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == []
    assert "not run (in no [proof] area): tests/billing/test_pay.py" in proc.stdout


def test_a_selection_without_a_proof_table_runs_project_tests_once(repo, outside):
    """REQ-016: brief #417 answer 1, Q-417-3 (no [proof] area can take the files: run more)."""
    project(repo, toml(outside, proof=False))
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full"]
    ((name, result, reason),) = RUN_LINE.findall(proc.stdout)
    assert (name, result) == ("full", "ok")
    assert "no [proof] table" in reason and "src/billing/pay.py matches code" in reason


def test_a_docs_only_change_selects_nothing_and_says_so(repo, outside):
    """REQ-016: brief #417 answer 2 (an empty regression set is said, not hidden)."""
    project(repo, toml(outside), {"docs/note.md": "a note\n"})
    proc = prepush(repo, outside)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == []
    assert "regression: nothing selected (only documentation changed)" in proc.stdout


def test_the_lock_is_held_while_the_tests_run_and_released_on_a_failure(repo, outside):
    """REQ-016: brief #417 answer 3 (the lock taken and released on a failing test)."""
    probe = f"test -d {held(outside)} && echo HELD >> LOG; exit 1"
    project(repo, toml(outside, area_cmd=probe))
    proc = prepush(repo, outside)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert ran(outside) == ["HELD"]
    assert RUN_LINE.findall(proc.stdout)[0][:2] == ("kit", "FAIL")
    assert "prepush: stopped at tests" in proc.stdout
    assert not held(outside).exists()


def test_no_lock_leaves_the_lock_out(repo, outside):
    """REQ-016: brief #417 answer 3 (`--no-lock`, for CI)."""
    probe = f"test -d {held(outside)} && echo HELD >> LOG || echo FREE >> LOG"
    project(repo, toml(outside, area_cmd=probe))
    proc = prepush(repo, outside, "--no-lock")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["FREE"]
    assert "lock heavy" not in proc.stdout


def test_quick_skips_every_test_and_takes_no_lock(repo, outside):
    """REQ-016: brief #417 answer 4 (`--quick` still skips every test)."""
    project(repo, toml(outside, full_cmd="echo full >> LOG; exit 1"))
    proc = prepush(repo, outside, "--quick")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == []
    assert "prepush: tests skipped" in proc.stdout
    assert not (outside / "locks").exists()


def test_a_held_lock_is_waited_for_with_lock_py_lines(repo, outside):
    """REQ-016: brief #417 answer 3 (lock.py's one-line wait messages)."""
    project(repo, toml(outside))
    holder = subprocess.Popen(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            str(SCRIPTS / "lock.py"),
            "run",
            "--name",
            "heavy",
            "--session",
            "other",
            "--",
            sys.executable,
            "-c",
            "import time; time.sleep(3)",
        ],
        cwd=repo.root,
    )
    try:
        deadline = time.monotonic() + 20
        while not held(outside).exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert held(outside).exists()
        proc = prepush(repo, outside)
    finally:
        holder.wait(timeout=30)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert re.search(r"^lock heavy: waiting; held by other \(pid \d+", proc.stdout, re.M)
    assert "lock heavy: taken" in proc.stdout
    assert ran(outside) == ["kit tests/billing/test_pay.py"]
    assert not held(outside).exists()


def test_a_run_under_lock_py_heavy_does_not_wait_for_itself(repo, outside):
    """REQ-016: brief #417 answer 3, Q-417-2 (rule 31's `lock.py run --name heavy -- prepush.py`
    already holds the lock for this run)."""
    project(repo, toml(outside))
    env = {**os.environ, "PATH": path_with(scanner(outside / "bin", 0))}
    for key in ("GITHUB_BASE_REF", "AGK_BASE", "CI"):
        env.pop(key, None)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            str(SCRIPTS / "lock.py"),
            "run",
            "--name",
            "heavy",
            "--session",
            "me",
            "--timeout",
            "5",
            "--",
            sys.executable,
            str(SCRIPTS / "prepush.py"),
        ],
        cwd=repo.root,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "lock heavy: held by this run's caller (lock.py run); not taken again" in proc.stdout
    assert "waiting" not in proc.stdout
    assert ran(outside) == ["kit tests/billing/test_pay.py"]
    assert not held(outside).exists()


def test_the_record_lists_the_regression_runs(repo, outside):
    """REQ-016: brief #417 answer 1 (each run is in the record of brief #374)."""
    project(repo, toml(outside))
    record = outside / "record.json"
    proc = prepush(repo, outside, "--record", str(record))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(record.read_text(encoding="utf-8"))
    entry = next(s for s in data["steps"] if s["name"] == "tests")
    (made,) = entry["runs"]
    assert made["name"] == "kit" and made["set"] == "regression" and made["exit"] == 0
    assert made["reason"].startswith("src/billing/pay.py matches code")
    assert str(outside) not in json.dumps(data)


def test_an_unknown_option_is_still_a_usage_error_and_no_lock_is_listed(repo, outside):
    """REQ-016: brief #417 answer 3 (`--no-lock` is an option; the usage names it)."""
    project(repo, toml(outside))
    proc = repo.run("prepush.py", "--no-locks")
    assert proc.returncode == 2
    assert "--no-lock" in proc.stderr


def test_the_testing_guide_has_a_section_on_the_pre_push_gate():
    """REQ-016: brief #417 answer 5 (`docs/guides/testing.md` gains a section)."""
    text = (ROOT / "docs" / "guides" / "testing.md").read_text(encoding="utf-8")
    assert "## The pre-push gate" in text
    section = text.split("## The pre-push gate", 1)[1]
    for needle in ("--no-lock", "--quick", "heavy", "not run (in no [proof] area)", "full"):
        assert needle in section, needle
    assert "Nothing runs the selection yet" not in text
