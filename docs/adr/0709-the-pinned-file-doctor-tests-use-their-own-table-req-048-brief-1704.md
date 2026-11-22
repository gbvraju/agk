# ADR-0709: The pinned-file doctor tests check against their own table (REQ-048)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1704, brief #1691, pull request #1699, brief #1506
- Requirements: REQ-048

Protected class this pull request changes: `tests/kit/` (`test_personal_lifecycle.py`). `scripts/agk/` and
`kit/hashes.json` are not changed.

## Context

`test_rule26_doctor_on_a_fresh_sidecar_finds_the_pinned_files_unchanged` and
`test_rule26_doctor_reports_a_pinned_file_changed_by_hand` ran the kit's own `doctor.py`, which compares the sidecar's
pinned copies with the `verbatim` row of the released `kit/hashes.json`. The sidecar's copies are the pull request's
files, and a build never edits `kit/hashes.json` (session rule 14), so any pull request that changes a pinned file
between releases failed `governance` (#1699).

## Decision

1. The two tests run `doctor.py` from a copy of the kit's scripts whose `kit/hashes.json` holds one row, for the
   plugin version, with the digests of the checkout's own pinned files (helper `own_table`). They prove the doctor's
   comparison, not the release table's freshness.
2. A new test, `test_rule26_doctor_passes_a_pinned_file_changed_between_releases`, changes a pinned copy, proves it
   matches a table made from it and that the kit's released row still reports it.
3. No assertion is removed and no check is weakened (principle 11): every assertion of the two tests stands, and a
   copy changed by hand is still reported.

## Consequences

A pull request that changes a pinned rule file between releases no longer turns the personal-mode doctor tests red.

## Residual

None.
