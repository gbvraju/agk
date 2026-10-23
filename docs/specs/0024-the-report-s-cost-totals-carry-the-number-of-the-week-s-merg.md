# SPEC-0024: The report's cost totals count the merged changes whose hours are not known

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-031

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "The report's cost totals carry the number of the week's merged changes whose hours are not known, so a reader can say how many lack them without counting." It is generic and project-agnostic: it holds for every project the kit is installed in and for any reader of the report, and it names no project and no reader. Evidence: the total of hours reads `unknown` when any merged change lacks its hours, and a reader had to count the cost lines to say how many; the numbers are in the data already. It is the first of the later intakes that SPEC-0022 names in its residual.
The maintainers answered 3 questions before it was written: the field is `hours_unknown`, an integer on the existing cost totals item, always present and 0 when every hours is known; in a busy week, when the per-change cost items are left out, it still counts all the changes merged in the week, the same set as `merged`; `report.json` `schema` becomes 2 for every report, with SPEC-0022 rules 3, 5 and 7 amended, while the markdown, the inbox output and `facts.json` (its own number 1) stay byte-identical.

## Rules

1. **The field.** The cost totals item of `report.json` (kind `week-totals`, SPEC-0022 rule 5) gains the field `hours_unknown`: a JSON integer, the number of the week's merged pull requests whose hours are `unknown` (the same condition that makes the `hours` of their `pull-request-cost` item and the `hours` of the totals read `unknown`: the created or the merged time is missing or cannot be read). It is present in every totals item and is 0 when every hours is known; it is never omitted, never a null and never the string `unknown`.
2. **The set counted.** It counts every pull request merged in the report's week, the set that `merged` counts, whether or not the per-change cost items are printed (a busy week leaves them out). So `merged` minus `hours_unknown` is the number of changes whose hours are in the total of `hours`; when `hours_unknown` is above 0 the total of `hours` is `unknown`, as before.
3. **Nothing printed changes.** The markdown report and the inbox output are byte-identical to before: the field is data only and the line "This week: ..." does not print it. The markdown rendered from `report.json` alone still equals the printed markdown (SPEC-0022 rule 2); the existing markdown and inbox goldens do not change.
4. **The schema number rises.** `report.json` `schema` is the number 2 for every report (SPEC-0022 rules 3 and 7: adding a field raises the number). `kit/report-schema.json` requires the number 2 and the field `hours_unknown` (an integer, at least 0) on the totals item, so a missing or an extra field fails. `facts.json` and its schema keep their own number 1. A reader that expects schema 1 sees the number change and knows to update.
5. **Unknown stays unknown.** When the facts do not hold the pull requests (SPEC-0022 rule 6) there is no totals item; the `unknown` item stands as before. A week with no merged pull request has no cost items, as before.
6. **Generic and deterministic.** The change adds no import and reads only the facts file; the same facts, day and week give a byte-identical `report.json` (SPEC-0022 rule 8).
7. **How it changes.** SPEC-0022 is Approved: the build changes it by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR: rules 3 (the number of the schema), 5 (the fields of `week-totals`) and 7 (`schema` is 2). The build is a kit change (a bump, the hashes, the plugin and `agk.toml` versions, an ADR that names the protected classes `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`), and the `report.json` goldens, which hold the number and the field, are regenerated with it. It is small.
8. **The tests.** The recorded facts of the report goldens, where some pull request has no time, give a count above 0 and the same facts with the times filled give 0; a busy week counts every merged pull request; every golden `report.json` validates against `kit/report-schema.json` with the number 2; a totals item without the field, with the string `unknown` or with an extra field fails the schema; the markdown and inbox goldens and the markdown rendered from `report.json` are unchanged. No network and no model.

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
- 2026-10-22: brownfield adoption path for teams already working with coding agents, a K5 candidate to plan after the current queue: an observe-only adoption mode (the report and the proof run as advisory, failing nothing); an adoption ladder (observe, guard new PRs, govern new work, measure; legacy code untouched); support for several developers with parallel pull requests; hosts beyond GitHub (already a candidate). Evidence so far: one single-maintainer brownfield adoption only. Validate with one real team pilot before any claim (owner: maintainers) (due 2026-12-31).

## Open questions

none
