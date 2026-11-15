# ADR-0577: One command moves a Windows workforce into WSL 2 and back

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: ADR-0525, ADR-0554, ADR-0568, ADR-0572, brief #1376, plan #661
- Requirements: REQ-050

## Context

Brief #1376 records one day of an adopted project in local mode on native Windows: every failure was Windows-only
(console encoding, CRLF line endings, PowerShell lines refused by the data guard, terminal tabs left open). WSL 2 with
the project on its own disk runs file-heavy work at near-Linux speed, and Podman on Windows already runs inside a WSL 2
machine. The co-owner wrote a host script that moves one project into WSL; the owner asked for one command that does
it for every person, without manual steps. `launch_adapter` is read from `agk.toml` in the checkout and on the default
branch alike (ADR-0525), so the switch of adapter is a protected change by pull request, and the watchdog task moves
only after that pull request merges.

## Decision

1. **A plugin skill, `/agk:wsl`** (`skills/wsl/SKILL.md`), run from Claude Code on the Windows host, with three forms:
   `/agk:wsl` (set up or resume), `/agk:wsl status` and `/agk:wsl back`. It reads the project's remote, the git name
   and email and the machine's memory itself, asks only for what it cannot read (a company certificate, when a download
   fails on one), shows a plan of five lines or fewer and runs it on the person's yes.
2. **One kit script does the machine work,** `scripts/agk/wsl_setup.ps1`, run from the plugin root and never installed
   into a project, from the co-owner's script. Every step is one `Invoke-Step` with a `-Done` check that runs first and
   skips what is done, so a stopped run resumes. It ends with one table of steps marked `done`, `skipped`, `waiting` or
   `failed`, and `-Json` prints that table as JSON (`steps` of `step`, `result`, `note`; `pending`; `project_dir`;
   `distro`), which the skill reads. It never asks for, stores or prints a password or token; the GitHub and Claude
   sign-ins are the normal browser sign-ins.
3. **A kit helper, `scripts/agk/wsl.py`**, run from the plugin root, prints the plan (`plan`), the status lines
   (`status`), writes the adapter change with its ADR and prints the body (`pr --to wsl|windows`), and opens the draft
   pull request by REST (`open`). It reads the default branch's `agk.toml` with one GET through `gh`, posts only the one
   pull request, and never merges.
4. **The protected step goes by pull request:** after the machine is ready, the skill prepares one pull request that
   sets `launch_adapter = "bash scripts/start-session-local.sh"` in the `[flow]` table with the project's own ADR, and
   the person commits, runs `prepush.py --record` in WSL, pushes and opens it with `wsl.py open`, as printed: SPEC-0005
   rule 8 keeps a command from committing or pushing (Q-1376-1). On the next `/agk:wsl` after the merge the script installs the WSL
   watchdog task and disables, never deletes, the Windows one (`AGK conductor watchdog`). `/agk:wsl back` makes the
   reverse pull request and re-enables the Windows task. Personal mode has no conductor and gets no watchdog step.
5. **The doctor knows WSL:** inside WSL with the project under `/mnt/`, `doctor.py` prints
   `wsl: the project is on a Windows drive; move it inside WSL (/agk:wsl)`; on Windows with the Windows adapter set and
   `wsl` on the PATH it prints one line naming `/agk:wsl`. Both are information lines, never a failure.
6. **The guide** (`docs/guides/local-mode.md`) gains the section "Running the workforce in WSL 2".

## Consequences

A person on Windows moves the workforce into WSL with one command and returns with another; the protected adapter
change still comes as a reviewed pull request, and nothing is merged by the kit. Protected path classes changed:
`skills/` (`skills/wsl/SKILL.md`), `scripts/agk/` (`wsl_setup.ps1`, `wsl.py`, `doctor.py`), `tests/kit/`
(`test_wsl_setup.py`), `tests/kit_dev/` (`test_distribution.py` lists the new command, `test_kit_manifest.py` the two
kit-only files) and `agk.toml` (the new test in the `[[testing.map]]` entries). No workflow, ruleset or required
check changes; CI mode and cloud sessions, which already run on Linux, are unchanged.

## Residual

- 2026-11-15 (verify): `wsl_setup.ps1` has not run on Windows; the pull request reports `Verified: (verify) run on
  Windows` until the owner runs it once.
- 2026-11-15 (verify): marking the project folder trusted in `~/.claude.json` (`hasTrustDialogAccepted`) is the
  co-owner's reading of the runtime's file, not confirmed from its documentation.
- 2026-11-15 (verify): screenshots that `design_compare.py` compares are captured again once on Linux; fonts differ.
