# ADR-0232: the weekly metrics show test time per pull request, backstop escapes and suites over budget (REQ-012, brief 427)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0209, ADR-0220
- Requirements: REQ-012

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #427 (priority 3, from #289 part 6): the targets of #289 (a small change proven within 10 minutes, the full suite in
5 minutes or less, a falling escape rate) cannot be checked, because no report counts test time, misses after a merge or
suites over budget. The jobs API gives each step's start and end (`metrics.py` already reads each run's jobs, ADR-0209),
and brief #373 (ADR-0220) added `[testing] budget_seconds`. The script and its tests are protected path classes, so this
ADR names them. The tests were written first (`tests/kit/test_metrics_testing.py`: 16 failed at the first checkpoint of
the pull request).

## Decision

1. **Two fields per merged pull request (answer 1).** Each record gains two columns, after `tests_after` and before the
   four CI fields of ADR-0209:
   - `project_test_seconds`: the whole seconds (round half up) from the start to the end of the `Project tests` step in
     the last governance run of the pull request's head that ran it;
   - `proof_seconds`: the whole seconds from the start to the end of the last `proof` job of the head that ran.

   A step or job "ran" when its conclusion is `success` or `failure`; a skipped or cancelled one is passed over, so a run
   for an edited description (which skips `Project tests`) and a draft's skipped proof job do not hide the run before
   them (Q-427-1). A governance run is one named `governance`, or `governance <run name>` (Q-427-2). Each field is
   `unknown` when the run list or a run's jobs cannot be read, when the newest candidate has not ended, when nothing ran
   the step, or when a time is missing (SPEC-0007 rule 10); a closed pull request that did not merge shows `-`.
2. **Backstop escapes (answer 2).** For each merged pull request of the window, the governance runs on the push of its
   merge commit (`runs-<merge sha>`, event `push`, branch the pull request's base) are read. A push whose run failed
   (`failure` or `timed_out`) is an escape when the head's last proof job ended `outcome: proven` (read as `facts.py`
   reads it) and the head's latest governance run concluded `success`; otherwise it is a red push that is not an escape.
   One line follows the `closed in window` line:
   `backstop escapes: <n> (#<pr> <merge sha>, ...); red pushes not escapes: <n> (#<pr> <merge sha>, ...); unknown: <n> (#<pr>, ...)`,
   with the list left out when its count is 0. A merge whose push run cannot be read or has not ended, or whose red push
   has a proof or governance that cannot be read, is `unknown`, never counted as no escape.
3. **Suites over budget (answer 3).** The budget is `[testing] budget_seconds` of `agk.toml` as `impact.py` reads it (300
   when the table or the key is unset). Each governance run of the window's pull requests (on their commits and, when
   merged, on the push of the merge commit), each counted once, whose `Project tests` step took longer than the budget is
   listed: `over budget (budget_seconds <b>): <n> (#<pr> run <id> <s>s, ...); unknown: <k>`, where `<k>` counts the commit
   lists, run lists and runs that cannot be read or whose step has no time. A setting that `impact.py` refuses prints
   `over budget: unknown (<its refusal, naming the setting>)`.
4. **Nothing blocks (answer 4).** The lines are information in the weekly metrics issue; they never change the exit
   status of `metrics.py`.
5. **One read per request.** A live run reads each endpoint once (`Gh.get` keeps what it read for the run), since the
   record, the escapes and the budget read the same run and job lists.

## Consequences

- Testing cost and misses are measured each week: the seconds of each merged pull request's tests and proof, the escapes
  after a proven merge, and the runs over budget, which the steward (#286) can read to flag a breach.
- Each merged pull request costs one more run-list read (its merge commit) and one job-list read per push run.
- The body of the weekly issue gains two columns and two lines, beyond the shape of SPEC-0007 rule 14 (Q-427-5).

## Residual

- Q-427-1 (2026-10-31): "its last governance run" and "its last proof job" are read as the last that ran the step or
  job, since a run for an edited description never runs `Project tests` and a draft's job is skipped.
- Q-427-2 (2026-10-31): whether the REST API's run `name` is the workflow name (`governance`) or the run name
  (`governance full`) (verify); both are accepted.
- Q-427-3 (2026-10-31): escapes and runs over budget are taken over the pull requests closed in the window, as the rest
  of the report is, not over runs created in the window.
- Q-427-4 (2026-10-31): in the kit's own repository the `Project tests` step is skipped (the kit runs its suite in other
  steps), so `project_test_seconds` is `unknown` there and nothing is over budget; a project shows real figures.
- Q-427-5 (2026-10-31): SPEC-0007 rules 14 and 20 do not name the two columns or the two lines; the spec text, the
  metrics guide and the steward are not changed here (the brief touches only the script, its test and the changelog).
