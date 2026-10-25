"""Kit-only tests of the bump rule in flow mode (SPEC-0028 rules 2, 3 and 6; REQ-035).

In flow mode a change to an installed path needs a line under `## Unreleased` of `CHANGELOG.md`
instead of a version bump; in strict mode the bump is required as before. No network, no model.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import KIT_ROOT, clean_env, git
from test_kit_hashes import current_row_problems, fake_kit, kit_hashes, write_kit

CHANGELOG = "# Changelog\n\n## Unreleased\n\n## 1.0.0 (2026-01-01)\n\n- #1 the start\n"


def settle(root: Path, message: str) -> None:
    """Regenerate the table and commit everything, as a merged pull request leaves the tree."""
    (root / "kit" / "hashes.json").write_text(
        kit_hashes.dump(kit_hashes.build_table(root, "HEAD")), encoding="utf-8"
    )
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def flow_kit(tmp_path: Path, mode: str = "flow") -> Path:
    root = fake_kit(tmp_path)
    (root / "agk.toml").write_text(f'version = "1.0.0"\npr_mode = "{mode}"\n', encoding="utf-8")
    (root / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    settle(root, "flow and the changelog")
    return root


def add_line(root: Path, line: str = "- #7 the a.txt change") -> None:
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    (root / "CHANGELOG.md").write_text(
        text.replace("## Unreleased\n", f"## Unreleased\n\n{line}\n", 1), encoding="utf-8"
    )


def refresh(root: Path) -> None:
    (root / "kit" / "hashes.json").write_text(
        kit_hashes.dump(kit_hashes.build_table(root, "HEAD")), encoding="utf-8"
    )


def test_ac1_a_flow_change_with_a_fragment_and_no_other_shared_file_passes(tmp_path):
    """REQ-035 AC1: rule 2 as amended by SPEC-0031 (a fragment replaces the Unreleased line)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed in flow\n", encoding="utf-8")
    (root / "changelog.d").mkdir()
    (root / "changelog.d" / "the-build.md").write_text("- the a.txt change\n", encoding="utf-8")
    assert kit_hashes.problems(root, "HEAD") == []


def test_ac2_a_flow_change_without_a_fragment_fails_naming_the_rule_and_the_class(tmp_path):
    """REQ-035 AC2: rule 2 as amended by SPEC-0031 (no silent change)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed silently\n", encoding="utf-8")
    found = kit_hashes.problems(root, "HEAD")
    assert any("flow mode" in f and "changelog.d/" in f and "a.txt" in f for f in found), found
    assert not any("kit_version bump" in f for f in found)


def test_ac2_a_change_to_nothing_the_installer_writes_needs_no_line(tmp_path):
    """REQ-035 AC2: rule 2 (only an installed path counts)."""
    root = flow_kit(tmp_path)
    (root / "notes.md").write_text("not installed\n", encoding="utf-8")
    assert kit_hashes.problems(root, "HEAD") == []


def test_ac3_in_strict_mode_the_bump_is_required_and_a_line_does_not_help(tmp_path):
    """REQ-035 AC3: rule 3 (exactly the rule before this spec)."""
    root = flow_kit(tmp_path, mode="strict")
    (root / "a.txt").write_text("a changed in strict\n", encoding="utf-8")
    add_line(root)
    refresh(root)
    found = kit_hashes.problems(root, "HEAD")
    assert any("needs a kit_version bump" in f for f in found), found
    assert not any("Unreleased" in f for f in found)


def test_ac3_in_strict_mode_a_bump_needs_no_changelog_line(tmp_path):
    """REQ-035 AC3: rule 3."""
    root = flow_kit(tmp_path, mode="strict")
    write_kit(root, "1.1.0", "a changed and bumped\n")
    (root / "agk.toml").write_text('version = "1.1.0"\npr_mode = "strict"\n', encoding="utf-8")
    refresh(root)
    assert kit_hashes.problems(root, "HEAD") == []


def test_ac1_a_bumping_change_in_flow_mode_is_left_to_the_release_check(tmp_path):
    """REQ-035 AC1: rule 4 (a raised version is a release pull request, not a build)."""
    root = flow_kit(tmp_path)
    write_kit(root, "1.1.0", "a changed and bumped\n")
    refresh(root)
    assert kit_hashes.problems(root, "HEAD") == []


def test_ac6_after_two_builds_the_release_regenerates_the_table(tmp_path):
    """REQ-035 AC6: rule 6 as amended by SPEC-0031 (the release writes the table)."""
    root = flow_kit(tmp_path)
    for n, word in ((7, "first"), (8, "second")):
        (root / "a.txt").write_text(f"a by the {word} build\n", encoding="utf-8")
        (root / "changelog.d").mkdir(exist_ok=True)
        (root / "changelog.d" / f"{word}.md").write_text(f"- the {word} build\n", encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", f"{word} build (#{n})")
    assert kit_hashes.problems(root, "HEAD") == []
    import subprocess
    import sys

    done = subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "kit_hashes.py"), "--write"],
        cwd=root,
        capture_output=True,
        text=True,
        env=clean_env(),  # AGK_BASE (set in CI) names no commit of this temporary repository
    )
    assert done.returncode == 0 and done.stdout == "wrote kit/hashes.json\n", done.stdout
    rows = json.loads((root / "kit" / "hashes.json").read_text(encoding="utf-8"))["releases"]
    # ADR-0134: the builds after the release of 1.0.0 do not widen its row; the next release's
    # row holds them
    assert len(rows["1.0.0"]["verbatim"]["a.txt"]) == 1


def test_adr_0108_in_flow_mode_the_current_row_is_not_compared_while_the_version_is_unchanged(
    tmp_path,
):
    """REQ-038: ADR-0108 decision 4 (the release regenerates the row; a build leaves it)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed in a build\n", encoding="utf-8")
    assert current_row_problems(root, "HEAD") == []


def test_adr_0108_in_strict_mode_the_current_row_is_compared_as_before(tmp_path):
    """REQ-038: ADR-0108 decision 4 (strict mode refreshes the table in each build)."""
    root = flow_kit(tmp_path, mode="strict")
    (root / "a.txt").write_text("a changed in strict\n", encoding="utf-8")
    assert current_row_problems(root, "HEAD") != []
    refresh(root)
    assert current_row_problems(root, "HEAD") == []


def test_adr_0108_a_release_compares_the_current_row_with_the_tree(tmp_path):
    """REQ-038: ADR-0108 decision 4 (a raised version is a release; its row must be regenerated)."""
    root = flow_kit(tmp_path)
    write_kit(root, "1.1.0", "a changed and bumped\n")
    assert current_row_problems(root, "HEAD") != []
    refresh(root)
    assert current_row_problems(root, "HEAD") == []
