# ADR-0365: The multi-agent playbook as checked data (REQ-045, brief 780)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0251, ADR-0352, ADR-0338, ADR-0337, ADR-0315, ADR-0259, SPEC-0038
- Requirements: REQ-045

Protected classes: `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0038 rule 12 build (l) ships the `multi-agent` playbook as checked data with the multi-agent
gates of rule 10: role and handoff contracts, `check` (a contract file for each role and handoff,
with tests mapped); trace-based evaluation, `judgement`; and cost and latency budgets, `check` that
they are declared as numbers and `judgement` that a recorded run meets them. Rule 11 gives
multi-agent no phases, lanes, testing map or milestone shape, and brief #780 answer 1 says to invent
nothing beyond the gates and to name no vendor, product or tool. ADR-0251 sets the direction and
lists the classes the builds of SPEC-0038 change; ADR-0259 added the format module and
`check_playbooks.py`, which this file must pass; ADR-0352 (mcp-server, build (k)) shipped the
playbook whose shape and tests this build follows. Brief #780 gives the build; this ADR number was
reserved for it by the conductor.

## Decision

1. `config/playbooks/multi-agent.toml` (new, installed, in `verbatim` of `kit/manifest.json`) holds
   the gates of rule 10 as four entries. Two are `check`, each naming the step a later build adds:
   `role-handoff-contracts` and `cost-latency-budgets`. Two are `judgement`:
   `trace-based-evaluation` and `cost-latency-budgets-met`. The budgets are one gate of rule 10 with
   two kinds, so they are two entries, as the quality bars of rag-app are (ADR-0315). Rule 10 marks
   none of them as the owner's action, so none is `owner_only`.
2. The format requires every section, and rule 11 gives multi-agent none of the delivery shape. So,
   as for mobile (ADR-0337 decision 2) and mcp-server (ADR-0352 decision 2), the file carries
   today's flow and nothing more: one phase and one brief kind `build` with no `depends_on` pair, no
   lanes, `[testing]` profile `balanced` (the kit's default; rule 4 refuses `fast`) with no
   `always_full` entry and no map, no heavy step, and milestone shape `per-brief`. The tests the
   contracts gate reads are mapped in the adopting project's own map; the playbook suggests no
   folder of its own.
3. The two check gates name governance steps that no build has added yet. As for the earlier
   playbooks (ADR-0315 decision 5, ADR-0337 decision 3, ADR-0338 decision 3, ADR-0352 decision 3,
   `Q-651-2`), the gates keep the `check` kind that rule 10 gives them, since rule 4 lets no
   playbook restate a gate with a weaker kind, and this build adds no step to `agk-governance` and
   changes no file under `.github/` or `agk.mk`; the conductor and the owner read each gate as
   judgement until a build adds its step, which is one more governance step under its own ADR
   (`Q-S0038-9`, brief #780 answer 2).
4. The playbook names the work's gates only: no vendor, product, tool, framework, URL or project
   name, and no version of anything (brief #780 answer 1, tested). It also carries the five
   `[[discovery]]` entries every playbook must hold (SPEC-0048 rule 4), in multi-agent words. Its
   one speed claim is `expected` with no `record`, since no run has measured it. No `reviewed` key
   is added (`Q-651-1`, amendment 129 is its own item).
5. `tests/kit_dev/test_kit_manifest.py` lists the playbook among the installed files outside the
   law roots, and the count lines of the rag-app, data-pipeline, mobile, cloud-migration and
   mcp-server playbook tests read seven playbooks; the LF pin of `kit/templates/gitattributes`
   (`config/playbooks/**`, ADR-0313 decision 5) already covers the file. `kit/hashes.json` is not
   edited; no version is bumped.

## Consequences

Every project that installs or upgrades the kit receives the multi-agent playbook unchanged, and
`check_playbooks.py` prints `ok playbooks (7 playbooks)` there. Nothing reads the file until a
project declares `work_type = "multi-agent"` by its own ADR (rule 5, ADR-0312), so a project that
declares no work type runs exactly as today. A project that declares it gets the four gates as
practices of its stack ADR (rule 6) and one brief kind, as today. Build (m), the voice-agent
playbook, changes `kit/manifest.json` and follows this one (`Q-S0038-16`).

## Residual

- 2026-11-08: the two check gates name governance steps that do not exist yet; until a build adds
  them, the conductor and the owner read the gates as judgement (`Q-651-2`, due 2026-12-31).
- 2026-11-08: rule 11 gives multi-agent no delivery shape or test map suggestion, so the file
  carries today's flow until an amendment gives it more (`Q-780-1`, due 2026-12-31).
- 2026-11-08: the claim is `expected`; no run of this playbook has been measured (SPEC-0038 rule
  11, due 2026-12-31).
