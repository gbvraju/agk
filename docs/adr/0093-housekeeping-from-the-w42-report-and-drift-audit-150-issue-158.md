# ADR-0093: housekeeping from the W42 report and drift audit #150 (issue #158)

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0012, SPEC-0004
- Requirements: REQ-009

Protected classes: `tests/kit/`

## Context

The drift audit of 2026-10-24 (issue #150) found two things: D4, the register line "workflow token label creation (verify on first live run)" of `docs/adr/0012-drift-audit.md`, overdue since 2026-10-22, and D7, a
marker in `tests/kit/test_review_report.py:109` that names `REQ-001 AC9`, which REQ-001 does not have. The brief in issue #158 asks for both to be settled in one pull request.

## Decision

1. **D4.** The register line moves from `## Open` to the `## Closed` table of `docs/runs/residuals.md` with its evidence: the live product-report run recorded in `docs/runs/product-report-live-1.md` (the label did not
   exist, the workflow created it, issue #68, 2026-10-17, `github-actions[bot]`), and the drift audit's own step, which is the same `gh label create ... || true` and which filed #150 with `agk-drift-audit` on 2026-10-24. It
   is the same item as the finding, so the finding is closed by the same row.
2. **D7.** The text `REQ-001 AC9` at `tests/kit/test_review_report.py:109` is not a marker: it is the fixture of the case "an invented requirement criterion", which the report validator must refuse. It proves no
   criterion of REQ-001, and a criterion that exists would not be invented. The test keeps its case and the string is built in two parts (`"REQ-001 AC" + "9"`), so the marker scan no longer reads fixture text as a marker.
3. `tests/kit/` is a protected class, so this ADR names it. No kit file changes, so there is no bump.

## Consequences

- `python3 scripts/agk/drift_audit.py --today 2026-10-24` on the tree after this change prints `findings=0`; the next audit and report should show neither finding.

## Residual

None.
