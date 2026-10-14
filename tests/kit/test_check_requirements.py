"""Tests of scripts/agk/check_requirements.py and scripts/agk/traceability.py."""

from __future__ import annotations


def reqs(*items: tuple[str, str]) -> str:
    out = "# Requirements\n\n"
    for rid, status in items:
        out += f"### {rid} — t\n\n- Acceptance: AC1\n- Status: {status}\n\n"
    return out


def check(repo, *args):
    return repo.run("check_requirements.py", *args)


def test_valid_file_passes(repo):
    """REQ-003"""
    repo.commit({"docs/requirements.md": reqs(("REQ-001", "planned"), ("REQ-002", "in-progress"))})
    assert check(repo).returncode == 0


def test_duplicate_ids_fail(repo):
    """REQ-003"""
    repo.commit({"docs/requirements.md": reqs(("REQ-001", "planned"), ("REQ-001", "planned"))})
    proc = check(repo)
    assert proc.returncode == 1
    assert "duplicate" in proc.stdout


def test_invalid_status_fails_without_echoing_value(repo):
    """REQ-003"""
    repo.commit({"docs/requirements.md": reqs(("REQ-001", "bogus-status"))})
    proc = check(repo)
    assert proc.returncode == 1
    assert "bogus-status" not in proc.stdout


def test_missing_status_fails(repo):
    """REQ-003"""
    repo.commit({"docs/requirements.md": "### REQ-001 — t\n\n- Acceptance: AC1\n"})
    assert check(repo).returncode == 1


def test_two_status_lines_fail(repo):
    """REQ-003"""
    repo.commit({"docs/requirements.md": "### REQ-001 — t\n\n- Status: planned\n- Status: done\n"})
    assert check(repo).returncode == 1


def test_no_requirements_fails(repo):
    """REQ-003"""
    repo.commit({"docs/requirements.md": "# Requirements\n"})
    assert check(repo).returncode == 1


def test_ac2_done_without_marker_fails(repo):
    """REQ-003 AC2"""
    repo.commit(
        {"docs/requirements.md": reqs(("REQ-001", "done")), "tests/test_t.py": "# REQ-002\n"}
    )
    proc = check(repo)
    assert proc.returncode == 1
    assert "REQ-001" in proc.stdout


def test_ac2_done_with_marker_passes(repo):
    """REQ-003 AC2"""
    repo.commit(
        {"docs/requirements.md": reqs(("REQ-001", "done")), "tests/test_t.py": "# REQ-001\n"}
    )
    assert check(repo).returncode == 0


def test_marker_dirs_configurable_by_flag(repo):
    """REQ-003 AC2"""
    repo.commit(
        {"docs/requirements.md": reqs(("REQ-001", "done")), "spec/test_t.py": "# REQ-001\n"}
    )
    assert check(repo).returncode == 1
    assert check(repo, "--tests-dir", "spec").returncode == 0


def test_marker_dirs_configurable_by_pyproject(repo):
    """REQ-003 AC2"""
    repo.commit(
        {
            "docs/requirements.md": reqs(("REQ-001", "done")),
            "spec/test_t.py": "# REQ-001\n",
            "pyproject.toml": '[tool.agk]\ntest_dirs = ["spec"]\n',
        }
    )
    assert check(repo).returncode == 0


def test_ac1_matrix_lists_requirements_and_tests(repo):
    """REQ-003 AC1"""
    repo.commit(
        {
            "docs/requirements.md": reqs(("REQ-001", "done"), ("REQ-002", "planned")),
            "tests/test_t.py": "# REQ-001\n",
        }
    )
    proc = repo.run("traceability.py")
    assert proc.returncode == 0
    assert "REQ-001" in proc.stdout and "tests/test_t.py" in proc.stdout
    row2 = next(ln for ln in proc.stdout.splitlines() if "REQ-002" in ln)
    assert "tests/" not in row2


def test_ac3_matrix_never_written_to_disk(repo):
    """REQ-003 AC3"""
    repo.commit({"docs/requirements.md": reqs(("REQ-001", "planned"))})
    before = repo.git("status", "--porcelain")
    repo.run("traceability.py")
    assert repo.git("status", "--porcelain") == before


def test_markers_only_count_in_test_files(repo):
    """REQ-003 AC2: a REQ-001 string in a non-test file is not a marker."""
    repo.commit(
        {
            "docs/requirements.md": reqs(("REQ-001", "done")),
            "tests/helper.py": "# REQ-001\n",
            "tests/notes.md": "REQ-001\n",
            "tests/data/fixture.txt": "REQ-001\n",
        }
    )
    assert check(repo).returncode == 1
    repo.commit({"tests/data/test_x.py": "# REQ-001\n"})
    assert check(repo).returncode == 0


def test_ac2_marker_for_undefined_id_never_fails(repo):
    """REQ-003 AC2: a REQ-999 marker with no REQ-999 requirement is ignored (SPEC-0001 rule 22)."""
    repo.commit(
        {
            "docs/requirements.md": reqs(("REQ-001", "done")),
            "tests/test_t.py": "# REQ-001\n# REQ-999\n# REQ-004\n",
        }
    )
    assert check(repo).returncode == 0
    proc = repo.run("traceability.py")
    assert proc.returncode == 0
    assert "REQ-999" not in proc.stdout and "REQ-004" not in proc.stdout


def test_ac1_markers_are_found_by_configured_patterns(repo):
    """REQ-010 AC1: SPEC-0002 rule 9 (unittest-style *_test.py files)."""
    repo.commit(
        {
            "docs/requirements.md": reqs(("REQ-001", "done")),
            "agk.toml": 'test_dirs = ["pkg/tests"]\ntest_patterns = ["*_test.py"]\n',
            "pkg/tests/a_test.py": "# REQ-001\n",
            "pkg/tests/test_b.py": "# REQ-002\n",
        }
    )
    assert check(repo).returncode == 0
    proc = repo.run("traceability.py")
    assert "a_test.py" in proc.stdout and "test_b.py" not in proc.stdout


def test_ac1_default_pattern_ignores_underscore_test_files(repo):
    """REQ-010 AC1: rule 9."""
    repo.commit(
        {"docs/requirements.md": reqs(("REQ-001", "done")), "tests/a_test.py": "# REQ-001\n"}
    )
    assert check(repo).returncode == 1


def test_ac1_adopt_mode_excludes_tests_kit_unless_listed(repo):
    """REQ-010 AC1: rule 9."""
    files = {
        "docs/requirements.md": reqs(("REQ-001", "done")),
        "tests/kit/test_k.py": "# REQ-001\n",
        "agk.toml": 'mode = "adopt"\ntest_dirs = ["tests"]\n',
    }
    repo.commit(files)
    assert check(repo).returncode == 1
    repo.commit({"agk.toml": 'mode = "adopt"\ntest_dirs = ["tests/kit"]\n'})
    assert check(repo).returncode == 0
    repo.commit({"agk.toml": 'mode = "init"\ntest_dirs = ["tests"]\n'})
    assert check(repo).returncode == 0
