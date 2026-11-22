"""`/agk:upgrade --clean-repo` moves an installed local-mode project to the clean layout in one
reversible pull request (brief #1456, SPEC-0071 rule 8, build (d), ADR-0614; REQ-078 AC3).

The migration of an installed sample removes the released kit files, writes the short `CLAUDE.md`
and the `[kit]` table, lists and keeps a changed kit file, fails naming the path class when a
remaining tracked file names a removed path, is undone by reverting its one commit, and refuses
with `execution = "hosted"`, in personal mode (`forge = "files"`), without `--rehearsal` while the
rehearsal's proof is not written, and when the project's version has no row of `kit/hashes.json`,
each naming the setting or the path class. A stub plugin root with its own
`.claude-plugin/plugin.json`, saved git trees in temporary folders and no network; invented data
only (example.com)."""

from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import tomllib
from pathlib import Path

import check_adrs
import pytest
import upgrade

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = "kit/templates/clean-claude.md"
SETTINGS = {
    "permissions": {
        "allow": ["Read", "Bash(python3 scripts/agk/*)"],
        "deny": ["Bash(gh pr merge:*)"],
    },
    "hooks": {},
}
KIT = {
    "scripts/agk/check_x.py": "print('x')\n",
    "scripts/agk/helper.py": "print('h')\n",
    ".claude/hooks/guard_x.py": "print('g')\n",
    ".claude/settings.json": json.dumps(SETTINGS) + "\n",
    ".github/workflows/governance.yml": "name: governance\n",
    ".github/PULL_REQUEST_TEMPLATE.md": "Advances:\n",
    ".github/ISSUE_TEMPLATE/problem.md": "a problem\n",
    ".gitignore": "__pycache__/\n.claude/settings.local.json\n",
    "CLAUDE.md": "# rules\nRead constitution/principles.md first.\n",
    "LICENSE-AGK": "The licence of example.com's kit.\n",
    "constitution/principles.md": "# Principles\n",
    "Makefile": "include agk.mk\n",
    "agk.mk": "agk-governance:\n\ttrue\n",
    "docs/specs/TEMPLATE.md": "# SPEC-NNNN: Title\n",
}
PROJECT = {
    "README.md": "A sample product of example.com.\n",
    "src/app.py": "print(1)\n",
    "docs/adr/0001-mine.md": "# ADR-0001: mine\n",
    "docs/index.md": "The specs live in docs/specs/, which the project keeps.\n",
    "config/protected-paths.txt": "config/\nagk.toml\n",
}
LOCAL = 'mode = "init"\nversion = "2.0.0"\nexecution = "local"\n'


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - local git, fixed list
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def kit(tmp_path, monkeypatch) -> Path:
    """A stub plugin at 2.0.0 with its own `.claude-plugin/plugin.json`; its table knows 1.0.0."""
    root = tmp_path / "plugin-example"
    for rel, text in {**KIT, TEMPLATE: (ROOT / TEMPLATE).read_text(encoding="utf-8")}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "plugin.json").write_text('{"name": "agk", "version": "2.0.0"}\n')
    manifest = {
        "kit_version": "2.0.0",
        "kit_tests": "tests/kit",
        "verbatim": sorted(KIT),
        "experimental": [],
        "templates": {},
        "rendered": [],
        "adopt": {"skip": [], "blocks": {}, "templates": {}},
    }
    (root / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    row = {"commits": [], "blocks": {}, "templates": {}}
    old = {**KIT, "scripts/agk/check_x.py": "print('old x')\n"}
    table = {
        "table": 1,
        "releases": {
            "1.0.0": {**row, "verbatim": {p: [digest(t)] for p, t in old.items()}},
            "2.0.0": {**row, "verbatim": {p: [digest(t)] for p, t in KIT.items()}},
        },
    }
    (root / "kit" / "hashes.json").write_text(json.dumps(table), encoding="utf-8")
    monkeypatch.setattr(upgrade, "KIT_ROOT", root)
    return root


def sample(tmp_path: Path, toml: str = LOCAL, over: dict[str, str] | None = None) -> Path:
    """An installed local-mode sample at 2.0.0, committed, so its work tree is clean."""
    root = tmp_path / "product-example"
    files = {**KIT, **PROJECT, "agk.toml": toml, **(over or {})}
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "member-example-1@example.com")
    git(root, "config", "user.name", "member-example-1")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "installed")
    return root


def run(capsys, root: Path, *args: str) -> tuple[int, str]:
    code = upgrade.main([str(root), "--clean-repo", *args])
    return code, capsys.readouterr().out


def test_the_migration_removes_the_kit_writes_the_clean_files_and_reverts(tmp_path, kit, capsys):
    root = sample(tmp_path)
    head = git(root, "rev-parse", "HEAD").strip()
    code, out = run(capsys, root, "--rehearsal", "--write")
    assert code == 0, out
    for rel in (
        "scripts/agk/check_x.py",
        ".claude/settings.json",
        ".github/workflows/governance.yml",
        "Makefile",
        "agk.mk",
        "constitution/principles.md",
        "docs/specs/TEMPLATE.md",
    ):
        assert not (root / rel).exists(), rel
    for rel in (
        ".gitignore",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/problem.md",
        "README.md",
        "src/app.py",
        "docs/adr/0001-mine.md",
    ):
        assert (root / rel).is_file(), rel
    claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
    assert (
        len(claude.splitlines()) <= 30 and "${CLAUDE_PLUGIN_ROOT}" in claude and "2.0.0" in claude
    )
    data = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    assert data["kit"] == {"layout": "plugin", "plugin_version": "2.0.0"}
    assert data["version"] == "2.0.0"
    local = json.loads((root / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    assert f"Bash(python3 {kit.as_posix()}/scripts/agk/*)" in local["permissions"]["allow"]
    assert "Bash(gh pr merge:*)" in local["permissions"]["deny"]
    assert "settings.local.json" not in git(root, "status", "--porcelain")  # never committed
    adr = next((root / "docs" / "adr").glob("0002-*.md"))
    text = adr.read_text(encoding="utf-8")
    assert check_adrs.validate(adr.name, text, {"0001"}) == []
    assert "- Status: Proposed" in text.splitlines()
    assert git(root, "branch", "--show-current").strip() == upgrade.CLEAN_BRANCH
    assert git(root, "rev-parse", "HEAD").strip() == head  # nothing committed
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "clean layout")
    git(root, "revert", "--no-edit", "HEAD")
    assert git(root, "diff", head, "HEAD", "--stat") == ""  # reverting its one commit undoes it


# SPEC-0071 rule 2: the files a clean project keeps (brief #1419 for the licence, Q-S0071-5).
RULE_2_KEPT = (
    ".gitignore",
    "CLAUDE.md",
    "LICENSE-AGK",
    ".github/ISSUE_TEMPLATE/",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "agk.toml",
)


def test_the_plan_never_deletes_the_licence(tmp_path, kit, capsys):
    root = sample(tmp_path)
    code, out = run(capsys, root, "--rehearsal", "--write")
    assert code == 0, out
    assert (root / "LICENSE-AGK").read_text(encoding="utf-8") == KIT["LICENSE-AGK"]
    assert not [ln for ln in out.splitlines() if "LICENSE-AGK" in ln and "delete" in ln], out
    assert "LICENSE-AGK" not in git(root, "status", "--porcelain")


def test_the_kept_files_are_one_list_and_rule_2s():
    assert upgrade.CLEAN_KEPT == RULE_2_KEPT
    assert set(upgrade.CLEAN_KEEPS) == set(RULE_2_KEPT) - {"CLAUDE.md"}  # rewritten short
    spec = next((ROOT / "docs" / "specs").glob("0071-*.md")).read_text(encoding="utf-8")
    rule = next(ln for ln in spec.splitlines() if "**In the repository:**" in ln)
    for rel in (".gitignore", "CLAUDE.md", "LICENSE-AGK", "agk.toml"):
        assert rel in rule, rel
    assert "the issue and pull request templates under `.github/`" in rule


def test_a_changed_kit_file_is_listed_and_kept(tmp_path, kit, capsys):
    root = sample(tmp_path, over={"scripts/agk/helper.py": "print('mine')\n"})
    code, out = run(capsys, root, "--rehearsal", "--write")
    assert code == 0, out
    assert any(ln.startswith("changed scripts/agk/helper.py") for ln in out.splitlines())
    assert "name each kept file in the pull request body: scripts/agk/helper.py" in out
    assert (root / "scripts" / "agk" / "helper.py").read_text() == "print('mine')\n"
    assert not (root / "scripts" / "agk" / "check_x.py").exists()


def test_a_remaining_file_that_names_a_removed_path_fails_and_writes_nothing(tmp_path, kit, capsys):
    root = sample(
        tmp_path, over={"README.md": "Run scripts/agk/check_x.py, then make governance.\n"}
    )
    code, out = run(capsys, root, "--rehearsal", "--write")
    assert code == 1, out
    assert "names a removed kit path: README.md:1 (path class (repository root))" in out
    assert out.splitlines()[-1].startswith("refused: 1 tracked files name a removed kit path")
    assert (root / "scripts" / "agk" / "check_x.py").is_file()
    assert git(root, "branch", "--show-current").strip() == "main"
    assert git(root, "status", "--porcelain") == ""


def test_a_protected_setting_naming_a_removed_folder_names_its_class(tmp_path, kit, capsys):
    root = sample(tmp_path, over={"config/settings-example.txt": "config/\nscripts/agk/\n"})
    code, out = run(capsys, root, "--rehearsal")
    assert code == 1 and "config/settings-example.txt:2 (path class config/)" in out


def test_the_protected_list_keeps_its_removed_paths_and_is_excepted(tmp_path, kit, capsys):
    """Q-1684-3 (brief #1684, ADR-0701): a removed path stays protected, so the list keeps it."""
    listed = "config/\nagk.toml\nscripts/agk/\n"
    root = sample(tmp_path, over={"config/protected-paths.txt": listed})
    code, out = run(capsys, root, "--rehearsal", "--write")
    assert code == 0 and "proof: no tracked file names a removed kit path" in out
    assert (root / "config" / "protected-paths.txt").read_text(encoding="utf-8") == listed


def test_a_plugin_path_is_not_a_removed_path(tmp_path, kit, capsys):
    root = sample(
        tmp_path,
        over={"README.md": 'Run python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_x.py".\n'},
    )
    code, out = run(capsys, root, "--rehearsal")
    assert code == 0, out
    assert "proof: no tracked file names a removed kit path" in out
    assert "nothing was written" in out and git(root, "status", "--porcelain") == ""


@pytest.mark.parametrize(
    ("toml", "args", "named"),
    [
        (
            'mode = "init"\nversion = "2.0.0"\nexecution = "hosted"\n',
            ["--rehearsal"],
            "(setting: execution)",
        ),
        ('mode = "init"\nversion = "2.0.0"\n', ["--rehearsal"], "(setting: execution)"),
        (LOCAL + '\n[personal]\nforge = "files"\n', ["--rehearsal"], "(setting: forge)"),
        (LOCAL, [], "SPEC-0071 rule 11"),
        (LOCAL.replace("2.0.0", "1.5.0"), ["--rehearsal"], "(path class kit/hashes.json)"),
        (LOCAL.replace("2.0.0", "1.0.0"), ["--rehearsal"], "(setting: version)"),
        (LOCAL + '\n[kit]\nlayout = "installed"\n', ["--rehearsal"], "(setting: layout)"),
    ],
)
def test_each_refusal_names_the_setting_and_writes_nothing(
    tmp_path, kit, capsys, toml, args, named
):
    root = sample(tmp_path, toml)
    code, out = run(capsys, root, *args, "--write")
    assert code == 1 and out.startswith("refused: ") and named in out, out
    assert "hosted" not in out and 'files"' not in out and "1.5.0" not in out
    assert git(root, "status", "--porcelain") == "" and (root / "Makefile").is_file()


def test_an_installed_sample_upgrades_as_today(tmp_path, kit, capsys):
    root = sample(tmp_path)
    assert upgrade.main([str(root), "--dry-run"]) == 0
    assert "--clean-repo" not in capsys.readouterr().out
    assert git(root, "status", "--porcelain") == ""


def test_the_skill_and_the_usage_name_the_clean_repo_form():
    skill = (ROOT / "skills" / "upgrade" / "SKILL.md").read_text(encoding="utf-8")
    assert 'upgrade.py" . --clean-repo' in skill and "--rehearsal" in skill
    assert "--clean-repo" in upgrade.USAGE
