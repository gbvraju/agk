# ADR-0777: Governance's kit-tests check holds the kit's testing map rules that a quick record missed (REQ-062)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1878, ADR-0731 (the gate runner map rule, moved here), ADR-0359 (the check's first map rule), ADR-0650
  (whole tests and the `kit/agk-kit.mk` guard), ADR-0014, ADR-0208 and ADR-0233 (the record and its check, unchanged),
  ADR-0774 (rule 4c), #1870, #1852, plan #661
- Requirements: REQ-062

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

`prepush.py --quick` runs no test, only the body check, lint, governance and the secret scan. On #1870 a new test that
runs the gate runner was left out of the `scripts/agk/gates/*.py` entry of `[[testing.map]]`; the quick record passed
(`Evidence check: agrees`) and the hosted governance job failed `tests/kit_dev/test_gate_runner_map.py` about 30
minutes later. Governance already runs `check_kit_tests.py` under `--quick`, in `make governance`, in the conductor's
`evidence.py check` and in CI's own `check_kit_tests` step. The owner's word (2026-11-24 06:24 IST, the steward chat,
quoted as data): "Yes, draft all four along with release".

## Decision

1. `check_kit_tests.runner_problems` holds the rule of ADR-0731: every `test_*.py` of `tests/kit/` and `tests/kit_dev/`
   that runs the gate runner (an import line, or the runner's file name in a string outside a docstring) is in the
   gates' entry, and no file that entry names is gone. With a base and `agk.toml` unchanged it reads only the test
   files the change adds or edits; with no base, or with `agk.toml` changed, every one. A file that does not parse
   fails naming its folder as a path class.
2. `check_kit_tests.stale_problems` holds the stale name rule: each test glob of every map entry matches a test file.
3. Both run only in the kit (`kit/agk-kit.mk`) with a `[testing]` table, after `whole_problems`; a project returns
   before any rule, as today. Messages give a count and the setting `testing.map`, never a file name.
4. `tests/kit_dev/test_gate_runner_map.py` imports the rule from the check (one source) and joins the check's map entry.
   `prepush.py`, `evidence.py`, the record's schema and its step list are unchanged (Q-QM-1).
5. A later rule over the kit's own testing map is added to `check_kit_tests.py` with a `tests/kit/` fixture case, not
   only as a `tests/kit_dev/` test.

## Consequences

A map miss fails the builder's quick prepush in seconds, so no passing record can be made, and the conductor's evidence
run sees the same failure. Governance costs about 2.5 s more with no base or an `agk.toml` change; milliseconds
otherwise. No workflow, check name or label changes.

## Residual

The wider shape seen on #1852 (a test that is not a map rule, run only by the full suite) stays open (Q-QM-2,
2026-11-24). Whether a SPEC-0055 amendment is wanted is the reviewers' call; amendment 224 is reserved for it (Q-QM-3,
2026-11-24).
