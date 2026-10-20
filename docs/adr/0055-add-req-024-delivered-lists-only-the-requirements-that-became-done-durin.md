# ADR-0055: Add REQ-024: Delivered lists only what became done in the week

- Status: Proposed
- Date: 2026-10-20
- Deciders: maintainers
- Related: SPEC-0017
- Requirements: REQ-024

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-20:

> Delivered lists only the requirements that became done during the week of the report, not every requirement that was ever done.

## Decision

REQ-024 is added to `docs/requirements.md` as `planned`. SPEC-0017 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until its open questions are ruled and a later change sets it `Approved`.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
