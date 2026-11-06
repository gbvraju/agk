# ADR-0307: The type check is a ratchet: its known errors may only go down (REQ-016, brief 633)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0010
- Requirements: REQ-016

Protected classes: `config/`, `tests/kit/`

## Context

ADR-0010 decision 2 made `tests/kit/test_scanner_hygiene.py` run mypy on `scripts/agk` wherever mypy is installed and
fail on any error. The kit code has since grown 85 errors in 27 files under mypy 2.3.1 (issue #588), so that test is
red on every full run of a machine with mypy, and everyone reads past it. CI installs no mypy and skips it. The owner
said yes on 2026-11-06 to ratcheting the type check, then paying the errors off (tracker #630 item 7, brief #633).

## Decision

1. `config/mypy-baseline.txt` records today's errors: one line `mypy <version>` with the exact version that made it,
   then one line `<file> <code> <count>` per file and error code. It holds no line numbers, so moving code does not
   change it.
2. The test `test_mypy_errors_on_scripts_match_the_baseline` replaces `test_mypy_is_clean_on_scripts`. It runs mypy
   on `scripts/agk` and fails when any file has more errors of a code than its baseline line (a change added one), and
   also when the baseline lists errors that are gone, so the baseline only shrinks and is lowered in the same pull
   request that fixes the error. Its failure prints the baseline as it should now read.
3. The pin: the test needs the exact mypy version of the `mypy` line. CI still installs no mypy and skips the test,
   as before. Where another version is installed the test skips with a reason that names the baseline's `mypy` line,
   because another version reports other errors. Moving the pin is a change of the baseline file, made with its
   counts in one pull request.
4. Reading mypy's output fails closed: an error line with no error code, or a total that differs from mypy's
   `Found N errors` summary, fails the test instead of being dropped. A baseline line that is malformed, a count
   below one, a repeated line, or a missing or inexact `mypy` line fails too. A test that needs no mypy checks that
   the baseline file reads and names only files that exist.
5. No error is fixed by this decision; the pay-off briefs are filed by the conductor. ADR-0010 decision 2 (no
   `type: ignore`, fixes in the code) still holds; only "clean" becomes "no worse than the baseline".

## Consequences

The red test of every full run with mypy 2.3.1 turns green, and a change that adds a type error fails it. The test
proves nothing in CI until CI installs the pinned mypy (tracker #630 item 8 pins the CI test tools).

## Residual

- CI installs no mypy, so a type error added in a pull request is caught only on a machine with the pinned version
  (2026-11-06).
