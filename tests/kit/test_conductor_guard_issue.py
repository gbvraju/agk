"""The conductor's guard allows it to file a brief, and nothing else that creates (brief 276).

The one new action: `gh api --method POST repos/<origin>/issues` with one `-f title=...`, one
`-f labels[]=agk-brief` and one `-F body=@<file>`, where the file is a regular file of a scratch
directory that `check_brief.py` accepts (with the project's `docs/requirements.md` as its root).
Any other label, a second label, another field, another repository, an issue edit, a label
creation, an inline body or a body that fails the check stays denied. The shadow mode allows none
of it. Hook run as Claude Code runs it; no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "conductor_guard.py"
MARK = "conductor guard rule 6"
BRIEF = """Brief: a project's conductor can file the briefs it writes

Sentence: "A conductor session files the briefs it writes."

Answers:
1. The guard allows the issue creation.
2. Nothing else widens.

Advances: REQ-039
Touches: .claude/hooks/conductor_guard.py
Priority: 1
Size: M
"""
REQUIREMENTS = "# Requirements\n\n### REQ-039 — a requirement\n\n- Status: planned\n"


def run_hook(command: str, project: Path, tmpdir: Path, *args: str):
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project), "TMPDIR": str(tmpdir)}
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(HOOK), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def denial(out) -> dict | None:
    return json.loads(out.stdout)["hookSpecificOutput"] if out.stdout.strip() else None


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding="utf-8"
    )
    (root / "docs").mkdir()
    (root / "docs" / "requirements.md").write_text(REQUIREMENTS, encoding="utf-8")
    return root


@pytest.fixture
def tmp(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("systmp")
    (root / "agk-conductor-1").mkdir()
    return root


def brief_file(tmp: Path, text: str = BRIEF, name: str = "agk-conductor-1/brief.md") -> Path:
    path = tmp / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def create(body: object, label: str = "agk-brief", repo: str = "o/r", extra: str = "") -> str:
    return (
        f"gh api --method POST repos/{repo}/issues -f 'title=Brief: x y'"
        f" -f 'labels[]={label}' -F body=@{body}{extra}"
    )


def assert_denied(out) -> None:
    found = denial(out)
    assert out.returncode == 0 and found is not None, out.stdout
    assert found["permissionDecision"] == "deny" and MARK in found["permissionDecisionReason"]


def test_a_checked_brief_from_a_scratch_file_can_be_filed(project, tmp):
    """REQ-039: brief #276 answers 1 and 4."""
    out = run_hook(create(brief_file(tmp)), project, tmp)
    assert out.returncode == 0 and denial(out) is None, out.stdout


@pytest.mark.parametrize(
    "order",
    [
        "-F body=@{b} -f 'labels[]=agk-brief' -f 'title=Brief: x'",
        "-X POST -f 'labels[]=agk-brief' -F body=@{b} -f title=x",
        "--method=POST -f title=x --raw-field 'labels[]=agk-brief' --field body=@{b}",
    ],
)
def test_the_fields_may_come_in_any_order_and_spelling(project, tmp, order):
    """REQ-039: brief #276 answers 1 and 4."""
    words = order.format(b=brief_file(tmp))
    method = "" if words.startswith(("-X", "--method=")) else "--method POST "
    out = run_hook(f"gh api {method}repos/o/r/issues {words}", project, tmp)
    assert denial(out) is None, out.stdout


@pytest.mark.parametrize("label", ["agk-conductor", "bug", "agk-shadow", "agk-brief,bug", ""])
def test_an_issue_with_another_label_is_refused(project, tmp, label):
    """REQ-039: brief #276 answers 1 and 4."""
    assert_denied(run_hook(create(brief_file(tmp), label=label), project, tmp))


@pytest.mark.parametrize(
    "extra",
    [
        " -f 'labels[]=bug'",
        " -f 'labels[]=agk-brief'",
        " -f 'assignees[]=someone'",
        " -f milestone=1",
        " -f 'title=second'",
        " -F body=@/etc/hostname",
        " -H 'Accept: x'",
        " --input /etc/hostname",
        " --jq .number",
    ],
)
def test_a_second_label_or_any_other_field_or_flag_is_refused(project, tmp, extra):
    """REQ-039: brief #276 answers 1 and 4."""
    assert_denied(run_hook(create(brief_file(tmp), extra=extra), project, tmp))


def test_the_label_given_as_a_plain_string_is_refused(project, tmp):
    """REQ-039: brief #276 answers 1 and 4."""
    command = create(brief_file(tmp)).replace("labels[]=", "labels=")
    assert_denied(run_hook(command, project, tmp))


@pytest.mark.parametrize(
    "text",
    [
        BRIEF.replace('Sentence: "A conductor session files the briefs it writes."\n', ""),
        BRIEF.replace("Size: M\n", ""),
        BRIEF.replace("Advances: REQ-039", "Advances: REQ-999"),
        BRIEF.replace("Priority: 1", "Priority: 0"),
        "Verdict: cleared a1b2c3d\n",
        "",
    ],
)
def test_a_body_that_check_brief_refuses_is_refused(project, tmp, text):
    """REQ-039: brief #276 answers 1 and 4."""
    assert_denied(run_hook(create(brief_file(tmp, text)), project, tmp))


def test_a_project_without_a_readable_requirements_file_files_nothing(project, tmp):
    """REQ-039: brief #276 answers 1 and 4."""
    (project / "docs" / "requirements.md").unlink()
    assert_denied(run_hook(create(brief_file(tmp)), project, tmp))


def test_a_body_outside_a_scratch_directory_or_through_a_link_is_refused(project, tmp):
    """REQ-039: brief #276 answers 1 and 4."""
    outside = tmp / "elsewhere" / "brief.md"
    outside.parent.mkdir()
    outside.write_text(BRIEF, encoding="utf-8")
    assert_denied(run_hook(create(outside), project, tmp))
    link = tmp / "agk-conductor-1" / "link.md"
    link.symlink_to(outside)
    assert_denied(run_hook(create(link), project, tmp))
    assert_denied(run_hook(create(tmp / "agk-conductor-1"), project, tmp))
    assert_denied(run_hook(create(tmp / "agk-conductor-1" / "missing.md"), project, tmp))


def test_an_inline_body_is_refused(project, tmp):
    """REQ-039: brief #276 answers 1 and 4."""
    command = "gh api --method POST repos/o/r/issues -f title=x -f 'labels[]=agk-brief' -f body=x"
    assert_denied(run_hook(command, project, tmp))


@pytest.mark.parametrize(
    "command",
    [
        "gh api --method POST repos/other/r/issues -f title=x -f 'labels[]=agk-brief' -F body=@{b}",
        "gh api --method POST repos/o/r/issues/7 -f title=x -f 'labels[]=agk-brief' -F body=@{b}",
        "gh api --method PATCH repos/o/r/issues/7 -f state=closed",
        "gh api --method PATCH repos/o/r/issues -f title=x -f 'labels[]=agk-brief' -F body=@{b}",
        "gh api --method POST repos/o/r/labels -f name=agk-brief",
        "gh api --method POST repos/o/r/issues/7/labels -f 'labels[]=agk-brief'",
        "gh api --method POST repos/o/r/issues -f title=x -F body=@{b}",
        "gh api --method POST repos/o/r/issues -f 'labels[]=agk-brief' -F body=@{b}",
        "gh api --method POST repos/o/r/issues -f title= -f 'labels[]=agk-brief' -F body=@{b}",
        "gh issue create --title x --label agk-brief --body-file {b}",
    ],
)
def test_every_other_creation_or_edit_stays_refused(project, tmp, command):
    """REQ-039: brief #276 answers 1 and 4."""
    assert_denied(run_hook(command.format(b=brief_file(tmp)), project, tmp))


def test_an_issue_of_a_repository_other_than_origin_is_refused(project, tmp):
    """REQ-039: brief #276 answers 1 and 4."""
    (project / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/x/y.git\n', encoding="utf-8"
    )
    assert_denied(run_hook(create(brief_file(tmp)), project, tmp))


def test_the_shadow_mode_files_no_brief(project, tmp):
    """REQ-039: brief #276 answers 1 and 4."""
    assert_denied(run_hook(create(brief_file(tmp)), project, tmp, "--shadow"))


def test_the_refusal_names_the_rule_and_never_the_body_or_the_path(project, tmp):
    """REQ-039: brief #276 answers 1 and 4."""
    path = brief_file(tmp, BRIEF.replace("Size: M\n", ""))
    reason = denial(run_hook(create(path), project, tmp))["permissionDecisionReason"]
    assert str(path) not in reason and "conductor session files" not in reason


def flat(rel: str) -> str:
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def test_the_role_file_says_how_to_file_a_brief_in_dependency_order():
    """REQ-039: brief #276 answer 2."""
    text = flat(".claude/agents/conductor.md")
    assert "labels[]=agk-brief" in text and "-F body=@" in text
    assert "check_brief.py" in text and "dependency order" in text
    assert "stop" in text and "number differs" in text
    assert "label is created by a person" in text


def test_the_session_rules_say_the_last_pull_request_of_a_brief_closes_it():
    """REQ-039: brief #276 answer 3."""
    text = flat("config/session-rules.md")
    assert "last pull request of a brief" in text and "`Closes #<brief>`" in text
