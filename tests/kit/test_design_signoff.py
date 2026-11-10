"""Tests of the frozen signed-off version (SPEC-0037 rules 9 and 12; REQ-044 AC5, brief #459).

`design_signoff.frozen_problems(root)` compares each `design` row of `docs/design/signoffs.md` with
`version_digest` of its folder and fails `rule 9: docs/design/prototype/<version>: a signed-off
version changed`, naming the version and never a digest; `screenshots/` stays outside.
`check_design.py` calls it, and a theme whose evidence line names a prototype version reads
approved only with a `design` row of a matching digest (rule 12). No check writes a file.
Invented data only, in `tmp_path`; files only, no network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_design  # noqa: E402
import design_signoff as ds  # noqa: E402

V1 = "docs/design/prototype/v1"
HEAD = "0123456789abcdef0123456789abcdef01234567"
LINK = "https://example.com/acme/books/pull/12#issuecomment-345"
CHANGED = "rule 9: docs/design/prototype/v1: a signed-off version changed"
THEME = "# Theme\n\n## Brand\n\n## Evidence\n\nEvidence: docs/design/prototype/v1/\n"


def signed(root: Path, digest: str | None = None) -> Path:
    """An invented version v1 and its `design` row with the digest of the folder as it is."""
    folder = root / V1
    (folder / "screenshots").mkdir(parents=True)
    (folder / "index.html").write_text("<!doctype html><title>Books</title>\n", encoding="utf-8")
    (folder / "books--default.html").write_text("<h1>Books</h1>\n", encoding="utf-8")
    (folder / "screenshots" / "reflow.json").write_text("{}\n", encoding="utf-8")
    value = digest or ds.version_digest(root, "v1")
    (root / ds.SIGNOFFS).write_text(
        "# Design sign-offs\n\n| kind | version | digest | head | date | comment |\n"
        f"|---|---|---|---|---|---|\n| design | v1 | {value} | {HEAD} | 2026-11-10 | {LINK} |\n",
        encoding="utf-8",
    )
    return folder


def listing(root: Path) -> dict[str, tuple[int, int]]:
    return {
        p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
    }


def test_ac5_a_frozen_version_passes(tmp_path):
    """REQ-044 AC5: a version whose folder still has the signed-off digest has no problem."""
    signed(tmp_path)
    assert ds.frozen_problems(tmp_path) == []


def test_ac5_a_changed_file_fails_naming_the_version_never_the_digest(tmp_path):
    """REQ-044 AC5: a change in place fails naming rule 9 and the version."""
    folder = signed(tmp_path)
    before = ds.version_digest(tmp_path, "v1")
    (folder / "books--default.html").write_text("<h1>Books, changed</h1>\n", encoding="utf-8")
    after = ds.version_digest(tmp_path, "v1")
    problems = ds.frozen_problems(tmp_path)
    assert problems == [CHANGED]
    assert before not in problems[0] and after not in problems[0]


def test_ac5_an_added_file_fails(tmp_path):
    """REQ-044 AC5: an addition counts as a change."""
    folder = signed(tmp_path)
    (folder / "books--empty.html").write_text("<h1>No books</h1>\n", encoding="utf-8")
    assert ds.frozen_problems(tmp_path) == [CHANGED]


def test_ac5_a_removed_file_fails(tmp_path):
    """REQ-044 AC5: a removal counts as a change."""
    folder = signed(tmp_path)
    (folder / "books--default.html").unlink()
    assert ds.frozen_problems(tmp_path) == [CHANGED]


def test_ac5_a_removed_folder_fails(tmp_path):
    """REQ-044 AC5: a signed-off folder that is gone has changed too."""
    folder = signed(tmp_path)
    for path in sorted(folder.rglob("*"), reverse=True):
        path.unlink() if path.is_file() else path.rmdir()
    folder.rmdir()
    assert ds.frozen_problems(tmp_path) == [CHANGED]


def test_ac5_a_change_under_screenshots_passes(tmp_path):
    """REQ-044 AC5: `screenshots/` stays outside what the person signs off."""
    folder = signed(tmp_path)
    (folder / "screenshots" / "reflow.json").write_text('{"v1": []}\n', encoding="utf-8")
    (folder / "screenshots" / "home--default-360-light.png").write_bytes(b"\x89PNG one")
    assert ds.frozen_problems(tmp_path) == []


def test_ac5_no_record_and_inventory_rows_have_no_problem(tmp_path):
    """REQ-044 AC5: only `design` rows freeze a folder; no record freezes nothing."""
    assert ds.frozen_problems(tmp_path) == []
    (tmp_path / "docs" / "design").mkdir(parents=True)
    (tmp_path / ds.SIGNOFFS).write_text(
        "| kind | version | digest | head | date | comment |\n|---|---|---|---|---|---|\n"
        f"| inventory | - | {'c' * 64} | {HEAD} | 2026-11-10 | {LINK} |\n",
        encoding="utf-8",
    )
    assert ds.frozen_problems(tmp_path) == []


def test_ac5_check_design_fails_a_changed_signed_off_version(tmp_path):
    """REQ-044 AC5: `check_design.py` calls `frozen_problems` and prints its line."""
    folder = signed(tmp_path)
    (folder / "index.html").write_text("<!doctype html><title>Other</title>\n", encoding="utf-8")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT_ROOT / "scripts/agk/check_design.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        env={**os.environ},
        check=False,
    )
    assert proc.returncode == 1
    assert f"FAIL design: {CHANGED}" in proc.stdout


def test_ac5_the_evidence_line_reads_approved_with_a_matching_row(tmp_path):
    """REQ-044 AC5 (rule 12): a prototype version with a row of its digest reads approved."""
    signed(tmp_path)
    assert check_design.theme_problems(tmp_path, THEME)[3] is True


def test_ac5_the_evidence_line_reads_not_approved_yet_without_a_matching_row(tmp_path):
    """REQ-044 AC5 (rule 12): no row, or a row of another digest, reads not approved yet."""
    signed(tmp_path, digest="d" * 64)
    assert check_design.theme_problems(tmp_path, THEME)[3] is False
    (tmp_path / ds.SIGNOFFS).unlink()
    assert check_design.theme_problems(tmp_path, THEME)[3] is False


def test_ac5_no_check_writes_a_file(tmp_path):
    """REQ-044 AC5: sizes and times of every path are unchanged after every check."""
    folder = signed(tmp_path)
    (tmp_path / check_design.THEME).write_text(THEME, encoding="utf-8")
    (folder / "books--default.html").write_text("<h1>Changed</h1>\n", encoding="utf-8")
    before = listing(tmp_path)
    ds.frozen_problems(tmp_path)
    ds.rows(tmp_path)
    check_design.theme_problems(tmp_path, THEME)
    subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT_ROOT / "scripts/agk/check_design.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert listing(tmp_path) == before
