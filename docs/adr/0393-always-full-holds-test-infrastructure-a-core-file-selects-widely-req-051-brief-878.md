# ADR-0393: `always_full` holds test infrastructure; a core file selects its mapped tests and importers

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0285, ADR-0359, ADR-0360, brief #878, amendment 153
- Requirements: REQ-051

Protected classes: `agk.toml`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`

## Context

`[testing] always_full` in this repository's `agk.toml` named the core scripts beside the test system's own files, so a
pull request that touched one of them ran the full suite: of the 60 pull request runs measured since 2026-11-08 13:03Z,
33 were full, every sampled one by that list, at a median of 529 s against 4 s for a selected run. The key had no rule on
what belongs in it, in the kit or in a project, and the full suite's time was bounded by nothing. A pull request that
changes a core script needs that script's own tests and the tests of what uses it, not all of them: the default branch
still runs everything after each merge.

## Decision

1. `always_full` names the files that change how tests are found or run: test configuration, shared fixtures, the build and
   CI files and the test runner's own code. This repository keeps nine: `tests/kit/conftest.py`, `tests/kit/pytest.ini`,
   `tests/kit_dev/conftest.py`, `Makefile`, `agk.mk`, `kit/agk-kit.mk`, `.github/workflows/**`, `scripts/agk/common.py` and
   `scripts/agk/impact.py`. The other scripts leave the list, each with a `[[testing.map]]` entry built from the tests that
   name or import it.
2. For a changed code file `impact.py` selects the tests its map entries name and the tests of every file that imports
   it, one level, read with `test_map.py`'s import reading, and prints `selected: <file> -> <k> tests (<j> by importers)`.
   A test file that imports it is selected itself. This only adds tests. `always_full`, `thorough` and rule 6 of SPEC-0055
   stay as they were.
3. `check_kit_tests.py` (the kit) and the error check `always-full-infra` of `doctor.py` (a project, and the kit) refuse an
   entry that is not test infrastructure unless the list carries an adjacent `# full: <reason>` comment, on the entry's
   line or the line above it. The refusal names SPEC-0055 rule 6 and the entry by its place (`testing.always_full[2]`),
   never its value (principle 8). What counts as test infrastructure is one list in `impact.py`, by stack.
4. The examples a new project copies in `kit/templates/agk.toml` and `agk.adopt.toml`, and the `test selection` practice of
   `kit/templates/stack-adr.md`, name test infrastructure only.
5. `[testing] budget_seconds` is reported, never enforced. The weekly report gives the full suite's median on the default
   branch against the budget, the slowest ten test files and the workers' balance, each `unknown` when the log does not
   hold it, and over budget says that one brief splits or speeds up the slowest files, never removing a test. It also
   gives the median selected and full minutes of pull request runs and the reason of each full run.

## Consequences

Most pull requests that change a core script run its tests and its importers' tests instead of the full suite. What a
selection misses fails on the default branch, which still runs the full suite after every merge, and `#853` requires a
pull request to be up to date with the default branch before it merges. A project whose `always_full` names ordinary code
fails `doctor.py` until it adds the reason or removes the entry; its selection does not change either way. `impact.py`
now reads the tree's imports for a selection that is not already full.

## Residual

- 2026-11-09: the full suite of this repository prints no per-test durations, so the slowest files and the balance read
  `unknown` for it until the suite's command prints them (`Q-878-1`).
- 2026-11-09: filing the brief when over budget is the conductor's reading of the report line; no check holds it
  (`Q-878-2`).
