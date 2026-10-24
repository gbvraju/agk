# ADR-0095: Add REQ-035: Kit builds do not bump the version and one release pull request does

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: SPEC-0028
- Requirements: REQ-035

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-24:

> In flow mode a kit build pull request does not bump the version, and one release pull request bumps it for all of them, so independent kit builds can run in parallel.

## Decision

REQ-035 is added to `docs/requirements.md` as `planned`. SPEC-0028 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
