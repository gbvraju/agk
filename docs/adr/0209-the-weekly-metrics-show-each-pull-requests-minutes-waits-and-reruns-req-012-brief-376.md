# ADR-0209: the weekly metrics show each pull request's minutes, waits and re-runs (REQ-012, brief 376)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0184, ADR-0016
- Requirements: REQ-012

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #376 (priority 2, split from #288 part 7): the targets of #288 (at most 10 hosted minutes per pull request with a
pool; no builder waiting on another's heavy job) cannot be checked, because nothing reports minutes, waits or re-runs per
pull request. `minutes.py` (ADR-0184) estimates a month's minutes per workflow; `metrics.py` (SPEC-0007) already reads the
head commits and governance jobs of each closed pull request. The script and its tests are protected path classes, so this
ADR names them. The tests were written first (`tests/kit/test_metrics_minutes.py`: 15 failed at the first checkpoint of the
pull request).

## Decision

1. **Four fields per record (answer 1).** Each record of `metrics.py` gains four columns after the existing ones:
   - `minutes`: the sum of `minutes.job_minutes` over the jobs of the pull request's runs on GitHub-hosted runners, as the
     total followed by the minutes per workflow name, for example `5 (governance 2, proof 3)`;
   - `pool_minutes`: the same sum over the jobs on self-hosted runners (label `self-hosted`, as `minutes.py` reads it),
     which are not billed and are not in `minutes`;
   - `wait_minutes`: per run, the earliest job start minus the run's creation (never below 0), summed, in minutes with
     one decimal, round half up;
   - `reruns`: the number of runs whose `run_attempt` is above 1.
2. **Which runs.** The runs of a pull request are the workflow runs whose head commit is one of its commits
   (`actions/runs?head_sha=<sha>`, saved as `runs-<sha>.json`), each run counted once; a run's jobs are read with
   `filter=all` (`actions/runs/<id>/jobs?filter=all`, saved as `run-jobs-<id>.json`), so every attempt of a re-run is
   billed, as `minutes.py` reads them. A run with no job asked for no runner and adds no wait.
3. **Unknown stays unknown (answer 2, SPEC-0007 rule 10).** An unreadable commit list or run list makes all four fields
   `unknown`; a run whose jobs cannot be read makes `minutes`, `pool_minutes` and `wait_minutes` `unknown` (`reruns` is read
   from the run list); a job without both times (`job_minutes` gives None) makes its field `unknown`; a run with jobs and
   no job start makes `wait_minutes` `unknown`. A pull request whose commits started no run has `0`, measured.
4. **The weekly totals (answer 2).** One line `ci totals: <field> median=<m> largest=<l> unknown=<n>; ...` follows the
   `totals:` line for the four fields, over the records whose field is known; a median of an even count is the mean of
   the middle two, one decimal, round half up, and a whole number prints without a decimal. A field known for no record is
   `unknown`; a week with no record prints `-`.
5. **One billing rule (answer 3).** `metrics.py` imports `job_minutes` and `SELF_HOSTED` from `minutes.py` at the time of
   use, because `minutes.py` imports `origin_repo` from `metrics.py`; `minutes.py` is not changed. Runner rates
   (`minutes.multiplier`) are not applied: answer 1 names `job_minutes` alone (Q-376-2).

## Consequences

- The cost of each pull request, and so of each tier, is measured each week: hosted minutes, pool minutes, waits for a
  runner and re-runs.
- Each closed pull request costs one more read per head commit and one per run; a live run of the weekly workflow reads
  more, with the `actions: read` permission it already has.
- The body of the weekly issue gains four columns and one line, beyond the shape of SPEC-0007 rule 14 (Q-376-1).

## Residual

- Q-376-1 (2026-10-30): SPEC-0007 rules 14 and 20 do not name the four columns, the `ci totals` line or the two saved
  response names; the spec text is not changed here (the brief touches only the script, its test and the changelog).
- Q-376-2 (2026-10-30): whether `minutes` should apply the runner rates of a private repository, as `minutes.py`'s
  monthly estimate does.
