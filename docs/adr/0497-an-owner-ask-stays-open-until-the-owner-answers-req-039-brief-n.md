# ADR-0497: An owner ask stays open until the owner answers

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: brief #1168, plan #661, amendment 172, amendment 150 item 1, Q-846-4, ADR-0385, ADR-0442, ADR-0483
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

`route.asks_owner` closed an `Owner needed:` by a listed verdict author at a later answer by a spec approver or at a
head pushed after it (amendment 150 item 1, `Q-846-4`). The merger holds `owner ask (rule 5)` only on the label
`agk:question` (ADR-0483). On 2026-11-13 #1165 carried an `Owner needed:` on its size from 00:17Z; the builder's merge of
the default branch at 00:33Z removed `agk:question`, and the pull request merged at 00:49Z with no `Maintainer answer:`.

## Decision

1. An `Owner needed:` comment by a listed verdict author closes only at a later `Maintainer answer:` or `Approve:` by an
   account in `spec_approvers`, in the order GitHub lists the comments. A new head no longer closes it.
2. A builder's `Question: Q-... for the maintainers` closes as before: at such an answer or at a head pushed after it,
   since the builder may have resolved it (ADR-0442).
3. The change is in `scripts/agk/route.py` `asks_owner` alone; `merge_cleared.py`, the labels and the workflows do not
   change. `tests/kit/test_route_owner_ask.py` holds its tests and is listed in the `route.py` entry of `[[testing.map]]`
   in `agk.toml`. Two assertions of the existing route tests that read a push as closing an `Owner needed:` now read it
   as staying open.
4. The conductor catch log gets row 27 (`owner-ask-unholds`, #1165), and the row count of
   `tests/kit_dev/test_conductor_catches.py` moves from 26 to 27.

## Consequences

In every project that installs the router, a pull request the conductor asked the owner about keeps `agk:question`, and
so stays held by the merger, through any push, until the owner answers; a conductor that no longer needs the answer says
so to the owner, who answers. Amendment 172 is applied to SPEC-0032 by the owner's `Approve: <head> SPEC-0032`.

## Residual

- 2026-11-13: the after-measure is the brief's: a pull request with an unanswered `Owner needed:` keeps `agk:question`
  after a push, at the router's next event.
