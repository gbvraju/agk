# ADR-0114: Add REQ-041: Parallel builders get briefs by capacity, overlap, reserved numbers and claims

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: SPEC-0034
- Requirements: REQ-041

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-25:

> A team sets how many builder sessions run at once, and AGK hands each session a brief that no open pull request overlaps, with its numbers reserved, so parallel work starts by itself, rarely conflicts, and every pull request traces to a brief and a requirement.

## Decision

REQ-041 is added to `docs/requirements.md` as `planned`. SPEC-0034 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
