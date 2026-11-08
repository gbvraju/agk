# ADR-0348: The kit's own pull requests run only their selected tests; the full suite runs on main (REQ-016, brief 749)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0242, ADR-0305, ADR-0220
- Requirements: REQ-016

Protected classes: `.github/`, `kit/`, `tests/kit/`, `agk.toml`

## Context

Brief #749 (owner yes for the workflow change, quoted in the brief, 2026-11-08): every pull request of this repository
runs the whole kit suite (about 8 minutes) in the governance step `Tests of the checks`, and the merge runs it again on
the default branch. The step runs `make -f agk.mk agk-test`, the target of `kit/agk-kit.mk`, which always ran the full
suite (ADR-0305 gave it workers, nothing else). The selection of `[testing] pr_tests = "selected"` (ADR-0242,
`project_tests.py`, `impact.py`) runs only in the step `Project tests`, which this repository skips
(`hashFiles('kit/agk-kit.mk')`). This repository already sets `pr_tests = "selected"`, a `[proof.kit]` area and an
`always_full` list, so the selection was configured and unused.

## Decision

1. `agk-test` of `kit/agk-kit.mk` plans its run with the plan of `Project tests` (`project_tests.plan`): with
   `pr_tests = "selected"` and the event `pull_request` it runs the files `impact.py` selects for the change against
   its merge base with the base, through the `[proof.kit]` area command, the same map, `always_full` list and
   `profile`. A push, any other event, an unset event, a release pull request (`version` raised in `agk.toml`), a base
   that does not resolve, a selected file in no `[proof]` area, and a full selection run the kit's full suite as
   before, with `[testing] workers` (ADR-0305). Without `selected` nothing changes.
2. It prints one line, `tests: mode selected, <n> test file(s) (event <event>)` or `tests: mode full (<reason>)`,
   after the plan's lines, and appends them to the job summary as `Project tests` does. A selection of nothing (only
   documentation changed) runs nothing and passes. A bad setting fails the target with one line naming it.
3. `.github/workflows/governance.yml` passes `EVENT: ${{ github.event_name }}` to `Tests of the checks`, as
   `Project tests` gets it; the base is `AGK_BASE`, which the step `Base of the merge ref` already writes to the job's
   environment for every later step. Nothing else in the workflow changes.
4. `always_full` stays the safety net: a change to a listed file (among them `kit/agk-kit.mk`, `agk.mk`,
   `scripts/agk/impact.py` and `.github/workflows/**`) runs everything.

## Consequences

A pull request that changes one mapped script runs its mapped test files in `Tests of the checks`; a documentation-only
pull request runs none there. The default branch still runs the full suite on every push, so a gap in the map is
caught on main, not lost. The `proof` workflow is not changed by this decision.

## Residual

- The before and after governance minutes of one documentation-only and one script pull request (brief #749 answer
  5) can only be read from CI runs after this merges; the pull request body records the before figures it could read
  and leaves the after figures as a question (2026-11-08).
- A map entry that misses a guard lets a pull request pass that main then fails; the full run on main is the check,
  and a gap found there is a map fix (2026-11-08).
