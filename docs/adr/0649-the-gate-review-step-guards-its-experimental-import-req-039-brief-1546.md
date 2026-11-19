# ADR-0649: The gate's `review` step guards its import of an experimental file (REQ-039, REQ-048)

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: brief #1546, brief #1503, brief #1214, ADR-0634, ADR-0514, ADR-0610
- Requirements: REQ-039, REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The default branch is red since #1527 (brief #1503, ADR-0634) merged at 0d4ba3a: `personal.py`, which every install
writes (`verbatim` in `kit/manifest.json`), imports `check_review_report` inside `review_step`, and that file is
installed only with the experimental files. `tests/kit/test_installed_imports.py` (ADR-0514) fails on it:
`personal.py:523 imports check_review_report (function level)`. In a default install the `review` level would stop
on an `ImportError` instead of failing by name.

## Decision

1. `review_step` imports `check_review_report` in a `try` and, on `ImportError`, fails the `review` step with one line
   that names the missing file's path, never a value: `gate: review FAIL: the reviewer report check is not installed
   (path: scripts/agk/check_review_report.py)`. The import line is marked `kit-only`, as ADR-0514's test allows a
   guarded import, in the form `common.py` uses for `personal_state` (ADR-0610).
2. The manifest does not change: `check_review_report.py` stays experimental. Moving it to the default install is a
   separate decision.
3. One test in `tests/kit/test_personal_gate.py` holds rule 1. The import test is unchanged (principle 11).

## Consequences

The default branch turns green. A default install that sets `level = "review"` sees a named failure in place of a
traceback; the experimental install and the kit behave as before.

## Residual

Whether `check_review_report.py` should join the default install, so the `review` level works without the
experimental files, is left to the maintainers (Q-1546-1).
