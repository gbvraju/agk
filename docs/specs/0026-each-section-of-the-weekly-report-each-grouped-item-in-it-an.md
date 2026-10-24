# SPEC-0026: Each section of the weekly report, each grouped item in it and each total that can be unknown states how many it holds

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-033

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "Each section of the weekly report, each grouped item in it, and each total that can be unknown states how many it holds, and nothing the facts could not read is left out silently, so a reader can show totals without counting." It is generic and project-agnostic: it holds for every project the kit is installed in and for any reader of the report, and it names no project and no reader. Evidence: a reader of `report.json` had to count the items of each section and the entries of each group to state a total, and open pull requests whose verdicts could not be read were skipped without a word; the numbers are in the data already. It is the second of the later intakes that SPEC-0022 names in its residual (the first is SPEC-0024). This intake takes the pre-L2 path (SPEC-0012), as SPEC-0025 did: it merges with the spec `Draft` and the ADR `Proposed`, and the next pull request is the approval alone, the two status lines and nothing else, cleared by the maintainers before the build starts.
The maintainers gave seven answers before it was written, in the issue and not as an interview: (1) `report.json` gains `counts` with `delivered`, `proven`, `needs_decision` and `at_risk`; (2) each grouped item carries `count`; (3) the week totals gain `fix_verdicts_unknown`, while an unreadable decisions group and the drift-audit total carry no unknown count; (4) the schema number becomes 3 and the list of kinds is unchanged; (5) open pull requests with unknown verdicts become one unknown item that names how many, with their links, in the pull-request group of the decisions section and in the at-risk section; (6) the drift-audit line appears under at-risk only when its total is above 0 or unknown; (7) the markdown changes only as answers 5 and 6 require.

## Rules

1. **The section counts.** `report.json` (SPEC-0022 rule 3) gains the key `counts`: an object with exactly the keys `delivered`, `proven`, `needs_decision` and `at_risk`, each a JSON integer, the number of items its section lists in `sections` (`needs_decision` being the section `needs_you`: the items inside all its groups together). Every list entry counts as one item as listed, an `unknown` item included, so the number equals what a reader would count in the same document. A section the markdown prints as `nothing this week` is 0. The `cost` section ("Time and review") has no count. `counts` is always present and never a null or the string `unknown`.
2. **The group counts.** Every grouped item, the kinds that list `entries` (`pull-requests-open-long`, `pull-requests-sent-back`, `pull-requests-merged-no-verdict`, `pull-requests-merged-not-cleared`), gains the field `count`: a JSON integer, the number of its `entries`, always present. The groups of the decisions section keep their `count` (a number or `"unknown"`, SPEC-0022 rule 3); the drift-audit item keeps its `total` and `counts` as they are.
3. **The unknown fix verdicts.** The `week-totals` item (SPEC-0022 rule 5) gains `fix_verdicts_unknown`: a JSON integer, the number of the week's merged pull requests whose verdicts are unknown, the same set as `merged` counts, whether or not the per-change cost items are printed. It is present in every totals item and is 0 when none is unknown; it is never omitted and never `"unknown"`. When it is above 0 the total `fix_verdicts` is `unknown`, as before.
4. **What stays not known yet.** A decisions group whose source cannot be read keeps `count` `"unknown"` and its single `unknown` item, and the drift-audit `total` stays a number or `"unknown"`: their items cannot be counted, so no unknown count is added for them and they are not turned into numbers.
5. **Open pull requests with unknown verdicts are not skipped.** Open pull requests whose verdicts cannot be read are no longer left out of the report. The pull-request group of the decisions section gains one `unknown` item, and so does the at-risk section, each naming in its `what` how many open pull requests could not be read, with a link to each of them (`links`, kind `pull-request`). When none is unreadable nothing is added. The `unknown` item has the fields it has (SPEC-0022 rule 5), so the number is in the text of `what`.
6. **The drift-audit line.** The `drift-audit` item of the at-risk section is present only when its `total` is above 0 or `"unknown"`; a total of 0 with no open drift-audit issue is left out (the section may then be empty and prints `nothing this week`). A total of 0 with an open issue stays listed, since the open issue is itself a thing to look at.
7. **The schema number rises and the markdown changes only where asked.** `report.json` `schema` is the number 3 for every report (SPEC-0022 rules 3 and 7: adding a field raises the number), the list of kinds is unchanged, and `kit/report-schema.json` requires the number 3, `counts`, and the new field of each kind, so a missing or an extra field fails. `facts.json` and its schema keep their own number. The markdown report and the inbox output change only by the unknown lines of rule 5 and the absent drift-audit line of rule 6; their goldens change only there, and the markdown rendered from `report.json` alone still equals the printed markdown (SPEC-0022 rule 2).
8. **Generic and deterministic.** The change adds no import and reads only the facts file; the same facts, day and week give a byte-identical `report.json` and markdown (SPEC-0022 rule 8).
9. **How it changes.** SPEC-0022 is Approved: the build changes it by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR: rules 3 (the key `counts`, the number of the schema), 5 (the fields) and 7 (`schema` is 3), and the rule that skipped open pull requests. The build is a kit change (a bump, the hashes, the plugin and `agk.toml` versions, an ADR that names the protected classes `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`), the goldens of `report.json` and of the markdown are regenerated with it, and it is measured first and split at about 600 changed lines of code and tests.
10. **The tests.** For every golden `report.json`: each number of `counts` equals the length of what its section lists, each group `count` equals its entries and `fix_verdicts_unknown` equals the merged pull requests with unknown verdicts, and a test fails if any count differs from what it counts or a field is missing; a week with facts that could not read the pull requests keeps the `unknown` items and adds no count to them; open pull requests with unknown verdicts give the two `unknown` items with their links, and none give no item; a drift-audit total of 0 with and without an open issue, above 0 and unknown; every golden validates against the schema file with the number 3 and a missing or an extra field fails; the markdown goldens differ from before only in the lines of rules 5 and 6. No network and no model.

## Tests

- Rule 1: the four section counts equal the items listed, in a quiet week, a busy week and a week of unknowns; REQ-033 AC1.
- Rule 2: each entries kind carries a `count` equal to its entries; REQ-033 AC2.
- Rule 3: merged pull requests with unknown verdicts give `fix_verdicts_unknown` equal to their number, and 0 when none; REQ-033 AC3.
- Rule 7: every golden has `schema` 3 and validates; a missing or an extra field fails; REQ-033 AC4.
- Rule 5: open pull requests with unknown verdicts give the two unknown items with links; REQ-033 AC5.
- Rule 6: the drift-audit line for a total of 0, above 0, unknown and with an open issue; REQ-033 AC6.
- Rule 4: an unreadable decisions group and the drift-audit total carry no unknown count; REQ-033 AC7.
- Rule 7: the markdown goldens change only where rules 5 and 6 say, and the markdown rendered from `report.json` equals the printed markdown; REQ-033 AC8.

## Proof

REQ-033 AC1 to AC3: *a reader can show each total without counting.* Rules 1 to 3. REQ-033 AC4: *the schema number says the data changed and the schema file enforces it.* Rule 7. REQ-033 AC5 to AC7: *nothing the facts could not read is left out silently, and what cannot be counted is not made to look counted.* Rules 4 to 6. REQ-033 AC8: *the markdown changes only where asked.* Rule 7.

## Residual

- 2026-10-24: the requirement rows and the per-week values are still not in `report.json`, and the proven items still carry no title (SPEC-0022 residual, SPEC-0024 residual); a later intake adds them (due 2026-12-31).
- 2026-10-24: this intake takes the pre-L2 path because `intake.py check --final` accepts only 1 to 3 answers in the opening paragraph; widening it to any number is in the brief of issue #137 (due 2026-12-31).

## Open questions

none
