# SPEC-0016: At risk shows one line per kind of pull request risk

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-023

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "At risk shows one line per kind of risk with the numbers of the pull requests it applies to, so a long list becomes a few lines and every pull
request is still named." The maintainers answered three questions before it was written: only the four pull-request kinds are grouped (the overdue residuals and the drift line stay as today); two or more
pull requests of one kind become one line and one stays exactly as today, with the numbers in ascending order, each its own link and no ranges; a grouped line drops the titles and keeps the per-pull-request
value in brackets for the two kinds that have one. The case that prompted it: on the live report 88, 33 of 37 At risk lines were the same kind (`docs/runs/short-report-live-1.md`).

## Rules

1. Now SPEC-0011 rule 37.
2. Now SPEC-0011 rule 38.
3. Now SPEC-0011 rule 39.
4. Now SPEC-0011 rule 40.
5. Now SPEC-0011 rule 41.
6. Now SPEC-0011 rule 42.
7. Now SPEC-0011 rule 43.
8. Now SPEC-0011 rule 44.
9. Now SPEC-0011 rule 45.
10. Now SPEC-0011 rule 46.

## Tests

- Rules 3 and 5: a facts fixture with three pull requests merged with no verdict, one open for 41 days and one for 30 days: each grouped line names every number in ascending order with links, and the set of numbers equals the set before the change; REQ-023 AC1; REQ-023 AC4.
- Rules 2 and 6: fixtures with one pull request per kind render the At risk section exactly as the existing goldens; REQ-023 AC2.
- Rule 4: the open-too-long and sent-back lines carry the brackets of the single line's value and no title; REQ-023 AC3.
- Rule 1: overdue residuals and the drift line in a fixture with grouped kinds are printed as before; REQ-023 AC5.
- Rule 8: the renderer's imports and file reads are those of SPEC-0011 rule 13; REQ-023 AC6.
- Rule 9: a facts document with `pull_requests` `"unknown"` keeps today's unknown line; REQ-023 AC7.
- Rule 7: Delivered, Proven, Needs you, Cost and the footer of the grouped fixture equal those of the same facts before the change; REQ-023 AC8.

## Proof

REQ-023 AC1 and AC3: *a long At risk list is a few lines.* Rules 3 and 4. REQ-023 AC4: *nothing at risk is hidden.* Rule 5. REQ-023 AC2: *a short list is not changed.* Rules 2 and 6. REQ-023 AC5, AC7 and
AC8: *only the four kinds change.* Rules 1, 7 and 9. REQ-023 AC6: *the numbers come from the facts alone.* Rule 8. The first weekly report rendered after the implementation is merged shows the short form
for a week with several pull requests of one kind, and the maintainers read it in that week's report issue.

## Residual

- 2026-10-20: a grouped line no longer shows the title of a pull request; it is one click away on the number (due 2026-12-31).

## Open questions

- Q-S0016-1 What is the exact wording of a grouped line, and does a line made of several links satisfy "each number its own link" in the issue as GitHub renders it? The criteria assume the wordings of rule 4,
  inline markdown links `[#12](url)`, and no trailing link; the maintainers rule the wording before the spec is Approved.
  **Ruled** (maintainers, 2026-10-20): as read. Inline `[#12](url)` is "each number its own link"; the grouped wordings of rule 4 stand.
