# ADR-0476: The merger starts only when a pull request can merge

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0032, SPEC-0039, ADR-0207, ADR-0354, ADR-0373, ADR-0383, ADR-0387, ADR-0417, ADR-0452, ADR-0184, brief #1116, plan #661
- Requirements: REQ-039

## Context

On 2026-11-12 (00:00 to 20:30 IST) the co-owner counted about 2,730 Actions minutes for 23 merged pull requests, by the rule
of `minutes.py` (each job that was not skipped, from its start to its end, rounded up to a whole minute). The merger
workflow took 44% of them: `merger.yml` starts on every completed `governance` and `proof` run of every pull request
(`workflow_run`), and each such run runs the job `merger` (which finds nothing unless the head carries a clearing
verdict), then `sweep-gate` and `sweep` (ADR-0383: GitHub drops scheduled runs under load). The router (`agk-route.yml`,
`route.py`) already starts on every one of those finished runs and labels each pull request; `agk:merge-ready` is its
state for a head that is cleared, with green checks, and that no person must merge (ADR-0385). `minutes.py` reads the run
list with one filtered query, which GitHub caps at 1,000 runs, so for this repository (about 2,500 runs a day) it printed
`at least 688` for the month.

Read on GitHub for this decision (brief #1116 answers 1 and 3): the cancelled merger runs 43143734569, 43141466373,
43140171516, 43145840780 and 43143279153 each end with the job `sweep` cancelled after waiting 1 to 18 minutes with no
runner and no step: it waits in its job group `agk-merger-sweep-job-2` until a newer sweep replaces it. The 2.7 minutes
are that wait, which `minutes.py` counts. The `governance edited` runs 43236702734 and 43234930310 install nothing; their
time is the step `Latest full run` (2 and 12 minutes waiting for the full run of the head) and `Record comments` (about
70 seconds: 27 reads one after another).

## Decision

1. The router starts the merger. When the event job of `route.py` labels a pull request `agk:merge-ready` and it had
   neither that label nor the old `agk:ready`, it starts `merger.yml` once with `workflow_dispatch` on the default branch
   and the input `pr` (the one event a job's own token may start; `actions: write` on the router's job). It does so only
   while `[flow] auto_merge = true` in GitHub mode, as `merge_cleared.py` reads it, and not for a `Verdict:` or
   `Approve:` comment or an edited `Final:`, on which the merger starts by itself. The router's own sweep of
   `agk:ci-running` starts it the same way. `--pr`, `--all` and `--dry-run` start nothing. A start that GitHub refuses
   prints one line and fails no routing.
2. The merger job runs on that dispatch for the pull request it names (`merge_cleared.py --event` reads `inputs.pr`, and
   the head from GitHub). Its `if:` no longer runs on a green `workflow_run` of a pull request, and its sweep's gate no
   longer runs on any `workflow_run`. The `Verdict:`, `Approve:` and edited `Final:` comments, the `agk/verdict` status,
   the 15-minute schedule, a dispatch without `pr`, and the failed `merge_group` run (ADR-0417) stay. This replaces
   ADR-0383's sweep after every finished run: the router reads every finished run and starts the merger exactly when a
   pull request can merge, and the schedule stays the fallback.
3. `minutes.py` reads the run list by time windows of the runs' creation, each halved while it answers more than 1,000
   runs, down to one hour, and adds them; only a one-hour window over the cap leaves the estimate `at least`. It also
   prints `minutes per merged pull request, last 7 days` beside the month's figure, by the same rule. The rule that counts
   a job is unchanged (see Residual).
4. The workflow files are the owner's (`.github/`): the exact new lines are posted as `Question: Q-1116-1 for the
   maintainers:` on the pull request, for the owner to commit on its branch. The protected path classes this decision
   changes are `scripts/agk/`, `tests/kit/`, `agk.toml` (two test map entries name the new test file) and, with the
   owner's commit, `.github/`.

## Consequences

A finished check of a pull request that is not cleared starts no merger job: on the measured day that removes about 648
merger jobs and the sweep jobs after them, so merger jobs fall to about one per merged pull request plus the schedule's
sweeps. The cost is one dispatch per pull request entering `agk:merge-ready`, made by a router run that already runs.
A merge waits for the router's run after the last check, as it waited for the merger's run before; a lost dispatch is
merged by the next scheduled sweep. Until the owner commits the workflow lines, the tests that read them fail on this
branch and the router's start is refused (it lacks `actions: write`) without harm. A busy repository's `minutes.py`
report reads every run of the month and the last 7 days, so the measurement of this brief can be repeated.

## Residual

- 2026-11-12: `minutes.py` counts a cancelled job's wait in a concurrency group (no runner, no step) as minutes, so its
  figure is above what GitHub bills; whether to count only jobs that had a runner is `Q-1116-2` (due 2026-11-30).
- 2026-11-12: a `governance edited` run waits up to 20 minutes for the head's full run; that wait guards the required
  check and is not changed here (due 2026-12-31).
- 2026-11-12: the `created=<from>..<to>` form with times and the cap of 1,000 runs are read from GitHub's behaviour,
  not its documentation (verify, due 2026-11-30).
- 2026-11-12: the conductor's `SWEEP late` line counts a dispatched merger run as a recent sweep (due 2026-12-31).
