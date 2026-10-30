"""A marker may name several settings, and an upgrade from before 0.59.0 lists the opt-in settings
0.59.0 shipped (brief #340; REQ-038, ADR-0193).

The marker `(opt-in: a, b, c)` names several settings separated by `, `; `upgrade.py` lists one line
per setting, each with the entry's summary. An entry whose change starts with `<version> added `
speaks for that earlier release: it is listed to an upgrade that crosses that version, even though
it sits in a later section, and never to an upgrade from that version or newer. Fixtures in
`tmp_path`; no network, no model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import check_release  # noqa: E402
import upgrade  # noqa: E402

FRAGMENT = KIT_ROOT / "changelog.d" / "opt-in-0-59-0.md"
SHIPPED = ("proof", "unused_code", "coverage")  # the opt-in settings that v0.59.0 added


# --- the marker with one and with several settings (answer 1) ----------------------------------


def test_a_marker_with_one_setting_gives_that_setting():
    assert check_release.opt_in("- #1 a toggle: more words (opt-in: proof)") == (
        ("proof",),
        "a toggle",
    )


def test_a_marker_with_several_settings_gives_each_in_its_order():
    assert check_release.opt_in(
        "- #1 three toggles: more words (opt-in: proof, unused_code, flow.assign)"
    ) == (("proof", "unused_code", "flow.assign"), "three toggles")


@pytest.mark.parametrize(
    "marker",
    [
        "proof,unused_code",  # no space after the comma
        "proof, ",  # an empty last setting
        "proof,, coverage",  # an empty setting in the middle
        ", proof",  # an empty first setting
        "proof coverage",  # no comma
        "proof; coverage",  # another separator
        "proof, Coverage!",  # a value, not a setting
        "proof, proof",  # the same setting twice
    ],
)
def test_a_malformed_list_offers_nothing(marker):
    assert check_release.opt_in(f"- #1 a toggle (opt-in: {marker})") is None


def test_opt_ins_gives_one_pair_per_setting_with_the_entry_summary():
    changelog = (
        "# Changelog\n\n## Unreleased\n\n## 2.0.0 (2026-10-30)\n\n"
        "- #3 two toggles: details (opt-in: proof, coverage)\n"
        "- #4 one more (opt-in: review_mode)\n"
    )
    assert check_release.opt_ins(changelog, "1.0.0", "2.0.0") == [
        ("proof", "two toggles"),
        ("coverage", "two toggles"),
        ("review_mode", "one more"),
    ]


def test_the_upgrade_prints_one_line_per_setting(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n\n## 2.0.0 (2026-10-30)\n\n"
        "- #3 two toggles: details (opt-in: proof, coverage)\n",
        encoding="utf-8",
    )
    assert upgrade.opt_in_lines(tmp_path, "1.0.0", "2.0.0") == [
        "opt-in: proof: two toggles",
        "opt-in: coverage: two toggles",
    ]


# --- an entry that speaks for an earlier release (answer 3) -------------------------------------

BACKFILL = (
    "# Changelog\n\n## Unreleased\n\n"
    "## 0.60.0 (2026-11-02)\n\n"
    "- #350 a feature of 0.60.0 (opt-in: later_thing)\n"
    "- #341 0.59.0 added proof per test area and the drift audit's two commands: details "
    "(opt-in: proof, unused_code, coverage)\n\n"
    "## 0.59.0 (2026-10-30)\n\n"
    "- #307 proof can run one command per test area: an optional table\n\n"
    "## 0.58.0 (2026-10-29)\n\n"
    "- #300 an older change\n"
)
SUMMARY = "0.59.0 added proof per test area and the drift audit's two commands"


def test_the_release_an_entry_speaks_for_is_read_from_its_start():
    assert check_release.release_named("- #341 0.59.0 added a toggle (opt-in: proof)") == "0.59.0"
    assert check_release.release_named("- 0.59.0 added a toggle (opt-in: proof)") == "0.59.0"
    assert check_release.release_named("- #341 a toggle that 0.59.0 added (opt-in: proof)") is None
    assert check_release.release_named("- #341 0.59.0 changed a toggle (opt-in: proof)") is None
    assert check_release.release_named("- #341 a plain toggle (opt-in: proof)") is None


def test_an_upgrade_from_0_58_0_lists_the_settings_0_59_0_added():
    assert check_release.opt_ins(BACKFILL, "0.58.0", "0.60.0") == [
        ("later_thing", "a feature of 0.60.0"),
        ("proof", SUMMARY),
        ("unused_code", SUMMARY),
        ("coverage", SUMMARY),
    ]


def test_an_upgrade_from_0_59_0_does_not_list_them_again():
    assert check_release.opt_ins(BACKFILL, "0.59.0", "0.60.0") == [
        ("later_thing", "a feature of 0.60.0")
    ]


def test_an_upgrade_from_an_older_release_lists_them_too():
    found = check_release.opt_ins(BACKFILL, "0.40.0", "0.60.0")
    assert [setting for setting, _ in found] == ["later_thing", *SHIPPED]


def test_an_upgrade_that_ends_before_the_entry_lists_nothing_of_it():
    """The new kit must have the entry: an upgrade to 0.59.0 reads no later section."""
    assert check_release.opt_ins(BACKFILL, "0.58.0", "0.59.0") == []


def test_an_entry_that_names_its_own_or_a_later_release_is_read_by_its_section():
    changelog = (
        "# Changelog\n\n## Unreleased\n\n## 0.60.0 (2026-11-02)\n\n"
        "- #1 0.60.0 added a toggle (opt-in: own)\n"
        "- #2 0.61.0 added a toggle (opt-in: later)\n\n"
        "## 0.59.0 (2026-10-30)\n\n- #0 plain\n"
    )
    assert [s for s, _ in check_release.opt_ins(changelog, "0.59.0", "0.60.0")] == ["own", "later"]
    assert check_release.opt_ins(changelog, "0.60.0", "0.60.0") == []


def test_the_two_upgrades_through_the_upgrade_listing(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(BACKFILL, encoding="utf-8")
    assert upgrade.opt_in_lines(tmp_path, "0.58.0", "0.60.0") == [
        "opt-in: later_thing: a feature of 0.60.0",
        *(f"opt-in: {setting}: {SUMMARY}" for setting in SHIPPED),
    ]
    assert upgrade.opt_in_lines(tmp_path, "0.59.0", "0.60.0") == [
        "opt-in: later_thing: a feature of 0.60.0"
    ]


# --- the fragment for the next release (answer 2) -----------------------------------------------


RELEASED_AS = "- #343 "  # the line the release gathers from the fragment of pull request #343


def entry_line(root: Path) -> str:
    """The 0.59.0 entry as a fragment line `- <change>` (brief #362 answer 1): from
    `changelog.d/opt-in-0-59-0.md` while that file exists, otherwise from the `- #343 ` line that
    the release moved into `CHANGELOG.md`, its number taken off."""
    fragment = root / "changelog.d" / FRAGMENT.name
    if fragment.is_file():
        lines = fragment.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1, lines  # one fragment of one line (SPEC-0031 rules 1 and 2)
        return lines[0]
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()
    released = [line for line in changelog if line.startswith(RELEASED_AS)]
    assert len(released) == 1, f"no fragment and {len(released)} lines {RELEASED_AS.strip()}"
    return "- " + released[0].removeprefix(RELEASED_AS)


def fragment_line() -> str:
    return entry_line(KIT_ROOT)


def test_the_fragment_speaks_for_0_59_0_and_names_the_settings_it_shipped():
    line = fragment_line()
    assert check_release.release_named(line) == "0.59.0"
    settings, _ = check_release.opt_in(line)
    assert settings == SHIPPED


def test_the_shipped_settings_are_settings_the_kit_reads():
    """`unused_code` and `coverage` are keys of the defaults; `proof` is the table that
    `common.proof_areas` reads (no setting is invented)."""
    import common

    assert {"unused_code", "coverage"} <= set(common.DEFAULT_CONFIG)
    assert 'config_source(root).get("proof")' in (
        KIT_ROOT / "scripts" / "agk" / "common.py"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize(("old", "listed"), [("0.58.0", SHIPPED), ("0.59.0", ())])
def test_the_released_fragment_lists_the_settings_across_0_59_0_only(old, listed):
    """The fragment as the next release would gather it (`- #n ` added, the line unchanged)."""
    changelog = (
        "# Changelog\n\n## Unreleased\n\n"
        f"## 0.60.0 (2026-11-02)\n\n- #999 {fragment_line()[2:]}\n\n"
        "## 0.59.0 (2026-10-30)\n\n- #307 plain\n\n## 0.58.0 (2026-10-29)\n\n- #300 plain\n"
    )
    found = check_release.opt_ins(changelog, old, "0.60.0")
    assert tuple(setting for setting, _ in found) == listed


# --- the entry before and after the release moves the fragment (brief #362) ---------------------

LINE = (
    "- 0.59.0 added proof per test area: details (brief #340, ADR-0193) "
    "(opt-in: proof, unused_code, coverage)"
)


def kit_copy(root: Path, *, fragment: bool) -> Path:
    """A kit with the entry as a fragment (before the release) or moved into the changelog."""
    if fragment:
        (root / "changelog.d").mkdir(parents=True)
        (root / "changelog.d" / FRAGMENT.name).write_text(LINE + "\n", encoding="utf-8")
        released = "- #300 an older change\n"
    else:
        root.mkdir(parents=True, exist_ok=True)
        released = f"- #343 {LINE[2:]}\n- #300 an older change\n"
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## Unreleased\n\n## 0.60.0 (2026-10-30)\n\n{released}", encoding="utf-8"
    )
    return root


@pytest.mark.parametrize("fragment", [True, False], ids=["fragment", "released"])
def test_the_entry_is_read_before_and_after_the_release(tmp_path, fragment):
    """Answers 1 and 2: from the fragment while it exists, else from the `- #343 ` line."""
    assert entry_line(kit_copy(tmp_path / "kit", fragment=fragment)) == LINE


def test_a_kit_with_neither_the_fragment_nor_the_line_fails_plainly(tmp_path):
    root = tmp_path / "kit"
    root.mkdir()
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="#343"):
        entry_line(root)
