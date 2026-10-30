# ADR-0191: one kit command takes and releases the heavy-step lock safely (REQ-040, brief 337)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0182, ADR-0186
- Requirements: REQ-040

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `config/`

## Context

Brief #337 (priority 1). In a pilot, several builders on one 16 GB laptop ran the full test suite at once and the machine killed
processes; the team made a lock folder by hand. The local-mode guide (#322, ADR-0182) shows a shell snippet whose `trap` releases
the lock only when one shell ends, which fails when an agent runs the lines as separate commands. The brief names no `Measured:`
line. The tests were written first (`tests/kit/test_lock.py`: collection fails without `scripts/agk/lock.py`, 0 of 19 run, at the
first checkpoint of the pull request).

## Decision

To be written with the implementation.

## Consequences

To be written with the implementation.

## Residual

Open items, each with a date.
