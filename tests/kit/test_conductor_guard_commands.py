"""The conductor guard allows the read-only routines of `conductor.py` (brief #643 build (a)).

REQ-037. Exactly `python3 scripts/agk/conductor.py sweep` and `... watch [--since <ISO>] [--once]`,
the project's own regular file, so that the role's operating lessons name a command it can run;
every other form stays denied. No test uses the network."""

from __future__ import annotations

import pytest
from test_conductor_guard_queue import RULE, reason, run_hook

SCRIPT = "scripts/agk/conductor.py"
WHEN = "2026-11-06T10:00:00Z"


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    (root / "scripts" / "agk").mkdir(parents=True)
    (root / SCRIPT).write_text("print('the project script')\n", encoding="utf-8")
    (root / ".git").mkdir()
    return root


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {SCRIPT} sweep",
        f"python3 {SCRIPT} watch",
        f"python3 {SCRIPT} watch --once",
        f"python3 {SCRIPT} watch --since {WHEN}",
        f"python3 {SCRIPT} watch --since {WHEN} --once",
    ],
)
def test_the_read_only_routines_are_allowed(project, command):
    result = run_hook(command, project)
    assert result.returncode == 0 and result.stdout == "", result.stdout


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {SCRIPT}",
        f"python3 {SCRIPT} merge-queue",
        f"python3 {SCRIPT} sweep --all",
        f"python3 {SCRIPT} watch --since yesterday",
        f"python3 {SCRIPT} watch --once --since {WHEN}",
        f"python3 {SCRIPT} watch --since {WHEN} --once x",
        f"python3 {SCRIPT} sweep; gh pr merge 7",
        f"python3 -I {SCRIPT} sweep",
        "python3 /elsewhere/scripts/agk/conductor.py sweep",
    ],
)
def test_every_other_form_is_denied(project, command):
    assert reason(run_hook(command, project).stdout) is not None


def test_a_linked_script_is_denied(project, tmp_path):
    (project / SCRIPT).unlink()
    other = tmp_path / "other.py"
    other.write_text("print(1)\n", encoding="utf-8")
    (project / SCRIPT).symlink_to(other)
    assert reason(run_hook(f"python3 {SCRIPT} sweep", project).stdout) == RULE
