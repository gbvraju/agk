"""The `Secret scan` step of governance.yml runs the pinned gitleaks binary (brief #258, ADR-0158).

The step has two parts. The first downloads one pinned release archive and verifies its SHA-256
against the digest written in the workflow; it is run here with a stand-in `curl` that writes a
wrong archive, so no test calls the network. The second picks the commits of the change and scans
them; it is run in throwaway repositories with a real gitleaks binary, found on PATH or named by
AGK_GITLEAKS, and skipped with a reason where there is none (governance installs it only in the
step itself, after the tests).

The first part also restores a cached copy of the archive (brief #275, ADR-0171): a cached copy
is used only when it matches the digest, a verified download is left where the cache action saves
it, and a failed download prints one plain line.
Those tests use a stand-in archive with its own digest.

The fake token is built when the test runs, so this file holds no pattern that the scan would flag.
"""

from __future__ import annotations

import hashlib
import io
import os
import random
import shutil
import string
import subprocess  # nosec B404 - fixed argument lists only, no shell
import tarfile
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
    reason="no gitleaks binary on PATH or in AGK_GITLEAKS; the governance step runs the scan",
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


def found(proc) -> bool:
    """Exit 1 because of a finding, not because the scan could not run."""
    log = proc.stdout + proc.stderr
    return proc.returncode == 1 and "leaks found" in log and "no leaks found" not in log


def clean(proc) -> bool:
    return proc.returncode == 0 and "no leaks found" in proc.stdout + proc.stderr


# --- the download, the cached copy and its digest (brief #258 answer 1, brief #275) --------------

CURL_STUB = """#!/bin/sh
# A stand-in for curl: records the call, writes STUB_ARCHIVE (or an error page) to the -o path,
# prints STUB_CODE as the write-out and exits STUB_EXIT. A raw curl error line goes to stderr when
# the step asks curl to show errors (-S), as the real one would.
printf 'called\\n' >> "$STUB_CALLS"
out=""
for arg in "$@"; do
  case "$arg" in
    --*) ;;
    -*S*) echo "curl: (22) The requested URL returned error: $STUB_CODE" >&2 ;;
  esac
done
while [ $# -gt 0 ]; do
  if [ "$1" = -o ]; then out="$2"; shift; fi
  shift
done
if [ -n "$STUB_ARCHIVE" ]; then cat "$STUB_ARCHIVE" > "$out"
else printf 'upstream timeout' > "$out"; fi
printf '%s' "$STUB_CODE"
exit "${STUB_EXIT:-0}"
"""


def stand_in_archive(path: Path) -> str:
    """A tar.gz holding a file `gitleaks`; returns its SHA-256."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"#!/bin/sh\necho stand-in gitleaks\n"
        info = tarfile.TarInfo("gitleaks")
        info.size = len(data)
        info.mode = 0o755
        tar.addfile(info, io.BytesIO(data))
    path.write_bytes(buf.getvalue())
    return hashlib.sha256(buf.getvalue()).hexdigest()


class Fetch:
    """The first part of the step, run with the stand-in curl in a throwaway runner directory."""

    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.runner = tmp_path / "runner"
        self.runner.mkdir()
        self.cache = self.runner / "gitleaks-cache"
        self.calls = tmp_path / "curl-calls"
        stub = tmp_path / "bin"
        stub.mkdir()
        (stub / "curl").write_text(CURL_STUB, encoding="utf-8")
        (stub / "curl").chmod(0o755)
        self.path = f"{stub}{os.pathsep}{os.environ['PATH']}"
        self.literal = env_of(scan_block())
        self.archive_name = f"gitleaks_{self.literal['GITLEAKS_VERSION']}_linux_x64.tar.gz"

    def run(
        self,
        *,
        digest: str | None = None,
        code: str = "200",
        exit_code: int = 0,
        archive: Path | None = None,
    ):
        env = {
            **os.environ,
            **self.literal,
            "PATH": self.path,
            "RUNNER_TEMP": str(self.runner),
            "STUB_CALLS": str(self.calls),
            "STUB_CODE": code,
            "STUB_EXIT": str(exit_code),
            "STUB_ARCHIVE": str(archive) if archive else "",
        }
        if digest:
            env["GITLEAKS_SHA256"] = digest
        script = run_script().split(SPLIT, 1)[0]
        return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["bash", "-e", "-c", script], cwd=self.tmp, env=env, capture_output=True, text=True
        )

    def curl_called(self) -> bool:
        return self.calls.exists()


def test_the_step_fails_when_the_downloaded_archive_does_not_match_the_digest(tmp_path):
    """Brief #258 answer 1: a mismatch fails the step and nothing is unpacked or run; brief #275
    answer 1: nor is the archive left for the cache to save."""
    fetch = Fetch(tmp_path)
    wrong = tmp_path / "wrong.tar.gz"
    wrong.write_bytes(b"not the archive")
    proc = fetch.run(archive=wrong)
    assert proc.returncode != 0
    assert not (fetch.runner / "gitleaks").exists()
    assert not (fetch.cache / fetch.archive_name).exists()


@pytest.mark.parametrize("code,exit_code", [("504", 0), ("404", 0), ("000", 7)])
def test_a_failed_download_with_no_cached_copy_fails_with_one_plain_line(tmp_path, code, exit_code):
    """Brief #275 answer 2: one line naming the cause and the fix, no raw curl line, no skip."""
    fetch = Fetch(tmp_path)
    proc = fetch.run(code=code, exit_code=exit_code)
    assert proc.returncode != 0
    lines = [line for line in (proc.stdout + proc.stderr).splitlines() if line.strip()]
    assert lines == [
        f"could not download the secret scanner from GitHub (HTTP {code}); re-run the job"
    ], lines
    assert not (fetch.runner / "gitleaks").exists()
    assert not (fetch.cache / fetch.archive_name).exists()


def test_a_cached_copy_that_matches_the_digest_is_used_with_no_download(tmp_path):
    """Brief #275 answer 1: restored before downloading, and checked on use."""
    fetch = Fetch(tmp_path)
    fetch.cache.mkdir()
    digest = stand_in_archive(fetch.cache / fetch.archive_name)
    proc = fetch.run(digest=digest, code="504")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not fetch.curl_called()
    assert (fetch.runner / "gitleaks").is_file()


def test_a_cached_copy_that_does_not_match_is_discarded_and_downloaded_again(tmp_path):
    """Brief #275 answer 1: the checksum is checked on every use; a bad cached copy is never run."""
    fetch = Fetch(tmp_path)
    fetch.cache.mkdir()
    (fetch.cache / fetch.archive_name).write_bytes(b"a corrupted copy")
    good = tmp_path / "good.tar.gz"
    digest = stand_in_archive(good)
    proc = fetch.run(digest=digest, archive=good)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert fetch.curl_called()
    assert (fetch.cache / fetch.archive_name).read_bytes() == good.read_bytes()
    assert (fetch.runner / "gitleaks").is_file()


def test_a_cached_copy_that_does_not_match_and_a_failed_download_fail(tmp_path):
    """Brief #275 answers 1 and 2: a bad cached copy is no fallback; the plain line is printed."""
    fetch = Fetch(tmp_path)
    fetch.cache.mkdir()
    (fetch.cache / fetch.archive_name).write_bytes(b"a corrupted copy")
    good = tmp_path / "good.tar.gz"
    digest = stand_in_archive(good)
    proc = fetch.run(digest=digest, code="503")
    assert proc.returncode != 0
    assert (
        "could not download the secret scanner from GitHub (HTTP 503); re-run the job"
        in proc.stdout + proc.stderr
    )
    assert not (fetch.runner / "gitleaks").exists()


def test_a_verified_download_is_left_where_the_cache_action_saves_it(tmp_path):
    """Brief #275 answer 1: saved after a verified download (the cache action saves that path)."""
    fetch = Fetch(tmp_path)
    good = tmp_path / "good.tar.gz"
    digest = stand_in_archive(good)
    proc = fetch.run(digest=digest, archive=good)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert fetch.curl_called()
    assert (fetch.cache / fetch.archive_name).read_bytes() == good.read_bytes()
    assert (fetch.runner / "gitleaks").is_file()


# --- the commits of the change (answer 1 and answer 3) ------------------------------------------


@needs_gitleaks
def test_a_pull_request_with_a_leaked_token_in_its_commits_fails(tmp_path):
    """Brief #258 answers 1 and 3: the merge base to the head is scanned, and a finding fails."""
    repo = new_repo(tmp_path / "r")
    base = commit(repo, "a.txt", "clean\n")
    git(repo, "checkout", "-q", "-b", "feature")
    head = commit(repo, "config.env", LEAK)
    proc = scan(tmp_path, repo, EVENT="pull_request", AGK_BASE=base, HEAD_SHA=head)
    assert found(proc), proc.stdout + proc.stderr
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
    assert clean(proc), proc.stdout + proc.stderr


@needs_gitleaks
def test_a_push_scans_the_pushed_range(tmp_path):
    """Brief #258 answer 1: on a push, the commits after `before` up to the head."""
    repo = new_repo(tmp_path / "r")
    commit(repo, "old.env", LEAK)
    before = commit(repo, "old.env", "removed\n")
    tidy = commit(repo, "b.txt", "clean\n")
    proc = scan(tmp_path, repo, EVENT="push", PUSH_BEFORE=before, HEAD_SHA=tidy)
    assert clean(proc), proc.stdout + proc.stderr
    leaked = commit(repo, "c.env", LEAK)
    proc = scan(tmp_path, repo, EVENT="push", PUSH_BEFORE=before, HEAD_SHA=leaked)
    assert found(proc), proc.stdout + proc.stderr


@needs_gitleaks
def test_the_first_push_of_a_repository_scans_the_whole_history(tmp_path):
    """Brief #258 answer 1: `before` is all zeros (or unknown), so every commit is scanned."""
    repo = new_repo(tmp_path / "r")
    commit(repo, "old.env", LEAK)
    head = commit(repo, "old.env", "removed\n")
    for before in (ZERO, "", "1" * 40):
        proc = scan(tmp_path, repo, EVENT="push", PUSH_BEFORE=before, HEAD_SHA=head)
        assert found(proc), (before, proc.stdout + proc.stderr)


@needs_gitleaks
def test_the_workflow_itself_holds_nothing_the_scan_flags(tmp_path):
    """Brief #275: a literal cache key after `key:` was flagged as a generic API key on the first
    run; the key is built from the pins, so the workflow passes the scan's default rules."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [gitleaks(), "dir", "--no-banner", "--redact", "--exit-code", "1", str(WORKFLOW)],
        capture_output=True,
        text=True,
    )
    assert clean(proc), proc.stdout + proc.stderr
