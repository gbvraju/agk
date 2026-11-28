# ADR-0864: An adopted project harvests its parts inferred and ratchets from a baseline

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers (the owner's yes on brief #2074, 2026-11-27T19:43:57Z)
- Related: ADR-0834, ADR-0867, ADR-0860, ADR-0680, ADR-0742, ADR-0743, ADR-0562, ADR-0810, ADR-0806, ADR-0333,
  SPEC-0076, SPEC-0072, SPEC-0059, REQ-083, brief #2074, plan #661
- Requirements: REQ-083

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (g) asks for rule 10: an adopted project's existing libraries enter the
parts record as `inferred` rows, the `parts` step (build (d), ADR-0867) starts green on a baseline, and a new or
touched library needs its full row. On main at 9b6ab96 the `parts` step has no `counts`, so no baseline holds its
findings, no command drafts a record from the build files, onboarding has no parts note and `detect` says nothing of
parts.

## Decision

1. **The harvest.** `python3 scripts/agk/gates/parts.py --harvest --at <YYYY-MM-DD> [--root DIR]` reads each
   runtime `front_door.detect_facts` finds for which `pins.STACKS` has a reader (`node`; `python-pyproject` and
   `python-pip` are `python`), in its folder, through `pins.declared`, `pins.locked` and `licences.components`, and
   writes `docs/parts.md` once from `kit/templates/parts.md`: one `## <runtime>` section per runtime, one row per
   direct dependency in build-file order. `Need` is the catalogue need whose `name` equals the part (the project's
   `config/parts/<stack>.toml`, then the kit's), else `unassigned`; `Version` the lock's, else the exact pin, else
   `not recorded`; `Kind` `dev` for `devDependencies` and every `optional-dependencies` group, else `runtime`; `Why`
   `inferred: not recorded` (`inferred: from the stack record` for a part an Accepted stack record names); `Licence`
   the lock's, else `not recorded`; `Health (date)` `not read (<date>)`; the other columns `not recorded`. It ends
   `Confirmed by: not yet (harvested <date>)` and prints `parts: harvested <n> rows (<k> needs named, <m>
   unassigned)` and `protected: none`. It refuses an existing record and reads no network. A build file it cannot
   read and a stack with no reader are one line each; the rest is written.
2. **The step's counts.** `gates/parts.py` gains `counts(root, playbook)` and `HELD`: every finding of the step,
   failure or warning, per file it is held to. A row whose `Why` begins `inferred`, whose `Need` is `unassigned`, or
   whose required column reads `not recorded` or `not read (...)` counts as a row with an empty required column. An
   `inferred` row whose `Version` differs from the record at the merge base is a finding held to its build file, so a
   touched library fails until its row is completed. The runner's `ratchet` writes `config/agk-baseline/parts.txt`
   in `mode = "adopt"` and the step prints `parts (baseline): <n> held (path class: docs/parts.md)`.
3. **Warnings on a baseline.** `run_gates.results` keeps a step's warnings `<id>: <n> warnings (setting: ...)`, never
   `ok <id>`, when its baseline rows pass with no failure: under `record = "optional"` the baseline is still written,
   so a later switch to `required` starts green.
4. **Onboarding.** `steward_onboard.from_parts(root, gaps)`, called by `harvest` after `from_domain`: with a record one
   decision `docs/parts.md: <n> parts, <c> confirmed, <i> inferred`; with none and a build file `pins.STACKS` reads,
   one gap `no parts record: parts.py --harvest drafts one`; an unreadable record is a gap naming the path.
5. **Detect.** `front_door.detect_facts` gains `parts` and `detect_lines` one line per `node` or `python` runtime:
   `parts: <n> direct dependencies in <build file>, no parts record (proposed: parts.py --harvest)` or `parts:
   record present`; `parts: not read (no kit copy)` when `pins` cannot be imported.

## Consequences

An adopted project gets a draft parts record and a green baseline on its first run, and each library gains its reason
as it is touched; the baseline only falls. The step is still not run with no Accepted stack record (`no stack
chosen`, ADR-0867). No workflow, ruleset, required check, `agk.mk` or `governance_map.CHECKS` changes.
