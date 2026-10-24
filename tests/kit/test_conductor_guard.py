"""Tests of .claude/hooks/conductor_guard.py (SPEC-0030 rule 6; REQ-037 AC5).

The hook runs as Claude Code runs it: JSON on stdin, a denial as JSON on stdout, an allow as no
output. No test uses the network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "conductor_guard.py"
MARK = "conductor guard rule 6"
COMMENT = "gh api --method POST repos/o/r/issues/7/comments -f body=hello"


def run_hook(payload: object, project: Path):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project)},
    )


def denial(out: str) -> dict | None:
    return json.loads(out)["hookSpecificOutput"] if out.strip() else None


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding="utf-8"
    )
    return tmp_path


BASH_OK = [
    "git status",
    "git log --oneline -5",
    "git diff origin/main...HEAD",
    "git show abc1234",
    "git merge-base origin/main HEAD",
    "gh api --method GET repos/o/r/pulls/7",
    "gh api repos/o/r/pulls/7/files",
    "gh api --method GET repos/o/r/commits/abc1234/check-runs",
    "gh api --method GET repos/o/r/actions/jobs/9/logs",
    COMMENT,
    "date -u",
]
BASH_NO = [
    "git push origin main",
    "git commit -m x",
    "git checkout main",
    "git merge origin/main",
    "git diff --output=/tmp/x",
    "gh pr merge 7",
    "gh pr comment 7 -b hi",
    "gh api --method PATCH repos/o/r/pulls/7 -f state=closed",
    "gh api --method PUT repos/o/r/pulls/7/merge",
    "gh api --method DELETE repos/o/r/git/refs/heads/x",
    "gh api --method POST repos/o/r/pulls/7/merge -f x=y",
    "gh api --method POST repos/o/r/issues/7/labels -f labels=x",
    "gh api --method POST repos/o/r/git/refs -f ref=x",
    "gh api --method POST repos/other/r/issues/7/comments -f body=hello",
    "gh api --method POST repos/o/r/issues/7/comments --input /tmp/x",
    "gh api --method POST repos/o/r/issues/7/comments",
    "gh api --method GET repos/o/r/pulls/7 --input /tmp/x",
    "make governance",
    "python3 scripts/agk/session.py next --session x",
    "python3 scripts/agk/session.py watch --pr 7",
    "rm -rf docs",
    "cat CLAUDE.md",
    "git status; rm x",
    "git status && gh pr merge 7",
    "git log $(rm x)",
    "git log `rm x`",
    "git log > out.txt",
    "date -u | sh",
    "",
]


@pytest.mark.parametrize("command", BASH_OK)
def test_ac5_reads_and_the_one_comment_post_are_allowed(project, command):
    """REQ-037 AC5"""
    out = run_hook({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    assert out.returncode == 0 and denial(out.stdout) is None, command


@pytest.mark.parametrize("command", BASH_NO)
def test_ac5_every_other_command_is_refused_naming_the_rule(project, command):
    """REQ-037 AC5"""
    out = run_hook({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    found = denial(out.stdout)
    assert out.returncode == 0 and found is not None, command
    assert found["permissionDecision"] == "deny" and MARK in found["permissionDecisionReason"]
    assert command.strip() == "" or command not in found["permissionDecisionReason"]


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit", "NotebookEdit"])
@pytest.mark.parametrize("path", ["docs/notes.md", "constitution/vision.md", "scripts/x.py", ""])
def test_ac5_no_file_write_is_allowed_anywhere(project, tool, path):
    """REQ-037 AC5"""
    data = {"notebook_path" if tool == "NotebookEdit" else "file_path": path}
    found = denial(run_hook({"tool_name": tool, "tool_input": data}, project).stdout)
    assert found is not None and MARK in found["permissionDecisionReason"]
    assert path not in found["permissionDecisionReason"] or path == ""


def test_ac5_a_comment_post_to_another_repository_than_origin_is_refused(project):
    """REQ-037 AC5"""
    (project / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/x/y.git\n', encoding="utf-8"
    )
    out = run_hook({"tool_name": "Bash", "tool_input": {"command": COMMENT}}, project)
    assert denial(out.stdout) is not None


def test_ac5_other_tools_pass_and_bad_input_is_refused(project):
    """REQ-037 AC5"""
    assert (
        denial(run_hook({"tool_name": "Read", "tool_input": {"file_path": "x"}}, project).stdout)
        is None
    )
    assert denial(run_hook("not json", project).stdout) is not None
    assert denial(run_hook({"tool_name": "Bash", "tool_input": {"command": 5}}, project).stdout)
