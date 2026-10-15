# ADR-0014: Every installed check ships with an installed test

- Status: Proposed
- Date: 2026-10-15
- Deciders: maintainers
- Related: ADR-0011, ADR-0013
- Requirements: REQ-009

## Context

PR #22 (the reviewer agent) first put the tests of an installed check, `check_review_report.py`, in `tests/kit_dev/`,
which is not installed: installed repositories got the check without its tests (principle 4). The human reviewer
caught it; the reviewer agent did not, even after shadow review 3 gave it CLAUDE.md and the changed files in full.
The maintainers ruled that a recurring finding becomes a deterministic check, not a reviewer prompt.

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.mk`, `kit/`. This PR changes all five.

## Decision

1. **The check.** `scripts/agk/check_kit_tests.py` reads the verbatim set of `kit/manifest.json`. For every
   `scripts/agk/check_*.py` in that set there must be at least one `tests/kit/test_*.py` in the same set that imports
   the check (`import check_x`, `from check_x import ...`) or runs it (a string naming `check_x.py`). A mention in a
   docstring or a comment, and a string inside a comparison (an exclusion list such as `name in ("check_x.py",)`),
   does not count. A test file on disk but not in the manifest's set does not count. A failure names the check's
   path and the class `tests/kit/`; it never prints a value.
2. **Where it runs.** It is called by `agk-governance` (`agk.mk`) and by CI through it. It is installed verbatim; a
   repository without `kit/manifest.json` (an installed one) has nothing to check, so it passes with a notice.
3. **Proof.** The tests in `tests/kit/test_check_kit_tests.py` include a fixture that reproduces #22 (a check whose
   tests are in an uninstalled directory). Run against the first commit of #22 (071ded6) the check fails, naming
   `scripts/agk/check_review_report.py`; against this repository it passes (9 checks, 19 test files).
4. **Kit version** `0.6.2`: installed content changed (`agk.mk`, the check, its test).

## Consequences

- A new check without an installed test fails `make governance` before review, instead of depending on a reviewer.
- The rule is syntactic: a test that imports the check but asserts nothing satisfies it. What the tests assert stays a
  matter for review.
- Every installed `check_*.py` must now be called by `agk-governance` or be excused in `tests/kit/test_agk_mk.py`, as
  before; this check adds a second, independent guarantee about tests.

## Residual

- 2026-10-15: the check is syntactic; a string that names the check outside a comparison counts even if the test does
  not run it (due 2026-12-15).
- 2026-10-15: class naming in an ADR is still a substring match (ADR-0003 residual).
