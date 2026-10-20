# SPEC-0017: Delivered lists only the requirements that became done in the week

- Status: Draft
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

1. **The date a requirement became done.** For each requirement, `facts.py` reads the first-parent history of the default branch for the commits that changed the requirement's `Status:` line in
   `docs/requirements.md`, and takes the latest one whose change set the status to `done` (a requirement added already `done` counts as that commit). The field is `done_on` on the requirement's row, the
   commit's committer date in UTC, `YYYY-MM-DD`. It is `unknown` when no such commit is found, the history is shallow or git cannot read it. It is computed from the repository's history only: no clock, no
   network, no pull request lookup.
2. **The schema.** `schema` stays 1. `done_on` is optional: a facts document without it is valid, and the renderer reads a missing `done_on` as `unknown` (no migration of old facts).
3. **Delivered lists the week's requirements.** A requirement whose `status` is `done` and whose `done_on` is a date inside the report's week (the same Monday and Sunday, in UTC, as the report's opening
   line) is listed with the line printed before this change. One whose `done_on` is a date outside the week is not listed.
4. **Unknown stays visible.** A requirement whose `status` is `done` and whose `done_on` is `unknown` or missing is listed with its usual line followed by ` (week it became done: unknown)`, before the link. It
   is never dropped.
5. **A week with nothing newly done.** Delivered prints no requirement line. Its pull request lines (a quiet week) or the single busy-week line (SPEC-0015) are unchanged. A requirement whose `status` is not
   `done` is not listed, as before.
6. **The workflow reads enough history.** The `product-report` workflow checks out the full history (`fetch-depth: 0`). A test reads the workflow file and fails if its checkout does not set `fetch-depth: 0`,
   so a shallow clone cannot turn every done requirement into `unknown`. (`facts.py` still writes `unknown` for a shallow history; it never guesses a date.)
7. **Nothing else changes.** Proven, Needs you, At risk, Cost, the footer, the inbox output and the metrics issue are byte-identical to the report of the same facts before this change. The quiet-week and
   busy-week goldens change only in Delivered; the implementation pull request shows the diff of each.
8. **The renderer stays pure.** `product_report.py` reads the facts file and no other file, and its imports are unchanged (SPEC-0011 rule 13). The week of a requirement is decided from `done_on` alone.
9. **Unknown is not a date.** When the facts mark `requirements` `"unknown"`, Delivered prints today's unknown line.

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
