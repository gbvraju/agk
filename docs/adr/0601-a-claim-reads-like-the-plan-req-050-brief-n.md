# ADR-0601: A claim reads like the plan

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1435, ADR-0529, ADR-0548, ADR-0555, ADR-0565
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

`session.py claim` read the list of every pull request ever (`pulls?state=all`) twice, once itself and once in the
survey of its overlap judgement, read the open-brief listing up to three times, never set the in-run memo of the plan
(ADR-0529 decision 2) and never asked the repository-wide `since` read (ADR-0548). On this repository one claim made
29 calls in 18 s, 16 of them every pull request ever; with the default `gh` transport on a slow machine that is minutes.
It printed no `reads:` line, and a primary rate-limit wait gave its seconds only.

## Decision

1. `claim` reads the pull requests with `recent_pulls`: the open ones and the closed ones updated within the larger of
   `claim_hours` and the plan's 14 days (`WINDOW_DAYS`), never `pulls?state=all`. Its survey is marked `recent`, so a
   build merged before the window is read as the plan reads it (ADR-0529 decision 4).
2. `claim` sets `MEMO` for its run and clears it at the end, and calls `changed_since_pass` first. It writes no plan
   stamp (`end_pass`): the stamp stays the plan's.
3. `survey` takes the pull requests a claim already read (`pulls`); the reservation, the overlap and the red-alarm
   surveys of `claim` pass them, so nothing is read twice.
4. A write forgets what it changed: the memo's reads of the endpoint written and, for a comment, that issue's place
   in the pass's unchanged set (`forget_read`), so the take a claim posts is read back from GitHub.
5. `claim` ends with the plan's `reads:` line (`session_plan.reads_line`) on standard error, also when a read fails.
6. A primary rate-limit wait prints `github: limited, waiting <s> s (primary, until HH:MM local)`; a secondary wait
   keeps its line.
7. No verdict of `claim` changes, no setting is added, and no file is written outside the read cache's folder.

## Consequences

A claim on this repository makes 18 calls (9 from cache) in about 12 s, against 29 in 18 s, and a claim of a brief this
session already holds makes 9. Most of the rest is the closed pull requests of the 14-day window (5 pages here), which
the plan reads too.

## Residual

- The brief's `Measured:` target of 12 calls or fewer is not met on this repository while 14 days of closed pull
  requests fill 5 pages (Q-1435-1).
