"""Tests of scripts/agk/reviewers.py."""

from __future__ import annotations

import pytest
from reviewers import ReviewerError, parse, render_codeowners, validate

GOOD = """version: 1
classes:
  protected: {paths: [config/, docs/requirements.md], approvers: [maintainers]}
  docs:      {paths: [docs/, README.md], approvers: [maintainers]}
teams:
  maintainers: {github_team: "@some-team"}   # comment
"""
PROTECTED = "config/\ndocs/requirements.md\n"


def test_ac1_schema_accepts_good_file():
    """REQ-005 AC1"""
    data = parse(GOOD)
    assert data["classes"]["docs"]["paths"] == ["docs/", "README.md"]
    assert data["teams"]["maintainers"]["github_team"] == "@some-team"
    assert validate(data, PROTECTED) == []


@pytest.mark.parametrize(
    "old,new",
    [
        ("version: 1", "version: 2"),
        ("approvers: [maintainers]}\n  docs", "approvers: [ghost]}\n  docs"),
        ("approvers: [maintainers]}\n  docs", "approvers: [@someone]}\n  docs"),
        ("paths: [docs/, README.md]", "paths: []"),
        ('"@some-team"', '"some-team"'),
    ],
)
def test_ac1_ac3_schema_rejects_bad_file(old, new):
    """REQ-005 AC1 AC3: approvers are team names, never personal handles."""
    assert validate(parse(GOOD.replace(old, new)), PROTECTED) != []


def test_protected_paths_must_equal_protected_class():
    """REQ-005 AC1"""
    assert validate(parse(GOOD), "config/\n") != []


def test_unparseable_input_raises():
    """REQ-005 AC1"""
    with pytest.raises(ReviewerError):
        parse("classes: [oops\n")


def test_ac2_codeowners_rendered_broad_to_narrow():
    """REQ-005 AC2: later lines win in CODEOWNERS, so broad paths come first."""
    out = render_codeowners(parse(GOOD))
    lines = [ln for ln in out.splitlines() if ln and not ln.startswith("#")]
    assert "/docs/ @some-team" in lines
    assert "/docs/requirements.md @some-team" in lines
    assert lines.index("/docs/ @some-team") < lines.index("/docs/requirements.md @some-team")


def test_cli_check_and_codeowners(repo):
    """REQ-005 AC1 AC2"""
    repo.commit({"config/reviewers.yaml": GOOD, "config/protected-paths.txt": PROTECTED})
    assert repo.run("reviewers.py", "--check").returncode == 0
    proc = repo.run("reviewers.py", "--codeowners")
    assert proc.returncode == 0 and "@some-team" in proc.stdout
    repo.commit({"config/protected-paths.txt": "config/\n"})
    assert repo.run("reviewers.py", "--check").returncode == 1


def codeowners_repo(repo, text=None):
    from reviewers import parse, render_codeowners

    rendered = render_codeowners(parse(GOOD))
    repo.commit(
        {
            "config/reviewers.yaml": GOOD,
            "config/protected-paths.txt": PROTECTED,
            ".github/CODEOWNERS": rendered if text is None else text,
        }
    )


def test_ac2_committed_codeowners_matching_rendering_passes(repo):
    """REQ-005 AC2"""
    codeowners_repo(repo)
    assert repo.run("reviewers.py", "--check-codeowners").returncode == 0


def test_ac2_codeowners_mismatch_fails_and_names_file_not_content(repo):
    """REQ-005 AC2"""
    codeowners_repo(repo, "/docs/ @someone-else\n")
    proc = repo.run("reviewers.py", "--check-codeowners")
    assert proc.returncode == 1
    assert "CODEOWNERS" in proc.stdout and "someone-else" not in proc.stdout


def test_ac2_missing_codeowners_fails(repo):
    """REQ-005 AC2"""
    codeowners_repo(repo)
    repo.commit({".github/CODEOWNERS": None})
    assert repo.run("reviewers.py", "--check-codeowners").returncode == 1
