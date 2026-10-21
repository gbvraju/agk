# ADR-0065: Add REQ-027: An intake pull request may carry its own approval

- Status: Accepted
- Date: 2026-10-21
- Deciders: maintainers
- Related: SPEC-0020
- Requirements: REQ-027

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-21:

> When the maintainers answer every intake question before the files are written, the intake pull request may carry the approval itself: its final commit, on their word, sets the spec Approved and the ADR Accepted, and no separate rulings pull request is needed.

## Decision

REQ-027 is added to `docs/requirements.md` as `planned`. SPEC-0020 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until its open questions are ruled and a later change sets it `Approved`.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
