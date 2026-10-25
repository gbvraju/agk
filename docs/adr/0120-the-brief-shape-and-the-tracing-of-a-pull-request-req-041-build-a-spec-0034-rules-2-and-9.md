# ADR-0120: the brief shape and the tracing of a pull request (REQ-041 build (a), SPEC-0034 rules 2 and 9)

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0114, ADR-0117
- Requirements: REQ-041

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0034 (Approved, #191) rule 13 splits its build in four; this is (a): the brief shape, `check_brief.py`, `check_pr_body.py` and the doctor finding (rules 2 and 9). It is built from the default branch in flow mode
(SPEC-0031). The number ADR-0120 was reserved for it by the conductor. The tests were written first (`tests/kit/test_check_brief.py`, `test_check_pr_body.py`, `test_doctor.py`, `test_session.py`, whose brief fixture gains the lines); on unchanged
`main` the new cases failed (16 in `test_check_brief.py`, 14 in the other two files) and pass after.

## Decision

1. **The shape (rule 2).** `brief_problems` in `scripts/agk/session.py` also requires exactly one `Advances:` line (`new`, or `REQ-nnn` ids separated by `, `), exactly one `Touches:` line (globs separated by commas, none
   empty) and at most one `Priority:` line (1, 2 or 3). `check_brief.py` and `session.py next` call that one function. Amendment 59 (`docs/runs/proposed-spec-amendments-59.md`) applies this to SPEC-0030 rule 4.
2. **`check_brief.py FILE --root DIR`** also fails a brief whose `Advances:` names an id that is not a `### REQ-nnn` header of `DIR/docs/requirements.md` (a file read; an unreadable file fails naming rule 2). Without
   `--root` it checks the shape alone. A message names the rule and the line, never the sentence or an id.
3. **The tracing (rule 9).** `check_pr_body.py` fails a body whose `Build-state row:` sets a requirement to `done` unless the body has a line `Closes #n`; with `--issues FILE` (a saved JSON list of the repository's
   issues) it also fails a body with no line `Brief: #n` when the list holds an issue labelled `agk-brief` (a pull request does not count). A message names rule 9, never a value. No `--issues`, an empty list or an
   unreadable one does not require `Brief:`.
4. **`doctor`** gains the check `brief-label` (`warn`): one more GET, `repos/OWNER/REPO/labels/agk-brief`; a 404 is a finding, any other failure is `cannot-check` as for the other reads; `--api-dir` reads
   `label-agk-brief.json`.
5. **Readings taken where the spec leaves a point open** (questions in the pull request, the most conservative reading each): "sets a requirement to `done`" is a `Build-state row:` line that holds a requirement id followed by `done` (`REQ-nnn done`, as `check_build_state.py` writes a row; the bare word does not count);
   "the saved copy it reads" is the file named by `--issues`.
6. **The workflow** `.github/workflows/governance.yml` gains the step `Open briefs` (one GET of the open `agk-brief` issues, saved to `$RUNNER_TEMP/briefs.json`) and passes `--issues` to the `PR body shape` step, so `Brief:` is enforced in CI (the class `.github/` is named above; `tests/kit/test_workflow.py` checks the step).
7. The example brief of `docs/guides/getting-started.md` gains the three lines (its test runs `check_brief.py` on it). Flow mode (SPEC-0028, SPEC-0031): `changelog.d/req-041-a-brief-shape.md`; no version bump; `CHANGELOG.md` and `kit/hashes.json` are as on `main`. The manifest is unchanged (the scripts are already installed).

## Consequences

- A brief written before this ADR lacks the three lines and fails `check_brief.py` and `session.py next` until its author adds them; an open brief is not rewritten here.

## Residual

- 2026-10-25: open briefs without `Advances:` and `Touches:` are skipped by `next` with a line naming rule 2 (due 2026-12-31).
