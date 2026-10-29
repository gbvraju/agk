"""Tests of the conductor guard's read-only queue commands (brief #284, ADR-0175).

The guard allows exactly `python3 scripts/agk/session.py review-queue [--all | --fingerprint]` and
`python3 scripts/agk/session.py queue --role conductor`, the project's own script, so that a timed
conductor pass reads its queue itself; every other script, form and limit stays denied. It also
names the likely cause when a comment's `body=@` file is not an absolute path (the Windows field
note on the brief), without allowing anything more. No test uses the network.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "conductor_guard.py"
RULE = "conductor guard rule 6: this command is not on the conductor's list"
SCRIPT = "scripts/agk/session.py"


def run_hook(command: str, project: Path, cwd: Path | None = None, shadow: bool = False):
    payload: dict = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK), *(["--shadow"] if shadow else [])],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd or project),
    )


def reason(out: str) -> str | None:
    if not out.strip():
        return None
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "scripts" / "agk").mkdir(parents=True)
    (root / SCRIPT).write_text("print('the project script')\n", encoding="utf-8")
    (root / "scripts" / "agk" / "route.py").write_text("print('x')\n", encoding="utf-8")
    git_dir = root / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding="utf-8"
    )
    return root


ALLOWED = [
    f"python3 {SCRIPT} review-queue",
    f"python3 {SCRIPT} review-queue --all",
    f"python3 {SCRIPT} review-queue --fingerprint",
    f"python3 {SCRIPT} queue --role conductor",
]


@pytest.mark.parametrize("command", ALLOWED)
def test_the_read_only_queue_commands_are_allowed(project, command):
    """REQ-039: brief #284 answers 2 and 5 (the read-only forms the brief names)."""
    result = run_hook(command, project)
    assert result.returncode == 0 and result.stdout == "", result.stdout


def test_the_absolute_path_of_the_projects_own_script_is_allowed(project):
    """REQ-039: brief #284 answer 2 (the same script, named by its full path)."""
    result = run_hook(f"python3 {project / SCRIPT} review-queue --all", project, cwd=project.parent)
    assert result.stdout == ""


DENIED = [
    # every other form of the two commands
    f"python3 {SCRIPT} review-queue --all --fingerprint",
    f"python3 {SCRIPT} review-queue --fingerprint --all",
    f"python3 {SCRIPT} review-queue --json",
    f"python3 {SCRIPT} review-queue all",
    f"python3 {SCRIPT} queue",
    f"python3 {SCRIPT} queue --role builder",
    f"python3 {SCRIPT} queue --role person",
    f"python3 {SCRIPT} queue --role conductor --author someone",
    f"python3 {SCRIPT} queue --role=conductor",
    f"python3 {SCRIPT}",
    # every other command of the script: they wait, post, claim or write
    f"python3 {SCRIPT} watch --pr 7",
    f"python3 {SCRIPT} watch --assign builder-a",
    f"python3 {SCRIPT} next --session builder-a",
    f"python3 {SCRIPT} claim --session builder-a --brief 9",
    f"python3 {SCRIPT} after --session builder-a",
    f"python3 {SCRIPT} resume --pr 7",
    f"python3 {SCRIPT} ids",
    f"python3 {SCRIPT} demand",
    f"python3 {SCRIPT} plan",
    f"python3 {SCRIPT} push-check",
    # another interpreter, flag, script or spelling
    f"python {SCRIPT} review-queue",
    f"/usr/bin/python3 {SCRIPT} review-queue",
    f"python3 -I {SCRIPT} review-queue",
    f"python3 -c 'print(1)' {SCRIPT} review-queue",
    "python3 -m session review-queue",
    "python3 scripts/agk/route.py review-queue",
    "python3 scripts/agk/../agk/route.py",
    f"python3 ./{SCRIPT}x review-queue",
    "python3 /elsewhere/scripts/agk/session.py review-queue",
    f"env X=1 python3 {SCRIPT} review-queue",
    f"PYTHONPATH=/tmp python3 {SCRIPT} review-queue",
    # operators and substitutions
    f"python3 {SCRIPT} review-queue && git push origin main",
    f"python3 {SCRIPT} review-queue; gh pr merge 7",
    f"python3 {SCRIPT} review-queue > /tmp/out",
    f"python3 {SCRIPT} review-queue | tee x",
    f"python3 {SCRIPT} review-queue $(id)",
    f"python3 {SCRIPT} review-queue &",
]


@pytest.mark.parametrize("command", DENIED)
def test_every_other_form_is_still_denied(project, command):
    """REQ-039: brief #284 answers 4 and 5 (every other form stays denied)."""
    assert reason(run_hook(command, project).stdout) == RULE


STILL_DENIED = [
    "git push origin main",
    "gh pr merge 7",
    "gh api --method PUT repos/o/r/pulls/7/merge",
    "gh api --method PATCH repos/o/r/pulls/7 -f state=closed",
    "gh api --method POST repos/o/r/issues/7/labels -f labels=x",
    "gh api --method DELETE repos/o/r/git/refs/heads/x",
    "make test",
    "sleep 600",
]


@pytest.mark.parametrize("command", STILL_DENIED)
def test_the_other_limits_of_the_guard_are_unchanged(project, command):
    """REQ-039: brief #284 answer 4 (no merge, no push, no write outside the comment POST)."""
    assert reason(run_hook(command, project).stdout) == RULE


def test_a_relative_path_counts_only_from_the_project_directory(project, tmp_path):
    """REQ-039: brief #284 answer 2 (a copy of the script elsewhere, as in a pull request's
    worktree, is never run with the session's token)."""
    other = tmp_path / "agk-conductor-pr"
    (other / "scripts" / "agk").mkdir(parents=True)
    (other / SCRIPT).write_text("print('the code of a pull request')\n", encoding="utf-8")
    result = run_hook(f"python3 {SCRIPT} review-queue", project, cwd=other)
    assert reason(result.stdout) == RULE
    result = run_hook(f"python3 {other / SCRIPT} review-queue", project)
    assert reason(result.stdout) == RULE


def test_a_link_to_another_script_is_not_the_projects_script(project, tmp_path):
    """REQ-039: brief #284 answer 2 (the real path is judged, not the spelling)."""
    outside = tmp_path / "outside.py"
    outside.write_text("print('x')\n", encoding="utf-8")
    (project / SCRIPT).unlink()
    os.symlink(outside, project / SCRIPT)
    assert reason(run_hook(f"python3 {SCRIPT} review-queue", project).stdout) == RULE


def test_a_missing_script_is_denied(project):
    """REQ-039: brief #284 answer 2 (only a regular file of the project)."""
    (project / SCRIPT).unlink()
    assert reason(run_hook(f"python3 {SCRIPT} review-queue", project).stdout) == RULE


@pytest.mark.parametrize("command", ALLOWED)
def test_the_shadow_reviewer_gets_none_of_them(project, command):
    """REQ-039: brief #284 answer 1 (the shadow's list is not widened by this brief)."""
    assert reason(run_hook(command, project, shadow=True).stdout) == RULE


BACKSLASH = (
    r"gh api --method POST repos/o/r/issues/7/comments "
    r"-F body=@C:\Users\g\AppData\Local\Temp\agk-conductor-v59\verdict.md"
)


@pytest.mark.parametrize(
    "command",
    [
        BACKSLASH,
        "gh api --method POST repos/o/r/issues/7/comments -F body=@agk-conductor-v59/verdict.md",
    ],
)
def test_a_body_file_that_is_not_absolute_is_denied_naming_the_likely_cause(project, command):
    """REQ-039: brief #284 (field note: a backslash path loses its backslashes in Git Bash)."""
    for shadow in (False, True):
        message = reason(run_hook(command, project, shadow=shadow).stdout)
        assert message is not None and message.startswith("conductor guard rule 6:")
        assert "not an absolute path" in message and "forward slashes" in message
        assert "Users" not in message and "verdict.md" not in message  # names no value


def test_an_absolute_body_file_outside_a_scratch_directory_keeps_the_plain_refusal(project):
    """REQ-039: brief #284 (the hint is only for a path that is not absolute)."""
    command = f"gh api --method POST repos/o/r/issues/7/comments -F body=@{project}/x.md"
    assert reason(run_hook(command, project).stdout) == RULE


ROLE = Path(__file__).resolve().parents[2] / ".claude" / "agents" / "conductor.md"


def role_parts() -> tuple[str, str]:
    _, front, body = ROLE.read_text(encoding="utf-8").split("---", 2)
    return front, " ".join(body.split())


def test_the_role_gains_the_self_wake_tool_and_nothing_else():
    """REQ-039: brief #284 answer 1 (it can wake itself; it cannot create recurring tasks)."""
    front, _ = role_parts()
    line = next(x for x in front.splitlines() if x.startswith("tools:"))
    tools = {t.strip() for t in line.split(":", 1)[1].split(",")}
    assert tools == {"Read", "Grep", "Glob", "Bash", "Write", "ScheduleWakeup"}
    assert "Edit|Write|MultiEdit|NotebookEdit|Bash" in front  # the guard's matcher is unchanged


def test_the_role_states_the_cadence_and_when_it_stops():
    """REQ-039: brief #284 answer 3."""
    _, body = role_parts()
    for phrase in (
        "every 10 minutes",
        "`ScheduleWakeup`",
        "python3 scripts/agk/session.py review-queue --fingerprint",
        "python3 scripts/agk/session.py review-queue --all",
        "python3 scripts/agk/session.py queue --role conductor",
        "post nothing",
        "empty for two passes in a row",
        "schedule no further wake",
    ):
        assert phrase in body, phrase
