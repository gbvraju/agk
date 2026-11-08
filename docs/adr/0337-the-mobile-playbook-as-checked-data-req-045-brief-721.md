# ADR-0337: The mobile playbook as checked data (REQ-045, brief 721)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0251, ADR-0315, ADR-0313, ADR-0259, SPEC-0038
- Requirements: REQ-045

Protected classes: `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0038 rule 12 build (i) ships the `mobile` playbook as checked data with the mobile gates of
rule 10: a device and simulator matrix, `check` that the matrix file lists the playbook's minimum
entries, with its results `judgement`; offline states, `check` that each screen of the inventory
lists an `offline` state; and store signing, `judgement` and `owner_only`. Unlike web-app and
rag-app, rule 11 gives mobile no phases, lanes, testing profile or milestone shape, and brief #721
answer 1 says to invent nothing beyond the gates. ADR-0251 sets the direction and lists the classes
the builds of SPEC-0038 change; ADR-0259 added the format module and `check_playbooks.py`, which
this file must pass; ADR-0315 shipped the rag-app playbook of build (d), whose shape and tests this
build follows. Brief #721 gives the build; this ADR number was reserved for it by the conductor.

## Decision

1. `config/playbooks/mobile.toml` (new, installed, in `verbatim` of `kit/manifest.json`) holds the
   three mobile gates of rule 10 as four gate entries, because the format gives a gate one `kind`:
   `device-matrix` (`check`, step `device-matrix`), `device-matrix-results` (`judgement`),
   `offline-states` (`check`, step `offline-states`) and `store-signing` (`judgement`,
   `owner_only = true`; rule 4 refuses a signing gate that is not owner only). No other gate is
   owner only.
2. The format requires every section, and rule 11 gives mobile none of the delivery shape. So the
   file holds the shape of today's flow and nothing more: one phase `build` and one brief kind
   `build` with no dependence, no lanes, `[testing]` profile `balanced` (the kit's default; rule 4
   refuses `fast`) with no `always_full` entry and no map, no heavy step, and milestone shape
   `per-brief`, one pull request per brief, as today. A project that declares `mobile` therefore
   gets the gates and keeps its order of work; a later amendment that gives mobile a shape changes
   this file.
3. The two check gates name governance steps that no build has added yet. As for web-app and
   rag-app (ADR-0313 decision 4, ADR-0315 decision 5, `Q-651-2`), this build adds no step to
   `agk-governance` and changes no file under `.github/` or `agk.mk`; the conductor and the owner
   read those gates as judgement until a build adds their steps, which is one more governance step
   under its own ADR (`Q-S0038-9`, brief #721 answer 2).
4. The playbook names the work's gates only: no vendor, device, store, tool, URL or project name,
   and no version of anything (brief #721 answer 1, tested). Its one speed claim is `expected` with
   no `record`, since no run has measured it. No `reviewed` key is added (`Q-651-1`, amendment 129
   is its own item).
5. `tests/kit_dev/test_kit_manifest.py` lists the playbook among the installed files outside the
   law roots, and the count line of `tests/kit/test_playbook_rag_app.py` reads three playbooks;
   the LF pin of `kit/templates/gitattributes` (`config/playbooks/**`, ADR-0313 decision 5) already
   covers the file. `kit/hashes.json` is not edited; no version is bumped.

## Consequences

Every project that installs or upgrades the kit receives the mobile playbook unchanged, and
`check_playbooks.py` prints `ok playbooks (3 playbooks)` there. Nothing reads the file until a
project declares `work_type = "mobile"` by its own ADR (rule 5, ADR-0312), so a project that
declares no work type runs exactly as today. Build (j), the cloud-migration playbook, and build
(n), the pilot playbook, change `kit/manifest.json` and follow this one (`Q-S0038-16`).

## Residual

- 2026-11-08: the two check gates name governance steps that do not exist yet; until a build adds
  them, the conductor and the owner read those gates as judgement (`Q-651-2`, due 2026-12-31).
- 2026-11-08: rule 11 gives mobile no delivery shape, so the file carries today's flow (one kind,
  no lanes, `per-brief`) until an amendment gives it one (`Q-721-1`, due 2026-12-31).
- 2026-11-08: the claim is `expected`; no run of this playbook has been measured (SPEC-0038 rule
  11, due 2026-12-31).
- 2026-11-08: the `device-matrix` gate and rule 10 point at minimum entries this playbook does not
  list (the format has no place for them and rule 1 forbids device names), so the gate is read as
  judgement until an amendment says where the entries live (`Q-721-3`, due 2026-12-31).
