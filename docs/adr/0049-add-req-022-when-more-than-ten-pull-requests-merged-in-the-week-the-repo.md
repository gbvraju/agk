# ADR-0049: Add REQ-022: A busy week's report links the full list of merged pull requests

- Status: Accepted
- Date: 2026-10-19
- Deciders: maintainers
- Related: SPEC-0015
- Requirements: REQ-022

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-19:

> When more than ten pull requests merged in the week, the report's Delivered and Cost sections show the requirements and the totals with one link to the full list, instead of one line per pull request.

## Decision

REQ-022 is added to `docs/requirements.md` as `planned`. SPEC-0015 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until its open questions are ruled and a later change sets it `Approved`.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
