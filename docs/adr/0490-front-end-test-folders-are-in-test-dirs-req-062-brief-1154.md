# ADR-0490: Front-end and end-to-end test folders are in test_dirs

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: brief #1154, issue #484, plan #661, ADR-0407
- Requirements: REQ-062

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

Issue #484 (the pilot run of 2026-11-02 on AGK 0.63.0): new tests in `e2e/` and `frontend/src/test/` were outside
`test_dirs`, so proof read `unknown (no-test-files)` on every design pull request. `init.py` always wrote
`test_dirs = ["tests"]` from `kit/templates/agk.toml`; only `adopt.py` took the folders from what it found. `doctor.py`
warned only when `test_dirs` matched no test file at all, never when test files existed elsewhere.

## Decision

1. When the target has no `agk.toml` yet and holds any of `e2e/`, `tests/e2e/`, `frontend/src/test/`, `frontend/tests/`,
   `src/__tests__/` or `cypress/`, `init.py` writes them into `test_dirs` beside `tests`, in that order, and prints one
   line `test_dirs: added <folders> (...)`. A target with none of them gets `["tests"]` as before. A target that already
   has an `agk.toml` is rendered as before, so a re-run of init compares against the same file.
2. `doctor.py` prints one information line,
   `doctor: warning: test files outside test_dirs: <up to three folders>; fix: add them to test_dirs in agk.toml`, when
   files named `test_*.py`, `*_test.py`, `*.test.*`, `*.spec.*` or `*_test.go` sit outside every `test_dirs` folder and
   match no `test_patterns`. The folders named are the topmost that hold such files, sorted. The walk skips dot folders
   (`.git/` among them), `vendor/`, the folders `adopt.py` skips (`node_modules/` among them) and the kit's own folders
   (`tests/kit/`, `scripts/agk/`). The line writes nothing and changes no exit code.
3. `docs/guides/testing.md` says both; the new `tests/kit/test_test_dirs_front_end.py` is listed in the `[[testing.map]]`
   entries of `scripts/agk/init.py` and `scripts/agk/doctor.py` in `agk.toml`.

## Consequences

A new project with a front end gets its test folders read by proof from its first pull request, and a project whose
tests sit outside `test_dirs` is told which folder to add. No test command changes, and no workflow changes.

## Residual

A test file whose name matches `test_patterns` but sits outside `test_dirs` (with the default `["test_*.py"]`, a
`scripts/test_tool.py`) is not warned, as the brief's answer 2 reads; proof still does not count it.
