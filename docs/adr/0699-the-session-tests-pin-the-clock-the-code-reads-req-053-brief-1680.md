# ADR-0699: The session tests pin the clock the code reads

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1680, found bug #1497, plan #661
- Requirements: REQ-053

## Context

Five session test files took `DAY` from the clock when the file loaded, while `session.py` reads the clock at the
post (`taken: <id> <day>`, `taken over: <id> <day>`). A proof run that crossed midnight UTC (run 44203041870) failed
ten tests with a day that differed by one. The code is right; the expected text was fixed too early.

## Decision

1. One autouse fixture `clock` in `tests/kit/conftest.py` pins the clock of the `session.py` child process (a
   `sitecustomize` on its `PYTHONPATH` reads `AGK_TEST_NOW`) to the test's start; `clock.set(instant)` moves it.
2. `DAY` in the session tests is the day of that pinned clock, read when formatted, so the expected line follows the
   post. `session.py` and every setting are unchanged.
3. Path class changed: `tests/kit/` (kit-only tests, not copied into a project).

## Consequences

A run that crosses midnight UTC stays green. A new test pins 23:59:59Z, then 00:00:01Z, and proves the post's day.

## Residual

None.
