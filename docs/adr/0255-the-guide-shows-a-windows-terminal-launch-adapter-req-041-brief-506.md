# ADR-0255: The guide shows a Windows Terminal launch adapter (REQ-041, brief 506)

- Status: Proposed
- Date: 2026-11-03
- Deciders: maintainers
- Related: ADR-0190
- Requirements: REQ-041

Protected classes: `tests/kit/`

## Context

The auto-start section of `docs/guides/getting-started.md` shows two launch adapters, GNOME Terminal and a cloud
session (#487). On Windows the pilot owner wrote an adapter by hand on 2026-11-02 and 2026-11-03 and met four faults:
a tab opened before its worktree existed (#481), tabs inherited `CLAUDE_CODE_CHILD_SESSION` so transcripts were not
saved (#496), tabs stayed open on a bare shell after the session ended (#497), and a crashed session left its tab open
(#503). Brief #506 asks for a third example that avoids all four, and a docs-only test of it in `tests/kit/`, a
protected class. This ADR number was reserved for brief #506 by the conductor (the field note on #506).

## Decision

1. The guide shows, beside the two adapters, a PowerShell script `scripts/start-session-windows.ps1`, marked
   `(verify)` for the terminal's options, which the kit does not install. In order it reads `AGK_SESSION`, `AGK_BRIEF`
   and the prompt on standard input; creates the worktree with `git worktree add` and waits until the folder exists;
   builds the tab's environment with PATH read fresh from the machine and user values, `TEMP`, `TMP` and `TMPDIR` set to
   the long path, and `CLAUDE_CODE_CHILD_SESSION` removed; and opens a Windows Terminal tab with
   `wt -w 0 new-tab --profile "AGK builder" --title <session> -d <worktree>` running a small wrapper that starts
   `claude` with the prompt. When `claude` exits, the wrapper writes `<worktree>/.agk-session-exit` with the exit code
   and the UTC time, and exits. After the worktree exists, the script appends `.agk-session-exit` to the worktree's
   exclude file (`git rev-parse --git-path info/exclude`), so the exit file never reaches a commit. The guide says,
   before the script, that it needs PowerShell 7 (`pwsh`) and must not run under Windows PowerShell 5.1, which strips
   the embedded double quotes of a prompt passed to `claude`.
2. The guide shows the Windows Terminal profile "AGK builder" with `"closeOnExit": "always"`, so the tab closes on any
   exit, a crash included, and says that the default `graceful` keeps a tab open after a non-zero exit and that other
   tabs keep their own setting.
3. The guide says that a builder's tab therefore closes when the session ends, that the exit file shows a crash, and how
   to try the adapter once by hand.
4. `tests/kit/test_guide_windows_adapter.py` checks the guide's section: the worktree step before `new-tab`, the removal
   of `CLAUDE_CODE_CHILD_SESSION`, `TEMP`/`TMP`/`TMPDIR`, `closeOnExit` `always`, the exit file, its exclude step and the PowerShell 7 sentence. It reads this ADR as
   Proposed or Accepted (ADR-0250).

## Consequences

A Windows team copies a working adapter instead of rediscovering the four faults. Nothing installed changes:
`launch.py`, `session.py` and the kit manifest are untouched, and the exit file is written but not yet read.

## Residual

- 2026-11-03: `session.py` reading `.agk-session-exit` is a later brief.
- 2026-11-03: the Windows Terminal and PowerShell options are marked `(verify)`; they were not run by the builder, whose session runs on Linux.
- 2026-11-03: macOS terminals are out of scope.
