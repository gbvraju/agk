# ADR-0858: A [parts] table, and a needs catalogue checked inside the playbooks step

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2068, 2026-11-27T19:43:32Z)
- Related: ADR-0834, ADR-0838, ADR-0839, ADR-0786, ADR-0527, ADR-0824, SPEC-0076, SPEC-0077, REQ-083, brief #2068, plan #661
- Requirements: REQ-083

Protected classes: `scripts/agk/`, `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (a) asks for the `[parts]` table of rule 9, the needs catalogue of rule 4
and the catalogue check of rule 5 inside the existing `playbooks` step. On main at 975eae66 none of it existed: `[parts]`
was a table the kit did not read, and `packs.KIT["parts"]` was `None`, so no layer of the `parts` kind was read. The forms
to copy are SPEC-0077 build (a) (ADR-0838: `config.packs_settings`, `doctor.packs_settings_result`, a check that
`check_playbooks.findings` adds) and the one reading order of ADR-0839 (`packs.files`).

## Decision

1. **The needs catalogue.** A kit file `config/parts/needs.toml` (`format = 1`), one `[[needs]]` per need with `id`
   (`^[a-z][a-z0-9-]*$`), `text` (one plain line) and `signals` (a non-empty list of plain words), holding rule 4's 28
   ids. It names no library and no version. `kit/manifest.json` lists it in `verbatim`.
2. **The check.** `scripts/agk/check_parts_catalogue.py` (standard library and `common.py` only; no network, no model)
   gives one line per problem, `rule 4|5: <path class>: <what> (key: <key>)`, never a value: a file that is not TOML,
   `format` not 1, a missing or unknown key, a wrong type (a `bool` is never a word or a number), a need id used twice
   across the needs files of every layer, a stack catalogue whose file name is no stack of `config/stack-signals.toml`, a
   row whose `need` no needs id names, a `pick` other than `recommended` or `alternative` (`Q-PA-1`), more than one
   `recommended` or more than two `alternative` rows for a need in one file, a name used twice for a need, a `licence`
   that is not one SPDX id, a `source` not `<URL> (accessed YYYY-MM-DD)` (the pattern of `playbook_format.GATE_SOURCE`,
   held equal by a test), a `reviewed` not `YYYY-MM-DD`, and any `version` key. A pack's needs row may also carry the
   provenance keys `source` and `basis` that SPEC-0077 rule 3 asks of a pack's entry.
3. **The reading order.** `packs.KIT["parts"]` is `config/parts`: the kit's folder (through `kit_root.kit_file`) as
   `agk-core`, then each pack in use's `parts/` files, then the project's own folder, read once in the installed layout
   (`Q-2032-1`, `Q-PA-2`). `check_playbooks.parts_catalogue` resolves the files and the stack names and passes them, so
   the script imports no other kit module (`Q-PA-4`); a refused `[packs]` table or plugin root adds no line there,
   since the pack check and the declaration already name that setting. `governance_map.CHECKS` and `agk.mk` are
   unchanged: a problem is one more `FAIL playbooks:` line.
4. **The table.** `config.parts_settings` reads `record` (`required` or `optional`, `optional`), `max_age_months` (a
   whole number from 1 to 60 by `STALE_MONTHS`, 12) and `advisories` (`critical-high`, `critical`, `any`,
   `critical-high`). Each refusal is `the [parts] table is refused (setting: parts.<key>)`; an unknown key is named; a
   table that is not a table or an unreadable file is `parts`. `parts` is in `config.TABLE_KEYS`, so in `KIT_SETTINGS`
   and `misplaced_settings`.
5. **Doctor and uninstall.** `doctor.py` gains `parts-settings` (`ok (record <r>, max age <n> months, advisories <a>)`
   or the refusal line). `uninstall.py` removes `[parts]` through `KIT_SETTINGS` with no code change; `needs.toml` goes
   as a `verbatim` file when unchanged, and a project's own file under `config/parts/` stays as any project file does.

## Consequences

Every needs and stack catalogue row of the kit, a pack in use and the project is checked for its form, licence form,
dated source and review date on every governance run, in CI and in `prepush.py`, before any reader uses it. With no
`[parts]` table and no stack catalogue every result is today's but one more `doctor.py` line.

## Residual

`record`, `max_age_months` and `advisories` are read, refused and printed only: the `parts` step and the hold that act on
`record` are build (d), the proposal and the health research that read the other two are build (c). The `node` and
`python-pyproject` catalogues are build (b), which also settles the file name of a project's override in the installed
layout (`Q-PA-2`). A domain pack's `[[parts]]` section stays refused by `check_domains.SECTIONS` until a build names it
(`Q-PA-3`). A licence is checked for its form only; `config/licences.toml` is read at choice time (build (c)).
