# ADR-0815: An owner-wait park holds until every asked Q id is answered and never keys on the agk:approve label

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: SPEC-0059, ADR-0543, ADR-0646, ADR-0685, ADR-0690, ADR-0657, ADR-0722, ADR-0723, ADR-0725, ADR-0747, ADR-0788, ADR-0813, brief #1968, plan #661
- Requirements: REQ-066

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0059 rule 10 parks a pull request that waits on the owner and unparks it on the owner's answer. Two readings in
`session.open_owner_items` ended parks with no answer. First, the `approve` item came only from the router's
`agk:approve` label, and with `agk:parked` set the router removes every other state label, so the next pass found the
park's key gone and unparked it (#1945 twice, #1949 twice, #1959 once). Second, ADR-0685 decision 1 let one
`Answer: Q-<id>` close every `Owner needed:` naming that id, so one answer ended a three-question ask (#1961).

## Decision

1. **An ask with Q ids closes when each is answered.** For each open `Owner needed:` key, the wait keeps the Q ids its
   newest post names (first line and body) that no answerer answered after it. An `Answer: Q-<id>` or
   `Maintainer answer: Q-<id>` by an answerer removes that id from every open ask; an ask's item closes when its last
   id is answered and none of the approvals it offers is still open. A maintainers question keyed by its own id, that
   no ask holds, closes on its id as before; an ask naming no Q id closes as before; an answer posted before the ask
   counts nothing for it. This narrows ADR-0685 decision 1 to a one-id ask, which behaves as before.
2. **The approval item comes from the comments.** An open `Owner needed:` that offers approvals (`route.approval_ask`)
   is the wait's item, and the `agk:approve` label adds no `approve` item beside it. An approval line closes the
   approvals (`route.answer_step`, ADR-0723) and never an ask's open Q ids (`Q-PF-2`), whether or not the ask offers
   an approval; an ask keyed by the Q id of an open maintainers question it names closes on the approval as ADR-0723's
   tests read (`Q-1968-1`). `Maintainer answer: accept <head>` (or one carried to it, ADR-0685 decision 2) and a
   `Maintainer answer:` naming neither a Q id nor an approval close every item, as before.
3. **A label-only approval park holds.** An `agk:approve` with no approval ask in the comments still opens `approve`
   from the label. While the wait's own park keyed `approve` (`own_park`) holds `agk:parked`, the item stays open until
   an answerer posts, after the `Parked-by:`, the accept of the head, a `Maintainer answer:` naming neither a Q id nor
   an approval, or an approval line for a spec or amendment that a listed verdict's `Approval:` line or `Owner needed:`
   asks or the pull request's changed files change (ADR-0723 decision 3); an approval of anything else counts nothing,
   since the router would set `agk:approve` again. A park keyed `approve` written before this build is held the same
   way. An `agk:parked` removed by hand is repaired as before.
4. **The settled line counts in the wait.** With `[steward] settle_amendments` on (`check_amendments.settle_on`, at the
   checkout found at or above the working folder), `owner_read` adds `settles` (`route.amendment_settles` of the
   changed files at the head, one GET per amendment file, read only when an approval line is named) and `settlers`
   (the spec approvers), and the steward's settled line by a settler closes that amendment's approval as the router
   does (ADR-0813 decision 3). With the setting off nothing more is read.
5. **The closing lines name what is left.** `session.closing_lines` and `session.py ask-lines --pr N` print, for an ask
   with open Q ids, one `Maintainer answer: Q-<id> <your answer>` per open id in the ask's order, then the open
   approvals' lines; any other item keeps `closing_line`'s one line (ADR-0747), which itself is unchanged, so the
   conductor's `Owner needed:` check reads as before. The `Parked-by:` and `Unparked-by:` forms do not change.
6. **One reader.** Every caller (the router's unpark, the conductor's sweep and owner pass, the steward's park and
   unpark, `watch`) decides through `owner_step` over `open_owner_items`; `route.py` does not change, and the router's
   label keeps ADR-0788 decision 3 (`Q-PF-3`). No setting is added.

## Consequences

A park ends only on the owner's answer to what it parked for: no flap from the label the park removes, and no unpark
while an asked question waits. No workflow, label, check or ruleset changes; with `settle_amendments` on, at most one
GET per amendment file in the fresh read.

## Residual

- 2026-11-26: `Q-PF-3`, whether the router's label also keeps an `Owner needed:` until each id is answered, is the
  owner's, in a separate brief.
