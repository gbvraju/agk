# ADR-0197: an edited description cures a full governance run that failed only on the description (REQ-039, brief 349)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0159, ADR-0171, ADR-0192
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #349 (priority 1), from #339: the full governance run of head a5439ff failed only in `PR body shape`, and the description
was then fixed. The `governance edited` run still failed in `Latest full run`, with "the last full run did not reach Post Restore
the secret scanner, Post Run actions/setup-python@…". GitHub skips those `Post` steps in any failed job (the cache action saves
only after a job that succeeded, ADR-0171), and `scripts/agk/full_run.py` counted every skipped step that is not a body step as a
step the run never reached (ADR-0159). So an edit could never cure a body-only failure, and a re-run of the full run reuses the
old description. Second, the step `PR body file` had no condition, so after a failed `Latest full run` it did not run and the
body steps after it failed with "the body file cannot be read", against the workflow's own header. The builder reproduced the
measurement on job 123926216899 (two `Post …` steps `completed skipped`) before changing anything.

## Decision

1. **Skipped post steps (answer 1).** `full_run.py` does not count a step whose name starts with `Post ` and whose conclusion is
   `skipped` as not reached. Every other step is judged as before: a skipped real step still blocks and is named, and a `Post`
   step that failed is a failed step that is not a body step.
2. **The body file (answer 2).** The step `PR body file` of `.github/workflows/governance.yml` carries `if: ${{ !cancelled() }}`.
3. **Tests first (answer 3).** `tests/kit/test_full_run_post_steps.py`: the measured run (a body failure with two skipped `Post`
   steps) is cured; a run that stopped before a real step is still not cured and the message names only real steps; a failed
   `Post` step and a step named `Postscript` are judged as before; the workflow step carries the condition.

## Consequences

A pull request whose full run failed only on its description turns green when the description is fixed, with no extra commit.
A skipped `Post` step hides no check, since it runs after every check of the job; a check that never ran is still caught.

## Residual

None.
