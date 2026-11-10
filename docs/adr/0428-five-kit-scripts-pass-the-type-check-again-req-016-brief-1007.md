# ADR-0428: Five more kit scripts pass the type check again (REQ-016, brief 1007)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0010, ADR-0307, ADR-0427, issue #986, brief #1007
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `config/`, `tests/kit/`

## Context

With mypy 2.3.1, the version `config/mypy-baseline.txt` pins, `scripts/agk/metrics.py` (6 errors, baseline 1),
`scripts/agk/test_map.py` (3), `scripts/agk/sbom.py` (2), `scripts/agk/personal.py` (1) and
`scripts/agk/front_door.py` (1) have 13 type errors between them, so the ratchet test of ADR-0307 is red on every full
local run with that mypy. CI installs no mypy, so they went in unseen. The errors come from optional values used without
a check, and from checks that mypy cannot follow.

## Decision

1. Each optional value is handled where it is read, as the scripts already do for a missing field: a checklist save
   whose time does not read is refused with a `CheckError` that names the field; a job's steps of another kind read as
   none; a project file whose top value is not a table, or a list of advisory ids of another form, is refused with the
   `ValueError` its caller already turns into "no entries" or a refusal; a test whose file name the subject pattern
   does not match has an empty stem; a folder with no personal table has no level; a blob git refuses is noted as not
   read. No `# type: ignore`, no `cast` and no new baseline line (ADR-0010 decision 2, ADR-0307 decision 5).
2. The line `scripts/agk/metrics.py union-attr 1` leaves `config/mypy-baseline.txt`, since the file then has no error
   (ADR-0307 decision 2). No other baseline line changes.
3. The output does not change on any input that works today. Two inputs that crashed with a `TypeError` (a checklist
   time that does not read, a test path with no file name) now give the refusal or the empty stem, each shown by a test
   that was red before the fix.

## Consequences

`python3 -m mypy` reports no error in these five files, and the ratchet test's message no longer names them.

## Residual

- `doctor.py`, `session.py` and `merge_cleared.py` of issue #986 still fail the ratchet test (2026-11-10).
