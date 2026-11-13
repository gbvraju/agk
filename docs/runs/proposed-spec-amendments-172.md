# Proposed spec amendments 172 (SPEC-0032; REQ-039)

Date: 2026-11-13 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0497 (brief #1168), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md`. It amends amendment 150
item 1 (the `agk:question` state) and its reading `Q-846-4`. The numbers 172 and 0497 are the ones brief #1168 reserved.
The owner decides it with `Approve: <head> SPEC-0032` on the pull request; no session posts that line.

The sentence (brief #1168): "An owner ask on a pull request stays open, and the merge waits, until the owner answers it; a
new commit on the branch no longer closes it."

## What is on the default branch today

Read in the code by this session on `origin/main` (8143696):

- `scripts/agk/route.py` `asks_owner` closes an `Owner needed:` by a listed verdict author at a later `Maintainer answer:`
  or `Approve:` by an account in `spec_approvers`, or at a head whose committer date is not before the ask
  (`open_ask = not pushed or created_at >= pushed`), as amendment 150 item 1 and `Q-846-4` read.
- `scripts/agk/merge_cleared.py` holds `owner ask (rule 5)` on the label `agk:question` alone (brief #1134, ADR-0483).
- Measured (brief #1168): on #1165, `Owner needed:` (size) at 00:17:11Z, labelled `agk:question` at 00:17:31Z; the
  builder's merge of the default branch at 00:33Z, unlabelled `agk:question` at 00:33:59Z; merged at 00:49:25Z with no
  `Maintainer answer:` on it.

## Items

1. **Amendment 150 item 1, the `agk:question` state, replaced.** "`agk:question` (owner): an `Owner needed:` comment by a
   listed verdict author on the pull request has no later `Maintainer answer:` or `Approve:` by an account in
   `spec_approvers`; a new head does not close it. A comment whose first line starts `Question: Q-` and contains
   `for the maintainers`, by any author, has no later such answer and no later head (ADR-0442). The two are read
   apart: the state holds while either is open, and a question never closes an `Owner needed:`."
2. **`Q-846-4`, its reading replaced.** "An `Owner needed:` comment by a listed verdict author on the pull request, closed
   only by a later `Maintainer answer:` or `Approve:` by an account in `spec_approvers`."
3. **No other change.** `merge_cleared.py`, the labels, their order and every workflow stay as they are: the merger still
   holds on `agk:question`, which now stays on the pull request through a push.
4. **Tests.** `tests/kit/test_route_owner_ask.py`: an `Owner needed:` followed by a push keeps `agk:question`, on a draft
   too, and a router run on it writes no label; a later `Maintainer answer:` or `Approve:` by a spec approver clears it,
   and one by another account or one before the ask does not; a `Question: Q-1-1 for the maintainers` followed by a push
   still clears; an `Owner needed:`, then such a question, then a push keeps `agk:question`; an `Owner needed:` by an unlisted account still asks nothing.
