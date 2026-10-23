# ADR-0077: Add REQ-031: The report's cost totals count the merged changes whose hours are not known

- Status: Accepted
- Date: 2026-10-22
- Deciders: maintainers
- Related: SPEC-0024
- Requirements: REQ-031

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-22:

> The report's cost totals carry the number of the week's merged changes whose hours are not known, so a reader can say how many lack them without counting.

## Decision

REQ-031 is added to `docs/requirements.md` as `planned`. SPEC-0024 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
