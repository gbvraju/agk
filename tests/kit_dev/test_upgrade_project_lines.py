"""Brief #269 (REQ-039, ADR-0164): a project's own `.gitignore` lines survive every upgrade.

The kit's `.gitignore` is a marked block; the lines outside it belong to the project. The fixture
kit mirrors the real one: its `.gitignore` is the block, the block's text is
`kit/templates/gitignore`, and `extendable` in the manifest names the file. Ignore lines are
invented.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, snapshot
from test_upgrade import (
    MARK_CLOSE,
    MARK_OPEN,
    NEW,
    OLD,
    adopt_target,
    init_target,
    lines_of,
    make_kit,
    put,
    run,
)

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import adopt  # noqa: E402
import upgrade  # noqa: E402

BLOCK_NEW = f"{MARK_OPEN}{NEW['.gitignore']}{MARK_CLOSE}"
BLOCK_OLD = f"{MARK_OPEN}{OLD['.gitignore']}{MARK_CLOSE}"


@pytest.fixture
def kit(tmp_path, monkeypatch):
    """The fixture kit of test_upgrade.py, as the upgrade's kit root."""
    root = make_kit(tmp_path)
    monkeypatch.setattr(upgrade, "KIT_ROOT", root)
    return root


@pytest.fixture
def ext_kit(kit):
    """The fixture kit with `.gitignore` extendable, as the real kit ships it."""
    manifest = json.loads((kit / "kit" / "manifest.json").read_text())
    manifest["extendable"] = {".gitignore": "hash"}
    manifest["adopt"]["block_sources"] = {".gitignore": "kit/templates/gitignore"}
    (kit / "kit" / "manifest.json").write_text(json.dumps(manifest))
    put(kit, {"kit/templates/gitignore": NEW[".gitignore"], ".gitignore": BLOCK_NEW})
    return kit


def line_for(out: list[str], rel: str) -> str:
    return next(ln for ln in out if ln.split(" (")[0].split(" ", 1)[-1] == rel)


# --- answer 3: an install without markers is migrated ---


def test_init_kit_lines_plus_project_lines_are_migrated(tmp_path, ext_kit, capsys):
    """REQ-039: brief #269 answer 3, the case of the pilot (one confidential folder added)."""
    target = init_target(tmp_path, **{".gitignore": OLD[".gitignore"] + "private-src/\n"})
    code, out = run(capsys, target)
    assert code == 0, out
    assert (target / ".gitignore").read_text() == BLOCK_NEW + "private-src/\n"
    assert line_for(out, ".gitignore") == (
        "replace .gitignore (agk block added; project lines kept: 1)"
    )


def test_init_untouched_file_gets_the_block(tmp_path, ext_kit, capsys):
    """REQ-039: brief #269 answer 3, no project line: the kit's file, with markers."""
    target = init_target(tmp_path)
    code, out = run(capsys, target)
    assert code == 0, out
    assert (target / ".gitignore").read_text() == BLOCK_NEW
    assert line_for(out, ".gitignore") == "replace .gitignore (agk block added)"


def test_init_any_other_difference_is_still_a_conflict(tmp_path, ext_kit, capsys):
    """REQ-039: brief #269 answer 3, a changed kit line, and project lines before the kit's."""
    for i, text in enumerate(
        [
            "*.pyo\nprivate-src/\n",
            "private-src/\n" + OLD[".gitignore"],
            "private-src/\n",
            "",
        ]
    ):
        target = init_target(tmp_path / str(i), **{".gitignore": text})
        before = snapshot(target)
        code, out = run(capsys, target)
        assert code == 1, (text, out)
        assert line_for(out, ".gitignore").startswith("conflict .gitignore (path class "), text
        assert "differs from every released copy" in line_for(out, ".gitignore"), text
        assert snapshot(target) == before


# --- answer 2: only the block is compared and replaced ---


def test_init_block_is_replaced_and_project_lines_kept_byte_for_byte(tmp_path, ext_kit, capsys):
    """REQ-039: brief #269 answers 1 and 2."""
    mine = "# my own\nprivate-src/\n"
    target = init_target(tmp_path, **{".gitignore": mine + BLOCK_OLD + "!keep.txt\n"})
    code, out = run(capsys, target)
    assert code == 0, out
    assert (target / ".gitignore").read_text() == mine + BLOCK_NEW + "!keep.txt\n"
    assert line_for(out, ".gitignore") == "replace .gitignore (project lines kept: 3)"


def test_init_second_run_reports_the_project_lines_once_and_writes_nothing(
    tmp_path, ext_kit, capsys
):
    """REQ-039: brief #269 answer 2 (reported once, never a conflict)."""
    target = init_target(tmp_path, **{".gitignore": OLD[".gitignore"] + "private-src/\n"})
    assert run(capsys, target)[0] == 0
    before = snapshot(target)
    code, out = run(capsys, target)
    assert code == 0 and out[-1] == "nothing to do", out
    assert snapshot(target) == before
    assert [ln for ln in out if "project lines kept" in ln] == [
        "unchanged .gitignore (project lines kept: 1)"
    ]


def test_init_edited_block_and_broken_markers_conflict(tmp_path, ext_kit, capsys):
    """REQ-039: brief #269 answer 2 (an edit inside the block is still the kit's line edited)."""
    for i, text in enumerate(
        [
            f"{MARK_OPEN}*.pyc\nprivate-src/\n{MARK_CLOSE}",
            f"{MARK_OPEN}{OLD['.gitignore']}",
            BLOCK_OLD * 2,
        ]
    ):
        target = init_target(tmp_path / str(i), **{".gitignore": text})
        before = snapshot(target)
        code, out = run(capsys, target)
        assert code == 1, (text, out)
        assert lines_of(out, "conflict") == [".gitignore"], text
        assert snapshot(target) == before


def test_init_absent_file_is_deleted_locally_and_a_new_one_is_the_block(tmp_path, ext_kit, capsys):
    """REQ-039: brief #269 answer 1 (a file the kit adds is created as the block)."""
    target = init_target(tmp_path)
    (target / ".gitignore").unlink()
    code, out = run(capsys, target)
    assert code == 0 and lines_of(out, "deleted-locally") == [".gitignore"], out
    assert not (target / ".gitignore").exists()
    table = json.loads((ext_kit / "kit" / "hashes.json").read_text())
    for row in table["releases"].values():
        row["verbatim"].pop(".gitignore", None)
        row["blocks"].pop(".gitignore", None)
    (ext_kit / "kit" / "hashes.json").write_text(json.dumps(table))
    code, out = run(capsys, target)
    assert code == 0 and lines_of(out, "create") == [".gitignore"], out
    assert (target / ".gitignore").read_text() == BLOCK_NEW


def test_init_without_the_extendable_key_is_compared_whole_as_before(tmp_path, kit, capsys):
    """REQ-039: brief #269 answer 4 (only a file the manifest names is extendable)."""
    target = init_target(tmp_path, **{".gitignore": OLD[".gitignore"] + "private-src/\n"})
    code, out = run(capsys, target)
    assert code == 1 and lines_of(out, "conflict") == [".gitignore"], out


# --- adopt targets ---


def test_adopt_block_with_project_lines_reports_them(tmp_path, ext_kit, capsys):
    """REQ-039: brief #269 answer 2 in an adopt install (the block was always marked there)."""
    target = adopt_target(tmp_path)
    code, out = run(capsys, target)
    assert code == 0, out
    assert (target / ".gitignore").read_text() == f"build/\n{BLOCK_NEW}tail\n"
    assert line_for(out, ".gitignore") == "replace .gitignore (project lines kept: 2)"


def test_adopt_file_without_markers_is_migrated_too(tmp_path, ext_kit, capsys):
    """REQ-039: brief #269 answer 3 in an adopt install whose markers are gone."""
    target = adopt_target(tmp_path, **{".gitignore": OLD[".gitignore"] + "private-src/\n"})
    code, out = run(capsys, target)
    assert code == 0, out
    assert (target / ".gitignore").read_text() == BLOCK_NEW + "private-src/\n"


# --- the real kit ---


def real_manifest() -> dict:
    return json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))


def test_the_kit_names_gitignore_as_its_only_extendable_file():
    """REQ-039: brief #269 answers 1 and 4 (ADR-0164 names `.gitignore` and no other file)."""
    manifest = real_manifest()
    assert manifest["extendable"] == {".gitignore": "hash"}
    assert manifest["adopt"]["block_sources"][".gitignore"] == "kit/templates/gitignore"
    for rel, style in manifest["extendable"].items():
        assert rel in manifest["verbatim"] and manifest["adopt"]["blocks"][rel] == style
        body = (KIT_ROOT / manifest["adopt"]["block_sources"][rel]).read_text(encoding="utf-8")
        assert adopt.find_block(body, style)[0] == "none", "the block's text has no markers"
        assert (KIT_ROOT / rel).read_text(encoding="utf-8") == adopt.block_of(style, body)


# The last release whose `.gitignore` is the bare template; every later release installs the marked
# block, so the test names this release and never takes the newest row of the table (brief #295).
BARE_GITIGNORE_RELEASE = "0.57.1"


def test_a_real_install_of_the_last_release_with_a_project_line_upgrades(tmp_path):
    """REQ-039: brief #269 answer 3 with the real table: the released bare file plus a line."""
    manifest = real_manifest()
    table = json.loads((KIT_ROOT / "kit" / "hashes.json").read_text(encoding="utf-8"))
    released = BARE_GITIGNORE_RELEASE
    assert released in table["releases"], "the release with the bare file is in the table"
    body = (KIT_ROOT / "kit/templates/gitignore").read_text(encoding="utf-8")
    assert (
        hashlib.sha256(body.encode()).hexdigest()
        in table["releases"][released]["verbatim"][".gitignore"]
    ), "the template is the released file's text"
    target = tmp_path / "t"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    (target / "agk.toml").write_text(f'mode = "init"\nversion = "{released}"\n')
    (target / ".gitignore").write_text(body + "private-src/\n")
    plan = upgrade.build_plan(target, KIT_ROOT)
    item = next(i for i in plan.items if i.rel == ".gitignore")
    assert item.action == "replace", item
    assert item.content.decode() == adopt.block_of("hash", body) + "private-src/\n"
    assert manifest["extendable"]
