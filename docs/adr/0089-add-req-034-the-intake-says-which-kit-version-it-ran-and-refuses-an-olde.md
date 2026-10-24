# ADR-0089: Add REQ-034: The intake names its kit version and the final check accepts review answers

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: SPEC-0027
- Requirements: REQ-034

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-24:

> The intake says which kit version it ran and refuses an older one, and a question the maintainers answered at review, before approval, has a true form that the final check accepts.

## Decision

REQ-034 is added to `docs/requirements.md` as `planned`. SPEC-0027 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
