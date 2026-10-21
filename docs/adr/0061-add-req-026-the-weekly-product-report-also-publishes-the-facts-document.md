# ADR-0061: Add REQ-026: The weekly report publishes the facts it was rendered from

- Status: Accepted
- Date: 2026-10-21
- Deciders: maintainers
- Related: SPEC-0019
- Requirements: REQ-026

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-21:

> The weekly product report also publishes the facts document it was rendered from, as a downloadable file of the workflow run, so a reader outside the repository can use the same numbers.

## Decision

REQ-026 is added to `docs/requirements.md` as `planned`. SPEC-0019 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until its open questions are ruled and a later change sets it `Approved`.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
