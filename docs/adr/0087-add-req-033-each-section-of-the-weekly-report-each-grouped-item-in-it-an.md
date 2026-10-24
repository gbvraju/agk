# ADR-0087: Add REQ-033: The report states how many each section, group and unknown total holds

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: SPEC-0026
- Requirements: REQ-033

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-24:

> Each section of the weekly report, each grouped item in it, and each total that can be unknown states how many it holds, and nothing the facts could not read is left out silently, so a reader can show totals without counting.

## Decision

REQ-033 is added to `docs/requirements.md` as `planned`. SPEC-0026 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
