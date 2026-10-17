# ADR-0028: this repository's project tests install ruff as well as pytest

- Status: Accepted
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
2. **A rule for every future change to `project_tests` or to the `proof` job**: besides the usual commands, the change is verified by
   running the exact `project_tests` command from the repository root in a fresh `python3 -m venv` with nothing installed and a `PATH`
   with neither `pytest` nor `ruff` on it, and the command, the versions it installed and the pass and fail counts, verbatim, are part of
   the pull request's "Verified" and of the ADR that makes the change. This ADR carries the run for this change (below).
3. **The seeded pull request is run again** after this merges, on a new pull request (the seeded #62 is closed unmerged with its real
   reading recorded), and the outcome is recorded in `docs/runs/proof-checks-live-2.md`.

## The clean-environment run (2026-10-17, the commit that changes `agk.toml`)

Environment: `python3 -m venv /tmp/claude-0/cleanvenv` (Python 3.13.16, pip 26.2.1, no system site packages), `PATH` =
`<venv>/bin:/usr/local/bin:/usr/bin:/bin`. Before the run: `python3 -m pytest --version` printed `No module named pytest` and `ruff` was
not on `PATH`.

The command, from the repository root, run with `sh -c`, exactly as in `agk.toml`:

```
(python3 -m pytest --version && ruff --version) >/dev/null 2>&1 || python3 -m pip install -q pytest ruff; AGK_KIT_TESTS=1 python3 -m pytest -c tests/kit/pytest.ini tests/kit tests/kit_dev -q
```

Installed by it: `pytest 9.1.1` and `ruff 0.17.1` (with `iniconfig 2.3.1`, `packaging 26.3`, `pluggy 1.7.0`, `Pygments 2.21.0`).

Result, verbatim: `861 passed, 4 skipped in 617.87s (0:10:17)`, exit 0, no `FAILED`.

Nothing else was missing. The four skips are by design and are the same kind the CI jobs show: `bandit is not installed` and `mypy is not
installed` (the scanner tests run only where those are installed), `the claude CLI is not installed`, and `kit 0.3.0 has no adopt`.
On a developer machine that has bandit or mypy the count is 862 passed and 3 skipped.

## Consequences

- The `proof` job here runs the kit tests in the environment that `governance` has, so `red-on-head` is no longer caused by the
  runner. A real `red-on-head` or `green-on-base` is then about the pull request.

## Residual

- 2026-10-17: the list of tools the kit tests need is found by running them in the `proof` job, not declared; a test that needs another
  tool will read `red-on-head` there until `project_tests` installs it (due 2026-11-07, with the playbook residual of ADR-0027).
