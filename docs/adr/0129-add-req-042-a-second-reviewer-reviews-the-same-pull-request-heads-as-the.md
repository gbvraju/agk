# ADR-0129: Add REQ-042: A shadow reviewer lets AGK measure the conductor's catch rate

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: SPEC-0035
- Requirements: REQ-042

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-25:

> A second reviewer reviews the same pull request heads as the conductor without seeing its verdicts, every finding of either is marked right or wrong at merge, and AGK reports the conductor's catch rate from those marks instead of anyone stating one.

## Decision

REQ-042 is added to `docs/requirements.md` as `planned`. SPEC-0035 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
