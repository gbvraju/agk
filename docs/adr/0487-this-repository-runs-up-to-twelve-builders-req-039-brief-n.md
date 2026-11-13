# ADR-0487: This repository runs up to twelve builders

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: ADR-0341, ADR-0384, ADR-0486, brief #1148, brief #1145, plan #661
- Requirements: REQ-039

## Context

The team guide (brief #1145, ADR-0486) says how four people on four laptops work one repository and left `max_builders`
at 6 for the owner to rule on (Q-1145-1). The owner answered on #1146, 2026-11-12 22:45Z: "Maintainer answer: Q-1145-1
raise max_builders to 12". `session.py plan` caps its `Assign` rows by `max_builders` and prints `Capacity: <n> of
<max>`; `agk.toml` is a protected path class.

## Decision

1. `[flow] max_builders = 12` in this repository's `agk.toml`, so four people with three builders each can work at once.
2. `reviews_in_flight` stays as it is on the default branch (9, pinned by `test_this_repository_sets_its_review_capacity`);
   this ADR does not change the conductor's review capacity.
3. `tests/kit/test_plan_holders.py` reads the repository's `[flow]` table and now pins `of 12`; no test of the rule changes.

Protected path classes changed: `agk.toml`, `tests/kit/` (`test_plan_holders.py`).

## Consequences

`session.py plan` prints `Capacity: <n> of 12`. No installed file changes, so no changelog fragment.

## Residual

- 2026-11-12: the conductor reviews at most 9 pull requests at once while up to 12 builders run; a change of
  `reviews_in_flight` is the maintainers' (Q-1148-1, due 2027-01-31).
