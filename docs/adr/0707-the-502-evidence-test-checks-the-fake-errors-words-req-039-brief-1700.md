# ADR-0707: The 502 evidence test checks the fake error's words (REQ-039)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1650, brief #1700, plan #661
- Requirements: REQ-039

Protected class this pull request changes: `tests/kit/` (`test_evidence.py`). `scripts/agk/` is not changed.

## Context

`tests/kit/test_evidence.py::test_comments_that_cannot_be_read_fail_closed_with_prepushs_line` asserted `"502" not in
proc.stdout`. The output also prints a temporary repository's head id, new every run; when it holds the digits 502 the
test fails although the code is right (job 137072506922 of #1682).

## Decision

1. The test asserts that the output holds neither `HTTP 502` nor `Bad Gateway`, the fake gh's own words, through the
   helper `echoes_gh_error`, which a test of its own pins on a head id holding 502.
2. No check is weakened (principle 11): output that echoes the error text still fails the test.

## Consequences

Full governance and prepush no longer go red on a random commit id.

## Residual

None.
