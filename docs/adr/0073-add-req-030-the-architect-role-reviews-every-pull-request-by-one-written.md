# ADR-0073: Add REQ-030: The architect reviews by one written protocol and its catch rate is measured

- Status: Proposed
- Date: 2026-10-22
- Deciders: maintainers
- Related: SPEC-0023
- Requirements: REQ-030

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-22:

> The architect role reviews every pull request by one written protocol that names what it read, walks the spec's rules, says what the tests do not prove and where a gap belongs, and its catch rate is measured against a person's before any claim is made.

## Decision

REQ-030 is added to `docs/requirements.md` as `planned`. SPEC-0023 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
