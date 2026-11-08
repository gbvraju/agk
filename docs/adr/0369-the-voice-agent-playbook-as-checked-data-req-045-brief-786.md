# ADR-0369: The voice-agent playbook as checked data (REQ-045, brief 786)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0251, ADR-0365, ADR-0352, ADR-0315, ADR-0259, SPEC-0038
- Requirements: REQ-045

Protected classes: `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0038 rule 12 build (m) ships the `voice-agent` playbook as checked data with the voice-agent
gates of rule 10: a latency budget, `check` that it is declared and `judgement` that a recorded run
meets it; an ASR/TTS evaluation set, `check` (the set exists with a version line); and barge-in and
fallback scenarios, `check` (each scenario is listed and the map names its tests). Rule 11 gives
voice-agent no phases, lanes, testing map or milestone shape, and brief #786 answer 1 says to invent
nothing beyond the gates and to name no vendor, product or tool. ADR-0251 sets the direction and
lists the classes the builds of SPEC-0038 change; ADR-0259 added the format module and
`check_playbooks.py`, which this file must pass; ADR-0365 (multi-agent, build (l)) shipped the
playbook whose shape and tests this build follows. Brief #786 gives the build; this ADR number was
reserved for it by the conductor.

## Decision

1. `config/playbooks/voice-agent.toml` (new, installed, in `verbatim` of `kit/manifest.json`) holds
   the gates of rule 10 as four entries. Three are `check`, each naming the step a later build adds:
   `latency-budget`, `asr-tts-evaluation-set` and `barge-in-fallback-scenarios`. One is `judgement`:
   `latency-budget-met`. The latency budget is one gate of rule 10 with two kinds, so it is two
   entries, as the budgets of multi-agent are (ADR-0365 decision 1). Rule 10 marks none of them as
   the owner's action, so none is `owner_only`.
2. The format requires every section, and rule 11 gives voice-agent none of the delivery shape. So,
   as for multi-agent (ADR-0365 decision 2), the file carries today's flow and nothing more: one
   phase and one brief kind `build` with no `depends_on` pair, no lanes, `[testing]` profile
   `balanced` (the kit's default; rule 4 refuses `fast`) with no `always_full` entry and no map, no
   heavy step, and milestone shape `per-brief`. The tests the scenarios gate reads are mapped in the
   adopting project's own map; the playbook suggests no folder of its own.
3. The three check gates name governance steps that no build has added yet. As for the earlier
   playbooks (ADR-0365 decision 3, `Q-651-2`), the gates keep the `check` kind that rule 10 gives
   them, since rule 4 lets no playbook restate a gate with a weaker kind, and this build adds no
   step to `agk-governance` and changes no file under `.github/` or `agk.mk`; the conductor and the
   owner read each gate as judgement until a build adds its step, which is one more governance step
   under its own ADR (`Q-S0038-9`, brief #786 answer 2).
4. The playbook names the work's gates only: no vendor, product, tool, framework, URL or project
   name, and no version of anything (brief #786 answer 1, tested). It also carries the five
   `[[discovery]]` entries every playbook must hold (SPEC-0048 rule 4), in voice-agent words. Its
   one speed claim is `expected` with no `record`, since no run has measured it. No `reviewed` key
   is added (`Q-651-1`, amendment 129 is its own item).
5. `tests/kit_dev/test_kit_manifest.py` lists the playbook among the installed files outside the
   law roots, and the count lines of the rag-app, data-pipeline, mobile, cloud-migration, mcp-server
   and multi-agent playbook tests read eight playbooks; the LF pin of `kit/templates/gitattributes`
   (`config/playbooks/**`, ADR-0313 decision 5) already covers the file. `kit/hashes.json` is not
   edited; no version is bumped.

## Consequences

Every project that installs or upgrades the kit receives the voice-agent playbook unchanged, and
`check_playbooks.py` prints `ok playbooks (8 playbooks)` there. Nothing reads the file until a
project declares `work_type = "voice-agent"` by its own ADR (rule 5, ADR-0312), so a project that
declares no work type runs exactly as today. A project that declares it gets the four gates as
practices of its stack ADR (rule 6) and one brief kind, as today.

## Residual

- 2026-11-08: the three check gates name governance steps that do not exist yet; until a build adds
  them, the conductor and the owner read the gates as judgement (`Q-651-2`, due 2026-12-31).
- 2026-11-08: rule 11 gives voice-agent no delivery shape or test map suggestion, so the file
  carries today's flow until an amendment gives it more (`Q-786-1`, due 2026-12-31).
- 2026-11-08: the claim is `expected`; no run of this playbook has been measured (SPEC-0038 rule
  11, due 2026-12-31).
