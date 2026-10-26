"""Install and upgrade on Windows: line endings (brief #263 build c, item 7; ADR-0160).

Git for Windows checks text out with CRLF (`core.autocrlf=true`), and the plugin cache on Windows
is unpacked with CRLF too. The kit's copies and its release rows are LF. So an untouched kit file
read as edited, the upgrade refused, and a kit copied from a CRLF cache matched no release row.
Comparisons now ignore the difference between CRLF and LF, and the kit writes its files with LF.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT
from test_upgrade import NEW, OLD, init_target, make_kit, run

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import init  # noqa: E402
import upgrade  # noqa: E402


@pytest.fixture
def kit(tmp_path, monkeypatch) -> Path:
    """The kit at 2.0.0 of test_upgrade, whose table also knows 1.0.0."""
    root = make_kit(tmp_path)
    monkeypatch.setattr(upgrade, "KIT_ROOT", root)
    return root


def crlf(root: Path, rels) -> None:
    for rel in rels:
        path = root / rel
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))


def test_a_windows_checkout_of_the_old_copies_upgrades_and_is_not_an_edit(tmp_path, kit, capsys):
    """Brief #263 item 7 (REQ-039): every kit file checked out with CRLF upgrades as untouched."""
    target = init_target(tmp_path)
    crlf(target, OLD)
    code, out = run(capsys, target)
    assert code == 0, out
    assert not [ln for ln in out if ln.startswith("conflict ")], out
    for rel, text in NEW.items():
        assert (target / rel).read_bytes() == text.encode(), rel  # written with LF


def test_a_windows_checkout_of_the_current_copy_is_unchanged(tmp_path, kit, capsys):
    """Brief #263 item 7 (REQ-039): a CRLF copy of the current file is not an edit either."""
    target = init_target(tmp_path, **{"b.txt": NEW["b.txt"]})
    crlf(target, ["b.txt"])
    code, out = run(capsys, target, "--dry-run")
    assert code == 0, out
    assert "unchanged b.txt" in out


def test_an_unmodified_removed_file_checked_out_with_crlf_is_deleted(tmp_path, kit, capsys):
    """Brief #263 item 7 (REQ-039): a file the new kit no longer ships, untouched but CRLF."""
    target = init_target(tmp_path)
    crlf(target, ["c.txt"])
    code, out = run(capsys, target)
    assert code == 0, out
    assert "removed-in-kit c.txt (unmodified, deleted)" in out


def test_a_real_edit_is_still_a_conflict_whatever_its_line_endings(tmp_path, kit, capsys):
    """Brief #263 item 7: only the line endings are ignored, never a changed line."""
    target = init_target(tmp_path, **{"b.txt": "b mine\n"})
    crlf(target, ["b.txt"])
    code, out = run(capsys, target)
    assert code == 1
    assert any(ln.startswith("conflict b.txt") for ln in out), out


def test_a_kit_unpacked_with_crlf_writes_lf_copies(tmp_path, kit, capsys):
    """Brief #263 item 7 (REQ-039): the plugin cache on Windows has CRLF; the copies are LF, so
    their digests match the release row."""
    crlf(kit, NEW)
    target = init_target(tmp_path)
    code, out = run(capsys, target)
    assert code == 0, out
    for rel, text in NEW.items():
        assert (target / rel).read_bytes() == text.encode(), rel


def test_init_from_a_crlf_kit_writes_lf_and_a_crlf_target_copy_is_unchanged(tmp_path, monkeypatch):
    """Brief #263 item 7 (REQ-039): init reads the kit's files as LF and ignores CRLF."""
    items, _, _ = init.build_items(tmp_path, "2026-10-26")
    rel, content = next((r, c) for r, c in items if r.startswith("scripts/agk/"))
    root = tmp_path / "crlf_kit"
    for part in ("kit/manifest.json", rel):
        (root / part).parent.mkdir(parents=True, exist_ok=True)
    (root / "kit" / "manifest.json").write_bytes((KIT_ROOT / "kit/manifest.json").read_bytes())
    (root / rel).write_bytes(content.replace(b"\n", b"\r\n"))
    assert init.kit_bytes(root / rel) == content
    target = tmp_path / "target"
    (target / rel).parent.mkdir(parents=True)
    (target / rel).write_bytes(content.replace(b"\n", b"\r\n"))
    plan = init.classify(target, [(rel, content)], [])
    assert plan[0][1] == "unchanged"


@pytest.mark.parametrize("data", [b"a\r\nb\r\n", b"a\nb\n", b"a\r\nb\n"])
def test_lf_turns_crlf_into_lf_and_leaves_binary_alone(data):
    """Brief #263 item 7: one rule for every comparison and every write; a file with a NUL byte
    is binary and kept as it is."""
    import common

    assert common.lf(data) == b"a\nb\n"
    assert common.lf(b"\x00\r\n") == b"\x00\r\n"
    assert upgrade.lf is common.lf and init.lf is common.lf
