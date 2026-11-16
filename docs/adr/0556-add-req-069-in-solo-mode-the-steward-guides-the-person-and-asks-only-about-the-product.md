# ADR-0556: Add REQ-069: In solo mode the steward guides the person and asks only about the product

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0062, SPEC-0059, SPEC-0038, SPEC-0048, ADR-0541, ADR-0546, brief #1277, brief #1318, plan #661
- Requirements: REQ-069

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-15:

> Intake for the steward's customer experience in solo mode: the person is understood in their own words, guided through AGK's path in order at their own pace, decides only about their product and never about AGK, and approves with a plain yes.

The brief is issue #1318, under plan #661. SPEC-0059 (Approved, ADR-0541) makes the steward the owner's one entry point,
but has no rule for who it talks to or how it adapts its words, no play-back before it acts, plain speech only in owner
questions, no rule that settles AGK matters without the person, no progress in the person's words, and an approval that
is still an exact line the person types. The `vision` skill and SPEC-0048 rule 5 write `pilot (proposed)` when no work
type is chosen, where the owner's default is an enterprise product. One day of a customer project in local mode showed
two clean specs waiting 15 and 12 hours for one exact line each, and a kit upgrade taking the owner five hand steps.

## Decision

1. REQ-069 is added to `docs/requirements.md` as `planned`, and SPEC-0062 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until the owner's own `Approve:` line approves it.
2. SPEC-0062 holds only in solo mode (`review_mode = "solo"`); in team mode the steward is SPEC-0059 exactly. The steward
   never changes `review_mode`.
3. In solo mode the steward starts from the kit alone, learns who the person is (a `Person:` memory entry), uses the
   person's words and no kit term, plays back what it understood before each stage's output, runs the kit's skill for
   each stage in the kit's order at the person's pace, and talks only about the product.
4. The person decides the product (scope, dates, cost, sign-off, architecture picks); the steward settles every AGK matter
   from the kit's rules and defaults, records each as a `Setup:` entry, does setup through the kit's commands and skills,
   and plans an enterprise product on the kit's full path unless the person asks for a pilot. The `[delivery] work_type`
   line stays the person's (SPEC-0038 rule 5), and the discovery document's `pilot (proposed)` stays until a proposed
   amendment of SPEC-0048 rule 5 by build (b) is approved.
5. An approval is one plain question and an explicit yes, relayed with the person's quoted words and time and
   `Who: ProductOwner`, which the readers count as the person's; a line marked as AGK's, or without the quote, approves
   nothing; merges, tags, force pushes and workflow changes stay the person's or denied. That build, (d), changes
   ADR-0546 decision 4 and session rule 29 and writes its own ADR.
6. This is the one ADR of REQ-069 for builds (a) to (c) of SPEC-0062 rule 18, for what it names here. They will change
   these protected path classes: `.claude/` (the steward's agent file and guard), `scripts/agk/` (the memory kinds, the
   progress summary and the counts), `tests/kit/`, `tests/kit_dev/` and `kit/` (the manifest, where a new file is
   installed). A build that changes a class named here and no other may cite this ADR with `Covered-by: ADR-0556` once it
   is Accepted (session rule 36). Build (d) writes its own ADR, as does any build that changes `config/`, `skills/`, an
   Approved spec or an ADR's decision. No build changes a workflow file (`.github/`), the ruleset or
   `config/reviewers.yaml`; `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: the steward is not built until SPEC-0059's build (a) lands.

## Residual

None beyond SPEC-0062's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.
