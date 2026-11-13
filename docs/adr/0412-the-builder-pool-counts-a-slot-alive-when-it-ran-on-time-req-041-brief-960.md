# ADR-0412: The builder pool counts a slot alive when it ran on time, not only while it holds a lease

- Status: Accepted
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0368, ADR-0402, brief #960, issue #937
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

A slot takes its lease only for the length of a run and releases it on every exit (ADR-0368). `conductor.pool_state`
counted a slot dead whenever it held no valid lease, so an idle pool whose slots all ran on time read as down: on
2026-11-10 issue #937 listed all nine slots `with no valid lease` while the slot tasks ran hourly.

## Decision

1. In `conductor.pool_state` a slot is alive when it holds a valid lease, or when its lease marker (one comment per
   slot, edited in place by `taken`, `renewed` and `released`) by a listed author carries a time younger than
   `slot_seen_minutes` of the `[flow]` table of `agk.toml`. The default is 90: one hourly run plus margin. Dead means
   not seen within that window. The row is still down when more than a third of the slots are dead and briefs wait.
2. The text of `Builder pool down` names each dead slot with the time it was last seen, or `never`, and names the
   settings `builder_slots` and `slot_seen_minutes`, never their values.
3. One issue per title: an open `Builder pool down` is updated in place and no second one is opened (unchanged in
   `route.route_health`, now under test).
4. A `slot_seen_minutes` that is not a whole number of 1 or more is refused naming the setting; the router's health
   step then skips and writes nothing, as for an unreadable lease.
5. `agk.toml` sets `slot_seen_minutes = 90` in its `[flow]` table. The test of `tests/kit/test_pool_health.py` that
   took a slot 11 minutes old for dead now takes one 91 minutes old, the rule of point 1.

## Consequences

`Builder pool down` opens only when slots stop running, not every hour they are idle, and its text tells a stopped
scheduled task from a busy pool. The report's `slot` lines (`slot_lines`) still show the lease alone.

## Residual

- Q-960-1 (2026-11-10): two router runs at once can still each find no open issue and open one each (the #936
  duplicate); closing the newer of two open issues with one title is left to a later brief.
