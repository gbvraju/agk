# ADR-0588: The adapters run jobs in the background with a log each, and show a tab only with `show_jobs`

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1388, SPEC-0064 rules 3, 4, 5 and 16 (e), brief #1386 (ADR-0584), brief #1355 (ADR-0568), brief #1252 (ADR-0530), plan #661
- Requirements: REQ-071

## Context

SPEC-0064 (Approved) makes every AI session a short job with one record and one log (rule 3) and no tabs to manage
(rule 5). Before this build the Windows adapter opened a Windows Terminal tab per session running `claude` interactively,
and the Linux adapter opened a GNOME Terminal tab whenever a desktop was there; only a Linux machine without a desktop
ran the job in the background with `<worktree>/.agk-session.log`.

## Decision

1. **Background by default.** Both adapters start `claude -p` (headless) in the job's worktree with no terminal tab and
   its output in `<worktree>/.agk-session.log`, beside the record and the exit file. The Windows adapter starts its
   wrapper with `Start-Process -WindowStyle Hidden` and needs no Windows Terminal for a job (verify: the runtime's
   headless flag and `Start-Process`'s quoting on Windows).
2. **`[autopilot] show_jobs` (default false).** `launch.py show_jobs` reads it, refusing another kind naming the
   setting, and every adapter call (a builder start or resume, and `launch.py role`) gets `AGK_SHOW_JOBS=true|false`.
   With `true` the Linux adapter, on a desktop, runs the same headless job in a GNOME Terminal tab with its output
   also in the log (`tee`), and the Windows adapter opens its `wt` tab, whose wrapper tees the output to the log; the
   tab runs only the job, so it closes when the job ends (the profile's `closeOnExit`; verify: GNOME Terminal's
   default on exit). Any other value of `AGK_SHOW_JOBS` is the background.
3. **The copies follow.** `scripts/start-session-windows.ps1` (this repository's adapter, ADR-0439) and the
   getting-started guide's block stay the template's code, as their tests require; `docs/guides/local-mode.md` names
   the background mode, the log and `show_jobs`.

Protected path classes changed: `kit/` (`templates/start-session-local.sh`, `templates/start-session-windows.ps1`),
`scripts/agk/` (`launch.py`), `tests/kit/` (`test_autopilot_adapters.py`, `test_adapter_model.py`), `agk.toml` (one
test in the `launch.py` `[[testing.map]]` entry), `docs/adr/` (this file) and `changelog.d/` (one fragment).
`scripts/start-session-windows.ps1` and `docs/guides/` change with them.

## Consequences

A job no longer leaves a tab open or needs a terminal at all; its output is read from the log, and a person who wants
to watch sets one setting. An interactive builder in a tab is gone: a builder that needs a person asks on GitHub
(session rule 21), as a job of rule 4 does.

## Residual

- 2026-11-16: no Windows run proves the hidden start and the tee on this build's CI (Linux); the wrapper test runs
  only where `pwsh` is installed (verify: a run on Windows) (due 2027-03-31).
