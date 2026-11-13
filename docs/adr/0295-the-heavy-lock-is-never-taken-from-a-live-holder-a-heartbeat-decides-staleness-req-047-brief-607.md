# ADR-0295: The heavy lock is never taken from a live holder; a heartbeat, not age, decides staleness (REQ-047, brief 607)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0191, ADR-0231, ADR-0264, ADR-0274
- Requirements: REQ-047

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #607 (tracker #606, item 1). ADR-0191 decision 3, kept by ADR-0231 decision 1, clears a lock "older than
`lock_stale_minutes`" (120 by default) even while its process still runs. In a pilot a 62-minute suite plus a 6-hour machine
sleep let a second builder take the lock and run its suite alongside the first, which broke test isolation and wasted both runs.
The queue runner of SPEC-0040 (ADR-0264, ADR-0274) takes its slots through the same `take`, so it had the same fault. This ADR
changes that one decision. The tests were written first (`tests/kit/test_lock_heartbeat.py` new; the two age tests of
`tests/kit/test_lock.py` and `tests/kit/test_lock_slots.py` changed to the new rule): 21 failed, 50 passed at the first
checkpoint.

## Decision

1. **A live holder here is never cleared (answers 1 and 3).** A lock whose owner file names this host and a readable process id
   (`pid` of `lock.py`, or `child` of its command) is judged by those process ids alone: it is kept while either runs, whatever
   its age and however long its heartbeat has stopped (a machine that slept), and cleared with `its process no longer runs` when
   neither does, as before.
2. **A heartbeat decides everywhere else (answer 2).** The holder writes `beat` (UTC, the format of `started`) into `owner.json`
   when it takes the lock and then every 60 seconds while its command runs, from a daemon thread, under the lock's mutex and only
   while the lock still carries its token. A lock of another host, or of this host with no readable process id, is stale only
   when its heartbeat is older than `lock_stale_minutes`; an owner file without `beat` (an older kit) has its `started` as its
   last heartbeat. The clearing line says `its heartbeat from host <host> is older than <n> min, setting: lock_stale_minutes`. A
   folder without an owner file is still cleared by its own age.
3. **Status (answer 4).** `status` and the waiting lines print the holder, its age and `heartbeat <m> min ago` (or
   `no heartbeat`); every cleared lock prints why. `lock_cleanup` still runs only after a dead run (Q-426-2): a lock cleared for a
   stale heartbeat may belong to a run that still goes on.
4. **The queue runner (answer 5).** A job's slot carries the same `beat`, written from the runner's clock, and is judged by the
   same rules, so a slot of a live runner is never cleared by age. The runner file's own `read` time and the job sweep of SPEC-0040
   rule 14 are unchanged (Q-607-1).
5. Nothing else changes: the setting, its default and its refusal, the slots, tickets, priorities, the mutex and the token.

## Consequences

A heavy run longer than `lock_stale_minutes`, or one paused by a sleeping machine, keeps the lock on its own machine, so two
suites never run together there. A holder that hangs while its process lives keeps the lock until a person ends that process;
that is the price of never taking the lock from a live run. On a shared `lock_dir`, a remote holder that is alive but whose machine
sleeps longer than `lock_stale_minutes` loses its lock, as before, but only by its heartbeat, never by the age of a lock whose
heartbeat is fresh.

## Residual

- Q-607-1: the job sweep of SPEC-0040 rule 14 still fails a running job of another machine's runner by its job file's age; moving
  it to the runner's `read` time would change an Approved spec's text and needs an amendment number.
