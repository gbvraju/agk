# ADR-0677: The interface contract and the data model before the first back-end change (REQ-079)

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: SPEC-0072, SPEC-0048, SPEC-0062, brief #1597, brief #1586, brief #1588, brief #1602, plan #661, ADR-0666, ADR-0668, amendment 207
- Requirements: REQ-079, REQ-055

Protected classes this pull request changes: `scripts/agk/` (the new `gates/contract_tests.py` and
`gates/mock_parity.py`, the shared reader in `gates/__init__.py`, `check_plan.py`), `config/` (the playbooks
`web-app.toml`, `api-service.toml` and `data-pipeline.toml`), `tests/kit/` (the new `test_contracts.py` and the
playbook tests that pinned the two gates as judgement), `tests/kit_dev/` (`test_stack_playbook.py`), `kit/` (the new
`kit/templates/contract-openapi.json` and `kit/templates/data-model.md`, `kit/templates/architecture.md`,
`kit/manifest.json`) and `agk.toml` (`[[testing.map]]` entries). `kit/hashes.json` is not edited by hand.

## Context

`web-app.toml`'s `brief_order` starts its feature work at `contract`, and its gates `contract-tests` and `mock-parity`
were restated as `judgement` by ADR-0666 (brief #1586) with a reason naming brief #1597; `api-service.toml`'s
`contract-tests` the same. No contract format, contract template or data model template exists, and SPEC-0072 rule 5's
architecture record names neither. The owner asks for no gap in the architecture before the first back-end change
(brief #1597, gap G20).

## Decision

1. The interface contract of an HTTP service is OpenAPI 3.1 in JSON at `contracts/openapi.json`, written from
   `kit/templates/contract-openapi.json`; a file input or output is a JSON Schema file under `contracts/`; the data
   model is `docs/data-model.md` from `kit/templates/data-model.md`, one row per entity with its keys, the personal-data
   class of each field, how long it is kept and who may see it. `kit/templates/architecture.md` names both. JSON only:
   the checks read with the standard library (brief `Q-1`, as recommended). SPEC-0072 rule 5 gains this by amendment
   207, proposed for the spec's approver.
2. `contract-tests` (`scripts/agk/gates/contract_tests.py`) fails a contract that does not parse, one whose `openapi`
   is not 3.1, an operation with no `operationId`, and an operation whose `operationId` no file under `test_dirs`
   names as a whole word (any stack: the reference is found by text). `mock-parity`
   (`scripts/agk/gates/mock_parity.py`) fails an operation with no mock under `mocks/` (a JSON file
   `{"operationId": ..., "response": {...}}`) and a mock whose response keys differ from the properties of the
   operation's first 2xx JSON response schema, a local `$ref` resolved. Each failure names the gate id, the rule and
   the path class, never an operation or a value (principle 8). JSON is read after line-end normalising.
3. With no `contracts/openapi.json` both steps print `not run <id>: no contract in the kit's format`, never `ok` and
   never red, so a project before its contract brief is not blocked. In `mode = "adopt"` a contract whose `openapi`
   is not 3.1 is kept and named as `not run <id>: a contract in another format`; outside adopt it is red.
4. Both gates return to `kind = "check"` with their `step` in `web-app.toml`, and `contract-tests` in `api-service.toml`
   (its reason named this brief), the stronger kind (SPEC-0072 rule 2). `data-pipeline.toml`'s `data-contract` gate
   names its JSON Schema path under `contracts/` and stays `judgement` with that reason.
5. `check_plan.py` refuses, naming `SPEC-0072 rule 5` and the brief key, a `Kind: back-end` brief file of a work type
   whose `brief_order` holds `contract` while `contracts/openapi.json` or `docs/data-model.md` is missing, unless it
   names the `Kind: contract` brief on a `Depends-on:` line; with both files present nothing is held.
6. The architect agent drafts the contract and the data model in the `contract` brief's pull request and a fresh
   reviewer agent reviews them, cleared like any build. The person is asked only the business part of the data model,
   in one plain question with a recommendation (which data is kept, for how long, who may see it; SPEC-0062 rule 9),
   and the template's `Approved by the person:` line records the yes. The person does not approve the whole contract
   (brief `Q-2`, as recommended).

## Consequences

A web app's or API service's governance is red when an operation has no test or (web app) no mock, naming the gate.
Projects without a contract see `not run`. The kit's own repository declares no work type, so its output is
unchanged. No workflow, ruleset, required check or `agk.mk` changes.

## Residual

- 2026-11-21: YAML contracts need a pinned reader and a later ADR (brief `Q-1`).
- 2026-11-21: a JSON Schema file of a data pipeline is not yet compared with the source and target fields; the
  `data-contract` gate stays a reviewer's judgement (due 2027-03-31).
