# ADR-0500: The conductor sees ready work on every watch return and sweep

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: ADR-0489, ADR-0482, brief #1151, brief #1179, plan #661
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

`conductor.py watch` returns `START #<brief> <kind>` (ADR-0489) only when a poll found no `Question:`, `Report:`,
answer, approval, green-main or held-review line. While builders are active there is almost always such a line, so the
conductor reviews it and its watch never names the ready brief; `sweep` prints no `START` line at all. On 2026-11-13,
of 21 builder starts between 00:00 and 09:55 IST the conductor made 7 and 11 were made by hand; #1096 had no start 3
minutes after #1147 merged while the conductor was reviewing #1160 and #1162.

## Decision

1. `watch` reads `start_lines` on every poll and appends its lines after the new, green and held lines, so a return
   that names a `Report:` or a held review also names each offered, unstarted brief, `START` last.
2. `sweep` prints the same `START` lines, read with the same function, after all its other lines.
3. The guards of ADR-0489 are unchanged: the plan is read at most once a minute (the `agk/starts` mark in the git
   directory, shared by `watch` and `sweep`), a `Started: cb` or `taken:` comment of the last 2 hours holds a brief, and
   a brief returned once is not returned again for 10 minutes. A busy watch therefore adds at most one plan read a
   minute.
4. The conductor's start rule and `.claude/agents/conductor.md` are unchanged; no new setting or label.

## Consequences

A brief that becomes ready while the conductor is busy is named in its next watch return or sweep, so it is started at
the conductor's next step instead of by hand. A `START` line that a watch named is not repeated by a sweep within 10
minutes, so the conductor acts on the first one it sees.

## Residual

- 2026-11-13: a `START` line on a busy return is read only once a minute, so a brief offered just after a plan read
  waits up to a minute more (due 2027-01-31).
