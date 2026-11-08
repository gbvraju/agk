# ADR-0377: The pilot playbook as checked data (REQ-045, brief 805)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0251, ADR-0260, ADR-0369, SPEC-0038
- Requirements: REQ-045

Protected classes: `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0038 rule 12 build (n) ships the `pilot` playbook as checked data: rule 10 gives its eight gates
and rule 11 its phases, lanes, milestone shape, heavy step and claims. ADR-0251 sets the direction,
ADR-0260 added the pilot work type and says this build writes its own ADR naming its classes
(`Q-S0038-9`), and ADR-0369 (voice-agent, build (m)) shipped the playbook whose shape and tests this
build follows. Brief #805 gives the build; this ADR number was reserved for it by the conductor.

## Decision

1. `config/playbooks/pilot.toml` (new, installed, in `verbatim` of `kit/manifest.json`) holds the
   phases of rule 11 in order: `intake`, `research`, `choice`, `contract`, `build`, `demo` and
   `report`, so `research` and `choice` come before `contract`. `build` is one phase with the three
   lanes of rule 11, `integration`, `demo-surface` and `evaluation`, which are its brief kinds.
   `[split]` has one brief kind per other phase, each depending on the one before; the three lanes
   depend on `contract` and `demo` depends on the three. A `choice` brief records the owner's choice
   and makes none (gate `tool-choice`).
2. The eight gates of rule 10 are ten entries. The research record and the cost estimate each have a
   `check` part and a `judgement` part, so each is two entries (`research-record`,
   `research-findings`; `cost-estimate`, `cost-estimate-holds`), as the budgets of voice-agent are
   (ADR-0369 decision 1). `tool-choice` and `credentials` are the `owner_only` entries.
3. The six check entries name governance steps that no build has added yet. As for the earlier
   playbooks (ADR-0369 decision 3, `Q-651-2`), they keep the `check` kind that rule 10 gives them,
   since rule 4 lets no playbook restate a gate with a weaker kind, and the conductor and the owner
   read each as judgement until a build adds its step. This build adds no step to `agk-governance`
   and changes no file under `.github/` or `agk.mk` (`Q-S0038-9`, brief #805 answer 2). No check
   enforces the time box (`Q-S0038-15`), and no check fetches a source (`Q-S0038-14`).
4. Rule 11 sets the milestone shape `per-phase` and the heavy step `demo smoke run`, and gives no
   test map, so `[testing]` is profile `balanced` with no `always_full` entry and no map. Its two
   claims are `expected` with no `record`, since no run has measured them.
5. The playbook names no vendor, product, tool, framework or URL and no version (brief #805 answer
   1, tested); the research record that names them is a file of the project running the pilot, never
   of the kit (`Q-S0038-17`). It carries the five `[[discovery]]` entries every playbook must hold
   (SPEC-0048 rule 4), in pilot words. No `reviewed` key is added (`Q-651-1`, amendment 129 is its
   own item).
6. `tests/kit_dev/test_kit_manifest.py` lists the playbook among the installed files outside the law
   roots, and the count lines of the eight other shipped playbooks' tests read ten playbooks; the LF
   pin of `kit/templates/gitattributes` (`config/playbooks/**`, ADR-0313 decision 5) already covers
   the file. `kit/hashes.json` is not edited; no version is bumped.

## Consequences

Every project that installs or upgrades the kit receives the pilot playbook unchanged, and
`check_playbooks.py` prints `ok playbooks (10 playbooks)` there. Nothing reads the file until a
project declares `work_type = "pilot"` by its own ADR (rule 5, ADR-0312), so a project that declares
no work type runs exactly as today. A project that declares it gets the seven phases, three lanes
and ten gate entries; a later production project declares its own work type (`Q-S0038-13`).

## Residual

- 2026-11-08: the six check entries name governance steps that do not exist yet; until a build adds
  them, the conductor and the owner read them as judgement (`Q-651-2`, due 2026-12-31).
- 2026-11-08: the time box is declared and shown, and nothing enforces it (`Q-S0038-15`, due
  2026-12-31).
- 2026-11-08: both claims are `expected`; no run of this playbook has been measured (SPEC-0038 rule
  11, due 2026-12-31).
