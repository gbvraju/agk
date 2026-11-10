# ADR-0427: The checklist script passes the type check again (REQ-016, brief 1004)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0010, ADR-0307, ADR-0374, ADR-0420, issue #986, brief #1004
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

With mypy 2.3.1, the version `config/mypy-baseline.txt` pins, `scripts/agk/checklist.py` has 30 type errors and a
baseline of 0, so the ratchet test of ADR-0307 is red on every full local run with that mypy. The errors come from
optional values used without a check: a parsed time that may be `None`, and a saved part that may be missing.

## Decision

1. Each optional value is handled where it is read, as the script already does for a missing field: a take or an
   `Assign:` line with no readable time is skipped, a verdict with no readable time does not date a head, and a saved
   table or list that is missing or of another kind reads as empty or as not saved. No `# type: ignore`, no `cast`
   and no new baseline line (ADR-0010 decision 2, ADR-0307 decision 5).
2. The output does not change: the same nine lines on the same saved inputs. The saved file's time is already
   required by `load_saved`; the window refuses a document without it with a `CheckError` that names the field.
3. Two tests show a record with no time and a read that returned nothing printing the nine lines without a crash.

## Consequences

`python3 -m mypy scripts/agk/checklist.py` reports no error, and the ratchet test's message no longer names the file.

## Residual

- The other over-baseline files of issue #986 still fail the ratchet test (2026-11-10).
