# ADR-0033: one shared installed target for the nested init tests (Q-K4-158)

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0028, ADR-0032
- Requirements: REQ-009, REQ-010

Protected classes: `tests/kit_dev/`

## Context

`make test` took 1343 s on the head of #71 (two runs of the kit and kit-dev suites, because the repository's `project_tests` is the
kit-test command; Q-K4-135 keeps that). Almost all of each run was seven tests that install the kit into a fresh repository and run
the *installed* kit suite inside it (about a minute each): six in `tests/kit_dev/test_init.py` and one in `test_adopt.py`. Measured
alone, `tests/kit_dev` took 612.63 s, of which those seven tests took 540 s (111.06, 79.47, 74.59, 71.33, 70.70, 69.98 and 62.96 s).
The maintainers ruled option 1 of Q-K4-158: one shared installed target for the nested tests, with no reduction of what any test asserts.

## Decision

1. **`tests/kit_dev/conftest.py`** gains `shared_install` (the kit installed once per session, into one repository, never run in),
   `shared_copy` (a copy of it for one test, git history included), `kit_suite` (the two commands whose own result is asserted, each
   run once in a copy of the shared install: `make test`, the alias, and `make -f agk.mk agk-test`, the direct form) and the small
   `Run` and `KitSuite` records.
2. **A test about the project's tests runs `make -o agk-test test`**: the same `test` target with the phony prerequisite `agk-test`
   treated as up to date by GNU make, so the kit suite is not run again; the kit suite itself is covered by `kit_suite`. A new test
   pins that this is the only difference: `make -n test` lists the kit-suite recipe before the project-tests recipe, and
   `make -n -o agk-test test` lists only the second.
3. **`test_adopt.py` is not changed**: it has one nested run, in an adopt-mode target whose files differ from an init target's.
4. No test file other than `tests/kit_dev/test_init.py` and `conftest.py` changes; no installed file, kit version or hash changes.

## What each changed test asserts, before and after

| Test | Before | After |
| --- | --- | --- |
| `test_ac2_governance_and_tests_green_in_target` | in a fresh install: `make governance` exits 0; `make test` exits 0 | `make governance` exits 0 in a copy of the shared install; `make test` exits 0 (`kit_suite.alias`: the same command, run once in another copy of the same install, no project tests of its own) |
| `test_ac2_project_tests_are_collected_and_run_by_make_test` | a passing project test is added; `make test` with `-rA` exits 0 and prints `PASSED tests/test_sample.py::test_sample_runs` | the same test is added to a copy; `make -o agk-test test` with `-rA` exits 0 and prints that line; and (new) prints nothing from `tests/kit`, so the kit suite did not run again |
| `test_ac2_failing_project_test_makes_make_test_fail` | a failing project test is added; `make test` with `-rA` exits non-zero and prints `FAILED tests/test_sample.py::test_sample_fails` | the same, with `make -o agk-test test` |
| `test_ac1_both_forms_are_green_in_the_target` | `make governance` exits 0; `make -f agk.mk agk-governance` exits 0; `make -f agk.mk agk-test` exits 0 | `make governance` and `make -f agk.mk agk-governance` exit 0 in a copy; `make -f agk.mk agk-test` exits 0 (`kit_suite.direct`: the same command, run once in a copy of the same install) |
| `test_ac1_ci_steps_include_the_project_tests_and_pass_when_they_pass` | the workflow has 12 `run:` steps (nine checks, then `agk-lint`, `agk-test`, `agk-project-test`); with a passing project test, every step exits 0 | the same twelve steps and the same exit codes; the step `make -f agk.mk agk-test` takes its exit code from `kit_suite.direct`, and the test asserts the step exists |
| `test_ac1_failing_project_test_makes_the_ci_steps_fail` | with a failing project test, the last step exits non-zero and the other eleven exit 0 | the same; the kit-suite step's code is `kit_suite.direct`'s |
| `test_ac2_make_test_is_the_kit_suite_then_the_project_tests` (new) | not asserted | `make -n test` shows the kit-suite recipe, then the project-tests recipe; `make -n -o agk-test test` shows only the second |

The assumption behind sharing a result is that a copy of one fresh install gives the same kit-suite result as another fresh install;
the copies are made before any command runs in them, and `kit_suite` runs each command in a copy of its own.

## Timing (this machine; `make test` runs `tests/kit` and `tests/kit_dev` twice)

| | Before (head of #71) | After |
| --- | --- | --- |
| `tests/kit_dev` alone | 612.63 s (and 614 s wall) | 303.52 s |
| `make test`, first run | 666.68 s | 372.67 s |
| `make test`, second run | about 650 s | 399.02 s |
| `make test`, wall | 1343 s | 773 s |
| passed, skipped | 1028, 3 | 1029, 3 (one new test) |

What is left in each run: the shared install's two kit-suite runs (about 133 to 136 s of setup, charged to the first test that uses
them) and the adopt test (90 to 108 s).

## Consequences

- `make test`, and the `governance` and `proof` jobs that run it, are about 570 s shorter (42%).
- A kit-suite failure inside a target now fails the tests that read `kit_suite`, not six separate ones; each says which command failed.
- The first test that asks for `kit_suite` pays its ~135 s; running a single such test alone costs the same as before.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-159 | `make -o agk-test test` runs the real `test` target without its kit-suite prerequisite; is that the same `make test`? | yes for what those tests assert (the project tests are collected, run, and fail the target); the kit-suite half is asserted by `kit_suite.alias`, and the new structural test pins the composition |
| Q-K4-160 | Should the adopt test share a target too? | no: its target is an adopt-mode install of a synthetic project, different from an init install; one run stays |
| Q-K4-161 | The suite results are shared within one pytest session. | one process only; a re-run of a single test (`-k`) pays its own `kit_suite` cost |

## Residual

- 2026-10-18: the adopt test still runs the installed kit suite once (90 to 108 s); sharing it would need an adopt-mode shared install
  and its own proof that nothing asserted is lost (due 2026-12-31).
