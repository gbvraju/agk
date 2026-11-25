# ADR-0804: Domain packs, their check inside the playbooks step, two seed packs and the [domain] table

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0074, SPEC-0073, SPEC-0072, SPEC-0059, SPEC-0048, SPEC-0038, ADR-0794, ADR-0801, ADR-0259, ADR-0527, brief #1935, brief #1933, plan #661
- Requirements: REQ-081

Protected classes: `scripts/agk/`, `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

SPEC-0074 (Approved) rule 16 build (a) is the first build of domain packs: rules 2, 3 and 12 and the layout part of
rule 15. Before it, on the default branch at 95324e7, `config/domains/` did not exist, no script checked a pack and
`config.TABLE_KEYS` had no `domain` row. The owner named the two seed packs on the brief (`Maintainer answer: Q-D74A-1
payments and field-service`).

## Decision

1. A domain pack is `config/domains/<slug>.toml` in rule 2's format: `format = 1`, `domain` (the file's name), `title`
   (one plain line) and `as_of` (a date); `[[terms]]` required; `[[actors]]`, `[[entities]]`, `[[workflows]]`,
   `[[kpis]]`, `[[regulations]]`, `[[constraints]]`, `[[discovery]]`, `[[references]]`, `[[acceptance]]`,
   `[[data_shapes]]` and `[[gates]]` optional, with the keys rule 2 names. A gate may name its `regulation`, and a
   `judgement` gate must name a regulation marked `critical`.
2. `scripts/agk/check_domains.py` checks every pack, the project's first by name and, in a clean layout, the plugin's,
   and fails each problem of rule 2 as `rule 2: config/domains/<file>: <what> (key: <key>)`, never a value. A
   `[[discovery]]` id may not reuse a topic id, a fixed id or any `[[discovery]]` id of the playbooks, grill ids
   included. A line that `guard.scan_text` flags with the shipped patterns fails naming the class and the key. An
   `as_of` older than `[domain] stale_months` is a `warn domains:` line and never fails. It reads files only and
   imports `common.py`, `guard.py` and `playbook_format.py`, all standard library (no network, no model).
3. `check_playbooks.findings` adds the packs' problems when it checks every playbook, so they print as
   `FAIL playbooks:` lines in the existing `playbooks` step; a call for named playbooks alone (a derive, a gate run)
   reads no pack. `governance_map.CHECKS`, `agk.mk` and every workflow are unchanged (`Q-S0074-8`).
4. Two seed packs ship: `payments` (regulated: card data, payment services and anti-money-laundering, each regulation
   cited by its number, title and public page) and `field-service` (operational, no regulation). Every constraint and
   gate carries `basis = "expected"`; the citations are marked `(verify)` because the building session could not open
   the public pages. They join `kit/manifest.json` `verbatim` with `check_domains.py`; `kit/hashes.json` waits for the
   release (session rule 14). A project's own pack is never in the manifest.
5. `config.domain_settings(root)` reads one optional `[domain]` table in `steward_settings`'s form: `packs` (a list of
   pack names, each found and passing the check; `[]`) and `stale_months` (1 to 60; 12). A `bool` is never a number;
   an unknown key, a wrong type or a bad name is `the [domain] table is refused (setting: domain.<key>)`. The row in
   `config.TABLE_KEYS` lets `misplaced_settings` report a misplaced key and `uninstall.py` remove the table through
   `KIT_SETTINGS`. `doctor.py` prints `domain-settings`: the packs and the stale months, or the refusal (`Q-D74A-2`).
   The kit's own `agk.toml` has no `[domain]` table.

## Consequences

Domain knowledge exists as checked, cited data before anything composes it (build (b)). With no `[domain]` table no
pack applies, so an upgrade changes nothing a project sees but two new files and one more doctor line. No workflow,
label, required check, `agk.mk` recipe or governance step changes.

## Residual

- 2026-11-25: a person checks the seed packs' citations against the public pages and removes each `(verify)`.
- 2026-11-25: composition, the grill's use of `[[discovery]]` and the cited-research use of `stale_months` are builds
  (b), (c) and (g).
