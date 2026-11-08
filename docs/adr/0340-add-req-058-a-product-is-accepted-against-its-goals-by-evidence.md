# ADR-0340: Add REQ-058: A product is accepted against its goals by evidence

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0051, SPEC-0012, SPEC-0047, SPEC-0048, SPEC-0046, SPEC-0020, ADR-0310, plan #661, brief #685
- Requirements: REQ-058

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-08:

> Intake for the acceptance loop: a delivered product is accepted against the goals the discovery recorded, by evidence, with the owner's one-line yes (plan #661 phase 7, wave 4).

The brief is issue #728, filed under plan #661 (phase 7, wave 4), whose phase 7 reads, quoted as
data: "product-owner acceptance loop (new intake: each goal of the discovery document is accepted
by a listed person against its evidence; a release lists the goals it closes)". The brief gave three
answers: each goal of the `success` discovery answer (SPEC-0048 rule 4) maps to evidence (a test, a
run record, a demo record) or is marked `not met`; the owner decides with one line and the
scorecard (SPEC-0047) shows the result; and an unmet goal becomes one brief, filed by the conductor.

What exists and is reused (SPEC-0051 rule 1): the discovery document and its `success` answer
(SPEC-0048 rules 4 and 5, build (b) open as #715), the run and demo records under `docs/runs/`
(SPEC-0048 rule 8), the approval readers of `reviewers.py`, the weekly scorecard
(`scorecard.py`, SPEC-0047) and the conductor's one brief creation. What is missing: nothing
records which goal a delivered product meets, by what evidence, or who accepted it.

## Decision

1. REQ-058 is added to `docs/requirements.md` as `planned`, and SPEC-0051 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it.
2. The goals are the discovery document's `success` answer only, split into quoted parts that
   together make the whole answer; an `open` answer has no goals (SPEC-0051 rule 2).
3. One acceptance record per problem, `docs/acceptance/<slug>.md`, maps each goal to evidence of
   three kinds (`test`, `run`, `demo`), read as files that exist, or to `not met`; a new installed
   check, `check_acceptance.py`, checks its form and staleness in `make governance` and never runs
   or judges the evidence (SPEC-0051 rules 3 to 5).
4. The owner's yes is one line, `Approve: acceptance <slug> <full head ID>`, by an account of
   `spec_approvers`, never a session's; the product is accepted only when no goal is `not met`
   (SPEC-0051 rules 6 and 7).
5. The conductor files one brief per unmet goal, searching first for its `Goal: <slug> G-<n>` line,
   and the scorecard gains `goals_not_met` by an amendment to SPEC-0047 rule 1 (SPEC-0051 rules 8
   and 9).
6. This is the one ADR of REQ-058 for the builds of SPEC-0051 rule 12. The builds will change
   these protected path classes: `scripts/agk/` (`check_acceptance.py`, `reviewers.py`,
   `scorecard.py`, builds (b), (c) and (d)), `tests/kit/` (their tests), `agk.mk` (the
   governance line, build (b)), `kit/` (`kit/manifest.json`, the new installed script, build
   (b)), `agk.toml` (its `[[testing.map]]` entry, build (b)), `.claude/`
   (`.claude/agents/conductor.md`, build (e)) and `config/` (`config/rule-budget.txt`, build (e)).
   A build that changes a class named here and no other may cite this ADR with
   `Covered-by: ADR-0340` once it is Accepted (session rule 36). The change to SPEC-0047 rule 1
   goes through an amendment file whose number is reserved on build (d)'s brief. The workflow line
   that passes saved comments to the check in CI (build (c)) is not covered here: it needs the
   owner's quoted yes and its own ADR. No build changes `constitution/`, `config/reviewers.yaml`,
   the ruleset (`kit/templates/ruleset.json`), `.github/CODEOWNERS`, `CLAUDE.md`, `Makefile`,
   `pyproject.toml`, `skills/` or `.claude-plugin/`; `kit/hashes.json` and the version stay the
   release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request; until build (b) lands no record is checked, and until build (c)
lands, or its CI line is approved, the owner's yes is read by the conductor alone.

## Residual

None beyond SPEC-0051's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.
