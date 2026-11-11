"""This repository's Windows Terminal launcher and the auto-start settings (brief #1030, ADR-0439).

`scripts/start-session-windows.ps1` is the guide's adapter (getting-started step 7) with one change:
an existing worktree folder `..\\agk-<AGK_SESSION>` of this repository is reused (fetch, then
`origin/main` checked out detached when its tree is clean), and a folder that is not clean starts
nothing and exits non-zero with one line naming the folder. `agk.toml` `[flow]` turns `auto_start` on
with that script as `launch_adapter`. The tests read files only; no PowerShell runs here. REQ-037.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "start-session-windows.ps1"
GUIDE = ROOT / "docs" / "guides" / "getting-started.md"
ADAPTER = "pwsh -NoProfile -File scripts/start-session-windows.ps1"

sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import launch  # noqa: E402


def text() -> str:
    assert SCRIPT.is_file(), "scripts/start-session-windows.ps1 is missing"
    return SCRIPT.read_text(encoding="utf-8")


def guide_block() -> str:
    guide = GUIDE.read_text(encoding="utf-8")
    start = guide.find("A Windows Terminal adapter")
    found = re.search(r"```powershell\n(.*?)```", guide[start:], re.S)
    assert start != -1 and found
    return found.group(1)


# --- (a) the script and its environment steps ---------------------------------------------------


def test_the_script_holds_the_guides_environment_steps():
    """REQ-037: brief #1030 answer 3 (a)."""
    code = text()
    for line in (
        "$env:TEMP = $LongTemp",
        "$env:TMP = $LongTemp",
        "$env:TMPDIR = $LongTemp",
        "Remove-Item Env:CLAUDE_CODE_CHILD_SESSION",
        "'.agk-session-exit'",
        '"exit_code=$code"',
        "[Environment]::GetEnvironmentVariable('Path', 'Machine')",
        '--profile "AGK builder"',
    ):
        assert line in code, line


def test_the_script_keeps_the_guides_wrapper_unchanged():
    """REQ-037: answer 1 (the guide's text as its start): the tab's wrapper is the guide's, line for line."""
    def wrapper(block: str) -> list[str]:
        found = re.search(r"@'\n(.*?)\n\s*'@", block, re.S)
        assert found
        return [line.strip() for line in found.group(1).splitlines()]

    assert wrapper(text()) == wrapper(guide_block())


def test_an_existing_worktree_of_this_repository_is_reused_when_clean():
    """REQ-037: answer 1, the reuse branch."""
    code = text()
    assert "Test-Path -LiteralPath $worktree" in code
    # it is a worktree of this repository: the same common git folder
    assert "--git-common-dir" in code
    # clean: no change, staged or not, and no untracked file but the exit file
    assert "status --porcelain" in code
    reuse = code[code.find("Test-Path -LiteralPath $worktree") :]
    fetch = reuse.find("fetch --quiet origin")
    checkout = reuse.find("checkout --quiet --detach origin/main")
    assert -1 < fetch < checkout
    add = code.find("worktree add --detach $worktree origin/main")
    assert add != -1, "a new session still gets its worktree with git worktree add"


def test_a_folder_that_is_not_clean_or_not_ours_starts_nothing():
    """REQ-037: answer 1: one line naming the folder, a non-zero exit, and no tab."""
    code = text()
    refusals = re.findall(r"\[Console\]::Error\.WriteLine\((.*?)\)\s*;\s*exit (\d+)", code)
    assert len(refusals) >= 2, refusals
    for message, code_ in refusals:
        assert "$worktree" in message
        assert code_ != "0"
    assert "is not clean" in code
    assert "is not a worktree of this repository" in code
    # every refusal comes before the tab is opened
    assert code.rfind("exit 2") < code.find("wt -w 0 new-tab")


def test_the_tab_opens_only_after_the_worktree_is_settled():
    """REQ-037: the guide's order is kept: worktree, wait, exclude file, wrapper, tab."""
    code = text()
    order = [
        code.find("worktree add --detach"),
        code.find("$deadline"),
        code.find("info/exclude"),
        code.find("run.ps1"),
        code.find("wt -w 0 new-tab"),
    ]
    assert -1 not in order and order == sorted(order), order


# --- (b) the settings on this checkout ---------------------------------------------------------


def test_auto_start_is_on_with_the_windows_adapter():
    """REQ-037: answer 2 and answer 3 (b)."""
    assert launch.launch_settings(ROOT) == (True, ADAPTER)


def test_the_setting_names_its_direction_and_powershell_7():
    """REQ-037: answer 2: the comment names the owner's direction, ADR-0439 and PowerShell 7."""
    toml = (ROOT / "agk.toml").read_text(encoding="utf-8")
    flow = toml[toml.find("[flow]") :]
    at = flow.find("auto_start = true")
    assert at != -1
    comment = flow[max(0, flow.rfind("\n\n", 0, at)) : at]
    for word in ("2026-11-11", "ADR-0439", "PowerShell 7", "winget install Microsoft.PowerShell"):
        assert word in comment, word


def test_the_script_is_not_installed_by_the_kit():
    """REQ-037: answer 1: the kit's manifest does not change."""
    manifest = (ROOT / "kit" / "manifest.json").read_text(encoding="utf-8")
    assert "start-session-windows" not in manifest
