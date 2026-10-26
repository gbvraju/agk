"""The `Secret scan` step of governance.yml runs the pinned gitleaks binary (brief #258, ADR-0158).

The step has two parts. The first downloads one pinned release archive and verifies its SHA-256
against the digest written in the workflow; it is run here with a stand-in `curl` that writes a
wrong archive, so no test calls the network. The second picks the commits of the change and scans
them; it is run in throwaway repositories with a real gitleaks binary, found on PATH or named by
AGK_GITLEAKS, and skipped with a reason where there is none (governance installs it only in the
step itself, after the tests).

The fake token is built when the test runs, so this file holds no pattern that the scan would flag.
"""

from __future__ import annotations

import os
import random
import shutil
import string
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "governance.yml"
SPLIT = "# 2. The commits of the change"
ZERO = "0" * 40


def scan_block() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    block = text.split("      - name: Secret scan\n", 1)[1].split("\n      - ", 1)[0]
    return block


def run_script() -> str:
    body = scan_block().split("run: |\n", 1)[1]
    return "\n".join(line[10:] for line in body.splitlines())


def env_of(block: str) -> dict[str, str]:
    """The literal `env:` values of the step (the ones without an expression)."""
    out = {}
    part = block.split("        env:\n", 1)[1].split("        run:", 1)[0]
    for line in part.splitlines():
        key, _, value = line.strip().partition(": ")
        if "${{" not in value:
            out[key] = value
    return out


def fake_token() -> str:
    alphabet = string.ascii_letters + string.digits
    body = "".join(random.Random(258).choices(alphabet, k=36))  # nosec B311 - not a secret
    return "gh" + "p_" + body


def gitleaks() -> str | None:
    named = os.environ.get("AGK_GITLEAKS")
    if named and Path(named).is_file():
        return named
    return shutil.which("gitleaks")


needs_gitleaks = pytest.mark.skipif(
    gitleaks() is None,
    reason="no gitleaks binary on PATH or in AGK_GITLEAKS; the governance step itself runs the scan",
)


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def new_repo(path: Path) -> Path:
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "t@example.invalid")
    git(path, "config", "user.name", "t")
    git(path, "config", "commit.gpgsign", "false")
    return path


def commit(repo: Path, name: str, text: str) -> str:
    (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"add {name}")
    return git(repo, "rev-parse", "HEAD")


def scan(tmp_path: Path, repo: Path, **env: str):
    """Run the second part of the step in `repo`, with the binary where the first part puts it."""
    runner = tmp_path / "runner"
    runner.mkdir(exist_ok=True)
    target = runner / "gitleaks"
    if not target.exists():
        target.symlink_to(gitleaks())
    script = SPLIT + run_script().split(SPLIT, 1)[1]
    full = {**os.environ, "RUNNER_TEMP": str(runner), "AGK_BASE": "", "PUSH_BEFORE": ""}
    full.update(env)
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["bash", "-e", "-c", script], cwd=repo, env=full, capture_output=True, text=True
    )


LEAK = f"token = {fake_token()}\n"


# --- the download and its digest (answer 1) -----------------------------------------------------


def test_the_step_fails_when_the_downloaded_archive_does_not_match_the_digest(tmp_path):
    """Brief #258 answer 1: a mismatch fails the step and nothing is unpacked or run."""
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "curl").write_text(
        '#!/bin/sh\nwhile [ "$1" != -o ]; do shift; done\nprintf "not the archive" > "$2"\n',
        encoding="utf-8",
    )
    (stub / "curl").chmod(0o755)
    runner = tmp_path / "runner"
    runner.mkdir()
    script = run_script().split(SPLIT, 1)[0]
    env = {
        **os.environ,
        **env_of(scan_block()),
        "PATH": f"{stub}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(runner),
    }
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["bash", "-e", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert proc.returncode != 0
    assert not (runner / "gitleaks").exists()


# --- the commits of the change (answer 1 and answer 3) ------------------------------------------


@needs_gitleaks
def test_a_pull_request_with_a_leaked_token_in_its_commits_fails(tmp_path):
    """Brief #258 answers 1 and 3: the merge base to the head is scanned, and a finding fails."""
    repo = new_repo(tmp_path / "r")
    base = commit(repo, "a.txt", "clean\n")
    git(repo, "checkout", "-q", "-b", "feature")
    head = commit(repo, "config.env", LEAK)
    proc = scan(tmp_path, repo, EVENT="pull_request", AGK_BASE=base, HEAD_SHA=head)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert fake_token() not in proc.stdout + proc.stderr  # redacted in the log


@needs_gitleaks
def test_a_clean_pull_request_passes_with_a_leak_only_before_its_base(tmp_path):
    """Brief #258 answer 1: on a pull request only the commits of the change are scanned."""
    repo = new_repo(tmp_path / "r")
    commit(repo, "old.env", LEAK)
    base = commit(repo, "old.env", "removed\n")
    git(repo, "checkout", "-q", "-b", "feature")
    head = commit(repo, "b.txt", "clean\n")
    proc = scan(tmp_path, repo, EVENT="pull_request", AGK_BASE=base, HEAD_SHA=head)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@needs_gitleaks
def test_a_push_scans_the_pushed_range(tmp_path):
    """Brief #258 answer 1: on a push, the commits after `before` up to the head."""
    repo = new_repo(tmp_path / "r")
    commit(repo, "old.env", LEAK)
    before = commit(repo, "old.env", "removed\n")
    clean = commit(repo, "b.txt", "clean\n")
    proc = scan(tmp_path, repo, EVENT="push", PUSH_BEFORE=before, HEAD_SHA=clean)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    leaked = commit(repo, "c.env", LEAK)
    proc = scan(tmp_path, repo, EVENT="push", PUSH_BEFORE=before, HEAD_SHA=leaked)
    assert proc.returncode == 1, proc.stdout + proc.stderr


@needs_gitleaks
def test_the_first_push_of_a_repository_scans_the_whole_history(tmp_path):
    """Brief #258 answer 1: `before` is all zeros (or unknown), so every commit is scanned."""
    repo = new_repo(tmp_path / "r")
    commit(repo, "old.env", LEAK)
    head = commit(repo, "old.env", "removed\n")
    for before in (ZERO, "", "1" * 40):
        proc = scan(tmp_path, repo, EVENT="push", PUSH_BEFORE=before, HEAD_SHA=head)
        assert proc.returncode == 1, (before, proc.stdout + proc.stderr)
