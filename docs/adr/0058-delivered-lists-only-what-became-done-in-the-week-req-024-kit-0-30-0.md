# ADR-0058: Delivered lists only the requirements that became done in the week (REQ-024, SPEC-0017), kit 0.30.0

- Status: Accepted
- Date: 2026-10-20
- Deciders: maintainers
- Related: ADR-0053, ADR-0055, ADR-0057, ADR-0036
- Requirements: REQ-024

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

PR 7 of the K5 early scope (ADR-0053). REQ-024 was taken in by intake (ADR-0055) and SPEC-0017 was Approved with its two open questions ruled (a shallow history gives `unknown` and nothing more; a requirement
added as `done` became done in the commit that created its section). Delivered listed every requirement that was ever done, so REQ-021 and REQ-022, done on 2026-10-20, would appear in every later report
(`docs/runs/short-report-live-1.md`). This ADR builds the weekly form tests first: the tests for AC1 to AC8 were written and run on unchanged `main` before any code (16 failed, 8 passed, the 8 being the
guards that must keep passing; the output is in the pull request body).

## Decision

1. **The date** (SPEC-0017 rule 1): `facts.py` gains `done_dates`, which walks the first-parent history of the checked-out branch for the commits that touched `docs/requirements.md`, oldest first, parses each
   version with `parse_requirements`, and dates a requirement by the latest commit at which it is `done` and was not `done` in the commit before. The date is the committer date converted to UTC,
   `YYYY-MM-DD`. No clock, no network, no pull request lookup; a squash merge is one commit, so it is the merge date.
2. **The field** (rules 1 and 2): each `requirements` row gains `done_on`: the date for a `done` requirement, `"unknown"` for a `done` one whose date cannot be found (no commit, or a shallow history,
   which is detected with `git rev-parse --is-shallow-repository` and never guessed), and `null` when the status is not `done` (there is no date to give, so it is not an unknown; Q-K4-213). `schema` stays 1:
   the field is optional for a reader, a facts document without it is valid and reads as `unknown`, as `path`, `proof_reason` and `kit_version` were added.
3. **Delivered** (rules 3 to 5): a `done` requirement is listed when `done_on` is a date in the report's week (Monday to Sunday, UTC, the dates of the opening line), with the usual line; when `done_on` is
   a date outside the week it is not listed; when it is `"unknown"`, missing or not a date, it is listed with the usual line followed by ` (week it became done: unknown)` before the link, never dropped. A
   week in which nothing became done lists no requirement; the pull request lines (SPEC-0015's single busy-week line included) are unchanged. The change is one condition and one suffix in `delivered`.
4. **The workflow** (rule 6): `product-report.yml` already checks out the full history (`fetch-depth: 0`); a test now reads the checkout step and fails if it does not set it. `facts.py` itself returns
   `unknown` for a shallow history.
5. **Nothing else changes** (rules 7 to 9): Proven, Needs you, At risk, Cost, the footer and the inbox are byte-identical; the renderer reads only the facts file and its imports are unchanged; unknown
   `requirements` keep today's unknown line. The report goldens change in Delivered only (the diff is in the pull request body); the facts goldens gain the `done_on` line of each requirement.
6. **Amendment 27** (`docs/runs/proposed-spec-amendments-27.md`) is applied to SPEC-0009 rule 8, which lists the fields of a requirements row (Q-K4-213); `kit/facts-schema.json` gets the optional property `done_on` (SPEC-0009 rule 19).
7. **Tests** (`tests/kit/test_facts_done_on.py` and `tests/kit/test_product_report_delivered.py`, new): the date from a history of commits with chosen committer dates (done, planned and done again, UTC,
   added as done, a merge commit, a shallow clone, an uncommitted edit); the week boundaries; the unknown note; no requirement line in a week with nothing new; the workflow checkout; the guards.
8. **Kit 0.30.0**: the manifest `kit_version`, the hashes of `scripts/agk/facts.py` and `scripts/agk/product_report.py`, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7).
   No file is added to or removed from the manifest.
9. **Docs**: one paragraph in the product-owner guide says what Delivered lists and what the note means.

## Consequences

- A report lists the requirements done in its week, so REQ-021 and REQ-022 are in the report of week W42 only; the first report after this merges shows it.
- The repository's history is read on every facts run: one `git show` for each commit that touched `docs/requirements.md` on the first-parent history (15 today, 0.15 s).
- The pilot gets this on its next `agk upgrade`, after its week W44 is scored on 2026-11-02.

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-213 | SPEC-0017 names `done_on` but not the spec that lists a requirements row (SPEC-0009 rule 8), and says it is `unknown` when no commit is found, which would make every `planned` requirement `unknown` | `null` for a requirement that is not `done` (a `done` one with no commit stays `unknown`); SPEC-0009 rule 8 gets one clause by amendment 27. Proposed for ruling. |

## Residual

- 2026-10-20: a requirement done before the history this repository keeps reads `unknown` and stays listed in every report until it is read (SPEC-0017 residual, due 2026-12-31).
