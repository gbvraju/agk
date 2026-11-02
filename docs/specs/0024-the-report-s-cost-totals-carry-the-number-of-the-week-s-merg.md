# SPEC-0024: The report's cost totals count the merged changes whose hours are not known

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-031

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "The report's cost totals carry the number of the week's merged changes whose hours are not known, so a reader can say how many lack them without counting." It is generic and project-agnostic: it holds for every project the kit is installed in and for any reader of the report, and it names no project and no reader. Evidence: the total of hours reads `unknown` when any merged change lacks its hours, and a reader had to count the cost lines to say how many; the numbers are in the data already. It is the first of the later intakes that SPEC-0022 names in its residual.
The maintainers answered 3 questions before it was written: the field is `hours_unknown`, an integer on the existing cost totals item, always present and 0 when every hours is known; in a busy week, when the per-change cost items are left out, it still counts all the changes merged in the week, the same set as `merged`; `report.json` `schema` becomes 2 for every report, with SPEC-0022 rules 3, 5 and 7 amended, while the markdown, the inbox output and `facts.json` (its own number 1) stay byte-identical.

## Rules

1. Now SPEC-0011 rule 78.
2. Now SPEC-0011 rule 79.
3. Now SPEC-0011 rule 80.
4. Now SPEC-0011 rule 81.
5. Now SPEC-0011 rule 82.
6. Now SPEC-0011 rule 83.
7. Now SPEC-0011 rule 84.
8. Now SPEC-0011 rule 85.

## Tests

- Rule 1: facts with merged pull requests lacking a time give `hours_unknown` equal to their number; REQ-031 AC1.
- Rule 1: a week with every hours known gives 0, present in the totals item; REQ-031 AC2.
- Rule 2: a busy week, whose per-change items are left out, counts every merged pull request; REQ-031 AC3.
- Rule 3: the markdown and the inbox goldens are byte-identical, and the markdown rendered from the parsed `report.json` equals the printed markdown; REQ-031 AC4.
- Rule 4: every golden `report.json` has `schema` 2 and validates against the schema file; a missing field, a string and an extra field fail; the facts schema is unchanged; REQ-031 AC5.
- Rules 5 and 6: unknown pull requests give the `unknown` item as before; two runs are byte-identical.

## Proof

REQ-031 AC1 to AC3: *a reader can say how many merged changes lack their hours without counting, in a quiet week and a busy one.* Rules 1 and 2. REQ-031 AC4: *nothing printed changes.* Rule 3. REQ-031 AC5: *the schema number says the data changed and the schema file enforces it.* Rule 4.

## Residual

- 2026-10-22: the requirement rows and the per-week values are still not in `report.json` (SPEC-0022 residual); when a later intake adds them, the proven and not-proven items should also carry the requirement's title, so a reader can show the plain sentence instead of the identifier (evidence: a reader could only show REQ-nnn). Generic (owner: maintainers) (due 2026-12-31).

## Open questions

none
