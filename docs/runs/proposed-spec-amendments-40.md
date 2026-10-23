# Proposed spec amendments 40 (SPEC-0022 rules 3, 5 and 7; SPEC-0024 Residual; REQ-031)

Date: 2026-10-23 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0078. The paths: `docs/specs/0022-the-weekly-product-report-also-publishes-the-sections-it-com.md`, `docs/specs/0024-the-report-s-cost-totals-carry-the-number-of-the-week-s-merg.md`.

1. **SPEC-0022 rule 3, the document.** `schema` is the number 2 (SPEC-0024 rule 4).
2. **SPEC-0022 rule 5, the fields of `week-totals`.** `hours_unknown` follows `hours`: a number, how many of the week's merged pull requests have the hours `unknown` (SPEC-0024 rules 1 and 2).
3. **SPEC-0022 rule 7, versioned.** `schema` is 2; a kind or a field that is not in rule 5 does not exist in schema 2.
4. **SPEC-0024 Residual.** The brownfield adoption line leaves the spec's Residual for the register `docs/runs/residuals.md`, as a K5 candidate (the maintainers' verdict on the intake pull request).
