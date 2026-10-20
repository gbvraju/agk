# SPEC-0018: Each brief declares a size and expected hours, compared with the actual hours

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-025

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "Each brief declares a size and an expected number of hours, and the weekly metrics and the product report compare them with the actual hours of the pull
requests that carried the brief." It is K5 candidate 16 of the residual register, opened early by ADR-0053. The maintainers answered three questions before it was written: the declaration is per item in
the three brief templates (`Size: S|M|L`, `Expected: <low>-<high> hours`), and the implementation session copies the item's `Size:` and `Expected:` lines into the pull request body together with
`Brief: <path>#<item>`, the metrics reading the body only, as for `Advances:` and `Behaviour:`; "actual" is not `hours_open_to_merge` (an agent builds before it opens the pull request, so open-to-merge
measures review and waiting) but the lead time from the pull request's first commit (author date) to its merge, in a new metrics column `actual_hours`; `Size` is recorded only; SPEC-0007 is Approved, so the
build changes it by an amendment file applied by the build's ADR.

## Rules

1. **The declaration.** `docs/briefs/TEMPLATE.md`, `kit/templates/playbook/brief-day.md` and `kit/templates/playbook/brief-overnight.md` give each item the lines `- Size: S|M|L` and
   `- Expected: <low>-<high> hours`. They are installed templates (a kit change), not checks.
2. **The pull request body.** The implementation session copies the item's two lines into the pull request body with `Brief: <path>#<item>`. The metrics read the body only. The `Size:` value is `S`, `M` or `L`.
   The `Expected:` value is `<low>-<high> hours` with two non-negative numbers (a decimal point allowed), `low` not above `high` (Q-S0018-1). Anything else is malformed.
3. **Two new fields, one new column.** The metrics record gains `estimated_size` and `estimated_hours` (read from the body as the text of rule 2, `unknown` when a line is missing or malformed, the
   `Brief:` line being recorded but not read for the values) and `actual_hours`. `actual_hours` is `merged_at` minus the earliest author date among the pull request's commits, in hours, one decimal,
   round half up, `unknown` when either is missing or the commits cannot be read (Q-S0018-2). `hours_open_to_merge` and `cost_class` are unchanged.
4. **Past pull requests.** A pull request without the lines reads `unknown`. No past record or issue is rewritten.
5. **The facts.** The facts carry, for each pull request, `estimated_size`, `estimated_hours` and `actual_hours`, optional, `unknown` when they cannot be read. `schema` stays 1 (a facts document without them
   reads `unknown`).
6. **The report.** The Cost section's totals line ends with ` estimate: N of M within range`. M is the number of the week's merged pull requests whose `estimated_hours` and `actual_hours` are both readable; N is
   the number of those with `low <= actual_hours <= high`, inclusive, on the one-decimal hours. A pull request with an unknown value is in neither M nor N and is not counted as a miss. When M is 0 the totals line
   ends with ` estimate: none declared this week`. In a busy week the same ending is on the same totals line. Nothing else in the report changes: a week in which no pull request declared an estimate differs from the
   report before this change only by that ending.
7. **No model, no buffer.** The kit makes no estimate, applies no buffer and uses no model. `Size` is recorded and not compared with `cost_class`. A firm's buffer stays its own, applied on top of its own measured actuals.
8. **The renderer stays pure.** `product_report.py` reads the facts file and no other file, and its imports are unchanged (SPEC-0011 rule 13). The metrics keep SPEC-0007 rules 1 and 17: read-only, `GET` only.
9. **SPEC-0007 by amendment.** SPEC-0007 lists the metrics columns and is Approved; the build changes it only by an amendment file `docs/runs/proposed-spec-amendments-N.md`, applied by the build's ADR, which names every
   protected class the change touches. This spec does not edit SPEC-0007.
10. **Size of the build.** If the build measures over about 600 changed lines of code and tests (fixtures, hashes and docs excluded), it is split: the brief templates and the metrics first, the report second.

## Tests

- Rule 1: the three templates contain the two lines for an item; REQ-025 AC1.
- Rules 2 and 3: a metrics fixture with a body carrying `Brief:`, `Size:` and `Expected:` records `estimated_size` and `estimated_hours`; REQ-025 AC2.
- Rules 2 and 3: bodies with a missing line, a letter outside S, M, L, `5-2 hours`, and `two hours` all read `unknown`; REQ-025 AC3.
- Rule 3: a pull request whose commits' earliest author date is 9.5 hours before `merged_at` has `actual_hours` `9.5`, and `hours_open_to_merge` is unchanged; REQ-025 AC4.
- Rule 6: a week with three declared estimates (two within, one above, inclusive at both ends) and one without prints `estimate: 2 of 3 within range`; a week with none prints `estimate: none declared this week`; REQ-025 AC5.
- Rules 4 and 5: facts without the fields render the totals line with only the new ending; the goldens differ only by that ending; REQ-025 AC6.
- Rule 7: no function of the kit computes an estimate, and `cost_class` is unchanged for every fixture; REQ-025 AC7.
- Rule 8: the renderer's imports and file reads are those of SPEC-0011 rule 13; REQ-025 AC8.

## Proof

REQ-025 AC1 to AC3: *the estimate is declared and read from the pull request.* Rules 1 to 3. REQ-025 AC4: *the actual is the lead time.* Rule 3. REQ-025 AC5 and AC6: *the report counts estimates within range
and leaves the past alone.* Rules 4 to 6. REQ-025 AC7: *the kit estimates nothing.* Rule 7. REQ-025 AC8: *the report reads the facts only.* Rule 8. The first weekly metrics and report after a pull request carries the
lines show its `estimated_hours` and `actual_hours` and the Cost ending, and the maintainers read them in that week's issues.

## Residual

- 2026-10-20: a check that the body's `Size:` and `Expected:` lines equal the brief item's, so an estimate cannot be edited after the work (due 2027-01-31).
- 2026-10-20: `Size` is recorded only and is not compared with `cost_class` (due 2027-01-31).
- 2026-10-20: author dates can be rewritten by a rebase, so `actual_hours` can move; a rebased pull request reads what its commits say, not what happened (due 2027-01-31).

## Open questions

- Q-S0018-1 What is the exact grammar of `Expected:`? The criteria assume `<low>-<high> hours`, two non-negative numbers with an optional decimal point, `low` not above `high`, a plain hyphen, and the word `hours`.
  **Ruled** (maintainers, 2026-10-20): as read. `Expected:` is `<low>-<high> hours`, two non-negative numbers (a decimal point allowed), `low` not above `high`, a plain hyphen; anything else is malformed and reads `unknown`.
- Q-S0018-2 Which commit is "the pull request's first commit"? The criteria assume the earliest author date among all commits of the pull request, not the first in list order.
  **Ruled** (maintainers, 2026-10-20): as read. "First commit" is the earliest author date among the pull request's commits; the rebase caveat stays a residual (above).
