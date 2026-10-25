"""A release pull request needs no ADR for the protected files it must change (REQ-035, brief #212).

`check_protected_changes.py` treats a pull request as a release when every file it changes is one
the release check allows (or a deleted fragment) and `check_release.py` passes on it (SPEC-0028
rules 4 and 5). Any other file, or a release that fails its own check, loses the exemption, and an
ordinary protected change still needs its ADR. The release check is kit-only: a project, which
does not have it, has no exemption. No network, no model.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, git

NEW_LINES = "- #5 the first change\n"
OLD = f"# Changelog\n\n## Unreleased\n\n{NEW_LINES}\n## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
NEW = (
    f"# Changelog\n\n## Unreleased\n\n## 1.1.0 (2026-10-24)\n\n{NEW_LINES}\n"
    "## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
)
PROTECTED = "config/\nagk.toml\nkit/\n.claude-plugin/\nscripts/agk/\n"
SCRIPTS = KIT_ROOT / "scripts" / "agk"


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def versions(root: Path, version: str, mode: str = "flow") -> None:
    put(root, "agk.toml", f'version = "{version}"\npr_mode = "{mode}"\n')
    put(root, "kit/manifest.json", json.dumps({"kit_version": version}))
    put(root, ".claude-plugin/plugin.json", json.dumps({"name": "agk", "version": version}))


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "kit"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    versions(root, "1.0.0")
    put(root, "CHANGELOG.md", OLD)
    put(root, "kit/hashes.json", "{}\n")
    put(root, "README.md", "readme\n")
    put(root, "config/protected-paths.txt", PROTECTED)
    put(root, "scripts/agk/check_release.py", "# this check exists on the base\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def release(root: Path, **changed: str) -> None:
    """A valid release pull request, then the extra files in `changed`."""
    git(root, "switch", "-q", "-c", "release")
    versions(root, "1.1.0")
    put(root, "CHANGELOG.md", NEW)
    put(root, "kit/hashes.json", '{"new": 1}\n')
    for rel, text in changed.items():
        put(root, rel.replace("__", "/"), text)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "release")


def check(root: Path, scripts: Path = SCRIPTS):
    base = subprocess.run(
        ["git", "rev-parse", "main"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    env = {**clean_env(), "AGK_BASE": base}
    return subprocess.run(
        [sys.executable, str(scripts / "check_protected_changes.py")],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )


def test_ac4_a_valid_release_needs_no_adr_for_the_files_it_must_change(repo):
    """REQ-035 AC4: the first flow-mode release changes agk.toml, kit/ and .claude-plugin/."""
    release(repo)
    proc = check(repo)
    assert (proc.returncode, proc.stdout) == (0, "ok protected-changes (a release pull request)\n")


def test_ac4_one_more_file_removes_the_exemption(repo):
    """REQ-035 AC4: an unprotected file and a protected one both fail the release check."""
    release(repo, README__md="changed\n")
    proc = check(repo)
    assert proc.returncode == 1 and "protected path class 'agk.toml'" in proc.stdout
    git(repo, "switch", "-q", "main")
    git(repo, "branch", "-q", "-D", "release")
    release(repo, config__x="changed\n")
    assert check(repo).returncode == 1


def test_ac4_a_release_that_fails_its_own_check_is_not_exempt(repo):
    """REQ-035 AC4: the three versions must agree."""
    release(repo)
    put(repo, "kit/manifest.json", json.dumps({"kit_version": "1.0.5"}))
    git(repo, "commit", "-qam", "versions differ")
    assert check(repo).returncode == 1


def test_ac4_an_ordinary_protected_change_still_needs_its_adr(repo):
    """REQ-035 AC4: no version is raised, so nothing is a release."""
    git(repo, "switch", "-q", "-c", "build")
    put(repo, "kit/hashes.json", '{"x": 1}\n')
    git(repo, "commit", "-qam", "build")
    proc = check(repo)
    assert proc.returncode == 1 and "protected path class 'kit/'" in proc.stdout


def test_ac4_in_strict_mode_nothing_is_a_release(repo):
    """REQ-035 AC4: SPEC-0028 rule 4 is a flow-mode rule."""
    versions(repo, "1.0.0", "strict")
    git(repo, "commit", "-qam", "strict")
    release(repo)
    versions(repo, "1.1.0", "strict")
    git(repo, "commit", "-qam", "strict release")
    assert check(repo).returncode == 1


def test_ac4_without_the_release_check_there_is_no_exemption(repo, tmp_path):
    """REQ-035 AC4: check_release.py is kit-only, so a project that has this script has none."""
    release(repo)
    copy = tmp_path / "installed"
    shutil.copytree(SCRIPTS, copy, ignore=shutil.ignore_patterns("check_release.py", "__pycache__"))
    assert check(repo, copy).returncode == 1
