# ADR-0568: The watchdog keeps builders alive, one session per name

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: ADR-0525, ADR-0554, ADR-0322, ADR-0563, brief #1355, plan #661
- Requirements: REQ-050

## Context

Brief #1355 records one day of an adopted project in local mode: builders ended or sat idle with nothing to wake them, a
restart opened a second session under a name already running, and the conductor's guard refused the two read-only checks
(`gh api rate_limit`, `lock.py status`) that would have explained a stuck claim. `conductor.py watchdog` (ADR-0525) and
`watchdog --pass` (ADR-0554) start only a conductor; both adapters write `<worktree>/.agk-session-exit` when a session
ends, and nothing records the process of a session that is still open.

## Decision

1. **A process record.** Both adapters write `<worktree>/.agk-session-pid` before the session's first turn, kept out of
   git as the exit file is: `session=`, `pid=` (the adapter's wrapper process, whose process tree holds the runtime),
   `started_utc=` and `brief=`. `launch.py` reads a session as `ended` (no live process, or an exit file whose
   `ended_utc` is not older than the record's `started_utc`), `live` or `idle` (decision 2).
2. **The watchdog checks builders.** `watchdog` and `watchdog --pass`, after their conductor checks, read each live take
   (`session.live_takes`) of an open `agk-brief` issue whose session has a record in this machine's worktrees
   (`<parent of the checkout>/agk-<session>`); a session without a record is another machine's and is left. A session
   with a live process is `idle` only when every sign of work has been quiet for `[flow] idle_minutes` (60 by default,
   never below `silent_minutes`; brief #1355's correction of answer 1): the builder owes the next move and has not made
   it (with a pull request, the newest `Verdict:`, `Correction:`, `Answer:` or `Maintainer answer:` is newer than the
   builder's newest `Report:`, `Progress:` or `Question:` and its head push, and older than `idle_minutes`; without one,
   nothing was posted on the brief or pushed since the take or the record for `idle_minutes`); its runtime transcript
   (`projects/<the worktree's path, each character other than a letter or digit a dash>` under `CLAUDE_CONFIG_DIR` or
   `~/.claude`) was not written, there is no local commit and no file change in its worktree (the record and the exit
   file aside) within `idle_minutes`; no `lock.py` lock whose `session` is the builder's name, or whose holder is a
   process of its tree, has a heartbeat younger than 5 minutes (a lock folder that cannot be read counts as held); and
   two reads of its process tree (`ps -A -o pid=,ppid=,time=`, on Windows `Get-CimInstance Win32_Process`), one per
   pass, 5 to 30 minutes apart, show the same processes with the same whole CPU seconds, so a child that started,
   ended or used CPU between them is work. Any one sign makes the builder `live`; a heavy step of any length is never
   stopped. Until the two reads agree, or when the table cannot be read, the line is `idle -> held (working)`, kept as
   the first read in `builders.json` and never a `NEEDS-YOU:` line. A builder whose newest line is its own `Report:` or
   `Question:` waits on someone else and is `live`.
   An `ended` builder is restarted through `launch.py prompts --resume`'s adapter call under the same name; an `idle` one
   is stopped first (decision 3) and then restarted; a `live` one is left. One line per session:
   `watchdog: builder <name> #<brief> ended|idle|live -> restarted|left|held (<reason>)`; it posts nothing. A builder
   whose pull request carries `agk:parked` (or a `Parked-by:` line not undone), or whose newest `Report:` hands over
   or reports over cap, is never restarted. A restart counts against `[flow] max_builders` and the free memory against
   `builder_memory_gb`, as a conductor start does. At most one restart per session per hour, kept in
   `<git dir>/agk/builders.json`; a second need within the hour prints `held (restarted within the hour)`, a failed adapter call
   `held (the adapter failed)` and a process that does not stop `held (the process did not stop)`, and the next
   `conductor.py sweep` prints `NEEDS-YOU: builder <name> #<brief> held (<reason>)` for each held session in that file.
3. **One session per name.** Before any adapter call, `launch.py` refuses a session whose record shows a live process
   (`launch: not started: session <name> is still running (one session per name)`), naming the session and never a
   path. To end an `idle` session the watchdog stops the process tree the record names only when its worktree is clean,
   its head is on its upstream and the two reads of decision 2 agree; otherwise it starts nothing and prints
   `held (unpushed work)` or `held (working)`.
4. **The conductor's guard** allows exactly `gh api rate_limit` (with one `--jq <filter>`) and
   `python|python3 scripts/agk/lock.py status [--name <name>]`, the project's own file; every other `lock.py`
   subcommand and every other `rate_limit` form (a method flag, a field) stays denied.
5. **By mode.** Local mode takes all of it, each machine's watchdog keeping its own sessions. CI mode (cloud builders as
   scheduled tasks) keeps its launcher and gains only decision 4; no workflow, ruleset or required check changes.
   Personal mode has no conductor and no watchdog and is unchanged.

## Consequences

A builder that ends is back within one watchdog pass; one that goes idle while it owes the next move is back within two
passes after `idle_minutes` with every sign of work quiet,
never two sessions of one name run, and the conductor can read the rate limit and the heavy lock. Protected path classes
changed: `scripts/agk/` (`conductor.py`, `launch.py`, `config.py` for the new `idle_minutes` key), `.claude/` (`.claude/hooks/conductor_guard.py`), `kit/`
(`kit/templates/start-session-windows.ps1`, `kit/templates/start-session-local.sh`), `tests/kit/`
(`test_watchdog_builders.py`, `test_conductor_guard_commands.py`) and `agk.toml` (the new test file in the
`[[testing.map]]` entries of `conductor.py` and `launch.py`, and the guard's test in that of `lock.py`).

## Residual

- 2026-11-15 (verify): the record names the wrapper's process id, not the runtime's own; whether the runtime can be read
  as a separate process on both platforms was not run by the session that wrote this.
- 2026-11-15 (verify): a process id can be reused after its process ends; the record's start time is kept for a later
  check of it, and the liveness test reads the id alone.
- 2026-11-15 (verify): the runtime's transcript folder and its naming, and whether an idle runtime's own process uses
  whole CPU seconds over 5 minutes, were not run by the session that wrote this; a runtime that ticks a second of CPU
  while it waits is read as working and is never stopped, the safe side.
