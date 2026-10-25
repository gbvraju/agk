# ADR-0128: the Flow section, the stalled work and the corrections in the report, schema 6 (REQ-041 build (d), SPEC-0033 build (c2), SPEC-0032 build (e2))

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0121, ADR-0117, ADR-0124
- Requirements: REQ-041, REQ-040, REQ-039

Protected classes: `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Three Approved items add to the weekly report: rule 10 of SPEC-0034 (the `Flow` section), the last sentence of rule 5 of SPEC-0033 (a pull request stalled on its builder is an At risk line; build (c2) of #182) and rule 11 of SPEC-0032
(the conductor's corrections next to its verdicts; build (e2) of #179). The conductor assigned the three to this one build so that `report.json` changes its schema once, from 5 to 6 (#204, #176). ADR-0117 opened K5 for the
conductor plan, which covers the residual of rule 10. ADR-0128 and amendment 66 were reserved on #176. The tests were written first (`tests/kit/test_facts_flow.py`, `tests/kit/test_product_report_flow.py`); on the unchanged
scripts 16 of the 17 failed.

## Decision

1. **Facts** (amendment 66, item 1). Each pull-request record gains `brief`, `flow`, `conflicts`, `renumbers`, `corrections` and `stalled`; the document gains the section `flow`. They are read from the saved copies the facts already
   read (the pull requests, their comments and commits) and from two more: the `agk-brief` issues and the comments of each. `facts.json` keeps schema 1; the new fields are optional in `kit/facts-schema.json`, so a document from an
   older run is still valid and its figures read `unknown` in the report.
2. **Report** (items 2 and 3). `report.json` takes schema 6: the section `flow` with the item `flow-figures`, the At risk kinds `pull-requests-stalled`, `briefs-idle` and `requirements-without-brief`, and `corrections` in
   `week-totals`. The markdown prints a sixth heading `## Flow`. `kit/report-schema.json` requires 6 and every golden is regenerated. A reader of schema 5 must accept 6, as it did for 5 (the portal reader of schema 6 is the
   condition for the merge, #204).
3. **Readings taken where the specs leave a point open** (questions in the pull request, the most conservative reading each): the medians are over the pull requests merged in the week; the take that counts for a pull request is the
   latest `taken:` comment of its brief before the pull request was opened; a conflict is a comment `conflict needs a person:` on a pull request; a renumber is a commit of a pull request whose first line contains `renumber`;
   a retake is a `taken:` comment that says `retakes`; an open brief has "no pull request" when no pull request in the facts names it by `Brief: #n`, and is idle when it is older than 7 days; a requirement has "no open brief" when it
   is not `done` and no open brief's `Advances:` names it; a pull request is stalled when it is a draft or has the label `agk:fix`, `agk:conflict` or `agk:ci-red`, its head is not cleared, and its head commit, its creation and its
   comments are all older than `stall_hours` as of the end of the facts day.
4. Flow mode (SPEC-0028, SPEC-0031): fragment `changelog.d/req-041-d-flow-report.md`; no version bump; `CHANGELOG.md` and `kit/hashes.json` as on `main`. The guides name the sixth section.

## Consequences

- The team sees where the time goes from files and saved GitHub copies, with no new network call in the report.
- The facts run reads one more list (the `agk-brief` issues) and the comments of each brief.

## Residual

- 2026-10-25: the portal reader of schema 6 does not exist yet; the pull request merges only after it (due 2026-12-31).
- 2026-10-25: `renumbers` is read from the first line of a commit message, so a renumber that is not named there is not counted (due 2026-12-31).
