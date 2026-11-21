# Proposed spec amendments 207 (SPEC-0072; REQ-079)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0677 (brief #1597), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md`. Brief #1597 reserved amendment 207.
This file proposes the lines and does not edit the spec. They are applied word for word, on a person's
`Approve: SPEC-0072`; no session posts it.

## Why

Rule 5's architecture record names the layers and the stack record, but no interface contract and no data model, and
`web-app.toml`'s `contract-tests` and `mock-parity` steps have no format to read (brief #1597, gap G20).

## Items

1. **Rule 5,** one sentence appended after "(it is added to the project's protected paths by build (d))."

   ```
   The record also names the interface contract and the data model (brief #1597, ADR-0677): an HTTP service's contract
   is OpenAPI 3.1 in JSON at `contracts/openapi.json` (from `kit/templates/contract-openapi.json`), a file input or
   output is a JSON Schema file under `contracts/`, and the data model is `docs/data-model.md` (from
   `kit/templates/data-model.md`: each entity with its keys, the personal-data class of each field, how long it is kept
   and who may see it); the `contract-tests` step fails an operation whose `operationId` no file under `test_dirs`
   names and a contract that does not parse, the `mock-parity` step fails an operation with no mock under `mocks/` of
   the same `operationId` and response keys, both print `not run` while no contract in this format exists (in
   `mode = "adopt"`, also for a contract in another format), and `check_plan.py` refuses a `back-end` brief that may
   merge before the contract and the data model exist.
   ```

2. **`## Tests`,** one line after the line of rules 5 and 6:

   ```
   - Rule 5, the contract: `tests/kit/test_contracts.py`, markers `REQ-079 AC2` and `REQ-055`.
   ```

No other rule changes.
