# ADR-0121: the usage figure of a pull request in the facts and the cost lines (REQ-040 part c1, SPEC-0033 rule 8)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0113, ADR-0116, ADR-0109
- Requirements: REQ-040

Protected classes: `config/`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0033 (Approved, #189) rule 8 and the guide statement of rule 7 are the first half of build (c) of brief #182; the stalled work in At risk (rule 5, last sentence) is the second half, a pull request of its own so that each stays under the size limit. The tests were written first (`tests/kit/test_usage_figures.py`, the schema cases in `tests/kit_dev/`; on the unchanged tree most of them failed).

## Decision

1. **Facts** (rule 8): `usage` for each pull request, computed by `metrics.usage_of` from the `Report:` comments of the pull request's author (a trailing `Usage: <n> tokens` on the first line, Q-K4-282): the sum, `not-reported`, or `unknown`. `facts.json` keeps schema 1; `kit/facts-schema.json` allows the field; the goldens of the facts are regenerated.
2. **Report** (rule 8): `pull-request-cost` and `week-totals` carry the figures as amendment 58 says; the markdown prints them; a missing figure is never zero; `report.json` takes schema 5 (`kit/report-schema.json`, every golden regenerated).
3. **Guide** (rule 7): the section "Running the loop" gains the item "When the credits run out" with the statements of the rule. It names `session.py resume` and the stalled takeover of `next`, which exist; `session.py queue` of the work-management brief is not built and is not named (Q-K4-283).
4. **Rules file** (the verdict on the first head): rule 12 of `config/session-rules.md` says that the figure on a `Report:` is the usage since the previous `Report:` of the same pull request, never a running total, so the sum counts no work twice; the guide and amendment 58 say so too.
5. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-bc1.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 58 (`docs/runs/proposed-spec-amendments-58.md`) is applied to SPEC-0009, SPEC-0022 and SPEC-0024.

## Consequences

- What a pull request cost in tokens is read where the runtime shows it and never guessed; a reader of `report.json` schema 4 must accept 5.
- Facts from an older run have no `usage` and read `unknown` in the report, not `not reported`.

## Residual

None beyond SPEC-0033's.
