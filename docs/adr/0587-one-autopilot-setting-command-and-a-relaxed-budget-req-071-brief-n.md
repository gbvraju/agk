# ADR-0587: One autopilot setting, one command and a cost budget relaxed by default

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1390, SPEC-0064 rules 7, 8, 9, 11 and 16 (d), brief #1386 (ADR-0584), brief #1387 (ADR-0585), brief #1283 (ADR-0544), plan #661
- Requirements: REQ-071

## Context

SPEC-0064 (Approved) runs every AI session as a short job that one supervisor per machine starts. Build (d) gives
the project one setting to turn it on (rule 7), a cost budget that is built but relaxed by default (rule 8), one
command that installs the scheduler entry and checks the machine (rules 7 and 11), and the `retry` of rule 9. Today
`[flow] auto_start`, `launch_adapter`, `[capacity]` and a hand-installed watchdog task are four separate settings,
and no table, command or budget of the autopilot exists; `[autopilot] show_jobs` (build (e)) is its only key.

## Decision

1. **The table.** `config.autopilot_settings` reads `[autopilot]`: `mode` (`off`, `assist` or `on`; `assist` when the
   table names none, Q-S0064-2), `interval_minutes` (a whole number of 1 or more, 5 when unset), `daily_budget`
   (absent or `"off"`: no limit; else a whole number of tokens of 1 or more) and `show_jobs` (true or false). An unknown
   key or another value is refused naming `setting: autopilot.<key>`, never the value. With no table, `mode` is None:
   today's `auto_start`, `launch_adapter` and `[capacity]` decide, for one release, and `legacy` names those set.
2. **The doctor.** `doctor.py` warns `autopilot-settings`, naming each of `auto_start`, `launch_adapter` and
   `[capacity]` that is set (read for one release while `[autopilot]` is absent; not read once it is set), never a
   value; its fix names the watchdog's scheduler task too.
3. **What a start asks.** `autopilot.mode_allows(mode, kind, owner_yes)`: `off` allows nothing, `assist` the
   `review`, `steward` and `conductor` jobs and a `build` or `fix` job only on the owner's recorded yes (Q-S0064-8),
   `on` all, None all (today's settings decide). `autopilot.job_allowed(root, kind, now)` adds the budget: with a
   figure set and not relaxed, a `build` or `fix` job does not start when the UTC day's tokens (as `metrics.py --cost
   --day` counts this clone's records) reach it, or when they cannot be read (Q-S0064-6); `review`, `steward` and
   `conductor` jobs are never stopped by it. `budget_note` is true once per UTC day, so the owner is told once.
4. **The command.** `autopilot.py on` installs one scheduler entry, a crontab line tagged `# agk-autopilot` (any
   older tagged line replaced, every other line kept) or the Windows task `agk-autopilot` (`schtasks /Create ... /F`),
   every `interval_minutes`, running `git fetch -q origin` then `conductor.py watchdog --pass`, runs the machine
   checks and prints the `[autopilot] mode = "on"` change as one the person makes by pull request with its ADR; `off`
   removes the entry and prints `mode = "off"` the same way. Neither edits a tracked file.
5. **The machine checks.** `ok:` or `warn:` lines, each warning naming its setting: the entry runs while nobody is
   signed in (cron: yes; Windows: a warning, `(verify)`), sleep is off (Linux: `systemctl is-enabled sleep.target`
   reads `masked`; elsewhere a warning, `(verify: per OS)`), free memory holds one builder
   (`capacity.builder_memory_gb`, by `conductor.memory_line`), `gh auth status` succeeds (`gh auth login`), and
   `[flow] launch_adapter` is set and its program is found (`flow.launch_adapter`). The checks only read; no power
   setting is ever changed.
6. **The relaxation and the retry.** `budget off` relaxes the budget until `budget on`; `budget off --today` for the
   rest of the UTC day; `retry N` records pull request N with the time for rule 9's back-off to lift its hold. Each is
   kept in `<git dir>/agk/autopilot.json`, never a tracked file, and `status` begins with the mode line (with `off`:
   the pass command a person would run) and `budget: <figure|off> [(relaxed ...)]; spend <day>: <n tokens|unknown>`.

Protected path classes changed: `scripts/agk/` (`config.py`, `autopilot.py`, `doctor.py`), `kit/`
(`templates/agk.toml`), `tests/kit/` (`test_autopilot_settings.py`, `test_doctor.py`,
`test_delivery_declaration.py`), `agk.toml` (the `[[testing.map]]` entries), `docs/adr/` (this file) and
`changelog.d/` (one fragment).

## Consequences

A project turns the autopilot on with one setting and one command, and a spend limit exists but limits nothing until
the owner sets a figure. The supervisor's own pass reads `mode_allows` and `job_allowed` from build (f) (the brief:
"the setting is read by build (f)'s launcher"); until then the pass starts jobs as build (b) does, and the old
settings stay the ones it reads. Rule 9's back-off, which reads the `retry` marks, is build (c)'s.

## Residual

- 2026-11-16: the scheduler entry runs every `interval_minutes`, not every minute while an event is pending (rule 2);
  the faster cadence needs the pass to know a pending event, build (f)'s (Q-1390-1) (due 2027-03-31).
- 2026-11-16: the sleep and signed-out checks read Linux only; Windows and macOS warn `(verify: per OS)` (due
  2027-03-31).
- 2026-11-16: the spend counts only this clone's local session records (SPEC-0064 Residual) (due 2027-03-31).
