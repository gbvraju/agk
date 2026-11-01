# SPEC-0022: The weekly report also publishes its sections as data in report.json

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-029

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "The weekly product report also publishes the sections it computed as data, in a report.json beside facts.json in the same artifact, so any reader can
show the same report without reimplementing its rules." It is generic and project-agnostic: it holds for every project the kit is installed in and for any reader of the report, and it names no project and no
reader. Evidence: reproducing the report's rules in another program was measured at about 2,300 changed lines; data removes that duplication and the drift it invites.
The maintainers answered 3 questions before it was written: the markdown and the inbox output are byte-identical to before (the goldens do not change) and `report.json` covers the weekly report; an item is data only with no printed text, the item
kinds are a fixed list in this spec each with its fields, and a new kind or field is a schema change (the schema number goes up) so a reader can rely on the list; the artifact keeps the name
`agk-facts-<week>` (renaming would break readers) and holds exactly `facts.json` and `report.json`, the run fails if either is missing, and the later intake for the per-week values and the requirement rows
is due 2026-12-31.

## Rules

1. Now SPEC-0011 rule 66.
2. Now SPEC-0011 rule 67.
3. Now SPEC-0011 rule 68.
4. Now SPEC-0011 rule 69.
5. Now SPEC-0011 rule 70.
6. Now SPEC-0011 rule 71.
7. Now SPEC-0011 rule 72.
8. Now SPEC-0011 rule 73.
9. Now SPEC-0011 rule 74.
10. Now SPEC-0011 rule 75.
11. Now SPEC-0011 rule 76.
12. Now SPEC-0011 rule 77.

## Tests

- Rules 1 to 4: `--json` writes the document with the opening, the five sections and the notices, the markdown unchanged; REQ-029 AC1.
- Rule 2: the markdown rendered from the parsed `report.json` equals the printed markdown for every golden facts, and the inbox goldens and the report goldens are unchanged; REQ-029 AC2.
- Rule 6: facts with unknown values give the string `unknown` in every section, never a number or a null; REQ-029 AC3.
- Rules 5 and 7: every golden `report.json` validates against `kit/report-schema.json`; an extra kind, an extra field and a missing field fail; REQ-029 AC4.
- Rule 8: two runs give byte-identical files; REQ-029 AC5.
- Rule 9: the workflow writes both files in the report step, uploads exactly the two paths, fails when either is missing or empty and leaves the issue; REQ-029 AC6.
- Rules 9 and 10: the permissions, retention, pin and order are unchanged and nothing else publishes the files; REQ-029 AC7.
- Rule 10: the script and the schema name no project or reader, add no import and read only the facts file; REQ-029 AC8.

## Proof

REQ-029 AC1 and AC2: *any reader gets the same report as data, and the markdown is rendered from it, so the two cannot differ.* Rules 1 to 4. REQ-029 AC3 to AC5: *unknown stays unknown, the list of kinds is closed
and the file is reproducible.* Rules 6 to 8. REQ-029 AC6 and AC7: *the artifact holds both files and nothing else changes.* Rule 9. REQ-029 AC8: *nothing project-specific.* Rule 10. The first scheduled run after
the build is merged shows both files in the artifact of its run page, and the maintainers download it and compare `report.json` with the issue of that week.

## Residual

- 2026-10-22: the per-week values and the requirement rows are not in `report.json`; a later intake (owner: maintainers) adds them to the same file, as a schema change (due 2026-12-31).
- 2026-10-22: the items carry no printed text, so a reader writes its own sentences from the kinds; the wording of the markdown can change without a schema change, and a reader that copies it can drift (due 2026-12-31).
- 2026-10-22: the structure is built from the facts alone, so a report is only as complete as the facts; a field the facts do not hold is `unknown` (due 2026-12-31).

## Open questions

none
