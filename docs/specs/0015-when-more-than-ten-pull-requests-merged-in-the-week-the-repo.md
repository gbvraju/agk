# SPEC-0015: A busy week's report links the full list of merged pull requests

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-022

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "When more than ten pull requests merged in the week, the report's Delivered and Cost sections show the requirements and the totals with one
link to the full list, instead of one line per pull request." The maintainers answered three questions before it was written: each of the two sections ends with the same one link, the link
is a GitHub search of merged pull requests that uses the week's UTC dates (`merged:YYYY-MM-DD..YYYY-MM-DD`, the same dates as the report's opening line), and Delivered says how many pull
requests were merged besides the link.

## Rules

1. **A busy week.** A week is busy when more than ten pull requests merged in it, counted as `merged_in_week` selects them (`state` `merged` and `merged_at` inside the report's week). Ten is one
   named constant in `product_report.py`, not a setting, not read from `agk.toml` and not carried by the facts. Ten or fewer is a quiet week.
2. **A quiet week is unchanged.** For a quiet week the report is byte-identical to what the same facts gave before this change. The existing report goldens are the test; the boundary is tested at
   exactly ten (unchanged) and at eleven (collapsed).
3. **Delivered in a busy week.** Every requirement whose `status` is `done` is still listed, in the same order and with the same lines as today. The lines `PR #N "<title>" was merged on <day>` are not
   printed. In their place there is one line after the requirements: `<N> pull requests were merged this week` (`N` the number of pull requests merged in the week), ending with the week link of rule 5.
4. **Cost in a busy week.** No line is printed for a single pull request. The totals line `This week: ...` is printed with its text exactly as today and ends with the week link of rule 5 instead of the
   link to all merged pull requests. It is the only line of the section.
5. **The week link.** `<repo URL>/pulls?q=is%3Apr+is%3Amerged+merged%3A<start>..<end>`, where `<repo URL>` is `https://github.com/` plus `repo` of the facts and `<start>` and `<end>` are the Monday
   and the Sunday of the report's week in UTC, `YYYY-MM-DD`, the dates of the opening line. It is built from `repo` and those two dates only (Q-S0015-1).
6. **Nothing else changes.** Proven, Needs you and At risk are unchanged: every pull request that At risk or Needs you named is still named (a pull request sent back, merged without a verdict or
   merged before its last commit was cleared stays in At risk). The footer, the inbox output and the metrics issue are unchanged.
7. **The renderer stays pure.** `product_report.py` reads the facts file and no other file, and its imports are unchanged (SPEC-0011 rule 13).
8. **Unknown is not a count.** When the facts mark `pull_requests` `"unknown"` the report prints today's unknown line and does not collapse; the count of rule 1 is made only from known rows.

## Tests

- Rules 1 and 3: a facts fixture with eleven pull requests merged in the week and two done requirements: Delivered lists both requirements and one line `11 pull requests were merged this week` with the link, and no `PR #` line; REQ-022 AC1.
- Rules 1 and 4: the same fixture: Cost is the totals line alone, its text as before, ending with the week link; REQ-022 AC2.
- Rule 5: the link of the fixture equals the expected search URL for the dates of its opening line, and no clock or file other than the facts is read; REQ-022 AC3.
- Rule 2: fixtures with ten and fewer pull requests render exactly as the existing goldens; a fixture with exactly ten is unchanged and one with eleven is collapsed; REQ-022 AC4.
- Rule 6: the busy fixture's Needs you and At risk equal those of the same facts rendered before the change, and every pull request they named is still named; REQ-022 AC5.
- Rules 7 and 8: the renderer's imports and file reads are those of SPEC-0011 rule 13; a facts document with `pull_requests` `"unknown"` keeps today's unknown line.

## Proof

REQ-022 AC1 and AC2: *a busy week's Delivered and Cost sections are short and name the week's merged pull requests by one link.* Rules 1, 3, 4 and 5. REQ-022 AC3: *the link is computed from the facts
alone.* Rule 5. REQ-022 AC4: *a quiet week is not changed.* Rule 2. REQ-022 AC5: *nothing at risk is hidden.* Rule 6. The first weekly report of a busy week rendered after the implementation is
merged shows the short form, and the maintainers read it in that week's report issue.

## Residual

- 2026-10-19: the per-pull-request hours and fix verdicts of a busy week are no longer in the report; they stay in that week's metrics issue and behind the link (due 2026-12-31).

## Open questions

- Q-S0015-1 Does GitHub's pull-request search accept `merged:YYYY-MM-DD..YYYY-MM-DD` for the week's dates, and does it read them in UTC? (verify) The criteria assume it does for both; a person checks one search on a real week
  before the spec is Approved, and if it does not, the link is a search with `is:merged` and the `created:` range instead, or the metrics issue of the week.
