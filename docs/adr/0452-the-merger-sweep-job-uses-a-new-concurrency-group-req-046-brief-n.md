# ADR-0452: The merger's sweep job uses a new concurrency group

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: brief #1066, brief #836, plan #661, ADR-0271, pull request #1051, pull request #1060, Q-1066-1
- Requirements: REQ-046

Protected classes: `.github/`, `tests/kit/`

## Context

The `sweep` job of `.github/workflows/merger.yml` has `concurrency: group: agk-merger-sweep-job` with
`cancel-in-progress: false` and `environment: merge`, so one sweep runs at a time across pull requests (brief #836
answer 3).

Run 42669997036 (created 2026-11-09T17:59:56Z) has its `sweep` job `waiting` for the `merge` environment, with no
reviewer listed and `current_user_can_approve: false` (measured 2026-11-12 with
`gh api repos/gbvraju/agk/actions/runs/42669997036/pending_deployments`). The run cannot be cancelled: the API answers
that it is completed or not yet queued, and the owner's Cancel button and the Settings route both fail. Because the
waiting job holds the group and `cancel-in-progress` is false, every later sweep stays `pending` behind it (run
43033775784 for pull request #1051), and the cleared pull requests #1051 and #1060 were merged by the owner by hand.

## Decision

1. The `sweep` job's concurrency group is `agk-merger-sweep-job-2`. `cancel-in-progress: false` and the rest of the
   workflow stay as they are, so one sweep at a time across pull requests still holds. The stuck run keeps the old
   group, which no later run uses, and it expires on its own.
2. `tests/kit/test_sweep_on_workflow_run.py::test_one_sweep_at_a_time_across_pull_requests` asserts the new group
   name and still asserts `cancel-in-progress: false`.
3. A builder never changes a workflow file: the one-line edit of `.github/workflows/merger.yml` is committed on the
   pull request's branch by the owner, and the owner merges it.

## Consequences

The first sweep after the merge runs instead of staying pending, and a cleared pull request merges without the
owner. No check is weakened (principle 11): the test asserts the same shape with the new name.

## Residual

- 2026-11-30: a sweep job that waits for an environment holds its group with no time limit, so a later brief makes
  `conductor.py sweep` report a merger run that has waited more than an hour.
