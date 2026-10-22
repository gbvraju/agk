# ADR-0072: the report is published as data in report.json (REQ-029 part R3, SPEC-0022), kit 0.39.0

- Status: Accepted
- Date: 2026-10-22
- Deciders: maintainers
- Related: ADR-0071, ADR-0070, ADR-0069, ADR-0063
- Requirements: REQ-029

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

Parts R1 (ADR-0070) and R2 (ADR-0071) made every section of the weekly report data and rendered the markdown and the inbox from it, with the printed text unchanged. This part R3 publishes that data:
`report.json` beside `facts.json` in the same artifact, so any reader can show the same report without reimplementing its rules (SPEC-0022 rules 1, 3 to 5, 7 to 9). The tests were written first and run on
unchanged `main` (76 failed, 11 passed; the output is in the pull request body).

## Decision

1. **The option** (SPEC-0022 rule 1): `product_report.py --facts FILE --json OUT` prints the markdown as before and writes `OUT`, the structure the markdown is rendered from, as JSON: two-space indent, UTF-8,
   keys in the order of the table `ITEM_KINDS`, one final newline. `--json` is a usage error with `--inbox` and `--print-action`. An unwritable path is a refusal naming the option, not the path. Without
   `--json` the script writes no file.
2. **The schema** (rule 7): `kit/report-schema.json`, hand-written, one line per kind, kit-only like `kit/facts-schema.json` (SPEC-0022 said installed; amendment 36 corrects it). A kit-only test validates
   every golden `report.json`, fails on an extra key, an extra kind, an extra field, a missing field, a null, a float and a link target outside the list, and ties the schema to `ITEM_KINDS` (the same kinds
   and the same fields).
3. **The goldens**: one `report.json` per golden facts (14), written by `AGK_WRITE_GOLDENS=1` with the pull request mask of the markdown goldens, and compared byte for byte; two runs give the same bytes.
4. **The workflow** (rule 9): the report step writes `report.json` in the same run of `product_report.py` as the markdown, before the issue; the check of the week label also fails the run, writing nothing,
   when `report.json` is missing or empty. The upload step names the two paths (`facts.json`, `report.json`) in the artifact `agk-facts-<week>`, whose name, retention, pin, `overwrite`, order after the issue
   and `permissions` are unchanged. The security guide's line for the workflow names the second file.
5. **Amendment 36** (`docs/runs/proposed-spec-amendments-36.md`) is applied to SPEC-0011 rules 1, 13, 14 and 18, SPEC-0019 rules 1, 3, 4 and 8, and SPEC-0022 rule 7.
6. **Tests, first**: `tests/kit/test_report_json.py` (new, installed), `tests/kit_dev/test_report_wiring.py` (new, kit-only), and `tests/kit/test_product_report_facts_artifact.py` (the path assertions become two
   paths, and the tests of the second file are added).
7. **Kit 0.39.0**: the manifest `kit_version`, the hashes of `product_report.py` and of the workflow, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). No file is added to
   or removed from the manifest (the schema is kit-only).
8. **REQ-029** is `done` by the final commit of this pull request, on the maintainers' word.

## Consequences

- For every installed project a reader of the weekly artifact gets the report as data from the first scheduled run after the upgrade, and the markdown it shows cannot differ from it.
- A new kind or field is a new schema number and an amendment; a reader can rely on the list.
- The per-week values and the requirement rows are a later intake (SPEC-0022 Residual, due 2026-12-31).

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-224 | SPEC-0022 rule 9 says the run fails when `report.json` is missing or empty; where? | In the report step, before the issue: the existing check of the week label also fails the run, writing nothing, when `report.json` is missing or empty (the same message, so the three `exit 1` of SPEC-0019 stay three); the upload step's `if-no-files-found: error` covers the rest. Proposed for ruling. |
| Q-K4-225 | SPEC-0022 rule 7 says `kit/report-schema.json` is installed verbatim, like the facts schema, which is kit-only | Kit-only, like `kit/facts-schema.json` (it is a test aid, not a script an installed project runs); amendment 36 corrects the rule. Proposed for ruling. |

## Residual

- 2026-10-22: the first scheduled run after this build is merged must show both files in the artifact; the maintainers download it and compare `report.json` with the issue of that week (SPEC-0022 Proof) (due 2026-11-09).
