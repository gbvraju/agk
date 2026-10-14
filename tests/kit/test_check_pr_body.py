"""Tests of scripts/agk/check_pr_body.py."""

from __future__ import annotations

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
