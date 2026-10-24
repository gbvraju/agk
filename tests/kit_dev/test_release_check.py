"""Kit-only tests of `check_release.py`, the release pull request check (SPEC-0028 rules 4 and 5).

A release pull request raises `version` in `agk.toml` in flow mode, changes only five files, moves
the Unreleased lines under the new version and raises the three versions together. No network, no
model.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, git

SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_release.py"
LINES = "- #5 the first change\n- #6 the second change\n"
OLD = f"# Changelog\n\n## Unreleased\n\n{LINES}\n## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
NEW = (
    f"# Changelog\n\n## Unreleased\n\n## 1.1.0 (2026-10-24)\n\n{LINES}\n"
    "## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
)


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def versions(root: Path, agk: str, manifest: str, plugin: str, mode: str = "flow") -> None:
    put(root, "agk.toml", f'version = "{agk}"\npr_mode = "{mode}"\n')
    put(root, "kit/manifest.json", json.dumps({"kit_version": manifest}))
    put(root, ".claude-plugin/plugin.json", json.dumps({"name": "agk", "version": plugin}))


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "kit"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    versions(root, "1.0.0", "1.0.0", "1.0.0")
    put(root, "CHANGELOG.md", OLD)
    put(root, "kit/hashes.json", "{}\n")
    put(root, "README.md", "readme\n")
    put(root, "scripts/agk/check_release.py", "# this check exists on the base\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def release(root: Path, agk="1.1.0", manifest="1.1.0", plugin="1.1.0", changelog=NEW) -> None:
    git(root, "switch", "-q", "-c", "release")
    versions(root, agk, manifest, plugin)
    put(root, "CHANGELOG.md", changelog)
    put(root, "kit/hashes.json", '{"new": 1}\n')


def check(root: Path):
    base = subprocess.run(
        ["git", "rev-parse", "main"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    env = {**clean_env(), "AGK_BASE": base}
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=root, capture_output=True, text=True, env=env
    )


def failed(proc, needle: str) -> None:
    assert proc.returncode == 1, proc.stdout
    assert proc.stdout.startswith("FAIL release: rule 5"), proc.stdout
    assert needle in proc.stdout, proc.stdout


def test_ac4_a_release_that_moves_the_lines_and_raises_the_three_versions_passes(repo):
    """REQ-035 AC4: rules 4 and 5."""
    release(repo)
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout


def test_ac4_a_pull_request_that_raises_no_version_is_not_a_release(repo):
    """REQ-035 AC4: rule 5 (a build pull request is left alone)."""
    git(repo, "switch", "-q", "-c", "build")
    put(repo, "README.md", "a build changes other files\n")
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n")


def test_ac3_in_strict_mode_nothing_is_checked(repo):
    """REQ-035 AC3: rule 5 (a bump with any other file passes as before)."""
    release(repo)
    versions(repo, "1.1.0", "1.1.0", "1.1.0", mode="strict")
    put(repo, "README.md", "strict allows this\n")
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n")


def test_ac5_a_sixth_changed_file_fails_naming_the_path(repo):
    """REQ-035 AC5: rule 5 (exactly the five files)."""
    release(repo)
    put(repo, "README.md", "a sixth file\n")
    failed(check(repo), "README.md")


def test_ac5_a_new_file_outside_the_five_fails(repo):
    """REQ-035 AC5: rule 5 (an untracked file counts as changed)."""
    release(repo)
    put(repo, "scripts/agk/new.py", "x = 1\n")
    failed(check(repo), "scripts/agk/new.py")


@pytest.mark.parametrize(
    ("agk", "manifest", "plugin"),
    [("1.1.0", "1.1.0", "1.0.0"), ("1.1.0", "1.0.0", "1.1.0"), ("1.1.0", "1.2.0", "1.1.0")],
)
def test_ac5_versions_that_differ_fail(repo, agk, manifest, plugin):
    """REQ-035 AC5: rule 5 (the three are raised together)."""
    release(repo, agk, manifest, plugin)
    failed(check(repo), "three versions differ")


@pytest.mark.parametrize("version", ["0.9.0", "0.10.0"])
def test_ac5_versions_that_do_not_rise_fail(repo, version):
    """REQ-035 AC5: rule 5 (greater than the old one, compared as numbers)."""
    release(repo, version, version, version)
    failed(check(repo), "do not rise")


def test_ac5_a_numeric_comparison_accepts_ten_after_nine(repo):
    """REQ-035 AC5: rule 5 (1.10.0 is greater than 1.9.0)."""
    versions(repo, "1.9.0", "1.9.0", "1.9.0")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base at 1.9.0")
    release(repo, "1.10.0", "1.10.0", "1.10.0", NEW.replace("1.1.0", "1.10.0"))
    assert check(repo).stdout == "ok release\n"


def test_ac5_a_line_changed_while_it_is_moved_fails(repo):
    """REQ-035 AC5: rule 5 (moved unchanged and in order)."""
    release(repo, changelog=NEW.replace("the first change", "the first change, reworded"))
    failed(check(repo), "moved unchanged")


def test_ac5_lines_in_another_order_or_dropped_fail(repo):
    """REQ-035 AC5: rule 5."""
    swapped = NEW.replace(LINES, "- #6 the second change\n- #5 the first change\n")
    release(repo, changelog=swapped)
    failed(check(repo), "moved unchanged")
    put(repo, "CHANGELOG.md", NEW.replace(LINES, "- #5 the first change\n"))
    failed(check(repo), "moved unchanged")


def test_ac5_an_unreleased_section_that_is_not_empty_fails(repo):
    """REQ-035 AC5: rule 5 (nothing is left under Unreleased)."""
    release(
        repo, changelog=NEW.replace("## Unreleased\n", "## Unreleased\n\n- #9 left behind\n", 1)
    )
    failed(check(repo), "Unreleased is not empty")


def test_ac5_an_older_release_section_that_changed_fails(repo):
    """REQ-035 AC5: rule 5 (the rest of the changelog is as it was)."""
    release(repo, changelog=NEW.replace("- #1 the start", "- #1 the start, rewritten"))
    failed(check(repo), "moved unchanged")


def test_ac5_a_new_heading_without_the_new_version_fails(repo):
    """REQ-035 AC5: rule 5 (the heading names the new version and a date)."""
    release(repo, changelog=NEW.replace("## 1.1.0 (2026-10-24)", "## 1.2.0 (2026-10-24)"))
    failed(check(repo), "moved unchanged")


def test_ac5_the_messages_name_the_rule_and_never_a_version_value(repo):
    """REQ-035 AC5: rule 5 and CLAUDE.md rule 6 (refusals name the setting or path class)."""
    release(repo, "1.1.0", "1.4.7", "1.1.0")
    proc = check(repo)
    assert "1.4.7" not in proc.stdout and "1.1.0" not in proc.stdout


def test_ac5_the_check_reads_git_and_files_only_and_is_not_installed():
    """REQ-035 AC5: rule 5 (no network; kit-only)."""
    import ast

    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    names |= {
        n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    assert not names & {"socket", "urllib", "http", "requests", "ssl"}
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/check_release.py" not in manifest["verbatim"]


def test_ac5_the_pull_request_that_adds_the_check_is_not_checked_by_it(repo):
    """REQ-035 AC5: rule 9 (the last build that bumps itself; the base has no check yet)."""
    git(repo, "rm", "-q", "scripts/agk/check_release.py")
    git(repo, "commit", "-q", "-m", "a base without the check")
    release(repo)
    put(repo, "README.md", "the adding pull request changes other files and bumps\n")
    put(repo, "scripts/agk/check_release.py", "# added by this pull request\n")
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout
