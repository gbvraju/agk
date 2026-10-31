# ADR-0226: a project's heavy check runs only when its inputs change, and says why it skipped (REQ-039, brief 416)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0217
- Requirements: REQ-039

Protected classes: `tests/kit_dev/`

## Context

Section 4 of the project CI guide (brief #283) shows how a heavy check skips a documentation-only change and still reports
success. In a pilot (#287 answer 5) the project's tests and its local profile also ran in full for changes to briefs, the kit's
own files and workflows they never read. A `paths` filter cannot be used on a required check: a workflow that does not start
never reports. Brief #416 gives the answers: the guide's section 4 and its tests.

## Decision

1. **Section 4 (answer 1).** It becomes "A heavy check runs only when its inputs change". One copyable job sets the job's own
   input globs once (`INPUTS`: application code, tests, the `Makefile`, container build files, compose files, the workflow
   itself, written `.github/workflows/<this workflow>.yml` as the guide writes `<pinned sha>`); one step lists the files the
   pull request changed against its base and compares them with the globs; the following step writes `skipped: none of <globs>
   changed` to the step summary and the log when none matched, and the heavy steps run unless that step said `false`. The job
   ends green either way.
2. **The must-nots (answer 2).** The guide states them: a required check is never removed or weakened; a push to the default
   branch and `ready_for_review` always run in full (the step decides `true` for every event but an ordinary pull request
   update, and for any error, an unknown base or a failed diff); the skip reason is always visible.
3. **The doctor (answer 3).** `ci-drafts` and `ci-concurrency` are unchanged; no script changes.
4. **Tests first (answer 4).** `tests/kit_dev/test_project_ci_guide.py` (a protected path class, hence this ADR) reads the
   snippet as a workflow with a small reader of the block style it uses, and with PyYAML as well where it is installed (the
   proof job installs only pytest and ruff); runs the shell step under `bash` in throwaway git repositories for each case of
   decisions 1 and 2; and checks the must-nots and that the section names no vendor beyond GitHub.
5. **No vendor in a file name either (Q-416-1).** Answer 1 names container build files, whose most common name carries a
   container vendor's name; answer 4 and the guide's own test of brief #283 (Q-283-3) keep every vendor name out of the guide.
   Read conservatively, the glob is the vendor-neutral `*Containerfile*` and the job's comment tells the project to write its
   container build file by its own name; the vendor check matches anywhere in the section, file names included.
6. **The older snippet (Q-416-2).** `tests/kit/test_doctor_ci.py` (outside `Touches:`) still reads section 4 by its number and
   looks for `outputs.docs_only`; the section keeps one sentence naming the older step's output, so a project that copied it
   knows what the new step replaces, and that test is left unchanged.

## Consequences

A change to briefs, documentation or the kit's own files costs one short job of a project's heavy check, which still reports
success and says why it skipped. A project whose check reads files outside its globs must add them, or the check skips a change
it should have tested: the globs are the project's own, written once on the job.

## Residual

- 2026-10-31: Q-416-1 and Q-416-2 (decisions 5 and 6) are read conservatively; whether the vendor lists of the guide tests
  should be one shared list, and whether `tests/kit/test_doctor_ci.py` should drop its `docs_only` needle, is a later brief.
