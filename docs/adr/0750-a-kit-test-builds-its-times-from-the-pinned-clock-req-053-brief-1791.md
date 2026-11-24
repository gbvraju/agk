# ADR-0750: A kit test builds its comment times from the pinned clock the code reads (REQ-053)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1791, ADR-0699, brief #1680, found bugs #446 and #1497, plan #661
- Requirements: REQ-053

Protected classes: `tests/kit/`

## Context

ADR-0699 pinned the clock `session.py` reads to the test's start and made `DAY` follow that pin, but `iso` in
`tests/kit/test_session.py` still read the live clock when a test built its comments. `iso(-timedelta(hours=30))` was
then 30 hours minus the time since set-up before the pin, and `session_plan.age_text` counts whole hours, so #1780's
governance job (head 83571b96) read `29 hours` where the test expected `30 hours`. One test of `test_session.py` also
computed its expected `taken:` day from the live clock after the post, so a run crossing 00:00Z failed it. The
owner's word (2026-11-23, the steward chat, quoted as data): "Yes, file the stale-claim clock brief".

## Decision

1. `iso(delta)` reads `AGK_TEST_NOW` when it is set and parses, truncated to the second, and the live clock otherwise.
   The `clock` fixture and every assertion are unchanged (principle 11).
2. The test of `test_session.py` that asserts the posted `taken:` day takes the `clock` fixture and reads the day
   from the pin.
3. A guard test, `tests/kit/test_clock_pin_guard.py`, fails naming the file, the line and the rule when a module that
   opts in to the `clock` fixture (`usefixtures("clock")`, or a test that takes `clock`), or a helper it imports from
   `test_session` or `test_session_flow`, reads a live clock outside `iso` and `Day`. It reads files only.
4. Path class changed: `tests/kit/` (kit-only tests, not copied into a project). No setting and no script changes.

## Consequences

A slow runner and a run across midnight UTC keep the session tests green, and a new live read under the pin fails
in the guard instead of as a flake. A module with its own `clock` fixture, or without the pin, is not checked.

## Residual

None.
