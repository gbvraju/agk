# Proposed spec amendments 181 (SPEC-0034; REQ-050)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0523 (brief #1232), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`. Brief #1232 named amendment 178,
already used on the default branch; the conductor's `Correction:` on the brief reserved 181. This file proposes the
lines and does not edit the spec.

The sentence (brief #1232): "Builders take ready work milestone by milestone: the earliest milestone first, the brief
that unblocks the most remaining hours first, and a later milestone only when the earlier ones have nothing ready, so no
builder sits idle and each milestone's demo lands first."

## Items

1. **Rule 15 gains one bullet after "The sessions to start":** "**The order.** The ready briefs are ordered by the
   GitHub milestone of their issue (by `due_on`, one without a due date after, then number; a brief without a milestone
   last), so the slots fill from the earliest milestone with a ready, non-overlapping brief and reach a later one only
   when the earlier ones have none; within a milestone by the hours of their dependants (every open brief whose
   `Depends-on` names it, directly or further down, by the mid point of its `Expected:` range, else S 3 and M 6 hours),
   then priority, then the smaller own hours, then number. `[plan] active_milestones`, a list of titles, keeps every
   other milestone's briefs unstarted. The plan prints `#<n> <milestone>: unblocks <h> h.` for each start and
   `idle: no ready brief in <milestones>[; first wait: <wait>].` for each free slot it cannot fill; with no milestone
   and no `active_milestones` it prints what it did before."
2. **Rule 3's order** ("orders by `Priority` ... then the oldest issue") stays the order of `next`; the plan's order is
   item 1's.
3. **Tests.** `tests/kit/test_session_plan_milestones.py`; the existing `tests/kit/test_session_plan*.py` unchanged.
