# ADR-0805: Domain packs compose after the playbook, never weakening, with a domain signal table

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: SPEC-0074, SPEC-0057, SPEC-0048, SPEC-0038, ADR-0804, ADR-0794, ADR-0371, ADR-0259, brief #1936, brief #1935, plan #661
- Requirements: REQ-081

Protected classes: `scripts/agk/`, `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`, `docs/specs/`, `agk.toml`

## Context

SPEC-0074 (Approved) rule 16 build (b): rule 4 (one composition), rule 3's project pack, rule 5's signal table and
amendment 240 to SPEC-0048 rule 23, which the owner approved on #1922 (`Maintainer answer: amendment 240 approved`,
comment 7159679447). Before it, on the default branch at 71eb8ab, `check_playbooks.composed` read `default`, the
modules and the playbook only, and no file named a domain's signals.

## Decision

1. `check_domains.compose(root, layers)` takes the layers of `check_playbooks._layers` unchanged and appends each pack
   of `[domain] packs` in `check_domains.order`: the shipped packs (`check_domains.SHIPPED`, which a test holds equal to
   the `config/domains/` entries of `kit/manifest.json`) in the person's order, each followed by its jurisdiction
   layers (a listed pack named `<domain>-<region>`, in list order, even when listed before its domain), then the
   project's own packs the same way. A jurisdiction layer whose domain is not listed stays where it is listed and is
   one `warn domains:` line naming the missing domain.
2. `check_playbooks.composed` judges every layer of that one list with its one `_weakened`: a pack gate with an earlier
   id replaces it only when the same or stronger, and a weakening is `rule 21: config/domains/<file>: a gate is
   restated weaker (key: <key>)`, naming the pack's file. A refused `[domain]` table is one problem line,
   `rule 4: agk.toml: the [domain] table is refused (setting: domain.packs)`; `config.domain_settings` now also
   refuses a pack listed twice. `findings` prints a line the same for every playbook once.
3. `check_domains.items(root)` keeps each `[[discovery]]`, `[[terms]]` and `[[acceptance]]` item once at its first
   place and every `[[constraints]]` entry with its pack (only an exact repeat is dropped). `check_domains.warnings`
   prints `warn domains: attribute <attribute>: <id> (<pack>) and <id> (<pack>) differ; the stricter holds until a
   person decides` for a constraint whose attribute an earlier one names with another scenario. The composer never
   ranks two scenarios (free text, `Q-D74B-2`) and never drops either; the person's decision is rule 9's (build (d)).
   The warnings go to stderr from `check_playbooks.py` and `check_domains.py` and never fail.
4. The domain signal table `config/domain-signals.toml`: `[[domain]]` rows of `name` (a pack of the kit's
   `config/domains/`), `words`, `files` and `dependencies` (lists of single words), one row per seed pack.
   `front_door.signal_problems` also checks it (`front_door.domain_signal_problems`), each line `rule 5:
   config/domain-signals.toml: [[domain]] row <n> ... (key: <key>)`, never a value; a kit copy without the file
   has nothing to check. It joins `kit/manifest.json` `verbatim`. Reading it to propose a domain is build (c).
5. `tests/kit_dev/test_kit_manifest.py` lists the table among the installed single files (SPEC-0074 rule 15), the
   one change under `tests/kit_dev/`, a class the brief's reserved line did not name. A project's own pack is never in the manifest, so the installer and `upgrade.py` (`installed_set`) never write it.
6. Amendment 240 is applied to SPEC-0048 rule 23 word for word; its proposal file records the application.
7. The order of `default`, the modules and the playbook stays the code's (modules before the playbook, SPEC-0074 rule
   1), while rule 4 and amendment 240 read "the work type, its modules" (`Q-D74B-3`): the packs follow both either way,
   and the maintainers may align the text or the code.

## Consequences

With no `[domain]` table, or `packs = []`, every playbook composes exactly as before (a test compares all eleven), so
the kit itself and every project without packs see no change but one new file. No workflow, label, required check,
`agk.mk` recipe or `governance_map.CHECKS` entry changes.

## Residual

- 2026-11-26: Q-D74B-3, the order of the modules and the playbook in the spec's text against the code's.
- 2026-11-26: the composed items reach the grill in build (c), and the constraints the architecture in build (e).
