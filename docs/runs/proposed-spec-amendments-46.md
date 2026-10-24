# Proposed spec amendments 46 (SPEC-0022, SPEC-0011; REQ-033)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0088. The paths: `docs/specs/0022-the-weekly-product-report-also-publishes-the-sections-it-com.md`, `docs/specs/0011-inbox-and-report.md`.

1. **SPEC-0022 rule 3, the document.** `report.json` also has the key `counts` (after `sections`): an object with the keys `delivered`, `proven`, `needs_you` and `at_risk`, each the number of its section's items counted by meaning (SPEC-0026 rule 1) or the string `unknown`; `schema` is the number 3.
2. **SPEC-0022 rule 5, the fields.** The four pull-request kinds that list `entries` also have `count`, the number of their entries; `week-totals` also has `fix_verdicts_unknown` (after `fix_verdicts`), the number of the week's merged pull requests whose verdicts are unknown. A decisions group's `count` is `unknown` when it holds an `unknown` item.
3. **SPEC-0022 rule 7, the schema number.** `schema` is 3.
4. **SPEC-0011 rule 10, Needs you and At risk.** Open pull requests whose verdicts cannot be read are not skipped: the pull-request group and At risk each hold one `unknown` item that names how many, with a link to each (SPEC-0026 rule 5); the drift-audit line is printed only when its total is above 0 or unknown, or when a drift issue is open (SPEC-0026 rule 6).
