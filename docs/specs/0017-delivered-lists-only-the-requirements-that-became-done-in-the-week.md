# SPEC-0017: Delivered lists only the requirements that became done in the week

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-024

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "Delivered lists only the requirements that became done during the week of the report, not every requirement that was ever done." The maintainers
answered three questions before it was written: the week of a requirement is the date, in UTC, of the commit on the default branch's first-parent history that last changed its `Status:` line to `done`
(with squash merges that commit is the merge itself, so it is the merge date, and no pull request is looked up); a requirement whose week cannot be read stays listed with its usual line and
`(week it became done: unknown)`, and a readable one outside the week is not listed; a week with nothing newly done shows no requirement line, the pull request lines are unchanged, and `schema` stays 1
with an optional per-requirement field that is `unknown` when it cannot be read, as for `path`, `proof_reason` and `kit_version`. The case that prompted it: REQ-021 and REQ-022, done on 2026-10-20,
appeared in the report of week W42 (`docs/runs/short-report-live-1.md`), and every later report would list them again.

## Rules

1. Now SPEC-0011 rule 47.
2. Now SPEC-0011 rule 48.
3. Now SPEC-0011 rule 49.
4. Now SPEC-0011 rule 50.
5. Now SPEC-0011 rule 51.
6. Now SPEC-0011 rule 52.
7. Now SPEC-0011 rule 53.
8. Now SPEC-0011 rule 54.
9. Now SPEC-0011 rule 55.

## Tests

- Rules 1 and 3: a repository fixture where one requirement is set `done` inside a week and another before it: the facts carry each `done_on`, and Delivered lists only the first; REQ-024 AC1; REQ-024 AC2.
- Rule 1: a fixture where a requirement is `done`, then `planned`, then `done` again: `done_on` is the date of the last change to `done`; REQ-024 AC3.
- Rules 2 and 4: a facts document without `done_on`, and one with `unknown`: the requirement is listed with ` (week it became done: unknown)`; REQ-024 AC4; REQ-024 AC6.
- Rule 5: a week in which no requirement became done prints no requirement line and its pull request lines equal the golden; REQ-024 AC5.
- Rule 6: the workflow file's checkout sets `fetch-depth: 0`; REQ-024 AC7.
- Rules 7 and 8: Proven, Needs you, At risk, Cost and the footer equal those of the same facts before the change, and the renderer's imports and file reads are those of SPEC-0011 rule 13; REQ-024 AC8.

## Proof

REQ-024 AC1 to AC3: *Delivered shows what was finished in the week.* Rules 1 and 3. REQ-024 AC4 and AC6: *nothing is hidden when the week cannot be read.* Rules 2 and 4. REQ-024 AC5: *a week with
nothing new is not padded.* Rule 5. REQ-024 AC7: *the report can read the history.* Rule 6. REQ-024 AC8: *only Delivered changes.* Rules 7 and 8. The first weekly report rendered after the implementation is
merged lists REQ-021 and REQ-022 for week W42 only, and the maintainers read it in the report issue.

## Residual

- 2026-10-20: a requirement done before the history this repository keeps reads `unknown` and stays listed in every report until it is read; none is known today (due 2026-12-31).

## Open questions

- Q-S0017-1 When `facts.py` runs in a shallow clone, does it print `unknown` for every `done_on` and say nothing, or does it also write a warning to its error output? The criteria assume the first; the workflow
  guard of rule 6 is what prevents a shallow run.
  **Ruled** (maintainers, 2026-10-20): as read. In a shallow history `facts.py` writes `unknown` for every `done_on` and nothing more; the workflow guard of rule 6 prevents it in CI.
- Q-S0017-2 Is a requirement that was added directly as `done`, in the commit that created its section, counted as becoming done in that commit? The criteria assume it is.
  **Ruled** (maintainers, 2026-10-20): as read. A requirement added directly as `done` became done in the commit that created its section.
