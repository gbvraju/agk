"""Tests of scripts/agk/check_pr_body.py."""

from __future__ import annotations

import pytest

GOOD = "Advances: REQ-001, REQ-002\n\nBuild-state row: 2026-10-14 | skeleton | REQ-001\n"


def test_ac2_good_body_from_stdin_passes(repo):
    """REQ-008 AC2"""
    assert repo.run("check_pr_body.py", "-", stdin=GOOD).returncode == 0


def test_ac2_good_body_from_file_passes(repo):
    """REQ-008 AC2"""
    repo.write("body.md", GOOD)
    assert repo.run("check_pr_body.py", "body.md").returncode == 0


def test_missing_advances_fails(repo):
    """REQ-008 AC2"""
    proc = repo.run("check_pr_body.py", "-", stdin="Build-state row: a | b | REQ-001\n")
    assert proc.returncode == 1
    assert "Advances:" in proc.stdout


def test_advances_without_req_id_fails(repo):
    """REQ-008 AC2"""
    body = "Advances: stuff\nBuild-state row: a | b | REQ-001\n"
    assert repo.run("check_pr_body.py", "-", stdin=body).returncode == 1


def test_missing_or_empty_build_state_row_fails(repo):
    """REQ-006 AC2"""
    assert repo.run("check_pr_body.py", "-", stdin="Advances: REQ-001\n").returncode == 1
    body = "Advances: REQ-001\nBuild-state row:   \n"
    assert repo.run("check_pr_body.py", "-", stdin=body).returncode == 1


def test_template_placeholders_are_rejected(repo):
    """REQ-008 AC2"""
    body = "Advances: REQ-nnn\nBuild-state row: YYYY-MM-DD | change | REQ-nnn\n"
    assert repo.run("check_pr_body.py", "-", stdin=body).returncode == 1


def test_unreadable_file_fails(repo):
    """REQ-008 AC2"""
    assert repo.run("check_pr_body.py", "nope.md").returncode == 1


# --- the tracing of SPEC-0034 rule 9 (REQ-041 AC3) ---------------------------------------------

BRIEF_ISSUES = '[{"number": 12, "labels": [{"name": "agk-brief"}], "title": "t"}]'
OTHER_ISSUES = (
    '[{"number": 3, "labels": [{"name": "bug"}]},'
    ' {"number": 4, "labels": [{"name": "agk-brief"}], "pull_request": {}}]'
)
DONE = "Advances: REQ-041\nBuild-state row: 2026-10-25 REQ-041 done\n"


def traced(repo, body: str, issues: str | None = BRIEF_ISSUES):
    args = ["-"]
    if issues is not None:
        repo.write("issues.json", issues)
        args = ["--issues", "issues.json", "-"]
    return repo.run("check_pr_body.py", *args, stdin=body)


def test_rule9_a_body_without_brief_fails_when_the_repository_has_a_brief(repo):
    """REQ-041 AC3"""
    proc = traced(repo, GOOD)
    assert proc.returncode == 1 and "rule 9" in proc.stdout and "Brief:" in proc.stdout
    assert "#12" not in proc.stdout


def test_rule9_a_body_with_brief_passes(repo):
    """REQ-041 AC3"""
    assert traced(repo, GOOD + "Brief: #12\n").returncode == 0


@pytest.mark.parametrize("line", ["Brief: 12", "Brief: #x", "Brief: #12 and #13", "Brief:"])
def test_rule9_a_brief_line_that_is_not_brief_n_fails(repo, line):
    """REQ-041 AC3"""
    assert traced(repo, GOOD + line + "\n").returncode == 1


@pytest.mark.parametrize("issues", [None, "[]", OTHER_ISSUES, "not json"])
def test_rule9_brief_is_not_required_without_an_agk_brief_issue_in_the_copy(repo, issues):
    """REQ-041 AC3: no copy, an empty copy, other labels, a pull request and a bad copy."""
    assert traced(repo, GOOD, issues).returncode == 0


def test_rule9_setting_done_needs_closes_whatever_the_copy(repo):
    """REQ-041 AC3"""
    for issues in (None, BRIEF_ISSUES):
        proc = traced(repo, DONE + "Brief: #12\n", issues)
        assert proc.returncode == 1 and "rule 9" in proc.stdout and "Closes" in proc.stdout
        assert "REQ-041 done" not in proc.stdout
    assert traced(repo, DONE + "Brief: #12\nCloses #12\n").returncode == 0
    assert traced(repo, DONE.replace("done", "planned"), None).returncode == 0


def test_rule9_a_closes_line_that_is_not_closes_n_fails(repo):
    """REQ-041 AC3"""
    assert traced(repo, DONE + "Brief: #12\nCloses 12\n").returncode == 1
