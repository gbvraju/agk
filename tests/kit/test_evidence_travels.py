"""Local evidence travels with the pushed branch as a git note (brief #1447, ADR-0605).

In local mode (`execution = "local"`, no `[personal]` table) `prepush.py --record` with no FILE also
writes the record, byte for byte, as a git note on the head under `refs/notes/agk-evidence`, after
the secret guard has read it. `evidence.py push --branch <b>` sends that ref with the branch.
`evidence.py check --head <sha>`, when the clone's shared folder has no record, fetches the notes
ref of `origin` and reads the note of that head; the check then runs as for a local record.

Two machines are two clones of one bare remote on disk; machine A builds in a worktree (a local-
mode main folder refuses a push off the default branch). Invented data only, no network.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_evidence import LINE, check
from test_evidence_location import EVIDENCE, MISSING, shared
from test_prepush import LINT_OK, MK_OK, TOML, path_with, scanner

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import prepush  # noqa: E402

REF = "refs/notes/agk-evidence"
LOCAL = 'execution = "local"\n'
PERSONAL = '\n[personal]\nforge = "files"\n'


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("outside")


def machine_a(repo, outside: Path, settings: str = LOCAL, tables: str = ""):
    """Machine A: the project on `main`, pushed to a bare remote, and a worktree on `feature`."""
    origin = outside / "origin.git"
    repo.git("init", "-q", "--bare", str(origin))
    toml = TOML + settings + f"lock_dir = '{outside / 'locks'}'\n" + tables
    files = {"agk.toml": toml, "agk.mk": MK_OK, "Makefile": LINT_OK, "src/a.txt": "a\n"}
    repo.commit(files, "base")
    repo.git("remote", "add", "origin", str(origin))
    repo.git("push", "-q", "origin", "main")
    path = outside / "a"
    repo.git("worktree", "add", "-q", "-b", "feature", str(path))
    a = type(repo)(path)
    a.commit({"src/a.txt": "b\n", "tests/test_new.py": "# new\n"}, "change")
    return a, origin


def machine_b(repo, outside: Path, origin: Path):
    """Machine B: a second clone of the remote, as the conductor's machine."""
    path = outside / "b"
    repo.git("clone", "-q", str(origin), str(path))
    b = type(repo)(path)
    b.git("config", "user.email", "member-example-1@example.com")
    b.git("config", "user.name", "member-example-1")
    return b


def record_and_push(a, outside: Path, scan: Path):
    made = a.run("prepush.py", "--record", PATH=path_with(scan))
    assert made.returncode == 0, made.stdout + made.stderr
    pushed = a.run("evidence.py", "push", "--branch", "feature")
    assert pushed.returncode == 0, pushed.stdout + pushed.stderr
    return made


def notes(repo) -> str:
    return repo.git("notes", "--ref", "agk-evidence", "list")


def test_a_record_made_on_machine_a_agrees_on_machine_b_from_the_note(repo, outside):
    """REQ-039: brief #1447 answers 1, 2 and 7 (a record on machine A checked on machine B); the
    digest the check prints is the one of the builder's `Evidence:` line."""
    a, origin = machine_a(repo, outside)
    scan = scanner(outside / "bin", 0)
    made = record_and_push(a, outside, scan)
    assert "evidence.py push --branch feature" in made.stdout
    head = a.git("rev-parse", "HEAD").strip()
    assert head in notes(a)
    b = machine_b(repo, outside, origin)
    assert not (shared(b) / f"{head}.json").exists()
    proc = check(b, outside, "--head", head, scan=scan)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    found = LINE.search(proc.stdout)
    assert found and found.group(1) == "agrees", proc.stdout
    assert found.group(3) == EVIDENCE.search(made.stdout).group(3)
    assert f"(ref: {REF})" in proc.stdout


def test_no_note_and_no_folder_record_exits_3_as_today(repo, outside):
    """REQ-039: brief #1447 answer 7 (no note and no folder record)."""
    a, origin = machine_a(repo, outside)
    a.git("push", "-q", "origin", "feature")
    b = machine_b(repo, outside, origin)
    proc = check(b, outside, "--head", a.git("rev-parse", "HEAD").strip())
    assert proc.returncode == 3 and proc.stderr.strip() == MISSING


def test_a_note_only_for_another_head_is_not_taken(repo, outside):
    """REQ-039: brief #1447 answer 7 (a note for another head): the note is read by the head."""
    a, origin = machine_a(repo, outside)
    record_and_push(a, outside, scanner(outside / "bin", 0))
    a.commit({"src/a.txt": "c\n"}, "newer")
    a.git("push", "-q", "origin", "feature")
    b = machine_b(repo, outside, origin)
    proc = check(b, outside, "--head", a.git("rev-parse", "HEAD").strip())
    assert proc.returncode == 3 and proc.stderr.strip() == MISSING


def test_a_note_holding_the_record_of_another_head_is_stale(repo, outside):
    """REQ-039: brief #1447 answers 3 and 7: a note on head H whose record names another head."""
    a, origin = machine_a(repo, outside)
    record_and_push(a, outside, scanner(outside / "bin", 0))
    old = a.git("rev-parse", "HEAD").strip()
    a.commit({"src/a.txt": "c\n"}, "newer")
    new = a.git("rev-parse", "HEAD").strip()
    a.git("notes", "--ref", "agk-evidence", "copy", old, new)
    assert a.run("evidence.py", "push", "--branch", "feature").returncode == 0
    b = machine_b(repo, outside, origin)
    proc = check(b, outside, "--head", new)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "stale: the record is of head" in proc.stdout


def test_a_note_whose_digest_differs_from_the_evidence_line_is_shown(repo, outside):
    """REQ-039: brief #1447 answers 3 and 7: an edited note prints its own digest, never the one
    of the `Evidence:` line, so the conductor's comparison catches it."""
    a, origin = machine_a(repo, outside)
    scan = scanner(outside / "bin", 0)
    made = record_and_push(a, outside, scan)
    head = a.git("rev-parse", "HEAD").strip()
    text = a.git("notes", "--ref", "agk-evidence", "show", head)
    edited = re.sub(r'"started": "[^"]*"', '"started": "2026-01-01T00:00:00Z"', text)
    assert edited != text
    a.git("notes", "--ref", "agk-evidence", "add", "-f", "-m", edited.rstrip("\n"), head)
    assert a.run("evidence.py", "push", "--branch", "feature").returncode == 0
    b = machine_b(repo, outside, origin)
    proc = check(b, outside, "--head", head, scan=scan)
    found = LINE.search(proc.stdout)
    assert found, proc.stdout + proc.stderr
    assert found.group(3) != EVIDENCE.search(made.stdout).group(3)


def test_a_dirty_tree_note_is_dirty(repo, outside):
    """REQ-039: brief #1447 answers 3 and 7 (a dirty-tree note)."""
    a, origin = machine_a(repo, outside)
    a.write("scratch.txt", "untracked\n")
    record_and_push(a, outside, scanner(outside / "bin", 0))
    b = machine_b(repo, outside, origin)
    proc = check(b, outside, "--head", a.git("rev-parse", "HEAD").strip())
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "dirty: the record's work tree was not clean (field: tree_clean)" in proc.stdout


def test_a_note_the_guard_refuses_is_not_written_and_names_the_path_class(repo, outside):
    """REQ-039: brief #1447 answers 4 and 7: a finding refuses the note, naming the path class,
    never the value."""
    a, _ = machine_a(repo, outside)
    head = a.git("rev-parse", "HEAD").strip()
    planted = "ghp_" + "a1B2c3D4e5" * 4
    line = prepush.write_note(a.root, head, ('{"argv": ["%s"]}\n' % planted).encode())
    assert line == prepush.NOTE_REFUSED
    assert planted not in line and REF in line
    assert notes(a) == ""


def test_a_refused_notes_push_leaves_the_branch_pushed_and_names_the_fallback(repo, outside):
    """REQ-039: brief #1447 answers 6 and 7 (a refused notes push)."""
    a, origin = machine_a(repo, outside)
    hook = origin / "hooks" / "update"
    hook.write_text('#!/bin/sh\ncase "$1" in refs/notes/*) exit 1;; esac\nexit 0\n')
    hook.chmod(0o755)
    made = a.run("prepush.py", "--record", PATH=path_with(scanner(outside / "bin", 0)))
    assert made.returncode == 0, made.stdout + made.stderr
    proc = a.run("evidence.py", "push", "--branch", "feature")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip().splitlines()[-1] == prepush.NOTE_NOT_PUSHED
    remote = a.git("ls-remote", str(origin), "refs/heads/feature").split()[0]
    assert remote == a.git("rev-parse", "HEAD").strip()
    assert a.git("ls-remote", str(origin), REF) == ""


@pytest.mark.parametrize(
    "settings,tables", [("", ""), ('execution = "hybrid"\n', ""), (LOCAL, PERSONAL)]
)
def test_hosted_hybrid_and_personal_mode_write_no_note(repo, outside, settings, tables):
    """REQ-039: brief #1447 answers 5 and 7 (hosted and personal mode write no note); the folder
    record is written as today."""
    a, _ = machine_a(repo, outside, settings, tables)
    made = a.run("prepush.py", "--record", PATH=path_with(scanner(outside / "bin", 0)))
    assert made.returncode == 0, made.stdout + made.stderr
    head = a.git("rev-parse", "HEAD").strip()
    assert (shared(a) / f"{head}.json").is_file()
    assert notes(a) == "" and "evidence.py push" not in made.stdout


def test_the_note_holds_the_record_bytes_and_the_folder_stays_first(repo, outside):
    """REQ-039: brief #1447 answers 1, 2 and 4: the note is the record file byte for byte, and a
    clone holding the folder record reads it without a fetch (no remote is needed)."""
    a, origin = machine_a(repo, outside)
    scan = scanner(outside / "bin", 0)
    made = a.run("prepush.py", "--record", PATH=path_with(scan))
    assert made.returncode == 0, made.stdout + made.stderr
    head = a.git("rev-parse", "HEAD").strip()
    blob = notes(a).split()[0]
    data = (shared(a) / f"{head}.json").read_bytes()
    note = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "cat-file", "blob", blob], cwd=a.root, capture_output=True, check=True
    ).stdout
    assert note == data
    a.git("remote", "remove", "origin")
    proc = check(a, outside, "--head", head, scan=scan)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"(ref: {REF})" not in proc.stdout
