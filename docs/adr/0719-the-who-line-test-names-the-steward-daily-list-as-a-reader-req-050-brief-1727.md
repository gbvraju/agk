# ADR-0719: The Who-line test names the steward's daily list as a reader of the line

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1727, brief #1716 (ADR-0715), brief #1289, brief #1691 (ADR-0704)
- Requirements: REQ-050

## Context

The default branch went red when #1720 (brief #1716) merged: `tests/kit/test_who_line.py::test_no_check_reads_the_who_line`
pins the scripts that read the `Who:` line to `reviewers.py` and `route.py`, and `scripts/agk/steward_daily.py` now
reads it (`WHO_LINE`, `WHO_FOOTER`) to count an override only from the owner, as ADR-0715 decision 1 decides. #1720 was
built before #1699 added `reviewers.py` to the list, so neither run saw the two together.

## Decision

1. **The list.** The asserted readers become `["reviewers.py", "route.py", "steward_daily.py"]`, with one clause in the
   comment naming why `steward_daily.py` reads the line.
2. **No other change.** No script changes. The test still fails on any other script that reads the line; the check is
   not weakened, it names one more reader that an Accepted decision added.

Protected path classes changed: `tests/kit/` (`test_who_line.py`).

## Consequences

The default branch's governance run turns green. A fourth reader of the line still fails the test.

## Residual

- 2026-11-22: none.
