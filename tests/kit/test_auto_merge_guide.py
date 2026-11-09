"""The owner's guide to the guarded merge (brief #925, SPEC-0039 build (e), rule 11). REQ-046.

`docs/guides/auto-merge.md` says what the setting does and does not do, how to add a second
account for the conductor, how to open the `agk-auto-merge` record issue, how to run the command
on Windows (PowerShell and cmd) and on POSIX, what each line of rule 2 means and how to stop
merging. Each line of rule 2 is read from `scripts/agk/merge_cleared.py`'s own text, so a renamed
line fails here. `docs/guides/local-mode.md` links to the guide. Docs only: files, no network.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guides" / "auto-merge.md"
LOCAL = ROOT / "docs" / "guides" / "local-mode.md"
SCRIPT = ROOT / "scripts" / "agk" / "merge_cleared.py"
COMMAND = "scripts/agk/merge_cleared.py --pr <n> --sha <the 40-character head sha>"


def guide() -> str:
    assert GUIDE.is_file(), "docs/guides/auto-merge.md is missing"
    return GUIDE.read_text(encoding="utf-8")


def script_lines() -> list[str]:
    """The lines of rule 2 as the script's docstring shows them: `merge-cleared #<n> <sha12>: ...`
    up to the reason, and the stop line."""
    text = SCRIPT.read_text(encoding="utf-8")
    line = r"^\s+(merge-cleared #<n> <sha12>: (?:merged|held|refused)[^ ]*)"
    found = re.findall(line, text, re.M)
    stopped = re.findall(r"^\s+(merge-cleared: stopped: default branch red after #<n>)", text, re.M)
    lines = sorted(set(found)) + stopped[:1]
    assert len(lines) == 4, lines
    return lines


def test_the_guide_exists_for_the_owner():
    """REQ-046"""
    text = guide()
    assert text.startswith("# "), "the guide has a title"
    assert "SPEC-0039" in text


def test_the_guide_names_the_three_settings():
    """REQ-046"""
    text = guide()
    for setting in ("auto_merge", "auto_merge_method", "conductor_accounts", "paused"):
        assert f"`{setting}" in text, setting
    assert "auto_merge = false" in text and "paused = true" in text


def test_the_guide_says_what_it_does_and_does_not_do():
    """REQ-046"""
    text = guide()
    assert "## What the setting does" in text
    assert "## What it does not do" in text


def test_the_guide_says_one_account_and_how_to_add_a_second():
    """REQ-046"""
    text = guide()
    assert "one account" in text.lower()
    assert "config/reviewers.yaml" in text and "spec_approvers" in text
    assert "example.com" in text, "invented accounts only"
    assert "conductor_accounts:" in text, "the guide shows the reviewers.yaml lines"


def test_the_guide_opens_the_record_issue():
    """REQ-046"""
    text = guide()
    assert "agk-auto-merge" in text
    assert "gh api" in text and "issues" in text
    assert "Auto merge: #<n>" in text


def test_the_guide_shows_posix_powershell_and_cmd():
    """REQ-046"""
    text = guide()
    assert "```sh\npython3 " + COMMAND.replace("<the 40-character head sha>", "<sha>") in text
    assert "```powershell" in text and "```bat" in text
    assert "python " + COMMAND.replace("<the 40-character head sha>", "<sha>") in text


def test_the_guide_explains_each_line_of_rule_2():
    """REQ-046"""
    text = guide()
    for line in script_lines():
        assert f"`{line}" in text, line


def test_the_guide_says_how_to_stop_merging():
    """REQ-046"""
    text = guide()
    assert "## Stop merging" in text
    assert "ADR" in text


def test_local_mode_links_to_the_guide():
    """REQ-046"""
    text = LOCAL.read_text(encoding="utf-8")
    assert "(auto-merge.md)" in text
