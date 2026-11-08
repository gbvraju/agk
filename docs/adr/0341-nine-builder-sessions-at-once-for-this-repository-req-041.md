# ADR-0341: Nine builder sessions at once for this repository

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0034, ADR-0266, plan #661
- Requirements: REQ-041

Protected classes: `agk.toml`

## Context

SPEC-0034 rule 1 lets a project set how many builder sessions run at once with `max_builders` in the `[flow]` table,
default 3. This repository never set it, so `session.py claim` and `session.py demand` read 3 while the owner directed,
on 2026-11-08 (plan #661), that nine builders run at once on work that does not overlap. The conductor's own plan and
the kit's capacity disagreed, and the kit's number is the one its commands enforce.

## Decision

1. This repository's `agk.toml` sets `max_builders = 9` in `[flow]`.
2. Nothing else changes: the claim rules, the overlap rule of SPEC-0050 and the review and merge path stay as they are;
   more builders means more parallel work, never a skipped check.

## Consequences

- `session.py demand` and `claim` allow up to nine open builder pull requests; the conductor's ready pool is sized to it.
- More pull requests are open at once, so merges of the default branch into open branches are more frequent; SPEC-0050's
  overlap rule keeps two builders off the same files.

## Residual

- The number is the owner's choice, not measured. SPEC-0049's usage figures and the scorecard (SPEC-0047) will show
  whether nine pays for itself in merged work per token; the owner changes the number by an ADR in the same pull request.
