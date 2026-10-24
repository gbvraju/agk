"""Kit-only tests of `intake.py renumber` (SPEC-0025 rule 2; REQ-032 AC2).

A pull request that took numbers which a merge on the default branch also took moves its own
requirement, spec and ADR to the next free numbers: files renamed, ids rewritten in its own files
and in the lines it added, nothing on the default branch touched, a second run a no-op. No
network, no model.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo, without_version_line

SCRIPT = KIT_ROOT / "scripts" / "agk" / "intake.py"
LOG = (
    "# Log\n\n| Date | Row |\n| --- | --- |\n"
    "| 2026-10-01 | an old row about ADR-0021 and SPEC-0013 |\n"
)
BASE = {
    "docs/requirements.md": "# R\n\n### REQ-003 — Three\n\n- Status: done\n",
    "docs/specs/0013-old.md": "# SPEC-0013: Old\n",
    "docs/adr/0021-old.md": "# ADR-0021: Old\n",
    "docs/runs/decisions-log.md": LOG,
}
SPEC = (
    "# SPEC-0014: Mine\n\n- Requirements: REQ-004\n\n"
    "See ADR-0022 and docs/adr/0022-add-req-004-mine.md. Q-S0014-1.\n"
)
ADR = (
    "# ADR-0022: Mine\n\n- Requirements: REQ-004\n\n"
    "My spec is SPEC-0014 (docs/specs/0014-mine.md).\n"
)
OWN = {
    "docs/requirements.md": BASE["docs/requirements.md"]
    + "\n### REQ-004 — Mine\n\n- Status: planned\n",
    "docs/specs/0014-mine.md": SPEC,
    "docs/adr/0022-add-req-004-mine.md": ADR,
    "docs/runs/decisions-log.md": LOG + "| 2026-10-02 | my row about ADR-0022 and REQ-004 |\n",
}
THEIRS = {
    "docs/requirements.md": BASE["docs/requirements.md"]
    + "\n### REQ-004 — Theirs\n\n- Status: planned\n",
    "docs/specs/0014-theirs.md": "# SPEC-0014: Theirs\n",
    "docs/adr/0022-add-req-004-theirs.md": "# ADR-0022: Theirs\n",
}


def put(root, files):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change")


@pytest.fixture
def repo(tmp_path):
    root = make_repo(tmp_path / "proj")
    put(root, BASE)
    git(root, "switch", "-q", "-c", "feature")
    put(root, OWN)
    git(root, "switch", "-q", "main")
    put(root, THEIRS)
    git(root, "switch", "-q", "feature")
    return root


def renumber(root, ident, *extra):
    return without_version_line(
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "renumber",
                ident,
                "--ref",
                "main",
                "--root",
                str(root),
                *extra,
            ],
            capture_output=True,
            text=True,
            env=clean_env(),
        )
    )


def out(root, *args):
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return proc.stdout


def read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


def test_ac2_it_moves_the_requirement_spec_and_adr_to_the_next_free_numbers(repo):
    """REQ-032 AC2: rule 2 (files renamed, ids rewritten, the log row it added follows)."""
    proc = renumber(repo, "REQ-004")
    assert proc.returncode == 0, proc.stdout
    for moved in ("REQ-004 -> REQ-005", "SPEC-0014 -> SPEC-0015", "ADR-0022 -> ADR-0023"):
        assert moved in proc.stdout
    assert not (repo / "docs/specs/0014-mine.md").exists()
    spec = read(repo, "docs/specs/0015-mine.md")
    assert spec.startswith("# SPEC-0015: Mine") and "REQ-005" in spec and "Q-S0015-1" in spec
    assert "docs/adr/0023-add-req-005-mine.md" in spec and "ADR-0023" in spec
    adr = read(repo, "docs/adr/0023-add-req-005-mine.md")
    assert adr.startswith("# ADR-0023: Mine") and "SPEC-0015 (docs/specs/0015-mine.md)" in adr
    assert "### REQ-005 — Mine" in read(repo, "docs/requirements.md")
    assert "my row about ADR-0023 and REQ-005" in read(repo, "docs/runs/decisions-log.md")


def merged_repo(repo):
    """The feature branch after `git merge main`, the conflict resolved keeping both sections."""
    merge = subprocess.run(["git", "merge", "main"], cwd=repo, capture_output=True, text=True)
    assert merge.returncode == 1 and "CONFLICT" in merge.stdout  # both appended to the last line
    both = (
        THEIRS["docs/requirements.md"]
        + OWN["docs/requirements.md"][len(BASE["docs/requirements.md"]) :]
    )
    (repo / "docs/requirements.md").write_text(both, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "merge main")
    return repo


def test_ac2_after_the_default_branch_is_merged_in_the_own_requirement_still_moves(repo):
    """REQ-032 AC2: rule 2 (found by position: its heading is a line the pull request added)."""
    merged_repo(repo)
    text = read(repo, "docs/requirements.md")
    assert text.count("### REQ-004") == 2
    proc = renumber(repo, "REQ-004")
    assert proc.returncode == 0, proc.stdout
    for moved in ("REQ-004 -> REQ-005", "SPEC-0014 -> SPEC-0015", "ADR-0022 -> ADR-0023"):
        assert moved in proc.stdout
    text = read(repo, "docs/requirements.md")
    assert "### REQ-004 — Theirs" in text and "### REQ-005 — Mine" in text
    assert "### REQ-004 — Mine" not in text and "### REQ-005 — Theirs" not in text
    assert (repo / "docs/specs/0015-mine.md").is_file() and (
        repo / "docs/specs/0014-theirs.md"
    ).is_file()
    assert "REQ-005" in read(repo, "docs/adr/0023-add-req-005-mine.md")
    assert "REQ-004" not in read(repo, "docs/adr/0022-add-req-004-theirs.md").replace(
        "# ADR-0022: Theirs", ""
    )


def test_ac2_after_the_merge_a_second_run_changes_nothing(repo):
    """REQ-032 AC2: rule 2 (idempotent also on a merged branch)."""
    merged_repo(repo)
    renumber(repo, "REQ-004")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "renumbered")
    proc = renumber(repo, "REQ-005")
    assert proc.returncode == 0 and "nothing to move" in proc.stdout
    assert out(repo, "status", "--porcelain") == ""


def test_ac2_nothing_that_is_on_the_default_branch_is_changed(repo):
    """REQ-032 AC2: rule 2 (only the lines the pull request added are rewritten)."""
    renumber(repo, "SPEC-0014")
    assert "an old row about ADR-0021 and SPEC-0013" in read(repo, "docs/runs/decisions-log.md")
    assert read(repo, "docs/specs/0013-old.md") == "# SPEC-0013: Old\n"
    assert "### REQ-003 — Three" in read(repo, "docs/requirements.md")
    removed = out(repo, "diff", "--name-status", "main...HEAD")
    assert "theirs" not in removed


def test_ac2_a_second_run_changes_nothing(repo):
    """REQ-032 AC2: rule 2 (idempotent)."""
    renumber(repo, "ADR-0022")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "renumbered")
    before = out(repo, "rev-parse", "HEAD")
    proc = renumber(repo, "REQ-005")
    assert proc.returncode == 0 and "nothing to move" in proc.stdout
    assert out(repo, "status", "--porcelain") == "" and out(repo, "rev-parse", "HEAD") == before


def test_ac2_two_own_requirements_move_without_colliding_with_each_other(repo):
    """REQ-032 AC2: rule 2 (a single pass: 004 -> 005 and 005 -> 006)."""
    text = read(repo, "docs/requirements.md") + "\n### REQ-005 — Mine too\n\n- Status: planned\n"
    put(repo, {"docs/requirements.md": text})
    proc = renumber(repo, "REQ-004")
    assert proc.returncode == 0, proc.stdout
    out = read(repo, "docs/requirements.md")
    assert "### REQ-005 — Mine\n" in out and "### REQ-006 — Mine too" in out


def test_ac2_it_refuses_a_dirty_work_tree_and_an_id_that_is_not_the_pull_requests_own(repo):
    """REQ-032 AC2: rule 2 (refusals name the rule, change nothing)."""
    (repo / "scratch.txt").write_text("x\n", encoding="utf-8")
    proc = renumber(repo, "REQ-004")
    assert (
        proc.returncode == 1
        and proc.stdout.startswith("refused: rule 2")
        and "clean" in proc.stdout
    )
    (repo / "scratch.txt").unlink()
    for ident in ("REQ-003", "SPEC-0013", "ADR-0021", "REQ-999"):
        proc = renumber(repo, ident)
        assert proc.returncode == 1 and "not one of the pull request's own" in proc.stdout, ident
    assert (repo / "docs/specs/0014-mine.md").exists() and out(repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("ident", ["", "REQ", "req-004", "ADR-22", "SPEC-0014x"])
def test_ac2_a_bad_id_is_refused(repo, ident):
    """REQ-032 AC2: rule 2 (the id is REQ-nnn, SPEC-nnnn or ADR-nnnn)."""
    proc = renumber(repo, ident)
    assert proc.returncode == 1 and proc.stdout.startswith("refused:")
