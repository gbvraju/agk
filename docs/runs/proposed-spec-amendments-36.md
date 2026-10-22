# Proposed spec amendments 36 (SPEC-0011 rules 1, 13, 14, 18; SPEC-0019 rules 1, 3, 4, 8; SPEC-0022 rule 7; REQ-029 part R3)

Date: 2026-10-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0072. The paths: `docs/specs/0011-inbox-and-report.md`,
`docs/specs/0019-the-weekly-product-report-also-publishes-the-facts-document.md`, `docs/specs/0022-the-weekly-product-report-also-publishes-the-sections-it-com.md`.

1. **SPEC-0011 rule 1.** `product_report.py` takes `--json FILE`: it prints the markdown as before and also writes `report.json`; it is refused with `--inbox` and `--print-action`.
2. **SPEC-0011 rule 13.** A run writes no file; with `--json` it writes that one file and nothing else.
3. **SPEC-0011 rule 14.** Determinism holds for `report.json` as for the markdown.
4. **SPEC-0011 rule 18.** The tests of SPEC-0022 are named: `test_report_structure.py` and `test_report_json.py` (installed), `test_report_wiring.py` (kit-only).
5. **SPEC-0019 rules 1, 3, 4, 8.** The artifact `agk-facts-<week>` holds `facts.json` and `report.json`; the upload names the two paths, with no pattern; the run fails if either is missing or empty and the issue
   already written stays; `product_report.py` and the report step change by the option only.
6. **SPEC-0022 rule 7.** `kit/report-schema.json` is kit-only (not installed), like `kit/facts-schema.json`, not installed verbatim as the rule said; its test is kit-only.
