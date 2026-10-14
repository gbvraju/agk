"""Fixtures for kit-only tests: run init against throwaway git repositories in tmp_path."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
INIT = KIT_ROOT / "scripts" / "agk" / "init.py"
MANIFEST = KIT_ROOT / "kit" / "manifest.json"


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def clean_env() -> dict[str, str]:
    drop = ("GITHUB_BASE_REF", "AGK_BASE", "CI", "AGK_KIT_TESTS")
    return {k: v for k, v in os.environ.items() if k not in drop}


def run_init(target: Path, *args: str, **kw):
    return subprocess.run(
        [sys.executable, str(INIT), str(target), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
        **kw,
    )


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    """Relative path -> (sha256, mtime_ns) of every file below root, excluding .git."""
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            rel = path.relative_to(root).as_posix()
            out[rel] = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
    return out


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture
def target(tmp_path: Path) -> Path:
    root = tmp_path / "My Project"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("# hello\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "initial")
    return root


@pytest.fixture
def installed(target: Path) -> Path:
    proc = run_init(target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return target


def expected_files() -> set[str]:
    m = manifest()
    return set(m["verbatim"]) | set(m["templates"]) | set(m["rendered"])


def make_repo(root: Path, branch: str = "main") -> Path:
    """A git repository with one commit (a README) on the given branch."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", branch)
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("# hello\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "initial")
    return root
