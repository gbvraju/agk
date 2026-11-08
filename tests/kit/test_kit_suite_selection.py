"""The kit's own pull requests run only their selected tests; the full suite runs on the default
branch (brief #749, ADR-0348, REQ-016).

`make -f agk.mk agk-test` (`kit/agk-kit.mk`, the governance step `Tests of the checks`) reads the
event that the workflow passes as `EVENT`. With `[testing] pr_tests = "selected"` and the event
`pull_request` it runs the tests that `impact.py` selects for the change, through the same plan as
the step `Project tests` (`project_tests.plan`: the same map, `always_full` list, `profile` and
`[proof]` area); otherwise, and whenever that plan is full, the kit's full suite as before. It
prints which mode ran and the selected count; a bad setting fails it with one line naming it.

Each case is an invented kit tree in a temporary git repository. `PY` is a stub runner: it records
a `-m pytest` call (the full suite) in a log outside the tree and runs every other call with the
real interpreter; the `[proof]` area's command only records the files it was given.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "governance.yml"
MAP = 'map = [ { code = "src/billing/**", tests = ["tests/kit/test_pay.py"] } ]\n'
SELECTED = (
    'profile = "fast"\npr_tests = "selected"\nalways_full = ["src/core.py"]\n' + MAP
)


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("outside")


def toml(outside: Path, testing: str = SELECTED, version: str = "1.0.0") -> str:
    log = outside / "ran.log"
    return (
        f'version = "{version}"\n'
        'default_branch = "main"\nlint_paths = ["scripts/agk"]\n'
        'test_dirs = ["tests/kit"]\ntest_patterns = ["test_*.py"]\n'
        f"project_tests = 'echo project >> {log}'\n"
        "[proof]\n"
        f'kit = {{ dirs = ["tests/kit"], patterns = ["test_*.py"], '
        f"command = 'echo kit {{files}} >> {log}' }}\n"
        "[testing]\n" + testing
    )


def stub(outside: Path) -> Path:
    """The stub runner given as `PY`: a `-m` call is the full suite, recorded; the rest run."""
    path = outside / "py"
    path.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "-m" ]; then echo "suite $*" >> "{outside / "ran.log"}"; '
        'exit "${STUB_CODE:-0}"; fi\n'
        f'exec "{sys.executable}" "$@"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def kit_tree(
    tmp_path: Path,
    base_toml: str,
    change: dict[str, str] | None = None,
    head_toml: str | None = None,
) -> Path:
    """An invented kit tree: agk.mk, kit/agk-kit.mk and scripts/agk of the kit, a base commit on
    main and a feature branch with one change commit."""
    root = tmp_path / "kit"
    shutil.copytree(
        ROOT / "scripts" / "agk",
        root / "scripts" / "agk",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (root / "kit").mkdir()
    shutil.copy(ROOT / "agk.mk", root / "agk.mk")
    shutil.copy(ROOT / "kit" / "agk-kit.mk", root / "kit" / "agk-kit.mk")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "Builder")
    write(
        root,
        {
            "agk.toml": base_toml,
            "src/billing/pay.py": "base\n",
            "src/core.py": "base\n",
            "tests/kit/test_pay.py": "# guards pay\n",
            "tests/kit/test_core.py": "# guards core\n",
            "docs/notes.md": "base\n",
        },
    )
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "checkout", "-q", "-b", "feature")
    files = dict(change or {"src/billing/pay.py": "change\n"})
    if head_toml is not None:
        files["agk.toml"] = head_toml
    write(root, files)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change")
    return root


def run(root: Path, outside: Path, event: str | None, **extra: str):
    drop = ("GITHUB_BASE_REF", "AGK_BASE", "CI", "EVENT", "GITHUB_STEP_SUMMARY", "STUB_CODE")
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env["AGK_BASE"] = git(root, "rev-parse", "main").strip()
    if event is not None:
        env["EVENT"] = event
    env.update(extra)
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-s", "-f", "agk.mk", "agk-test", f"PY={stub(outside)}"],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )


def ran(outside: Path) -> list[str]:
    log = outside / "ran.log"
    return log.read_text(encoding="utf-8").split("\n")[:-1] if log.exists() else []


def is_full(lines: list[str]) -> bool:
    return lines == ["suite -m pytest -c tests/kit/pytest.ini tests/kit -q"]


def test_a_pull_request_runs_only_the_selected_files(tmp_path, outside):
    """REQ-016: brief #749 answer 1 (a mapped change on a pull request runs its selection)."""
    root = kit_tree(tmp_path, toml(outside))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert ran(outside) == ["kit tests/kit/test_pay.py"], out
    assert "tests: mode selected, 1 test file (event pull_request)" in out.splitlines(), out


def test_an_always_full_change_runs_the_full_suite(tmp_path, outside):
    """REQ-016: brief #749 answer 3 (`always_full` stays the safety net)."""
    root = kit_tree(tmp_path, toml(outside), change={"src/core.py": "change\n"})
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert is_full(ran(outside)), out
    assert "tests: mode full (always_full src/core.py matches src/core.py)" in out, out


@pytest.mark.parametrize("event", ["push", None])
def test_a_push_or_an_unknown_event_runs_the_full_suite(tmp_path, outside, event):
    """REQ-016: brief #749 answer 2 (a push to the default branch runs the full suite)."""
    root = kit_tree(tmp_path, toml(outside))
    proc = run(root, outside, event)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert is_full(ran(outside)), out
    assert f"tests: mode full (event {event or 'unknown'})" in out.splitlines(), out


def test_a_release_pull_request_runs_the_full_suite(tmp_path, outside):
    """REQ-016: brief #749 answer 2 (a release pull request runs the full suite)."""
    root = kit_tree(tmp_path, toml(outside), head_toml=toml(outside, version="1.1.0"))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert is_full(ran(outside)), out
    assert "tests: mode full (release: version raised in agk.toml)" in out, out


def test_without_selected_a_pull_request_runs_the_full_suite(tmp_path, outside):
    """REQ-016: brief #749 answer 1 (without `pr_tests = "selected"` nothing changes)."""
    root = kit_tree(tmp_path, toml(outside, testing='profile = "fast"\n' + MAP))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert is_full(ran(outside)), out
    assert "tests: mode full (pr_tests full)" in out.splitlines(), out


def test_a_docs_only_pull_request_runs_nothing(tmp_path, outside):
    """REQ-016: brief #749 answer 1 (a documentation change selects nothing, as Project tests)."""
    root = kit_tree(tmp_path, toml(outside), change={"docs/notes.md": "change\n"})
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert ran(outside) == [], out
    assert "tests: mode selected, 0 test files (event pull_request)" in out.splitlines(), out


def test_a_failing_full_suite_fails_the_target(tmp_path, outside):
    """REQ-016: brief #749 answer 2 (the full run keeps its exit code)."""
    root = kit_tree(tmp_path, toml(outside))
    proc = run(root, outside, "push", STUB_CODE="1")
    assert proc.returncode != 0
    assert is_full(ran(outside))


def test_a_bad_setting_fails_with_one_line_naming_it(tmp_path, outside):
    """REQ-016: brief #749 answer 4 (a bad setting fails, naming the setting, never the value)."""
    bad = SELECTED.replace('pr_tests = "selected"', 'pr_tests = "sometimes"')
    root = kit_tree(tmp_path, toml(outside, testing=bad))
    proc = run(root, outside, "pull_request")
    out = proc.stdout + proc.stderr
    own = [line for line in out.splitlines() if line and not line.startswith("make")]
    assert proc.returncode != 0
    assert ran(outside) == []
    assert len(own) == 1 and "setting: pr_tests" in own[0], out
    assert "sometimes" not in out


def test_the_workflow_passes_the_event_to_tests_of_the_checks():
    """REQ-016: brief #749 answer 2 (`Tests of the checks` gets `EVENT`, as `Project tests`)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split("- name: Tests of the checks\n", 1)[1].split("- name: ", 1)[0]
    assert "EVENT: ${{ github.event_name }}" in step, step
    assert "run: make -f agk.mk agk-test" in step
