"""Kit-only tests of the `Left in your files:` section of scripts/agk/uninstall.py (brief #1443,
ADR-0604; REQ-009): the lines of the project's own files that still name a removed kit path.

The sample projects are the fixture installs of test_uninstall.py, under the test's temporary
folder only; invented data, no network.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import test_uninstall
from conftest import snapshot
from test_uninstall import REVIEWERS, commit, init_target, run

kit = test_uninstall.kit  # the fixture kit, used by every test below
pytestmark = pytest.mark.usefixtures("kit")

# The probe's case (answer 6): 2 settings lines, 6 record lines, and lines that must not count.
MINE = {
    "config/reviewers.yaml": REVIEWERS + "# kit paths: scripts/agk/ and .claude/\n",
    "docs/adr/0002-mine.md": (
        "# ADR-0002: mine\n"
        "We run make governance from the Makefile.\n"
        "It includes agk.mk.\n"
        "Checks live in scripts/agk/check_x.py.\n"
        "Our own scripts/agkx/ tool and myMakefile.old stay.\n"
    ),
    "docs/adr/0003-upgrade.md": "Upgraded ./scripts/agk/ to 2.0.0\nsee .claude/hooks/h.py\n",
    "docs/runs/flakes.md": "python3 scripts/agk/flakes.py --list\n",
    "src/app.py": "print('src/scripts/agk/ is not a kit path')\n",
}
SECTION = [
    "Left in your files: 8 lines name removed kit paths",
    "tidy by hand:",
    "config/reviewers.yaml:3: protected: {paths: [config/, agk.toml], approvers: [maintainers]}",
    "config/reviewers.yaml:6: # kit paths: scripts/agk/ and .claude/",
    "records, keep as written:",
    "docs/adr/0002-mine.md:2: We run make governance from the Makefile.",
    "docs/adr/0002-mine.md:3: It includes agk.mk.",
    "docs/adr/0002-mine.md:4: Checks live in scripts/agk/check_x.py.",
    "docs/adr/0003-upgrade.md:1: Upgraded ./scripts/agk/ to 2.0.0",
    "docs/adr/0003-upgrade.md:2: see .claude/hooks/h.py",
    "docs/runs/flakes.md:1: python3 scripts/agk/flakes.py --list",
]


def section(out: list[str]) -> list[str]:
    starts = [i for i, ln in enumerate(out) if ln.startswith("Left in your files:")]
    assert len(starts) == 1, out
    found = out[starts[0] :]
    end = next(
        (i for i, ln in enumerate(found) if ln.startswith("kept: the project's own work")),
        len(found),
    )
    return found[:end]


def test_the_probes_case_lists_settings_then_records(tmp_path, capsys):
    """REQ-009: brief #1443 answers 1, 2 and 4 (two groups; whole path segments only)."""
    target = init_target(tmp_path, **MINE)
    code, out = run(capsys, target)
    assert code == 0, out
    assert section(out) == SECTION
    assert out.index(SECTION[0]) > max(i for i, ln in enumerate(out) if ln.startswith("delete "))


def test_a_dry_run_and_a_write_run_give_the_same_section_and_edit_none(tmp_path, capsys):
    """REQ-009: brief #1443 answers 3 and 6 (the same section; the lines stay as written)."""
    target = init_target(tmp_path, **MINE)
    dry = section(run(capsys, target)[1])
    code, out = run(capsys, target, "--write")
    assert code == 0, out
    assert section(out) == dry == SECTION
    for rel, text in MINE.items():
        assert (target / rel).read_text(encoding="utf-8") == text


def test_a_pause_prints_no_such_section(tmp_path, capsys):
    """REQ-009: brief #1443 answer 6 (`--pause` removes nothing)."""
    target = init_target(tmp_path, **MINE)
    for args in (("--pause",), ("--pause", "--write")):
        code, out = run(capsys, target, *args)
        assert code == 0, out
        assert not any(ln.startswith("Left in your files") for ln in out), out


def test_more_than_forty_lines_end_with_how_many_more(tmp_path, capsys):
    """REQ-009: brief #1443 answer 1 (at most 40 lines, then `and <k> more`)."""
    many = "".join(f"step {n}: include agk.mk\n" for n in range(1, 46))
    target = init_target(tmp_path, **{"docs/runs/log.md": many})
    found = section(run(capsys, target)[1])
    assert found[0] == "Left in your files: 45 lines name removed kit paths"
    shown = [ln for ln in found if ln.startswith("docs/runs/log.md:")]
    assert len(shown) == 40 and shown[-1] == "docs/runs/log.md:40: step 40: include agk.mk"
    assert found[-1] == "and 5 more"


def test_a_binary_and_a_large_file_are_skipped_and_counted(tmp_path, capsys):
    """REQ-009: brief #1443 answer 4 (binary and over 1 MB skipped, counted on one line)."""
    target = init_target(tmp_path)
    (target / "docs" / "logo.png").write_bytes(b"\x89PNG\0\0 agk.mk\n")
    (target / "docs" / "big.md").write_text("agk.mk\n" + "x" * (1024 * 1024), encoding="utf-8")
    commit(target)
    found = section(run(capsys, target)[1])
    assert found == ["Left in your files: none", "skipped: 2 binary, large or unreadable files"]


def test_a_project_with_no_leftover_lines_says_none(tmp_path, capsys):
    """REQ-009: brief #1443 answer 5 (`Left in your files: none`)."""
    target = init_target(tmp_path)
    before = snapshot(target)
    found = section(run(capsys, target)[1])
    assert found == ["Left in your files: none"]
    assert snapshot(target) == before


def test_the_removed_kit_files_and_git_are_never_searched(tmp_path, capsys):
    """REQ-009: brief #1443 answer 4 (the kit's removed files and `.git/` are not searched)."""
    target = init_target(tmp_path)
    assert (target / "agk.mk").is_file()  # names Makefile targets, and is removed
    (target / ".git" / "agk-note").write_text("agk.mk\n", encoding="utf-8")
    found = section(run(capsys, target)[1])
    assert found == ["Left in your files: none"]
    assert Path(target / ".git" / "agk-note").is_file()


def test_settings_come_before_other_files_to_tidy(tmp_path, capsys):
    """REQ-009: brief #1443 answer 2 (settings first under `tidy by hand:`, other files after)."""
    target = init_target(tmp_path, **{"README.md": "Run make -f agk.mk\n", **MINE})
    found = section(run(capsys, target)[1])
    assert found[2].startswith("config/reviewers.yaml:3:")
    assert found[4] == "README.md:1: Run make -f agk.mk" and found[5] == "records, keep as written:"


def test_an_unreadable_file_is_skipped_and_counted(tmp_path, capsys, monkeypatch):
    """REQ-009: brief #1443 answer 4 (verdict 6953292089 item 1: a file the account cannot read
    is counted as skipped and the report goes on)."""
    target = init_target(tmp_path, **MINE)
    locked = target / "build" / "theirs.md"
    locked.parent.mkdir()
    locked.write_text("agk.mk\n", encoding="utf-8")
    locked.chmod(0)
    if os.geteuid() == 0:  # root reads it anyway: make the read fail as it would for a person
        real = Path.read_bytes

        def read_bytes(self: Path) -> bytes:
            if self == locked:
                raise PermissionError(13, "Permission denied")
            return real(self)

        monkeypatch.setattr(Path, "read_bytes", read_bytes)
    try:
        code, out = run(capsys, target)
    finally:
        locked.chmod(0o644)
    assert code == 0, out
    found = section(out)
    assert found[:-1] == SECTION and found[-1] == "skipped: 1 binary, large or unreadable files"
