# ADR-0485: The merger starts when the default branch turns green

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0032, SPEC-0039, ADR-0373, ADR-0383, ADR-0476, brief #1143, plan #661
- Requirements: REQ-039

## Context

ADR-0476 made the router start `merger.yml` (with `workflow_dispatch` and the input `pr`) only in a run that labels a pull
request `agk:merge-ready` when it did not have that label. A pull request labelled `agk:merge-ready` while the default
branch is red is held by `merge_cleared.py`, and when the branch turns green no run labels it again, so nothing starts the
merger for it until the 15-minute scheduled sweep, which GitHub drops under load (the conductor reported `SWEEP late 60
min` on 2026-11-12). Measured on 2026-11-12: the default branch was red from 20:40Z until 21:42Z; #1135 and #1138, labelled
`agk:merge-ready` while it was red, merged only after a person dispatched the merger by hand for each at 21:43Z. The
owner's word for the merger (2026-11-13, IST): it "can sit for trigger, no load".

## Decision

1. The router starts the merger when the default branch turns green. A run of the event job of `route.py` for the
   default branch (a push to it, or a finished workflow on it) that reads its required checks green, and either closes
   the red-branch issue in this run or finds that the head was pending or red without the check runs of the check suite
   of the finished workflow that woke it (`turned_green`), starts `merger.yml` once with `workflow_dispatch` and the input
   `pr` for every open pull request labelled `agk:merge-ready`, by the same call as ADR-0476 decision 1, and not twice
   for a pull request that entered that state in the same run. It does so only while `[flow] auto_merge = true` in
   GitHub mode (`merger_on`). A branch that stays green, stays red or still runs starts nothing; `--branch`, `--pr`,
   `--all` and `--dry-run` start nothing. A list of open pull requests that cannot be read fails the run naming rule 7;
   the red-branch issue is closed first.
2. The merger's triggers are a verdict or approval comment, the `agk/verdict` status, a pull request entering
   `agk:merge-ready`, the default branch turning green, a failed merge queue run and a dispatch by hand. The 15-minute
   `schedule:` of `merger.yml` stays, because a review of every start found three paths that only it covers: (a) a start
   the router's token is refused (ADR-0476: one line, the label stays); (b) a merger run that ends without a merge (an
   error of GitHub, an environment wait past the job's limit) on a pull request whose label does not change, so no
   router run starts it again; (c) the conductor's `SWEEP late` signal, which counts finished sweep runs of `merger.yml`.
   No workflow file changes.
3. The protected path classes this decision changes are `scripts/agk/` (`route.py`) and `tests/kit/`
   (`test_route_red.py`, `test_merger_trigger.py`).

## Consequences

A pull request cleared while the default branch is red, or while its checks still run after a merge, is merged by the
router's run that sees the branch green, with no person and no wait for a scheduled sweep. The cost is one dispatch per
`agk:merge-ready` pull request at each turn to green, from a router run that already runs. Two finished workflows whose
router runs both read the other's checks done can each start the merger for the same pull request; the merger's group is
one per pull request and the second run finds the head merged, so the cost is one short job.

## Residual

- 2026-11-12: dropping the schedule needs a trigger for paths (a) to (c) first (a retry of a refused start, a router
  start after a merger run that ends without a merge, and a `SWEEP late` that counts dispatched runs); `Q-1143-1` asks
  the maintainers whether to drop it anyway (due 2026-11-30).
- 2026-11-12: `turned_green` reads the check suite of the waking run from `workflow_run.check_suite_id` and
  `check_suite.id` of a check run, read from GitHub's payloads, not its documentation (verify, due 2026-11-30).
