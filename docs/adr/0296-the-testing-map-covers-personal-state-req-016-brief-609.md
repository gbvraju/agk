# ADR-0296: The `[testing]` map covers `personal_state.py` (REQ-016, brief 609)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0285, ADR-0292
- Requirements: REQ-016

Protected classes: `agk.toml`

## Context

ADR-0285 gave this repository's `agk.toml` a `[testing]` map with one entry per script under `scripts/agk/` that is not in
`always_full`. #587 added `scripts/agk/personal_state.py`, and its checks last ran before #581's map existed, so after it
merged the script had no entry and
`tests/kit_dev/test_intelligent_testing.py::test_every_script_is_covered_by_an_entry_or_always_full` failed on main
(brief #609). This is the same cause ADR-0292 fixed for the data guard's scripts. The conductor reserved the ADR number
for brief #609.

## Decision

1. `agk.toml` gains one `[[testing.map]]` entry for `scripts/agk/personal_state.py`, built by ADR-0285 decision 2: the test
   files that import the script or name it as `<script>.py`, closed over imports (`tests/kit/test_personal_state.py` and
   `tests/kit_dev/test_kit_manifest.py`; no script imports `personal_state`).
2. Nothing else changes.

## Consequences

The test of ADR-0285 decision 5 passes on main again, and a change to `personal_state.py` runs its own and affected tests.

## Residual

None.
