# ADR-0670: A tests floor: the tests-first gate becomes a check (REQ-079)

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1590, SPEC-0072, amendment 198, ADR-0666, ADR-0668, ADR-0673, brief #1586, brief #1587, plan #661
- Requirements: REQ-079

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

On the default branch at 11fa8bc (2026-11-21) `config/playbooks/default.toml` holds `tests-first` as `kind = "judgement"`
("The tests of a brief land before its code."), and `kit/templates/agk.toml`'s `project_tests` passes with no `tests` folder
and on pytest's exit 5 (no tests collected). A product with a work type can therefore pass with no tests at all (gap G17).
SPEC-0072 rule 2 allows a later layer to restate a gate stronger, and rule 9 keeps `test_dirs` and `project_tests`
unchanged. This changes a decision of SPEC-0072 (rules 2, 4 and 9), so amendment 198 proposes the text.

## Decision

1. `default.toml`'s `tests-first` becomes `kind = "check"` with `step = "tests-floor"`, a stronger kind; every work type
   inherits it. The step is `scripts/agk/gates/tests_floor.py`, run by `run_gates.py` (ADR-0666), offline, with no shell.
2. It runs only in a project with a `[delivery] work_type` whose foundation build has merged, read as: the architecture
   record `docs/architecture.md` that the foundation writes (SPEC-0072 rule 5) exists (Q-1590-3). Otherwise it prints
   `not run tests-first: no work type` or `no foundation yet`, never `ok`, so the kit's own repository and an existing
   project are not made red. A stack with no reader yet prints `no reader for <stack>` (as the `layers` step does).
3. It fails, each failure naming the rule and the path class and never a file or a value (principle 8), when
   (a) the `test_dirs` hold no test file of the stack (Python: `test_*.py` or `*_test.py`); (b) the integration folder,
   `<first test_dirs entry>/integration/` for every stack until its pack names another (Q-1590-2), holds none; (c) the
   change (`git diff` from the merge base with `common.resolve_base`'s base) adds or changes a code file of an
   `[architecture]` layer and adds or changes no test file. A file only deleted, or a change that only removes lines,
   needs no test change (Q-1590-1). The kit's installed folders and the `test_dirs` are not layer code.
4. With `mode = "adopt"` rules (a) and (b) are held until the person records today's behaviour as tests
   (`docs/guides/existing-codebase.md` step 3); rule (c) applies to changed code from the first run, which changes nothing
   and so is green.
5. `project_tests`, `test_dirs` (default `["tests"]`, compared by forward slash) and `coverage` are unchanged.
6. The foundation build writes one unit test and one integration test that pass, in the stack's layout (Python:
   `tests/unit/` and `tests/integration/` under the first `test_dirs` entry): amendment 198 to SPEC-0072 rule 4.

## Consequences

A work-type product after its foundation is red in `governance`, `make governance` and `prepush.py` with no test file, with
no integration test, or with layer code changed and no test changed. The kit's own `run_gates.py` output gains one
`not run tests-first: no work type` line and its count rises to 3. No workflow, ruleset or required check changes.

## Residual

- Each stack's pack names its own test and integration forms (SPEC-0072 Residual; due 2027-03-31).
- An adopted project's held rules (a) and (b) are lifted by the person's yes of the existing-codebase guide's step 3
  (brief #1600's baseline; due 2027-01-31).
- A coverage floor stays off until the person's priority orders it (SPEC-0072 rule 8).
