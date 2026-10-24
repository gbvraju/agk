# ADR-0088: the report states its counts (REQ-033, SPEC-0026), kit 0.50.0

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0087, ADR-0078
- Requirements: REQ-033

Protected classes: `.claude-plugin/`, `agk.toml`, `docs/requirements.md`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0026 (Approved, #149) lets a reader show the report's totals without counting and stops the report from leaving out silently what the facts could not read. The tests were written first
(`tests/kit/test_report_counts.py`; on unchanged `main`: 15 failed, 8 passed).

## Decision

1. `report.json` gains `counts` (`delivered`, `proven`, `needs_you`, `at_risk`), counted by meaning and `unknown` for a section that holds an `unknown` item (SPEC-0026 rule 1); the four pull-request kinds that
   list `entries` gain `count`; `week-totals` gains `fix_verdicts_unknown`; `schema` is 3 (`REPORT_SCHEMA`, `kit/report-schema.json`, hand-edited). The list of kinds is unchanged.
2. Open pull requests whose verdicts are unknown become one `unknown` item in the pull-request group of Needs you and one in At risk, naming how many in `what`, with a link to each; the markdown prints the
   numbers as links. A group that holds an `unknown` item has the count `unknown` (the heading prints `(unknown)`).
3. The drift-audit item is left out of At risk when its total is 0 and no drift issue is open; an unreadable total or unreadable issues keep it.
4. Amendment 46 (`docs/runs/proposed-spec-amendments-46.md`) is applied to SPEC-0022 and SPEC-0011. The goldens of `report.json` and of the markdown and the inbox are regenerated; the markdown goldens change only
   where SPEC-0026 rules 5 and 6 say. `docs/requirements.md` sets REQ-033 `done`.
5. **Kit 0.50.0**: the manifest `kit_version`, the hashes, the plugin version and `version` in this repository's `agk.toml`.

## Consequences

- A reader of `report.json` shows totals as they are; a project that reads `schema` 2 sees the number change.
- A week with open pull requests whose verdicts cannot be read prints one more line in two places, and a quiet repository with no drift findings prints `nothing this week` under At risk.

## Residual

None.
