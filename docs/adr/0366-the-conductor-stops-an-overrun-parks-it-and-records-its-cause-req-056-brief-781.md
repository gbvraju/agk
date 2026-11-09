# ADR-0366: The conductor stops an overrun, parks it and records its cause (REQ-056)

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: SPEC-0049, ADR-0324, ADR-0308, ADR-0330, ADR-0310, brief #781, plan #661
- Requirements: REQ-056

Protected classes: `.claude/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0049 build (d) is the conductor's side of a build past its cap (rules 8 and 10 to 12). Builds (b) and (c) added the
`OVER` line and the builder's stop. Brief #781 orders this build to write its own decision record, because the
`Protected classes:` line of ADR-0324 names only `docs/requirements.md` and this build changes `.claude/`, `scripts/agk/`
and the tests.

## Decision

1. The conductor's role file says: on an `OVER` line send the `session.py tell` stop to the session of the build's newest
   take; give no clearing verdict while the pull request is parked; put one `over-cap` row in a report or a brief. The file
   stays within its line of `config/rule-budget.txt`.
2. `conductor.py over --pr N` reads GitHub with GET only and prints the counts of SPEC-0049 rule 12 one per line and the
   cause of the first matching rule. Evidence that cannot be read prints `unknown`, never 0.
3. The conductor guard allows exactly `conductor.py over --pr <n>`, and refuses every other form and the shadow reviewer.
4. The catch-log test holds the shape of an `over-cap` row: counts and numbers only, a cause of the fixed list, and the used
   figure as the cost.
5. Until the owner rules on Q-781-2, `estimate` needs at most half the counted hours to be blocked, so that all five causes
   stay reachable in the order written.

## Consequences

- An overrun ends with one message, a parked pull request and one row with a cause that rests on counts.
- `over` makes one GET per commit and one per head, so a long branch costs more reads. It runs only on an overrun and never
  inside a check.
- A commit date stands in for the time of a push, so a blocked span can read shorter than it was. The cause then leans to
  `estimate` over `blocked`.

## Residual

- 2026-11-09: a builder's checkpoints in a draft have no run, so three of them on one file read as `loop` (Q-781-3); the
  conductor may write another cause with the count that supports it (due 2027-01-31).
