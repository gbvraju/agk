# ADR-0313: The web-app playbook as checked data (REQ-045, brief 651)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0251, ADR-0259, SPEC-0038
- Requirements: REQ-045

Protected classes: `config/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0038 rule 12 build (c) ships the first playbook, `web-app`, as checked data with the phases,
lanes, testing profile, milestone shape and gates that rules 10 and 11 give it. ADR-0251 sets the
direction and lists the classes the builds of SPEC-0038 change; ADR-0259 added the format module
`scripts/agk/playbook_format.py` and the governance step `check_playbooks.py` that this file must
pass. Brief #651 gives the build; this ADR number was reserved for it by the conductor.

The owner asked on 2026-11-06 how playbooks are kept from going out of date (brief #651 answer 3).

## Decision

1. `config/playbooks/web-app.toml` (new, installed, in `verbatim` of `kit/manifest.json`) holds
   exactly the content of SPEC-0038 rule 11: phases `contract`, `mocks`, then `front-end` and
   `back-end` (both after `mocks`, same order) in two lanes, then `joins` after both; brief kinds
   in that order with their `depends_on` pairs and no dependence between the two sides; `[testing]`
   profile `balanced`, `always_full` for the contract folder and a per-module `map` suggestion; the
   e2e smoke run as its one heavy step; milestone shape `per-batch`, batched by demo value; the
   four web-app gates of rule 10 (contract tests and mock parity `check`, the e2e smoke run per
   merge batch and accessibility `judgement`), none `owner_only`; and two speed claims, both
   `expected`, since no measured record exists under `docs/runs/`.
2. The playbook holds the shape of the work and its gates only: no tool, vendor, framework, URL or
   project name. A tool choice is a per-engagement decision with a sourced research record, as
   for the pilot playbook (brief #651 answer 3). The folders it names (`contracts/`, `mocks/`,
   `frontend/`, `backend/` and their `tests/` mirrors) are suggestions a project maps to its own.
3. No `reviewed` date key is added: SPEC-0038 rule 2 allows no key outside the format and the
   check refuses one. Whether a dated review line is added is asked on the pull request
   (`Q-651-1`); amendment 129 is reserved for it and not written here.
4. The `step` of each check gate names the governance step that a later build adds
   (`contract-tests`, `mock-parity`); this build adds no step to `agk-governance` and changes no
   file under `.github/` or `agk.mk` (rule 12 build (c) lists only the playbook, the manifest and
   one test; `Q-651-2`).
5. The installed `.gitattributes` block (`kit/templates/gitattributes`) gains
   `config/playbooks/** text eol=lf`, so every shipped playbook keeps LF line ends as every other
   installed file does, and `tests/kit_dev/test_kit_manifest.py` lists the playbook among the
   installed files outside the law roots; both tests failed without these lines.
6. `kit/hashes.json` is not edited; no version is bumped.

## Consequences

Every project that installs or upgrades the kit receives the web-app playbook unchanged, and
`check_playbooks.py` prints `ok playbooks (1 playbooks)` there. Nothing reads the file yet: the
declaration, `/agk:stack`, `/agk:brief`, the plan and the verdict's evidence are builds (b) and
(e) to (h), so a project that declares no work type runs exactly as today.

## Residual

- 2026-11-06: the two check gates name governance steps that do not exist yet; until a build adds
  them, the conductor and the owner read those gates as judgement (`Q-651-2`, due 2026-12-31).
- 2026-11-06: the claims stay `expected` until an anonymised Phase 2 record is a file under
  `docs/runs/` (SPEC-0038 rule 11, due 2026-12-31).
- 2026-11-06: a dated review line awaits the ruling on `Q-651-1` (due 2026-12-31).
