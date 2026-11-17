# ADR-0606: Inside WSL the one autopilot scheduler is a Windows task that runs signed out

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1448, ADR-0587 (the autopilot command), ADR-0577 (`/agk:wsl`), plan #661
- Requirements: REQ-071

## Context

ADR-0587 decision 4 has `autopilot.py on` write a crontab line on every system but Windows. Inside WSL there is no
cron (`wsl_setup.ps1` installs none) and WSL stops an idle distro, so the line would rarely fire `(verify: the WSL idle
shutdown)`. ADR-0577's `/agk:wsl` registers its own task `AGK conductor watchdog (WSL)` with no principal, which runs
only while the person is signed in, and doctor's `autopilot-settings` fix points at `autopilot.py on`: two schedulers,
and the recommended one does not run in WSL.

## Decision

1. **One scheduler in WSL.** On Linux whose `/proc/version` names Microsoft (as `doctor.inside_wsl` reads it),
   `autopilot.py on` writes no crontab line: it prints and runs one `schtasks.exe /Create` through Windows interop for
   the task `agk-autopilot (WSL)`, running `wsl.exe -d <WSL_DISTRO_NAME> --cd <clone> -- bash -lc "git fetch -q origin
   && python3 scripts/agk/conductor.py watchdog --pass"` every `[autopilot] interval_minutes`, replaced by name (`/F`)
   on a second `on`. `off` runs `schtasks.exe /Delete` of that name and nothing else.
2. **Signed out.** The call names the person's own account (`whoami.exe`) with `/RP *`, so Windows asks for the stored
   sign-in on the person's own terminal; the script never reads, asks for or stores it `(verify: on Windows)`. When it
   fails (the person declines), the task is registered without an account, signed-in only, and `on` prints `warn: runs
   only while you are signed in (setting: the task's sign-in option)`.
3. **Interop off.** With `[interop] enabled` false in `/etc/wsl.conf`, `on` and `off` refuse with one line naming that
   setting and write nothing.
4. **`/agk:wsl` hands over.** When `agk.toml` of `origin/HEAD` has an `[autopilot]` table, its watchdog step runs
   `python3 scripts/agk/autopilot.py on` inside WSL on the person's console and disables (never deletes) `AGK conductor
   watchdog (WSL)` and the Windows watchdog task; without the table it keeps ADR-0577's task.
5. **Unchanged.** Native Windows (ADR-0587's `agk-autopilot`) and native Linux (the crontab line); hosted mode uses no
   machine scheduler; personal mode installs none.

Protected path classes changed: `scripts/agk/` (`autopilot.py`, `wsl_setup.ps1`), `tests/kit/`
(`test_autopilot_wsl.py`, `test_autopilot_settings.py`), `agk.toml` (the `[[testing.map]]` entries), `docs/adr/` (this
file) and `changelog.d/` (one fragment).

## Consequences

A WSL workforce has one scheduler that survives a sign-out, and doctor's advice to use `autopilot.py on` now holds
inside WSL. The behaviour on Windows is proven only by doubles here; the owner's run on Windows confirms it.

## Residual

- 2026-11-17: `/RP *` prompting, the signed-in-only default without `/RU`, and interop's quoting of `/TR` are read from
  the `schtasks` documentation, not run on Windows `(verify: on Windows)` (due 2027-03-31).
- 2026-11-17: a clone path with spaces is not quoted inside `/TR` (WSL clones live under `/home/<user>/work`) (due
  2027-03-31).
