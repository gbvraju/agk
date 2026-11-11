# ADR-0441: Auto test workers are capped by free memory

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: brief #1032, plan #661, SPEC-0044 rule 4, ADR-0305 (brief #631), ADR-0422 (brief #980), ADR-0436 (brief #1021)
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On 2026-11-11 at 03:16 IST the owner's laptop ran out of memory during a full prepush. `impact.workers_setting`
turned `[testing] workers = "auto"` into the CPU count alone, and since brief #1021 (#1024) the laptop has
pytest-xdist, so the full run started one test process per CPU thread, each loading the whole suite, with three
sessions open and about 5 GB free. `common.available_memory()` already read the free memory on Linux, macOS and
Windows, and nothing used it for the workers. The owner's word, 2026-11-11 08:46 IST: "File it".

## Decision

1. `"auto"` is the smaller of the CPU count and the free memory in MB over `[testing] worker_memory_mb`, at least 1.
   When the free memory cannot be read it is the CPU count, as before. The memory is read once per process, so every
   run's `-n` and the printed line give one number.
2. `[testing] worker_memory_mb` is optional, a whole number of at least 100, 500 by default; any other value is
   refused naming `testing.worker_memory_mb`.
3. The environment variable `AGK_TEST_WORKERS`, a whole number of at least 1, overrides the result for one machine
   wherever the `[testing]` table is set, whatever `workers` says; any other value is refused naming the variable,
   never the value. Without the table the run stays single, as before.
4. Prepush prints one line when it starts a run in workers: `tests: <n> workers (cpu <c>, free memory <m> MB at
   <w> MB each)` for `"auto"`, `(cpu <c>, free memory unknown)` when the memory cannot be read,
   `(AGK_TEST_WORKERS)` for the variable and `(setting: testing.workers)` for a number as written.
5. A numeric `workers` is used as written.

## Consequences

Every project on `workers = "auto"` gets the cap with the next kit; a numeric setting is unchanged. CI runners have
ample memory, so their worker count stays the CPU count. A laptop running several sessions starts fewer workers and a
full run may take longer there; a person can set `AGK_TEST_WORKERS` for that machine or `worker_memory_mb` for the
project. Free memory is read once, at the start of the run: memory taken later by other sessions is not counted.

## Residual

- 2026-11-11: the after-measure is the brief's: the next full prepush on the owner's laptop prints a worker count
  that its free memory holds, and does not run it out of memory.
