# Proposed spec amendments 30 (SPEC-0011 rule 15)

Date: 2026-10-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0063. SPEC-0019 rule 9 names it. The path:
`docs/specs/0011-inbox-and-report.md`.

1. **SPEC-0011 rule 15, the steps of the workflow.** The rule lists the steps: run `facts.py` into a file, run `product_report.py` on it, create or update the issue. A fourth is added: after the issue is
   written, one step uploads that same facts file as the workflow artifact `agk-facts-<week>` (SPEC-0019), with no new permission. The `permissions` of the rule are unchanged, and so is every other
   rule of SPEC-0011 (rule 17 still says that `metrics.yml`, `drift-audit.yml` and `governance.yml` are unchanged). The workflow's header comment, which says the workflow's only writes are the issue and
   the label, now names the artifact.
