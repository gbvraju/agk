"""The guide's Windows Terminal launch adapter (brief #506, ADR-0255).

`docs/guides/getting-started.md`, in the auto-start section beside the GNOME Terminal and cloud
adapters, shows a third adapter: a PowerShell script `scripts/start-session-windows.ps1` that
creates the worktree before it opens the tab, removes `CLAUDE_CODE_CHILD_SESSION`, sets `TEMP`,
`TMP` and `TMPDIR` to the long path, and writes an exit file; and the Windows Terminal profile
"AGK builder" with `"closeOnExit": "always"`. Docs only: the test reads the guide and runs nothing.
REQ-041.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guides" / "getting-started.md"
ADR_DIR = ROOT / "docs" / "adr"
HEADER = "A Windows Terminal adapter"


def section() -> str:
    """The Windows adapter's text: from its header line to the next guide section."""
    text = GUIDE.read_text(encoding="utf-8")
    start = text.find(HEADER)
    assert start != -1, "the guide has no Windows Terminal adapter"
    end = text.find("\n## ", start)
    return text[start : end if end != -1 else len(text)]


def script() -> str:
    """The PowerShell block of the section."""
    found = re.search(r"```powershell\n(.*?)```", section(), re.S)
    assert found, "the section shows no powershell block"
    return found.group(1)


def test_the_windows_adapter_sits_beside_the_other_two():
    """REQ-041"""
    text = GUIDE.read_text(encoding="utf-8")
    gnome = text.find("A local terminal adapter")
    cloud = text.find("A cloud adapter")
    windows = text.find(HEADER)
    upgrading = text.find("## Upgrading the kit")
    assert -1 < gnome < cloud < windows < upgrading


def test_the_script_is_named_and_marked_verify():
    """REQ-041"""
    body = section()
    assert "scripts/start-session-windows.ps1" in script()
    assert "(verify" in body
    assert "The kit installs the script `scripts/start-session-windows.ps1`" in body  # ADR-0525


def test_the_worktree_is_made_before_the_tab_opens():
    """REQ-041"""
    code = script()
    add = code.find("git worktree add")
    wait = code.find("Test-Path")
    tab = code.find("new-tab")
    assert -1 < add < wait < tab


def test_the_tab_command_names_profile_title_and_folder():
    """REQ-041"""
    code = script()
    assert "wt" in code and "-w 0 new-tab" in code
    assert '--profile "AGK builder"' in code
    assert "--title" in code and "-d" in code


def test_the_child_session_marker_is_removed():
    """REQ-041"""
    code = script()
    assert "CLAUDE_CODE_CHILD_SESSION" in code
    assert re.search(r"Remove-Item\s+Env:\\?CLAUDE_CODE_CHILD_SESSION", code) or re.search(
        r"\.Remove\('CLAUDE_CODE_CHILD_SESSION'\)", code
    )


def test_path_is_read_fresh_and_temp_is_the_long_path():
    """REQ-041"""
    code = script()
    assert "GetEnvironmentVariable('Path', 'Machine')" in code
    assert "GetEnvironmentVariable('Path', 'User')" in code
    for name in ("TEMP", "TMP", "TMPDIR"):
        assert re.search(rf"\$env:{name}\s*=", code), name
    assert "GetFolderPath('LocalApplicationData')" in code


def test_the_session_input_is_read():
    """REQ-041"""
    code = script()
    assert "AGK_SESSION" in code and "AGK_BRIEF" in code
    assert "$input" in code or "[Console]::In" in code


def test_the_wrapper_writes_the_exit_file_with_code_and_utc_time():
    """REQ-041"""
    code = script()
    assert ".agk-session-exit" in code
    assert "$LASTEXITCODE" in code
    assert "ToUniversalTime" in code or "UtcNow" in code


def test_the_profile_closes_on_any_exit():
    """REQ-041"""
    body = section()
    found = re.search(r"```json\n(.*?)```", body, re.S)
    assert found, "the section shows no settings.json profile"
    profile = found.group(1)
    assert '"name": "AGK builder"' in profile
    assert '"closeOnExit": "always"' in profile
    assert "graceful" in body


def test_the_section_says_how_the_tab_ends_and_how_to_try_it():
    """REQ-041"""
    body = section()
    assert "crash" in body
    assert "by hand" in body
    assert "AGK_SESSION=" in body or "$env:AGK_SESSION" in body


def test_the_adr_names_the_protected_class_and_is_proposed_or_accepted():
    """REQ-041"""
    adrs = sorted(ADR_DIR.glob("0255-*.md"))
    assert len(adrs) == 1, "ADR-0255 is missing or doubled"
    text = adrs[0].read_text(encoding="utf-8")
    assert "`tests/kit/`" in text
    status = [line for line in text.splitlines() if line.startswith("- Status: ")]
    assert status in (["- Status: Proposed"], ["- Status: Accepted"])


def test_the_section_says_the_adapter_needs_powershell_7_before_the_script():
    """REQ-041"""
    body = section()
    need = body.find("PowerShell 7")
    block = body.find("```powershell")
    assert -1 < need < block, "the section does not say PowerShell 7 before the script"
    assert "winget install Microsoft.PowerShell" in body[:block]
    assert "5.1" in body[:block]


def test_the_exit_file_is_kept_out_of_git_by_the_worktree_exclude():
    """REQ-041"""
    code = script()
    exclude = code.find("rev-parse --git-path info/exclude")
    wait = code.find("Test-Path")
    tab = code.find("new-tab")
    assert -1 < wait < exclude < tab
    assert re.search(r"Add-Content[^\n]*\$exclude[^\n]*\.agk-session-exit", code)
    assert "info/exclude" in section().split("```powershell")[0]
