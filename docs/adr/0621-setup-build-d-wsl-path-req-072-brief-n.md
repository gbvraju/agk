# ADR-0621: /agk:setup build (d): the WSL path calls /agk:wsl unchanged, then the scheduler

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: SPEC-0065, ADR-0577, ADR-0579, ADR-0606, ADR-0618, ADR-0619, ADR-0620, brief #1463, plan #661
- Requirements: REQ-072

## Context

SPEC-0065 (Approved) names eight builds of `/agk:setup` (rule 18); this is build (d): the WSL path of rule 7, wiring
`/agk:wsl` in (rule 17). `/agk:wsl` (ADR-0577) already does the machine work inside WSL 2 with its kit-only
`wsl_setup.ps1` (each step check-then-act, `-Json`) and `wsl.py` (the plan and the status); brief #1448 (ADR-0606) made
that script's watchdog step hand the scheduler to `autopilot.py on` inside WSL when `[autopilot]` is set. Brief #1463
answer 1: the two are called, never copied, and the scheduler is that one task, not a second one.

## Decision

1. **`setup.py wsl`**, a new form of the kit-only helper, runs on the Windows host only when the person chose WSL 2
   (`--answer windows=wsl`) and the work runs on this machine or for them only (`where`, else `execution`; CI mode,
   `hosted` by default, installs nothing, rule 16). Any other platform, Windows itself or CI mode is refused naming its
   setting, and nothing is called.
2. **`/agk:wsl` called unchanged.** It runs the plugin's own `wsl_setup.ps1 -Status -Engine <engine> -Json` and
   `wsl.py plan --state <its table>`; without the person's yes it stops there with one line and sets up nothing. After
   the yes it runs one `wsl_setup.ps1 -Engine <engine> -Json` pass and `wsl.py status`. The table is the script's own
   rows (`done`, `skipped`, `waiting`, `failed`), so a second run reports every step `skipped` and a stopped run resumes
   at its failed step; a failed step stops with one line, and a script that gives no table (PowerShell 7 missing) stops
   before any setup pass. The table file lives in a temporary folder removed at the end. Neither script changes.
3. **The engine.** Podman unless the person chose Docker (`--answer engine=docker`, rule 4; ADR-0579).
4. **The scheduler is the script's one task.** The setup pass carries `-InstallWatchdog` only when `wsl.py plan`'s
   watchdog line says the WSL task goes on (the WSL launch adapter merged and `auto_start` on, as `/agk:wsl` decides);
   the script then installs `autopilot.py on`'s task inside WSL when `[autopilot]` is on the default branch, else
   today's WSL watchdog task. Setup itself calls no `autopilot.py`, `conductor.py` or `schtasks`. Before the adapter
   change merges the `scheduler` row waits with the plan's line; for me only (personal mode) it is `skipped` and no
   task is added.
5. **The skill** gains one step that runs the WSL form after the plan's yes, with the same answers.

## Consequences

On Windows with WSL 2 chosen, `/agk:setup` sets the workforce up inside WSL with one plan and one yes besides the
sign-ins, and `/agk:wsl` stays callable on its own. Protected path classes changed: `scripts/agk/` (`setup.py`),
`tests/kit/` (`test_setup_wsl.py`), `skills/` (`skills/setup/SKILL.md`) and `agk.toml` (the `[[testing.map]]` entry for
`setup.py`).

## Residual

- 2026-11-17 (verify): the path has run only against a stub runtime in a Linux workspace standing in for WSL; it reports
  `Verified: (verify) run on Windows` until the owner runs it (due 2027-03-31).
- 2026-11-17: which machine of a team runs the conductor follows `/agk:wsl`'s watchdog line (`auto_start`) until build
  (h) chooses the roles of rule 14.
