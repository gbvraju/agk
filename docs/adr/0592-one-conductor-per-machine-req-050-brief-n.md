# ADR-0592: One machine runs at most one conductor; an idle one is replaced, never doubled

- Status: Accepted
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1409, brief #1355 (ADR-0568), brief #1237 (ADR-0525), brief #1387 (ADR-0585), brief #1386 (ADR-0584), plan #661
- Requirements: REQ-050

## Context

Brief #1409 records an adopted project in local mode on Windows where four extra conductors opened in one morning.
`conductor.py watchdog` (ADR-0525) and `watchdog --pass` (ADR-0585) start a conductor when the lease on the plan issue is
not held by a live conductor; a conductor renews the lease only as it works, so one that sits idle past the lease window
lets it lapse while its process is still alive, and the next pass starts another. `launch.py`'s one session per name
(ADR-0568 decision 3) never fires for conductors of different names, and the conductor jobs the watchdog started carried
no job kind in their record. On Windows `autopilot.py status` did not read the process list at all.

## Decision

1. **One conductor per machine, read from the machine.** Before any conductor start, `watchdog`, `watchdog --pass` and
   `launch.py role --role conductor` read `launch.live_conductors`: this machine's job records (`agk-<session>` beside
   the checkout) of kind `conductor`, or with no kind and `conductor` in the session name (records written before this
   build), whose process is there and has no newer exit file, and each `claude ... --agent conductor` process outside
   every recorded tree (a person's own). The process list is `ps -A -o pid=,ppid=,args=` on POSIX and `Get-CimInstance
   Win32_Process` with its command lines on Windows (`launch.command_lines`, which `autopilot.py status` now uses too).
   One alive: nothing starts, `watchdog: conductor <name> is running on this machine; nothing started`, and
   `launch.py role` prints `stuck: conductor <session> not started (conductor <name> is running on this machine)`. The
   watchdog's conductor starts now hand the adapter `AGK_JOB_KIND=conductor`, so their records carry the kind. Both
   adapters refuse a job of kind `conductor` while such a record names a live process (exit 3). The lease stays the rule
   between machines and is unchanged.
2. **An idle conductor is replaced, not doubled.** When the pass would start a conductor (the lease lapsed, or the last
   job no longer renews it) and the one live conductor has a record, it is read by ADR-0568's signs: started less than
   `[flow] idle_minutes` ago, a transcript write, a commit, a file change or a fresh lock is work, and two reads of its
   process tree 5 to 30 minutes apart must agree. A working one is `left (working)`; an idle one is stopped (its record's
   process tree only, its worktree clean and pushed) and one starts in its place, at most once an hour (kept in
   `<git dir>/agk/builders.json` under `conductor`): `idle -> stopped; one starts in its place`, else
   `idle -> held (stopped within the hour|unpushed work|the process did not stop)`. A conductor without a record, or two
   or more alive, are never stopped.
3. **A conductor that is not the lease holder ends itself.** The watchdog's, the pass's and `launch.py role`'s conductor
   prompts say: at each turn run `lease --show`; when it names another holder, release nothing, print `close-tab: <name>
   is not the lease holder; this session ends` and end; when the pass finds nothing to do, `lease --release <name>` and
   end. The pass's job prompt keeps "do not release it" while work remains.
4. **Extras already running are named once.** `conductor.py sweep`, and so `agk status`, prints one line
   `NEEDS-YOU: <n> conductors on this machine: keep <lease holder>, close <names>; stop with: <command>`, the command
   `taskkill /T /F /PID <pid> ...` on Windows and `pkill -TERM -P <pids>; kill <pids>` elsewhere. The kit stops only what
   decision 2 stops.
5. **Memory before a start.** No conductor starts and no builder restarts below `[flow] min_free_memory_mb`, read at
   that moment (`watchdog: conductor not started: free memory below [flow] min_free_memory_mb`; a builder is
   `held (setting: [flow] min_free_memory_mb)`); the next pass tries again.
6. **Every mode.** Local mode takes all of it. CI mode keeps its one hosted job by the workflow's concurrency group; no
   workflow, ruleset or required check changes. Personal mode has no conductor and is unchanged.

Protected path classes changed: `scripts/agk/` (`conductor.py`, `launch.py`, `autopilot.py`), `kit/`
(`kit/templates/start-session-windows.ps1`, `kit/templates/start-session-local.sh`), `tests/kit/` (`test_one_conductor_per_machine.py`), `agk.toml` (the `[[testing.map]]` entries),
`docs/adr/` (this file) and `changelog.d/` (one fragment). `scripts/start-session-windows.ps1` and the getting-started
guide's block stay the template's code.

## Consequences

A lapsed lease beside an idle conductor no longer starts a second one: twenty passes leave exactly one on the machine,
and extras that already run are named for the person to close.

## Residual

- 2026-11-16 (verify): the Windows process list, the adapter's PowerShell check and `taskkill` were not run on Windows by
  the session that wrote this.
- 2026-11-16: a conductor a person types as `claude --agent conductor` reads only its role file, which this build does
  not change, so decision 3 reaches it only through `launch.py role` (Q-1409-1) (due 2027-03-31).
