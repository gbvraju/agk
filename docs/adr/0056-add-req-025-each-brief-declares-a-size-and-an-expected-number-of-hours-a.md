# ADR-0056: Add REQ-025: Each brief declares a size and expected hours, compared with actual

- Status: Proposed
- Date: 2026-10-20
- Deciders: maintainers
- Related: SPEC-0018
- Requirements: REQ-025

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-20:

> Each brief declares a size and an expected number of hours, and the weekly metrics and the product report compare them with the actual hours of the pull requests that carried the brief.

## Decision

REQ-025 is added to `docs/requirements.md` as `planned`. SPEC-0018 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until its open questions are ruled and a later change sets it `Approved`.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
