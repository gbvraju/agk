"""SPEC-0041 build (m): export to team mode, renumbered and lossless, never pushed (brief #1508).

Advances REQ-048 (AC7).

Rule 24: `personal.py export --target CLONE` is a dry run; `--write` writes, on a new branch of the
target and never on its default branch, the adopt plan when AGK is not installed there, the records
renumbered against the target with statuses reset and the confirmation line, printed (never run)
`gh issue create` commands for open briefs, a second branch of test markers and `export-map.json`;
nothing is pushed. Rule 25: `export --check` fails unless every record is mapped or withheld, and
private field notes are withheld by default. Invented repositories and sidecars only; no network.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import personal  # noqa: E402
import personal_state as ps  # noqa: E402

PERSON = "member-example-1"
SHA = "a" * 40
AT = "2026-11-18T04:00:00Z"
IDENTITY = {
    "GIT_AUTHOR_NAME": "member-example-1",
    "GIT_AUTHOR_EMAIL": "member-example-1@example.com",
    "GIT_COMMITTER_NAME": "member-example-1",
    "GIT_COMMITTER_EMAIL": "member-example-1@example.com",
}
REQ_101 = """
### REQ-101 — A customer can empty the cart

- Acceptance: AC1 the cart empties
- Status: done
"""
SPEC = """# SPEC-0001: A customer can empty the cart

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-101

Observed in code. See ADR-0001.
"""
ADR = """# ADR-0001: The cart empties in one step

- Status: Accepted
- Date: 2026-11-18
- Deciders: maintainers
- Related: SPEC-0001
- Requirements: REQ-101

## Decision

Invented.
"""
BRIEF = "# Brief: Empty the cart faster\n\nAdvances REQ-101 under SPEC-0001.\n"
CLOSED_BRIEF = "# Brief: An old item\n\n- Status: closed\n"
LOG_ROW = (
    "| 2026-11-18 | The cart empties at once (SPEC-0001) | invented | ADR-0001 "
    "| member-example-1 |\n"
)
NOTE = "The checkout code is slow on Mondays (invented).\n"
TEST_FILE = "def test_empty():\n    assert True\n"


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def commit(root: Path, subject: str) -> str:
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
        "commit", "-q", "--no-verify", "-m", subject)  # fmt: skip
    return git(root, "rev-parse", "HEAD")


def confirmation(rid: str, word: str) -> dict:
    body = "\n".join(
        [f"Confirmed: {SHA}", f"Verdict: cleared {SHA}", f"Record: {rid}", f"{word}: {rid}",
         "Shown:", "a", "b", "c", f"confirmed by {PERSON} at a terminal at {AT}"]
    )  # fmt: skip
    return {"id": 1, "body": body, "user": {"login": PERSON}, "created_at": AT,
            "performed_via_github_app": None}  # fmt: skip


def sidecar(path: Path, note: str = NOTE) -> Path:
    """A sidecar holding one of each record kind, the spec and the ADR confirmed at a terminal."""
    ps.make_sidecar(path, PERSON)
    req = path / "docs" / "requirements.md"
    req.write_text(req.read_text(encoding="utf-8") + REQ_101, encoding="utf-8")
    (path / "docs/specs/0001-empty-cart.md").write_text(SPEC, encoding="utf-8")
    (path / "docs/adr/0001-empty-cart.md").write_text(ADR, encoding="utf-8")
    (path / "docs/briefs/empty-cart.md").write_text(BRIEF, encoding="utf-8")
    (path / "docs/briefs/old-item.md").write_text(CLOSED_BRIEF, encoding="utf-8")
    log = path / "docs/runs/decisions-log.md"
    log.write_text(log.read_text(encoding="utf-8") + LOG_ROW, encoding="utf-8")
    (path / "records/notes").mkdir(parents=True, exist_ok=True)
    (path / "records/notes/monday.md").write_text(note, encoding="utf-8")
    (path / "test-map.toml").write_text(
        '"REQ-101 AC1" = ["tests/test_cart.py::test_empty", "tests/test_gone.py::test_x"]\n',
        encoding="utf-8",
    )
    comments = [confirmation("SPEC-0001", "Approve"), confirmation("ADR-0001", "Accept")]
    (path / "forge/comments-1.json").write_text(json.dumps(comments), encoding="utf-8")
    commit(path, "records")
    return path


def product(path: Path, installed: bool) -> Path:
    """An invented product clone on `main`; with AGK installed it already holds REQ-101, SPEC-0001
    and ADR-0001, so every exported id collides."""
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    (path / "tests").mkdir()
    (path / "tests/test_cart.py").write_text(TEST_FILE, encoding="utf-8")
    if installed:
        (path / "agk.toml").write_text(
            'version = "0.1.0"\nmode = "adopt"\ndefault_branch = "main"\n', encoding="utf-8"
        )
        (path / "docs/specs").mkdir(parents=True)
        (path / "docs/adr").mkdir(parents=True)
        (path / "docs/runs").mkdir(parents=True)
        (path / "docs/requirements.md").write_text(
            "# Requirements\n\n### REQ-101 — Team's own\n\n- Status: planned\n", encoding="utf-8"
        )
        (path / "docs/specs/0001-team.md").write_text("# SPEC-0001: Team\n\n- Status: Draft\n")
        (path / "docs/adr/0001-team.md").write_text("# ADR-0001: Team\n\n- Status: Proposed\n")
        (path / "docs/runs/decisions-log.md").write_text(
            "# Decisions log\n\n| Date | Decision | Reason | Recorded in | By |\n"
            "| ---- | -------- | ------ | ----------- | -- |\n",
            encoding="utf-8",
        )
    else:
        (path / "README.md").write_text("An invented product.\n", encoding="utf-8")
    commit(path, "product")
    return path


def export(side: Path, target: Path, *flags: str, monkeypatch=None) -> tuple[int, str]:
    if monkeypatch is not None:
        for key, value in IDENTITY.items():
            monkeypatch.setenv(key, value)
    code, lines = personal.export(
        side,
        target,
        write="--write" in flags,
        branch=_branch(flags),
        with_notes="--with-notes" in flags,
    )
    return code, "\n".join(lines)


def _branch(flags: tuple[str, ...]) -> str | None:
    return flags[flags.index("--branch") + 1] if "--branch" in flags else None


def at(target: Path, ref: str, rel: str) -> str:
    return git(target, "show", f"{ref}:{rel}")


# --- rule 24: the dry run writes nothing ---------------------------------------------------------


def test_req_048_ac7_export_without_write_writes_nothing(tmp_path):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=True)
    before = (git(target, "for-each-ref"), git(target, "status", "--porcelain"))
    side_head = git(side, "rev-parse", "HEAD")
    code, out = export(side, target)
    assert code == 0, out
    assert "dry run" in out
    assert "SPEC-0001 -> SPEC-0002" in out and "ADR-0001 -> ADR-0002" in out
    assert (git(target, "for-each-ref"), git(target, "status", "--porcelain")) == before
    assert git(side, "rev-parse", "HEAD") == side_head
    assert not (side / personal.EXPORT_MAP).exists()


# --- rule 24: a target with AGK installed: renumbered, statuses reset, confirmation line ---------


def test_req_048_ac7_export_renumbers_colliding_ids_and_resets_statuses(tmp_path, monkeypatch):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=True)
    code, out = export(side, target, "--write", monkeypatch=monkeypatch)
    assert code == 0, out
    branch = personal.EXPORT_BRANCH
    assert git(target, "symbolic-ref", "--short", "HEAD") == "main"  # the checkout is restored
    names = git(target, "ls-tree", "-r", "--name-only", branch).splitlines()
    assert "docs/adr/0001-adopt-agk.md" not in names  # AGK is installed: no install files
    spec = at(target, branch, "docs/specs/0002-empty-cart.md")
    assert spec.startswith("# SPEC-0002:") and "- Status: Draft" in spec
    assert "- Requirements: REQ-102" in spec and "See ADR-0002." in spec  # references rewritten
    assert f"confirmed by {PERSON} in personal mode on 2026-11-18" in spec
    adr = at(target, branch, "docs/adr/0002-empty-cart.md")
    assert "- Status: Proposed" in adr and "- Related: SPEC-0002" in adr
    reqs = at(target, branch, "docs/requirements.md")
    assert "### REQ-101 — Team's own" in reqs and "### REQ-102 — A customer can empty" in reqs
    section = reqs.split("### REQ-102")[1]
    assert "- Status: planned" in section and "- Status: done" not in section
    assert "drafted in personal mode, not confirmed" in section  # no terminal confirmation
    log = at(target, branch, "docs/runs/decisions-log.md")
    assert "The cart empties at once (SPEC-0002)" in log and "| ADR-0002 |" in log
    assert at(target, "main", "docs/specs/0001-team.md").startswith("# SPEC-0001: Team")


def test_req_048_ac7_export_prints_issue_commands_for_open_briefs_and_runs_none(
    tmp_path, monkeypatch
):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=True)
    fake = tmp_path / "bin"
    fake.mkdir()
    ran = tmp_path / "gh-ran"
    (fake / "gh").write_text(f"#!/bin/sh\ntouch {ran}\n", encoding="utf-8")
    (fake / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake}{os.pathsep}{os.environ.get('PATH', '')}")
    code, out = export(side, target, "--write", monkeypatch=monkeypatch)
    assert code == 0, out
    assert not ran.exists()  # printed, never run
    commands = [x for x in out.splitlines() if "gh issue create" in x]
    assert len(commands) == 1  # the closed brief has none
    assert "Empty the cart faster" in commands[0] and "docs/briefs/empty-cart.md" in commands[0]
    body = at(target, personal.EXPORT_BRANCH, "docs/briefs/empty-cart.md")
    assert "REQ-102" in body and "SPEC-0002" in body


def test_req_048_ac7_export_proposes_test_markers_on_a_second_branch(tmp_path, monkeypatch):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=True)
    code, out = export(side, target, "--write", monkeypatch=monkeypatch)
    assert code == 0, out
    tests = at(target, personal.EXPORT_BRANCH + "-tests", "tests/test_cart.py")
    assert tests.splitlines()[0] == "# REQ-102 AC1"
    assert tests.splitlines()[1] == "def test_empty():"
    assert at(target, "main", "tests/test_cart.py") == TEST_FILE.rstrip("\n")
    mapping = json.loads(at(target, personal.EXPORT_BRANCH, "docs/runs/export-map.json"))
    gone = [r for r in mapping["records"] if r["id"].endswith("tests/test_gone.py::test_x")]
    assert gone and gone[0]["status"] == "withheld" and gone[0]["reason"]


def test_req_048_ac7_export_never_pushes(tmp_path, monkeypatch):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=True)
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(target, "remote", "add", "origin", str(remote))
    git(target, "push", "-q", "origin", "main")
    git(target, "remote", "set-head", "origin", "main")
    code, out = export(side, target, "--write", monkeypatch=monkeypatch)
    assert code == 0, out
    assert git(remote, "for-each-ref", "--format=%(refname)").splitlines() == ["refs/heads/main"]
    assert "nothing pushed" in out


# --- rule 24: a target without AGK: the adopt plan -----------------------------------------------


def test_req_048_ac7_export_to_a_target_without_agk_writes_the_adopt_plan(tmp_path, monkeypatch):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=False)
    code, out = export(side, target, "--write", monkeypatch=monkeypatch)
    assert code == 0, out
    names = git(target, "ls-tree", "-r", "--name-only", personal.EXPORT_BRANCH).splitlines()
    assert "agk.toml" in names and "docs/adr/0001-adopt-agk.md" in names
    assert "docs/adr/0002-empty-cart.md" in names  # numbered past the plan's ADR-0001
    assert "docs/specs/0001-empty-cart.md" in names
    assert "### REQ-101 — A customer" in at(target, personal.EXPORT_BRANCH, "docs/requirements.md")
    assert not (target / "agk.toml").exists()  # the default branch's checkout is untouched


# --- rule 24: refusals ---------------------------------------------------------------------------


def test_req_048_ac7_export_on_the_default_branch_is_refused(tmp_path, monkeypatch):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=True)
    code, out = export(side, target, "--write", "--branch", "main", monkeypatch=monkeypatch)
    assert code == 1
    assert "default branch" in out and "option: --branch" in out
    assert git(target, "rev-list", "--count", "main") == "1"


def test_req_048_ac7_a_secret_in_a_field_note_is_refused_naming_the_path_class(
    tmp_path, monkeypatch
):
    secret = "aws_secret_access_key = " + "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" + "\n"
    side = sidecar(tmp_path / "side", note=secret)
    target = product(tmp_path / "product", installed=True)
    refs = git(target, "for-each-ref")
    code, out = export(side, target, "--write", "--with-notes", monkeypatch=monkeypatch)
    assert code == 1
    assert "path class: records/notes" in out
    assert "wJalr" not in out and "monday" not in out
    assert git(target, "for-each-ref") == refs


# --- rule 25: export --check ---------------------------------------------------------------------


def test_req_048_ac7_check_passes_when_every_record_is_mapped_or_withheld(tmp_path, monkeypatch):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=True)
    assert export(side, target, "--write", monkeypatch=monkeypatch)[0] == 0
    code, lines = personal.export_check(side)
    assert code == 0, lines
    mapping = json.loads((side / personal.EXPORT_MAP).read_text(encoding="utf-8"))
    note = [r for r in mapping["records"] if r["kind"] == "field-note"]
    assert note and note[0]["status"] == "withheld" and "Q-S0041-11" in note[0]["reason"]
    kinds = {r["kind"] for r in mapping["records"]}
    assert kinds >= {"requirement", "spec", "adr", "brief", "decisions-log", "test-map"}


def test_req_048_ac7_check_fails_naming_the_count_and_the_first_unmapped_id(tmp_path, monkeypatch):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=True)
    assert export(side, target, "--write", monkeypatch=monkeypatch)[0] == 0
    (side / "docs/adr/0002-later.md").write_text("# ADR-0002: Later\n\n- Status: Proposed\n")
    code, lines = personal.export_check(side)
    assert code == 1
    assert lines[-1] == (
        "export --check: failed: 1 record not in export-map.json, first ADR-0002 "
        "(SPEC-0041 rule 25)"
    )


def test_req_048_ac7_check_without_a_map_fails(tmp_path):
    side = sidecar(tmp_path / "side")
    code, lines = personal.export_check(side)
    assert code == 1 and "export-map.json" in lines[-1]


def test_req_048_ac7_the_command_line_runs_check_and_writes_nothing_in_the_clone(tmp_path):
    side, target = sidecar(tmp_path / "side"), product(tmp_path / "product", installed=True)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "personal.py"), "export", "--check", "--sidecar", str(side),
         "--clone", str(target)],
        capture_output=True, text=True, env=env, check=False,
    )  # fmt: skip
    assert done.returncode == 1 and "export-map.json" in done.stdout
    assert git(target, "status", "--porcelain") == ""
