"""Kit-only tests of scripts/agk/upgrade.py (SPEC-0008 rules 4-17, 18-21)."""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, make_repo, snapshot

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import kit_hashes  # noqa: E402
import upgrade  # noqa: E402

OLD = {
    "a.txt": "a\n",
    "b.txt": "b old\n",
    "c.txt": "c old\n",
    ".claude/e.txt": "e old\n",
    "scripts/agk/reviewers.py": "rev old\n",
    "skipme.txt": "skip old\n",
    "Makefile": "mk old\n",
    ".gitignore": "*.pyc\n",
    "CLAUDE.md": "# rules old\n",
}
NEW = {
    "a.txt": "a\n",
    "b.txt": "b new\n",
    "d.txt": "d new\n",
    ".claude/e.txt": "e new\n",
    "scripts/agk/reviewers.py": "rev new\n",
    "skipme.txt": "skip new\n",
    "Makefile": "mk new\n",
    ".gitignore": "*.pyc\n__pycache__/\n",
    "CLAUDE.md": "# rules new\n",
}
TEMPLATES_OLD = {
    "kit/templates/agk.toml": 'mode = "init"\nversion = "{{kit_version}}"\nbranch = "main"\n',
    "kit/templates/agk.adopt.toml": 'mode = "adopt"\nversion = "{{kit_version}}"\n',
    "kit/templates/protected-paths.txt": "config/\n.claude/\n",
    "kit/templates/reviewers.yaml": "teams: old\n",
    "kit/templates/adr.md": "adr old\n",
}
TEMPLATES_NEW = {
    **TEMPLATES_OLD,
    "kit/templates/agk.toml": TEMPLATES_OLD["kit/templates/agk.toml"] + "review_diff_cap = 4000\n",
    "kit/templates/protected-paths.txt": "config/\n.claude/\ndocs/requirements.md\n",
}
MARK_OPEN, MARK_CLOSE = "# >>> agk\n", "# <<< agk\n"
HTML_OPEN, HTML_CLOSE = "<!-- >>> agk -->\n", "<!-- <<< agk -->\n"
PROTECTED = "config/\n.claude/\nagk.toml\nb.txt\n"
AGK_TOML = '# my notes\nmode = "{mode}"\nversion = "1.0.0"\ninstalled = "2020-01-02"\nmine = 1\n'


def manifest_of(version: str, files: dict, templates: dict) -> dict:
    return {
        "kit_version": version,
        "verbatim": sorted(files),
        "templates": {
            "agk.toml": "kit/templates/agk.toml",
            "config/protected-paths.txt": "kit/templates/protected-paths.txt",
            "config/reviewers.yaml": "kit/templates/reviewers.yaml",
            "docs/adr/0001.md": "kit/templates/adr.md",
        },
        "rendered": [".github/CODEOWNERS"],
        "adopt": {
            "skip": ["Makefile", "skipme.txt"],
            "blocks": {".gitignore": "hash", "CLAUDE.md": "html", ".github/CODEOWNERS": "hash"},
            "templates": {
                "agk.toml": "kit/templates/agk.adopt.toml",
                "config/protected-paths.txt": "kit/templates/protected-paths.txt",
                "config/reviewers.yaml": "kit/templates/reviewers.yaml",
                "docs/adr/0001.md": "kit/templates/adr.md",
            },
        },
    }


def make_kit(tmp_path: Path) -> Path:
    """A kit at 2.0.0 whose table also knows 1.0.0 (an older kit, smaller than the real one)."""
    root = tmp_path / "kit_root"
    table = {"table": 1, "releases": {}}
    for version, files, templates in (("1.0.0", OLD, TEMPLATES_OLD), ("2.0.0", NEW, TEMPLATES_NEW)):
        manifest = manifest_of(version, files, templates)
        store = {**{k: v.encode() for k, v in files.items()}}
        store.update({k: v.encode() for k, v in templates.items()})
        snap = kit_hashes.snapshot_of(manifest, store.get)
        table["releases"][version] = {
            "commits": [],
            **{name: {p: [d] for p, d in snap[name].items()} for name in snap},
        }
        if version == "2.0.0":
            for rel, data in store.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(data)
            (root / "kit").mkdir(exist_ok=True)
            (root / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "kit" / "hashes.json").write_text(kit_hashes.dump(table), encoding="utf-8")
    return root


def put(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def init_target(tmp_path: Path, **over: str) -> Path:
    target = tmp_path / "target"
    target.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    put(target, {k: v for k, v in OLD.items()})
    put(
        target,
        {
            "agk.toml": AGK_TOML.format(mode="init"),
            "config/protected-paths.txt": PROTECTED,
            "config/reviewers.yaml": "teams: mine\n",
            "docs/adr/0001.md": "my adr\n",
            "src/app.py": "print(1)\n",
        },
    )
    put(target, over)
    return target


def adopt_target(tmp_path: Path, **over: str) -> Path:
    target = tmp_path / "target"
    target.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    whole = ("a.txt", "b.txt", "c.txt", ".claude/e.txt", "scripts/agk/reviewers.py")
    put(target, {k: OLD[k] for k in whole})
    put(
        target,
        {
            ".gitignore": f"build/\n{MARK_OPEN}{OLD['.gitignore']}{MARK_CLOSE}tail\n",
            "CLAUDE.md": f"# mine\n{HTML_OPEN}{OLD['CLAUDE.md']}{HTML_CLOSE}more\n",
            "Makefile": "the project's own\n",
            "skipme.txt": "the project's own\n",
            "agk.toml": AGK_TOML.format(mode="adopt"),
            "config/protected-paths.txt": PROTECTED,
            "config/reviewers.yaml": "teams: mine\n",
            "docs/adr/0001.md": "my adr\n",
        },
    )
    put(target, over)
    return target


@pytest.fixture
def kit(tmp_path, monkeypatch) -> Path:
    root = make_kit(tmp_path)
    monkeypatch.setattr(upgrade, "KIT_ROOT", root)
    return root


def run(capsys, target: Path, *args: str) -> tuple[int, list[str]]:
    code = upgrade.main([str(target), *args])
    return code, capsys.readouterr().out.splitlines()


def lines_of(out: list[str], action: str) -> list[str]:
    return [ln.split(" ", 1)[1].split(" (")[0] for ln in out if ln.startswith(action + " ")]


# --- the rows of rule 7 ---


def test_ac1_each_row_of_rule_7_for_an_init_target(tmp_path, kit, capsys):
    """REQ-014 AC5: rules 6, 7, 10, 11, 14."""
    target = init_target(tmp_path)
    (target / "a.txt").write_text("a\n")
    code, out = run(capsys, target)
    assert code == 0, out
    assert lines_of(out, "unchanged") == ["a.txt"]
    assert lines_of(out, "create") == ["d.txt"]
    assert lines_of(out, "replace") == [
        ".claude/e.txt",
        ".gitignore",
        "CLAUDE.md",
        "Makefile",
        "b.txt",
        "scripts/agk/reviewers.py",
        "skipme.txt",
    ]
    assert lines_of(out, "removed-in-kit") == ["c.txt"]
    assert (target / "c.txt").read_text() == OLD["c.txt"]  # never deleted
    for rel, text in NEW.items():
        assert (target / rel).read_text() == text, rel
    assert "upgraded 8 files; the version line of agk.toml is set to 2.0.0" in out


def test_ac1_a_file_deleted_locally_is_reported_and_not_recreated(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 7."""
    target = init_target(tmp_path)
    (target / ".claude" / "e.txt").unlink()
    code, out = run(capsys, target)
    assert code == 0
    assert lines_of(out, "deleted-locally") == [".claude/e.txt"]
    assert not (target / ".claude" / "e.txt").exists()


def test_ac1_a_new_file_in_the_kit_is_created_and_an_edited_one_stops_the_run(
    tmp_path, kit, capsys
):
    """REQ-014 AC5: rules 7 and 8 (every edited path is listed; nothing is written)."""
    target = init_target(tmp_path)
    put(target, {"b.txt": "my edit\n", "scripts/agk/reviewers.py": "my edit\n"})
    before = snapshot(target)
    code, out = run(capsys, target)
    assert code == 1
    assert lines_of(out, "conflict") == ["b.txt", "scripts/agk/reviewers.py"]
    assert any(ln.startswith("refused:") for ln in out) and any(ln.startswith("fix:") for ln in out)
    assert snapshot(target) == before, "a conflict writes nothing, not even the version line"
    assert not (target / "d.txt").exists()


def test_ac1_a_conflict_in_a_dry_run_has_the_same_exit_code(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 14."""
    target = init_target(tmp_path)
    put(target, {"b.txt": "my edit\n"})
    real = run(capsys, target)
    dry = run(capsys, target, "--dry-run")
    assert real == dry and real[0] == 1


# --- user-owned files and the version line ---


def test_ac1_user_owned_files_are_never_rewritten(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 9 (bytes and modification times)."""
    target = init_target(tmp_path)
    owned = [
        "config/protected-paths.txt",
        "config/reviewers.yaml",
        "docs/adr/0001.md",
        "src/app.py",
    ]
    for rel in owned:
        os.utime(target / rel, ns=(1_000_000_000, 1_000_000_000))
    before = snapshot(target)
    assert run(capsys, target)[0] == 0
    after = snapshot(target)
    for rel in owned:
        assert after[rel] == before[rel], rel


def test_ac1_only_the_version_line_of_agk_toml_changes(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 11."""
    target = init_target(tmp_path)
    before = (target / "agk.toml").read_text()
    assert run(capsys, target)[0] == 0
    after = (target / "agk.toml").read_text()
    assert after == before.replace('version = "1.0.0"', 'version = "2.0.0"')
    assert after != before


def test_ac1_template_changes_and_new_keys_are_printed_not_merged(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 10."""
    target = init_target(tmp_path)
    _, out = run(capsys, target)
    assert "template-changed agk.toml (kit/templates/agk.toml)" in out
    assert "template-changed config/protected-paths.txt (kit/templates/protected-paths.txt)" in out
    assert "template-key agk.toml review_diff_cap = 4000" in out
    assert "template-line config/protected-paths.txt docs/requirements.md" in out
    assert not any("reviewers.yaml" in ln or "adr.md" in ln for ln in out if "template" in ln)
    assert "review_diff_cap" not in (target / "agk.toml").read_text()
    assert "template-" not in "\n".join(run(capsys, target)[1])  # the second run: unchanged


def test_ac1_an_error_on_a_write_stops_the_run_and_leaves_the_version(
    tmp_path, kit, capsys, monkeypatch
):
    """REQ-014 AC5: rules 11 and 15 (exit 3; the version line is not written)."""
    target = init_target(tmp_path)
    real = upgrade.write_atomic

    def failing(path: Path, data: bytes) -> None:
        if path.name == "d.txt":
            raise OSError("disk")
        real(path, data)

    monkeypatch.setattr(upgrade, "write_atomic", failing)
    code, out = run(capsys, target)
    assert code == 3
    assert any(ln.startswith("error: cannot write d.txt") for ln in out)
    assert any(ln.startswith("already written: .claude/e.txt") for ln in out)
    assert 'version = "1.0.0"' in (target / "agk.toml").read_text()


def test_ac1_writes_are_in_sorted_order_and_the_version_line_is_last(tmp_path, kit, monkeypatch):
    """REQ-014 AC5: rule 15."""
    target = init_target(tmp_path)
    seen: list[str] = []
    real = upgrade.write_atomic

    def spy(path: Path, data: bytes) -> None:
        seen.append(path.relative_to(target).as_posix())
        real(path, data)

    monkeypatch.setattr(upgrade, "write_atomic", spy)
    assert upgrade.main([str(target)]) == 0
    assert seen[-1] == "agk.toml" and seen[:-1] == sorted(seen[:-1]) and len(seen) == 9


def test_ac1_the_same_version_with_current_files_is_nothing_to_do(tmp_path, kit, capsys):
    """REQ-014 AC5: rules 5, 14, 21 (no file is touched)."""
    target = init_target(tmp_path)
    put(target, {k: v for k, v in NEW.items()})
    put(target, {"agk.toml": AGK_TOML.format(mode="init").replace("1.0.0", "2.0.0")})
    before = snapshot(target)
    code, out = run(capsys, target)
    assert code == 0 and out[-1] == "nothing to do"
    assert snapshot(target) == before


def test_ac1_an_upgraded_target_is_upgraded_again_with_nothing_to_do(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 21."""
    target = init_target(tmp_path)
    assert run(capsys, target)[0] == 0
    before = snapshot(target)
    code, out = run(capsys, target)
    assert code == 0 and out[-1] == "nothing to do"
    assert snapshot(target) == before


def test_ac1_dry_run_prints_what_the_real_run_prints_and_writes_nothing(tmp_path, kit, capsys):
    """REQ-014 AC5: rules 14 and 20."""
    one = init_target(tmp_path / "one")
    two = init_target(tmp_path / "two")
    before = snapshot(one)
    dry_code, dry = run(capsys, one, "--dry-run")
    assert snapshot(one) == before and dry_code == 0
    code, real = run(capsys, two)
    assert code == 0

    def body(out: list[str]) -> list[str]:
        return [ln for ln in out if not ln.startswith(("dry run:", "upgraded "))]

    assert body(dry) == body(real)
    assert any(ln.startswith("dry run: 8 files would change") for ln in dry)
    assert run(capsys, one, "--dry-run")[1] == dry  # deterministic


def test_ac1_the_protected_classes_line_and_adr_skeleton_are_printed(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 16 (from the target's own list, only for the paths it would write)."""
    _, out = run(capsys, init_target(tmp_path))
    line = next(ln for ln in out if ln.startswith("Protected classes: "))
    assert set(re.findall(r"`([^`]+)`", line)) == {".claude/", "b.txt", "agk.toml"}
    assert "# ADR-NNNN: Upgrade agk from 1.0.0 to 2.0.0" in out and "- Status: Proposed" in out
    assert not list((tmp_path / "target" / "docs" / "adr").glob("*upgrade*"))  # it writes no ADR


def test_ac1_codeowners_command_is_printed_when_the_generator_is_written(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 12."""
    _, out = run(capsys, init_target(tmp_path))
    assert "run: python3 scripts/agk/reviewers.py --codeowners --write" in out


# --- adopt targets: whole files, skips and marked blocks ---


def test_ac1_adopt_replaces_inside_the_markers_only(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 13."""
    target = adopt_target(tmp_path)
    code, out = run(capsys, target)
    assert code == 0, out
    assert (
        target / ".gitignore"
    ).read_text() == f"build/\n{MARK_OPEN}{NEW['.gitignore']}{MARK_CLOSE}tail\n"
    assert (
        target / "CLAUDE.md"
    ).read_text() == f"# mine\n{HTML_OPEN}{NEW['CLAUDE.md']}{HTML_CLOSE}more\n"
    assert lines_of(out, "replace") == [
        ".claude/e.txt",
        ".gitignore",
        "CLAUDE.md",
        "b.txt",
        "scripts/agk/reviewers.py",
    ]
    assert lines_of(out, "create") == ["d.txt"]


def test_ac1_adopt_never_touches_skipped_files(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 6 (`Makefile` and `skipme.txt` are `adopt.skip`)."""
    target = adopt_target(tmp_path)
    _, out = run(capsys, target)
    assert (target / "Makefile").read_text() == "the project's own\n"
    assert (target / "skipme.txt").read_text() == "the project's own\n"
    assert not any(
        "Makefile" in ln or "skipme" in ln
        for ln in out
        if ln.split(" ")[0] in {"replace", "conflict", "create", "unchanged"}
    )


def test_ac1_adopt_edited_block_missing_markers_and_broken_markers_conflict(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 13."""
    for i, over in enumerate(
        [
            {".gitignore": f"{MARK_OPEN}*.pyc\nmine\n{MARK_CLOSE}"},
            {".gitignore": "*.pyc\n"},
            {".gitignore": f"{MARK_OPEN}*.pyc\n"},
            {"CLAUDE.md": f"{HTML_OPEN}{HTML_OPEN}{OLD['CLAUDE.md']}{HTML_CLOSE}"},
            {"CLAUDE.md": "# my own rules\n"},
        ]
    ):
        target = adopt_target(tmp_path / str(i), **over)
        before = snapshot(target)
        code, out = run(capsys, target)
        assert code == 1, over
        assert next(iter(over)) in " ".join(lines_of(out, "conflict")), over
        assert snapshot(target) == before


def test_ac1_adopt_created_whole_file_is_replaced_whole(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 13 (adopt writes CLAUDE.md without markers when the file did not exist)."""
    target = adopt_target(tmp_path, **{"CLAUDE.md": OLD["CLAUDE.md"]})
    code, out = run(capsys, target)
    assert code == 0, out
    assert (target / "CLAUDE.md").read_text() == NEW["CLAUDE.md"]


def test_ac1_adopt_creates_an_absent_block_file_with_markers(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 13 (a new block file in the kit; `.gitignore` is created as a block)."""
    target = adopt_target(tmp_path)
    (target / ".gitignore").unlink()
    manifest = json.loads((kit / "kit" / "manifest.json").read_text())
    table = json.loads((kit / "kit" / "hashes.json").read_text())
    table["releases"]["1.0.0"]["blocks"].pop(".gitignore")
    table["releases"]["1.0.0"]["verbatim"].pop(".gitignore")
    (kit / "kit" / "hashes.json").write_text(kit_hashes.dump(table))
    assert manifest["kit_version"] == "2.0.0"
    code, out = run(capsys, target)
    assert code == 0 and ".gitignore" in lines_of(out, "create")
    assert (target / ".gitignore").read_text() == f"{MARK_OPEN}{NEW['.gitignore']}{MARK_CLOSE}"


def test_ac1_adopt_second_run_changes_nothing(tmp_path, kit, capsys):
    """REQ-014 AC5: rules 13 and 21."""
    target = adopt_target(tmp_path)
    assert run(capsys, target)[0] == 0
    before = snapshot(target)
    code, out = run(capsys, target)
    assert code == 0 and out[-1] == "nothing to do" and snapshot(target) == before


# --- refusals ---


@pytest.mark.parametrize(
    ("over", "needle"),
    [
        ({"agk.toml": 'mode = "init"\nversion = "1.5.0"\n'}, "kit/hashes.json"),
        ({"agk.toml": 'mode = "init"\nversion = "3.0.0"\n'}, "newer than this kit"),
        ({"agk.toml": 'mode = "init"\n'}, "no version"),
        ({"agk.toml": 'mode = "other"\nversion = "1.0.0"\n'}, "not init or adopt"),
        ({"agk.toml": "mode = \n"}, "not readable TOML"),
    ],
)
def test_ac1_refusals_of_rule_5_write_nothing(tmp_path, kit, capsys, over, needle):
    """REQ-014 AC5: rule 5."""
    target = init_target(tmp_path, **over)
    before = snapshot(target)
    code, out = run(capsys, target)
    assert code == 1 and out[0].startswith("refused: ") and needle in out[0]
    assert snapshot(target) == before


def test_ac1_an_install_without_agk_toml_is_refused(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 5 (kit 0.1.0 and 0.2.0 stamp `[tool.agk]` in pyproject.toml only)."""
    target = init_target(tmp_path)
    (target / "agk.toml").unlink()
    code, out = run(capsys, target)
    assert code == 1 and "agk.toml is missing (path class agk.toml)" in out[0]


def test_ac1_a_symlinked_path_to_write_is_refused(tmp_path, kit, capsys):
    """REQ-014 AC5: rule 5."""
    target = init_target(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "e.txt").write_text(OLD[".claude/e.txt"])
    for child in (target / ".claude").iterdir():
        child.unlink()
    (target / ".claude").rmdir()
    (target / ".claude").symlink_to(elsewhere)
    code, out = run(capsys, target)
    assert (
        code == 1
        and "symlink" in out[0]
        and (elsewhere / "e.txt").read_text() == OLD[".claude/e.txt"]
    )


def test_ac1_target_must_be_a_git_work_tree_a_directory_and_not_the_kit(tmp_path, kit, capsys):
    """REQ-014 AC5: rules 4 and 5."""
    target = init_target(tmp_path)
    subprocess.run(["rm", "-rf", str(target / ".git")], check=True)
    assert run(capsys, target)[0] == 1
    assert run(capsys, tmp_path / "missing")[0] == 1
    assert run(capsys, kit)[0] == 1
    assert run(capsys, kit / "kit")[0] == 1


@pytest.mark.parametrize("args", [[], ["a", "b"], ["--bogus"], ["--dry-run"]])
def test_ac1_usage_errors_exit_2(kit, args):
    """REQ-014 AC5: rule 4."""
    assert upgrade.main(args) == 2


# --- the real history: every kit version that wrote agk.toml upgrades to this kit ---


def real_versions() -> list[str]:
    rows = json.loads((KIT_ROOT / "kit" / "hashes.json").read_text(encoding="utf-8"))["releases"]
    return [
        v
        for v in rows
        if v != json.loads((KIT_ROOT / "kit" / "manifest.json").read_text())["kit_version"]
    ]


def checkout(commit: str, dest: Path) -> Path:
    data = subprocess.run(
        ["git", "archive", "--format=tar", commit], cwd=KIT_ROOT, capture_output=True, check=True
    ).stdout
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, filter="data")
    return dest


def old_install(tmp_path: Path, version: str, mode: str) -> Path | None:
    rows = json.loads((KIT_ROOT / "kit" / "hashes.json").read_text(encoding="utf-8"))["releases"]
    old = checkout(rows[version]["commits"][0], tmp_path / "old_kit")
    script = old / "scripts" / "agk" / f"{mode}.py"
    if not script.is_file():
        return None
    target = make_repo(tmp_path / "target")
    proc = subprocess.run(
        [sys.executable, str(script), str(target)], capture_output=True, text=True, env=clean_env()
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return target


def upgrade_cli(target: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "upgrade.py"), str(target), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


@pytest.mark.parametrize("mode", ["init", "adopt"])
@pytest.mark.parametrize("version", [v for v in real_versions() if v not in ("0.1.0", "0.2.0")])
def test_ac1_a_real_old_install_upgrades_with_no_conflict(tmp_path, version, mode):
    """REQ-014 AC5: rules 7, 13 and 21 against the real kit and the real table."""
    target = old_install(tmp_path, version, mode)
    if target is None:
        pytest.skip(f"kit {version} has no {mode}")
    proc = upgrade_cli(target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not [ln for ln in proc.stdout.splitlines() if ln.startswith("conflict ")]
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    whole, blocks = upgrade.installed_set(manifest, mode)
    for rel in whole:
        assert (target / rel).read_bytes() == (KIT_ROOT / rel).read_bytes(), rel
    for rel, style in blocks.items():
        _, begin, end, lines = upgrade.locate((target / rel).read_text(encoding="utf-8"), style)
        body = (KIT_ROOT / rel).read_text(encoding="utf-8").rstrip("\n") + "\n"
        text = (target / rel).read_text(encoding="utf-8")
        assert "".join(lines[begin + 1 : end]) == body or text == body, rel
    assert f'version = "{manifest["kit_version"]}"' in (target / "agk.toml").read_text()
    again = upgrade_cli(target)
    assert again.returncode == 0 and again.stdout.splitlines()[-1] == "nothing to do"


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0"])
def test_ac1_an_install_stamped_only_in_pyproject_is_refused(tmp_path, version):
    """REQ-014 AC5: rule 5 (the gap recorded in docs/runs/proposed-spec-amendments-12.md)."""
    target = old_install(tmp_path, version, "init")
    assert target is not None and not (target / "agk.toml").exists()
    proc = upgrade_cli(target)
    assert proc.returncode == 1 and proc.stdout.startswith("refused: agk.toml is missing")
