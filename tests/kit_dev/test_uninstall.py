"""Kit-only tests of scripts/agk/uninstall.py (brief #348 build (b), answers 2 to 4 and 6, and the
`--pause` form of answer 1; ADR-0203; REQ-009).

A fixture kit at 2.0.0 whose table also knows 1.0.0 stands for the plugin; targets are git work
trees installed at either release. One test removes the kit from a real install of this checkout.
No network: a `gh` on PATH records any call, and none is made.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from conftest import KIT_ROOT, copy_of, git, snapshot

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import common  # noqa: E402
import kit_hashes  # noqa: E402
import uninstall  # noqa: E402

REVIEWERS = (
    "version: 1\n"
    "classes:\n"
    "  protected: {paths: [config/, agk.toml], approvers: [maintainers]}\n"
    "teams:\n"
    '  maintainers: {github_team: "@demo"}\n'
)
PROTECTED = "config/\n.claude/\n.github/\nscripts/agk/\nMakefile\nagk.mk\nagk.toml\nCLAUDE.md\n"
OLD = {
    "scripts/agk/check_x.py": "x old\n",
    ".claude/hooks/h.py": "h old\n",
    ".github/workflows/governance.yml": "gov old\n",
    "agk.mk": "agk-governance:\n\ttrue\n",
    "Makefile": "include agk.mk\n\ngovernance: agk-governance\n",
    ".gitignore": "# >>> agk\n__pycache__/\n# <<< agk\n",
    "CLAUDE.md": "# rules old\n",
    "docs/adr/TEMPLATE.md": "adr template old\n",
    "config/session-rules.md": "rules old\n",
    "gone.txt": "only release 1.0.0 shipped this\n",
}
NEW = {
    **{k: v for k, v in OLD.items() if k != "gone.txt"},
    "scripts/agk/check_x.py": "x new\n",
    "scripts/agk/check_y.py": "y new\n",
    ".github/workflows/governance.yml": "gov new\n",
    ".gitignore": "# >>> agk\n__pycache__/\n.ruff_cache/\n# <<< agk\n",
    "CLAUDE.md": "# rules new\n",
}
TEMPLATES = {
    "kit/templates/agk.toml": (
        'mode = "init"\nversion = "{{kit_version}}"\ninstalled = "{{date}}"\n'
        'default_branch = "{{default_branch}}"\npr_mode = "strict"\n'
        "# [flow]\n# claim_stale_hours = 24\n"
    ),
    "kit/templates/agk.adopt.toml": 'mode = "adopt"\nversion = "{{kit_version}}"\n',
    "kit/templates/protected-paths.txt": PROTECTED,
    "kit/templates/neutrality.txt": "# tokens\n",
    "kit/templates/reviewers.yaml": REVIEWERS,
    "kit/templates/gitignore": "__pycache__/\n.ruff_cache/\n",
    "kit/templates/gitattributes": "docs/runs/decisions-log.md merge=union\n",
    "kit/templates/adr.md": "# ADR-0001: {{project}} adopts agk\n",
    "kit/templates/requirements.md": "# Requirements\n",
    "kit/templates/vision.md": "# Vision\n",
}
OLD_TEMPLATES = {**TEMPLATES, "kit/templates/gitignore": "__pycache__/\n"}
RULESET = {"ruleset": {"name": "agk default branch"}}
AGK_TOML = (
    '# settings\nmode = "{mode}"\nversion = "{version}"\ninstalled = "2026-01-02"\n'
    'default_branch = "main"\npr_mode = "flow"\n\n[flow]\nclaim_stale_hours = 12\n'
)
PROJECT = {
    "src/app.py": "print(1)\n",
    "tests/test_app.py": "def test_app():\n    assert True\n",
    "docs/requirements.md": "# Requirements\n\n### REQ-001 — mine\n",
    "docs/adr/0001-adopt-agk.md": "# ADR-0001: proj adopts agk\n",
    "docs/adr/0002-mine.md": "# ADR-0002: mine\n",
    "docs/specs/0001-mine.md": "# SPEC-0001\n",
    "docs/briefs/0001-mine.md": "# brief\n",
    "docs/runs/decisions-log.md": "# Decisions log\n",
    "docs/build-state.md": "# Build state\n",
    "docs/design/theme.md": "# Theme\n",
    "constitution/vision.md": "# Vision of mine\n",
}


def manifest_of(version: str, files: dict) -> dict:
    templates = {
        "agk.toml": "kit/templates/agk.toml",
        "config/protected-paths.txt": "kit/templates/protected-paths.txt",
        "config/neutrality.txt": "kit/templates/neutrality.txt",
        "config/reviewers.yaml": "kit/templates/reviewers.yaml",
        ".gitattributes": "kit/templates/gitattributes",
        "docs/adr/0001-adopt-agk.md": "kit/templates/adr.md",
        "docs/requirements.md": "kit/templates/requirements.md",
        "constitution/vision.md": "kit/templates/vision.md",
    }
    return {
        "kit_version": version,
        "kit_tests": "tests/kit",
        "verbatim": sorted(files),
        "experimental": [],
        "templates": templates,
        "rendered": [".github/CODEOWNERS"],
        "adopt": {
            "skip": ["Makefile"],
            "blocks": {
                ".gitignore": "hash",
                "CLAUDE.md": "html",
                ".github/CODEOWNERS": "hash",
                ".gitattributes": "hash",
            },
            "templates": {**templates, "agk.toml": "kit/templates/agk.adopt.toml"},
            "block_sources": {
                ".gitignore": "kit/templates/gitignore",
                ".gitattributes": "kit/templates/gitattributes",
            },
        },
        "extendable": {".gitignore": "hash"},
    }


def make_kit(tmp_path: Path) -> Path:
    root = tmp_path / "kit_root"
    table: dict = {"table": 1, "releases": {}}
    for version, files, templates in (("1.0.0", OLD, OLD_TEMPLATES), ("2.0.0", NEW, TEMPLATES)):
        manifest = manifest_of(version, files)
        store = {k: v.encode() for k, v in {**files, **templates}.items()}
        snap = kit_hashes.snapshot_of(manifest, store.get)
        table["releases"][version] = {
            "commits": [],
            **{name: {p: [d] for p, d in snap[name].items()} for name in snap},
        }
        if version == "2.0.0":
            for rel, data in store.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(data)
            (root / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "kit" / "hashes.json").write_text(kit_hashes.dump(table), encoding="utf-8")
    (root / "kit" / "templates" / "ruleset.json").write_text(json.dumps(RULESET), encoding="utf-8")
    return root


def put(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def commit(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "state")


def new_repo(tmp_path: Path) -> Path:
    root = tmp_path / "target"
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    return root


def init_target(tmp_path: Path, files: dict = NEW, version: str = "2.0.0", **over: str) -> Path:
    """An init install at VERSION: the kit's files of that release, its rendered templates, the
    project's own files; committed, so the work tree is clean."""
    root = new_repo(tmp_path)
    put(root, files)
    put(
        root,
        {
            "agk.toml": AGK_TOML.format(mode="init", version=version),
            "config/protected-paths.txt": PROTECTED,
            "config/neutrality.txt": "# tokens\n",
            "config/reviewers.yaml": REVIEWERS,
            ".gitattributes": TEMPLATES["kit/templates/gitattributes"],
            ".github/CODEOWNERS": uninstall.codeowners_of_text(REVIEWERS),
            **PROJECT,
        },
    )
    put(root, over)
    commit(root)
    return root


def adopt_target(tmp_path: Path, **over: str) -> Path:
    """An adopt install at 2.0.0: whole kit files, and marked blocks in the project's own files."""
    root = new_repo(tmp_path)
    whole = (
        "scripts/agk/check_x.py",
        "scripts/agk/check_y.py",
        ".claude/hooks/h.py",
        ".github/workflows/governance.yml",
        "agk.mk",
        "docs/adr/TEMPLATE.md",
        "config/session-rules.md",
    )
    put(root, {k: NEW[k] for k in whole})
    put(
        root,
        {
            ".gitignore": "build/\n# >>> agk\n__pycache__/\n.ruff_cache/\n# <<< agk\n*.log\n",
            "CLAUDE.md": "# my rules\n<!-- >>> agk -->\n# rules new\n<!-- <<< agk -->\nmore\n",
            ".gitattributes": (
                "*.png binary\n# >>> agk\ndocs/runs/decisions-log.md merge=union\n# <<< agk\n"
            ),
            "Makefile": "include agk.mk\n\nbuild:\n\tcc main.c\n",
            "agk.toml": AGK_TOML.format(mode="adopt", version="2.0.0"),
            "config/protected-paths.txt": PROTECTED,
            "config/reviewers.yaml": REVIEWERS,
            ".github/CODEOWNERS": "* @owner\n# >>> agk\n"
            + uninstall.codeowners_of_text(REVIEWERS)
            + "# <<< agk\n",
            **PROJECT,
        },
    )
    put(root, over)
    commit(root)
    return root


@pytest.fixture
def kit(tmp_path, monkeypatch) -> Path:
    root = make_kit(tmp_path)
    monkeypatch.setattr(uninstall, "KIT_ROOT", root)
    return root


@pytest.fixture
def gh_log(tmp_path, monkeypatch) -> Path:
    """A `gh` first on PATH that records any call: the tool must make none."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh-calls"
    gh = bin_dir / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\nexit 1\n', encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return log


def run(capsys, target: Path, *args: str) -> tuple[int, list[str]]:
    code = uninstall.main([str(target), *args])
    return code, capsys.readouterr().out.splitlines()


def paths_of(out: list[str], action: str) -> list[str]:
    return [ln.split(" ", 1)[1].split(" (")[0] for ln in out if ln.startswith(action + " ")]


def branch(root: Path) -> str:
    return subprocess.run(
        ["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


KIT_FILES = sorted(
    {*NEW, "agk.toml", "config/protected-paths.txt", "config/neutrality.txt"}
    | {"config/reviewers.yaml", ".gitattributes", ".github/CODEOWNERS"}
)


# --- a dry run writes nothing (answer 6) ---------------------------------------------------------


def test_a_dry_run_is_the_default_and_writes_nothing(tmp_path, kit, capsys, gh_log):
    """REQ-009: answers 2 and 6 (a dry run by default writes nothing, makes no branch)."""
    target = init_target(tmp_path)
    before = snapshot(target)
    code, out = run(capsys, target)
    assert code == 0, out
    assert snapshot(target) == before
    assert branch(target) == "main"
    assert paths_of(out, "delete") == KIT_FILES
    assert any(
        ln.startswith(f"dry run: {len(KIT_FILES)} files would be deleted, 0 edited;") for ln in out
    ), out
    assert "next: run again with --write to build the branch" in out
    assert not gh_log.exists()


# --- removal of unchanged files only (answers 2 and 6) -------------------------------------------


def test_write_deletes_every_unchanged_kit_file_on_one_new_branch(tmp_path, kit, capsys, gh_log):
    """REQ-009: answer 2 (unchanged kit files deleted, on one branch, nothing committed)."""
    target = init_target(tmp_path)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=target, capture_output=True, text=True, check=True
    ).stdout
    code, out = run(capsys, target, "--write")
    assert code == 0, out
    assert branch(target) == uninstall.BRANCH
    for rel in KIT_FILES:
        assert not (target / rel).exists(), rel
    for rel, text in PROJECT.items():
        assert (target / rel).read_text(encoding="utf-8") == text, rel
    assert not (target / "scripts").exists() and not (target / ".claude").exists()
    assert (
        subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=target, capture_output=True, text=True, check=True
        ).stdout
        == head
    )  # nothing committed
    assert any(
        ln.startswith(f"branch {uninstall.BRANCH}: deleted {len(KIT_FILES)} files") for ln in out
    ), out
    assert not gh_log.exists()


def test_a_project_installed_at_an_older_release_is_read_by_its_own_row(tmp_path, kit, capsys):
    """REQ-009: answer 6 (a project at an older release: its digests are in older rows)."""
    target = init_target(tmp_path, files=OLD, version="1.0.0")
    code, out = run(capsys, target, "--write")
    assert code == 0, out
    assert "gone.txt" in paths_of(out, "delete")  # a file only the older release shipped
    assert paths_of(out, "changed") == []
    for rel in OLD:
        assert not (target / rel).exists(), rel
    assert (target / "src" / "app.py").is_file()


# --- a changed kit file is listed, not deleted ---------------------------------------------------


def test_a_changed_kit_file_is_listed_and_kept(tmp_path, kit, capsys):
    """REQ-009: answer 2 (a kit file the project changed is listed, not deleted)."""
    target = init_target(
        tmp_path, **{"scripts/agk/check_x.py": "my edit\n", "config/reviewers.yaml": "mine: 1\n"}
    )
    code, out = run(capsys, target, "--write")
    assert code == 0, out
    assert paths_of(out, "changed") == [
        ".github/CODEOWNERS",  # no longer what the kit generates from reviewers.yaml
        "config/reviewers.yaml",
        "scripts/agk/check_x.py",
    ]
    line = next(ln for ln in out if ln.startswith("changed scripts/agk/check_x.py"))
    assert "path class scripts/agk/" in line and "kept for you to decide" in line
    assert "my edit" not in "\n".join(out)  # a message names the path class, never the content
    assert (target / "scripts" / "agk" / "check_x.py").read_text() == "my edit\n"
    assert not (target / "scripts" / "agk" / "check_y.py").exists()


def test_a_symlink_at_a_kit_path_is_listed_and_kept(tmp_path, kit, capsys):
    """REQ-009: answer 2 (only regular files are deleted)."""
    target = init_target(tmp_path)
    (target / "agk.mk").unlink()
    (target / "agk.mk").symlink_to("Makefile")
    commit(target)
    code, out = run(capsys, target, "--write")
    assert code == 0
    assert "agk.mk" in paths_of(out, "changed")
    assert (target / "agk.mk").is_symlink()


# --- the kit's own lines only (answer 2) ---------------------------------------------------------


def test_the_kit_block_leaves_a_file_and_the_project_lines_stay(tmp_path, kit, capsys):
    """REQ-009: answer 2 (`.gitattributes`, `.gitignore`, `CLAUDE.md`: the kit's lines only)."""
    target = adopt_target(tmp_path)
    code, out = run(capsys, target, "--write")
    assert code == 0, out
    assert paths_of(out, "edit") == [
        ".gitattributes",
        ".github/CODEOWNERS",
        ".gitignore",
        "CLAUDE.md",
        "Makefile",
    ]
    assert (target / ".gitignore").read_text() == "build/\n*.log\n"
    assert (target / "CLAUDE.md").read_text() == "# my rules\nmore\n"
    assert (target / ".gitattributes").read_text() == "*.png binary\n"
    assert (target / ".github" / "CODEOWNERS").read_text() == "* @owner\n"
    assert "edit .gitignore (agk block removed; project lines kept: 2)" in out


def test_a_changed_block_is_listed_and_the_file_kept(tmp_path, kit, capsys):
    """REQ-009: answer 2 (a block the project changed is not the kit's own lines)."""
    text = "# mine\n<!-- >>> agk -->\n# rules I rewrote\n<!-- <<< agk -->\n"
    target = adopt_target(tmp_path, **{"CLAUDE.md": text})
    code, out = run(capsys, target, "--write")
    assert code == 0
    assert "CLAUDE.md" in paths_of(out, "changed")
    assert (target / "CLAUDE.md").read_text() == text


def test_the_makefile_include_goes_with_agk_mk_and_the_rest_stays(tmp_path, kit, capsys):
    """REQ-009: answer 2 (the kit's `Makefile` include, removed where it is the kit's line)."""
    mine = "include agk.mk\n\ngovernance: agk-governance\n\nbuild:\n\tcc main.c\n"
    target = init_target(tmp_path, **{"Makefile": mine})
    code, out = run(capsys, target, "--write")
    assert code == 0, out
    assert paths_of(out, "edit") == ["Makefile"]
    assert "Makefile" not in paths_of(out, "changed")
    assert (
        target / "Makefile"
    ).read_text() == "\ngovernance: agk-governance\n\nbuild:\n\tcc main.c\n"
    line = next(ln for ln in out if ln.startswith("edit Makefile"))
    assert "include agk.mk" in line and "kept for you to decide" in line
    assert not (target / "agk.mk").exists()


def test_agk_toml_goes_only_when_it_holds_the_kits_settings_alone(tmp_path, kit, capsys):
    """REQ-009: answer 2 (`agk.toml`, removed only where it is the kit's own)."""
    target = init_target(tmp_path)
    assert run(capsys, target)[1].count("delete agk.toml (the kit's settings only)") == 1
    mine = AGK_TOML.format(mode="init", version="2.0.0") + "\n[my_tool]\nlevel = 3\n"
    target = init_target(tmp_path / "second", **{"agk.toml": mine})
    code, out = run(capsys, target, "--write")
    assert code == 0
    assert "agk.toml" in paths_of(out, "changed")
    assert "settings the kit does not read: my_tool" in next(
        ln for ln in out if ln.startswith("changed agk.toml")
    )
    assert (target / "agk.toml").read_text() == mine


# --- the project's documents are kept (answer 3) -------------------------------------------------


def test_the_projects_documents_are_kept_and_remove_docs_only_lists_them(tmp_path, kit, capsys):
    """REQ-009: answer 3 (kept by default; `--remove-docs` lists, never deletes)."""
    target = init_target(tmp_path)
    code, out = run(capsys, target, "--write", "--remove-docs")
    assert code == 0, out
    listed = sorted(ln.split(": ", 1)[1] for ln in out if ln.startswith("remove by hand: "))
    assert listed == sorted(rel for rel in PROJECT if rel.startswith(("docs/", "constitution/")))
    for rel, text in PROJECT.items():
        assert (target / rel).read_text(encoding="utf-8") == text, rel
    assert not (target / "docs" / "adr" / "TEMPLATE.md").exists()  # the kit's template, not an ADR
    assert any("never deletes the project's own documents" in ln for ln in out)


def test_a_document_that_matches_a_kit_template_is_still_kept(tmp_path, kit, capsys):
    """REQ-009: answer 3 (the requirements file and the vision, even as the kit wrote them)."""
    target = init_target(
        tmp_path,
        **{"docs/requirements.md": "# Requirements\n", "constitution/vision.md": "# Vision\n"},
    )
    code, out = run(capsys, target, "--write")
    assert code == 0
    assert (target / "docs" / "requirements.md").is_file()
    assert (target / "constitution" / "vision.md").is_file()
    assert "docs/requirements.md" not in "\n".join(out)


# --- the GitHub side is printed (answer 4) -------------------------------------------------------


def test_the_github_side_is_printed_and_never_done(tmp_path, kit, capsys, gh_log):
    """REQ-009: answer 4 (ruleset by name, labels, issues, plugin command; no `gh` call)."""
    target = init_target(tmp_path)
    code, out = run(capsys, target)
    assert code == 0
    text = "\n".join(out)
    assert 'ruleset "agk default branch"' in text
    labels = next(ln for ln in out if ln.startswith("- labels: "))
    for name in ("agk:ci-running", "agk:ready", "agk-brief", "agk-conductor"):
        assert name in labels
    issues = next(ln for ln in out if ln.startswith("- issues: "))
    assert '"The default branch is red"' in issues and "agk-drift-audit" in issues
    assert "claude plugin uninstall agk@agk" in text and "(verify)" in text
    assert not gh_log.exists()


def test_the_printed_labels_and_title_are_the_kits_own():
    """REQ-009: answer 4 (the list follows the router's labels and the red-branch title)."""
    import route  # noqa: PLC0415
    import session  # noqa: PLC0415

    assert uninstall.LABELS[: len(route.LABELS)] == route.LABELS
    assert uninstall.RED_TITLE == session.RED_TITLE
    assert json.loads((KIT_ROOT / uninstall.RULESET).read_text())["ruleset"]["name"]


def test_the_removal_prints_an_adr_skeleton_naming_each_protected_class(tmp_path, kit, capsys):
    """REQ-009: answer 2 (the removal pull request is reviewed: its protected classes)."""
    target = init_target(tmp_path)
    out = run(capsys, target)[1]
    line = next(ln for ln in out if ln.startswith("Protected classes: "))
    for cls in ("config/", ".claude/", ".github/", "scripts/agk/", "Makefile", "agk.mk"):
        assert f"`{cls}`" in line
    assert "# ADR-NNNN: Remove agk from the project" in out


# --- refusals ------------------------------------------------------------------------------------


def test_write_refuses_a_work_tree_with_changes_and_writes_nothing(tmp_path, kit, capsys):
    """REQ-009: answer 2 (the branch holds the removal only)."""
    target = init_target(tmp_path)
    (target / "src" / "app.py").write_text("print(2)\n")
    before = snapshot(target)
    code, out = run(capsys, target, "--write")
    assert code == 1
    assert out[0].startswith("refused: the work tree has changes")
    assert snapshot(target) == before and branch(target) == "main"


def test_write_refuses_an_existing_branch(tmp_path, kit, capsys):
    """REQ-009: answer 2 (one new branch, never an existing one)."""
    target = init_target(tmp_path)
    git(target, "branch", uninstall.BRANCH)
    before = snapshot(target)
    code, out = run(capsys, target, "--write")
    assert code == 1 and "exists already" in out[0]
    assert snapshot(target) == before


def test_refusals_name_the_path_class(tmp_path, kit, capsys):
    """REQ-009: answer 2 (no agk.toml, not a git work tree, the kit itself; usage)."""
    bare = tmp_path / "bare"
    bare.mkdir()
    assert run(capsys, bare) == (1, ["refused: TARGET is not a git work tree (path class .git/)"])
    repo = new_repo(tmp_path)
    code, out = run(capsys, repo)
    assert code == 1 and out == [
        "refused: agk.toml is missing (path class agk.toml): no kit installed"
    ]
    assert run(capsys, kit)[0] == 1
    assert uninstall.main([]) == 2
    assert uninstall.main([str(repo), "--pause", "--remove-docs"]) == 2
    assert uninstall.main([str(repo), "--force"]) == 2


# --- pause (answer 1, the command of build (b)) --------------------------------------------------


def test_pause_dry_run_writes_nothing(tmp_path, kit, capsys, gh_log):
    """REQ-009: answer 1 (`--pause` is a dry run too until `--write`)."""
    target = init_target(tmp_path)
    before = snapshot(target)
    code, out = run(capsys, target, "--pause")
    assert code == 0, out
    assert out[0] == "edit agk.toml (adds the top-level line `paused = true`)"
    assert "dry run: 1 file would be edited; nothing was written" in out
    assert snapshot(target) == before and branch(target) == "main"
    assert not gh_log.exists()


def test_pause_write_adds_the_top_level_line_on_its_own_branch(tmp_path, kit, capsys):
    """REQ-009: answer 1 (one branch that sets `paused = true`; the ADR is the person's)."""
    target = init_target(tmp_path)
    code, out = run(capsys, target, "--pause", "--write")
    assert code == 0, out
    assert branch(target) == uninstall.PAUSE_BRANCH
    assert common.paused(target) is True
    data = tomllib.loads((target / "agk.toml").read_text())
    assert data["flow"] == {"claim_stale_hours": 12} and "paused" not in data["flow"]
    assert "Protected classes: `agk.toml`" in out
    assert "# ADR-NNNN: Pause agk" in out
    assert not list((target / "docs" / "adr").glob("0003*"))  # the tool writes no ADR
    assert (target / "scripts" / "agk" / "check_x.py").is_file()  # nothing is deleted
    # resume: removing the line resumes
    text = (target / "agk.toml").read_text().replace("paused = true\n", "")
    (target / "agk.toml").write_text(text)
    assert common.paused(target) is False


def test_pause_replaces_false_and_a_paused_project_has_nothing_to_do(tmp_path, kit, capsys):
    """REQ-009: answer 1 (`paused = false` becomes true; a paused project is left as it is)."""
    mine = 'paused = false\nmode = "init"\nversion = "2.0.0"\n'
    target = init_target(tmp_path, **{"agk.toml": mine})
    assert run(capsys, target, "--pause", "--write")[0] == 0
    assert (target / "agk.toml").read_text() == 'paused = true\nmode = "init"\nversion = "2.0.0"\n'
    commit(target)
    code, out = run(capsys, target, "--pause", "--write")
    assert code == 0 and out == ["nothing to do: agk paused already (setting: paused in agk.toml)"]


def test_pause_refuses_a_bad_value_by_the_settings_name(tmp_path, kit, capsys):
    """REQ-009: answer 1 (a refusal names the setting, never the value)."""
    target = init_target(tmp_path, **{"agk.toml": 'paused = "secretvalue"\n'})
    code, out = run(capsys, target, "--pause")
    assert code == 1
    assert "setting: paused in agk.toml" in out[0] and "secretvalue" not in out[0]


# --- a real install of this checkout -------------------------------------------------------------


def test_a_real_install_leaves_only_the_projects_own_files(
    shared_install, tmp_path, monkeypatch, capsys
):
    """REQ-009: answers 2, 3 and 6 on an install of this checkout (its files as one more row)."""
    target = copy_of(shared_install, tmp_path)
    commit(target)
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))

    def read(rel: str) -> bytes | None:
        path = KIT_ROOT / rel
        return common.lf(path.read_bytes()) if path.is_file() else None

    snap = kit_hashes.snapshot_of(manifest, read)
    table = uninstall.load_table(KIT_ROOT)
    table["releases"]["9.9.9"] = {name: {p: [d] for p, d in snap[name].items()} for name in snap}
    monkeypatch.setattr(uninstall, "load_table", lambda _root: table)
    code, out = run(capsys, target, "--write")
    assert code == 0, out
    left = {
        p.relative_to(target).as_posix()
        for p in target.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(target).parts
    }
    assert left == {
        "README.md",
        "config/reviewers.yaml",  # the handle was set: a changed kit file, listed
        "constitution/vision.md",
        "docs/adr/0001-adopt-agk.md",
        "docs/build-state.md",
        "docs/requirements.md",
        "docs/runs/decisions-log.md",
        "docs/runs/residuals.md",
        "pyproject.toml",
    }, out
    assert paths_of(out, "changed") == ["config/reviewers.yaml"]
    assert paths_of(out, "kept") == ["pyproject.toml"]
    doctor = subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "doctor.py"), str(target)],
        capture_output=True,
        text=True,
    )
    assert doctor.returncode == 0 and "summary: no kit installed" in doctor.stdout  # answer 5


# --- the skill (`/agk:uninstall`) ----------------------------------------------------------------


def test_the_skill_previews_each_form_before_it_writes():
    """REQ-009: answers 1 and 2 (`/agk:uninstall` is a dry run by default; `--write` after)."""
    import re  # noqa: PLC0415

    text = (KIT_ROOT / "skills" / "uninstall" / "SKILL.md").read_text(encoding="utf-8")
    calls = re.findall(r'python3 "\$\{CLAUDE_PLUGIN_ROOT\}/scripts/agk/uninstall\.py" (.*)', text)
    assert calls == [". --pause", ". --pause --write", ".", ". --write"]
    assert "disable-model-invocation: true" in text
    for verb in ("git push", "git commit", "gh pr", "gh api"):
        assert verb not in text
