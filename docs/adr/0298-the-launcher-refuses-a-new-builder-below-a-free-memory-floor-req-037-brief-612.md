# ADR-0298: The launcher refuses a new builder below a free-memory floor (REQ-037, brief 612)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0190, ADR-0219, ADR-0223
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Pilot feedback #606 (item 2) counted about six stops of the conductor's background watches under memory pressure, with
finished builder tabs holding about 300 MB each. `launch.py` starts builder sessions through the project's adapter
(ADR-0190, and resumed ones by ADR-0219) without looking at the machine's free memory. The kit already reads available
memory for `[flow] builder_memory_gb` (brief #409, ADR-0223) through `common.available_memory`.

## Decision

1. `[flow] min_free_memory_mb` is a new optional setting: a whole number of MiB, 1 or more. Unset means today's
   behaviour, and the memory is not read. Any other value is refused naming the setting, never the value (exit 2).
2. Before `launch.py prompts --adapter` starts or resumes a session, it reads the machine's free memory with
   `common.available_memory`: standard library only and no network (`/proc/meminfo` `MemAvailable` on Linux,
   `sysctl` page size and free pages on macOS, `GlobalMemoryStatusEx` through `ctypes` on Windows). The macOS reader
   stays the kit's existing `sysctl` one rather than a second, `vm_stat`, reader; it counts free pages only, so it errs
   low.
3. Below the floor (strictly less) it starts nothing and prints the one line
   `launch: not started: free memory below [flow] min_free_memory_mb` and exits 1. At or above the floor, today's
   behaviour.
4. When the memory cannot be read, it starts the sessions as today and prints one line
   `launch: note: free memory cannot be read; started without [flow] min_free_memory_mb`.
5. Printing the prompts (no `--adapter`) starts nothing, so the floor does not apply there.

## Consequences

A machine short of memory gets no new builder from the launcher, and the person or the conductor sees one line saying
which setting held it. Nothing changes for a project that does not set the floor.

## Residual

- 2026-11-06: whether the printed prompts should also be withheld below the floor is Q-612-1; whether the setting
  belongs in the commented `[flow]` block of `kit/templates/agk.toml` (a hashed release file) is Q-612-2.
