# ADR-0866: The weekly report names old and deprecated parts and never fails

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers (the owner's yes on brief #2076, 2026-11-27T19:44:05Z)
- Related: ADR-0834, ADR-0858, ADR-0860, ADR-0867, ADR-0848, ADR-0852, ADR-0016, SPEC-0076, SPEC-0011, SPEC-0054,
  SPEC-0041, REQ-083, brief #2076, brief #2045, brief #2054, plan #661
- Requirements: REQ-083

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`, `config/`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (i) asks for rule 12's weekly `parts:` line: the parts older than
`max_age_months` since their recorded release, the parts the advisory scan flags and the parts recorded deprecated,
reported and never failing. On main at 9b6ab96 neither `metrics.py` nor `personal.py` reads `docs/parts.md`. SPEC-0011's
product report has five fixed sections and a closed `At risk` list (rule 10), and SPEC-0054's advisory scan does not run
(its build (d) waits for the owner's yes).

## Decision

1. **The reader.** `scripts/agk/gates/parts.py` `report_lines(root, today)` reads the record through `sections` (build
   (d)) and the settings through `config.parts_settings`, and gives, in record order: `parts: old <part> (<runtime>)
   released <date>, older than [parts] max_age_months` for a row whose `last release` date in its `Health (date)` cell is
   over `max_age_months` calendar months before `today` (the day ignored, as `packs._over` counts); `parts: deprecated
   <part> (<runtime>) recorded <status> (read <date>)` for a row whose status is `deprecated` or `archived`; `parts:
   health not read <n> rows` for cells that start `not read` or whose release date is out of form; at most 10 such lines
   then `parts: and <k> more`; and one summary `parts: <n> recorded; old <a>; deprecated <b>; flagged unknown (no
   advisory scan)`. A cell with no release date is never old; a future date is not old.
2. **One line, never a failure.** No declared work type: `parts: not run (no stack chosen)`; a refused `[parts]` table:
   `parts: unknown (setting: parts.<key>)`; no record: `parts: not run (no parts record)`; a record with no table of the
   nine columns or not UTF-8: `parts: unknown (path class: docs/parts.md)`. `record` changes nothing here; `advisories`
   is the level a later scan will read and changes nothing while none runs.
3. **Where it shows (`Q-PI-1`).** `metrics.report` adds `parts_report_lines` right after `stale_pack_lines` and before
   `signal_lines`; `personal.report` adds the same reader after the packs lines. No exit code and no `incomplete`
   changes. SPEC-0011's product report is unchanged; a line there is a later brief with its own amendment.
4. **The scan (`Q-PI-3`).** The flagged count is `unknown (no advisory scan)` and never 0 while no saved scan result is
   read; no workflow, scanner or network read is added.
5. **The update bots (`Q-S0076-5`).** `docs/guides/reference.md` names Renovate and Dependabot; the kit writes neither.
6. **Registered.** `config/signals.toml` gains `parts-weekly` (kind `none`): the kit declares no work type, so the
   lines show only in projects' weekly issues. The `[[testing.map]]` entries of `gates/parts.py`, `metrics.py` and
   `personal.py` gain `tests/kit/test_parts_weekly.py`.

## Consequences

An old, deprecated or unread library is named in the weekly issue every week until its row changes. The kit's own weekly
issue gains only `parts: not run (no stack chosen)`. No workflow, ruleset, required check, label, `agk.mk` or
`governance_map.CHECKS` changes.

## Residual

The flagged count reads SPEC-0054's saved scan result through `sbom.findings` once its build (d) ships one, in a later
brief.
