# ADR-0098: Add REQ-037: A conductor reviews the queue and a builder finds its work by itself

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: SPEC-0030
- Requirements: REQ-037

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-24:

> A conductor role reviews every pull request, posts the verdict and keeps the queue, and a builder session finds its next item and its verdicts by itself, through files and comments that a check can read.

## Decision

REQ-037 is added to `docs/requirements.md` as `planned`. SPEC-0030 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
