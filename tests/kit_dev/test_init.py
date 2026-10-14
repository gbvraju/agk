"""Tests of scripts/agk/init.py (SPEC-0001)."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from conftest import INIT, KIT_ROOT, clean_env, expected_files, manifest, run_init, snapshot

INSTALLED_PROTECTED = [
    "constitution/",
    "config/",
    ".claude/",
    ".github/",
    "docs/requirements.md",
    "CLAUDE.md",
    "scripts/agk/",
    "tests/kit/",
    "Makefile",
    "pyproject.toml",
]


def make(target: Path, *args: str, **env: str):
    full = {**clean_env(), **env}
    return subprocess.run(["make", *args], cwd=target, capture_output=True, text=True, env=full)


# --- Interface and effects ------------------------------------------------------------------


def test_ac1_usage_errors_exit_2(tmp_path):
    """REQ-009 AC1: rules 1-2."""
    for args in ([], ["--bogus"], [str(tmp_path), "extra"], [str(tmp_path), "--dry-run", "--x"]):
        proc = subprocess.run(
            [sys.executable, str(INIT), *args], capture_output=True, text=True, env=clean_env()
        )
        assert proc.returncode == 2, args


def test_ac1_unusable_target_exits_1(tmp_path):
    """REQ-009 AC1: rule 2."""
    assert run_init(tmp_path / "missing").returncode == 1
    afile = tmp_path / "f"
    afile.write_text("x")
    assert run_init(afile).returncode == 1


def test_ac1_self_target_refused(tmp_path):
    """REQ-009 AC1: rule 5."""
    before = snapshot(KIT_ROOT / "docs")
    for tgt in (KIT_ROOT, KIT_ROOT / "docs"):
        proc = run_init(tgt)
        assert proc.returncode == 1
        assert "kit/" in proc.stdout + proc.stderr
    assert snapshot(KIT_ROOT / "docs") == before


def test_ac1_interpreter_refusal_below_3_11():
    """REQ-009 AC1: rule 4."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import init

    assert init.check_interpreter((3, 10, 9)) is not None
    assert init.check_interpreter((3, 11, 0)) is None
    assert init.check_interpreter((3, 13, 1)) is None


def test_ac1_init_has_no_network_or_process_imports():
    """REQ-009 AC1: rule 3 (no network, git, gh); rule 1 (standard library only)."""
    tree = ast.parse(INIT.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    forbidden = {"subprocess", "socket", "urllib", "http", "ftplib", "smtplib", "requests", "ssl"}
    assert not names & forbidden
    local = {"common", "reviewers"}
    assert names <= set(sys.stdlib_module_names) | local


def test_ac1_symlinked_path_is_refused_and_nothing_written(target, tmp_path):
    """REQ-009 AC1: rule 3."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    os.symlink(elsewhere, target / ".claude")
    before = snapshot(target)
    proc = run_init(target)
    assert proc.returncode == 1
    assert ".claude/" in proc.stdout + proc.stderr
    assert snapshot(target) == before
    assert not any(elsewhere.rglob("*"))


def test_ac1_target_without_git_gets_a_notice_and_succeeds(tmp_path):
    """REQ-009 AC1: rule 3."""
    plain = tmp_path / "plain"
    plain.mkdir()
    proc = run_init(plain)
    assert proc.returncode == 0
    assert "not a git" in proc.stdout.lower()
    assert (plain / "Makefile").is_file()


# --- Target result ----------------------------------------------------------------------------


def test_ac2_creates_exactly_the_planned_file_list(target):
    """REQ-009 AC2: rule 10."""
    readme = (target / "README.md").read_bytes()
    before = set(snapshot(target))
    proc = run_init(target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    created = set(snapshot(target)) - before
    assert created == expected_files()
    assert (target / "README.md").read_bytes() == readme
    for rel in manifest()["verbatim"]:
        assert (target / rel).read_bytes() == (KIT_ROOT / rel).read_bytes(), rel


def test_ac2_kit_only_files_are_not_installed(installed):
    """REQ-009 AC2: rules 6-7, 18."""
    for rel in ("scripts/agk/init.py", "kit", "tests/kit_dev"):
        assert not (installed / rel).exists(), rel


def test_ac2_governance_and_tests_green_in_target(installed):
    """REQ-009 AC2: rule 23 (governance green after init)."""
    gov = make(installed, "governance")
    assert gov.returncode == 0, gov.stdout + gov.stderr
    test = make(installed, "test")
    assert test.returncode == 0, test.stdout[-2000:] + test.stderr[-2000:]


def test_ac2_seeded_requirements(installed):
    """REQ-009 AC2: rule 11."""
    text = (installed / "docs" / "requirements.md").read_text(encoding="utf-8")
    ids = re.findall(r"^### (REQ-\d{3})", text, flags=re.M)
    assert ids == ["REQ-001", "REQ-002", "REQ-003"]
    assert re.findall(r"^- Status: (.*)$", text, flags=re.M) == ["planned"] * 3
    assert "agk doctor" not in text


def test_ac2_installed_protected_list_and_reviewers_equal(installed):
    """REQ-009 AC2: rule 21."""
    listed = [
        ln.strip()
        for ln in (installed / "config" / "protected-paths.txt").read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    assert listed == INSTALLED_PROTECTED
    assert make(installed, "governance").returncode == 0


def test_ac2_reviewers_placeholder_codeowners_and_notice(target):
    """REQ-009 AC2: rule 12 (warn only)."""
    proc = run_init(target)
    assert "@REPLACE-ME" in (target / "config" / "reviewers.yaml").read_text()
    assert "@REPLACE-ME" in (target / ".github" / "CODEOWNERS").read_text()
    assert "config/reviewers.yaml" in proc.stdout and "@REPLACE-ME" in proc.stdout
    check = subprocess.run(
        [sys.executable, "scripts/agk/reviewers.py", "--check-codeowners"],
        cwd=target,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0


def test_ac2_adr_names_every_protected_entry_and_is_proposed(installed):
    """REQ-009 AC2: rule 13."""
    text = (installed / "docs" / "adr" / "0001-adopt-agk.md").read_text(encoding="utf-8")
    assert "- Status: Proposed" in text
    for entry in INSTALLED_PROTECTED:
        assert entry in text, entry
    assert not re.findall(r"ADR-(?!0001)\d{4}", text)


def test_ac2_version_stamp_and_date(installed):
    """REQ-009 AC2: rule 14."""
    import tomllib

    data = tomllib.loads((installed / "pyproject.toml").read_text(encoding="utf-8"))
    agk = data["tool"]["agk"]
    assert agk["version"] == manifest()["kit_version"]
    assert agk["test_dirs"] == ["tests"]
    today = datetime.now(UTC).date().isoformat()
    assert agk["installed"] == today
    assert data["project"]["name"] == "my-project"


def test_ac2_branch_rules_are_printed_not_applied(target):
    """REQ-009 AC2: rule 19."""
    proc = run_init(target)
    out = " ".join(proc.stdout.split())
    for phrase in (
        "ruleset `main` is exactly",
        "required status check `governance`",
        "allow auto-merge; auto-delete head branches",
    ):
        assert phrase in out, phrase
    dry = run_init(target, "--dry-run")
    assert "required status check `governance`" in " ".join(dry.stdout.split())


# --- Idempotence, refusal, dry run --------------------------------------------------------------


def test_ac1_second_run_changes_nothing(installed):
    """REQ-009 AC1: rule 15 (hashes and mtimes equal)."""
    before = snapshot(installed)
    proc = run_init(installed)
    assert proc.returncode == 0
    assert "nothing to do" in proc.stdout
    assert snapshot(installed) == before


def test_ac1_second_run_reads_the_stamped_date(installed):
    """REQ-009 AC1: rule 14. An install made on another date is still unchanged."""
    old = "2020-01-02"
    today = datetime.now(UTC).date().isoformat()
    for path in installed.rglob("*"):
        if path.is_file() and ".git" not in path.relative_to(installed).parts:
            data = path.read_bytes()
            if today.encode() in data and path.suffix in {".md", ".toml"}:
                path.write_bytes(data.replace(today.encode(), old.encode()))
    proc = run_init(installed)
    assert proc.returncode == 0, proc.stdout
    assert "nothing to do" in proc.stdout


def test_ac1_conflict_refuses_lists_files_and_writes_nothing(target):
    """REQ-009 AC1: rule 16."""
    (target / "Makefile").write_text("all:\n\ttrue\n")
    (target / "pyproject.toml").write_text("[project]\nname='x'\n")
    before = snapshot(target)
    proc = run_init(target)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1
    assert "Makefile" in out and "pyproject.toml" in out
    assert snapshot(target) == before
    assert (target / "Makefile").read_text() == "all:\n\ttrue\n"


def test_ac1_conflict_message_never_prints_content(target):
    """REQ-009 AC1: rule 2 (principle 8)."""
    (target / "Makefile").write_text("SECRET_MARKER_12345 := 1\n")
    proc = run_init(target)
    assert "SECRET_MARKER_12345" not in proc.stdout + proc.stderr


def test_ac1_partial_install_completes(installed):
    """REQ-009 AC1: rule 16."""
    (installed / "docs" / "build-state.md").unlink()
    before = snapshot(installed)
    proc = run_init(installed)
    assert proc.returncode == 0
    after = snapshot(installed)
    assert "docs/build-state.md" in after
    for rel, value in before.items():
        assert after[rel] == value, rel


def test_ac1_dry_run_writes_nothing_and_exit_code_matches(target):
    """REQ-009 AC1: rule 17."""
    before = snapshot(target)
    proc = run_init(target, "--dry-run")
    assert proc.returncode == 0
    assert snapshot(target) == before
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("create ")]
    assert {ln.split(" ", 1)[1] for ln in lines} == expected_files()
    (target / "Makefile").write_text("x:\n")
    dry = run_init(target, "--dry-run")
    assert dry.returncode == 1
    assert any(ln.startswith("conflict Makefile") for ln in dry.stdout.splitlines())


def test_ac1_dry_run_on_installed_target_says_unchanged(installed):
    """REQ-009 AC1: rule 17."""
    proc = run_init(installed, "--dry-run")
    assert proc.returncode == 0
    assert "create " not in proc.stdout and "unchanged " in proc.stdout


# --- Neutrality ----------------------------------------------------------------------------------

FORBIDDEN = [r"gbvraju", r"day-\d", r"\bK[0-4]\b", r"PR #\d+", r"Q-K\d"]


def test_ac2_rendered_output_is_neutral(installed):
    """REQ-009 AC2: rule 20."""
    for rel in expected_files():
        text = (installed / rel).read_text(encoding="utf-8")
        for pat in FORBIDDEN:
            assert not re.search(pat, text), (rel, pat)
    for rel in manifest()["templates"]:
        text = (installed / rel).read_text(encoding="utf-8")
        assert not re.findall(r"ADR-(?!0001)\d{4}", text), rel
        assert "{{" not in text, rel
