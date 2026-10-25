# ADR-0142: The weekly report carries the shadow review's catch rate, report schema 7 (REQ-042, build (c) of SPEC-0035)

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0128, ADR-0138
- Requirements: REQ-042

Protected classes: `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Build (c) of SPEC-0035 on #207 (assigned to `builder-c` on #204; ADR-0142 and amendment 78 were reserved on #207). Rule 5: the weekly report gains the catch-rate line and the counts of rule 4 next to the conductor's
verdicts; this raises the report schema (it stood at 6) and the build merges only after the portal reader of the new number is merged and deployed, with a line `Readers:` in its body, as for schemas 4 to 6. The facts
save what the report needs. The tests were written first (`tests/kit/test_facts_shadow.py`, `tests/kit/test_report_shadow.py`; before the code all 28 of their cases failed).

## Decision

1. **The facts** (`scripts/agk/facts.py`, `kit/facts-schema.json`): an optional section `shadow` (`facts.json` keeps schema 1). It holds the counts of `shadow_rate.py` for the pull requests merged in the window of the
   facts (`--weeks`, 8 by default): `issue` (the number of the one open issue labelled `agk-shadow`), `unpaired` and `unread`, `weeks` (ISO week of the merge -> counts) and `total`; the counts are `heads`,
   `right_conductor_only`, `right_shadow_only`, `right_both`, `wrong_conductor`, `wrong_shadow`, `unmarked_heads` and `unmarked_findings`. No open issue is `{"issue": null}` (a review that is not running); two open issues,
   an unreadable copy, no listed author and a refused mark are `unknown`, never zero. The comments of each merged pull request are the copy the facts already fetch for the flow (`pull_record` keeps them), so no
   request is added except the list of issues labelled `agk-shadow` and the comments of that issue. `shadow_rate.py` gains `count_pulls` (the counting on merged pull requests with their comments, which `count` now calls)
   and `summary` (the counts as fields); the script and its output are unchanged.
2. **The report** (`scripts/agk/product_report.py`, `kit/report-schema.json`): `report.json` takes schema number 7. The item `week-totals` gains `shadow`: an object `{week, total, unpaired, unread}` whose `week` and
   `total` hold the eight counts and `catch_rate` (the right conductor findings, `right_conductor_only + right_both`, over those plus `right_shadow_only`, printed `R/T (P%)` with one decimal, `none` without a right
   finding, never 0), or `not-running`, or `unknown` (a missing or unreadable section, or a count that is not a whole number). A week with no shadow-reviewed head has zero counts and the rate `none`. The markdown adds
   to the totals line `shadow review: heads reviewed by both ..; right: conductor only .., shadow only .., both ..; wrong: conductor .., shadow ..; unmarked heads ..; catch rate .., all time ..`
   (`shadow review: not running` and `shadow review: unknown` otherwise). The report reads the facts and nothing else.
3. Amendment 78 (`docs/runs/proposed-spec-amendments-78.md`) is applied to SPEC-0009, SPEC-0022 and SPEC-0024. The product-owner guide describes the line without a number about the conductor (SPEC-0035 rule 6). A
   flow-mode fragment `changelog.d/req-042-report-catch-rate.md` records the change; `CHANGELOG.md` and `kit/hashes.json` are not touched.

## Readings taken where the brief leaves a point open

Recorded as questions in the pull request, the most conservative reading each: the counts are those of the pull requests merged in the window of the facts, so "in total" is the total of the window and not of all time
(the facts do not fetch older pull requests); the line sits in the totals line of the Cost section (`week-totals`), which is where the report already prints the conductor's fix verdicts and corrections, and so it
appears only in a week in which something merged; "the one open issue" with two open issues is `unknown`, not the lowest number; a week that has no entry in `weeks` has zero counts, not `unknown`, because the
section was read; the schema keeps `catch_rate` a string in the form of `shadow_rate.py` so that a reader prints what the script prints.

## Consequences

- Anyone reading the report sees how much the conductor catches without a person stating a rate; `unknown` and `none` are never 0.
- The pull request changes `report.json`: it merges only after the portal reader of schema 7 is merged and deployed (`Readers:` in the body).

## Residual

- 2026-10-25: the total is the window of the facts, not all time (due 2026-12-31).
- 2026-10-25: one account for both reviewers cannot be told apart (SPEC-0035 residual); the line is only as blind as the role file (due 2026-12-31).
