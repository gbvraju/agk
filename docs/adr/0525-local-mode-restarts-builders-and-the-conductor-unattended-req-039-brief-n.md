# ADR-0525: Local mode restarts builders and the conductor unattended

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0182, ADR-0190, ADR-0298, ADR-0368, ADR-0409, ADR-0439, ADR-0453, ADR-0477, brief #1237, plan #661
- Requirements: REQ-039

## Context

On a customer project in local mode (a 4-core Windows cloud PC, Actions disabled by policy), the conductor's sweep finds a
builder silent for 45 minutes or labelled `agk:handover`, but it can restart one only through `[flow] launch_adapter`, and
the kit shipped no adapter: the Windows Terminal adapter was a code example in `docs/guides/getting-started.md` that each
project copied and tested by hand. Nothing restarted the conductor itself in local mode: the cloud launcher tasks
(ADR-0477) need Actions and cloud sessions, so a conductor killed by memory pressure stayed dead until a person looked.

## Decision

1. The kit ships two launch adapters as templates (`kit/manifest.json`, `templates` and `adopt.templates`), written once by
   `init`, `adopt` or `upgrade` when absent and then the project's own: `scripts/start-session-windows.ps1` from
   `kit/templates/start-session-windows.ps1`, the guide's Windows Terminal example, and its POSIX twin
   `scripts/start-session-local.sh` from `kit/templates/start-session-local.sh`: a worktree `../agk-<session>` per session,
   `claude` with the prompt in a GNOME Terminal tab when a desktop is there and otherwise in the background (`claude -p`,
   output in `<worktree>/.agk-session.log`), and the exit file `<worktree>/.agk-session-exit`, both kept out of git by the
   worktree's exclude file. A first start is the guide's, unchanged in behaviour (`git worktree add`). A restart finds the
   folder of the session that ended or crashed (Q-1237-1, answered on the fix list): both adapters then reuse it when it is
   a clean worktree of the repository (fetch, then the default branch checked out detached), as this repository's own
   adapter does (ADR-0439), and otherwise start nothing, exiting 2 with one line naming the folder. The guide's block is
   the Windows template, byte for byte, and a test keeps them equal; another keeps the template's code equal to this
   repository's own script, which differ only in comments.
2. `doctor.py` gains the information line `launch-adapter` (severity `warn`, never a failure of the run): while
   `auto_start` is on and `launch_adapter` is unset, or a word of it that names a file of the project (a path or a script
   suffix) is missing, it names the kit's adapter for the platform and the `launch_adapter` line to set. The project's own
   command is never printed.
3. `python3 scripts/agk/conductor.py watchdog [--session NAME] [--install]` is one pass, never a loop. It starts nothing while
   the default branch is paused, or unless `auto_start` and `launch_adapter` are set in the checkout and on
   `origin/<default branch>` alike (as for the review pass's starts, ADR-0190), or while the lease is off. While a live
   conductor holds the lease (ADR-0368) it prints the holder and starts nothing; the lease already keeps two conductors from
   running. When the lease is free or expired it calls the adapter once, split into words and without a shell, with a
   conductor prompt on standard input and `AGK_SESSION` (`conductor-local` by default), `AGK_ROLE=conductor` and
   `AGK_TIER=strongest`; the started conductor takes the lease under that name. It posts nothing. `--install` reads and runs
   nothing: it prints the one scheduler line for the platform, `schtasks /Create /SC MINUTE /MO 30 ...` on Windows and a
   crontab line elsewhere, each a `git fetch` and then the pass; the person runs it.
4. Before a start the watchdog prints the machine's free memory (`common.available_memory`) against `builder_memory_gb`, the
   smaller of the `[flow]` and `[capacity]` values as the plan reads it (ADR-0409), and when free memory is below one
   builder it starts nothing and says so, so a restart never makes a memory hit worse. Memory that cannot be read is
   printed as `unknown` and the start goes ahead, as `launch.py`'s floor does (ADR-0298).
5. `docs/guides/local-mode.md` gains "Running unattended": the adapter, `auto_start`, `[capacity] profile = "auto"` with
   `builder_memory_gb`, and the watchdog line, in that order; `docs/guides/getting-started.md`, `docs/guides/reference.md`
   and the comment of `kit/templates/agk.toml` say the kit now installs the two adapters.

## Consequences

A project in local mode sets the adapter, `auto_start`, its capacity and one scheduler line once, and a conductor that dies
comes back within 30 minutes; the conductor then restarts handed-over and silent builders through the same adapter. A
machine short of memory waits instead of starting a session that would make it worse. The conductor's guard is unchanged:
the watchdog is a command of the person's scheduler, not of the conductor's session. CI mode keeps the cloud launcher; no
workflow changes.
The decision of ADR-0439 and of the guide's tests that the kit installs no adapter is changed by this one: the two tests that
said so (`tests/kit_dev/test_windows_launcher.py`, `tests/kit/test_guide_windows_adapter.py`) now say the kit installs it as
a template, and this repository keeps its own `scripts/start-session-windows.ps1`, which a template never overwrites.
Protected path classes changed: `scripts/agk/` (`conductor.py`, `doctor.py`), `kit/` (`manifest.json`, the two new adapter
templates and the comment of `templates/agk.toml`), `tests/kit/` (`test_conductor_watchdog.py`, new; `test_doctor.py` and
`test_delivery_declaration.py`, their counts; `test_guide_windows_adapter.py`), `tests/kit_dev/` (`test_windows_launcher.py`) and `docs/adr/` (this file).

## Residual

- 2026-11-14: the adapters were run only with test doubles (the POSIX one with a `claude` double and no desktop); neither a
  Windows Terminal tab, a GNOME Terminal tab, `schtasks` nor `cron` was run by the session that wrote this `(verify)`.
