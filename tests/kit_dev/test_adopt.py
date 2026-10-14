"""Tests of scripts/agk/adopt.py (SPEC-0002 rules 1-4, 7, 9, 11, 13-18)."""

from __future__ import annotations

import ast
import hashlib
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo, manifest, run_init, snapshot

ADOPT = KIT_ROOT / "scripts" / "agk" / "adopt.py"

ADOPTED_PROTECTED = [
    "constitution/",
    "config/",
    ".claude/",
    ".github/",
    "docs/requirements.md",
    "CLAUDE.md",
    "scripts/agk/",
    "tests/kit/",
    "agk.mk",
    "agk.toml",
]

MAKEFILE = "test:\n\t@echo PROJECT_OWN_TEST_RAN\n"
PYPROJECT = (
    '[build-system]\nrequires = ["hatchling>=0.25.1"]\nbuild-backend = "hatchling.build"\n\n'
    '[project]\nname = "pkg"\nversion = "1.0"\n\n[tool.hatch.version]\npath = "pkg/__init__.py"\n'
)
GITIGNORE = "*.pyc\n/build/\n"
CI = "name: ci\non: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps: []\n"
CODEOWNERS = "* @project-owner\n/pkg/ @project-owner\n"
UNITTEST = (
    "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_x(self):\n"
    "        self.assertTrue(True)\n"
)


def adopt(target: Path, *args: str, **kw):
    return subprocess.run(
        [sys.executable, str(ADOPT), str(target), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
        **kw,
    )


def make_existing(root: Path, branch: str = "master", origin: bool = True, **files: str) -> Path:
    """A synthetic existing project: Makefile with its own test, hatch pyproject, master branch."""
    root.mkdir(parents=True, exist_ok=True)
    tree = {
        "Makefile": MAKEFILE,
        "pyproject.toml": PYPROJECT,
        ".gitignore": GITIGNORE,
        ".github/workflows/ci.yml": CI,
        ".github/FUNDING.yml": "github: [someone]\n",
        ".github/CODEOWNERS": CODEOWNERS,
        "README.md": "# project\n",
        "pkg/__init__.py": "__version__ = '1.0'\n",
        "pkg/tests/__init__.py": "",
        "pkg/tests/x_test.py": UNITTEST,
        "tox.ini": "[tox]\nenvlist = py311\n",
    }
    tree.update(files)
    git(root, "init", "-q", "-b", branch)
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    for rel, text in tree.items():
        if text is None:
            continue
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "initial")
    if origin:
        git(root, "remote", "add", "origin", "https://example.invalid/project.git")
        git(root, "update-ref", f"refs/remotes/origin/{branch}", "HEAD")
        git(root, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{branch}")
    return root


@pytest.fixture
def existing(tmp_path: Path) -> Path:
    return make_existing(tmp_path / "proj")


@pytest.fixture
def adopted(existing: Path) -> Path:
    proc = adopt(existing)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return existing


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_before(root: Path) -> dict[str, bytes]:
    out = git_out(root, "ls-files", "-z")
    return {p: (root / p).read_bytes() for p in out.split("\0") if p}


def git_out(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


def adopt_files() -> set[str]:
    m = manifest()
    a = m["adopt"]
    owned = set(m["verbatim"]) - set(a["skip"])
    return owned | set(a["templates"]) | set(a["blocks"])


# --- Interface and effects (rules 1-3) ---------------------------------------------------------


def test_ac2_usage_errors_exit_2(tmp_path):
    """REQ-010 AC2: rules 1-2."""
    for args in ([], ["--bogus"], [str(tmp_path), "extra"], [str(tmp_path), "--dry-run", "--x"]):
        proc = subprocess.run(
            [sys.executable, str(ADOPT), *args], capture_output=True, text=True, env=clean_env()
        )
        assert proc.returncode == 2, args


def test_ac2_unusable_targets_exit_1_and_write_nothing(tmp_path):
    """REQ-010 AC2: rules 1-2."""
    assert adopt(tmp_path / "missing").returncode == 1
    afile = tmp_path / "f"
    afile.write_text("x")
    assert adopt(afile).returncode == 1
    plain = tmp_path / "plain"
    plain.mkdir()
    proc = adopt(plain)
    assert proc.returncode == 1 and "git" in proc.stdout.lower()
    assert not any(plain.iterdir())


def test_ac2_self_target_refused(tmp_path):
    """REQ-010 AC2: rule 2."""
    for tgt in (KIT_ROOT, KIT_ROOT / "docs"):
        proc = adopt(tgt)
        assert proc.returncode == 1 and "kit/" in proc.stdout + proc.stderr


def test_ac2_interpreter_refusal_below_3_11():
    """REQ-010 AC2: rule 2."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import init

    assert init.check_interpreter((3, 10, 9)) is not None
    assert init.check_interpreter((3, 12, 0)) is None


def test_ac2_adopt_has_no_network_or_process_imports():
    """REQ-010 AC2: rules 1-2 (stdlib only, no git/gh/network)."""
    tree = ast.parse(ADOPT.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    assert not names & {"subprocess", "socket", "urllib", "http", "ftplib", "smtplib", "ssl"}
    assert names <= set(sys.stdlib_module_names) | {"common", "reviewers", "init"}


def test_ac2_target_files_are_never_executed_or_imported():
    """REQ-010 AC2: rule 3. adopt.py has no exec/eval/import of target code."""
    text = ADOPT.read_text(encoding="utf-8")
    for needle in ("exec(", "eval(", "importlib", "runpy", "__import__"):
        assert needle not in text, needle


# --- What a product file is (rules 4, 11) -------------------------------------------------------


def test_ac1_pre_existing_files_are_byte_identical_except_marked_blocks(existing):
    """REQ-010 AC1: rule 4, 18."""
    before = tracked_before(existing)
    proc = adopt(existing)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    block_files = {".gitignore", ".github/CODEOWNERS"}
    for rel, data in before.items():
        now = (existing / rel).read_bytes()
        if rel in block_files:
            assert now.startswith(data) and now != data, rel
            assert b">>> agk" in now[len(data) :] and b"<<< agk" in now[len(data) :], rel
        else:
            assert now == data, rel


def test_ac1_adopt_creates_exactly_the_adopt_owned_files(existing):
    """REQ-010 AC1: rule 4."""
    before = set(snapshot(existing))
    assert adopt(existing).returncode == 0
    created = set(snapshot(existing)) - before
    expected = adopt_files() - {".gitignore", ".github/CODEOWNERS"}
    assert created == expected
    for never in ("Makefile", "pyproject.toml", "tox.ini", "README.md"):
        assert never not in created


def test_ac1_makefile_and_project_make_test_are_untouched(adopted):
    """REQ-010 AC1: rules 4 and 18. The project's own make test still runs its own target."""
    assert (adopted / "Makefile").read_text() == MAKEFILE
    proc = subprocess.run(["make", "test"], cwd=adopted, capture_output=True, text=True)
    assert proc.returncode == 0 and "PROJECT_OWN_TEST_RAN" in proc.stdout
    assert (adopted / "pyproject.toml").read_text() == PYPROJECT


def test_ac1_existing_claude_md_and_pr_template_get_one_appended_block(tmp_path):
    """REQ-010 AC1: rule 11."""
    root = make_existing(
        tmp_path / "p",
        **{
            "CLAUDE.md": "# project notes\n\nKeep it short.",
            ".github/PULL_REQUEST_TEMPLATE.md": "## Summary\n",
        },
    )
    assert adopt(root).returncode == 0
    for rel, begin in (
        ("CLAUDE.md", "<!-- >>> agk -->"),
        (".github/PULL_REQUEST_TEMPLATE.md", "<!-- >>> agk -->"),
    ):
        text = (root / rel).read_text()
        assert text.count(begin) == 1 and text.count("<!-- <<< agk -->") == 1, rel
    assert (root / "CLAUDE.md").read_text().startswith("# project notes\n\nKeep it short.")
    assert adopt(root).stdout.count("nothing to do") == 1


def test_ac1_absent_claude_md_and_pr_template_are_created_whole(existing):
    """REQ-010 AC1: rule 4."""
    assert adopt(existing).returncode == 0
    for rel in ("CLAUDE.md", ".github/PULL_REQUEST_TEMPLATE.md"):
        assert (existing / rel).read_bytes() == (KIT_ROOT / rel).read_bytes(), rel
        assert b">>> agk" not in (existing / rel).read_bytes()


def test_ac1_gitignore_absent_gets_the_block_only(tmp_path):
    """REQ-010 AC1: rule 4."""
    root = make_existing(tmp_path / "p", **{".gitignore": None})
    assert adopt(root).returncode == 0
    text = (root / ".gitignore").read_text()
    assert text.startswith("# >>> agk\n") and text.rstrip().endswith("# <<< agk")


def test_ac1_block_after_a_file_without_trailing_newline_keeps_the_old_bytes(tmp_path):
    """REQ-010 AC1: rule 4."""
    root = make_existing(tmp_path / "p", **{".gitignore": "*.pyc"})
    assert adopt(root).returncode == 0
    assert (root / ".gitignore").read_text().startswith("*.pyc\n# >>> agk\n")


def test_ac1_codeowners_block_matches_and_check_codeowners_passes(adopted):
    """REQ-010 AC1: rule 11. A project CODEOWNERS keeps its lines; the block is checked alone."""
    text = (adopted / ".github" / "CODEOWNERS").read_text()
    assert text.startswith(CODEOWNERS) and "# >>> agk" in text
    proc = subprocess.run(
        [sys.executable, "scripts/agk/reviewers.py", "--check-codeowners"],
        cwd=adopted,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout
    (adopted / ".github" / "CODEOWNERS").write_text(text.replace("@REPLACE-ME", "@someone-else"))
    bad = subprocess.run(
        [sys.executable, "scripts/agk/reviewers.py", "--check-codeowners"],
        cwd=adopted,
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 1


def test_ac1_absent_codeowners_is_created_whole_and_checked(tmp_path):
    """REQ-010 AC1: rule 4."""
    root = make_existing(tmp_path / "p", **{".github/CODEOWNERS": None})
    assert adopt(root).returncode == 0
    assert b">>> agk" not in (root / ".github" / "CODEOWNERS").read_bytes()
    check = subprocess.run(
        [sys.executable, "scripts/agk/reviewers.py", "--check-codeowners"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0


# --- Default branch and agk.toml (rule 7, 9) ----------------------------------------------------


def test_ac1_agk_toml_is_stamped_for_adopt(adopted):
    """REQ-010 AC1: rules 5, 7, 9."""
    cfg = tomllib.loads((adopted / "agk.toml").read_text(encoding="utf-8"))
    assert cfg["mode"] == "adopt"
    assert cfg["version"] == manifest()["kit_version"]
    assert cfg["default_branch"] == "master"
    assert cfg["test_dirs"] == ["pkg/tests"]
    assert cfg["test_patterns"] == ["*_test.py"]
    assert cfg["project_tests"] == ""
    assert cfg["lint_paths"] == ["scripts/agk", "tests/kit", ".claude/hooks"]


def test_ac1_default_branch_from_head_when_there_is_no_origin(tmp_path):
    """REQ-010 AC1: rule 7."""
    root = make_existing(tmp_path / "p", branch="trunk", origin=False)
    assert adopt(root).returncode == 0
    cfg = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    assert cfg["default_branch"] == "trunk"


def test_ac2_unknown_default_branch_refuses_and_writes_nothing(tmp_path):
    """REQ-010 AC2: rules 7 and 15 (origin exists but origin/HEAD does not)."""
    root = make_existing(tmp_path / "p", origin=False)
    git(root, "remote", "add", "origin", "https://example.invalid/p.git")
    before = snapshot(root)
    proc = adopt(root)
    assert proc.returncode == 1 and "default branch" in proc.stdout.lower()
    assert "git remote set-head origin --auto" in proc.stdout
    assert ".git/refs/remotes/origin/HEAD" in proc.stdout
    assert snapshot(root) == before


def test_ac1_test_detection_unittest_layout_and_topmost_dirs(tmp_path):
    """REQ-010 AC1: rule 9."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import adopt as adopt_mod

    root = tmp_path / "p"
    for rel in (
        "tests/test_a.py",
        "tests/unit/test_b.py",
        "pkg/tests/c_test.py",
        "node_modules/x/test_d.py",
        ".venv/lib/test_e.py",
        "tests/kit/test_kit.py",
        "src/app.py",
    ):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("")
    dirs, patterns = adopt_mod.detect_tests(root)
    assert dirs == ["pkg/tests", "tests"]
    assert patterns == ["*_test.py", "test_*.py"]
    rootlevel = tmp_path / "r"
    rootlevel.mkdir()
    (rootlevel / "test_root.py").write_text("")
    (rootlevel / "tests").mkdir()
    (rootlevel / "tests" / "test_a.py").write_text("")
    assert adopt_mod.detect_tests(rootlevel) == (["."], ["test_*.py"])
    empty = tmp_path / "e"
    empty.mkdir()
    assert adopt_mod.detect_tests(empty) == (["tests"], ["test_*.py"])


def test_ac1_marker_in_a_project_unittest_file_is_found(adopted):
    """REQ-010 AC1: rule 9, 18."""
    req = adopted / "docs" / "requirements.md"
    req.write_text(
        req.read_text() + "\n### REQ-101 — Project requirement\n\n- Status: done\n",
        encoding="utf-8",
    )
    run = lambda: subprocess.run(  # noqa: E731
        [sys.executable, "scripts/agk/check_requirements.py"],
        cwd=adopted,
        capture_output=True,
        text=True,
    )
    assert run().returncode == 1
    test_file = adopted / "pkg" / "tests" / "x_test.py"
    test_file.write_text(test_file.read_text() + "\n# REQ-101\n", encoding="utf-8")
    assert run().returncode == 0


def test_ac1_kit_tests_markers_are_not_project_markers_in_adopt_mode(adopted):
    """REQ-010 AC1: rule 9. tests/kit is excluded from the marker search unless listed."""
    (adopted / "agk.toml").write_text(
        (adopted / "agk.toml").read_text().replace('["pkg/tests"]', '["tests"]'), encoding="utf-8"
    )
    req = adopted / "docs" / "requirements.md"
    req.write_text(req.read_text().replace("- Status: planned", "- Status: done", 1))
    out = subprocess.run(
        [sys.executable, "scripts/agk/check_requirements.py"],
        cwd=adopted,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 1  # REQ-001 markers exist only in tests/kit, which is excluded


# --- Governance green, bare pytest (rule 18) ----------------------------------------------------


def test_ac1_governance_and_kit_tests_pass_in_the_adopted_target(adopted):
    """REQ-010 AC1: rule 18."""
    for target in ("agk-governance", "agk-test", "agk-project-test"):
        proc = subprocess.run(
            ["make", "-f", "agk.mk", target],
            cwd=adopted,
            capture_output=True,
            text=True,
            env=clean_env(),
        )
        assert proc.returncode == 0, target + proc.stdout[-1500:] + proc.stderr[-1500:]
        if target == "agk-project-test":
            assert "no project_tests configured" in proc.stdout


def test_ac1_bare_pytest_in_the_target_collects_the_project_test_and_no_kit_test(adopted):
    """REQ-010 AC1: rules 6 and 18."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "."],
        cwd=adopted,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert "pkg/tests/x_test.py::T::test_x" in proc.stdout
    assert "tests/kit/" not in proc.stdout


def test_ac1_adopted_protected_list_has_no_makefile_or_pyproject(adopted):
    """REQ-010 AC1: rule 12 (adopted mode)."""
    listed = [
        ln.strip()
        for ln in (adopted / "config" / "protected-paths.txt").read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    assert listed == ADOPTED_PROTECTED
    reviewers = (adopted / "config" / "reviewers.yaml").read_text()
    protected = re.search(r"protected:\s*\{paths: \[([^\]]*)\]", reviewers).group(1)
    assert [p.strip() for p in protected.split(",")] == ADOPTED_PROTECTED
    assert "Makefile" not in reviewers and "pyproject.toml" not in reviewers


def test_ac1_adopted_adr_is_neutral_proposed_and_names_every_class(adopted):
    """REQ-010 AC1: rule 13."""
    text = (adopted / "docs" / "adr" / "0001-adopt-agk.md").read_text(encoding="utf-8")
    assert "- Status: Proposed" in text
    for entry in ADOPTED_PROTECTED:
        assert entry in text, entry
    flat = " ".join(text.split())
    assert "master" in flat and "creation commit" not in flat
    assert "history before" in flat.lower() and "not governed" in flat.lower()
    assert "first governed change" in flat
    for existing_file in (".github/FUNDING.yml", ".github/workflows/ci.yml"):
        assert existing_file in text
    assert not re.findall(r"ADR-(?!0001)\d{4}", text)


# --- Idempotence, dry run, refusal (rules 14-16) ------------------------------------------------


def test_ac2_second_run_changes_nothing(adopted):
    """REQ-010 AC2: rule 14 (hashes and mtimes equal)."""
    before = snapshot(adopted)
    proc = adopt(adopted)
    assert proc.returncode == 0 and "nothing to do" in proc.stdout
    assert snapshot(adopted) == before


def test_ac2_partial_install_completes(adopted):
    """REQ-010 AC2: rule 14."""
    (adopted / "docs" / "build-state.md").unlink()
    before = snapshot(adopted)
    assert adopt(adopted).returncode == 0
    after = snapshot(adopted)
    assert "docs/build-state.md" in after
    for rel, value in before.items():
        assert after[rel] == value, rel


def test_ac2_dry_run_writes_nothing_and_prints_actions(existing):
    """REQ-010 AC2: rule 16."""
    before = snapshot(existing)
    proc = adopt(existing, "--dry-run")
    assert proc.returncode == 0 and snapshot(existing) == before
    lines = proc.stdout.splitlines()
    assert any(ln == "append .gitignore" for ln in lines)
    assert any(ln == "append .github/CODEOWNERS" for ln in lines)
    created = {ln.split(" ", 1)[1] for ln in lines if ln.startswith("create ")}
    assert created == adopt_files() - {".gitignore", ".github/CODEOWNERS"}
    (existing / "agk.mk").write_text("x:\n")
    dry = adopt(existing, "--dry-run")
    assert dry.returncode == 1
    assert any(ln.startswith("conflict agk.mk") for ln in dry.stdout.splitlines())


def test_ac2_dry_run_on_an_adopted_target_says_unchanged(adopted):
    """REQ-010 AC2: rule 16."""
    proc = adopt(adopted, "--dry-run")
    assert proc.returncode == 0
    assert "create " not in proc.stdout and "append " not in proc.stdout
    assert "unchanged .gitignore" in proc.stdout


@pytest.mark.parametrize(
    "files",
    [
        {"agk.mk": "other:\n"},
        {"scripts/agk/common.py": "# mine\n"},
        {".claude/settings.json": "{}\n"},
        {"config/reviewers.yaml": "version: 9\n"},
        {"docs/requirements.md": "# mine\n"},
        {".github/workflows/governance.yml": "name: mine\n"},
        {".gitignore": "*.pyc\n# >>> agk\nold content\n# <<< agk\n"},
        {".gitignore": "# >>> agk\n# >>> agk\n# <<< agk\n"},
        {".gitignore": "# <<< agk\n"},
        {".gitignore": "# >>> agk\nnever closed\n"},
        {"CLAUDE.md": "<!-- >>> agk -->\nstale\n<!-- <<< agk -->\n"},
    ],
)
def test_ac2_refusals_write_nothing_and_never_print_content(tmp_path, files):
    """REQ-010 AC2: rules 11, 15."""
    secret = {k: v + "SECRET_CONTENT_9\n" for k, v in files.items()}
    root = make_existing(tmp_path / "p", **secret)
    before = snapshot(root)
    proc = adopt(root)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1
    for rel in secret:
        assert rel in out, rel
    assert "SECRET_CONTENT_9" not in out
    assert snapshot(root) == before


def test_ac2_every_problem_is_listed_not_just_the_first(tmp_path):
    """REQ-010 AC2: rule 15."""
    root = make_existing(tmp_path / "p", **{"agk.mk": "a\n", "config/neutrality.txt": "b\n"})
    out = adopt(root).stdout
    assert "agk.mk" in out and "config/neutrality.txt" in out


def test_ac2_symlinked_path_refuses_and_writes_nothing(tmp_path):
    """REQ-010 AC2: rules 2 and 15."""
    root = make_existing(tmp_path / "p")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    os.symlink(elsewhere, root / ".claude")
    before = snapshot(root)
    proc = adopt(root)
    assert proc.returncode == 1 and ".claude/" in proc.stdout
    assert snapshot(root) == before and not any(elsewhere.rglob("*"))


# --- Init and adopt together (rule 17) ----------------------------------------------------------


def test_ac2_init_after_adopt_refuses_and_writes_nothing(adopted):
    """REQ-010 AC2: rule 17."""
    before = snapshot(adopted)
    proc = run_init(adopted)
    assert proc.returncode == 1 and "adopt" in proc.stdout
    assert snapshot(adopted) == before


def test_ac2_adopt_after_init_refuses_and_writes_nothing(tmp_path):
    """REQ-010 AC2: rule 17."""
    root = make_repo(tmp_path / "p")
    assert run_init(root).returncode == 0
    before = snapshot(root)
    proc = adopt(root)
    assert proc.returncode == 1 and "already installed by init" in proc.stdout
    assert snapshot(root) == before


def test_ac2_adopt_refuses_a_repository_with_a_tool_agk_table(tmp_path):
    """REQ-010 AC2: rule 17 (an install from before agk.toml)."""
    root = make_existing(
        tmp_path / "p", **{"pyproject.toml": PYPROJECT + '\n[tool.agk]\nversion = "0.1.0"\n'}
    )
    before = snapshot(root)
    proc = adopt(root)
    assert proc.returncode == 1 and "already installed by init" in proc.stdout
    assert snapshot(root) == before


def test_ac2_adopt_gains_no_option_for_the_default_branch(tmp_path):
    """REQ-010 AC2: the refusal names the fix; there is no new option (usage error)."""
    root = make_existing(tmp_path / "p")
    for flag in ("--set-head", "--default-branch=master", "--branch"):
        proc = subprocess.run(
            [sys.executable, str(ADOPT), str(root), flag],
            capture_output=True,
            text=True,
            env=clean_env(),
        )
        assert proc.returncode == 2, flag


def test_ac2_printed_branch_rules_in_adopt_say_default_branch(adopted):
    """REQ-010 AC2: the printed rule text names no branch called main."""
    out = " ".join(adopt(adopted, "--dry-run").stdout.split())
    assert "The ruleset for the default branch is exactly:" in out
    assert "ruleset `main`" not in out
