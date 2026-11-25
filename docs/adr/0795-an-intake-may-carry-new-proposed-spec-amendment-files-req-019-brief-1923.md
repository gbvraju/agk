# ADR-0795: An intake may carry new proposed spec amendment files beside its three (REQ-019)

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1923, SPEC-0012 rule 11 (C2), brief 557 (the decision-file exception of C2), ADR-0083, ADR-0793,
  ADR-0275 (amendment numbers), amendment 242
- Requirements: REQ-019

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Two intakes whose briefs ask for proposed spec amendments (#1920 for brief #1918, #1922 for brief #1919) failed their own
`intake.py check` with `FAIL intake: C2 the difference is not the requirements file, one new spec and one new ADR`: C2
let only new decision files sit beside the three files of rule 4, so each verdict read the intake form by hand. Elsewhere
the kit already allows these files beside a spec pull request (`check_pr_body.NONE_SHARED`) and checks their numbers
(`check_numbers.py`). The owner's word (2026-11-25, the steward chat, quoted as data): "Yes, file the intake
amendment-file brief".

## Decision

1. **C2 accepts new amendment files.** `Intake.files` drops from the difference, beside new decision files, each added
   (`A`) path whose full path matches `docs/runs/proposed-spec-amendments-<digits>.md`. The pattern is one, `common.AMENDMENT`,
   moved there from `check_numbers.py`, which imports it, so the form cannot drift. Any number of such files may be added.
2. **Nothing else changes.** A modified or deleted amendment file, one in another folder or of another name, a row of the
   frozen `docs/runs/decisions-log.md` and any other file still fail C2 with today's line. C2 reads no amendment's content,
   checks no number (`check_numbers.py` does, in governance) and requires no amendment. `check --final` and C1 are unchanged.
3. **One list.** The kinds an intake may add are one tuple, `intake.INTAKE_EXTRAS`; a test asserts that each `docs/runs/`
   kind of `check_pr_body.NONE_SHARED` but the frozen log is accepted by C2.
4. SPEC-0012 rule 11 C2 still reads "exactly the three files of rule 4"; amendment 242 proposes its words and the spec is
   not edited here (`Q-IA-1`).

## Consequences

An intake with proposed amendments passes its own check, so its verdict no longer reads the intake form by hand. A new
document kind added to `NONE_SHARED` and not to `INTAKE_EXTRAS` fails a test, not an intake.

## Residual

C2 still accepts an amendment number with a leading zero (`-0240.md`), as `check_numbers.py` reads it today; unchanged.
Recorded 2026-11-25.
