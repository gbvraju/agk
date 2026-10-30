"""A project's own make targets live in `project.mk` (brief #390, ADR-0214, REQ-038).

Answer 1: the kit's `Makefile` includes `project.mk` after `agk.mk` when it exists, and the kit
never installs, lists, hashes or writes that file. Answer 2: an upgrade refused over an edited
`Makefile` says to move the project's own targets to `project.mk`, naming the file and never its
content.
Answer 4: a CRLF copy of a released `Makefile` is read as LF and is not refused.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import pytest
import upgrade

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
PROJECT_MK = "project.mk"
INCLUDE = "-include project.mk"
# The 0.60.0 Makefile: the released copy an older project holds.
OLD_MAKEFILE = (
    "PY ?= python3\n\ninclude agk.mk\n\n.PHONY: governance test lint traceability\n\n"
    "governance: agk-governance\n\nlint: agk-lint\n\ntraceability: agk-traceability\n\n"
    "# Kit tests, then the project's own tests (agk.toml project_tests).\n"
    "test: agk-test agk-project-test\n"
)
# A stand-in for agk.mk: the four kit targets, each printing its name.
STUB_AGK_MK = "".join(
    f".PHONY: {t}\n{t}:\n\t@echo {t}\n"
    for t in ("agk-governance", "agk-lint", "agk-test", "agk-project-test", "agk-traceability")
)
PROJECT_TARGET = "PROJECT_SECRET_TARGET_LINE"
PROJECT_MK_TEXT = f".PHONY: hello\nhello:\n\t@echo project-hello\n# {PROJECT_TARGET}\n"
NEEDS_MAKE = pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")


def make(cwd: Path, *targets: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "--no-print-directory", "-f", "Makefile", *targets],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def project(tmp_path: Path, with_project_mk: bool) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    shutil.copyfile(MAKEFILE, root / "Makefile")
    (root / "agk.mk").write_text(STUB_AGK_MK, encoding="utf-8")
    if with_project_mk:
        (root / PROJECT_MK).write_text(PROJECT_MK_TEXT, encoding="utf-8")
    return root


# --- answer 1: the Makefile template ------------------------------------------------------------


def test_the_makefile_includes_project_mk_right_after_agk_mk():
    lines = MAKEFILE.read_text(encoding="utf-8").splitlines()
    assert lines.count("include agk.mk") == 1
    assert lines.count(INCLUDE) == 1
    assert lines.index(INCLUDE) == lines.index("include agk.mk") + 1


@NEEDS_MAKE
def test_the_makefile_works_when_project_mk_is_absent(tmp_path):
    root = project(tmp_path, with_project_mk=False)
    proc = make(root, "governance", "lint", "test")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["agk-governance", "agk-lint", "agk-test", "agk-project-test"]
    assert not (root / PROJECT_MK).exists()


@NEEDS_MAKE
def test_a_target_in_project_mk_is_run_by_make_beside_the_kit_targets(tmp_path):
    root = project(tmp_path, with_project_mk=True)
    proc = make(root, "hello", "governance")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["project-hello", "agk-governance"]


def test_the_kit_never_installs_lists_or_hashes_project_mk():
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert PROJECT_MK not in json.dumps(manifest)
    assert f'"{PROJECT_MK}"' not in (ROOT / "kit" / "hashes.json").read_text(encoding="utf-8")
    assert not (ROOT / PROJECT_MK).exists()


# --- answers 1, 2 and 4: an upgrade -------------------------------------------------------------


def digest(text: bytes) -> str:
    return hashlib.sha256(text).hexdigest()


def tiny_kit(tmp_path: Path) -> Path:
    """A kit at 2.0.0 that ships today's Makefile, whose table knows the 0.60.0 copy at 1.0.0."""
    kit = tmp_path / "kit_root"
    (kit / "kit").mkdir(parents=True)
    shutil.copyfile(MAKEFILE, kit / "Makefile")
    manifest = {
        "kit_version": "2.0.0",
        "verbatim": ["Makefile"],
        "templates": {},
        "rendered": [],
        "adopt": {"skip": ["Makefile"], "blocks": {}, "templates": {}},
    }
    (kit / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    new = upgrade.lf(MAKEFILE.read_bytes())
    row = {"commits": [], "verbatim": {}, "blocks": {}, "templates": {}}
    table = {
        "table": 1,
        "releases": {
            "1.0.0": {**row, "verbatim": {"Makefile": [digest(OLD_MAKEFILE.encode())]}},
            "2.0.0": {**row, "verbatim": {"Makefile": [digest(new)]}},
        },
    }
    (kit / "kit" / "hashes.json").write_text(json.dumps(table), encoding="utf-8")
    (kit / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n", encoding="utf-8")
    return kit


def init_target(tmp_path: Path, makefile: bytes) -> Path:
    target = tmp_path / "target"
    target.mkdir()
    git = ["git", "init", "-q", str(target)]
    subprocess.run(git, check=True)  # nosec B603 - fixed argument list, no shell
    (target / "agk.toml").write_text('mode = "init"\nversion = "1.0.0"\n', encoding="utf-8")
    (target / "Makefile").write_bytes(makefile)
    (target / PROJECT_MK).write_text(PROJECT_MK_TEXT, encoding="utf-8")
    return target


@pytest.fixture
def kit(tmp_path, monkeypatch) -> Path:
    root = tiny_kit(tmp_path)
    monkeypatch.setattr(upgrade, "KIT_ROOT", root)
    return root


def run(capsys, target: Path, *args: str) -> tuple[int, str]:
    code = upgrade.main([str(target), *args])
    return code, capsys.readouterr().out


def test_project_mk_survives_an_upgrade_untouched_and_the_makefile_is_replaced(
    tmp_path, kit, capsys
):
    target = init_target(tmp_path, OLD_MAKEFILE.encode())
    before = (target / PROJECT_MK).read_bytes(), (target / PROJECT_MK).stat().st_mtime_ns
    code, out = run(capsys, target)
    assert code == 0, out
    assert "replace Makefile" in out.splitlines()
    assert PROJECT_MK not in out
    assert (target / "Makefile").read_bytes() == MAKEFILE.read_bytes()
    assert ((target / PROJECT_MK).read_bytes(), (target / PROJECT_MK).stat().st_mtime_ns) == before
    code, out = run(capsys, target)
    assert (code, out.splitlines()[-1]) == (0, "nothing to do")


@NEEDS_MAKE
def test_after_the_upgrade_make_still_runs_the_project_target(tmp_path, kit, capsys):
    target = init_target(tmp_path, OLD_MAKEFILE.encode())
    assert run(capsys, target)[0] == 0
    (target / "agk.mk").write_text(STUB_AGK_MK, encoding="utf-8")
    proc = make(target, "hello")
    assert (proc.returncode, proc.stdout.split()) == (0, ["project-hello"]), proc.stderr


@pytest.mark.parametrize("dry_run", [False, True])
def test_a_refusal_over_an_edited_makefile_names_project_mk_and_writes_nothing(
    tmp_path, kit, capsys, dry_run
):
    edited = OLD_MAKEFILE + f"\nmine:\n\t@echo {PROJECT_TARGET}\n"
    target = init_target(tmp_path, edited.encode())
    code, out = run(capsys, target, *(["--dry-run"] if dry_run else []))
    assert code == 1
    assert "conflict Makefile" in out
    assert "refused: edited vendored files differ from every released copy" in out
    hint = [ln for ln in out.splitlines() if PROJECT_MK in ln]
    assert len(hint) == 1 and "Makefile" in hint[0] and "run again" in hint[0]
    assert PROJECT_TARGET not in out  # the message names the file, never its content
    assert (target / "Makefile").read_text(encoding="utf-8") == edited
    assert 'version = "1.0.0"' in (target / "agk.toml").read_text(encoding="utf-8")


def test_a_conflict_on_another_file_does_not_mention_project_mk():
    plan = upgrade.Plan("1.0.0", "2.0.0", "init")
    plan.items = [upgrade.Item("CLAUDE.md", "conflict", " (differs)")]
    assert not any(PROJECT_MK in ln for ln in upgrade.report(plan, False))
    plan.items = [upgrade.Item("Makefile", "conflict", " (differs)")]
    assert sum(PROJECT_MK in ln for ln in upgrade.report(plan, False)) == 1


def test_a_crlf_makefile_equal_to_a_released_copy_is_not_refused(tmp_path, kit, capsys):
    crlf = OLD_MAKEFILE.replace("\n", "\r\n").encode()
    target = init_target(tmp_path, crlf)
    code, out = run(capsys, target)
    assert code == 0, out
    assert "conflict" not in out and "refused" not in out
    assert "replace Makefile" in out.splitlines()


def test_a_crlf_copy_of_the_current_makefile_is_unchanged(tmp_path, kit, capsys):
    current = MAKEFILE.read_text(encoding="utf-8").replace("\n", "\r\n").encode()
    target = init_target(tmp_path, current)
    (target / "agk.toml").write_text('mode = "init"\nversion = "2.0.0"\n', encoding="utf-8")
    code, out = run(capsys, target)
    assert code == 0, out
    assert "unchanged Makefile" in out.splitlines()
