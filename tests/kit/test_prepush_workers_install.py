"""A builder installs the pinned test tools before the full run (brief #1021, ADR-0436, REQ-051).

`[testing] tools_file`, unset by default, names a pinned requirements file. When it is set,
`[testing] workers` is above 1 and the run's interpreter cannot import xdist, prepush runs
`<python> -m pip install -q -r <tools_file>` once (adding `--break-system-packages` only when pip
refuses without it) and checks again; a failed install prints one line naming the setting and the
run stays in one process. Without the key nothing is installed (SPEC-0044 rule 4 by default). The
full run of a compound command takes `[testing] parallel_command` (ruled (b) of Q-1021-1), with the
same one-time install before it when its last part is a pytest command. A fake `python3` in
`tmp_path` answers `import xdist` and logs each pip call: no network, no install, invented data.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import tomllib
from pathlib import Path

import impact
import prepush
import pytest
from common import CheckError

ROOT = Path(__file__).resolve().parents[2]
TOOLS = 'tools_file = "tools.txt"\n'
FAKE = """#!/bin/sh
dir="$(dirname "$0")"
if [ "$1" = "-c" ]; then
  [ -f "$dir/xdist-installed" ] && exit 0
  exit 1
fi
if [ "$1" = "-m" ] && [ "$2" = "pip" ]; then
  echo "$*" >> "$dir/pip.log"
  case "{mode}" in
    ok) touch "$dir/xdist-installed"; exit 0 ;;
    fail) echo "ERROR: invented failure" >&2; exit 1 ;;
    managed)
      case "$*" in
        *--break-system-packages*) touch "$dir/xdist-installed"; exit 0 ;;
      esac
      echo "error: externally-managed-environment" >&2; exit 1 ;;
  esac
fi
exit 2
"""


@pytest.fixture(autouse=True)
def fresh_installs():
    prepush.INSTALLS.clear()
    yield
    prepush.INSTALLS.clear()


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )


def tree(tmp_path: Path, project: str, testing: str) -> Path:
    """An invented project in a git repository with one commit, and a pinned tools file."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "tools.txt").write_text("pytest-xdist==0.0.0\n", encoding="utf-8")
    (root / "agk.toml").write_text(
        'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
        f"project_tests = '{project}'\n[testing]\n{testing}",
        encoding="utf-8",
    )
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "Builder")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def interpreter(folder: Path, mode: str, xdist: bool = False) -> Path:
    """A fake `python3`: `-c "import xdist"` succeeds once the plugin is there; `-m pip` logs its
    arguments and installs (`ok`), fails (`fail`) or refuses without the system flag (`managed`)."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "python3"
    path.write_text(FAKE.replace("{mode}", mode), encoding="utf-8")
    path.chmod(0o755)
    if xdist:
        (folder / "xdist-installed").touch()
    return path


def pip_calls(python: Path) -> list[str]:
    log = python.parent / "pip.log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def full(root: Path) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    found = impact.Impact(table=True, profile="balanced", full=True, reason="always")
    return prepush.regression_sets(root, found, None)


def test_a_set_tools_file_and_missing_xdist_install_once_then_add_n(tmp_path):
    """REQ-051: brief #1021 answer 4 (a): one install, then `-n`, also for a selected run."""
    python = interpreter(tmp_path / "py", "ok")
    root = tree(tmp_path, f"{python} -m pytest -q", f"workers = 4\n{TOOLS}")
    sets, notes = full(root)
    assert sets[0][1] == f"{python} -m pytest -q -n 4"
    assert notes == []
    made, lines = prepush.selected_workers(root, [("kit", f"{python} -m pytest a.py", ".", "r")])
    assert made[0][1] == f"{python} -m pytest a.py -n 4"
    assert lines == []
    assert pip_calls(python) == [f"-m pip install -q -r {root / 'tools.txt'}"]


def test_unset_tools_file_installs_nothing(tmp_path):
    """REQ-051: brief #1021 answer 4 (b): without the key, today's behaviour and no install."""
    python = interpreter(tmp_path / "py", "ok")
    root = tree(tmp_path, f"{python} -m pytest -q", "workers = 4\n")
    sets, notes = full(root)
    assert sets[0][1] == f"{python} -m pytest -q"
    assert notes == [prepush.NO_XDIST]
    assert pip_calls(python) == []


def test_a_failing_install_prints_one_line_and_runs_in_one_process(tmp_path):
    """REQ-051: brief #1021 answer 4 (c): one line naming the setting, the command of today."""
    python = interpreter(tmp_path / "py", "fail")
    root = tree(tmp_path, f"{python} -m pytest -q", f"workers = 4\n{TOOLS}")
    sets, notes = full(root)
    assert sets[0][1] == f"{python} -m pytest -q"
    assert notes == [prepush.NO_TOOLS]
    assert "(setting: testing.tools_file)" in prepush.NO_TOOLS
    assert "tools.txt" not in prepush.NO_TOOLS
    made, lines = prepush.selected_workers(root, [("kit", f"{python} -m pytest a.py", ".", "r")])
    assert made[0][1] == f"{python} -m pytest a.py"
    assert lines == [prepush.NO_TOOLS]
    assert len(pip_calls(python)) == 1


def test_an_importable_xdist_runs_no_install(tmp_path):
    """REQ-051: brief #1021 answer 4 (d): xdist already there, `-n` and no pip call."""
    python = interpreter(tmp_path / "py", "ok", xdist=True)
    root = tree(tmp_path, f"{python} -m pytest -q", f"workers = 4\n{TOOLS}")
    sets, notes = full(root)
    assert sets[0][1] == f"{python} -m pytest -q -n 4"
    assert notes == []
    assert pip_calls(python) == []


def test_one_worker_runs_no_install(tmp_path):
    """REQ-051: brief #1021 answer 2 (only with `workers` above 1)."""
    python = interpreter(tmp_path / "py", "ok")
    root = tree(tmp_path, f"{python} -m pytest -q", f"workers = 1\n{TOOLS}")
    sets, _ = full(root)
    assert sets[0][1] == f"{python} -m pytest -q"
    assert pip_calls(python) == []


def test_the_system_flag_is_added_only_when_pip_refuses_without_it(tmp_path):
    """REQ-051: brief #1021 answer 2 (`--break-system-packages` only after pip refuses)."""
    python = interpreter(tmp_path / "py", "managed")
    root = tree(tmp_path, f"{python} -m pytest -q", f"workers = 2\n{TOOLS}")
    sets, notes = full(root)
    assert sets[0][1] == f"{python} -m pytest -q -n 2"
    assert notes == []
    tools = root / "tools.txt"
    assert pip_calls(python) == [
        f"-m pip install -q -r {tools}",
        f"-m pip install -q -r {tools} --break-system-packages",
    ]


def test_a_compound_command_takes_parallel_command_after_the_install(tmp_path):
    """REQ-051: Q-1021-1 ruled (b): the full run of a compound command takes `parallel_command`,
    with the same one-time install before it."""
    python = interpreter(tmp_path / "py", "ok")
    parallel = f"true || echo setup; {python} -m pytest -q -n {{workers}}"
    root = tree(
        tmp_path,
        f"true || echo setup; {python} -m pytest -q",
        f'workers = 3\n{TOOLS}parallel_command = "{parallel}"\n',
    )
    sets, notes = full(root)
    assert sets[0][1] == f"true || echo setup; {python} -m pytest -q -n 3"
    assert notes == []
    assert len(pip_calls(python)) == 1


def test_a_failed_install_keeps_a_compound_command_in_one_process(tmp_path):
    """REQ-051: Q-1021-1 ruled (b) with answer 2: a failed install runs the command of today."""
    python = interpreter(tmp_path / "py", "fail")
    command = f"true || echo setup; {python} -m pytest -q"
    root = tree(
        tmp_path,
        command,
        f'workers = 3\n{TOOLS}parallel_command = "{command} -n {{workers}}"\n',
    )
    sets, notes = full(root)
    assert sets[0][1] == command
    assert notes == [prepush.NO_TOOLS]


def test_a_non_pytest_parallel_command_never_reaches_the_install(tmp_path):
    """REQ-051: brief #1021 contexts (stacks: other runners never reach the install)."""
    python = interpreter(tmp_path / "py", "ok")
    root = tree(
        tmp_path, "npm test", f'workers = 3\n{TOOLS}parallel_command = "npx jest -w {{workers}}"\n'
    )
    sets, notes = full(root)
    assert sets[0][1] == "npx jest -w 3"
    assert notes == []
    assert pip_calls(python) == []


@pytest.mark.parametrize("value", ['""', "3", '"/etc/tools.txt"', '"../tools.txt"'])
def test_a_malformed_tools_file_is_refused_naming_the_setting(tmp_path, value):
    """REQ-051: brief #1021 answer 2 (the key is a file path inside the repository)."""
    root = tree(tmp_path, "python3 -m pytest -q", f"tools_file = {value}\n")
    with pytest.raises(CheckError) as caught:
        impact.testing_table(root)
    assert "(setting: testing.tools_file)" in str(caught.value)
    assert "etc" not in str(caught.value)


def test_this_repository_installs_its_ci_tools_and_runs_the_full_suite_in_workers():
    """REQ-051: brief #1021 answer 3 and Q-1021-1 ruled (b) (this repository's settings)."""
    data = tomllib.loads((ROOT / "agk.toml").read_text(encoding="utf-8"))
    testing = data["testing"]
    assert testing["tools_file"] == "config/ci-tools.txt"
    assert (ROOT / testing["tools_file"]).is_file()
    parallel = testing["parallel_command"].replace("{workers}", "2")
    assert parallel == f"{data['project_tests']} -n 2"
    assert prepush.last_pytest(parallel) == "python3"
