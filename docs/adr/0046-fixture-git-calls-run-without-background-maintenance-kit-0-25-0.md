# ADR-0046: the facts test's fixture runs git without background maintenance, kit 0.25.0

- Status: Proposed
- Date: 2026-10-19
- Deciders: maintainers
- Related: ADR-0045
- Requirements: REQ-018

Protected classes: `tests/kit/`, `kit/`, `.claude-plugin/`

## Context

`governance` run 39242038671 (attempt 1, job 118024933940, step "Tests of the checks") failed once and passed on attempt 2 with no change. The failing test was
`test_ac2_it_reads_only_and_leaves_the_work_tree_alone` in `tests/kit/test_facts.py`, reached through the alias target run in `tests/kit_dev/test_init.py`. The failing assert:
`At index 52 diff: '.git/objects/maintenance.lock' != '.git/refs/heads/main'`.

Cause: `git commit` in the fixture starts git's automatic maintenance, which holds `.git/objects/maintenance.lock` for a few milliseconds. The test lists every file, `.git`
included, right after the commit, and on the CI runner (git 2.55) the first listing sometimes catches the lock, so `before != after`. The first theory (a racy index) was
wrong; `--no-optional-locks` would not help because the lock is not an optional one.

Measured locally (git 2.43), polling for the lock while `git commit` runs: seen in 196 of 200 trials as it was, 0 of 200 with `-c maintenance.auto=false -c gc.auto=0`. The
whole failing assert was not reproduced locally (0 of 300 trials of the test sequence), so the mechanism is shown and the CI log names the file.

## Decision

1. The fixture helper `git()` in `tests/kit/test_facts.py` runs every call with `-c maintenance.auto=false -c gc.auto=0`. The listing in the test stays strict (`.git` included).
2. A new test, `test_ac2_a_fixture_commit_starts_no_background_maintenance`, polls for the lock during 20 fixture commits and fails if it is ever seen; it fails with the flags removed.
3. Other installed tests were checked: the only test that lists files under `.git` after a commit is the one above. `tests/kit/drift_fixtures.py`, `review_fixtures.py`, `test_doctor.py`
   (`tree_hash`) and `tests/kit_dev/conftest.py` (`snapshot`) skip `.git`; the `Repo.git` helpers in `tests/kit/conftest.py` and `drift_fixtures.py` commit but never list it. No other change.
4. **Kit 0.25.0**: manifest, hashes, plugin version (`tests/kit/test_facts.py` is installed).

## Consequences

- The test no longer depends on how long git's maintenance runs after a fixture commit. Behaviour of the kit is unchanged; only an installed test file changes.

## Residual

None.
