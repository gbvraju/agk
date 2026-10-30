# ADR-0202: the opt-in test reads its entry from the changelog once a release has moved the fragment (REQ-038, brief 362)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0193
- Requirements: REQ-038

Protected classes: `tests/kit_dev/`

## Context

Brief #362 (priority 0): the 0.60.0 release (#358, pull request #359) moves `changelog.d/opt-in-0-59-0.md` into
`CHANGELOG.md` as the line `- #343 ...` and deletes the fragment, as every release does. Three tests of
`tests/kit_dev/test_upgrade_opt_in_several.py` (ADR-0193) read the fragment by path and fail with FileNotFoundError on the
release head; the release may change only its five files (`check_release.py` rule 5), so the test changes first, in its own
pull request. Measured as the brief says: on d823917, the release head of #359,
`python3 -m pytest -q tests/kit_dev/test_upgrade_opt_in_several.py` gave 3 failed, 20 passed. The new tests were written
first (6 failed, 20 passed at the first checkpoint of the pull request).

## Decision

1. **Where the entry is read (answer 1).** The test reads the 0.59.0 entry from `changelog.d/opt-in-0-59-0.md` while that file
   exists, and otherwise from the one line of `CHANGELOG.md` that starts `- #343 `, its number taken off so that it is the
   fragment's line again. A kit with neither fails with a message naming `#343`. Nothing else changes: the assertions on the
   entry stay as ADR-0193 wrote them.
2. **Both states are tested (answer 2).** Two fixture kits in `tmp_path`, one with the fragment and one with the line moved as
   the release moves it, give the same line; the real kit passes on today's main and on the release head.
3. **This ADR (answer 3)** names `tests/kit_dev/`. No fragment: no file that the installer writes changes.

## Consequences

- The 0.60.0 release pull request moves every fragment unchanged, and the test of the 0.59.0 entry keeps checking it.
- The test names pull request #343 as the number the release gives the line; that number is fixed once #343 merged.

## Residual

- None (2026-10-30).
