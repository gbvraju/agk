# ADR-0078: the cost totals carry hours_unknown and the report schema is 2 (REQ-031, SPEC-0024), kit 0.43.0

- Status: Accepted
- Date: 2026-10-23
- Deciders: maintainers
- Related: ADR-0077, ADR-0070, ADR-0072
- Requirements: REQ-031

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

SPEC-0024 (Approved, #128) gives the cost totals item of `report.json` a count of the week's merged pull requests whose hours are not known, so a reader can say how many lack them without counting. The
build is one field, the schema number and the goldens. The tests were written first and run on unchanged `main` (10 failed, 1 passed; the output is in the pull request body).

## Decision

1. **The field**: `scripts/agk/product_report.py` adds `hours_unknown` to the kind `week-totals`, after `hours`: the number of merged pull requests of the week whose hours are `unknown` (the created or merged
   time is missing or cannot be read), over the same set as `merged`, in a busy week too; present and 0 when every hours is known. The markdown and the inbox output do not print it and are unchanged.
2. **The number**: `REPORT_SCHEMA` is 2; `facts.json` keeps its own number 1.
3. **The schema file**: `kit/report-schema.json` requires the number 2 and `hours_unknown` (an integer) on the totals item.
4. **Amendment 40** (`docs/runs/proposed-spec-amendments-40.md`) is applied to SPEC-0022 rules 3, 5 and 7; it also moves the brownfield adoption line from SPEC-0024's Residual to `docs/runs/residuals.md`
   (the maintainers' instruction in the verdict on #128).
5. **Tests, first** (`tests/kit/test_report_hours_unknown.py`, new, installed; `tests/kit_dev/test_report_hours_schema.py`, new, kit-only): the count with missing and unreadable times, 0 when all are
   known, a busy week, the markdown without the field, the numbers 2 and 1; the schema file, the goldens and the mutations. Two existing assertions of the number 1 of `report.json` become 2; the fifteen
   `report.json` goldens are regenerated (the markdown and inbox goldens are unchanged).
6. **Kit 0.43.0**: the manifest `kit_version`, the hashes, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). L3b takes 0.44.0.

## Consequences

- A reader of `report.json` sees the number 2 and the new field; a reader of schema 1 must update. Nothing printed changes.
- The report goldens carry the number and the field.

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-229 | SPEC-0024 rule 4 says `hours_unknown` is "an integer, at least 0"; the kit's schema validator (SPEC-0009 rule 19) has no `minimum` keyword. How is "at least 0" held? | The schema file says `{"type": "integer"}`, like `merged`, and a test asserts on every golden that the value is between 0 and `merged`; the validator's keyword list is not widened. Ruled as read in the #129 verdict: the value cannot be negative by construction (a count of unknown hours) and the kit_dev test pins `0 <= hours_unknown <= merged` on every golden. |

## Residual

None.
