# ADR-0289: Add REQ-052: Each kind of work runs on the model it needs and its token usage is recorded

- Status: Proposed
- Date: 2026-11-05
- Deciders: maintainers
- Related: SPEC-0045, SPEC-0012, SPEC-0033, SPEC-0011, SPEC-0007, ADR-0247, ADR-0270, ADR-0271, REQ-040, plan #542, #489
- Requirements: REQ-052

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-05:

> AGK runs each piece of work on the model and effort its complexity needs, starts small follow-ups with a lean prompt, and records the tokens each pull request used, without lowering any gate.

The brief is issue #591. The owner's decision, quoted as data from the brief (dated 2026-11-06 in
the brief, chat): "go ahead ... choose the model and efforts based on the work or task complexity.
Best token optimization without loosing speed and quality of the product." It is a ruled exception
to plan #542's requirement freeze at REQ-051, limited to three parts; dashboards and budgets stay
parked.

What exists and is reused: the brief's `Size:` and `Touches:` lines (`session.brief_problems`,
SPEC-0034 rule 2), the protected classes (`config/protected-paths.txt`), the builder's `Report:`
line (session rule 17), the stalled-work takeover on the same branch (session rule 9), the usage
reader of SPEC-0033 rule 8 (`metrics.usage_of`, `facts.py`, `product_report.py`, REQ-040), the
lead time and fix-list verdict counts of the weekly report, the core-rules page (ADR-0247), and the
launch prompts (`launch.py prompts`). No file of the repository records a model or an effort today.

## Decision

1. REQ-052 is added to `docs/requirements.md` as `planned`, and SPEC-0045 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it (SPEC-0032 rule 5).
2. No gate is lowered: a tier, an effort or a kind chooses only the model, the effort and the
   first reading of a session; every check, test, review and verdict runs as today, a reviewer is
   never below `strongest`, and with no `[models]` table each kind gets the defaults (SPEC-0045
   rules 1, 2 and 6).
3. The table names tiers (`strongest`, `mid`, `fast`), never a vendor's model name; a project maps
   a tier to its model name only in an optional `[models.names]` table, which the kit never ships
   (SPEC-0045 rule 3, `Q-S0045-1`).
4. A lower tier escalates instead of losing quality: a builder below `strongest` stops with
   `Report: <head> escalate` on a repeated failing check, a conflict it cannot resolve or an
   unnamed protected class, and the conductor restarts the same branch and pull request one tier
   up (SPEC-0045 rule 5).
5. Usage is recorded with the reader that exists; a missing figure is `not reported`, never 0, and
   the per-kind sums and the before-and-after comparison are a separate read-only command, so no
   Approved spec changes and amendment 121, reserved for this intake, is not used (SPEC-0045 rules
   8 and 9, `Q-S0045-11` and `Q-S0045-12`).
6. Per plan #542, this is the one ADR of REQ-052: each build of SPEC-0045 rule 10 cites it and
   records its decisions in its pull request body. The builds will change these protected path
   classes: `agk.toml` (the `[models]` table, build (b)), `scripts/agk/` (the table's reader,
   `session.py kind`, `launch.py` prompts and the read-only usage sum), `tests/kit/` (their tests),
   `.claude/` (the agent instructions in `.claude/agents/`, build (c)), `config/`
   (`config/session-rules.md` and `config/core-rules.md`, builds (c) and (d)), and `CLAUDE.md` only
   if build (c) needs the lean exception in its compaction-recovery list. A build that changes a
   class named here and no other may cite this ADR with `Covered-by: ADR-0289` once it is Accepted
   (session rule 36). No build changes `constitution/`, `.github/`, `config/reviewers.yaml`, the
   ruleset (`kit/templates/ruleset.json`), `.github/CODEOWNERS`, `kit/`, `Makefile`, `agk.mk`,
   `pyproject.toml`, `skills/` or `.claude-plugin/`.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request; until build (b) lands no session reads a `[models]` table, and
a project that sets none sees only the defaults.

## Residual

None beyond SPEC-0045's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.
