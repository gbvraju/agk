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
   with a live process is `idle` when the builder owes the next move and has not made it for `[flow] silent_minutes`
   (30 by default): with a pull request, the newest `Verdict:`, `Correction:`, `Answer:` or `Maintainer answer:` is
   newer than the builder's newest `Report:`, `Progress:` or `Question:` and its head push, and older than
   `silent_minutes`; without one, nothing was posted on the brief or pushed since the take or the record for
   `silent_minutes`. A builder whose newest line is its own `Report:` or `Question:` waits on someone else and is `live`.
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
   path. To end an `idle` session the watchdog stops the process tree the record names only when its worktree is clean
   and its head is on its upstream; otherwise it starts nothing and prints `held (unpushed work)`.
4. **The conductor's guard** allows exactly `gh api rate_limit` (with one `--jq <filter>`) and
   `python|python3 scripts/agk/lock.py status [--name <name>]`, the project's own file; every other `lock.py`
   subcommand and every other `rate_limit` form (a method flag, a field) stays denied.
5. **By mode.** Local mode takes all of it, each machine's watchdog keeping its own sessions. CI mode (cloud builders as
   scheduled tasks) keeps its launcher and gains only decision 4; no workflow, ruleset or required check changes.
   Personal mode has no conductor and no watchdog and is unchanged.

## Consequences

A builder that ends or goes idle while it owes the next move is back within one watchdog pass after `silent_minutes`,
never two sessions of one name run, and the conductor can read the rate limit and the heavy lock. Protected path classes
changed: `scripts/agk/` (`conductor.py`, `launch.py`), `.claude/` (`.claude/hooks/conductor_guard.py`), `kit/`
(`kit/templates/start-session-windows.ps1`, `kit/templates/start-session-local.sh`), `tests/kit/`
(`test_watchdog_builders.py`, `test_conductor_guard_commands.py`) and `agk.toml` (the new test file in the
`[[testing.map]]` entries of `conductor.py` and `launch.py`, and the guard's test in that of `lock.py`).

## Residual

- 2026-11-15 (verify): the record names the wrapper's process id, not the runtime's own; whether the runtime can be read
  as a separate process on both platforms was not run by the session that wrote this.
- 2026-11-15 (verify): a process id can be reused after its process ends; the record's start time is kept for a later
  check of it, and the liveness test reads the id alone.
