# ADR-0159: a description edit never cures a full run whose later steps never ran (REQ-039, brief 261)

- Status: Proposed
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0137, ADR-0144, ADR-0158
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #261 (priority 0). Build (b) of brief #216 (ADR-0144) lets an edited description cure a red full `governance` run whose
failed steps are all body steps. `full_run.py` counted a `skipped` step as acceptable (`OK_STEP`), and in the full run the steps
`Lint`, `Tests of the checks`, `Project tests` and `Secret scan` had the default condition, so GitHub skipped them after the first
failed step. A pull request whose description and code were both wrong turned green after the description alone was fixed, with
its lint, tests and secret scan never run (measured on a project's pull request #2 on 2026-10-26). The cause was reproduced first
with a fixture of that full run (`PR body shape` failed, those four steps skipped): `full_run.py --jobs` printed `ok full-run (the
failed steps read the body only)` and exited 0. The tests were written first and were red on the unchanged tree (9 of
`tests/kit/test_full_run.py`, 3 of `tests/kit/test_workflow.py`).

## Decision

1. **`full_run.py`** (answers 1 and 2). A red full run that failed only on body steps is cured only when every step it skipped is
   a body step (the partial run repeats it) or is skipped by its own condition. GitHub's jobs response shows both kinds of skip
   alike (`conclusion: skipped`), so the steps skipped by their own condition are named: `OWN_CONDITION` holds `Latest full run`
   (it runs on an edit only) and `Release check` (it carries `!cancelled()` and runs only where `kit/agk-kit.mk` is), and
   `Project tests` is accepted as skipped only when the run's `Release check` ran, which shows that the run is of the kit's own
   repository, where its condition skips it (`KIT_ONLY`). Any other skipped step makes the run not curable, and the edited run
   fails with one line, `rule 2: the last full run did not reach <steps>; push a commit or re-run it`, naming those steps of the
   workflow in the order of the run and never a value. A test pins both lists to the conditions in the workflow.
2. **The workflow** (answer 3): every step after `PR body file` carries `!cancelled()` in its `if:`: `PR comments`, `PR states and
   open pull requests`, `Open briefs`, `PR body shape`, `Lint`, `Tests of the checks`, `Project tests` and `Secret scan` gain it,
   each keeping its other conditions. A failed body step (or any failed check) therefore skips none of them, and a full run reports
   every check in one pass. The other option of answer 3, moving the body steps, was not taken: `!cancelled()` alone covers it,
   keeps the order of the steps that other tests pin, and keeps `Secret scan` last, as ADR-0158 decision 3 says. Both changes are
   made, so that `full_run.py` stays sound for a full run made under the earlier workflow (the measured case) as well.
3. **The tests** (answer 4): the measured run is not cured and gets the line of answer 2; a body failure with every other step run
   and passed is cured, in a project and in the kit's repository, as before; a skipped `Lint`, `Secret scan`, `Project tests` (in a
   project), `Open briefs`, `PR comments` or check, and the status-only skip, are not cured; the workflow is checked as text for
   `!cancelled()` on every step after `PR body file`, and `Secret scan` is still last.
4. Flow mode: fragment `changelog.d/full-run-not-reached.md`; no version bump.

## Consequences

- A pull request whose full run failed on its description and never reached its lint, tests or secret scan stays red after the
  description is fixed, until a full run executes them.
- From this change on, a failed description no longer hides those steps, so the full run shows every failure at once, and the edit
  cures a description-only failure as before.
- A full run of a status-only final commit skips the lint and the tests by its own condition, but the jobs response cannot show
  why; such a run with a description failure is not cured by an edit (the conservative reading, Q-261-1).

## Residual

- 2026-10-26: Q-261-1, the status-only skip read as "not reached", is for the maintainers (due 2026-12-15).
- 2026-10-26: Q-261-2 (verify): whether a re-run of a `pull_request` run reads the edited description or the event's original
  one; ADR-0144 records that "a re-run replays the old body", so "re-run it" in the line of answer 2 may need a push instead
  (due 2026-12-15).
- 2026-10-26: the after measurement of the brief (the same sequence on a project's pull request leaves governance red) is to be
  taken on a project repository; this session can reach none (due 2026-12-15).
