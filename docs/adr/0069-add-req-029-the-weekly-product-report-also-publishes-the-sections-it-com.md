# ADR-0069: Add REQ-029: The weekly report also publishes its sections as data in report.json

- Status: Accepted
- Date: 2026-10-22
- Deciders: maintainers
- Related: SPEC-0022
- Requirements: REQ-029

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-22:

> The weekly product report also publishes the sections it computed as data, in a report.json beside facts.json in the same artifact, so any reader can show the same report without reimplementing its rules.

## Decision

REQ-029 is added to `docs/requirements.md` as `planned`. SPEC-0022 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
