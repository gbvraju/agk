# Proposed spec amendments 21 (SPEC-0006 and SPEC-0011; found by the pilot, Day 14 E1b)

Date: 2026-10-18 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). The paths:
`docs/specs/0006-doctor.md`, `docs/specs/0011-inbox-and-report.md`.

**Applied by ADR-0034** (2026-10-18) on the maintainers' brief: the pilot repository had Issues disabled, so the workflows that write
issues (the metrics, the drift audit and the product report) could not write theirs.

## SPEC-0006 (`docs/specs/0006-doctor.md`)

1. **Rule 5, a new check `issues-disabled`** (error, maintainers' ruling of Q-K4-162): fails when the repository setting `has_issues` is false and any of the three workflow
   files that write issues exists in ROOT; ok otherwise (also when nothing writes an issue, whatever the setting). `cannot-check` when the
   repository read fails (its reason class) or lacks `has_issues` (`bad-response`). Printed fix: enable Issues in the repository settings,
   or delete the workflow files that write issues. The fail message names the setting and the installed files, never a value.
2. **Rule 6, the reads.** `has_issues` comes from the repository read the doctor already makes; there is no new read and no new path.
3. **Rule 15, fixtures.** Three cases: `issues-disabled` (fails), `issues-disabled-no-workflows` (ok), `issues-unknown` (cannot-check).

## SPEC-0011 (`docs/specs/0011-inbox-and-report.md`)

4. **Rule 17.** The install notice about workflows with `issues: write` is followed by a warning line that Issues must be enabled on
   the repository, and that `agk doctor` checks it. Init and adopt print it; neither reads GitHub.
