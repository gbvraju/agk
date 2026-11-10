# ADR-0417: The merger queues cleared heads, and governance and proof run on the merge queue's commit

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: brief #972 (build (a) of amendment 158), brief #971, ADR-0416, ADR-0387, ADR-0354, SPEC-0039, SPEC-0050 rule 6, plan #661
- Requirements: REQ-046, REQ-057

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

ADR-0416 (Accepted) decided that, with `[flow] merge_queue = true` in GitHub mode, a cleared pull request joins GitHub's
merge queue instead of being merged, and that `governance` and `proof` run on the queue's commit. Brief #972 builds it.
The owner's yes for the workflow changes is quoted in the brief (#661, 2026-11-10T07:54Z). The co-owner's narrowing on
#972 records that GitHub offers the merge queue only to organization-owned repositories (verify), so this repository
keeps `merge_queue = false`; the merger job's timeout is the part that helps here as well.

## Decision

1. `scripts/agk/merge_cleared.py`: with `merge_queue = true`, GitHub mode and not local mode, every hold of today runs
   first in the same order, including the governance and pre-merge run on the would-be merge (`Q-S0039-18`). Then,
   only inside GitHub Actions (`GITHUB_ACTIONS=true`, the merger job) with the job's own `AGK_MERGE_TOKEN`, the command adds the head to the queue with
   GraphQL's `enqueuePullRequest`, `expectedHeadOid` set to the cleared sha, and prints `queued`; a head already queued
   prints `already queued`; a head GitHub reports as moved prints `refused: head moved`. Outside Actions it is refused
   with a line naming rule 2a, before any GraphQL call, and so is a run without that token: sessions stay REST-only. A
   head with a `Removed from the merge queue:` line newer than its clearing verdict is held until a new verdict (rule 2c),
   so a sweep never queues a removed head again. With the setting off it merges as today.
2. `.github/workflows/governance.yml` and `proof.yml` run on `merge_group: types: [checks_requested]`, on the queue's
   commit. Governance's test steps run the full suite there, a superset of the batch's selection, `always_full` and
   `[testing] pre_merge_tests`, because the kit's selection reads only the `pull_request` event and its files are outside
   the brief (`Q-972-5`); the secret scan covers the queue's base to its commit, and the `Paused` step reads the queue's
   base sha, so a batch member that adds `paused = true` is still checked in full. `AGK_BASE` stays set by the one
   `Base of the merge ref` step alone; without it a check that reads the body would diff the whole batch against an
   empty body, so `check_protected_changes`, `check_specs` and `check_final_clearance` are skipped on `merge_group`, as
   are the pull-request body checks: each passed on its own head. Proof takes the default branch as its base. Job and
   check names do not change.
3. `.github/workflows/merger.yml`: the merger job ends after 30 minutes of running (`timeout-minutes`), and a step of
   that job, on a failed `governance` or `proof` run of `merge_group`, posts one `Removed from the merge queue: <check>
   failed on <sha12>` line on the pull request the queue branch names, only when GitHub removed it (open, not merged,
   not in the queue, read with the merger's token), never twice for one queue sha (no new job: the cost rule). The
   `dequeued` event that amendment 158 names is not used: only a `pull_request` or `pull_request_target` trigger
   delivers it, and the merger starts only on events GitHub runs from the default branch (`Q-972-6`).
4. `agk.toml` carries `merge_queue = false` with this ADR; `doctor.py` prints `merge queue: on|off` from the setting
   alone. The getting-started guide gives the ruleset settings and the switch-over order.

## Consequences

A project in an organization-owned repository can turn the queue on with one setting after the owner sets the ruleset;
until then nothing changes. The GraphQL call is made only from the merger job's token on Actions.

## Residual

- 2026-11-10: the GraphQL names (`enqueuePullRequest`, `expectedHeadOid`, `isInMergeQueue`), the queue branch name
  `gh-readonly-queue/<base>/pr-<n>-<sha>` and the error text of a moved head are read from GitHub's documentation, not
  from a live call `(verify)` (due 2026-11-30).
- 2026-11-10: whether `timeout-minutes` bounds a job's wait for its environment's approval is `(verify)` (due 2026-11-30).
  Until it is confirmed the timeout is known to end only a run that hangs while running; a run that waits on the `merge`
  environment may still block later merger runs, and the owner then cancels it by hand.
- 2026-11-10: a batch member that the queue branch does not name gets no removal line, and the line is read from the
  state after the failed run (not in the queue, not merged), not from the `dequeued` event (`Q-972-6`, verify).
