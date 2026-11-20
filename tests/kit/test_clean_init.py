"""`init --layout plugin` and `adopt --layout plugin` start a project in the clean layout, with no
kit file in its first commit (brief #1603, SPEC-0071 rule 2 as amendment 211 proposes, ADR-0683;
REQ-078 AC1 and AC3).

Both write only the files the migration of rule 8 keeps: the project's records and settings that
the kit renders, the short `CLAUDE.md`, `agk.toml` with `execution = "local"` and the `[kit]`
table, `LICENSE-AGK`, `.gitignore` and the `.github/` templates; no kit script, hook, agent,
workflow or guide. Both refuse, naming the setting or the proof, in personal mode, with another
`execution`, and until the rehearsal's proof is held (rule 11) unless `--rehearsal`. Temporary
folders and the kit checkout only; no network; invented data only (example.com)."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - a fixed `git init`, no shell
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import adopt  # noqa: E402
import doctor  # noqa: E402
import init  # noqa: E402
import upgrade  # noqa: E402

MANIFEST = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
VERSION = str(MANIFEST["kit_version"])
KIT_FILES = {*MANIFEST["verbatim"], *MANIFEST.get("experimental", [])}


def kept(rel: str) -> bool:
    return rel in doctor.CLEAN_KEEPS or rel.startswith(doctor.CLEAN_KEEPS_UNDER)


def repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)  # nosec B603 B607
    return path


def written(root: Path) -> set[str]:
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


def test_req078_ac1_init_layout_plugin_writes_only_rule_2_files(tmp_path, capsys):
    target = repo(tmp_path / "shop-example")
    assert init.main([str(target), "--unreleased", "--layout", "plugin", "--rehearsal"]) == 0
    files = written(target)
    assert not [rel for rel in files & KIT_FILES if not kept(rel)]
    assert not any(rel.startswith(("scripts/agk/", ".claude/", ".github/workflows/")) for rel in files)
    for rel in ("LICENSE-AGK", ".gitignore", ".github/PULL_REQUEST_TEMPLATE.md", "agk.toml"):
        assert rel in files
    for rel in ("docs/requirements.md", "docs/build-state.md", "config/reviewers.yaml"):
        assert rel in files  # the project's own records stay, as the migration keeps them
    claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "AGK clean layout" in claude and len(claude.splitlines()) <= 30
    data = tomllib.loads((target / "agk.toml").read_text(encoding="utf-8"))
    assert data["kit"] == {"layout": "plugin", "plugin_version": VERSION}
    assert data["execution"] == "local"
    assert doctor.kit_in_repository_lines(target, ROOT) == []
    assert "layout: plugin" in capsys.readouterr().out


def test_req078_ac1_a_second_clean_init_changes_nothing(tmp_path, capsys):
    target = repo(tmp_path / "shop-example")
    args = [str(target), "--unreleased", "--layout", "plugin", "--rehearsal"]
    assert init.main(args) == 0
    capsys.readouterr()
    assert init.main(args) == 0
    assert "nothing to do" in capsys.readouterr().out


def test_req078_ac3_adopt_layout_plugin_writes_no_manifest_kit_file(tmp_path):
    target = repo(tmp_path / "app-example")
    (target / "src").mkdir()
    (target / "src" / "app.py").write_text("print('example.com')\n", encoding="utf-8")
    (target / "CLAUDE.md").write_text("# The product's own notes\n", encoding="utf-8")
    assert adopt.main([str(target), "--unreleased", "--layout", "plugin", "--rehearsal"]) == 0
    files = written(target)
    assert not [rel for rel in files & KIT_FILES if not kept(rel)]
    assert "LICENSE-AGK" in files and "docs/requirements.md" in files
    claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude.startswith("# The product's own notes\n") and "AGK clean layout" in claude
    data = tomllib.loads((target / "agk.toml").read_text(encoding="utf-8"))
    assert data["kit"] == {"layout": "plugin", "plugin_version": VERSION}
    assert data["execution"] == "local"
    assert doctor.kit_in_repository_lines(target, ROOT) == []


def test_req078_ac3_without_the_layout_init_and_adopt_install_as_today(tmp_path):
    target = repo(tmp_path / "shop-example")
    assert init.main([str(target), "--unreleased", "--dry-run"]) == 0
    items, _entries, _branch = init.build_items(target, "2026-11-20")
    assert "scripts/agk/doctor.py" in dict(items)
    assert "kit" not in tomllib.loads(dict(items)["agk.toml"].decode("utf-8"))


@pytest.mark.parametrize("tool", [init, adopt])
def test_req078_ac3_both_refuse_without_the_proof_naming_it(tool, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(init, "proof_held", lambda _root: False)
    target = repo(tmp_path / "shop-example")
    assert tool.main([str(target), "--unreleased", "--layout", "plugin"]) == 1
    out = capsys.readouterr().out
    assert "refused:" in out and "rule 11" in out and "--rehearsal" in out
    assert written(target) == set()


@pytest.mark.parametrize("tool", [init, adopt])
def test_req078_ac3_with_the_proof_held_no_rehearsal_flag_is_needed(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(init, "proof_held", lambda _root: True)
    target = repo(tmp_path / "shop-example")
    assert tool.main([str(target), "--unreleased", "--layout", "plugin"]) == 0
    assert doctor.clean_layout(target)


@pytest.mark.parametrize("tool", [init, adopt])
@pytest.mark.parametrize(
    ("toml", "setting"),
    [
        ('execution = "hosted"\n', "setting: execution"),
        ('[personal]\nforge = "files"\n', "setting: forge"),
    ],
)
def test_req078_ac3_both_refuse_hosted_and_personal_naming_the_setting(
    tool, toml, setting, tmp_path, capsys
):
    target = repo(tmp_path / "shop-example")
    (target / "agk.toml").write_text(toml, encoding="utf-8")
    assert tool.main([str(target), "--unreleased", "--layout", "plugin", "--rehearsal"]) == 1
    out = capsys.readouterr().out
    assert "refused: " in out and setting in out
    assert '"hosted"' not in out and '"files"' not in out  # the setting, never its value
    assert written(target) == {"agk.toml"}


@pytest.mark.parametrize("tool", [init, adopt])
@pytest.mark.parametrize(
    "args", [["--layout"], ["--layout", "installed"], ["--rehearsal"]]
)
def test_req078_ac3_a_bad_layout_flag_is_a_usage_error(tool, args, tmp_path):
    target = repo(tmp_path / "shop-example")
    assert tool.main([str(target), "--unreleased", *args]) == 2
    assert written(target) == set()


def test_req078_ac1_init_keeps_the_same_files_as_the_migration():
    assert set(init.CLEAN_KEPT) == set(upgrade.CLEAN_KEPT)
    assert {r for r in init.CLEAN_KEPT if not r.endswith("/")} - {"agk.toml"} == set(
        doctor.CLEAN_KEEPS
    )
