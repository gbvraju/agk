# ADR-0384: Review capacity follows `max_builders` unless a team sets it

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: SPEC-0034 rule 15, ADR-0153, ADR-0341, brief #842
- Requirements: REQ-041

Protected classes: `agk.toml`, `scripts/agk/`, `tests/kit/`

## Context

`session.py plan` starts the smallest of the ready briefs, the free builder slots and `reviews_in_flight` less the pull
requests waiting for a verdict. ADR-0153 gave `reviews_in_flight` a default of 3, chosen when one person reviewed. This
repository sets `max_builders = 9` (ADR-0341) and never set `reviews_in_flight`, so on 2026-11-09 the plan printed
`Start 0` with 6 of 9 builder slots free. The live conductor clears a pull request in minutes, so the default no longer
measures anything. A second number that nobody typed held builders back.

## Decision

This is build (a) of brief #842, its answer 1. It changes item 8 of ADR-0153 for one setting.

1. When `reviews_in_flight` of the `[flow]` table is unset, it is `max_builders`, instead of 3. The value `max_builders`
   itself has (typed, or its default of 3) is the value used.
2. A value that a team sets still decides, and a value that is not a whole number of 1 or more is still refused, naming
   the setting.
3. This repository's `agk.toml` sets `reviews_in_flight = 9` in `[flow]`, equal to its `max_builders`.

## Consequences

One setting decides the count unless a team lowers review on purpose. A project that sets neither key keeps 3, because
`max_builders` defaults to 3. A project that raised `max_builders` and left `reviews_in_flight` unset now starts more
sessions while pull requests wait for a verdict; it sets `reviews_in_flight` to keep the lower figure.

## Residual

- 2026-11-09: the capacity table, profiles and measurement of brief #842 answers 2 to 6 are not decided here; they wait for
  `docs/runs/proposed-spec-amendments-149.md` and the owner's `Approve:`.
- 2026-11-09: `docs/guides/getting-started.md` still says `reviews_in_flight` is 3 by default, because build (a) names
  `agk.toml` and `session_plan.py` only (Q-842-1 on the pull request).
