# ADR-0416: A cleared pull request joins the merge queue, and no branch must be up to date before it merges

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0339, ADR-0354, ADR-0387, amendment 151, amendment 158, brief #971, brief #972, plan #661
- Requirements: REQ-046, REQ-057

## Context

On 2026-11-10, 00:00 to 13:20 IST, 76 pull-request `governance` runs took 443 minutes, and 30 of them (203 minutes, 46%)
ran only because the branch had merged the default branch: the ruleset requires a branch to be up to date before it
merges (asked for by ADR-0387), so every merge sends every open pull request back through its checks. #949 passed its own
change in 1 minute, then ran 21 and 24 minutes on two merges of the default branch.

Two guards already make that rule unnecessary: SPEC-0050 rule 6 (brief #727, ADR-0339) holds a pull request whose files
the default branch changed since its merge base, and `merge_cleared.py` runs governance and `[testing] pre_merge_tests`
on the would-be merge before it merges (SPEC-0039 rule 6, briefs #667 and #765). The `[flow] merge_queue` key exists
(brief #853, ADR-0387), but today it only holds the merge and asks the queue to require `agk/verdict`, a status set only
on a pull request's head, which the queue's commit never carries. The owner approved GitHub's merge queue on #661
(2026-11-10T07:54Z).

## Decision

1. With `[flow] merge_queue = true`, GitHub mode and `auto_merge = true`, the guarded command applies every hold it has
   today and then adds the cleared head to GitHub's merge queue, pinned to that sha, instead of merging it
   (amendment 158 items 1 and 2).
2. `governance` and `proof` run on `merge_group` with the selected tests of the batch plus the pre-merge tests, and are the
   queue's only required checks; no head-only status, `agk/verdict` included, is required by the queue (item 3).
3. A pull request the queue removes for a failed check gets one comment naming the check and the queue sha, and the
   router's `agk:ci-red` label (item 4).
4. The up-to-date rule is off in every mode; the owner sets the ruleset by the guide, and no session sets or reads it
   (items 5 and 6). `doctor.py` prints `merge queue: on|off` from the setting alone (item 7).
5. Local and personal mode, and `merge_queue = false`, are unchanged: re-prove only on overlap, as SPEC-0050 rule 6.

This replaces item 4 and the strict ruleset of item 3 of amendment 151 (ADR-0387, Proposed).

## Consequences

No pull request re-runs its checks only because the default branch moved, with the queue on or off. With the queue on,
GitHub tests up to 5 pull requests together on top of the default branch, so the default branch never receives an untested
combination. This pull request changes documents only; brief #972 builds it, with its own ADR naming the protected classes
it changes, after the owner's `Approve: <head> SPEC-0039`.

## Residual

- 2026-11-10: whether GitHub offers the merge queue to a repository owned by a personal account, as `gbvraju/agk` is, is
  `(verify)` (`Q-S0039-16`); until the owner confirms it, this repository keeps the queue off and gains only the
  up-to-date change (due 2026-11-30).
- 2026-11-10: whether the enqueue call exists in REST is `(verify)` (`Q-S0039-19`); if only GraphQL offers it, the one call
  is the merger job's alone (due 2026-11-30).
- 2026-11-10: the queue's run and the queue-off path test the selection, not the full suite; the push's full run and the
  red-branch stop catch what the selection misses (due 2026-12-31).
