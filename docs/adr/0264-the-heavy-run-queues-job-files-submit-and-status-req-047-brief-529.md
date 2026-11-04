# ADR-0264: The heavy-run queue's job files, submit and status (REQ-047, brief 529)

- Status: Proposed
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0262, SPEC-0040, ADR-0191, ADR-0231, ADR-0254
- Requirements: REQ-047

Protected classes: `scripts/agk/`, `kit/`, `agk.toml`, `tests/kit/`

## Context

SPEC-0040 (Approved on #526, ADR-0262) splits the heavy-run queue into the builds of its rule 16.
This is build (a): the setting of rule 1, the queue folder and job files of rules 2 and 3, the
order and the dedupe and replace cases of rule 5 for waiting jobs, and `status` with the estimate
of rule 7. No job runs in this build; the runner is build (b). The conductor reserved this ADR
number for brief #529 (the field note on #529).

## Decision

1. `scripts/agk/common.py` gains `queue_settings`, reading the `[locks]` table of `agk.toml`:
   `queue` and `queue_autostart` (booleans, false by default), `queue_idle_minutes` (a positive
   whole number, 10), `queue_order` (`"fifo"`, the default, or `"priority"`) and `queue_max_wait`
   (a positive whole number of minutes, 120). A value of another type or range, a key the table
   does not hold, or a `locks` value that is not a table is refused naming the setting
   (`setting: [locks] <key>`), never the value. The top-level lock settings do not move.
2. `scripts/agk/heavy_queue.py` is new and installed (`verbatim` in `kit/manifest.json`, sorted).
   It holds the queue folder `.agk-lock-NAME.queue/` beside the lock (`jobs/`, `results/`, `seq`,
   `runner.json`), every file written whole under a `.new` name and moved into place; the job
   file with every field of rule 3 and `seq`; the order of rule 5; dedupe and replace in place for
   waiting jobs; and the estimate of rule 7. A job is running when the runner has written its
   `started` time into it (build (b)); otherwise it waits.
3. `scripts/agk/lock.py` gains `submit --name NAME --session S [--kind K] [--brief N] -- <cmd...>`.
   It refuses a work tree with uncommitted changes to tracked files (exit 2, nothing written),
   reads the brief's single `Priority:` line (0 to 3) with one REST GET through `session.py`'s
   reader, and records `unknown`, never 0, for no brief, an unreadable brief, no line, several
   lines or a value outside 0 to 3. It has no option that sets the priority. It takes only the
   lock's mutex, never a slot, prints `queued <ticket> position <n> of <m> (head <sha12>)` and,
   with no live runner, `no runner; start one with lock.py runner --name heavy`, and returns.
4. With the setting on, `lock.py status` prints, after the lock's lines, `order: fifo` or
   `order: priority, max wait <m> min`, the running and waiting lines of rule 7 and `queue empty`;
   `status --ticket T` prints the one job's line, its result line or `unknown ticket` (exit 1).
   `status` reads the queue without the mutex (every file is moved into place whole) and changes
   no file.
5. `lock.py runner` exits 2 with `not built yet`. With the setting off, `submit`, `runner` and
   `status --ticket` exit 2 naming `setting: [locks] queue`, and `run` and `status` print and do
   what they do today; no queue folder is made.
6. `kit/templates/agk.toml`, `kit/templates/agk.adopt.toml` and this repository's `agk.toml`
   carry a commented `[locks]` table. This repository keeps the queue off.
7. The one `git` call of `lock.py` becomes a small helper used by `repo_root` and `submit`; no new
   scanner suppression is added, and the brief is read through the existing `session.gh` reader.

## Consequences

A builder on a machine with the setting on can queue a heavy run and see the queue and its
estimated start, but nothing runs it until build (b) lands; `submit` says so on every call while
no runner lives. Results come only from the runner, except the `replaced by <ticket>` result that
`submit` writes when a later head replaces a waiting job.

## Residual

- 2026-11-04: rule 3 lists no `kind` in a result, while rule 7 groups past results by `kind`; the
  estimate reads a `kind` field from each result, which the runner of build (b) must write
  (Q-529-2, due 2026-12-31).
- 2026-11-04: with `queue_autostart = true`, `submit` starts no runner in this build, because
  there is none to start (Q-529-1, due 2026-12-31).
