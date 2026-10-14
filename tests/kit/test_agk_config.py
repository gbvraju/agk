"""Tests of agk.toml configuration, default-branch resolution and detection (SPEC-0002 5, 7, 8)."""

from __future__ import annotations

from pathlib import Path

import common

DEFAULTS = {
    "default_branch": "main",
    "test_dirs": ["tests"],
    "lint_paths": ["scripts/agk", "tests/kit", ".claude/hooks"],
    "project_tests": "",
    "test_patterns": ["test_*.py"],
    "mode": "",
}


def test_ac1_defaults_when_no_config_exists(tmp_path):
    """REQ-010 AC1: rule 5."""
    assert common.load_config(tmp_path) == DEFAULTS


def test_ac1_agk_toml_is_read(tmp_path):
    """REQ-010 AC1: rule 5."""
    text = 'default_branch = "master"\ntest_dirs = ["pkg/tests"]\nlint_paths = ["x"]\n'
    (tmp_path / "agk.toml").write_text(text)
    cfg = common.load_config(tmp_path)
    assert cfg["default_branch"] == "master"
    assert cfg["test_dirs"] == ["pkg/tests"] and cfg["lint_paths"] == ["x"]


def test_ac1_pyproject_tool_agk_is_the_fallback(tmp_path):
    """REQ-010 AC1: rule 5 (earlier installs)."""
    (tmp_path / "pyproject.toml").write_text('[tool.agk]\ntest_dirs = ["spec"]\n')
    cfg = common.load_config(tmp_path)
    assert cfg["test_dirs"] == ["spec"] and cfg["default_branch"] == "main"


def test_ac1_agk_toml_wins_over_pyproject(tmp_path):
    """REQ-010 AC1: rule 5."""
    (tmp_path / "agk.toml").write_text('test_dirs = ["a"]\n')
    (tmp_path / "pyproject.toml").write_text('[tool.agk]\ntest_dirs = ["b"]\n')
    assert common.load_config(tmp_path)["test_dirs"] == ["a"]


def test_ac1_check_requirements_uses_test_dirs_from_agk_toml(repo):
    """REQ-010 AC1: rule 5."""
    repo.commit(
        {
            "docs/requirements.md": "### REQ-001 — t\n\n- Status: done\n",
            "pkg/tests/test_t.py": "# REQ-001\n",
            "agk.toml": 'test_dirs = ["pkg/tests"]\n',
        }
    )
    assert repo.run("check_requirements.py").returncode == 0


def test_ac1_config_cli_prints_values_and_refuses_unknown_keys(repo):
    """REQ-010 AC1: rule 10 (agk.mk reads lint_paths through config.py)."""
    repo.commit({"agk.toml": 'lint_paths = ["a", "b/c"]\n'})
    proc = repo.run("config.py", "lint_paths")
    assert proc.returncode == 0 and proc.stdout.strip() == "a b/c"
    assert repo.run("config.py", "default_branch").stdout.strip() == "main"
    bad = repo.run("config.py", "nope")
    assert bad.returncode == 1 and "nope" in bad.stdout + bad.stderr


def on_branch(repo, branch, files):
    repo.commit({"src.txt": "1\n"}, "base")
    repo.git("branch", "-m", branch)
    repo.git("checkout", "-q", "-b", "feature")
    repo.commit(files)


def test_ac1_base_resolves_the_configured_default_branch(repo):
    """REQ-010 AC1: rule 8 (a master repository with default_branch = master is not skipped)."""
    on_branch(repo, "master", {"agk.toml": 'default_branch = "master"\n'})
    proc = repo.run("check_build_state.py")
    assert proc.returncode == 0 and "skipped" not in proc.stdout


def test_ac1_unconfigured_master_repository_still_skips_outside_ci(repo):
    """REQ-010 AC1: rule 8 (the default is main)."""
    on_branch(repo, "master", {"src.txt": "2\n"})
    assert "skipped" in repo.run("check_build_state.py").stdout


def test_ac1_ci_with_master_default_resolves_without_a_main_branch(repo):
    """REQ-010 AC1: rule 8 (a push event in CI has no AGK_BASE)."""
    on_branch(repo, "master", {"agk.toml": 'default_branch = "master"\n'})
    proc = repo.run("check_build_state.py", CI="true")
    assert proc.returncode == 0, proc.stdout


def git_dir(tmp_path: Path) -> Path:
    git = tmp_path / ".git"
    (git / "refs" / "remotes" / "origin").mkdir(parents=True)
    return git


def test_ac1_detect_default_branch_from_origin_head(tmp_path):
    """REQ-010 AC1: rule 7."""
    git = git_dir(tmp_path)
    (git / "refs" / "remotes" / "origin" / "HEAD").write_text("ref: refs/remotes/origin/master\n")
    (git / "HEAD").write_text("ref: refs/heads/other\n")
    assert common.detect_default_branch(tmp_path) == "master"


def test_ac1_detect_default_branch_from_head_without_origin(tmp_path):
    """REQ-010 AC1: rule 7."""
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/trunk\n")
    (git / "config").write_text("[core]\n\tbare = false\n")
    assert common.detect_default_branch(tmp_path) == "trunk"


def test_ac1_detect_default_branch_is_none_when_origin_exists_without_head(tmp_path):
    """REQ-010 AC1: rule 7."""
    git = git_dir(tmp_path)
    (git / "HEAD").write_text("ref: refs/heads/trunk\n")
    assert common.detect_default_branch(tmp_path) is None


def test_ac1_detect_default_branch_is_none_without_a_git_directory(tmp_path):
    """REQ-010 AC1: rule 7."""
    assert common.detect_default_branch(tmp_path) is None
    (tmp_path / ".git").write_text("gitdir: elsewhere\n")
    assert common.detect_default_branch(tmp_path) is None


def test_ac1_project_tests_is_read_and_printed(repo):
    """REQ-010 AC1: rule 5 (project_tests)."""
    repo.commit({"agk.toml": 'project_tests = "echo hi; exit 0"\n'})
    assert common.load_config(repo.root)["project_tests"] == "echo hi; exit 0"
    assert repo.run("config.py", "project_tests").stdout.strip() == "echo hi; exit 0"


def test_ac1_project_tests_is_empty_by_default(repo):
    """REQ-010 AC1: rule 5 (adopt leaves it empty)."""
    assert repo.run("config.py", "project_tests").stdout.strip() == ""


def test_ac1_test_patterns_and_mode_are_read(tmp_path):
    """REQ-010 AC1: rules 5 and 9."""
    (tmp_path / "agk.toml").write_text('mode = "adopt"\ntest_patterns = ["*_test.py"]\n')
    cfg = common.load_config(tmp_path)
    assert cfg["mode"] == "adopt" and cfg["test_patterns"] == ["*_test.py"]
