# ADR-0439: The conductor starts local builders in Windows Terminal tabs

- Status: Accepted
- Date: 2026-11-11
- Deciders: maintainers
- Related: brief #1030, plan #661, ADR-0438 (brief #1029), ADR-0255 (brief #506), ADR-0190 (brief #331)
- Requirements: REQ-037

Protected classes: `agk.toml`, `tests/kit_dev/`

## Context

On 2026-11-11 the owner opened the conductor and the builders lap1 and lap2 by hand on his Windows laptop, made their
worktrees by hand and pasted each prompt. AGK already has the mechanism: the conductor's re-plan runs
`launch.py prompts --plan FILE --adapter COMMAND` when `[flow] auto_start = true` and `launch_adapter` are set on the
default branch, and the guide shows a Windows Terminal adapter, `scripts/start-session-windows.ps1`, "shown here and not
installed by the kit". On main neither setting was set and the script did not exist, so `launch.launch_settings`
returned `(False, None)` and the conductor only printed prompts. The guide's script also fails at `git worktree add`
when a session's folder is left from an earlier start. The owner's word (2026-11-11 02:56 IST): "file it both 1 and 2,
launcher item as well".

## Decision

1. This repository carries `scripts/start-session-windows.ps1`, the guide's script with one change: when the folder
   `..\agk-<AGK_SESSION>` already exists and is a worktree of this repository (the same common git folder, and the
   folder is its top level), the script fetches and checks out `origin/main` detached when its tree is clean (no
   change, staged or not, and no untracked file but the exit file), instead of running `git worktree add`. When the
   folder exists and is not clean, or is not a worktree of this repository, it opens no tab and exits 2 with one line
   naming the folder. The kit does not install it; `kit/manifest.json` does not change.
2. `agk.toml` `[flow]` sets `auto_start = true` and
   `launch_adapter = "pwsh -NoProfile -File scripts/start-session-windows.ps1"` by the owner's direction of
   2026-11-11, with a comment saying the adapter needs PowerShell 7.

## Consequences

The conductor's next re-plan with a free slot opens a builder tab and worktree by itself, up to the plan's capacity and
`max_builders`; no person opens terminals or pastes prompts. A conductor that runs where `pwsh` or `wt` is missing (a
cloud session on Linux) gets the adapter refused; `launch.py` reports a refused adapter once and never retries it, so
it starts nothing there, as before. A reused worktree keeps the branches it held; a detached head's own commits stay
in its reflog. Turning auto-start off is again a change to `agk.toml` with an ADR.

## Residual

- 2026-11-11: the trial run on Windows (the guide's own check, brief #1030 answer 4) is run by the owner on his laptop;
  the builder of #1030 runs on Linux and asked for it as `Q-1030-1`.
