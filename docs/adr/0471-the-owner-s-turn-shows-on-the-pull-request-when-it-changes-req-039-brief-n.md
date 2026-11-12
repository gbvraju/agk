# ADR-0471: The owner's turn shows on the pull request when it changes

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: brief #1101, plan #661, SPEC-0032 rule 2, amendment 150, amendment 162, ADR-0385, ADR-0442, ADR-0453
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `.github/`

## Context

On 2026-11-12 #1087 and #1088 read `agk:fix`, the builder's turn, from 14:29 to about 15:55 IST while both waited only
for the owner's size rulings; their builders had already answered "nothing to change". Two causes, read in the code:
`route.base_state` returns `agk:fix` before it asks `asks_owner` (amendment 150's order, ADR-0385 decision 2), and
`agk-route.yml` starts the router on a comment only when its first line starts `Verdict:`, `Approve:`, `Approval:`,
`Correction:`, `Assign:`, `Request:` or an edited `Final:`, so an `Owner needed:`, a builder's `Question:` for the
maintainers (ADR-0442), a `Maintainer answer:` and a `Report:` hand-over (ADR-0453) changed no label until another
event came. The owner's word, 2026-11-12 15:55 IST: "see the best way to follow consistency in all features across
AGK. Don't leave gaps".

## Decision

1. `route.base_state` decides an open owner ask (`asks_owner`) right after `agk:parked`, before `agk:conflict`, the
   checks and every builder state, on a draft and on a ready pull request alike; so a pull request that waits for the
   owner reads `agk:question`, and the owner's turn wins over the builder's. A `Maintainer answer:` or `Approve:` by
   a spec approver, or a later push, closes the ask as before, and the state the facts give returns. This changes the
   precedence of ADR-0385 decision 2 for `agk:question` only; SPEC-0032 rule 2's list of states is unchanged.
2. `route.state_of` replaces only a builder's state with `agk:handover`, and never an owner's state (`OWNER_STATES`:
   `agk:question`, `agk:approve`, `agk:owner-merge`, `agk:parked`), so a builder that hands over while the owner is
   asked is not restarted for nothing.
3. `agk-route.yml` also starts the router on a created comment whose first line starts `Owner needed:`, `Question:`,
   `Maintainer answer:` or `Report:`. A builder never changes a workflow: the owner commits the new `if:` line on the
   pull request's branch (`Q-1101-1`).

## Consequences

A pull request's label changes the moment the owner is asked or answers, or a builder asks or hands over. Each such
comment starts one router job, billed as at least one minute (ADR-0207). The conductor's habit of posting its
`Owner needed:` on the pull request it concerns, not only on the plan issue, is the co-owner's change to the long
conductor's prompt, outside this repository.

## Residual

- 2026-11-12: an `Owner needed:` posted only on a plan issue still sets no label on the pull request it concerns;
  the conductor's prompt change covers it (due 2026-12-31).
