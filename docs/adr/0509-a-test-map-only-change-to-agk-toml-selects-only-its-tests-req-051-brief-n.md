# ADR-0509: A test-map-only change to agk.toml selects only its tests

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: SPEC-0055 rule 6, ADR-0359, brief #1198, plan #661
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

`agk.toml` is covered by no `[[testing.map]]` entry, so under the `balanced` profile a change to it selects every test
file that names it (SPEC-0055 rule 6, ADR-0359): about 200 test files. Almost every brief changes `agk.toml` only to
list its new test file in its script's map entry (`tests/kit/test_always_full_infra.py` checks that it does). Measured on
the merge of #1187 (brief #1184): 210 test files selected, 200 of them only because one map entry gained one test name;
pull request test steps averaged 495 s against 593 s for the full suite.

## Decision

1. Before the unmapped rule for `agk.toml`, `scripts/agk/impact.py` reads the file at the base and at the head with
   `tomllib` and compares them with every `[[testing.map]]` entry left out. When they are equal, `agk.toml` is not
   unmapped and selects only the head's test files matching a test name that was added to, removed from or moved
   between entries (a (code, test) pair present at one end only), plus each test file of the head named
   `test_always_full_infra.py` (in this repository `tests/kit/test_always_full_infra.py`). The installed script names
   the file by its base name only, because a lean install names no kit test path (ADR-0052).
2. Any other difference in `agk.toml`, or a file that does not parse at either end, keeps today's rule exactly.
3. The selected tests carry `agk.toml (testing map only)` in the `code` field, and the plan prints it as the reason.
4. No profile, `always_full`, importers rule or workflow changes; no new dependency.

## Consequences

A pull request whose `agk.toml` change only edits the test map selects a few test files instead of about 210 (the
merge of #1187: 28 instead of 210). The comparison is of parsed values, so a comment-only change outside the map counts
as no difference; comments of `always_full` are checked by `check_kit_tests.py` in governance, not by this selection.

## Residual

- 2026-11-13: a project whose `[testing]` table lives in `pyproject.toml` (`[tool.agk.testing]`) keeps today's rule for a
  map-only change there; a later brief may extend the comparison to that file (due 2027-01-31).
