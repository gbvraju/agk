# ADR-0407: Adoption finds front-end test folders and patterns (REQ-051)

- Status: Accepted
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0270, SPEC-0044, brief #946, plan #661, issue #484
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit_dev/`

## Context

SPEC-0044 rule 10 asks adoption to find a project's front-end test folders and name patterns as
well as its Python ones, so that the proof run finds those tests instead of none. ADR-0270
(Accepted) covers the build in `scripts/agk/`, but it does not name `tests/kit_dev/`, where the
tests of `adopt.py` live and are mapped, so the build cannot use a `Covered-by:` line (session
rule 36). Q-946-1 was answered on the brief: this ADR names both classes and changes no decision
of ADR-0270 or SPEC-0044.

## Decision

`adopt.py`'s `detect_tests` also matches `*.test.ts`, `*.test.tsx`, `*.spec.ts` and
`*.spec.tsx`, and records the topmost folders holding them (`__tests__/`, `e2e/` and `cypress/`
among them) as folder prefixes, never as path globs. The folders the walk skips stay skipped. A
project without such files gets today's answer, and a stamped project keeps its stamped values
(Q-S0044-10). The tests are in `tests/kit_dev/test_adopt.py`, marked `REQ-051`.

## Consequences

A new adopter with TypeScript test runners gets its test folders and patterns in `agk.toml`; a
Python project and an adopted project read as before. `common.DEFAULT_CONFIG` is unchanged.

## Residual

- 2026-11-10: the second part of SPEC-0044 build (d), the `doctor.py` lines of rules 9 and 10, is a
  later brief.
