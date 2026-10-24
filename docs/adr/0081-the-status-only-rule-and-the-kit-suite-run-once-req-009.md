# ADR-0081: the status-only rule, and the kit suite run once in this repository

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Amends: ADR-0050
- Related: ADR-0005
- Requirements: REQ-009

Protected classes: `tests/kit_dev/`

## Context

ADR-0050 records the standing rule, restated by the maintainers on 2026-10-20: the full `make test` passes before every push, no exceptions. Two costs follow in this repository (the kit's own development).
First, `make test` runs `agk-test` and then `agk-project-test`, and `agk.toml` `project_tests` is the same command as `agk-test` on purpose (the CI proof job runs the kit's tests as the project's tests),
so every local run executes the 2,153-test suite twice. Measured on 2026-10-24, one run after another on the same machine: `agk-test` alone 316.5 s, `agk-project-test` alone 332.3 s, `make test` 642.4 s.
Second, a commit that changes only the status lines a verdict names (the final commit) runs the whole suite although it cannot change a test result, and CI's proof job runs it again on the pull request.
The maintainers' brief (issue #134) asks to run the suite once here and gives the status-only rule (their rule of 2026-10-24).

## Decision

1. **The suite runs once in this repository.** A repository-only `GNUmakefile` (not in `kit/manifest.json`, never installed) is read by GNU make before `Makefile`; it keeps the aliases `governance`, `lint`
   and `traceability` and makes `test` run `agk-test` only. `Makefile` is a verbatim kit file and a protected path, so it is not changed (a change would reach every project and need a kit bump); `agk.mk`,
   `kit/agk-kit.mk`, `agk.toml` `project_tests` and the proof job are exactly as they were. `make -f Makefile test` and `make agk-project-test` still run the second target. A test pins that `make -n test`
   runs the suite once, that the template still runs both targets, and that the two files have the same other aliases.
2. **The status-only rule** (the maintainers' rule of 2026-10-24) amends the standing rule of ADR-0050: a commit that changes only `Final:` status lines (the `- Status:` lines named by a covered fix list,
   SPEC-0021 rule 2) runs `make governance` and the final-commit check (`python3 scripts/agk/intake.py check --final` for an intake), not the full `make test`. CI's proof still runs on the pull request. Any commit that
   changes more than those lines runs the full `make test` before the push, as before. The rule is written here, in a decisions-log row, and nowhere else in this repository: ADR-0050 is Accepted and
   changes only its status line, and no other file of the repository states it.
3. **Parallel tests are measured, not adopted** (issue #134 step 4): the result is in the pull request body; a ruling decides later.

## Consequences

- A local `make test` here takes about one suite run instead of two. The CI jobs are unchanged.
- A final commit costs a governance run, not a suite run; the proof of the pull request is CI's.

## Residual

None.
