# ADR-0223: the session plan counts the machine's memory when it says how many builders to start (REQ-041, brief 409)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0189, ADR-0219
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

Brief #409, from #286 part 3 and its field note of 2026-10-27 (memory). On a 16 GB-class laptop running two builders with
containers, the runtime stopped a builder's background `watch` for low memory, and the builder's loop paused until a person
noticed. The plan's capacity (`session.py plan`, SPEC-0034 rule 15) reads only `max_builders` and the review backlog. The
brief names no `Measured:` line. The tests were written first (`tests/kit/test_session_plan.py`, the memory sections: 14
failed, 50 passed at the first checkpoint).

## Decision

1. **The setting (answer 1, Q-409-1).** `builder_memory_gb` of the `[flow]` table of `agk.toml`, beside the plan's other
   settings: a whole number, 1 or more, unset by default. A value that is not one (0, a negative, a fraction, a string, a
   boolean) is refused with `rule 15: builder_memory_gb of the flow table must be a whole number, 1 or more`, which names the
   setting and never the value.
2. **The capacity (answer 1).** Unset, the plan is as before. Set, the plan's slots are the lowest of `max_builders` less the
   running builders, `reviews_in_flight` less the pull requests waiting for a verdict, and the available memory divided by
   `builder_memory_gb` GiB, rounded down and never below 1. The available memory is read with the running builders already
   on the machine, so the memory figure counts only builders still to start, as the other two do. A GB is read as a GiB
   (1024^3 bytes), the lower count of builders (Q-409-2).
3. **The reading (answer 2).** `common.available_memory()` uses no new dependency: on Linux the `MemAvailable:` line of
   `/proc/meminfo`; on macOS `sysctl -n hw.pagesize vm.page_free_count`, the free pages times the page size `(verify: the
   two sysctl names, not run on a Mac by the builder)`, which leaves out the memory macOS can reclaim and so errs low
   (Q-409-3); on Windows `ullAvailPhys` of `GlobalMemoryStatusEx` through `ctypes`. Any other platform and any failure read
   as unknown: the plan says `memory: unknown` and keeps the other two figures.
4. **The limit (answer 3, Q-409-4).** `plan --json` adds `capacity.limit`, always: `max_builders`, `reviews` or `memory`,
   the figure that gave the slots, the first of them in that order on a tie, so `memory` is named only when memory alone is
   the lowest. With the setting it adds `capacity.builder_memory_gb` and `capacity.memory`, either `"unknown"` or
   `{"available_bytes": n, "builders": n}`. The plain words add, with the setting only, one line after the start line:
   `Capacity: <slots> (limit: <limit>; <n> GB available, builder_memory_gb is <g>, room for <b>).` or
   `Capacity: <slots> (limit: <limit>; memory: unknown).`; without it the words are unchanged. `Start 0:` keeps its reason.
5. **Tests (answer 4).** Unset (unchanged, the limit named); a memory limit below `max_builders`; above it; the reviews
   limit; never below 1; an unreadable reading; a value that is not a whole number (refused, naming the setting); the three
   readers and the platform dispatch. The plan's memory tests run the plan in the test's process with the reading replaced,
   so no test depends on the memory of the machine that runs it.
6. **Flow mode.** The template `kit/templates/agk.toml` documents the setting in its commented `[flow]` block; one fragment
   `changelog.d/plan-memory.md`; no version bump; `kit/hashes.json` not edited. `session.py next` and `demand` still read
   `max_builders` alone.

## Consequences

- A project that sets `builder_memory_gb` gets a plan, and an `auto_start` run (which starts no more than `capacity.slots`),
  that a laptop can carry; the plan says when memory was the limit.
- The reading is a moment's figure: memory freed or taken after the plan is not seen until the next plan.

## Residual

- 2026-10-31: Q-409-1 to Q-409-4 asked on the pull request; the readings above are the most conservative ones.
