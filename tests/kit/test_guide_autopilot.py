"""The local-mode guide's unattended steps use `[autopilot]` (brief #1451, ADR-0609).

`docs/guides/local-mode.md`, "Running unattended", must lead a person to a setup that doctor
passes: the adapter, then `[autopilot] mode`, `interval_minutes` and `daily_budget`, then
`agk autopilot on`. The settings that `[autopilot]` replaces (`config.legacy_autopilot`, the ones
doctor reports `not read: [autopilot] is set`) appear once, in the one note that says they are
read only while `[autopilot]` is absent. Docs only: the test reads the guide and saved text, runs
nothing and uses no network. REQ-071.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import config

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guides" / "local-mode.md"
HEADER = "## Running unattended"
NOTE_START = "**Older settings**"
# The names doctor reports as not read once `[autopilot]` is set, as config reads them.
LEGACY = config.legacy_autopilot(
    {"flow": {"auto_start": True, "launch_adapter": "x"}, "capacity": {}}
)
TOKENS = {"auto_start": "auto_start", "launch_adapter": "launch_adapter", "capacity": "[capacity]"}


def section(text: str | None = None) -> str:
    """The unattended section: its header to the next `## ` heading."""
    text = GUIDE.read_text(encoding="utf-8") if text is None else text
    start = text.find(HEADER)
    assert start != -1, "the guide has no Running unattended section"
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def split_note(body: str) -> tuple[str, str]:
    """The section without its one note, and the note (the paragraph of `**Older settings**`)."""
    paragraphs = re.split(r"\n\s*\n", body)
    notes = [p for p in paragraphs if p.lstrip().startswith(NOTE_START)]
    rest = "\n\n".join(p for p in paragraphs if p not in notes)
    return rest, "\n\n".join(notes)


def named_outside_note(body: str) -> list[str]:
    """The replaced settings that the section names anywhere but in its one note."""
    rest, _ = split_note(body)
    return [name for name in LEGACY if TOKENS[name] in rest]


def test_the_replaced_settings_are_the_ones_doctor_names():
    """REQ-071"""
    assert LEGACY == ["auto_start", "launch_adapter", "capacity"]


def test_the_section_names_no_replaced_setting_outside_the_note():
    """REQ-071"""
    assert named_outside_note(section()) == []


def test_the_guide_sets_autopilot_then_turns_it_on():
    """REQ-071"""
    rest, _ = split_note(section())
    for key in ("[autopilot]", "mode", "interval_minutes", "daily_budget"):
        assert key in rest
    set_at = rest.find("[autopilot]")
    on_at = rest.find("agk autopilot on")
    assert -1 < set_at < on_at, "the table is set before the command that turns it on"
    # the plain `watchdog --install` step is gone; the scripted pass keeps its own line
    assert not re.search(r"watchdog --install(?! --pass)", rest)


def test_the_one_note_names_each_replaced_setting_once():
    """REQ-071"""
    _, note = split_note(section())
    assert note, "the section has no Older settings note"
    assert "[autopilot]" in note and "absent" in note
    for name in LEGACY:
        assert note.count(TOKENS[name]) == 1


def test_a_second_note_or_a_stray_mention_fails():
    """REQ-071: edge cases on saved text."""
    good = section()
    stray = good.replace("`agk autopilot on`", "`agk autopilot on` (set `auto_start = true`)", 1)
    assert named_outside_note(stray) == ["auto_start"]
    unmarked = good.replace(NOTE_START, "**Notes**")
    assert set(named_outside_note(unmarked)) == set(LEGACY)
    assert named_outside_note(good) == []


def test_a_guide_without_the_section_is_refused():
    """REQ-071"""
    with pytest.raises(AssertionError, match="Running unattended"):
        section("# Local mode\n\ntext\n")


def test_each_command_line_of_the_section_is_a_kit_command():
    """REQ-071: the guide's command lines name scripts and subcommands that exist."""
    for found in re.findall(r"python3 (scripts/agk/\w+\.py)", section()):
        assert (ROOT / found).exists(), found
