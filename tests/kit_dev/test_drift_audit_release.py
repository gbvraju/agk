"""D1 of the drift audit exempts a valid release commit (REQ-011, brief #594, SPEC-0004 rule 6).

The per-pull-request check exempts a valid release pull request (`check_protected_changes.
release_pull_request`, SPEC-0028); D1 applies the same check per first-parent commit, so it asks
`check_release.valid_release` about the release part of the commit at its parent, with the
verified Final comments of the parent's records (`--comments FILE`; without them while a record
exists, no exemption). Any other protected file of the commit is still a finding. The release
check is kit-only, so these tests are kit-only too: an installed copy has no exemption. Invented
data only; no network, no model.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env

SCRIPTS = KIT_ROOT / "scripts" / "agk"
TODAY = "2026-10-15"
NEW_LINES = "- #5 the first change\n"
OLD = f"# Changelog\n\n## Unreleased\n\n{NEW_LINES}\n## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
NEW = (
    f"# Changelog\n\n## Unreleased\n\n## 1.1.0 (2026-10-13)\n\n{NEW_LINES}\n"
    "## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
)
PROTECTED = "config/\nagk.toml\nkit/\n.claude-plugin/\nscripts/agk/\n"
RELEASE_CLASSES = [".claude-plugin/", "agk.toml", "kit/"]
FINDING = re.compile(r"^- (D\d) (\S+) \| [^|]+ \| protected class `([^`]+)`")
ADR = "docs/adr/0001-x.md"
RECORD = "Example (#7)\n\nADR-0001 Accepted (Final 42)\nMerged-by: merge_cleared.py\n"


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *args: str, day: str | None = None) -> str:
    env = clean_env()
    if day:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{day}T12:00:00+0000"
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True, env=env
    )
    return proc.stdout


def commit(root: Path, message: str, day: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message, day=day)
    return git(root, "rev-parse", "HEAD").strip()


def versions(root: Path, agk: str, manifest: str, plugin: str) -> None:
    put(root, "agk.toml", f'version = "{agk}"\npr_mode = "flow"\n')
    put(root, "kit/manifest.json", json.dumps({"kit_version": manifest}))
    put(root, ".claude-plugin/plugin.json", json.dumps({"name": "agk", "version": plugin}))


def adr(status: str) -> str:
    return f"# ADR-0001: x\n\n- Status: {status}\n- Date: 2026-09-01\n\n## Decision\n\nd\n"


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
    put(root, "config/protected-paths.txt", PROTECTED)
    put(root, "scripts/agk/check_release.py", "# this check exists on the base\n")
    commit(root, "base", "2026-09-01")
    return root


def release(root: Path, manifest: str = "1.1.0", **extra: str) -> str:
    """A release commit on the default branch two days before TODAY, with the files of EXTRA."""
    versions(root, "1.1.0", manifest, "1.1.0")
    put(root, "CHANGELOG.md", NEW)
    put(root, "kit/hashes.json", '{"new": 1}\n')
    for rel, text in extra.items():
        put(root, rel.replace("__", "/"), text)
    return commit(root, "release: the kit 1.1.0 (#9)", "2026-10-13")


def audit(root: Path, *args: str, scripts: Path = SCRIPTS) -> list[tuple[str, str, str]]:
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(scripts / "drift_audit.py"), "--today", TODAY, *args],
        cwd=root,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return [m.groups() for line in proc.stdout.splitlines() if (m := FINDING.match(line))]


def d1(root: Path, *args: str, scripts: Path = SCRIPTS) -> list[tuple[str, str]]:
    return [(sha, cls) for code, sha, cls in audit(root, *args, scripts=scripts) if code == "D1"]


def test_ac1_a_valid_release_commit_gives_no_d1(repo):
    """REQ-011 AC1: SPEC-0004 rule 6 as amended (amendment 121): a valid release is exempt."""
    release(repo)
    assert d1(repo) == []


def test_ac1_a_release_that_also_touches_another_protected_file_gives_d1_for_that_class_only(repo):
    """REQ-011 AC1: rule 6 as amended: any other protected file of the commit is still a finding."""
    sha = release(repo, config__extra__txt="x\n")
    assert d1(repo) == [(sha[:12], "config/")]


def test_ac1_another_file_of_a_release_class_keeps_that_class_a_finding(repo):
    """REQ-011 AC1: rule 6 as amended: only the release files are exempt, not their classes."""
    sha = release(repo, kit__other__txt="x\n")
    assert d1(repo) == [(sha[:12], "kit/")]


def test_ac1_an_invalid_release_gives_d1_as_today(repo):
    """REQ-011 AC1: rule 6: the three versions differ, so it is no release: every class counts."""
    sha = release(repo, manifest="1.0.5")
    assert d1(repo) == [(sha[:12], c) for c in RELEASE_CLASSES]


def test_ac1_a_raised_version_alone_is_no_release(repo):
    """REQ-011 AC1: rule 6: the Unreleased lines were not moved, so the release check fails."""
    versions(repo, "1.1.0", "1.1.0", "1.1.0")
    sha = commit(repo, "bump only", "2026-10-13")
    assert d1(repo) == [(sha[:12], c) for c in RELEASE_CLASSES]


def final_comments(root: Path) -> str:
    """The Final comment of the record, as `gh api repos/{repo}/issues/comments/<id>` gives it."""
    item = {
        "id": 42,
        "issue_url": "https://api.example.com/repos/example-owner/example-repo/issues/7",
        "user": {"login": "reviewer"},
        "body": f"Verdict: fix list a1b2c3d\n\nreviewed.\n\nFinal: {ADR} Proposed -> Accepted\n",
    }
    path = root.parent / "final-comments.json"
    path.write_text(json.dumps([item]), encoding="utf-8")
    return str(path)


def recorded_release(root: Path) -> str:
    put(root, "config/reviewers.yaml", "version: 1\nverdict_authors: [reviewer]\n")
    put(root, ADR, adr("Proposed"))
    commit(root, "reviewers", "2026-09-02")
    git(root, "commit", "-q", "--allow-empty", "-m", RECORD, day="2026-09-03")
    return release(root, **{ADR.replace("/", "__"): adr("Accepted")})


def test_ac1_with_a_record_on_the_parent_the_release_needs_the_verified_final_comments(repo):
    """REQ-011 AC1: rule 6 as amended: without the Final comments of the parent's records, no
    exemption (fail closed, as the release check of #558); with them, the release is exempt."""
    sha = recorded_release(repo)
    assert d1(repo) == [(sha[:12], c) for c in RELEASE_CLASSES]
    assert d1(repo, "--comments", final_comments(repo)) == []


def test_ac1_an_unreadable_comments_file_gives_no_exemption(repo, tmp_path):
    """REQ-011 AC1: rule 6 as amended: an unreadable file is no exemption."""
    sha = recorded_release(repo)
    missing = str(tmp_path / "missing.json")
    assert d1(repo, "--comments", missing) == [(sha[:12], c) for c in RELEASE_CLASSES]


def test_ac1_without_the_release_check_there_is_no_exemption(repo, tmp_path):
    """REQ-011 AC1: check_release.py is kit-only, so an installed copy of the audit has none."""
    sha = release(repo)
    copy = tmp_path / "installed"
    shutil.copytree(SCRIPTS, copy, ignore=shutil.ignore_patterns("check_release.py", "__pycache__"))
    assert d1(repo, scripts=copy) == [(sha[:12], c) for c in RELEASE_CLASSES]


def full_snapshot(root: Path) -> dict[str, str]:
    """Every file below ROOT, `.git` included, by content."""
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_ac3_judging_a_release_writes_nothing_in_the_repository(repo):
    """REQ-011 AC3: SPEC-0004 rule 2: the release is judged in a temporary copy outside the
    checkout, removed after the run; the repository and its `.git` are unchanged."""
    recorded_release(repo)
    before = full_snapshot(repo)
    comments = final_comments(repo)
    assert d1(repo, "--comments", comments) == []
    assert full_snapshot(repo) == before
    assert set(os.listdir(repo.parent)) == {"kit", "final-comments.json"}
