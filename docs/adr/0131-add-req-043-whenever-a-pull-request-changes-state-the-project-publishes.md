# ADR-0131: Add REQ-043: The project publishes what waits for a person in plain words

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: SPEC-0036
- Requirements: REQ-043

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-25:

> Whenever a pull request changes state, the project publishes one small pipeline document saying, in plain words a non-developer understands, which pull requests are ready to merge, which specs wait for approval and how many pull requests are in each state.

## Decision

REQ-043 is added to `docs/requirements.md` as `planned`. SPEC-0036 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
