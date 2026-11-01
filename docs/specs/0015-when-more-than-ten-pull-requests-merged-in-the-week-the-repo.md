# SPEC-0015: A busy week's report links the full list of merged pull requests

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-022

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "When more than ten pull requests merged in the week, the report's Delivered and Cost sections show the requirements and the totals with one
link to the full list, instead of one line per pull request." The maintainers answered three questions before it was written: each of the two sections ends with the same one link, the link
is a GitHub search of merged pull requests that uses the week's UTC dates (`merged:YYYY-MM-DD..YYYY-MM-DD`, the same dates as the report's opening line), and Delivered says how many pull
requests were merged besides the link.

## Rules

1. Now SPEC-0011 rule 29.
2. Now SPEC-0011 rule 30.
3. Now SPEC-0011 rule 31.
4. Now SPEC-0011 rule 32.
5. Now SPEC-0011 rule 33.
6. Now SPEC-0011 rule 34.
7. Now SPEC-0011 rule 35.
8. Now SPEC-0011 rule 36.

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

- Q-S0015-1 Does GitHub's pull-request search accept `merged:YYYY-MM-DD..YYYY-MM-DD` for the week's dates, and does it read them in UTC? The criteria assume it does for both.
  **Ruled** (maintainers, 2026-10-20): verified on a real search. `https://github.com/gbvraju/agk/pulls?q=is%3Apr+is%3Amerged+merged%3A2026-10-12..2026-10-18` returns merged pull requests with
  #79 at the top and #80 absent. #79 was merged on 2026-10-19 in India (IST) and on 2026-10-18 in UTC, so the search reads the dates in UTC, the same boundary as the report. Rule 5 stands as written;
  there is no fallback.
