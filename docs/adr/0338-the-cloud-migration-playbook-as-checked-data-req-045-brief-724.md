# ADR-0338: The cloud-migration playbook as checked data (REQ-045, brief 724)

- Status: Accepted
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0251, ADR-0315, ADR-0337, ADR-0313, ADR-0259, SPEC-0038
- Requirements: REQ-045

Protected classes: `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0038 rule 12 build (j) ships the `cloud-migration` playbook as checked data with the
cloud-migration gates of rule 10: inventory, then wave plan, then cut-over, `check` that each
cut-over brief depends on its wave plan brief, which depends on the inventory brief; a rollback
rehearsal as evidence, `judgement`; plan diffs as evidence, `judgement`, a committed plan output
with no secret; and any apply, `judgement` and `owner_only`. Rule 11 gives cloud-migration no
lanes, testing profile or milestone shape, and brief #724 answer 1 says to invent nothing beyond
the gates and to name no vendor, cloud, region, account or tool. ADR-0251 sets the direction and
lists the classes the builds of SPEC-0038 change; ADR-0259 added the format module and
`check_playbooks.py`, which this file must pass; ADR-0315 (rag-app, build (d)) and ADR-0337
(mobile, build (i)) shipped the playbooks whose shape and tests this build follows. Brief #724
gives the build; this ADR number was reserved for it by the conductor.

## Decision

1. `config/playbooks/cloud-migration.toml` (new, installed, in `verbatim` of `kit/manifest.json`)
   holds the four cloud-migration gates of rule 10 as four entries: `cut-over-order` (`check`,
   step `cut-over-order`), `rollback-rehearsal` (`judgement`), `plan-diffs` (`judgement`) and
   `apply` (`judgement`, `owner_only = true`; rule 4 refuses an apply of infrastructure that is
   not owner only). No other gate is owner only.
2. The order gate is the one part of rule 10 that is a delivery shape, so the file states it in
   the format's own places: three phases `inventory`, `wave-plan` and `cut-over`, each after the
   one before, and the brief kinds in that order with `depends_on` pairs `[wave-plan, inventory]`
   and `[cut-over, wave-plan]`. Everything else is today's flow and nothing more: no lanes,
   `[testing]` profile `balanced` (the kit's default; rule 4 refuses `fast`) with no
   `always_full` entry and no map, no heavy step, and milestone shape `per-brief`.
3. The check gate names a governance step that no build has added yet. As for web-app, rag-app
   and mobile (ADR-0313 decision 4, ADR-0315 decision 5, ADR-0337 decision 3, `Q-651-2`), this
   build adds no step to `agk-governance` and changes no file under `.github/` or `agk.mk`; the
   conductor and the owner read the gate as judgement until a build adds its step, which is one
   more governance step under its own ADR (`Q-S0038-9`, brief #724 answer 2).
4. The plan-diffs gate says "with no credential in it" where rule 10 says "with no secret": rule
   4 refuses a gate that names a secret with `owner_only = false`, and this gate is not the
   owner's action, so the plain word that states the same condition is used. The gate keeps its
   kind and its owner flag exactly as rule 10 marks them.
5. The playbook names the work's gates only: no vendor, cloud, region, account, tool, URL or
   project name, and no version of anything (brief #724 answer 1, tested). Its one speed claim is
   `expected` with no `record`, since no run has measured it. No `reviewed` key is added
   (`Q-651-1`, amendment 129 is its own item).
6. `tests/kit_dev/test_kit_manifest.py` lists the playbook among the installed files outside the
   law roots, and the count lines of `tests/kit/test_playbook_rag_app.py` and
   `tests/kit/test_playbook_mobile.py` read four playbooks; the LF pin of
   `kit/templates/gitattributes` (`config/playbooks/**`, ADR-0313 decision 5) already covers the
   file. `kit/hashes.json` is not edited; no version is bumped.

## Consequences

Every project that installs or upgrades the kit receives the cloud-migration playbook unchanged,
and `check_playbooks.py` prints `ok playbooks (4 playbooks)` there. Nothing reads the file until a
project declares `work_type = "cloud-migration"` by its own ADR (rule 5, ADR-0312), so a project
that declares no work type runs exactly as today. A project that declares it gets the three brief
kinds in order with their `Depends-on` pairs from `playbook.py split`, and a brief with no `Kind:`
line is planned as today (`Q-S0038-8`). Build (k), the mcp-server playbook, changes
`kit/manifest.json` and follows this one (`Q-S0038-16`).

## Residual

- 2026-11-08: the order gate names a governance step that does not exist yet; until a build adds
  it, the conductor and the owner read the gate as judgement (`Q-651-2`, due 2026-12-31).
- 2026-11-08: rule 11 gives cloud-migration no lanes, test map or batching, so the file carries
  today's flow around the three ordered kinds until an amendment gives it more (`Q-724-1`, due
  2026-12-31).
- 2026-11-08: the claim is `expected`; no run of this playbook has been measured (SPEC-0038 rule
  11, due 2026-12-31).
