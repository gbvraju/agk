# Proposed spec amendments 19 (SPEC-0006; found while building the report workflow, SPEC-0011 (b))

Date: 2026-10-17 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). The path:
`docs/specs/0006-doctor.md`.

**Applied by ADR-0030** (2026-10-17), on the maintainers' ruling of `Q-K4-52` (extend `drift-workflow-state`, no new check id).

## SPEC-0006 (`docs/specs/0006-doctor.md`)

1. **Rule 5, the row `drift-workflow-state`.** "the workflow's `state` is not `active` on GitHub" becomes "the `state` of the drift-audit
   workflow, or of the product-report workflow where its file is installed, is not `active` on GitHub".
2. **Rule 6, the reads.** "The four reads" becomes "The reads (four, and a fifth where the product report is installed)": the fifth is
   `gh api repos/{o}/{r}/actions/workflows/product-report.yml` (`state`), made only where `.github/workflows/product-report.yml` exists
   in ROOT. A file the repository removed is reported by `vendored-missing`, not read here.
3. **Rule 2.** "the four paths of rule 6" becomes "the paths of rule 6". The doctor still calls `gh` only as `gh api` with `GET`.
