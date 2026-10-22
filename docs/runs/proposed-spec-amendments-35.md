# Proposed spec amendments 35 (SPEC-0011 rule 8, SPEC-0022 rules 3 and 5; REQ-029 part R2)

Date: 2026-10-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0071. The paths: `docs/specs/0011-inbox-and-report.md`,
`docs/specs/0022-the-weekly-product-report-also-publishes-the-sections-it-com.md`.

1. **SPEC-0011 rule 8.** Part R1 said Needs you and At risk were lines until a later part. They are items now: the opening, every section and the footer are items of the fixed kinds, Needs you being groups
   of items, and the inbox prints the same groups as Needs you. The printed text does not change.
2. **SPEC-0022 rule 3.** The groups of `needs_you` are named: `group` is one of `spec`, `adr`, `question`, `pull-request`, `residual`, `requirement` (the six kinds of the inbox table, SPEC-0011 rule 3).
3. **SPEC-0022 rule 5, titles.** The report prints a title for a single pull request only in the lines "has been open" and "was sent back"; the lines "was merged with no verdict" and "was merged before its
   last commit was cleared" print none. The two `at_risk` kinds for them have entries `{"number"}` without a title (the table said "with `title` when one"); the other two keep `title` for a single entry.
4. **SPEC-0022 rule 5, `unknown`.** The thing that could not be read in the age-limit line is printed `the age limit for pull requests (inbox_hours)`; that is the `what` value (the table named the shorter text).
