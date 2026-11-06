# ADR-0311: Add REQ-054: Every repository has one weekly scorecard of numbers with thresholds and trends

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: SPEC-0047, SPEC-0012, SPEC-0004, SPEC-0007, SPEC-0032, SPEC-0042, SPEC-0046, ADR-0303, ADR-0310, plan #542, tracker #630
- Requirements: REQ-054

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-06:

> Every repository on AGK has one weekly scorecard of hard numbers with thresholds and trends, so that a slip in speed, quality, security or freshness opens an issue before anyone notices it, whether AGK is still being built, is frozen in use, or the world around it has moved on.

The brief is issue #649, item 10 of tracker #630, widened by the owner's direction, quoted as data
from the brief (conductor chat, 2026-11-06): "this is the important AGK to sustain and stay ahead,
solve the purpose otherwise it can go outdated soon, make it live or think beyond case 1 and case 2
also if it needed to go beyond". It is a ruled exception to plan #542's requirement freeze, like
REQ-052 and REQ-053.

AGK degrades three ways: while it builds itself, numbers slip a step at a time and each step passes
review (case 1); while it is frozen and only used, a slip has no reader (case 2); and while the
world moves, its pins, `(verify)` marks and residual due dates stand still, so it goes outdated
with no number slipping (case 3). Levels against hard lines cover case 1, lines that open issues
cover case 2, and freshness numbers and trends cover case 3.

What exists and is reused: the per-pull-request and weekly readers of `metrics.py` (SPEC-0007),
`facts.py` (SPEC-0009), `minutes.py`, `full_run.py`, `rules.py budget` (ADR-0310, kit-only), the
drift audit's residual reader (SPEC-0004 D4) and its `--previous` body, the red-branch issue of
SPEC-0032 rule 7, the failure issues of SPEC-0046 and the data guard's `guard.scan_text`
(SPEC-0042 rule 10).

## Decision

1. REQ-054 is added to `docs/requirements.md` as `planned`, and SPEC-0047 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it.
2. The scorecard reads level, trend and freshness numbers of the week (SPEC-0047 rule 1), from the
   repository's own history, issues, comments and CI runs with GET requests only, and one GET per
   pinned tool for upstream versions; no governance check, `make governance` or `prepush.py` step
   runs it, so checks still make no network call (SPEC-0047 rule 2).
3. The lines and trend windows are a `[scorecard]` table of `agk.toml` with kit defaults marked
   `(verify)`; a malformed table is refused naming the setting; changing a line is a protected
   change with an ADR, so nothing lowers one silently (SPEC-0047 rule 3).
4. A metric above its line, or higher three weeks in a row within the last four, is a finding; one
   `agk-scorecard` issue per metric name holds numbers only, a repeat adds a comment, and the issue
   closes itself after two weeks inside its line. The scorecard blocks nothing (SPEC-0047 rules 4
   and 5).
5. It runs as a separate, non-blocking step of the weekly drift audit job, and its trend history is
   the last four weeks carried in the audit issue's body, so no file grows. That needs amendment
   128 of SPEC-0004 (rules 2, 3, 13, 14 and 21, for the scorecard step only) and the owner's
   `Approve: SPEC-0004`; `drift_audit.py` is unchanged (SPEC-0047 rules 6 and 7).
6. A project's numbers stay in its own repository; the kit ships no collector; publishing counts
   to a place the owner names is parked (SPEC-0047 rule 10).
7. Per plan #542, this is the one ADR of REQ-054 for the builds of SPEC-0047 rule 11 other than
   (e). The builds will change these protected path classes: `scripts/agk/` (`scorecard.py`,
   `config.py`, builds (b), (c) and (d)), `tests/kit/` (their tests, builds (b), (c), (d) and (f)),
   `kit/` (`kit/manifest.json` for the new installed script, build (b)) and `agk.toml` (the
   `[[testing.map]]` entry, build (b), and the `[scorecard]` table with this repository's own
   lines, build (f)). A build that changes a class named here and no other may cite this ADR with
   `Covered-by: ADR-0311` once it is Accepted (session rule 36). Build (e) changes
   `.github/workflows/drift-audit.yml` (the scorecard step and `actions: read`) and
   `.claude/agents/conductor.md` (reading `agk-scorecard` issues), and carries amendment 128 of
   SPEC-0004, so it writes its own ADR, as session rule 36 requires for a workflow, and it is on
   the owner's hold list. No build changes `constitution/`, `config/reviewers.yaml`, the ruleset
   (`kit/templates/ruleset.json`), `.github/CODEOWNERS`, `CLAUDE.md`, `Makefile`, `agk.mk`,
   `pyproject.toml`, `skills/` or `.claude-plugin/`; `kit/hashes.json` and the version stay the
   release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request; until build (b) lands there is no scorecard, and until build (e)
lands and amendment 128 is approved the drift audit is unchanged and the scorecard runs only when a
person starts it.

## Residual

None beyond SPEC-0047's residual. The intake checks cannot tell whether the metrics and lines are
the right ones; that is the review of this pull request.
