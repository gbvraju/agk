# ADR-0285: This repository runs a change's own and affected tests before a push, and the full suite on main (REQ-016, brief 578)

- Status: Accepted
- Date: 2026-11-05
- Deciders: maintainers
- Related: ADR-0185, ADR-0220, ADR-0227, ADR-0238, ADR-0242, SPEC-0044
- Requirements: REQ-016

Protected classes: `agk.toml`, `tests/kit/`, `tests/kit_dev/`

## Context

The owner decided on 2026-11-05 (chat, quoted as data from brief #578): "builders will test their changes and other change
impact tests, main will run full test. We have decided on this." The full kit suite takes 15 to 19 minutes on a builder's
machine. The machinery is Accepted: the `[testing]` table and its selection (ADR-0220), prepush running the selected regression
tests (brief #417, ADR-0227) and `pr_tests` (ADR-0242). This repository's `agk.toml` had no `[testing]` table, so everything ran
in full. Reading the code shows two facts the brief does not state: `prepush.regression_sets` runs the whole `project_tests`
command once when no `[proof]` table can take single files, so a `[testing]` table alone would not narrow a builder's run; and
this repository's `Project tests` step, the one `pr_tests` governs, is skipped (`kit/agk-kit.mk`), so its pull requests' CI runs
the full suite as "Tests of the checks" whatever `pr_tests` says.

## Decision

1. **`agk.toml` gains `[testing]`** with `profile = "balanced"` (a changed file no entry covers makes the selection full),
   `pr_tests = "selected"` (the owner's setting), and `always_full`: the files the brief names (`scripts/agk/common.py`,
   `kit/agk-kit.mk`, `Makefile`, `agk.mk`, `.github/workflows/**`, `tests/kit/conftest.py`, `tests/kit/pytest.ini`),
   `tests/kit_dev/conftest.py`, and the 18 scripts whose import closure reaches more than 100 of the kit's test files.
2. **The map is built from the code.** One entry per other script under `scripts/agk/` (50 entries): the test files under
   `tests/kit/` and `tests/kit_dev/` that import the script or name it as `<script>.py`, closed over the scripts' own imports.
3. **`agk.toml` gains one `[proof]` area, `kit`,** over `tests/kit` and `tests/kit_dev`, whose command is `project_tests`'s with
   `{files}`, so that prepush runs the selected files rather than the whole command. Proof then runs a pull request's own test
   files, red on the base and green on the head, rather than the whole suite (SPEC-0010 rules 11 and 12, unchanged);
   `proof_regression` stays off.
4. **Nothing else changes.** No code, workflow or template. A push to main and a release run the full suite (SPEC-0044 rule 1).
   ADR-0242 decision 5 ("its `agk.toml` does not set `pr_tests`") no longer holds for this repository; its pinning test now
   checks `selected`.
5. **Tests.** `tests/kit_dev/test_intelligent_testing.py` checks that the table is accepted, that every script is covered by an
   entry or by `always_full`, that every test name of the map exists, and that the real table gives a narrow selection for one
   script, the full suite for `common.py` or an unmapped file, nothing for documentation only, a single proof-area run in
   prepush, and the full suite on a push.

## Consequences

A builder's prepush on a change outside the shared core runs that change's tests and the tests that reach it, not the full
suite. A neighbour that the map misses can break unnoticed until main or a pull request's CI runs the full suite. Stepping back
is removing the tables, by an ADR in the same pull request.

## Residual

- 2026-11-05: a test that exercises a script without importing or naming it (through a make target, or an installer copying the
  whole folder) is not in that script's entry; the full suite on main and in this repository's pull-request CI is the backstop.
- 2026-11-05: the map does not follow new tests by itself; a stale test name fails `test_intelligent_testing.py`, a missing one
  does not (due 2026-12-31).
