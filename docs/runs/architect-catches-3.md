# Architect catches 3 (a project build that rebuilds what already exists, brief #2065)

Date: 2026-11-27 (from `date -u`). The third list, in the form of `docs/runs/architect-catches-2.md`: each catch with its kind and who caught it, so that the kit's review checklist grows from
evidence (SPEC-0023 rule 5). Row 1 is cited by ADR-0857 for the widened item 10 of `config/review-checklist.md`; no question is added and no kind.

## How the rows were checked

The row was read by GET on the project's pull request named in brief #2065 (ADR-0025 decision 6's project; its pull requests are not in this repository, so "project PR #n" is a pull request of that
project). Nothing is added that the record does not support.

Kinds (fixed list): `wrong-assumption`, `false-declaration`, `test-proves-less`, `stale-claim`, `fragile-code`, `security`, `vendored-file-change`, `scope-rule`, `process-order`, `kit-defect`, `cost`,
`late-discovery` (a fact found after intake that should have been asked at intake).

## The catches

| # | Date | Where | Kind (architect-assigned) | Caught by | What | Outcome | Agrees |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-22 | project PR #27 | `kit-defect` | the reviewer | The build rebuilt the report's logic in a second language: "duplicates the report's logic in a second language. That is a kit gap" (the reviewer's comment, read by GET). Caught by hand at review, after the build was planned. | rejected | yes |
