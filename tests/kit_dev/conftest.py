"""Fixtures for kit-only tests: run init against throwaway git repositories in tmp_path."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
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


def without_version_line(proc):
    """PROC with the first line of its output (`intake: kit <version>`, SPEC-0027) taken off."""
    first, _, rest = proc.stdout.partition("\n")
    if first.startswith("intake: kit "):
        proc.stdout = rest
    return proc


def run_init(target: Path, *args: str, **kw):
    return subprocess.run(
        [sys.executable, str(INIT), str(target), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
        **kw,
    )


def set_handle(root: Path, handle: str = "@demo-maintainer") -> None:
    """Step 4 of the getting-started guide: a real handle for `maintainers`, then CODEOWNERS.

    `@REPLACE-ME` is never a listed verdict author (SPEC-0021 rule 5), so `reviewers.py --check`
    fails until the handle is set."""
    path = root / "config" / "reviewers.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("@REPLACE-ME", handle))
    proc = subprocess.run(
        [sys.executable, "scripts/agk/reviewers.py", "--codeowners", "--write"],
        cwd=root,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


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


def assert_lean(listed: set[str]) -> None:
    """The listed files that are not tests of the kit are installed; the tests stay in the kit.

    Lean install (ADR-0052): nothing under `tests/kit/` is in the manifest, so no target has it.
    """
    m = manifest()
    installed = {p for p in listed if not p.startswith("tests/kit/")}
    assert installed <= set(m["verbatim"]) and installed <= expected_files()
    for rel in listed - installed:
        assert (KIT_ROOT / rel).is_file(), rel
        assert rel not in m["verbatim"] and rel not in expected_files(), rel


def kit_fixture_files(rel: str) -> set[str]:
    """The files of one fixture folder of the kit repository (they are not installed)."""
    return {p.relative_to(KIT_ROOT).as_posix() for p in (KIT_ROOT / rel).rglob("*") if p.is_file()}


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


# --- One installed target shared by the tests that run the kit suite in a target ---------------
#
# Running `make test` or `make -f agk.mk agk-test` in an installed repository runs the kit
# suite (about a minute). test_init.py used to do that six times, each in a fresh install of its
# own. Now the kit is installed once per session (`shared_install`, never run in), a test that
# needs a target takes a copy of it, and the two commands whose own result is asserted are each run
# once, in a copy: `make test` (the alias) and `make -f agk.mk agk-test` (the direct form). A test
# that is about the project's tests runs `make -o agk-test test`: the same `test` target with the
# phony prerequisite `agk-test` treated as up to date, so the kit suite is not run again.


@dataclass
class Run:
    returncode: int
    stdout: str
    stderr: str


@pytest.fixture(scope="session")
def shared_install(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("shared") / "My Project"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("# hello\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "initial")
    proc = run_init(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    set_handle(root)
    return root


def copy_of(shared: Path, dest: Path) -> Path:
    """A copy of the shared install, git history included, to run in or to change."""
    target = dest / shared.name
    shutil.copytree(shared, target, symlinks=True)
    return target


@pytest.fixture
def shared_copy(shared_install: Path, tmp_path: Path) -> Path:
    return copy_of(shared_install, tmp_path)


def run_make(root: Path, *args: str) -> Run:
    proc = subprocess.run(
        ["make", *args], cwd=root, capture_output=True, text=True, env=clean_env()
    )
    return Run(proc.returncode, proc.stdout, proc.stderr)


@dataclass
class KitSuite:
    alias: Run  # `make test` in a copy of the shared install (no project tests of its own)
    direct: Run  # `make -f agk.mk agk-test` in another copy


@pytest.fixture(scope="session")
def kit_suite(shared_install: Path, tmp_path_factory) -> KitSuite:
    alias = run_make(copy_of(shared_install, tmp_path_factory.mktemp("alias")), "test")
    direct = run_make(
        copy_of(shared_install, tmp_path_factory.mktemp("direct")), "-f", "agk.mk", "agk-test"
    )
    return KitSuite(alias, direct)
