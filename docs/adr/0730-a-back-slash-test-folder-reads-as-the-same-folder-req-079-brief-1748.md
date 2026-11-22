# ADR-0730: A back-slash test folder reads as the same folder in the environment-settings step (REQ-079)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1748, issue #1747, ADR-0728, SPEC-0072
- Requirements: REQ-079

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On the default branch at 5f82d6e (2026-11-22) the `environment-settings` step (ADR-0728) checks each `test_dirs` entry
with `impact._folder_ok` before it turns back slashes into forward slashes, so an entry such as `.\tests\`, which the
tests floor reads as `tests` (REQ-079 AC7), is refused. The floor then prints no `ok tests-first`, and
`tests/kit/test_tests_floor.py::test_test_dirs_compare_by_forward_slash` fails: the default branch is red (#1747).

## Decision

1. The step turns each back slash of a `test_dirs` entry into a forward slash before it drops the leading `./` and the
   trailing `/` and checks the folder, so `.\tests\` reads as `tests`, as the tests floor reads it.
2. An entry that is no folder (a number, an empty entry, a path outside the repository, a wildcard) is still refused
   with the one line naming `test_dirs` of ADR-0728.
3. No test is weakened (principle 11): `tests/kit/test_tests_floor.py` is unchanged.

## Consequences

The default branch's governance run turns green again. A list of folders written with forward slashes reads as before.
No workflow, ruleset or required check changes.

## Residual

- `common.load_config` still hands each reader the raw value (ADR-0728 residual).
