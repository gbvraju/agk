"""Tests of the shadow mode of .claude/hooks/conductor_guard.py (SPEC-0035 rules 1, 2; REQ-042 AC2).

`--shadow` keeps every read of the conductor's guard and allows one comment `POST` only when its one
`-f` field is `body=Shadow: #<pr> <sha> cleared|fix list|rejected ...`. No test uses the network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "conductor_guard.py"
MARK = "conductor guard rule 6"
POST = "gh api --method POST repos/o/r/issues/9/comments"


def run_hook(payload: object, project: Path, *args: str):
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK), *args],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def denial(out: str) -> dict | None:
    return json.loads(out)["hookSpecificOutput"] if out.strip() else None


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding="utf-8"
    )
    return tmp_path


SHADOW_OK = [
    f"{POST} -f 'body=Shadow: #7 abc1234 fix list'",
    f"{POST} -f 'body=Shadow: #7 abc1234def5678 cleared'",
    f"{POST} -f 'body=Shadow: #12 abc1234 rejected (the reason)'",
    "gh api --method GET repos/o/r/pulls/7/files",
    "gh api repos/o/r/commits/abc1234/check-runs",
    "git diff origin/main...HEAD",
    "git fetch origin",
    "date -u",
]
SHADOW_NO = [
    f"{POST} -f body=hello",
    f"{POST} -f 'body=Verdict: cleared abc1234'",
    f"{POST} -f 'body=Marks:'",
    f"{POST} -f 'body=Shadow: #x abc1234 cleared'",
    f"{POST} -f 'body=Shadow: #7 zzz cleared'",
    f"{POST} -f 'body=Shadow: #7 abc1234 approved'",
    f"{POST} -f 'body=Shadow: #7 abc1234 cleared' -f x=y",
    f"{POST} -f 'body=Shadow: #7 abc1234 cleared' -f 'body=Shadow: #8 abc1234 cleared'",
    f"{POST} -f 'x=Shadow: #7 abc1234 cleared'",
    f"{POST}",
    "gh api --method POST repos/o/r/pulls/7/comments -f 'body=Shadow: #7 abc1234 cleared'",
    "gh api --method POST repos/x/y/issues/9/comments -f 'body=Shadow: #7 abc1234 cleared'",
    "gh api --method PATCH repos/o/r/issues/comments/1 -f 'body=Shadow: #7 abc1234 cleared'",
    "gh pr merge 7",
    "git push origin main",
]


@pytest.mark.parametrize("command", SHADOW_OK)
def test_ac2_shadow_mode_allows_reads_and_one_shadow_comment(project, command):
    """REQ-042 AC2"""
    out = run_hook(bash(command), project, "--shadow")
    assert out.returncode == 0 and denial(out.stdout) is None, command


@pytest.mark.parametrize("command", SHADOW_NO)
def test_ac2_shadow_mode_refuses_every_other_write_naming_the_rule(project, command):
    """REQ-042 AC2"""
    out = run_hook(bash(command), project, "--shadow")
    found = denial(out.stdout)
    assert out.returncode == 0 and found is not None, command
    assert found["permissionDecision"] == "deny" and MARK in found["permissionDecisionReason"]
    assert command not in found["permissionDecisionReason"]


def test_ac2_the_conductors_own_mode_is_unchanged(project):
    """REQ-042 AC2: without `--shadow` any comment is still the conductor's one POST."""
    for command in (f"{POST} -f body=hello", f"{POST} -f 'body=Verdict: cleared abc1234'"):
        assert denial(run_hook(bash(command), project).stdout) is None, command


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit", "NotebookEdit"])
def test_ac2_shadow_mode_writes_no_file_in_the_work_tree(project, tool):
    """REQ-042 AC2"""
    data = {"notebook_path" if tool == "NotebookEdit" else "file_path": "docs/notes.md"}
    found = denial(run_hook({"tool_name": tool, "tool_input": data}, project, "--shadow").stdout)
    assert found is not None and MARK in found["permissionDecisionReason"]


def test_ac2_an_unknown_argument_fails_closed(project):
    """REQ-042 AC2"""
    for args in (("--shadows",), ("--shadow", "x")):
        found = denial(run_hook(bash("git status"), project, *args).stdout)
        assert found is not None and MARK in found["permissionDecisionReason"]
