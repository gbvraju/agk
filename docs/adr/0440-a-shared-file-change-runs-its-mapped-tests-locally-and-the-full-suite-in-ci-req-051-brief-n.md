# ADR-0440: A shared-file change runs its mapped tests locally and the full suite in CI

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: brief #1031, plan #661, SPEC-0044 rule 1, ADR-0227 (brief #417), ADR-0242 (brief #453), ADR-0422 (brief #980), ADR-0436 (brief #1021)
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `agk.toml`, `tests/kit/`

## Context

On 2026-11-11 the local `prepush.py` of #1022 ran the whole suite for more than 20 minutes, because one changed file
(`scripts/agk/common.py`) matches `[testing] always_full`; when the pull request was marked ready, CI's `proof` job ran
the same full suite again. The local copy added builder time and tokens and caught nothing CI does not. The owner
directed the change on 2026-11-11 ("file it"). SPEC-0044 rule 1 names what keeps the full suite (CI's push run, a
release pull request and `pr_tests = "full"`); a builder's local run is not among them, and CI's runs do not change.

## Decision

1. `[testing]` gains one optional key `local_full`, `"local"` (the default) or `"ci"` (`impact.KEYS`,
   `impact.local_full`); any other value is refused naming `testing.local_full`. Absent, or `"local"`, prepush runs
   exactly as before.
2. With `"ci"`, when `impact` made the selection full because a changed file matches `always_full`, and the profile is
   not `thorough`, `pr_tests` is not `full` (its default), a `[proof]` table can run single files and the selected
   files are below `full_when_share` of the areas' test files, `prepush.left_to_ci` turns it into a selection of its
   mapped files. They run through their areas with the same workers and under the same heavy-step lock, after one
   line `tests: full suite left to CI's proof job (always_full <glob>); ran the <n> mapped test files`; with nothing
   mapped nothing runs and the line says `0`.
3. The record names each such run's set `selected (full left to CI)`, so the conductor's evidence check and the
   verdict see that the full suite did not run locally.
4. This repository sets `local_full = "ci"`.

## Consequences

`project_tests.py`, CI's proof job and the merge gate never call `left_to_ci`: CI still runs the full suite on every
ready head, and the merge still needs it green. `evidence.py` rebuilds the regression runs without the rule, so a record
made under it differs (`not what prepush runs: tests/selected (full left to CI)/<area> (field: name)`); in local mode
(session rule 30), where no CI proof runs, such a record therefore cannot stand in for CI, which is the conservative
outcome. A selection full for another reason (profile `thorough`, unmapped files under `balanced` with no `always_full`
match, `full_when_share`, `pr_tests = "full"`) runs the full suite locally as before. A change that matches
`always_full` and also has unmapped files is full for the `always_full` match, as `impact` reports it, so it runs its
mapped files here too.

## Residual

- 2026-11-11: the after-measure is the brief's: the next always_full change in this repository runs only its mapped
  test files locally while CI's proof job still runs the full suite; the first is this pull request's own change to
  `scripts/agk/impact.py`.
