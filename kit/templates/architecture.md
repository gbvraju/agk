# Architecture

The architecture record of this project (SPEC-0072 rule 5). The foundation build writes it once from the playbook
`{{work_type}}`; it changes only by an ADR of the project (`docs/architecture.md` is a protected path). The `layers`
step of `make governance` fails an import from one layer into another that the allowed directions below do not list.

## Layers

| Layer | Paths |
|-------|-------|
{{layers}}

## Allowed directions

{{allow}}

Any other import between two layers is refused. A new direction needs an ADR of the project that names it.

## Contract and data model

The interface contract is `contracts/openapi.json` (OpenAPI 3.1 in JSON; a file input or output is a JSON Schema file
under `contracts/`), and the data model is `docs/data-model.md`: each entity with its keys, the personal data of each
field, how long it is kept and who may see it (ADR-0677). The `contract-tests` and `mock-parity` steps keep the tests
and the mocks in step with the contract, and no back-end brief merges before both exist.

## Stack

The stack record: {{stack_adr}}. Before writing code, read this record and the chosen stack's standards pack.
