"""Kit-only tests of the bump rule in flow mode (SPEC-0028 rules 2, 3 and 6; REQ-035).

In flow mode a change to an installed path needs a line under `## Unreleased` of `CHANGELOG.md`
instead of a version bump; in strict mode the bump is required as before. No network, no model.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import KIT_ROOT, clean_env, git
from test_kit_hashes import fake_kit, kit_hashes, write_kit

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


def test_ac1_a_flow_change_with_a_changelog_line_and_refreshed_hashes_passes(tmp_path):
    """REQ-035 AC1: rule 2 (no bump; the row of the current version lists both digests)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed in flow\n", encoding="utf-8")
    add_line(root)
    refresh(root)
    assert kit_hashes.problems(root, "HEAD") == []
    rows = json.loads((root / "kit" / "hashes.json").read_text(encoding="utf-8"))["releases"]
    assert len(rows["1.0.0"]["verbatim"]["a.txt"]) == 2
    assert list(rows) == ["1.0.0"]


def test_ac2_a_flow_change_without_a_changelog_line_fails_naming_the_rule_and_the_class(tmp_path):
    """REQ-035 AC2: rule 2 (no silent change)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed silently\n", encoding="utf-8")
    refresh(root)
    found = kit_hashes.problems(root, "HEAD")
    assert any("flow mode" in f and "Unreleased" in f and "a.txt" in f for f in found), found
    assert not any("kit_version bump" in f for f in found)


def test_ac2_a_line_that_is_not_new_or_not_a_pull_request_line_does_not_count(tmp_path):
    """REQ-035 AC2: rule 2 (the line must be new against the base and name a pull request)."""
    root = flow_kit(tmp_path)
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    (root / "CHANGELOG.md").write_text(text.replace("- #1 the start", "- #1 the start, reworded"))
    (root / "a.txt").write_text("a changed\n", encoding="utf-8")
    refresh(root)
    assert any("Unreleased" in f for f in kit_hashes.problems(root, "HEAD"))
    add_line(root, "a line without a number")
    assert any("Unreleased" in f for f in kit_hashes.problems(root, "HEAD"))
    add_line(root, "- #8 now a real line")
    assert kit_hashes.problems(root, "HEAD") == []


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


def test_ac6_after_two_builds_the_regenerated_table_is_accepted(tmp_path):
    """REQ-035 AC6: rule 6 (a collision in the table is resolved by `kit_hashes.py --write`)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a by the first build\n", encoding="utf-8")
    add_line(root, "- #7 the first build")
    settle(root, "first build")
    first_table = (root / "kit" / "hashes.json").read_text(encoding="utf-8")
    (root / "a.txt").write_text("a by the second build\n", encoding="utf-8")
    add_line(root, "- #8 the second build")
    (root / "kit" / "hashes.json").write_text(
        first_table, encoding="utf-8"
    )  # stale after the merge
    stale = kit_hashes.problems(root, "HEAD")
    assert any("row 1.0.0 differs from the history" in f for f in stale), stale
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
    assert kit_hashes.problems(root, "HEAD") == []
    rows = json.loads((root / "kit" / "hashes.json").read_text(encoding="utf-8"))["releases"]
    assert len(rows["1.0.0"]["verbatim"]["a.txt"]) == 3
