# ADR-0110: Add REQ-039: GitHub events label each PR, people approve specs, a red branch stops new work

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: SPEC-0032
- Requirements: REQ-039

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-25:

> GitHub events, not sessions, compute the next step of every pull request as one label, so a conductor or builder that restarts resumes from GitHub with no memory and no polling of its own, a person approves every spec, and a red default branch stops new work until it is green.

## Decision

REQ-039 is added to `docs/requirements.md` as `planned`. SPEC-0032 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
