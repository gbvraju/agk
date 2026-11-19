"""`/agk:uninstall` in a clean project (brief #1457, SPEC-0071 rule 9, build (e), ADR-0615;
REQ-078 AC4).

The uninstall of a clean sample removes the agreed records and `LICENSE-AGK`, keeps the specs and
decisions by default, prints a clean-up whose path list equals every kit path that the sample's
history holds, with its checklist, and runs no `git filter-repo`, no `git push --force` and no
GitHub write. An installed project is read as before. A stub plugin root with its own
`.claude-plugin/plugin.json`, saved git trees in temporary folders, a `gh` stub that records any
call and no network; invented data only (example.com, logins such as `member-example-1`)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import pytest
import uninstall

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = "kit/templates/clean-claude.md"
KIT = {
    "scripts/agk/check_x.py": "print('x')\n",
    ".claude/hooks/guard_x.py": "print('g')\n",
    ".github/workflows/governance.yml": "name: governance\n",
    ".github/PULL_REQUEST_TEMPLATE.md": "Advances:\n",
    ".gitignore": "__pycache__/\n",
    "LICENSE-AGK": "The licence of example.com's kit.\n",
    "constitution/principles.md": "# Principles\n",
    "docs/specs/TEMPLATE.md": "# SPEC-NNNN: Title\n",
    "scripts/agk/never_installed.py": "print('n')\n",
}
CLEAN_TOML = (
    'mode = "init"\nversion = "2.0.0"\nexecution = "local"\n\n'
    '[kit]\nlayout = "plugin"\nplugin_version = "2.0.0"\n'
)
RECORDS = {
    "README.md": "A sample product of example.com.\n",
    "src/app.py": "print(1)\n",
    "docs/specs/0001-a-sample.md": "# SPEC-0001: a sample\n",
    "docs/adr/0001-mine.md": "# ADR-0001: mine\n",
    "docs/build-state.md": "| 2026-11-19 | a row |\n",
    "docs/runs/2026-11-19-run.md": "a run of cb-example-1\n",
}
# What the sample's history holds of the table: the install commit, a side branch and the licence.
IN_HISTORY = {
    ".claude/hooks/guard_x.py",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/governance.yml",
    ".gitignore",
    "LICENSE-AGK",
    "constitution/principles.md",
    "docs/specs/TEMPLATE.md",
    "scripts/agk/check_x.py",
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - local git, fixed list
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


@pytest.fixture
def kit(tmp_path, monkeypatch) -> Path:
    """A stub plugin at 2.0.0 with its own `.claude-plugin/plugin.json`."""
    root = tmp_path / "plugin-example"
    write(root, {**KIT, TEMPLATE: (ROOT / TEMPLATE).read_text(encoding="utf-8")})
    write(root, {".claude-plugin/plugin.json": '{"name": "agk", "version": "2.0.0"}\n'})
    manifest = {
        "kit_version": "2.0.0",
        "verbatim": sorted(KIT),
        "templates": {},
        "rendered": [],
        "adopt": {"skip": [], "blocks": {}, "templates": {}},
    }
    row = {"commits": [], "blocks": {}, "templates": {}}
    table = {
        "table": 1,
        "releases": {"2.0.0": {**row, "verbatim": {p: [digest(t)] for p, t in KIT.items()}}},
    }
    write(root, {"kit/manifest.json": json.dumps(manifest), "kit/hashes.json": json.dumps(table)})
    monkeypatch.setattr(uninstall, "KIT_ROOT", root)
    return root


@pytest.fixture
def gh_log(tmp_path, monkeypatch) -> Path:
    """A `gh` on PATH that records any call; none is made."""
    stub = tmp_path / "bin"
    stub.mkdir()
    log = tmp_path / "gh-calls.txt"
    (stub / "gh").write_text(f'#!/bin/sh\necho "$@" >> {log}\n', encoding="utf-8")
    (stub / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", f"{stub}{os.pathsep}{os.environ['PATH']}")
    return log


def clean_sample(tmp_path: Path, over: dict[str, str] | None = None) -> Path:
    """A project installed, then moved to the clean layout, with a kit hook on a side branch."""
    root = tmp_path / "product-example"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "member-example-1@example.com")
    git(root, "config", "user.name", "member-example-1")
    git(root, "config", "commit.gpgsign", "false")
    installed = {
        k: v
        for k, v in KIT.items()
        if k not in (".claude/hooks/guard_x.py", "scripts/agk/never_installed.py")
    }
    write(root, {**installed, **RECORDS, "agk.toml": 'version = "2.0.0"\n'})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "installed")
    git(root, "switch", "-q", "-c", "side")
    write(root, {".claude/hooks/guard_x.py": KIT[".claude/hooks/guard_x.py"]})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "a hook on a side branch")
    git(root, "switch", "-q", "main")
    for rel in (
        "scripts/agk/check_x.py",
        ".github/workflows/governance.yml",
        "constitution/principles.md",
        "docs/specs/TEMPLATE.md",
    ):
        (root / rel).unlink()
    short = (ROOT / TEMPLATE).read_text(encoding="utf-8")
    short = short.replace("{{project}}", "product-example").replace("{{kit_version}}", "2.0.0")
    write(root, {"agk.toml": CLEAN_TOML, "CLAUDE.md": short, **(over or {})})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "clean layout")
    return root


def run(capsys, root: Path, *args: str) -> tuple[int, str]:
    code = uninstall.main([str(root), *args])
    return code, capsys.readouterr().out


def listed(out: str) -> set[str]:
    return {
        ln.split("history path: ", 1)[1]
        for ln in out.splitlines()
        if ln.startswith("history path: ")
    }


def test_the_clean_uninstall_removes_the_licence_and_keeps_specs_and_decisions(
    tmp_path, kit, gh_log, capsys
):
    root = clean_sample(tmp_path)
    head = git(root, "rev-parse", "HEAD").strip()
    code, out = run(capsys, root, "--write")
    assert code == 0, out
    for rel in ("LICENSE-AGK", "agk.toml", "CLAUDE.md"):
        assert not (root / rel).exists(), rel
    for rel in RECORDS:
        assert (root / rel).is_file(), rel  # by default the records stay (Q-S0071-1)
    assert "kept: the specs and decisions (docs/specs/, docs/adr/)" in out
    assert git(root, "branch", "--show-current").strip() == uninstall.BRANCH
    assert git(root, "rev-parse", "HEAD").strip() == head  # one branch, nothing committed
    assert not gh_log.exists()


def test_the_agreed_records_go_and_the_rest_stay(tmp_path, kit, gh_log, capsys):
    root = clean_sample(tmp_path)
    code, out = run(
        capsys, root, "--write", "--agreed", "docs/runs/", "--agreed", "docs/build-state.md"
    )
    assert code == 0, out
    assert not (root / "docs/runs/2026-11-19-run.md").exists()
    assert not (root / "docs/build-state.md").exists()
    assert "delete docs/build-state.md (an agreed record)" in out
    for rel in ("docs/specs/0001-a-sample.md", "docs/adr/0001-mine.md", "src/app.py", "README.md"):
        assert (root / rel).is_file(), rel


def test_specs_and_decisions_go_only_when_named(tmp_path, kit, gh_log, capsys):
    root = clean_sample(tmp_path)
    code, out = run(capsys, root, "--agreed", "docs/specs/")
    assert code == 0, out
    assert "delete docs/specs/0001-a-sample.md (an agreed record)" in out
    assert "docs/adr/0001-mine.md" not in out.split("Left in your files")[0]
    assert "nothing was written" in out and git(root, "status", "--porcelain") == ""


@pytest.mark.parametrize("agreed", ["src/app.py", "../outside.md", "docs/runs/missing.md"])
def test_an_agreed_path_that_is_not_a_record_is_refused_by_the_flag(
    tmp_path, kit, gh_log, capsys, agreed
):
    root = clean_sample(tmp_path)
    code, out = run(capsys, root, "--agreed", agreed)
    assert code == 1
    assert out.startswith("refused: ") and "(setting: --agreed)" in out and agreed not in out
    assert git(root, "status", "--porcelain") == ""


def test_the_printed_clean_up_lists_every_kit_path_of_the_history_with_its_checklist(
    tmp_path, kit, gh_log, capsys
):
    root = clean_sample(tmp_path)
    code, out = run(capsys, root)
    assert code == 0, out
    assert listed(out) == IN_HISTORY  # never-installed paths and project files are not listed
    assert "git filter-repo --invert-paths --paths-from-file" in out
    lines = out.splitlines()
    for item in (
        "the customer's written agreement",
        "audit and retention policy",
        "keep it and record the decision",
        "every clone made again",
        "branch protections paused and restored by the repository's administrator",
        "the kit never runs this, never force-pushes and changes no GitHub setting",
    ):
        assert any(item in ln for ln in lines), item
    assert any(
        ln.startswith("shared with the project's own lines: ") and ".gitignore" in ln
        for ln in lines
    )


def test_no_history_rewrite_no_force_push_and_no_github_write(
    tmp_path, kit, gh_log, capsys, monkeypatch
):
    root = clean_sample(tmp_path)
    calls: list[list[str]] = []
    real = subprocess.run

    def record(argv, *a, **k):
        calls.append(list(argv))
        return real(argv, *a, **k)

    monkeypatch.setattr(uninstall.subprocess, "run", record)
    code, out = run(capsys, root, "--write", "--agreed", "docs/runs/")
    assert code == 0, out
    assert calls and all(c[0] == "git" for c in calls)
    assert not [c for c in calls if {"filter-repo", "push", "filter-branch", "replace"} & set(c)]
    assert not gh_log.exists()
    assert len(git(root, "rev-list", "--all").split()) == 3  # the history is as it was


def test_an_installed_project_prints_no_history_clean_up_and_refuses_agreed(
    tmp_path, kit, gh_log, capsys
):
    root = tmp_path / "installed-example"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    write(root, {**KIT, "agk.toml": 'version = "2.0.0"\n'})
    code, out = run(capsys, root)
    assert code == 0, out
    assert "history path:" not in out and "delete LICENSE-AGK (unchanged kit file)" in out
    code, out = run(capsys, root, "--agreed", "docs/runs/")
    assert code == 1 and "(setting: layout)" in out
