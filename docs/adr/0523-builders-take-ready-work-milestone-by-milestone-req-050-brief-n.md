# ADR-0523: Builders take ready work milestone by milestone, the most-unblocking brief first

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0034 rule 15, amendment 181, ADR-0153, ADR-0318, ADR-0465, brief #1232, plan #661
- Requirements: REQ-050

## Context

`session.py plan` (`scripts/agk/session_plan.py`, used by `/agk:launch` and the conductor) offers ready briefs from any
milestone in the order `candidates` gives: priority, then number (read in the code; the brief says priority, size and
number, but no size key is in the order). It does not look at milestones or at what a brief unblocks. The owner saw
eight builders on M1 with four idle for dependences while ready work of later milestones waited (brief #1232). In a
planned project an idle builder could take a brief after go-live while the current milestone's work waits, and small
briefs started before the brief that others depend on.

## Decision

1. Each ready brief's milestone is the GitHub milestone of its issue (the `milestone` of the open-briefs read the plan
   already makes; no new read), ordered by `due_on`, a milestone without a due date after those with one, then its
   number; a brief without one comes last. The ready briefs are ordered by milestone before the waves and the capacity,
   so free slots fill from the earliest milestone that has a ready, non-overlapping brief and reach a later one only
   when the earlier ones have none. Overlap, `Blocked-by`, capacity, reviews, the merge-queue limit and a red branch's
   fix brief apply as before.
2. Within a milestone: the brief whose dependants carry the most hours first (every open brief whose `Depends-on: #n`
   names it, directly or further down, each counted once, a cycle ended), then priority, then the smaller own hours,
   then number. A brief's hours are the mid point of its `Expected:` range, else S 3 hours and M 6 hours, else none: 0
   as a dependant, last among its own milestone (Q-1232-1). With a declared playbook the lane order of ADR-0318 applies
   inside each milestone, and this order breaks its ties in place of the number.
3. `[plan] active_milestones` (a list of non-empty titles, `common.plan_settings`) leaves every brief outside them
   unstarted, listed as skipped `not in an active milestone (setting: [plan] active_milestones)`; when absent every
   milestone is active. A wrong value is refused naming the setting, never the value.
4. The plan prints `#<n> <milestone>: unblocks <h> h.` for each start and, for each free slot it cannot fill,
   `idle: no ready brief in <milestones>[; first wait: <wait>].`, the milestones in order and the wait the first one in
   the earliest milestone (an overlap wait or a `waits for` skip); none while the merge queue holds the starts. The data
   (`--json`) carries them as `milestones`. A plan with no milestone on any open brief and no `active_milestones` prints
   and returns exactly what it did before (Q-1232-2).
5. `session.py next` and `claim` keep their order; this is the plan's order, which `/agk:launch`, the conductor and the
   review pass use.

## Consequences

A milestone's demo lands first, and an idle builder takes the next milestone's work instead of waiting. Projects
without milestones see no change. SPEC-0034 rule 15 says nothing of the order; the lines are proposed in
`docs/runs/proposed-spec-amendments-181.md` (amendment 181, the conductor's correction on brief #1232), not applied
here. Protected path classes changed: `scripts/agk/` (`session_plan.py`, `common.py` for the `[plan]` key),
`tests/kit/` (`test_session_plan_milestones.py`, new) and `agk.toml` (the new test file added to the
`[[testing.map]]` entries of `scripts/agk/session_plan.py` and `scripts/agk/session.py`, nothing else).

## Residual

- 2026-11-14: Q-1232-1 (an `L` brief or one with no size counts no hours) and Q-1232-2 (no new lines without
  milestones) are this session's conservative readings, for the maintainers.
- 2026-11-14: amendment 181 (SPEC-0034 rule 15) waits for the maintainers' decision.
