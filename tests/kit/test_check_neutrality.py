"""Tests of scripts/agk/check_neutrality.py."""

from __future__ import annotations


def test_ac3_empty_list_passes(repo):
    """REQ-007 AC3"""
    repo.commit({"config/neutrality.txt": "# comment only\n", "a.md": "anything goes\n"})
    assert repo.run("check_neutrality.py").returncode == 0


def test_ac2_token_in_tracked_file_fails_without_echoing_token(repo):
    """REQ-007 AC2"""
    repo.commit({"config/neutrality.txt": "# t\nAcmeCorp\n", "src/a.md": "we love acmecorp\n"})
    proc = repo.run("check_neutrality.py")
    assert proc.returncode == 1
    assert "src/a.md:1" in proc.stdout
    assert "acmecorp" not in proc.stdout.lower()


def test_ac2_adr_directory_is_exempt(repo):
    """REQ-007 AC2"""
    repo.commit({"config/neutrality.txt": "AcmeCorp\n", "docs/adr/0001-x.md": "AcmeCorp\n"})
    assert repo.run("check_neutrality.py").returncode == 0


def test_token_list_file_itself_is_exempt(repo):
    """REQ-007 AC1"""
    repo.commit({"config/neutrality.txt": "AcmeCorp\n"})
    assert repo.run("check_neutrality.py").returncode == 0


def test_untracked_files_are_ignored_and_binary_skipped(repo):
    """REQ-007 AC2"""
    repo.commit({"config/neutrality.txt": "AcmeCorp\n"})
    (repo.root / "bin.dat").write_bytes(b"\xff\xfeAcmeCorp")
    repo.git("add", "bin.dat")
    (repo.root / "untracked.md").write_text("AcmeCorp\n")
    assert repo.run("check_neutrality.py").returncode == 0


def test_missing_token_file_fails(repo):
    """REQ-007 AC1"""
    repo.commit({"a.md": "x\n"})
    assert repo.run("check_neutrality.py").returncode == 1
