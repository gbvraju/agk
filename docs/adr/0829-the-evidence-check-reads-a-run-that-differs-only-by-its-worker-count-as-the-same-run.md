# ADR-0829: The evidence check reads a run that differs only by its worker count as the same run (REQ-051)

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #2005, ADR-0422 (selected runs in workers), ADR-0441 (auto workers capped by memory,
  `AGK_TEST_WORKERS`), ADR-0825 (the quick prepush runs the whole tests), ADR-0818, ADR-0233, #1992, plan #661
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

`[testing] workers = "auto"` gives each machine its own worker count, and prepush writes it into each test run's
command (` -n <n>` at the end of a pytest command, or the number in a filled `parallel_command`). `evidence.py check`
compared the recorded command with the one it plans on the conductor's machine, so a record made where the count
differs failed as `not what prepush runs: <name> (field: command)` with nothing in the pull request changed. On #1992
(verdict 7194161165) that cost one builder wake and one review. The owner's word (2026-11-26, the steward chat,
quoted as data): "Draft 1 , 2 and 3 then file it".

## Decision

1. `prepush.without_workers(command, root)` returns COMMAND without its worker part: a trailing ` -n <digits>` (the
   one form `pytest_workers` writes, never `-n 0`), or, for `[testing] parallel_command` with `{workers}` filled, the
   template itself. Any other command is returned as it is. `evidence.py` compares the recorded and the planned command
   through it; the cwd and the name are compared as before.
2. A run that matches only by decision 1 is replayed with the conductor's own planned command, and the check adds one
   note `workers: <name> recorded <r>, replayed <p>` (worker counts, 1 for a run with none). The `Evidence check:` line
   stays `agrees` when every replayed exit matches.
3. Nothing else loosens: another file, option, interpreter, `-n auto`, or `-n` not at the end still differs by
   `field: command`. A single run against a planned `-n <p>`, and the reverse, match.

## Consequences

A record from a machine with another processor count, memory or `AGK_TEST_WORKERS` agrees; the files, folder and exit
of each run are still compared and replayed. A later set that `selected_workers` gives workers is read the same way,
since every recorded command is compared through `without_workers`. CI, workflows, labels and settings are unchanged.

## Residual

Another runner's worker option (not `-n`, not `parallel_command`) is still compared as written.
