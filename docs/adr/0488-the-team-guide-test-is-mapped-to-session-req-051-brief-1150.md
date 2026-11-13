# ADR-0488: The team guide test is mapped to session.py

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: brief #1150, brief #1145, pull request #1146, ADR-0486, ADR-0447
- Requirements: REQ-051

Protected classes: `agk.toml`

## Context

Pull request #1146 (brief #1145, ADR-0486) added `tests/kit/test_guide_team.py`, which names `session.py`. On the
merged head 33ef7d5 the `governance` job (job 131549059123) failed with `1 failed, 11829 passed`:
`test_always_full_infra.py::test_a_script_that_left_the_list_has_a_map_entry_with_its_tests[session]` requires every
test that names `session.py` to be listed by the `[[testing.map]]` entry of `scripts/agk/session.py` in `agk.toml`,
and the new test was not listed. The default branch was red.

## Decision

The `scripts/agk/session.py` entry of `[[testing.map]]` in `agk.toml` lists `tests/kit/test_guide_team.py`. The test
and the check are unchanged.

## Consequences

A change to `scripts/agk/session.py` selects the team guide test, and the check passes on the default branch again.

## Residual

None.
