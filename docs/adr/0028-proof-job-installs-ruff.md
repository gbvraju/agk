# ADR-0028: this repository's project tests install ruff as well as pytest

- Status: Proposed
- Date: 2026-10-17
- Deciders: maintainers
- Amends: ADR-0027
- Related: ADR-0026
- Requirements: REQ-016

Protected classes: `agk.toml`

## Context

ADR-0027 made this repository's `project_tests` install pytest when it is missing, so that the `proof` job can run the kit tests. It
said "no kit test uses `ruff`". That was wrong: it was checked by searching the test files for the word, and two kit tests,
`tests/kit/test_init.py::test_ac1_ci_steps_include_the_project_tests_and_pass_when_they_pass` and
`::test_ac1_failing_project_test_makes_the_ci_steps_fail`, run the steps of the installed `governance.yml` in a freshly installed target,
and one of those steps is `Lint`, which calls `ruff`.

The seeded pull request #62 (a new test that passes on `main`) showed it. Its `proof` job read `not-proven (red-on-head)`, not the
expected `green-on-base`: in both runs, the base with the new test and the head, the same two tests failed (`2 failed, 860 passed,
4 skipped`), with the lint step exiting 2 at index 9 of the step results. The `governance` job installs `pytest` and `ruff`, so it
passes the same tests. Reproduced locally with `ruff` removed from `PATH`: the same two tests fail (`2 failed, 37 deselected`).

## Decision

1. **`project_tests` installs pytest and ruff when either is missing**: `(python3 -m pytest --version && ruff --version) >/dev/null
   2>&1 || python3 -m pip install -q pytest ruff; AGK_KIT_TESTS=1 python3 -m pytest -c tests/kit/pytest.ini tests/kit tests/kit_dev -q`.
   Where both exist (`governance`, a developer machine) nothing is installed. ADR-0027 is not edited (it is Accepted); this ADR amends
   its statement about `ruff`.
2. **The seeded pull request is run again** after this merges, on a new pull request (the seeded #62 is closed unmerged with its real
   reading recorded), and the outcome is recorded in `docs/runs/proof-checks-live-2.md`.

## Consequences

- The `proof` job here runs the kit tests in the environment that `governance` has, so `red-on-head` is no longer caused by the
  runner. A real `red-on-head` or `green-on-base` is then about the pull request.

## Residual

- 2026-10-17: the list of tools the kit tests need is found by running them in the `proof` job, not declared; a test that needs another
  tool will read `red-on-head` there until `project_tests` installs it (due 2026-11-07, with the playbook residual of ADR-0027).
