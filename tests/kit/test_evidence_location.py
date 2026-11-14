"""In local mode the evidence record lives in one shared place per clone (brief #1269, ADR-0536).

`prepush.py --record` with no FILE (or `--record auto`) writes the record to
`<git common dir>/agk-evidence/<40-hex head>.json`: the folder `git rev-parse --git-common-dir`
names, shared by every worktree of the clone, never tracked and never making the tree dirty.
`evidence.py check --head <sha>` with no RECORD reads that file, so the conductor finds the
record from the head alone; a missing one exits 3 naming the option, never a path. `--record FILE`
and `check FILE` behave as before.

The fixture repositories are those of `test_prepush.py` and `test_evidence.py`: a stand-in
`agk.mk`, `Makefile` and `gitleaks`, with the lock and temp folders outside the repository.
Invented data only.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from test_evidence import LINE, check, project, worktrees
from test_prepush import path_with, scanner

EVIDENCE = re.compile(
    r"^Evidence: prepush schema 1, head ([0-9a-f]{12}), (\d+) steps ok, record ([0-9a-f]{12})$",
    re.M,
)
MISSING = "evidence: no record for this head in the shared evidence folder (option: --record)"


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    """A folder outside the fixture repository: the lock folder, the temp folder, the worktree."""
    return tmp_path_factory.mktemp("outside")


def shared(repo) -> Path:
    """The clone's shared evidence folder, as git names its common dir."""
    common = repo.git("rev-parse", "--git-common-dir").strip()
    return (repo.root / common).resolve() / "agk-evidence"


def second_worktree(repo, outside: Path):
    """A second worktree of the same clone, detached at the head, as a fixture repository."""
    path = outside / "wt"
    repo.git("worktree", "add", "-q", "--detach", str(path), "HEAD")
    return type(repo)(path)


@pytest.mark.parametrize("args", [["--record"], ["--record", "auto"], ["--record", "--no-lock"]])
def test_record_without_a_file_goes_to_the_shared_folder_and_the_tree_stays_clean(
    repo, outside, args
):
    """REQ-039: brief #1269 answers 1 and 4 (a): the record of the head is written to
    `<git common dir>/agk-evidence/<head>.json`; the tree stays clean and the `Evidence:` line is
    unchanged."""
    project(repo, outside)
    head = repo.git("rev-parse", "HEAD").strip()
    proc = repo.run("prepush.py", *args, PATH=path_with(scanner(outside / "bin", 0)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record = shared(repo) / f"{head}.json"
    assert record.is_file(), proc.stdout
    assert repo.git("status", "--porcelain") == ""
    assert '"tree_clean": true' in record.read_text(encoding="utf-8")
    found = EVIDENCE.search(proc.stdout)
    assert found and found.group(1) == head[:12], proc.stdout
    assert found.group(3) == hashlib.sha256(record.read_bytes()).hexdigest()[:12]
    assert str(record) not in proc.stdout + proc.stderr  # the line names the digest, not a path


def test_the_check_from_another_worktree_finds_the_record_from_the_head_alone(repo, outside):
    """REQ-039: brief #1269 answers 2 and 4 (b): `check --head <sha>` with no RECORD, run in
    another worktree of the clone, reads the shared record and agrees."""
    project(repo, outside)
    scan = scanner(outside / "bin", 0)
    made = repo.run("prepush.py", "--record", PATH=path_with(scan))
    assert made.returncode == 0, made.stdout + made.stderr
    head = repo.git("rev-parse", "HEAD").strip()
    other = second_worktree(repo, outside)
    proc = check(other, outside, "--head", head, scan=scan)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    found = LINE.search(proc.stdout)
    assert found and found.group(1) == "agrees", proc.stdout
    assert found.group(2) == head[:12]
    record = shared(repo) / f"{head}.json"
    assert found.group(3) == hashlib.sha256(record.read_bytes()).hexdigest()[:12]
    assert EVIDENCE.search(made.stdout).group(3) == found.group(3)
    assert worktrees(repo) == 2  # the check's own worktree is removed again


def test_a_record_written_in_a_second_worktree_lands_in_the_same_folder(repo, outside):
    """REQ-039: brief #1269 answer 1 (the folder is the clone's, shared by every worktree)."""
    project(repo, outside)
    other = second_worktree(repo, outside)
    head = other.git("rev-parse", "HEAD").strip()
    proc = other.run("prepush.py", "--record", PATH=path_with(scanner(outside / "bin", 0)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert shared(other) == shared(repo)
    assert (shared(repo) / f"{head}.json").is_file()
    assert other.git("status", "--porcelain") == ""


def test_a_missing_record_exits_3_naming_the_option_never_a_path(repo, outside):
    """REQ-039: brief #1269 answers 2 and 4 (c)."""
    project(repo, outside)
    head = repo.git("rev-parse", "HEAD").strip()
    proc = check(repo, outside, "--head", head)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert proc.stderr.strip() == MISSING
    assert "agk-evidence" not in proc.stdout and worktrees(repo) == 1


def test_a_record_of_another_head_in_the_folder_is_not_taken(repo, outside):
    """REQ-039: brief #1269 answer 2 (the file is named by the head the check is given)."""
    project(repo, outside)
    made = repo.run("prepush.py", "--record", PATH=path_with(scanner(outside / "bin", 0)))
    assert made.returncode == 0, made.stdout + made.stderr
    older = repo.git("rev-parse", "HEAD~1").strip()
    proc = check(repo, outside, "--head", older)
    assert proc.returncode == 3 and proc.stderr.strip() == MISSING


def test_check_without_a_record_or_a_head_is_a_usage_error(repo, outside):
    """REQ-039: brief #1269 answer 2 (RECORD is optional only with `--head`)."""
    project(repo, outside)
    proc = check(repo, outside, "--sample", "2")
    assert proc.returncode == 2 and proc.stderr.startswith("usage: evidence.py check")


def test_record_file_and_check_file_behave_as_before(repo, outside):
    """REQ-039: brief #1269 answer 4 (d): `--record FILE` writes FILE and nothing in the shared
    folder; `check FILE --head <sha>` reads FILE."""
    project(repo, outside)
    scan = scanner(outside / "bin", 0)
    record = outside / "record.json"
    made = repo.run("prepush.py", "--record", str(record), PATH=path_with(scan))
    assert made.returncode == 0, made.stdout + made.stderr
    assert record.is_file() and not shared(repo).exists()
    head = repo.git("rev-parse", "HEAD").strip()
    proc = check(repo, outside, str(record), "--head", head, scan=scan)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert LINE.search(proc.stdout).group(1) == "agrees"
