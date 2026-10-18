"""Kit-only tests of scripts/agk/intake.py: ids, sentence, ADR stub (SPEC-0012 1, 2, 8, 16)."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import check_adrs  # noqa: E402

SCRIPT = KIT_ROOT / "scripts" / "agk" / "intake.py"
SENTENCE = "Let a visitor export their saved list as a file."
BASE_REQS = (
    "# Requirements\n\n### REQ-003 — Three\n\n- Acceptance: AC1 x\n- Status: done\n\n"
    "### REQ-001 — One\n\n- Acceptance: AC1 x\n- Status: planned\n"
)


@pytest.fixture
def repo(tmp_path):
    root = make_repo(tmp_path / "proj")
    for rel, text in (
        ("docs/requirements.md", BASE_REQS),
        ("docs/specs/0013-old.md", "# SPEC-0013: Old\n"),
        ("docs/specs/0002-older.md", "# SPEC-0002: Older\n"),
        ("docs/adr/0021-old.md", "# ADR-0021: Old\n"),
        ("docs/adr/0007-older.md", "# ADR-0007: Older\n"),
    ):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "switch", "-q", "-c", "intake/req-004-export")
    return root


def run(repo, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(repo), "--date", "2026-10-18"],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def write(repo, rel, text, mode="w"):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as fh:
        fh.write(text)


# --- ids and the sentence (rules 1, 2) ----------------------------------------------------------


def test_ac1_ids_are_the_next_free_numbers_of_the_base_not_the_work_tree(repo):
    """REQ-019 AC1: rule 2 (gaps; the highest is not the last; leading zeros; independent)."""
    write(repo, "docs/specs/0099-draft-only.md", "# SPEC-0099: x\n")
    proc = run(repo, "ids", "--sentence", SENTENCE, "--ref", "main")
    assert proc.returncode == 0, proc.stdout
    assert json.loads(proc.stdout) == {
        "req": "REQ-004",
        "spec": "0014",
        "adr": "0022",
        "slug": "let-a-visitor-export-their-saved-list-as-a-file",
    }
    assert git_status_unchanged(repo)


def git_status_unchanged(repo) -> bool:
    out = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
    ).stdout
    return out.strip() == "?? docs/specs/0099-draft-only.md"


def test_ac1_ids_on_an_empty_base_start_at_one(tmp_path):
    """REQ-019 AC1: rule 2 (an empty requirements file)."""
    root = make_repo(tmp_path / "e")
    write(root, "docs/requirements.md", "# Requirements\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "r")
    proc = run(root, "ids", "--sentence", SENTENCE, "--ref", "main")
    assert json.loads(proc.stdout)["req"] == "REQ-001"
    assert json.loads(proc.stdout)["spec"] == "0001" and json.loads(proc.stdout)["adr"] == "0001"


def test_ac1_ids_read_origin_of_the_default_branch_by_default(repo, tmp_path):
    """REQ-019 AC1: rule 2 (git fetch is the skill's step; the script reads `origin/<default>`)."""
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(repo), str(bare)], check=True)
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "fetch", "-q", "origin", "main")
    proc = run(repo, "ids", "--sentence", SENTENCE)
    assert proc.returncode == 0 and json.loads(proc.stdout)["req"] == "REQ-004"
    git(repo, "remote", "remove", "origin")
    proc = run(repo, "ids", "--sentence", SENTENCE)
    assert proc.returncode == 1  # no origin/main: nothing is guessed


@pytest.mark.parametrize(
    "sentence",
    ["", "   ", "x" * 301, "One thing. And another thing.", "Line\nbreak", "...", "!!!"],
)
def test_ac1_a_bad_sentence_is_refused_with_the_rule_and_nothing_is_written(repo, sentence):
    """REQ-019 AC1: rule 1 (empty; over 300 characters; more than one sentence)."""
    proc = run(repo, "ids", "--sentence", sentence, "--ref", "main")
    assert proc.returncode == 1 and proc.stdout.startswith("refused: rule 1")
    assert sentence.strip() not in proc.stdout or not sentence.strip()
    stub = run(
        repo, "stub", "--req", "REQ-004", "--title", "T", "--sentence", sentence, "--ref", "main"
    )
    assert stub.returncode == 1 and not list((repo / "docs" / "adr").glob("0022*"))


def test_ac1_a_sentence_of_exactly_300_characters_is_accepted(repo):
    """REQ-019 AC1: rule 1 (the limit)."""
    sentence = ("a" * 299) + "."
    assert run(repo, "ids", "--sentence", sentence, "--ref", "main").returncode == 0


def test_ac1_the_slug_is_at_most_60_characters(repo):
    """REQ-019 AC1: rule 2 (the rule of new_spec.py)."""
    out = json.loads(run(repo, "ids", "--sentence", "word " * 40 + "end.", "--ref", "main").stdout)
    assert len(out["slug"]) <= 60 and not out["slug"].endswith("-")


# --- the ADR stub (rule 8) ----------------------------------------------------------------------


def test_ac1_the_stub_passes_check_adrs_names_the_class_and_uses_the_given_date(repo):
    """REQ-019 AC1: rule 8."""
    proc = run(
        repo,
        "stub",
        "--req",
        "REQ-004",
        "--title",
        "Export",
        "--sentence",
        SENTENCE,
        "--ref",
        "main",
    )
    assert proc.returncode == 0, proc.stdout
    name = "0022-add-req-004-let-a-visitor-export-their-saved-list-as-a-file.md"
    assert proc.stdout == f"created docs/adr/{name}\n"
    text = (repo / "docs" / "adr" / name).read_text(encoding="utf-8")
    assert check_adrs.validate(name, text, {"0021", "0007"}) == []
    assert "- Status: Proposed" in text and "- Date: 2026-10-18" in text
    assert "- Requirements: REQ-004" in text
    assert "Protected classes: `docs/requirements.md`" in text
    assert f"> {SENTENCE}" in text and "SPEC-0014" in text
    assert (
        run(
            repo,
            "stub",
            "--req",
            "REQ-004",
            "--title",
            "Export",
            "--sentence",
            SENTENCE,
            "--ref",
            "main",
        ).returncode
        == 1
    )


def test_ac1_the_stub_refuses_a_requirement_that_is_not_the_next_free_one(repo):
    """REQ-019 AC1: rules 2 and 8 (ids are read, never guessed)."""
    proc = run(
        repo,
        "stub",
        "--req",
        "REQ-009",
        "--title",
        "Export",
        "--sentence",
        SENTENCE,
        "--ref",
        "main",
    )
    assert proc.returncode == 1 and "REQ-009" not in proc.stdout.replace("--req", "")
    assert not list((repo / "docs" / "adr").glob("0022*"))


def test_ac1_the_stub_refuses_a_title_over_80_characters_or_with_a_semicolon(repo):
    """REQ-019 AC1: rule 5 (the title)."""
    for title in ("x" * 81, "a; b", ""):
        proc = run(
            repo,
            "stub",
            "--req",
            "REQ-004",
            "--title",
            title,
            "--sentence",
            SENTENCE,
            "--ref",
            "main",
        )
        assert proc.returncode == 1, title
