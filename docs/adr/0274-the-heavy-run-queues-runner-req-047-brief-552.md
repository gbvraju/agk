# ADR-0274: The heavy-run queue's runner: first in, first out, one job at a time, replace in place and cleanup (REQ-047, brief 552)

- Status: Accepted
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0262, ADR-0264, SPEC-0040, ADR-0191, ADR-0231, ADR-0254
- Requirements: REQ-047

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/` (the commented `[locks]` table of the two templates, amendment 117)

## Context

SPEC-0040 (Approved on #526, ADR-0262) splits the heavy-run queue into the builds of its rule 16.
Build (a) (#532, ADR-0264) wrote the job files, `submit` and `status`, and left `lock.py runner`
saying `not built yet`. This is build (b): the runner of rules 4 to 6, 8 and 14. The conductor
reserved this ADR number for brief #552 (the field note on #552).

## Decision

1. `lock.py runner --name NAME` works the queue with the setting on. It first claims
   `runner.json` under the lock's mutex: a live runner on this machine (or one on another
   machine whose last read is newer than `lock_stale_minutes`) makes it exit 0 with
   `runner already running (pid <n>, host <name>)`; a file whose process no longer runs is
   replaced with a line saying so. It then removes results and output files older than seven
   days (Q-S0040-9).
2. Each pass, under the mutex, the runner fails the jobs of rule 14 that are not its own and
   starts the next waiting jobs in the order of build (a) (`heavy_queue.waiting_order`) while a
   slot is free, up to `lock_slots`, marking each `started` with its runner's process and host.
   A job therefore starts only when every job ahead of it has started (Q-S0040-15), and a running
   job is never stopped, paused or replaced: nothing in the runner ends a job but the job itself
   or the runner being stopped.
3. Each job takes a slot with the lock's own `take` (the slot, ticket, stale and cleanup rules of
   ADR-0191, ADR-0231 and ADR-0254, at the default priority, Q-S0040-12), with the job's session,
   and its command gets `AGK_LOCK_SESSION`, `AGK_LOCK_TOKEN` and `AGK_LOCK_NAME`. It runs without a
   shell in a detached worktree of the job's head (`git worktree add --detach`) in a temporary
   folder outside every repository, made under `common.long_temp_dir()` so that a Windows 8.3
   short name never reaches a job (ADR-0257), at the job's folder inside it; the worktree is removed when
   the job ends, also when it fails. A head that is not in the repository fails with
   `failed (head not found)`.
4. The result is written whole beside the ticket, with `schema`, `ticket`, `head`, `kind` (Q-529-2,
   so the estimate of rule 7 groups by kind), `session`, `outcome` (`passed`, `failed (exit <n>)`,
   `failed (<reason>)`), `exit`, `output_sha256` and `output_bytes` of `results/<ticket>.out`,
   `queued_seconds`, `run_seconds`, `started`, `ended` and `record` (the path after `--record`, or
   null); then the job file is removed. When the result cannot be written, the runner writes
   `failed (the result cannot be written)` where it can and removes the job file either way, so
   no job stays `started` under a live runner, and goes on with the next job.
5. Rule 14: a running job whose runner no longer runs on this machine, a running job of another
   machine's runner started longer than `lock_stale_minutes` ago, a command that cannot be started,
   one ended by a signal and a job file that cannot be read each get `failed (<reason>)`, never
   `passed`. `status` changes no file (rule 7), so only the runner sweeps.
6. The runner stops with `runner idle for <m> min; stopped` when the queue has been empty for
   `queue_idle_minutes`. It decides to stop, by reading the queue again, and removes its
   `runner.json` in one mutex section; `submit` checks for a live runner under the same mutex as
   it adds the job, so a job is either seen by the runner or finds no runner and starts one. On an interrupt or a termination it stops
   its running commands, which then fail with the signal, and removes its file.
7. With `queue_autostart = true`, a `submit` that finds no live runner starts one (Q-529-1): the
   same Python running `lock.py runner --name NAME`, without a shell, detached
   (`start_new_session` on POSIX, a new process group and no console on Windows), its output
   appended to `runner.log` in the queue folder; it prints `runner started (pid <n>)`. Off, it
   prints the line of build (a) as before.
8. The runner's clock and sleep are parameters of `lock.runner`, so its tests use a fake clock and
   wait on no timer.
9. Amendment 117 to SPEC-0040 (`docs/runs/proposed-spec-amendments-117.md`, the owner's direction
   of 2026-11-05 in the conductor's field note on #552), applied to the spec in this pull request:
   `queue_order` defaults to `"priority"` (`"fifo"` stays), and at `submit` a job whose brief is
   named in a `Depends-on:` line of another open brief (label `agk-brief`) or open pull request is
   raised one level, recording `raised: unblocks #<n>[, #<m>]` in its `raised` field. A raise never
   reaches 0, which stays the red-default-branch brief's (Q-552-3, ruled on #555); `unknown` is not
   raised and a failed read raises nothing (Q-552-4). Such a job also records the numbers it
   unblocks in an `unblocks` field, and within one priority a job with that field goes before the
   other jobs, then by sequence number (the conductor's ruling on Q-552-3), so an unblocker
   already at priority 1 runs before an older job of priority 1 without reaching 0. A running job is still never pre-empted, overdue jobs
   still go first, and no gate is skipped. The kit's templates name the new default.

## Consequences

With the setting on, a queued heavy run now runs, and its result for its exact head appears in
the queue folder. A project that turns the queue on without `queue_order` now gets the priority
order, and its builds that others wait on run sooner; `queue_order = "fifo"` keeps the old order; `--queue` on `prepush.py` and the proof run is build (c).

## Residual

- 2026-11-04: whether a runtime ends an autostarted runner when a session's turn ends is not
  confirmed for every runtime `(verify)`; the owner-started runner stays the default (SPEC-0040
  residual, due 2026-12-31).
