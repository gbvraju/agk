# ADR-0082: Add REQ-032: Teams phase 1: independent pull requests run in parallel without collisions

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: SPEC-0025
- Requirements: REQ-032

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-24:

> A team can run independent pull requests in parallel without colliding on numbers or logs, a pull request that needs another one's unmerged change says so and cannot merge before it, and each repository chooses a strict or a flow mode for how many pull requests a person may have open.

## Decision

REQ-032 is added to `docs/requirements.md` as `planned`. SPEC-0025 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
