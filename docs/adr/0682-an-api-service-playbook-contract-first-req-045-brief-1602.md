# ADR-0682: An api-service playbook, contract first, with its layers, gates and detect signals (REQ-045, REQ-079)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: SPEC-0038, SPEC-0057, SPEC-0072, ADR-0665, brief #1602, brief #1585, brief #1591, brief #1597, brief #1593, plan #661
- Requirements: REQ-045, REQ-079

Protected classes this pull request changes: `config/` (`config/playbooks/api-service.toml`,
`config/stack-signals.toml`), `scripts/agk/` (`playbook_format.py`), `kit/` (`kit/manifest.json`), `tests/kit/` (the
new `test_api_service_playbook.py` and the playbook tests whose counts change) and `tests/kit_dev/`
(`test_kit_manifest.py`). `kit/hashes.json` is not edited by hand: `kit_hashes.py` reports it current.

## Context

On the default branch at 28ddd04 (2026-11-20) `config/playbooks/` holds ten playbooks and none for a service that other
apps call. SPEC-0048 rule 22 and SPEC-0072 rule 8 give such a project a playbook of its own, drafted once per project,
so no two API projects share one reviewed default. SPEC-0038 rule 1 names a fixed list of nine work types, and
`playbook_format.WORK_TYPES` holds it ("a later amendment adds one entry here"); a shipped playbook outside the list is
refused by rule 1. SPEC-0057 rule 5 has `config/stack-signals.toml` name, per work type, one manifest file and one word,
and `front_door.py check-signals` refuses a playbook that has neither a row nor a place in `no_signal`.

## Decision

1. The work type `api-service` is added to the fixed list of SPEC-0038 rule 1, as the tenth entry of
   `playbook_format.WORK_TYPES`, the way amendment 130 added `data-pipeline`. This ADR is that widening; the text of
   SPEC-0038 rule 1 is the maintainers' to amend (`Q-1602-1`).
2. `config/playbooks/api-service.toml` is shipped verbatim (`kit/manifest.json`) and composes on `default.toml`:
   - `[split] brief_order` is `foundation`, `contract`, `back-end`, `join`, each after the one before it;
   - `[architecture]` has the four layers `contracts`, `api`, `domain` and `data`, each one `[testing] map` code
     (`contracts/**`, `api/**`, `domain/**`, `data/**`), and the `allow` entries `api -> contracts`, `api -> domain` and
     `domain -> data`; `contracts/**` is always tested in full;
   - the gates `contract-tests` (the step of brief #1597), `secrets` and `environment-settings` (brief #1593) are
     checks; `input-validation`, `sign-in-permissions` and `logging-tracing` are judgement with a reason until their
     steps land; `accessibility` is judgement with the reason that a service has no screens. The other base gates come
     from `default.toml` unchanged, so no gate is lowered;
   - besides the five common discovery ids it asks who calls the service, how fast each call must answer and how
     callers sign in.
3. `front_door.py detect` proposes `api-service` on these rows of `config/stack-signals.toml`: `fastapi` in
   `pyproject.toml` or `requirements.txt`, and `@nestjs/core` in `package.json`. A framework that serves pages as often
   as it serves calls (a general web framework) is not a signal, so a web app's tree is not proposed as a service. A
   signal stays a proposal; the owner's `[delivery] work_type` line (SPEC-0038 rule 5) decides.
4. Settings: `[delivery] work_type = "api-service"` selects this playbook; with no line, nothing changes. A project's own
   module may add gates over it; loosening one needs an ADR, as for every playbook (SPEC-0038 rule 4).
5. A project that already drafted its own API playbook is never moved to this one automatically (`Q-1602-2`).

## Consequences

- Hosted, local and personal modes read the same playbook through the same `check_playbooks.py`; solo and team, strict
  and flow are unchanged; a clean layout takes it from the plugin. On Windows, WSL and macOS it is data only.
- New repositories are offered it at the vision stage; adopted ones by `detect`, applied only on the owner's yes.
- The playbook tests that count the shipped playbooks or the work types now count eleven and ten.

## Residual

- 2026-11-20: the stack default row `api-service` of `config/stack-defaults.toml` (one service with a published
  interface description and a managed database) lands once brief #1591 has added that file (`Q-1602-3`).
- 2026-11-20: the `contract-tests` step is brief #1597's; until it lands the gate is a check without its step on disk,
  as the other shipped check gates whose steps a later build adds.
