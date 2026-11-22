# ADR-0722: An owner merge is labelled and never parked

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1733, brief #1719, brief #1656, brief #1534, brief #1282, ADR-0385, ADR-0543, ADR-0570, ADR-0690
- Requirements: REQ-039, REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

A cleared pull request that the merger holds for the owner (`held: outside author`, `release` or `protected
class`, `merge_cleared.OWNER_HOLDS`) gets the conductor's `Owner needed:` naming
`python3 scripts/agk/merge_cleared.py --pr <n> --owner` (`merge_cleared.OWNER_COMMAND`). The router read that ask
as `agk:question`, and the owner wait (ADR-0543) parked it 30 minutes later: on #1719 the labels went
`agk:merge-ready` (09:28Z), `agk:question` (09:32Z) and `agk:parked` (10:03Z, `Parked-by: wait owner-needed`). The
owner read "parked" and could not tell that only their merge was left. The router gave `agk:owner-merge` only for
a cleared head that changes a path of `OWNER_PATHS`, and the owner wait parked even that label.

## Decision

1. ADR-0385's `agk:owner-merge` now means any cleared head only the owner may merge. In `route.owner_ask`, an
   open `Owner needed:` by a listed verdict author whose body names `merge_cleared.OWNER_COMMAND` for the pull
   request's own number (the constant imported) is a merge ask. It gives `agk:owner-merge` when the pull request
   is not a draft, the latest trusted verdict clears the current head (cleared, a covered fix list whose `Final:`
   lines the head adds, or a covered head) and the ask was posted at or after the head's last push. Otherwise the
   ask is stale and read as absent. An open approval ask (`APPROVAL_ASK`) gives `agk:approve` first, and any other
   open `Owner needed:` or maintainers question gives `agk:question` first. The facts carry the pull request's
   `number`.
2. An `Approve:` or `Maintainer answer:` by a spec approver closes a merge ask as it closes every `Owner needed:`,
   except while an approval ask is open: that answer gives the approval, and the merge ask stays open (the
   approval comes before the merge).
3. ADR-0543 is changed: `session.open_owner_items` keys a merge ask `owner-merge`, never `owner-needed`; it stays
   open while the pull request is not a draft and the newest verdict by a listed verdict author names the current
   head. `session.owner_step` returns `("handover", "owner-merge")` for an `owner-merge` item (from the ask or the
   label) when no other owner item is open, at once, whatever `owner_wait_minutes` and `owner_rest_hours` say; it
   never parks it. `owner_apply` writes nothing for it and returns None, so the conductor and the steward write
   nothing. `watch --pr N` prints `owner-merge #<n>` and the same `next:` hand-over line as a park.
4. `session.running_builders` also leaves out a pull request labelled `agk:owner-merge`.
5. A park written before this change with `Parked-by: wait owner-needed`, whose only open item is now keyed
   `owner-merge`, is removed by the existing `("unpark", key)` step with its `Unparked-by:` comment; no migration
   step is needed. A person's own `agk:parked` is never touched.
6. `[flow] auto_merge = false` and a queue-button-only ask (`merge_queue`) are unchanged (Q-1733-2, Q-1733-3 of the
   brief: later briefs).

## Consequences

The owner sees `agk:owner-merge` on every change that waits only on their merge, and it is never parked. A builder
whose pull request waits on that merge hands over at once and frees its slot. The label still closes at the merge,
at a push after the ask, at a newer verdict that does not clear the head, or at the owner's answer.
