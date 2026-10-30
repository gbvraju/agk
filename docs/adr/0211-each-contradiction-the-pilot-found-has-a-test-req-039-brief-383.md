# ADR-0211: each contradiction the pilot found has a test (REQ-039, brief 383)

- Status: Proposed
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

1. **One test file, one test per contradiction (answer 1).** `tests/kit/test_core_contradictions.py` holds:
   (a) `test_a_stack_adr_is_accepted_by_one_ordinary_commit_that_both_checks_pass`: one ordinary commit sets `Chosen` and
   `Status: Accepted` together; `engines.py stack-check` and `check_final_clearance.py` (under a plain cleared verdict) both pass
   it, and the `Final:` route on the same change still fails naming the ordinary commit;
   (b) `test_b_every_importing_kit_script_starts_under_the_guards_isolated_python`, one case per script under `scripts/agk/` that
   imports another: `python3 -I <script> --help` from an unrelated folder ends with exit 0, 1 or 2 and no import error or
   traceback (Q-383-2).
2. **Contradiction (c) (answer 2).** It is not built here until the conductor answers Q-383-1 on the pull request.
3. **Tests only (answer 3).** No script, rule or spec changes. Flow mode: one fragment, `changelog.d/core-contradictions.md`.

## Consequences

- A change that brings back contradiction (a) or (b) fails a test named after it.

## Residual

- 2026-10-30: Q-383-1, contradiction (c), is open on the pull request (due 2026-11-15).
- 2026-10-30: Q-383-2, four kit scripts (`check_brief.py`, `check_pr_body.py`, `config.py`, `reviewers.py`) answer `--help`
  with their own refusal and exit 1; test (b) accepts exit 1 with no traceback, a reading of "exit 0 or 2" for the maintainers
  (due 2026-11-15).
