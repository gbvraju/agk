# ADR-0442: A draft that waits on the owner shows agk:question

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: brief #1043, plan #661, amendment 150 item 1, Q-846-4, ADR-0385, Q-1023-1
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

`route.state_of` returned `agk:build` for every draft before it read `asks_owner`, and `asks_owner` counted only an
`Owner needed:` comment by a listed verdict author. On 2026-11-11 the drafts #1040 (`Question: Q-1023-2`) and #1041
(`Question: Q-1030-1`) each waited on an answer only the owner could give and both showed `agk:build`; the owner
found the questions only by reading the comments. The owner's word, 2026-11-11 12:04 IST: "File it".

## Decision

1. `asks_owner` also counts a comment whose first line starts `Question: Q-` and contains the words
   `for the maintainers`, by any author. It closes as an `Owner needed:` does: a later `Maintainer answer:` or
   `Approve:` by a spec approver, or a head pushed after it.
2. `state_of` reads `asks_owner` right after the parked check and before the draft check, so a draft that waits on
   the owner shows `agk:question`. The other states keep their order.
3. A `Question:` without those words still asks the conductor, and a draft that has one stays `agk:build`.

## Consequences

The label filter `agk:question` lists every pull request the owner must act on, drafts included, in every project
that installs the router. A builder that needs the owner writes `for the maintainers` on the first line of its
`Question:`; the cloud builder's prompt carries the phrase (the co-owner's edit, outside this change). Because the
check now comes before the conflict and check states, a ready pull request with an open ask shows `agk:question`
also while its checks run, fail or it conflicts, where before those states came first.

## Residual

- 2026-11-11: the after-measure is the brief's: a draft with an unanswered `for the maintainers` question shows
  `agk:question` at the router's next event.
