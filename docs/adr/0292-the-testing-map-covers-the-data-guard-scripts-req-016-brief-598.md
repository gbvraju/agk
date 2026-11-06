# ADR-0292: The `[testing]` map covers the data guard's scripts (REQ-016, brief 598)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0285
- Requirements: REQ-016

Protected classes: `agk.toml`

## Context

ADR-0285 gave this repository's `agk.toml` a `[testing]` map with one entry per script under `scripts/agk/` that is not in
`always_full`. The map was built (#581) before #579 merged, so after both merged `scripts/agk/guard.py` and
`scripts/agk/guard_logs.py` had no entry, and `tests/kit_dev/test_intelligent_testing.py::test_every_script_is_covered_by_an_entry_or_always_full`
failed on main (found-bug #597). The ADR number was reserved for brief #598 by the conductor.

## Decision

1. `agk.toml` gains one `[[testing.map]]` entry for `scripts/agk/guard.py` and one for `scripts/agk/guard_logs.py`, built by
   ADR-0285 decision 2: the test files that import the script or name it as `<script>.py`, closed over the scripts' own
   imports (`config.py` and `guard_logs.py` import `guard`).
2. Nothing else changes.

## Consequences

The test of ADR-0285 decision 5 passes on main again, and a change to either script runs its own and affected tests.

## Residual

None.
