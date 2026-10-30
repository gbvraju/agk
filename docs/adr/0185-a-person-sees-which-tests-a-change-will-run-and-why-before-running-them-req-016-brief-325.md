# ADR-0185: a person sees which tests a change will run, and why, before running them (REQ-016, brief 325)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0167, ADR-0172
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

Brief #325 (priority 1), part of #289 (answer 4 of its parts, "`agk test --plan`"). Since brief #305 (ADR-0172) proof runs per
test area with only the pull request's own test files, but nobody can see that selection before CI runs it; in a pilot, builders
waited 13 to 25 minutes to learn which tests ran. The brief names no `Measured:` line. The tests were written first
(`tests/kit/test_test_plan.py`: 15 of 15 failed at the first checkpoint of the pull request).

## Decision

1. **One function builds the plan (answer 2).** `proof.plan(root, base, head)` returns the plan of proof for the change: the
   test files proof places on the base (deletions included), the runs (each a name, its added or changed test files, its command
   line and its working folder), the areas with nothing to run, and the added or changed test files in no area. It reads git and
   files only. With a `[proof]` table each run is an area, its command line built by `area_command` (`{files}` relative to the
   area's `cwd`, `shlex.quote`d), and a `cwd` that is not a folder of the head is refused there, naming `proof.<area>.cwd`. Without
   the table there is at most one run, `project_tests`, given the files `test_dirs` and `test_patterns` select. `prove` and
   `prove_areas` now take their runs from `plan` alone, so the plan shown is the plan run; outcomes, lines, `--json` keys, the
   order of refusals and exit codes of `proof.py` are unchanged (`tests/kit/test_proof.py`, `test_proof_areas.py` and
   `test_proof_timeout.py` pass unchanged). A test records the commands and folders proof runs on the base and on the head, with
   and without a table, and compares them with the plan's.
2. **`scripts/agk/test_plan.py [--base REF] [--head REF] [--json] [ROOT]` (answer 1).** Read-only: no worktree, no test run. The
   base defaults to the merge base with the default branch, as in proof (`resolve_range`). The text names, for each run, its
   name, the number of files and why they were chosen (the area's `dirs` and `patterns`, or `test_dirs` and `test_patterns`),
   its folder, its command line and its files; then `<area>: nothing to run`; then `not run by proof (in no [proof] area):
   <file>`; then `deleted (removed on the base, not run): <file>`. Without a table the `project_tests` command (or `not set
   (setting: project_tests)`) and the selected test files that are not deleted are always printed, also when nothing runs
   (finding 1 of the verdict on fc54475). `--json` holds `base`, `head`, `proof_table`, `runs` (`name`, `files`, `command`,
   `cwd`), `nothing_to_run`, `not_run_by_proof`, `deleted` and `project_tests` (without a table `command`, null when not set,
   and `files`; with a table null). Exit 0 printed, 2 usage or a refused setting (the same message as proof's,
   named `test-plan`), 3 I/O or a ref that does not resolve (path class `git ref`).
3. **Installed (Q-325-1).** `kit/manifest.json` lists `scripts/agk/test_plan.py` with the verbatim scripts, so a project has it
   and the guide's command works there; `tests/kit_dev/test_kit_manifest.py` requires every script to be listed or kit-only. The
   brief's `Touches:` does not name `kit/manifest.json`; it is the one file outside it.
4. **The guide (answer 3).** `docs/guides/existing-codebase.md` step 4, after the `[proof]` table, shows the command and what it
   prints. `docs/guides/reference.md` is not changed here, since open pull request #323 changes it (Q-325-2).
5. **Readings taken (the conservative ones).** Q-325-3: a test file "in no area" is an added or changed file that `test_dirs` and
   `test_patterns` select and no area's `dirs` and `patterns` match: that is the kit's only definition of a test file outside the
   table. A deleted file is listed apart, not as "not run". The plan does not read a pull request body, so `Behaviour: unchanged`
   (which makes proof `skipped`) is not shown; the brief gives the command no body option.
6. **Tests (answer 4).** `tests/kit/test_test_plan.py`: two areas; an area with nothing to run; a file in no area; a deletion
   only; no table; no table and no `project_tests`; no table and a deletion only; `{files}` quoting of a path with a space; no `cwd`; the plan equal to proof's
   runs with and without a table; one function; read-only; the same `cwd` refusal; `--base` and `--head`; usage and a bad ref.
7. **Flow mode.** Fragment `changelog.d/test-plan.md`; no version bump; `kit/hashes.json` not edited (session rule 14).

## Consequences

- A person or a session sees in a second, before pushing, which test files proof will run, with which command and where, and
  which test files no area covers.
- A change to how proof chooses its runs changes the plan with it; the two cannot drift apart without the equality test failing.

## Residual

- 2026-10-30: Q-325-1 answered in the verdict on fc54475: `kit/manifest.json` is accepted, listed in the body as a change
  outside `Touches:` (decision 3).
- 2026-10-30: Q-325-2 answered in the verdict on fc54475: a `docs/guides/reference.md` line can follow after #323 merges; it is
  not in this pull request (decision 4).
- 2026-10-30: Q-325-3 answered in the verdict on fc54475: the reading is sound; it matches proof's own definition of a test file
  (decision 5).
