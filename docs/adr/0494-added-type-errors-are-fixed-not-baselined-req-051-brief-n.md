# ADR-0494: Added type errors are fixed, not baselined

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: ADR-0307, issue #986, brief #1157, plan #661
- Requirements: REQ-051

## Context

ADR-0307 (brief #633) keeps `config/mypy-baseline.txt`: `tests/kit/test_scanner_hygiene.py` runs the pinned mypy on
`scripts/agk` and fails when a file has more errors of a code than its baseline line, or fewer. CI installs no mypy, so
the test skips there and errors added since the baseline went unseen (issue #986). On 2026-11-13, with mypy 2.3.1,
`design_compare.py`, `doctor.py` and `merge_cleared.py` had 5 errors over their lines (brief #1157's `Measured:` line).

## Decision

1. An error a change added over the baseline is fixed with a type-only change (an annotation, a narrowing that the
   code's behaviour already implies, a `cast` where the value is known), never with `# type: ignore` and never by
   raising the baseline; only a fix that would change behaviour raises a line, with a one-line reason in the pull
   request body.
2. Part 1 (brief #1157) fixes the three files: `design_compare.py` casts the browser where `ran` already implies it is
   set; `doctor.py` narrows the brief number before `setdefault`, widens `suggested_profile` to the `float` that
   `session_plan.figure` returns, casts `route_of`'s result where the routes table is non-empty (its `None` is
   unreachable) and returns `float(seconds)` inside the type test; `merge_cleared.py` tests `item` beside `pull`,
   which a dict `pull` already implies. `doctor.py`'s `arg-type` line, now 0, leaves the baseline.
3. Part 2 fixes `prepush.py`, `product_report.py` and `route.py`, and closes #986.

Protected path classes changed: `scripts/agk/` (`design_compare.py`, `doctor.py`, `merge_cleared.py`), `config/`
(`config/mypy-baseline.txt`).

## Consequences

The three files match their baseline lines under the pinned mypy and behave as before. The test still fails on a
machine with mypy 2.3.1 until part 2 lands; CI, which installs no mypy, still skips it.

## Residual

- 2026-11-13: part 2 (`prepush.py`, `product_report.py`, `route.py`) is the next brief for #986.
