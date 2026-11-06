# ADR-0324: Add REQ-056: A build has a token and time cap by its size, and an overrun stops it

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: SPEC-0049, SPEC-0012, SPEC-0018, SPEC-0033, SPEC-0034, SPEC-0045, SPEC-0047, ADR-0308, ADR-0310, plan #542, plan #661
- Requirements: REQ-056

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-06:

> Every brief declares a token and a time cap by its size; a builder reports its usage at each milestone; the conductor's sweep marks a build over its cap as OVER and stops it; the overrun is a lesson row with its cause, and the caps are tuned from the weekly scorecard.

The brief is issue #671. The owner's direction, quoted as data from the brief (2026-11-06):
strategy review item 1, "go ahead with your recommendation". It is a ruled exception to plan
#542's requirement freeze, like REQ-052 to REQ-055. This ADR is written by hand in the shape of
ADR-0303, because it names the classes the later builds change, which the fixed text of
`intake.py stub` cannot.

What exists and is reused: the brief's `Size:` line (SPEC-0018 rule 1, `check_brief.py`), the
`Usage:` ending of a builder's `Report:` and its reader `metrics.usage_of` (SPEC-0045 rule 8), the
progress line (session rule 8), `session.py tell` and the `tell` end of `session.py watch`
(session rules 10 and 32), the read-only `conductor.py sweep` (ADR-0308), the stalled offer of
`session.py next` (SPEC-0033 rule 5), the conductor catch log (brief #604) and the rule budget
(ADR-0310).

## Decision

1. REQ-056 is added to `docs/requirements.md` as `planned`, and SPEC-0049 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it.
2. The caps are one optional `[caps]` table of `agk.toml`, a token cap and an hours cap for each
   size `S`, `M` and `L`; without the table nothing is capped, and the kit ships no numbers
   (SPEC-0049 rules 2 and 3).
3. A builder reports its usage on its progress line at every milestone as well as on every
   `Report:`; a missing figure is `not reported`, never 0 and never over (SPEC-0049 rules 4 and 5).
4. `conductor.py sweep` stays read-only and marks a build past a cap with one `OVER` line; hours
   count only while the builder holds the turn (SPEC-0049 rules 6 and 7).
5. The conductor stops a build with one `Tell:` line; the builder pushes a checkpoint, keeps its
   branch and pull request, posts `Report: <head> over cap ...` and ends; the pull request is parked
   until a person rules, and no session stops another (SPEC-0049 rules 8 to 10).
6. Every overrun is one row of kind `over-cap` in the conductor catch log, with a cause from a fixed
   list resting on counts (SPEC-0049 rules 11 and 12).
7. The caps change only by a pull request with an ADR and a `Caps-evidence:` line citing the weekly
   scorecard and the measured usage by size, which a check requires; review and merge work are never
   capped, and no cap moves a gate (SPEC-0049 rules 13 to 15).
8. Per plan #542, this is the one ADR of REQ-056 for the builds of SPEC-0049 rule 18. The builds
   will change these protected path classes: `scripts/agk/` (`config.py`, `caps.py` (new),
   `conductor.py`, `session.py`, `check_protected_changes.py`, builds (b) to (e)), `tests/kit/`
   (their tests), `tests/kit_dev/` (`test_conductor_catches.py`, build (d)), `kit/` (the line of
   `caps.py` in `kit/manifest.json`, build (b)), `agk.toml` (the `[[testing.map]]` entry, build (b),
   and this repository's `[caps]` table, build (e)), `config/` (`config/session-rules.md` rules 8
   and 32 within `config/rule-budget.txt`, build (c)) and `.claude/` (`.claude/agents/conductor.md`
   and `.claude/hooks/conductor_guard.py`, build (d)). A build that changes a class named here and
   no other may cite this ADR with `Covered-by: ADR-0324` once it is Accepted (session rule 36). No
   build changes `constitution/`, `config/reviewers.yaml`, a workflow, the ruleset
   (`kit/templates/ruleset.json`), `.github/CODEOWNERS`, `CLAUDE.md`, `Makefile`, `agk.mk`,
   `pyproject.toml`, `skills/` or `.claude-plugin/`; `kit/hashes.json` and the version stay the
   release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request: no build is capped and the sweep prints what it prints today
until build (b) lands and a project sets a `[caps]` table.

## Residual

None beyond SPEC-0049's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.
