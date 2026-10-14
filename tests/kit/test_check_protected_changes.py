"""Tests of scripts/agk/check_protected_changes.py."""

from __future__ import annotations

import pytest

REQ_V1 = "# Requirements\n\n### REQ-001 — A\n\n- Status: planned\n- Acceptance: AC1\n"
NAMES = "constitution/ config/ .claude/ .github/ docs/requirements.md"
ADR = f"# ADR-0003: x\n\n- Status: Accepted\n\nCovers {NAMES}\n"
ADR_UNRELATED = "# ADR-0003: x\n\n- Status: Accepted\n\nNothing relevant here.\n"


@pytest.fixture
def base(repo):
    repo.commit(
        {
            "config/protected-paths.txt": "# c\nconstitution/\nconfig/\n.claude/\n"
            ".github/\ndocs/requirements.md\n",
            "docs/requirements.md": REQ_V1,
            "constitution/vision.md": "v\n",
            "src/app.py": "x = 1\n",
        },
        "base",
    )
    repo.branch()
    return repo


def check(repo):
    return repo.run("check_protected_changes.py", "--base", "main")


def test_unprotected_change_passes(base):
    """REQ-001"""
    base.commit({"src/app.py": "x = 2\n"})
    assert check(base).returncode == 0


def test_ac1_protected_change_without_adr_fails(base):
    """REQ-001 AC1"""
    base.commit({"constitution/vision.md": "changed\n"})
    proc = check(base)
    assert proc.returncode == 1
    assert "constitution/" in proc.stdout


def test_ac1_protected_change_with_new_adr_passes(base):
    """REQ-001 AC1"""
    base.commit({"constitution/vision.md": "changed\n", "docs/adr/0003-x.md": ADR})
    assert check(base).returncode == 0


def test_adr_template_does_not_count_as_adr(base):
    """REQ-001 AC1"""
    base.commit({"config/new.txt": "n\n", "docs/adr/TEMPLATE.md": "t\n"})
    assert check(base).returncode == 1


def test_ac2_status_only_change_in_requirements_is_exempt(base):
    """REQ-001 AC2"""
    base.commit({"docs/requirements.md": REQ_V1.replace("planned", "in-progress")})
    assert check(base).returncode == 0


def test_ac2_other_change_in_requirements_fails(base):
    """REQ-001 AC2"""
    base.commit({"docs/requirements.md": REQ_V1.replace("AC1", "AC1 AC2")})
    assert check(base).returncode == 1


def test_ac2_status_plus_other_change_fails(base):
    """REQ-001 AC2"""
    text = REQ_V1.replace("planned", "done").replace("AC1", "AC9")
    base.commit({"docs/requirements.md": text})
    assert check(base).returncode == 1


def test_ac3_message_names_path_class_not_content(base):
    """REQ-001 AC3"""
    base.commit({".github/x.yml": "secret-looking-content-123\n"})
    proc = check(base)
    assert proc.returncode == 1
    assert ".github/" in proc.stdout
    assert "secret-looking-content-123" not in proc.stdout + proc.stderr


def test_deleting_protected_file_fails(base):
    """REQ-001"""
    base.commit({"constitution/vision.md": None})
    assert check(base).returncode == 1


def test_uncommitted_change_is_seen(base):
    """REQ-001"""
    base.write("config/x.txt", "n\n")
    assert check(base).returncode == 1


def test_protected_list_is_read_from_base(base):
    """REQ-001: a PR cannot shrink the list it is judged by."""
    base.commit({"config/protected-paths.txt": "docs/requirements.md\n"})
    assert check(base).returncode == 1


def test_unresolvable_base_in_ci_fails(base):
    """REQ-001"""
    base.git("branch", "-m", "main", "trunk")
    proc = base.run("check_protected_changes.py", CI="true")
    assert proc.returncode == 1


def test_unresolvable_base_locally_is_skipped_with_notice(tmp_path, repo):
    """REQ-001"""
    repo.commit({"a.txt": "a\n"})
    repo.git("branch", "-m", "trunk")
    proc = repo.run("check_protected_changes.py")
    assert proc.returncode == 0
    assert "skipped" in proc.stdout


def test_base_from_env_github_base_ref(base):
    """REQ-001"""
    base.commit({"constitution/vision.md": "changed\n"})
    proc = base.run("check_protected_changes.py", GITHUB_BASE_REF="main")
    assert proc.returncode == 1


def test_ac1_unrelated_adr_does_not_cover(base):
    """REQ-001 AC1: an ADR that does not name the changed path class is not cover."""
    base.commit({"constitution/vision.md": "changed\n", "docs/adr/0003-x.md": ADR_UNRELATED})
    proc = check(base)
    assert proc.returncode == 1
    assert "constitution/" in proc.stdout


def test_ac1_adr_must_name_every_changed_class(base):
    """REQ-001 AC1: one ADR must name each changed class; naming only one is not cover."""
    only_one = "# ADR-0003: x\n\n- Status: Accepted\n\nCovers constitution/ only\n"
    base.commit(
        {"constitution/vision.md": "c\n", ".github/x.yml": "y\n", "docs/adr/0003-x.md": only_one}
    )
    proc = check(base)
    assert proc.returncode == 1
    assert ".github/" in proc.stdout


def test_ac1_adr_naming_the_class_passes(base):
    """REQ-001 AC1"""
    base.commit({"constitution/vision.md": "changed\n", "docs/adr/0003-x.md": ADR})
    assert check(base).returncode == 0


def test_ac1_modified_adr_with_body_change_naming_class_covers(repo):
    """REQ-001 AC1"""
    repo.commit(
        {
            "config/protected-paths.txt": "constitution/\n",
            "constitution/vision.md": "v\n",
            "docs/adr/0003-x.md": "# ADR-0003: x\n\n- Status: Proposed\n\nbody\n",
        },
        "base",
    )
    repo.branch()
    repo.commit(
        {
            "constitution/vision.md": "c\n",
            "docs/adr/0003-x.md": (
                "# ADR-0003: x\n\n- Status: Proposed\n\nbody names constitution/\n"
            ),
        }
    )
    assert check(repo).returncode == 0


def test_ac1_status_only_adr_edit_is_not_cover(repo):
    """REQ-001 AC1: flipping Status on an ADR that already names the class does not cover."""
    text = "# ADR-0003: x\n\n- Status: Proposed\n\nCovers constitution/\n"
    repo.commit(
        {
            "config/protected-paths.txt": "constitution/\n",
            "constitution/vision.md": "v\n",
            "docs/adr/0003-x.md": text,
        },
        "base",
    )
    repo.branch()
    repo.commit(
        {
            "constitution/vision.md": "c\n",
            "docs/adr/0003-x.md": text.replace("Proposed", "Accepted"),
        }
    )
    proc = check(repo)
    assert proc.returncode == 1
    assert "constitution/" in proc.stdout


def test_ac2_status_only_requirements_change_needs_no_adr(base):
    """REQ-001 AC2: still exempt with the stricter ADR rule."""
    base.commit({"docs/requirements.md": REQ_V1.replace("planned", "done")})
    assert check(base).returncode == 0
