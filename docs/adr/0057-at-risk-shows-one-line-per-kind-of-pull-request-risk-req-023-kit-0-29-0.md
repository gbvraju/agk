# ADR-0057: At risk shows one line per kind of pull request risk (REQ-023, SPEC-0016), kit 0.29.0

- Status: Accepted
- Date: 2026-10-20
- Deciders: maintainers
- Related: ADR-0053, ADR-0054, ADR-0051
- Requirements: REQ-023

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

PR 6 of the K5 early scope (ADR-0053). REQ-023 was taken in by intake (ADR-0054) and SPEC-0016 was Approved with its open question ruled (inline `[#12](url)` is "each number its own link"). On the live
report 88, 33 of the 37 At risk lines were one kind (`docs/runs/short-report-live-1.md`). This ADR builds the grouped form tests first: the tests for AC1 to AC8 were written and run on unchanged `main`
before any code (6 failed, 7 passed, the 7 being the guards that must keep passing; the output is in the pull request body).

## Decision

1. **The four kinds** (SPEC-0016 rule 1): open too long, sent back, merged with no verdict, merged before its last commit was cleared. The overdue-residual lines and the drift line are never grouped.
2. **One line per kind of two or more** (rules 3 and 4): `PRs [#12](url) (41 days), [#15](url) and [#20](url) have been open`, `... were sent back`, `... were merged with no verdict`, `... were merged before
   their last commit was cleared`; the numbers ascending, each its own link, never a range, no title, no trailing link. The bracketed value is the one the single line prints (days open, times sent back).
3. **One pull request stays as today** (rule 2): the same line, with its title and its trailing link.
4. **Where a grouped line stands** (rule 6): at the place of the line of its lowest-numbered pull request, so a section with no kind of two or more is byte-identical to the one before, and the order is still
   residuals, open too long, sent back, the drift line, then the merged pull requests.
5. **Nothing else changes** (rules 5, 7, 8 and 9): the set of numbers named in At risk is unchanged; Delivered, Proven, Needs you, Cost, the footer and the inbox are byte-identical; the renderer reads only the
   facts file and its imports are unchanged; unknown pull requests keep today's unknown line. The change is in `scripts/agk/product_report.py` (`at_risk`, `by_kind`, `pull_list`), with no new field in the facts.
6. **Tests** (`tests/kit/test_product_report_at_risk.py`, new, and `tests/kit/test_product_report.py`): the grouped lines of each kind, the single line unchanged, 33 pull requests named, the order, the
   guards. Existing tests that pinned the single-line forms of several pull requests of one kind now pin the grouped line (`test_ac5_needs_you_at_risk_proven_and_the_footer_are_not_changed`,
   the three `merged before cleared` tests, `test_every_line_in_a_section_links_to_evidence`). The four report goldens that held several pull requests of one kind change in At risk only (`kinds`,
   `dirty-unknown`, `facts-pr-states`, `busy`); the diff is in the pull request body.
7. **Kit 0.29.0**: the manifest `kit_version`, the hashes of `scripts/agk/product_report.py`, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). No file is added to or
   removed from the manifest.
8. **Docs**: one sentence in the product-owner guide says what a grouped At risk line looks like.

## Consequences

- A long At risk list is a few lines and every pull request is still named; the title is one click away on the number.
- The pilot gets this on its next `agk upgrade`, after its week W44 is scored on 2026-11-02.

## Questions

none

## Residual

- 2026-10-20: a grouped line no longer shows the title of a pull request (SPEC-0016 residual, due 2026-12-31).
