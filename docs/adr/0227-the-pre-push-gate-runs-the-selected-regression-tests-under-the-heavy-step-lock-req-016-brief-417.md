# ADR-0227: the pre-push gate runs the selected regression tests too, under the heavy-step lock (REQ-016, brief 417)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0186, ADR-0191, ADR-0208, ADR-0220
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #417 (from #289 parts 2 and 4, and #288 tier T0): `prepush.py` (ADR-0186) runs only proof's plan, the pull request's
own test files. `impact.py` (ADR-0220, brief #373) now gives the regression set that the `[testing]` table of `agk.toml`
selects, but nothing runs it. In the pilot two builders' gates collided on one laptop; `lock.py` (ADR-0191) exists, but
prepush does not use it. The script and its tests are protected path classes, so this ADR names them. The tests were
written first (`tests/kit/test_prepush_regression.py`: 14 failed, 2 passed at the first checkpoint).

## Decision

Pending: written with the implementation.

## Consequences

Pending.

## Residual

Pending.
