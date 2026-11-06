# ADR-0294: The conductor learns from a catch log, each incident turned into a check, a test or a rule line (REQ-037, brief 604)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0265, ADR-0271, ADR-0277
- Requirements: REQ-037

Protected classes: `.claude/`, `tests/kit_dev/`

## Context

The owner directed on 2026-11-06 (chat, quoted as data from brief #604) that the conductor's real learnings be adopted into the
kit. The review checklist already grows from the architect catch logs; the conductor's operating lessons lived only in one
session's notes.

## Decision

1. **A conductor catch log**, `docs/runs/conductor-catches-1.md`, in the shape of the architect catch logs: per row the date,
   the kind (its own fixed list, none shared with the architect kinds), what happened (counts and timings only), the cost, the
   cause and the guard, seeded with the twelve incidents of 2026-11-04 to 2026-11-06.
2. **A guard per row**, of four forms: `check <path>`, `test <path>`, `rule <path>` (a line of the conductor role file) or
   `pending #n`; several per row, strongest first.
3. **`.claude/agents/conductor.md` gains "Operating lessons"**: one line per `rule` row, citing it; an incident is logged before
   the conductor reports it; the strongest guard first (a check before a test before a rule line); each `rule` row is revisited
   monthly. The conductor writes no file, so it puts the row in the brief it files or in its report for a person to add.
4. **`config/review-checklist.md` is unchanged**: no conductor kind is one it reads.
5. **Tests.** `tests/kit_dev/test_conductor_catches.py` checks that the log parses with its columns, each row's kind, cost, cause
   and guard form, that every `check` or `test` path exists, that every `rule` row is cited by a lesson line and every lesson line
   cites a `rule` row, and that a `pending` guard names an issue number (its form only; no network).

## Consequences

A lesson of a conductor run lands as a row and its guard in one pull request. Seven of the twelve rows are guarded by a rule
line only, which holds only as far as the conductor reads it; the monthly revisit is the path to a check.

## Residual

- 2026-11-06: the tests read a `pending #n` for its form, not whether the issue is open or merged (no network in tests); a stale
  number is found by a person reading the row (due 2026-12-31).
- 2026-11-06: the monthly revisit of the `rule` rows has no check of its own (due 2026-12-31).
