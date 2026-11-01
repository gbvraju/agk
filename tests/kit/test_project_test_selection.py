"""A pull request's CI can run only the selected tests, while the default branch and every release
run the full suite (brief #453, ADR-0242).

`make -f agk.mk agk-project-test` calls `scripts/agk/project_tests.py`. With `[testing] pr_tests =
"selected"` and the event `pull_request` (the workflow passes `EVENT`), it runs the regression set
that `prepush.regression_sets` builds for the head against its merge base; on a push, any other
event, an unknown event, or a release pull request (one that changes `version` in `agk.toml`) it
runs the full `project_tests` command. With `full`, or without a `[testing]` table, nothing changes.

Each case is an invented project in a temporary git repository; its `project_tests` command and
its `[proof]` area command only record what they were asked to run in a log outside the tree.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAP = 'map = [ { code = "src/billing/**", tests = ["tests/billing/**"] } ]\n'
SELECTED = 'profile = "fast"\npr_tests = "selected"\n' + MAP


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("outside")


def toml(outside: Path, testing: str | None = SELECTED, version: str = "1.0.0") -> str:
    log = outside / "ran.log"
    text = (
        f'version = "{version}"\n'
        'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
        f"project_tests = 'echo full >> {log}'\n"
        "[proof]\n"
        f'kit = {{ dirs = ["tests"], patterns = ["test_*.py"], '
        f"command = 'echo kit {{files}} >> {log}' }}\n"
    )
    if testing is not None:
        text += "[testing]\n" + testing
    return text


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


def project(
    tmp_path: Path,
    base_toml: str,
    change: dict[str, str] | None = None,
    head_toml: str | None = None,
) -> Path:
    """An invented project: `agk.mk` and `scripts/agk` of the kit, a base commit on main, and a
    feature branch with one change commit."""
    root = tmp_path / "proj"
    shutil.copytree(
        ROOT / "scripts" / "agk",
        root / "scripts" / "agk",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copy(ROOT / "agk.mk", root / "agk.mk")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "Builder")
    write(
        root,
        {
            "agk.toml": base_toml,
            "src/billing/pay.py": "base\n",
            "src/other.py": "base\n",
            "tests/billing/test_pay.py": "# guards pay\n",
            "tests/test_other.py": "# guards other\n",
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
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI", "EVENT", "GITHUB_STEP_SUMMARY")
    }
    env["AGK_BASE"] = git(root, "rev-parse", "main").strip()
    if event is not None:
        env["EVENT"] = event
    env.update(extra)
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-s", "-f", "agk.mk", "agk-project-test"],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )


def ran(outside: Path) -> list[str]:
    log = outside / "ran.log"
    return [line.rstrip() for line in log.read_text().splitlines()] if log.is_file() else []


def test_a_pull_request_with_a_selection_runs_only_the_selected_runs(tmp_path, outside):
    """REQ-016, REQ-039: brief #453 answer 2 (a pull request runs only each selected run)."""
    root = project(tmp_path, toml(outside))
    proc = run(root, outside, "pull_request")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["kit tests/billing/test_pay.py"]
    assert "project tests: kit ok" in proc.stdout


def test_a_failing_selected_run_fails_the_step(tmp_path, outside):
    """REQ-016: brief #453 answer 2 (a red selected run is a red step)."""
    text = toml(outside).replace("command = 'echo kit", "command = 'exit 3; echo kit")
    root = project(tmp_path, text)
    proc = run(root, outside, "pull_request")
    assert proc.returncode != 0
    assert "project tests: kit FAIL" in proc.stdout


def test_a_push_to_the_default_branch_runs_the_full_command(tmp_path, outside):
    """REQ-016, REQ-039: brief #453 answer 2 (a push runs the full `project_tests` command)."""
    root = project(tmp_path, toml(outside))
    proc = run(root, outside, "push")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full"]
    assert "project tests: full (event push)" in proc.stdout


def test_a_pull_request_touching_an_always_full_path_runs_the_full_command(tmp_path, outside):
    """REQ-016: brief #453 answer 2 (the plan says full: an `always_full` path)."""
    testing = SELECTED + 'always_full = ["src/billing/**"]\n'
    root = project(tmp_path, toml(outside, testing))
    proc = run(root, outside, "pull_request")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full"]
    assert "regression: full (always_full src/billing/** matches src/billing/pay.py)" in proc.stdout


def test_a_pull_request_with_an_unmapped_file_under_balanced_runs_the_full_command(
    tmp_path, outside
):
    """REQ-016: brief #453 answer 2 (unmapped files under `balanced` make the plan full)."""
    testing = SELECTED.replace('"fast"', '"balanced"')
    root = project(tmp_path, toml(outside, testing), {"src/other.py": "change\n"})
    proc = run(root, outside, "pull_request")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full"]


def test_a_release_pull_request_runs_the_full_command(tmp_path, outside):
    """REQ-016, REQ-039: brief #453 answer 3 (a raised `version` is a release: full)."""
    root = project(tmp_path, toml(outside), head_toml=toml(outside, version="1.1.0"))
    proc = run(root, outside, "pull_request")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full"]
    assert "project tests: full (release: version raised in agk.toml)" in proc.stdout


def test_an_unknown_or_missing_event_runs_the_full_command(tmp_path, outside):
    """REQ-016: brief #453 answer 2 (an unknown or missing event runs the full command)."""
    root = project(tmp_path, toml(outside))
    proc = run(root, outside, "workflow_dispatch")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = run(root, outside, None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full", "full"]
    assert "project tests: full (event unknown)" in proc.stdout


@pytest.mark.parametrize(
    "testing", ['profile = "fast"\npr_tests = "full"\n' + MAP, None], ids=["full", "no-table"]
)
def test_the_default_full_and_no_table_are_unchanged(tmp_path, outside, testing):
    """REQ-016: brief #453 answer 1 (with `full` or no `[testing]` table nothing changes)."""
    root = project(tmp_path, toml(outside, testing))
    proc = run(root, outside, "pull_request")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == ["full"]
    assert "project tests:" not in proc.stdout
    assert "regression:" not in proc.stdout


def test_a_bad_pr_tests_value_is_refused_naming_the_setting(tmp_path, outside):
    """REQ-016: brief #453 answer 1 (refused with `(setting: pr_tests)`, never the value)."""
    testing = 'pr_tests = "sometimes-zz"\n'
    root = project(tmp_path, toml(outside, testing))
    proc = run(root, outside, "pull_request")
    assert proc.returncode != 0
    out = proc.stdout + proc.stderr
    assert "(setting: pr_tests)" in out
    assert "sometimes-zz" not in out
    assert ran(outside) == []


def test_impact_keys_and_reader_know_pr_tests(tmp_path):
    """REQ-016: brief #453 answer 1 (`pr_tests` joins `impact.KEYS`, `full` by default)."""
    import impact

    assert "pr_tests" in impact.KEYS
    root = tmp_path / "r"
    root.mkdir()
    (root / "agk.toml").write_text("[testing]\n", encoding="utf-8")
    assert impact.pr_tests(root) == "full"
    (root / "agk.toml").write_text('[testing]\npr_tests = "selected"\n', encoding="utf-8")
    assert impact.pr_tests(root) == "selected"
    (root / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    assert impact.pr_tests(root) == "full"


def test_the_summary_lines_are_printed_and_appended_to_the_job_summary(tmp_path, outside):
    """REQ-016: brief #453 answer 4 (the regression section and the not-run lines, printed and in
    `$GITHUB_STEP_SUMMARY`, before anything runs)."""
    text = toml(outside).replace('dirs = ["tests"], patterns', 'dirs = ["tests/unit"], patterns')
    root = project(tmp_path, text)
    summary = outside / "summary.md"
    proc = run(root, outside, "pull_request", GITHUB_STEP_SUMMARY=str(summary))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    written = summary.read_text(encoding="utf-8")
    for line in (
        "project tests: pr_tests selected, event pull_request",
        "regression: 1 test file selected",
        "tests: not run (in no [proof] area): tests/billing/test_pay.py",
    ):
        assert line in proc.stdout
        assert line in written
    # Q-453-2: a selected file that no [proof] area can take makes the run full.
    assert ran(outside) == ["full"]
    assert proc.stdout.index("regression: 1 test file selected") < proc.stdout.index(
        "project tests: full"
    )


def test_a_pull_request_that_selects_nothing_runs_nothing_and_says_so(tmp_path, outside):
    """REQ-016: brief #453 answer 4 (only documentation changed: nothing runs, the line says so)."""
    root = project(tmp_path, toml(outside), {"docs/note.md": "a note\n"})
    proc = run(root, outside, "pull_request")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ran(outside) == []
    assert "regression: nothing selected (only documentation changed)" in proc.stdout


def test_no_project_tests_still_prints_the_notice(tmp_path, outside):
    """REQ-016: brief #453 answer 1 (an empty `project_tests` keeps the notice of agk.mk)."""
    text = toml(outside).replace("project_tests = ", "old_tests = ")
    root = project(tmp_path, text)
    proc = run(root, outside, "pull_request")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "agk: no project_tests configured; the project runs its own tests" in proc.stdout


def test_the_workflow_passes_the_event_and_agk_mk_calls_the_script():
    """REQ-039: brief #453 answer 2 (the step passes `EVENT`; the target calls the script, listed
    in the manifest)."""
    import json

    workflow = (ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    block = workflow.split("      - name: Project tests\n", 1)[1].split("      - name:", 1)[0]
    assert "EVENT: ${{ github.event_name }}" in block
    assert "make -f agk.mk agk-project-test" in block
    mk = (ROOT / "agk.mk").read_text(encoding="utf-8")
    target = mk.split("agk-project-test:\n", 1)[1].split("\n\n", 1)[0]
    assert "scripts/agk/project_tests.py" in target
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/project_tests.py" in manifest["verbatim"]


def test_the_kit_repository_does_not_set_pr_tests():
    """REQ-016: brief #453 answer 5 (the kit's own agk.toml leaves `pr_tests` out)."""
    assert "pr_tests" not in (ROOT / "agk.toml").read_text(encoding="utf-8")
