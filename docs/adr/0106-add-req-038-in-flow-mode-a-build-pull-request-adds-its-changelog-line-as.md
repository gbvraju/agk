# ADR-0106: Add REQ-038: A flow-mode build adds its changelog line as a file of its own

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: SPEC-0031
- Requirements: REQ-038

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-24:

> In flow mode a build pull request adds its changelog line as its own file, so two builds open at once never conflict on `CHANGELOG.md`, and the release pull request gathers the files into the changelog.

## Decision

REQ-038 is added to `docs/requirements.md` as `planned`. SPEC-0031 is added as `Draft`. Merging
this pull request approves the requirement as a proposal; it does not approve the spec, which stays
`Draft` until it is approved, by a later pull request or by this intake's own final commit.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.
