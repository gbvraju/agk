# ADR-0801: The [quality] table, the grill keys of the playbooks and grill.py questions

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0073, SPEC-0038, SPEC-0048, ADR-0793, ADR-0527, ADR-0786, brief #1933, brief #1715, plan #661
- Requirements: REQ-080

Protected classes: `scripts/agk/`, `config/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0073 (Approved) rule 15 build (a) is the first build of the grill. Before it, on the default branch at e1640ba,
`agk.toml` had no `[quality]` table and no reader for one, a `[[discovery]]` entry of a playbook accepted only `id`
and `text`, every entry was asked as a discovery question by `engines.py questions`, and `scripts/agk/grill.py` did not
exist. Amendment 237 item 1 (SPEC-0038 rule 2, the two keys) was approved by the owner on #1920 (comment 7159666133,
`Maintainer answer: amendment 237 approved`); this build applies it word for word.

## Decision

1. `config.quality_settings(root)` reads one optional `[quality]` table in the form of `steward_settings`: `grill`
   (`light`, `standard`, `deep`; `standard`, or `light` with a declared `[delivery] work_type = "pilot"` and no `grill`
   key), `grill_hold` (a boolean, `true`), `glossary_terms` (10 to 200, 40), `designs` (1 or 2; 2, or 1 with a declared
   pilot) and `survey_days` (0 to 30, 7). A `bool` is never a number. A refusal is
   `the [quality] table is refused (setting: quality.<key>)`, never the value. `config.TABLE_KEYS` lists the five keys,
   so `misplaced_settings` reports one placed elsewhere and `uninstall.py` removes the table through `KIT_SETTINGS`.
2. A `[[discovery]]` entry may carry `depth` (`light`, `standard`, `deep`) and `critical` (a boolean), both or neither;
   with both it is a grill item. `playbook_format.problems` refuses a depth outside the three, a non-boolean critical,
   one key without the other, and a grill id that reuses a topic id, a fixed id, another `[[discovery]]` id of the file
   or, in a work type's playbook, a grill id of `default.toml`, each naming the playbook and the key, never a value. The
   checks live in `playbook_format._discovery`, which `check_playbooks.py` runs (`Q-73A-2`).
3. `playbook_format.discovery()` returns only entries without `depth`, so no grill item is asked as a discovery question;
   `playbook_format.grill_items()` returns the grill items; the derived playbook's skeleton copies only `default.toml`'s
   discovery questions. The ten topic ids are one tuple, `playbook_format.TOPIC_IDS`, which a test pins equal to
   `front_door.TOPICS` and `engines.TOPICS`.
4. `config/playbooks/default.toml` carries the twelve seed grill items of SPEC-0073 rule 3; `problem`, `who-hurts`,
   `non-goals` and `riskiest` are the critical ones at depth `light`, and `success` stays a discovery id, read as the
   fifth critical item.
5. `scripts/agk/grill.py questions [--depth D] [--playbook KIND] [--answers FILE] [--root DIR]` prints the items to ask
   in order: `default.toml`'s at or below the depth, then the work type's own (`Q-73A-3`), then `success`; never an id
   the answers file holds; one `Recommended: <steward fills>` line after each item and a last `budget: <n>` line (5, 12
   or 20). Standard library, `common.py`, `config.py` and `playbook_format.py`; no network, no model.
6. `doctor.py` prints `quality-settings`: the five values in the kit's own words, or the refusal naming the key.

## Consequences

The grill's items and depths exist as checked data and build (b)'s interview has a source. Every shipped playbook,
every discovery document and every question asked today is unchanged; with no `[quality]` table every default holds.
Builds (b), (c), (e), (g) and (h) read their keys from `quality_settings`. No workflow, label, required check,
`agk.mk` recipe or governance step changes; `kit/hashes.json` and the version stay the release's.

## Residual

- 2026-11-25: `grill.py record` and `ready`, the `/agk:grill` skill and the install manifest entry are build (b)'s.
