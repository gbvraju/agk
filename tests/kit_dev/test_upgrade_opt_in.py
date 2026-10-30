"""An upgrade ends with the opt-in features the new release offers (brief #320 answers 2 and 3;
REQ-038, ADR-0181).

A changelog fragment may end with one marker `(opt-in: <setting>)` for a feature a project switches
on by a setting; the release keeps it in the moved line. After a successful upgrade `upgrade.py`
prints one line `opt-in: <setting>: <summary>` per entry of the kit's `CHANGELOG.md` between the
old version (excluded) and the new one (included) that carries the marker, and nothing extra when
there is none. It writes nothing for it. Fixtures in `tmp_path`; settings and entries are invented.
No network, no model.
"""

from __future__ import annotations

import sys

import pytest
from conftest import KIT_ROOT, git, snapshot
from test_changelog_fragments import bump, check, gather, put, release_repo
from test_upgrade import init_target, make_kit, run

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import check_release  # noqa: E402
import upgrade  # noqa: E402

CHANGELOG = (
    "# Changelog\n\nIntro.\n\n## Unreleased\n\n- #40 an unreleased toggle (opt-in: later_thing)\n\n"
    "## 2.0.0 (2026-10-30)\n\n"
    "- #30 proof runs per test area: an optional table (brief #1, ADR-0001) (opt-in: proof)\n"
    "- #31 a plain fix with no setting (brief #2)\n"
    "- #32 the weekly audit can run an unused-code command (opt-in: unused_code)\n\n"
    "## 1.5.0 (2026-10-20)\n\n"
    "- #20 a review mode for one person: one yes per pull request (opt-in: review_mode)\n\n"
    "## 1.0.0 (2026-10-01)\n\n"
    "- #10 an old toggle the project already had (opt-in: old_thing)\n\n"
    "## 0.9.0 (2026-09-01)\n\n"
    "- #5 an older one (opt-in: older_thing)\n"
)


@pytest.fixture
def kit(tmp_path, monkeypatch):
    root = make_kit(tmp_path)
    monkeypatch.setattr(upgrade, "KIT_ROOT", root)
    return root


def opt_in_lines(out: list[str]) -> list[str]:
    return [ln for ln in out if ln.startswith("opt-in:")]


# --- the marker (answer 2) ---------------------------------------------------------------------


def test_a_marker_gives_the_setting_and_the_one_line_summary():
    found = check_release.opt_in(
        "- #30 proof runs per test area: an optional table (brief #1, ADR-0001) (opt-in: proof)"
    )
    assert found == ("proof", "proof runs per test area")


def test_a_fragment_line_without_a_number_is_read_the_same_way():
    assert check_release.opt_in("- a toggle for coverage (opt-in: coverage)") == (
        "coverage",
        "a toggle for coverage",
    )


def test_a_dotted_setting_names_a_key_of_a_table():
    assert check_release.opt_in("- #9 assign by the conductor (opt-in: flow.assign)") == (
        "flow.assign",
        "assign by the conductor",
    )


@pytest.mark.parametrize(
    "line",
    [
        "- #31 a plain fix with no setting (brief #2)",
        "- #31 a marker in the middle (opt-in: proof) and more text",
        "- #31 two markers (opt-in: proof) (opt-in: coverage)",
        "- #31 an empty marker (opt-in: )",
        "- #31 a value, not a setting (opt-in: Proof Table!)",
        "- #31 no space before the marker(opt-in: proof)",
    ],
)
def test_a_line_without_exactly_one_marker_at_its_end_offers_nothing(line):
    assert check_release.opt_in(line) is None


def test_a_long_summary_is_cut_at_a_word_boundary():
    words = " ".join(["word"] * 60)
    setting, summary = check_release.opt_in(f"- #1 {words} (opt-in: proof)")
    assert setting == "proof"
    assert len(summary) <= check_release.SUMMARY_LIMIT and summary.endswith("word")


def test_the_entries_between_two_versions_are_the_newer_releases_only():
    found = check_release.opt_ins(CHANGELOG, "1.0.0", "2.0.0")
    assert found == [
        ("proof", "proof runs per test area"),
        ("unused_code", "the weekly audit can run an unused-code command"),
        ("review_mode", "a review mode for one person"),
    ]
    assert check_release.opt_ins(CHANGELOG, "2.0.0", "2.0.0") == []


def test_the_release_keeps_the_marker_in_the_moved_line(tmp_path):
    """Answer 2: the gather moves the fragment's line unchanged, marker included, and the release
    check passes."""
    root = release_repo(tmp_path, numbers=())
    put(root, "changelog.d/toggle.md", "- a toggle for coverage (opt-in: coverage)\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "feat: a toggle (#21)")
    git(root, "switch", "-q", "-c", "release")
    assert gather(root).returncode == 0
    bump(root)
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "- #21 a toggle for coverage (opt-in: coverage)\n" in text
    proc = check(root)
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout
    assert check_release.opt_ins(text, "1.0.0", "1.1.0") == [("coverage", "a toggle for coverage")]


# --- the upgrade listing (answer 3) ------------------------------------------------------------


def test_an_upgrade_ends_with_one_line_per_opt_in_entry_of_the_newer_releases(
    tmp_path, kit, capsys
):
    (kit / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    code, out = run(capsys, init_target(tmp_path))
    assert code == 0, out
    assert opt_in_lines(out) == [
        "opt-in: proof: proof runs per test area",
        "opt-in: unused_code: the weekly audit can run an unused-code command",
        "opt-in: review_mode: a review mode for one person",
    ]
    assert out[-3:] == opt_in_lines(out)  # the listing ends the upgrade


def test_an_upgrade_with_no_marker_prints_nothing_extra(tmp_path, kit, capsys):
    plain = "# Changelog\n\n## Unreleased\n\n## 2.0.0 (2026-10-30)\n\n- #31 a plain fix\n"
    (kit / "CHANGELOG.md").write_text(plain, encoding="utf-8")
    code, out = run(capsys, init_target(tmp_path))
    assert code == 0 and opt_in_lines(out) == []
    assert out[-1].startswith("upgraded ") or out[-1].startswith("run: "), out


def test_the_listing_writes_nothing(tmp_path, kit, capsys):
    (kit / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    one = init_target(tmp_path / "one")
    two = init_target(tmp_path / "two")
    (kit / "CHANGELOG.md").write_text(CHANGELOG.replace("(opt-in:", "(note:"), encoding="utf-8")
    run(capsys, one)
    (kit / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    run(capsys, two)
    def contents(root):
        return {rel: digest for rel, (digest, _) in snapshot(root).items()}

    assert contents(one) == contents(two)  # the same files and bytes with or without markers


def test_a_dry_run_and_a_refused_or_empty_run_list_nothing(tmp_path, kit, capsys):
    (kit / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    target = init_target(tmp_path)
    code, out = run(capsys, target, "--dry-run")
    assert code == 0 and opt_in_lines(out) == []
    assert run(capsys, target)[0] == 0
    code, out = run(capsys, target)
    assert code == 0 and out[-1] == "nothing to do" and opt_in_lines(out) == []


def test_an_unreadable_changelog_says_so_and_does_not_fail_the_upgrade(tmp_path, kit, capsys):
    (kit / "CHANGELOG.md").unlink(missing_ok=True)
    code, out = run(capsys, init_target(tmp_path))
    assert code == 0
    assert out[-1] == "opt-in: the new features cannot be listed (path class CHANGELOG.md)"
