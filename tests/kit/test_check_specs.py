"""Tests of scripts/agk/check_specs.py (principle 6: Approved specs change by amendment)."""

from __future__ import annotations

import pytest

SPEC = "docs/specs/0001-thing.md"
OTHER = "docs/specs/0002-other.md"
AMEND = "docs/runs/proposed-spec-amendments-1.md"


def spec(status: str, body: str = "rules") -> str:
    return (
        f"# SPEC-0001: Thing\n\n- Status: {status}\n- Owner: maintainers\n\n## Rules\n\n1. {body}\n"
    )


@pytest.fixture
def base(repo):
    repo.commit(
        {
            SPEC: spec("Approved"),
            OTHER: spec("Draft"),
            "docs/specs/TEMPLATE.md": spec("Draft", "t"),
            "src/a.py": "1\n",
        },
        "base",
    )
    repo.branch()
    return repo


def check(repo):
    return repo.run("check_specs.py", "--base", "main")


def test_unrelated_change_passes(base):
    """REQ-001 AC1: principle 6 check ignores PRs that touch no spec."""
    base.commit({"src/a.py": "2\n"})
    assert check(base).returncode == 0


def test_approved_spec_edit_without_amendment_fails_naming_the_path_only(base):
    """REQ-001 AC3: the message names the spec path, never content."""
    base.commit({SPEC: spec("Approved", "SECRET_RULE_TEXT_77")})
    proc = check(base)
    assert proc.returncode == 1
    assert SPEC in proc.stdout
    assert "SECRET_RULE_TEXT_77" not in proc.stdout + proc.stderr


def test_approved_spec_edit_with_added_amendment_naming_it_passes(base):
    """REQ-001 AC1"""
    base.commit({SPEC: spec("Approved", "changed"), AMEND: f"Amends {SPEC}\n"})
    assert check(base).returncode == 0


def test_approved_spec_edit_with_modified_amendment_naming_it_passes(repo):
    """REQ-001 AC1"""
    repo.commit({SPEC: spec("Approved"), AMEND: f"Amends {SPEC}\n"}, "base")
    repo.branch()
    repo.commit({SPEC: spec("Approved", "changed"), AMEND: f"Amends {SPEC}\nmore\n"})
    assert check(repo).returncode == 0


def test_amendment_naming_another_spec_does_not_cover(base):
    """REQ-001 AC1"""
    base.commit({SPEC: spec("Approved", "changed"), AMEND: f"Amends {OTHER}\n"})
    assert check(base).returncode == 1


def test_amendment_not_touched_by_the_pr_does_not_cover(repo):
    """REQ-001 AC1: an old amendment file in the base is not cover."""
    repo.commit({SPEC: spec("Approved"), AMEND: f"Amends {SPEC}\n"}, "base")
    repo.branch()
    repo.commit({SPEC: spec("Approved", "changed")})
    assert check(repo).returncode == 1


def test_wrongly_named_file_is_not_an_amendment(base):
    """REQ-001 AC1"""
    base.commit({SPEC: spec("Approved", "changed"), "docs/runs/notes.md": f"{SPEC}\n"})
    assert check(base).returncode == 1


def test_deleted_amendment_does_not_cover(repo):
    """REQ-001 AC1"""
    repo.commit({SPEC: spec("Approved"), AMEND: f"Amends {SPEC}\n"}, "base")
    repo.branch()
    repo.commit({SPEC: spec("Approved", "changed"), AMEND: None})
    assert check(repo).returncode == 1


def test_draft_spec_edit_passes(base):
    """REQ-001 AC1"""
    base.commit({OTHER: spec("Draft", "changed"), "docs/specs/TEMPLATE.md": spec("Draft", "x")})
    assert check(base).returncode == 0


def test_draft_to_approved_flip_passes(base):
    """REQ-001 AC1: the base version is Draft, so the flip is not an amendment."""
    base.commit({OTHER: spec("Approved")})
    assert check(base).returncode == 0


def test_new_approved_spec_passes(base):
    """REQ-001 AC1"""
    base.commit({"docs/specs/0003-new.md": spec("Approved")})
    assert check(base).returncode == 0


def test_status_only_change_of_an_approved_spec_still_needs_an_amendment(base):
    """REQ-001 AC1: conservative reading."""
    base.commit({SPEC: spec("Draft")})
    assert check(base).returncode == 1


def test_deleting_an_approved_spec_needs_an_amendment(base):
    """REQ-001 AC1"""
    base.commit({SPEC: None})
    assert check(base).returncode == 1


def test_uncommitted_change_is_seen(base):
    """REQ-001 AC1"""
    base.write(SPEC, spec("Approved", "dirty"))
    assert check(base).returncode == 1


def test_no_base_locally_is_skipped_with_notice(repo):
    """REQ-001 AC1"""
    repo.commit({SPEC: spec("Approved")})
    repo.git("branch", "-m", "trunk")
    proc = repo.run("check_specs.py")
    assert proc.returncode == 0 and "skipped" in proc.stdout


def test_unresolvable_base_in_ci_fails(repo):
    """REQ-001 AC1"""
    repo.commit({SPEC: spec("Approved")})
    repo.git("branch", "-m", "trunk")
    assert repo.run("check_specs.py", CI="true").returncode == 1
