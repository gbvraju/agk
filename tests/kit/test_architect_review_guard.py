"""Tests of `architect_guard.py --review`, the guard of the read-only review agent (SPEC-0023).


The hook runs as Claude Code runs it: JSON on stdin, a denial as JSON on stdout. In review mode no
write is ever allowed, not even under docs/; Bash is judged as for the deciding architect.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys

import pytest
from test_architect_guard import (
    BASH_NO,
    BASH_OK,
    HOOK,
    RULE9_MARK,
    WRITE_NO,
    WRITE_OK,
    denied,
)
from test_architect_guard import (
    project as base_project,  # noqa: F401  (the fixture of test_architect_guard)
)

TOOLS = ["Edit", "Write", "MultiEdit", "NotebookEdit"]


@pytest.fixture
def project(request):
    return request.getfixturevalue("base_project")


def review(payload, project_dir, *flags):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK), *(flags or ("--review",))],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project_dir)},
    )


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("path", [*WRITE_OK, *WRITE_NO])
def test_ac1_review_mode_denies_every_write_even_under_docs(project, tool, path):
    """REQ-030 AC1: rule 2 (no path is allowed; the message names the rule, never the path)."""
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    proc = review({"tool_name": tool, "tool_input": {key: path}}, project)
    verdict = denied(proc.stdout)
    assert proc.returncode == 0 and verdict["permissionDecision"] == "deny"
    assert RULE9_MARK in verdict["permissionDecisionReason"]
    assert "review agent" in verdict["permissionDecisionReason"]
    assert not path or path not in proc.stdout


@pytest.mark.parametrize("command", BASH_OK)
def test_ac1_review_mode_allows_the_same_commands_as_the_deciding_architect(project, command):
    """REQ-030 AC1: rule 2 (read-only git, gh api GET, the comment POST, date -u, governance)."""
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    assert proc.returncode == 0 and proc.stdout == "", command


@pytest.mark.parametrize("command", BASH_NO)
def test_ac1_review_mode_denies_every_other_command_without_echoing_it(project, command):
    """REQ-030 AC1: rule 2 (a merge, a push, a write, an operator, a substitution)."""
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    verdict = denied(proc.stdout)
    assert verdict and verdict["permissionDecision"] == "deny", command
    assert not command or command not in proc.stdout


def test_ac1_review_mode_leaves_reads_alone_and_denies_a_broken_payload(project):
    """REQ-030 AC1: rule 2."""
    for tool in ("Read", "Grep", "Glob"):
        payload = {"tool_name": tool, "tool_input": {"file_path": "docs/a.md"}}
        assert review(payload, project).stdout == ""
    assert denied(review("not json", project).stdout)["permissionDecision"] == "deny"


def test_ac1_without_the_flag_the_guard_is_the_deciding_architects_and_unchanged(project):
    """REQ-030 AC2: rule 1 (the deciding architect still writes under docs/ and the vision)."""
    for path in WRITE_OK:
        payload = {"tool_name": "Write", "tool_input": {"file_path": path}}
        assert (
            subprocess.run(  # nosec B603 - fixed argument list, no shell
                [sys.executable, str(HOOK)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project)},
            ).stdout
            == ""
        )


# --- brief #982 answer 4: the review agent re-runs the evidence check --------------------------

EVIDENCE_OK = [
    "python3 scripts/agk/evidence.py check .agk/evidence.json",
    "python3 scripts/agk/evidence.py check rec.json --head " + "a" * 40,
    "python3 scripts/agk/evidence.py check rec.json --sample 2 --json",
    "python3 ./scripts/agk/evidence.py check --json rec.json",
]
EVIDENCE_NO = [
    "python3 scripts/agk/evidence.py",
    "python3 scripts/agk/evidence.py check",
    "python3 scripts/agk/evidence.py record rec.json",
    "python3 scripts/agk/evidence.py check rec.json --write",
    "python3 scripts/agk/evidence.py check rec.json --out x.json",
    "python3 scripts/agk/evidence.py check a.json b.json",
    "python3 scripts/agk/evidence.py check rec.json > out.txt",
    "python3 scripts/agk/evidence.py check rec.json --head",
]


@pytest.mark.parametrize("command", EVIDENCE_OK)
def test_review_mode_allows_the_evidence_check_with_its_read_only_arguments(project, command):
    """REQ-013: brief #982 answer 4 (`check` writes nothing in the repository; the worktree it
    adds is in a temporary folder and removed)."""
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    assert proc.returncode == 0 and proc.stdout == "", command


@pytest.mark.parametrize("command", EVIDENCE_NO)
def test_review_mode_denies_any_other_evidence_command(project, command):
    """REQ-013: brief #982 answer 4"""
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project)
    verdict = denied(proc.stdout)
    assert verdict and verdict["permissionDecision"] == "deny", command


def test_the_deciding_architect_is_not_given_the_evidence_check(project):
    """REQ-013: brief #982 answer 4 (the allowance is for `--review` only)."""
    command = EVIDENCE_OK[0]
    proc = review({"tool_name": "Bash", "tool_input": {"command": command}}, project, "--x")
    assert denied(proc.stdout)["permissionDecision"] == "deny"
