# ADR-0419: Selected pull request tests run in the full suite's workers

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: brief #980, plan #661, SPEC-0044 rules 4 and 5, ADR-0305 (brief #631), ADR-0348 (brief #749), ADR-0242
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `kit/`, `tests/kit/`, `agk.toml`

## Context

With `[testing] pr_tests = "selected"` a pull request runs the test files that `impact.py` selects, each through the
command of its `[proof]` area (`prepush.regression_sets`, `project_tests.plan`, the `agk-test` chooser of
`kit/agk-kit.mk`). The full suite gains `-n <workers>` from `prepush.full_command` (SPEC-0044 rule 4, ADR-0305); a
selected run never did, because the rule left every `[proof]` area command single. So a selection of 163 to 255 files
took 14.7 to 17.5 minutes in one process, against 6.4 minutes for the whole suite in workers (brief #980).

## Decision

1. A selected run gains the workers by the full suite's rule, through one helper of `prepush.py` that `full_command`
   shares: with `[testing] workers` above 1, a pytest command whose interpreter imports xdist in the run's folder
   gets `-n <workers>` at its end. The pytest command is the whole command or, when the command is a shell step
   followed by `;` and one simple command, that last command (the kit's own `[proof.kit]` command has that form);
   any other shell syntax leaves the command single. Without xdist, or for another runner, the run is the command of
   today after one line naming `testing.workers`; `parallel_command` stays the full suite's alone, since it carries
   no file list.
2. It is applied where the selected runs are assembled: `project_tests.plan` (the CI step, and through it the
   `agk-test` chooser) and the regression runs of `prepush.gate`. `regression_sets`, the `[proof]` table in
   `agk.toml` and proof's own base and head runs do not change, nor does the record of `evidence.py`.
3. A new `[testing] full_when_share` (a number above 0 and at most 1; default 0.5): when the selected test files are
   at least that share of the test files the `[proof]` areas hold at the head, the pull request runs the full
   suite in workers instead, saying `selection <n> of <m> files` as the reason (`tests: mode full (selection 255 of
   396 files)` in the chooser). A bad value is refused naming `testing.full_when_share`.
4. Nothing is selected out: the selected file list is the same before and after; only how it runs changes.

## Consequences

A wide pull request takes about the full suite's minutes, not up to 23 minutes in one process. Every installed
project with pytest-xdist importable gains the workers in its pull request step and in prepush. A test that is not
safe in parallel, already a failure of the full suite, can now also fail a selected run.

## Residual

- 2026-11-10: the measured gain is answer 1's timed pair on #917's head in the pull request; the PR step minutes of the
  next 20 merged pull requests are the brief's after-measure.
