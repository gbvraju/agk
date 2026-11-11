"""Parallel test workers with the same result (SPEC-0044 rules 4 to 7, brief #583, build (b) of
REQ-051).

`[testing] workers` is 1 by default, `"auto"` or a positive whole number. With more than one, the
full run of a pytest command gains `-n <workers>` only when `import xdist` succeeds with that
command's interpreter in the run's folder; otherwise it runs single with one line. A non-pytest
command takes `[testing] parallel_command` for the full run, or runs single with one line. A
`[proof]` area's command is never replaced. A kit fixture project, invented, carries a fake `xdist`
on its own path, and its single and parallel runs give the same counts and exit code. `doctor.py
--record FILE` prints one information line for a slow single-process full run. Fake interpreters
and files in `tmp_path` only: no network, no install, invented data.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import doctor
import impact
import prepush
import pytest
from common import CheckError, proof_areas

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "workers"
NO_XDIST = (
    "tests: pytest-xdist is not importable, running in one process (setting: testing.workers)"
)
COUNT = re.compile(r"(\d+) (passed|failed|skipped)")


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout


def tree(tmp_path: Path, project: str, testing: str | None, proof: str = "") -> Path:
    """An invented project in a git repository with one commit."""
    root = tmp_path / "proj"
    root.mkdir()
    text = (
        'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
        f"project_tests = '{project}'\n{proof}"
    )
    if testing is not None:
        text += "[testing]\n" + testing
    (root / "agk.toml").write_text(text, encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "Builder")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def interpreter(folder: Path, xdist: bool) -> Path:
    """A fake `python3` that answers `-c "import xdist"` with or without the plugin."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "python3"
    path.write_text(f"#!/bin/sh\nexit {0 if xdist else 1}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture(autouse=True)
def fresh_memory():
    """Each test reads free memory afresh (`impact.MEMORY` holds one reading per process)."""
    impact.MEMORY.clear()
    yield
    impact.MEMORY.clear()


def full(root: Path) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    found = impact.Impact(table=True, profile="balanced", full=True, reason="always")
    return prepush.regression_sets(root, found, None)


# --- rule 1: nothing changes without the keys; a malformed key is refused ------------------------


@pytest.mark.parametrize("testing", [None, 'profile = "balanced"\n', "workers = 1\n"])
def test_without_workers_the_full_command_is_unchanged(tmp_path, testing, capsys):
    """REQ-051 AC2: SPEC-0044 rule 1 (no key, or `workers = 1`: the command of today, no line)."""
    root = tree(tmp_path, "python3 -m pytest -q", testing)
    sets, notes = full(root)
    assert sets == [("full", "python3 -m pytest -q", ".", "always")]
    assert notes == []
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("line", "setting"),
    [
        ("workers = 0\n", "testing.workers"),
        ('workers = "many"\n', "testing.workers"),
        ("workers = true\n", "testing.workers"),
        ("workers = -2\n", "testing.workers"),
        ('parallel_command = ""\n', "testing.parallel_command"),
        ("parallel_command = 3\n", "testing.parallel_command"),
        ("slow_suite_seconds = 0\n", "testing.slow_suite_seconds"),
        ('slow_suite_seconds = "x"\n', "testing.slow_suite_seconds"),
    ],
)
def test_a_malformed_key_is_refused_naming_the_setting(tmp_path, line, setting):
    """REQ-051 AC2: SPEC-0044 rules 1 and 4 (`0`, `"many"` and other bad values refused)."""
    root = tree(tmp_path, "python3 -m pytest -q", line)
    with pytest.raises(CheckError) as caught:
        impact.testing_table(root)
    assert f"(setting: {setting})" in str(caught.value)
    assert "many" not in str(caught.value)


# --- rule 4: parallel workers for pytest --------------------------------------------------------


def test_workers_above_one_add_n_when_the_interpreter_imports_xdist(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 4 (`workers = 4`, a fake interpreter with xdist: `-n 4`)."""
    python = interpreter(tmp_path / "with", xdist=True)
    root = tree(tmp_path, f"{python} -m pytest -q", "workers = 4\n")
    sets, notes = full(root)
    assert sets[0][1] == f"{python} -m pytest -q -n 4"
    assert notes == []


def test_without_xdist_the_run_is_single_with_one_line(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 4 (a fake interpreter without xdist: unchanged, one line)."""
    python = interpreter(tmp_path / "without", xdist=False)
    root = tree(tmp_path, f"{python} -m pytest -q", "workers = 4\n")
    sets, notes = full(root)
    assert sets[0][1] == f"{python} -m pytest -q"
    assert notes == [NO_XDIST]


def test_a_bare_pytest_is_checked_with_python3_on_the_path(tmp_path, monkeypatch):
    """REQ-051 AC2: SPEC-0044 rule 4 (a bare `pytest` checks `python3`)."""
    folder = tmp_path / "bin"
    interpreter(folder, xdist=True)
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    root = tree(tmp_path, "AGK_FLAG=1 pytest -q tests", "workers = 3\n")
    assert full(root)[0][0][1] == "AGK_FLAG=1 pytest -q tests -n 3"


def test_auto_takes_the_cpu_count(tmp_path, monkeypatch):
    """REQ-051 AC2: SPEC-0044 rule 4 (`"auto"` is the machine's CPU count, at least 1)."""
    python = interpreter(tmp_path / "with", xdist=True)
    root = tree(tmp_path, f"{python} -m pytest", 'workers = "auto"\n')
    monkeypatch.setattr(impact.os, "cpu_count", lambda: 4)
    monkeypatch.setattr(impact, "available_memory", lambda: None)  # brief #1032: memory unread
    assert impact.workers_setting(root) == 4
    assert full(root)[0][0][1] == f"{python} -m pytest -n 4"
    monkeypatch.setattr(impact.os, "cpu_count", lambda: None)
    assert impact.workers_setting(root) == 1
    assert full(root)[0][0][1] == f"{python} -m pytest"


def test_a_compound_shell_command_is_not_taken_for_pytest(tmp_path):
    """REQ-051 AC2: SPEC-0044 rules 4 and 5 (only a simple pytest command gains `-n`)."""
    python = interpreter(tmp_path / "with", xdist=True)
    root = tree(tmp_path, f"cd sub && {python} -m pytest", "workers = 2\n")
    sets, notes = full(root)
    assert sets[0][1] == f"cd sub && {python} -m pytest"
    assert notes == [prepush.NO_PARALLEL]


def test_project_tests_full_mode_adds_n_and_prints_nothing_more(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 4 (`project_tests.py` gains `-n` as prepush does)."""
    python = interpreter(tmp_path / "with", xdist=True)
    log = tmp_path / "argv.log"
    python.write_text(
        f'#!/bin/sh\n[ "$1" = "-c" ] && exit 0\necho "$@" > {log}\n', encoding="utf-8"
    )
    root = tree(tmp_path, f"{python} -m pytest -q", "workers = 2\n")
    proc = project_tests(root, {})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert log.read_text(encoding="utf-8").split() == ["-m", "pytest", "-q", "-n", "2"]
    assert proc.stdout == ""


def test_project_tests_without_xdist_prints_the_one_line(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 4 (`project_tests.py` single, with the line)."""
    python = interpreter(tmp_path / "without", xdist=False)
    python.write_text('#!/bin/sh\n[ "$1" = "-c" ] && exit 1\nexit 0\n', encoding="utf-8")
    root = tree(tmp_path, f"{python} -m pytest -q", "workers = 2\n")
    proc = project_tests(root, {})
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == [NO_XDIST]


def test_evidence_rebuilds_the_command_a_record_made_with_workers(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 4 (`evidence.py` rebuilds the same full command)."""
    import evidence

    python = interpreter(tmp_path / "with", xdist=True)
    root = tree(tmp_path, f"{python} -m pytest -q", "workers = 2\n")
    shown = json.dumps({"runs": [], "regression": {"table": True}})
    plan = [sys.executable, "-c", f"print({shown!r})"]
    base = git(root, "rev-parse", "HEAD").strip()
    (root / "app.py").write_text("print('example.com')\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "an unmapped change selects the full run")
    planned = evidence.planned_runs(root, plan, dict(os.environ), base, 60)
    recorded = prepush.safe_command(full(root)[0][0][1], root)
    assert prepush.safe_command(planned[("regression", "full")][0], root) == recorded
    assert recorded.endswith(" -n 2")


# --- rule 5: parallel workers for other runners -------------------------------------------------


def test_parallel_command_replaces_a_non_pytest_full_run(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 5 (`{workers}` filled in)."""
    root = tree(
        tmp_path, "npm test", 'workers = 3\nparallel_command = "npx jest --maxWorkers={workers}"\n'
    )
    sets, notes = full(root)
    assert sets[0][1] == "npx jest --maxWorkers=3"
    assert notes == []


def test_without_parallel_command_a_non_pytest_run_is_single_with_one_line(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 5 (no `parallel_command`: unchanged, one line)."""
    root = tree(tmp_path, "npm test", "workers = 3\n")
    sets, notes = full(root)
    assert sets[0][1] == "npm test"
    assert notes == [prepush.NO_PARALLEL]
    assert "(setting: testing.parallel_command)" in prepush.NO_PARALLEL


def test_an_area_command_is_never_replaced(tmp_path):
    """REQ-051 AC2: SPEC-0044 rules 4 and 5 (a `[proof]` area's command stays as it is)."""
    area = (
        "[proof]\nkit = { dirs = ['tests'], patterns = ['test_*.py'], command = 'one {files}' }\n"
    )
    root = tree(tmp_path, "npm test", 'workers = 3\nparallel_command = "jest -w {workers}"\n', area)
    item = impact.Selected("tests/test_a.py", "src/a.js", "src/**", ["tests/**"])
    found = impact.Impact(table=True, profile="fast", full=False, reason=None, selected=[item])
    sets, notes = prepush.regression_sets(root, found, proof_areas(root))
    assert sets[0][1] == "one tests/test_a.py"
    assert notes == []


# --- rule 6: the same result --------------------------------------------------------------------


def project_tests(root: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    full_env = {k: v for k, v in os.environ.items() if k not in ("EVENT", "AGK_BASE", "CI")}
    full_env.update(env)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(ROOT / "scripts" / "agk" / "project_tests.py")],
        cwd=root,
        capture_output=True,
        text=True,
        env=full_env,
        timeout=300,
    )


def counts(output: str) -> dict[str, int]:
    lines = [line for line in output.splitlines() if COUNT.search(line)]
    return {kind: int(n) for n, kind in COUNT.findall(lines[-1])}


def fixture_run(tmp_path: Path, workers: int) -> subprocess.CompletedProcess:
    root = tmp_path / f"workers-{workers}"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("__pycache__"))
    (root / "agk.toml").write_text(
        'default_branch = "main"\n'
        f"project_tests = '{sys.executable} -m pytest -q'\n"
        f"[testing]\nworkers = {workers}\n",
        encoding="utf-8",
    )
    git(root, "init", "-q", "-b", "main")
    # The fake plugin alone: an installed plugin is not loaded by its entry point.
    return project_tests(root, {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})


def test_a_parallel_run_gives_the_same_counts_and_exit_code(tmp_path):
    """REQ-051 AC3: SPEC-0044 rule 6 (the fixture project with `workers` 1 and 2, never skipped)."""
    single = fixture_run(tmp_path, 1)
    parallel = fixture_run(tmp_path, 2)
    assert "fake xdist" not in single.stdout
    assert "(fake xdist, 2 workers)" in parallel.stdout, parallel.stdout + parallel.stderr
    assert counts(single.stdout) == {"failed": 1, "passed": 2, "skipped": 1}
    assert counts(parallel.stdout) == counts(single.stdout)
    assert single.returncode == parallel.returncode == 1


# --- rule 7: a slow single-process suite --------------------------------------------------------


def record(path: Path, seconds: float | None) -> Path:
    runs = (
        []
        if seconds is None
        else [{"name": "full", "set": "regression", "exit": 0, "seconds": seconds}]
    )
    data = {"schema": 1, "steps": [{"name": "tests", "outcome": "ok", "runs": runs}]}
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


SLOW = (
    "tests: the full suite took 3060 s in one process, more than slow_suite_seconds (600 s); "
    "see the testing guide on workers (setting: testing.workers)"
)


@pytest.mark.parametrize(
    ("testing", "seconds", "lines"),
    [
        (None, 3060.4, [SLOW]),
        ("workers = 1\n", 3060.4, [SLOW]),
        ("workers = 4\n", 3060.4, []),
        (None, 599.0, []),
        ("slow_suite_seconds = 4000\n", 3060.4, []),
        (None, None, []),
    ],
)
def test_doctor_reports_a_slow_single_process_full_run(tmp_path, testing, seconds, lines):
    """REQ-051 AC5: SPEC-0044 rule 7 (above and below the setting, workers 1 and 4, no full run)."""
    root = tree(tmp_path, "python3 -m pytest", testing)
    assert doctor.suite_lines(root, record(tmp_path / "record.json", seconds)) == lines


def test_doctor_names_the_option_for_a_record_it_cannot_read(tmp_path):
    """REQ-051 AC5: SPEC-0044 rule 7 (a missing or broken record changes nothing; one line)."""
    root = tree(tmp_path, "python3 -m pytest", None)
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    for path in (tmp_path / "missing.json", tmp_path / "bad.json"):
        assert doctor.suite_lines(root, path) == [doctor.NO_RECORD]
    assert "(option: --record)" in doctor.NO_RECORD


def test_doctor_reads_no_record_without_the_option():
    """REQ-051 AC5: SPEC-0044 rule 7 (without `--record` nothing about the suite)."""
    assert doctor.parse_args([])["record"] is None
    assert doctor.parse_args(["--record", "r.json"])["record"] == "r.json"
    assert doctor.parse_args(["--paused", "--record", "r.json"]) is None


def test_doctor_prints_the_line_before_the_summary(tmp_path):
    """REQ-051 AC5: SPEC-0044 rule 7 (an information line; the exit code does not change)."""
    from test_doctor import doctor as run_doctor
    from test_doctor import prepare

    dirs = prepare("ok", tmp_path)
    args = ("--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]))
    plain = run_doctor(*args, str(dirs["root"]))
    slow = run_doctor(
        *args, "--record", str(record(tmp_path / "r.json", 3060.4)), str(dirs["root"])
    )
    assert slow.returncode == plain.returncode
    out = slow.stdout.splitlines()
    assert out[-2] == SLOW
    assert SLOW not in plain.stdout


# --- brief #1032: auto workers capped by free memory ----------------------------------------------

MIB = 1024 * 1024
WORKERS_ENV = "AGK_TEST_WORKERS"


def machine(monkeypatch, cpus: int | None, free_mb: int | None, env: str | None = None) -> None:
    """Stub the CPU count, the free memory (in MB) and the one-machine override."""
    monkeypatch.setattr(impact.os, "cpu_count", lambda: cpus)
    monkeypatch.setattr(
        impact, "available_memory", lambda: None if free_mb is None else free_mb * MIB
    )
    if env is None:
        monkeypatch.delenv(WORKERS_ENV, raising=False)
    else:
        monkeypatch.setenv(WORKERS_ENV, env)


def test_auto_is_capped_by_free_memory(tmp_path, monkeypatch):
    """REQ-051: brief #1032 answer 5 (a) (16 CPUs, 3000 MB free at 500 MB each: 6 workers)."""
    root = tree(tmp_path, "python3 -m pytest", 'workers = "auto"\n')
    machine(monkeypatch, 16, 3000)
    assert impact.workers_setting(root) == 6
    assert impact.workers_line(root) == (
        "tests: 6 workers (cpu 16, free memory 3000 MB at 500 MB each)"
    )


def test_auto_with_ample_memory_is_the_cpu_count(tmp_path, monkeypatch):
    """REQ-051: brief #1032 answer 5 (b) (4 CPUs and 32000 MB free: 4 workers)."""
    root = tree(tmp_path, "python3 -m pytest", 'workers = "auto"\n')
    machine(monkeypatch, 4, 32000)
    assert impact.workers_setting(root) == 4


def test_auto_with_unreadable_memory_is_the_cpu_count(tmp_path, monkeypatch):
    """REQ-051: brief #1032 answer 5 (c) (memory unreadable: the CPU count, as before)."""
    root = tree(tmp_path, "python3 -m pytest", 'workers = "auto"\n')
    machine(monkeypatch, 8, None)
    assert impact.workers_setting(root) == 8
    assert impact.workers_line(root) == "tests: 8 workers (cpu 8, free memory unknown)"


def test_auto_is_at_least_one_worker(tmp_path, monkeypatch):
    """REQ-051: brief #1032 answer 1 (less free memory than one worker holds: still 1)."""
    root = tree(tmp_path, "python3 -m pytest", 'workers = "auto"\n')
    machine(monkeypatch, 8, 100)
    assert impact.workers_setting(root) == 1


def test_worker_memory_mb_sets_the_share_of_each_worker(tmp_path, monkeypatch):
    """REQ-051: brief #1032 answer 2 (`worker_memory_mb = 1000`, 3000 MB free: 3 workers)."""
    root = tree(tmp_path, "python3 -m pytest", 'workers = "auto"\nworker_memory_mb = 1000\n')
    machine(monkeypatch, 16, 3000)
    assert impact.workers_setting(root) == 3
    assert impact.workers_line(root).endswith("(cpu 16, free memory 3000 MB at 1000 MB each)")


@pytest.mark.parametrize("testing", ['workers = "auto"\n', "workers = 3\n", "workers = 1\n"])
def test_the_environment_variable_overrides_the_result(tmp_path, monkeypatch, testing):
    """REQ-051: brief #1032 answer 5 (d) (`AGK_TEST_WORKERS=2` gives 2 for one machine)."""
    root = tree(tmp_path, "python3 -m pytest", testing)
    machine(monkeypatch, 16, 32000, env="2")
    assert impact.workers_setting(root) == 2
    assert impact.workers_line(root) == "tests: 2 workers (AGK_TEST_WORKERS)"


@pytest.mark.parametrize("value", ["99", "0", "-5", "1.5", '"500"', "true"])
def test_a_bad_worker_memory_mb_is_refused_naming_the_setting(tmp_path, monkeypatch, value):
    """REQ-051: brief #1032 answer 5 (e) (`worker_memory_mb` below 100 or not whole: refused)."""
    root = tree(tmp_path, "python3 -m pytest", f'workers = "auto"\nworker_memory_mb = {value}\n')
    machine(monkeypatch, 4, 32000)
    for call in (impact.testing_table, impact.workers_setting):
        with pytest.raises(CheckError) as caught:
            call(root)
        assert "(setting: testing.worker_memory_mb)" in str(caught.value)
        assert value.strip('"') not in str(caught.value)


@pytest.mark.parametrize("value", ["0", "-1", "two", "1.5", "", " 3"])
def test_a_bad_environment_variable_is_refused_naming_it(tmp_path, monkeypatch, value):
    """REQ-051: brief #1032 answer 5 (e) (`AGK_TEST_WORKERS` not a whole number above 0)."""
    root = tree(tmp_path, "python3 -m pytest", 'workers = "auto"\n')
    machine(monkeypatch, 4, 32000, env=value)
    with pytest.raises(CheckError) as caught:
        impact.workers_setting(root)
    assert "(setting: AGK_TEST_WORKERS)" in str(caught.value)
    if value.strip():
        assert value.strip() not in str(caught.value).replace("AGK_TEST_WORKERS", "")


def test_a_numeric_workers_is_used_as_written(tmp_path, monkeypatch):
    """REQ-051: brief #1032 answer 5 (f) (`workers = 12` with 1000 MB free: 12, unchanged)."""
    root = tree(tmp_path, "python3 -m pytest", "workers = 12\n")
    machine(monkeypatch, 2, 1000)
    assert impact.workers_setting(root) == 12
    assert impact.workers_line(root) == "tests: 12 workers (setting: testing.workers)"


def test_without_the_table_the_variable_changes_nothing(tmp_path, monkeypatch):
    """REQ-051: brief #1032 answer 3 (no `[testing]` table: one worker, as before)."""
    root = tree(tmp_path, "python3 -m pytest", None)
    machine(monkeypatch, 16, 32000, env="4")
    assert impact.workers_setting(root) == 1


def test_one_reading_of_free_memory_serves_the_whole_run(tmp_path, monkeypatch):
    """REQ-051: brief #1032 answer 4 (the `-n` of the command and the line give one number)."""
    root = tree(tmp_path, "python3 -m pytest", 'workers = "auto"\n')
    readings = iter([3000, 1000, 500])
    monkeypatch.setattr(impact.os, "cpu_count", lambda: 16)
    monkeypatch.setattr(impact, "available_memory", lambda: next(readings) * MIB)
    monkeypatch.delenv(WORKERS_ENV, raising=False)
    assert impact.workers_setting(root) == 6
    assert impact.workers_setting(root) == 6
    assert impact.workers_line(root).startswith("tests: 6 workers ")


def test_prepush_prints_the_workers_line_for_a_parallel_run(tmp_path, monkeypatch):
    """REQ-051: brief #1032 answer 4 (one line when the run starts in workers, none when single)."""
    python = interpreter(tmp_path / "with", xdist=True)
    root = tree(tmp_path, f"{python} -m pytest -q", 'workers = "auto"\n')
    machine(monkeypatch, 16, 3000)
    sets, _ = full(root)
    assert sets[0][1] == f"{python} -m pytest -q -n 6"
    assert prepush.workers_notes(root, sets) == [
        "tests: 6 workers (cpu 16, free memory 3000 MB at 500 MB each)"
    ]
    single = [("full", f"{python} -m pytest -q", ".", "always")]
    assert prepush.workers_notes(root, single) == []
    (tmp_path / "x").mkdir()
    other = tree(tmp_path / "x", "npm test", 'workers = 3\nparallel_command = "jest -w {workers}"\n')
    made, _ = full(other)
    assert prepush.workers_notes(other, made) == ["tests: 3 workers (setting: testing.workers)"]
