"""The kit's own full suite in parallel workers (brief #631, ADR-0305, SPEC-0044 rules 1, 4 and 6).

The kit repository runs its full suite as `make -f agk.mk agk-test` (the governance step `Tests
of the checks`, on a push to the default branch and on a release pull request). That target takes
its command from `prepush.full_command` with `[testing] workers` of `agk.toml`, as prepush and
`project_tests.py` do: `-n <workers>` only when the suite's interpreter imports xdist, else the
command of today after the one line naming the setting. A fixture tree, invented, runs the target
with a fake `xdist` on its own path and with an `xdist` that cannot be imported, and the counts
and the exit code are the same. No network, no install.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import impact

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "workers"
NO_XDIST = (
    "tests: pytest-xdist is not importable, running in one process (setting: testing.workers)"
)
COUNT = re.compile(r"(\d+) (passed|failed|skipped)")


def counts(output: str) -> dict[str, int]:
    lines = [line for line in output.splitlines() if COUNT.search(line)]
    return {kind: int(n) for n, kind in COUNT.findall(lines[-1])}


def kit_tree(tmp_path: Path, testing: str, xdist: bool) -> Path:
    """An invented kit tree: agk.mk, kit/agk-kit.mk, the kit's scripts and a small suite."""
    root = tmp_path / ("with" if xdist else "without")
    (root / "kit").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "scripts" / "agk").symlink_to(ROOT / "scripts" / "agk", target_is_directory=True)
    shutil.copy(ROOT / "agk.mk", root / "agk.mk")
    shutil.copy(ROOT / "kit" / "agk-kit.mk", root / "kit" / "agk-kit.mk")
    suite = root / "tests" / "kit"
    suite.mkdir(parents=True)
    for name in ("check_alpha.py", "check_beta.py"):
        shutil.copy(FIXTURE / name, suite / name)
    ini = (FIXTURE / "pytest.ini").read_text(encoding="utf-8")
    if not xdist:
        ini = ini.replace("-p xdist ", "")
    (suite / "pytest.ini").write_text(ini, encoding="utf-8")
    (root / "agk.toml").write_text(
        f'default_branch = "main"\nlint_paths = ["scripts/agk"]\n[testing]\n{testing}',
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)  # nosec B603 B607
    return root


def run_suite(tmp_path: Path, testing: str, xdist: bool) -> subprocess.CompletedProcess:
    root = kit_tree(tmp_path, testing, xdist)
    if xdist:
        path = FIXTURE  # the fake plugin of SPEC-0044 rule 6
    else:
        path = tmp_path / "no-xdist"
        path.mkdir()
        (path / "xdist.py").write_text('raise ImportError("invented: no plugin")\n', "utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("EVENT", "AGK_BASE", "CI")}
    env.update({"PYTHONPATH": str(path), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-s", "-f", "agk.mk", "agk-test", f"PY={sys.executable}"],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )


def test_this_repository_runs_its_full_suite_in_workers():
    """REQ-051 AC2: ADR-0305 (`[testing] workers = "auto"` in this repository's agk.toml)."""
    assert impact.config_source(ROOT)["testing"]["workers"] == "auto"
    assert impact.workers_setting(ROOT) >= 1


def test_agk_test_adds_n_when_the_interpreter_imports_xdist(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 4 (`agk-test` takes `prepush.full_command`'s `-n`)."""
    proc = run_suite(tmp_path, "workers = 2\n", xdist=True)
    out = proc.stdout + proc.stderr
    assert "-c tests/kit/pytest.ini tests/kit -q -n 2" in out, out
    assert "(fake xdist, 2 workers)" in out, out
    assert NO_XDIST not in out


def test_agk_test_without_xdist_runs_single_with_the_one_line(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 4 (no plugin: the command of today, after one line)."""
    proc = run_suite(tmp_path, "workers = 2\n", xdist=False)
    out = proc.stdout + proc.stderr
    assert NO_XDIST in out.splitlines(), out
    assert " -n " not in out and "fake xdist" not in out


def test_agk_test_gives_the_same_counts_and_exit_code_in_workers(tmp_path):
    """REQ-051 AC3: SPEC-0044 rule 6 (the kit target, single and parallel, never skipped)."""
    single = run_suite(tmp_path / "one", "workers = 1\n", xdist=True)
    parallel = run_suite(tmp_path / "two", "workers = 2\n", xdist=True)
    assert "fake xdist" not in single.stdout
    assert "(fake xdist, 2 workers)" in parallel.stdout, parallel.stdout + parallel.stderr
    assert counts(single.stdout) == {"failed": 1, "passed": 2, "skipped": 1}
    assert counts(parallel.stdout) == counts(single.stdout)
    assert single.returncode == parallel.returncode != 0


def test_agk_test_refuses_a_malformed_workers_naming_the_setting(tmp_path):
    """REQ-051 AC2: SPEC-0044 rule 1 (a bad value fails the target, naming the setting)."""
    proc = run_suite(tmp_path, 'workers = "many"\n', xdist=True)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "setting: testing.workers" in out and "many" not in out
    assert "passed" not in out
