# ADR-0480: An edited run waits for the full governance run without a runner

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: ADR-0302, ADR-0277, brief #1122, brief #1116 items 3 and 3b, brief #216, brief #621, brief #557, plan #661
- Requirements: REQ-039

## Context

On the default branch at a5318c5, `.github/workflows/governance.yml` gives a run for an edited description a
concurrency group of its own (`governance-<n>-edited`, brief #216), so that it cannot cancel the full run of the same
head. Its step `Latest full run` then holds a runner while it polls for that full run every 30 seconds, for up to 20
minutes: about 368 seconds in an average edited run (the step timings of 31 full, 15 edited and 8 push runs, comment
6827171618 on #1116). The step `Record comments` reads about 114 record comments one by one, about 67 seconds in every
run. `route.latest_runs` takes the highest check run id as the latest, so an edited run must never end green while
the full run is queued or in progress (the guard of brief #216).

## Decision

1. A pull request's full and edited runs share one concurrency group, `governance-<n>-code`, as a push to the default
   branch keeps `governance-<branch>-code` (ADR-0302). `cancel-in-progress` is true for every pull request run but an
   edited one: an edit that arrives during the full run waits as a pending run, which holds no runner, and never
   cancels the full run; a new push still cancels the full run and any waiting edited run of the old head.
2. The step `Latest full run` stays as the fallback and fails closed as before: a full run that was cancelled, failed in
   a step that does not read the body, or did not finish in 20 minutes fails it. When an edited run replaces a full
   run that GitHub was still starting, the edited run finds that full run cancelled and fails; it never ends green
   while the full run is queued or in progress.
3. The step `Record comments` reads the ids of `check_adrs.py --record-ids` in parallel, at most 8 at a time
   (`xargs -P 8`), each into a file of its own, and joins them in the order the ids are printed (id order) into the same
   `record-comments.json`. A comment that cannot be read is left out, with the same message, so its record counts for
   nothing (fail closed); a failed read leaves no partial answer in the file. The step is never skipped.
4. Workflow files are the owner's: the builder writes the tests and gives the exact new lines in a `Question:` for the
   maintainers, and the owner commits them on the pull request's branch.

Protected path classes changed: `.github/` (`.github/workflows/governance.yml`, committed by the owner), `tests/kit/`
(`test_workflow.py`, `test_ci_saving.py`, `test_main_batching.py`) and `kit/` (`kit/hashes.json` only as
`kit_hashes.py` prints it).

## Consequences

A description edit no longer holds a runner for minutes while the full run goes on, and every governance run reads
its record comments in about an eighth of the time, so a project spends fewer Actions minutes. A partial run still
cannot turn a failed or unfinished full run green.

## Residual

- 2026-11-12: the minutes saved are to be confirmed by the step timings of a comparable day after the merge (the
  brief's `Measured:` after) (due 2026-12-31).
