# ADR-0211: each contradiction the pilot found has a test (REQ-039, brief 383)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0161, ADR-0163
- Requirements: REQ-039

Protected classes: `tests/kit/`

## Context

Brief #383 (priority 2, split from #278): plan #278 measures success partly by "the three contradictions have tests". A project
pilot found three places where one rule of the kit contradicted another: (a) a stack ADR could not be accepted by a `Final:`
commit, since `engines.py stack-check` refuses `Chosen` while Proposed and a `Final:` commit may change only status lines (fixed by
brief #274, ADR-0163); (b) the conductor's guard allows Python only as `python3 -I`, which broke every kit script that imports
another (fixed by brief #270, ADR-0161); (c) a check that fails once the charter is accepted, with no fix found in the changelog.
None was tested as a contradiction, one rule against the other.

## Decision

1. **One test file, one test per contradiction that has a fix (answer 1).** `tests/kit/test_core_contradictions.py` holds:
   (a) `test_a_stack_adr_is_accepted_by_one_ordinary_commit_that_both_checks_pass`: one ordinary commit sets `Chosen` and
   `Status: Accepted` together; `engines.py stack-check` and `check_final_clearance.py` (under a plain cleared verdict) both pass
   it, and the `Final:` route on the same change still fails naming the ordinary commit;
   (b) `test_b_every_importing_kit_script_starts_under_the_guards_isolated_python`, one case per script under `scripts/agk/` that
   imports another: `python3 -I <script> --help` from an unrelated folder ends with exit 0, 1 or 2 and no import error or
   traceback (Q-383-2).
   (c) has no test: `playbook.py check-start` rule 5 refuses a charter that is not Proposed (`the charter is not Proposed`), so
   a project whose charter is already `Accepted` before its start pull request fails it. On the default branch that is a
   decided rule, asserted by `tests/kit_dev/test_playbook.py::test_ac1_charter_failures_name_the_rule`; a test that it passes
   would contradict that rule (Q-383-1). It is recorded as a residual below, with no test and no expected failure.
2. **Contradiction (c) (answer 2).** Nothing is changed for it here: a live contradiction is a new brief.
3. **Tests only (answer 3).** No script, rule or spec changes. Flow mode: one fragment, `changelog.d/core-contradictions.md`.

## Log

- 2026-10-30, verdict on 183106b: Q-383-1, (c) is `check-start` rule 5 on a charter created `Accepted`; it is deliberate on
  the default branch (`tests/kit_dev/test_playbook.py` asserts it), so by brief answers 2 and 3 no test and no expected failure
  are added, nothing is changed, and (c) is recorded as a residual; this replaces the field note's expected-failure suggestion.
  Q-383-2, the reading is right: the contradiction is the import error, so exit 0, 1 or 2 with no traceback passes, and the four
  scripts that refuse `--help` with exit 1 are not failures.

## Consequences

- A change that brings back contradiction (a) or (b) fails a test named after it.
- Contradiction (c) stays as the decided rule of `check-start` until a later brief rules on it.

## Residual

- 2026-10-30: contradiction (c), a question for a later brief: how a project whose charter was created `Accepted` outside the
  start pull request gets started, given `playbook.py check-start` rule 5 (`the charter is not Proposed`) and its test
  `tests/kit_dev/test_playbook.py::test_ac1_charter_failures_name_the_rule` (owner: maintainers; due 2026-12-15).
