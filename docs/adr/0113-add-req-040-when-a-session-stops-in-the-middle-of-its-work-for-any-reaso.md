# ADR-0113: Add REQ-040: A stopped session loses nothing and the next one resumes with one command

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: SPEC-0033
- Requirements: REQ-040

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-25:

> When a session stops in the middle of its work for any reason, nothing it did is lost or half-applied, and the next session resumes from the branch and the pull request with one command instead of starting again.

## Decision

REQ-040 is added to `docs/requirements.md` as `planned`. SPEC-0033 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
