# ADR-0447: The two guard tests of brief #1050 collect in a copied kit and are mapped to session.py

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: brief #1059, brief #1050, pull request #1055, ADR-0444, pull request #1058, Q-1059-1, Q-1048-1
- Requirements: REQ-051, REQ-010

Protected classes: `agk.toml`, `tests/kit/`

## Context

Pull request #1055 (brief #1050, ADR-0444) added `tests/kit/test_architect_review_guard.py` cases and
`tests/kit/test_shadow_guard.py` cases that run `session.py slot` commands. On the merged head b146c29 the step
`Tests of the checks` of `governance` failed, `2 failed, 11173 passed` (run 43102265154), so the default branch is red:

1. `test_agk_mk.py::test_ac1_project_pytest_config_is_neither_read_nor_needed` collects `tests/kit` in a copy of the
   kit that has `scripts/agk/` and `tests/kit/` but no `.claude/hooks/`. `test_architect_review_guard.py` imported
   `REVIEW_RULE` from `architect_guard` at module level, so the collection failed with
   `ModuleNotFoundError: No module named 'architect_guard'`.
2. `test_always_full_infra.py::test_a_script_that_left_the_list_has_a_map_entry_with_its_tests[session]` requires
   every test that names `session.py` to be listed by the `[[testing.map]]` entry of `scripts/agk/session.py` in
   `agk.toml`. The two guard tests now name it and were not listed.

## Decision

1. `test_architect_review_guard.py` reads the hook's `REVIEW_RULE` text from the hook file when a test runs, not by
   an import at collection. The three assertions compare with the same text as before.
2. The `scripts/agk/session.py` entry of `[[testing.map]]` in `agk.toml` lists `tests/kit/test_architect_review_guard.py`
   and `tests/kit/test_shadow_guard.py`.

No check and no hook changes.

## Consequences

Both checks keep their strength (principle 11): the copied kit still must collect, and the map still must list
every test that names the script. A change to `session.py` now selects the two guard tests. The default branch turns
green when this merges.

## Residual

- 2026-11-11: none.
