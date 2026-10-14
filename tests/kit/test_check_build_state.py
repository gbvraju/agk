"""Tests of scripts/agk/check_build_state.py."""

from __future__ import annotations

import pytest

BS = "# Build state\n\n## Done log\n\n| Date | Change | REQs |\n\n## Decisions\n"


@pytest.fixture
def base(repo):
    repo.commit({"docs/build-state.md": BS, "src/a.py": "1\n", "docs/x.md": "x\n"}, "base")
    repo.branch()
    return repo


def check(repo):
    return repo.run("check_build_state.py", "--base", "main")


def test_unrelated_pr_passes(base):
    """REQ-006 AC1"""
    base.commit({"src/a.py": "2\n"})
    assert check(base).returncode == 0


def test_ac1_feature_pr_editing_build_state_fails(base):
    """REQ-006 AC1"""
    base.commit({"docs/build-state.md": BS + "row\n", "src/a.py": "2\n"})
    proc = check(base)
    assert proc.returncode == 1
    assert "docs/build-state.md" in proc.stdout


def test_docs_only_pr_may_edit_build_state(base):
    """REQ-006 AC1"""
    base.commit({"docs/build-state.md": BS + "row\n", "docs/x.md": "y\n"})
    assert check(base).returncode == 0


def test_readme_is_not_docs(base):
    """REQ-006 AC1"""
    base.commit({"docs/build-state.md": BS + "row\n", "README.md": "y\n"})
    assert check(base).returncode == 1


def test_creating_build_state_is_allowed_for_bootstrap(repo):
    """REQ-006 AC1"""
    repo.commit({"src/a.py": "1\n"}, "base")
    repo.branch()
    repo.commit({"docs/build-state.md": BS, "src/a.py": "2\n"})
    assert check(repo).returncode == 0


def test_deleting_build_state_fails(base):
    """REQ-006 AC1"""
    base.commit({"docs/build-state.md": None, "docs/x.md": "y\n"})
    assert check(base).returncode == 1


def test_creation_exemption_only_when_absent_at_base(repo):
    """REQ-006 AC1: with the file present at base, an edit alongside code fails."""
    repo.commit({"docs/build-state.md": BS, "src/a.py": "1\n"}, "base")
    repo.branch()
    repo.commit({"docs/build-state.md": BS + "edited\n", "src/a.py": "2\n"})
    proc = check(repo)
    assert proc.returncode == 1
    assert "docs/build-state.md" in proc.stdout


def test_editing_existing_file_uncommitted_fails(base):
    """REQ-006 AC1: uncommitted edits to an existing file are judged against the base too."""
    base.write("docs/build-state.md", BS + "edited\n")
    base.write("src/a.py", "3\n")
    assert check(base).returncode == 1
