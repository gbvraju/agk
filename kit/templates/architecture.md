# Architecture

The architecture record of this project (SPEC-0072 rule 5). The foundation build writes it once from the playbook
`{{work_type}}`; it changes only by an ADR of the project (`docs/architecture.md` is a protected path). The `layers`
step of the governance gate (`python3 <plugin>/scripts/agk/kit_root.py governance` (`<plugin>` the plugin's folder); `make governance` in an installed project) fails an import from one layer into another that the allowed directions below do not list.

Its required parts (amendment 204, brief #1595): the `architecture-record` step of the same gate fails a missing
section, an outside service missing from the diagram, and a `Needs` number other than the quoted needs answer, and
the quality sections (amendment 236) a missing one, a marker or a line out of its form. A
front-door design under `docs/design/architecture/` is a slice of this record: it carries one line
`Architecture: docs/architecture.md` and adds only what its problem changes; a change to a layer, a store or a service
goes through this record's ADR.

## Context

TODO(architect): what the product is for, who uses it and what it runs beside.

## Parts

TODO(architect): each part (`- <part>: <what it does>`) and its interfaces.

## Data stores

TODO(architect): each store (`- <store>: <what it holds and for how long>`).

## Outside services

{{services}}

## Needs

The numbers are the person's quoted answer to the needs question, word for word.

- Busiest hour: TODO(architect)
- Downtime: TODO(architect)
- Cost: TODO(architect)
- Recovery time: TODO(architect)
- Logged: TODO(architect)

## Diagram

```text
TODO(architect): the parts, the data stores and each outside service above, and the data flow between them
{{drawn}}
```

## Quality scenarios

TODO(architect): one or more lines `- <attribute>: <stimulus> -> <response> (<number>)` for each need above, the attribute one of the eight quality characteristics of ISO/IEC 25010 (functional suitability, performance efficiency, compatibility, usability, reliability, security, maintainability, portability). With `[domain] packs` set, one more line for each domain constraint, its attribute the constraint's own and ending ` [<pack>.<constraint>]` (SPEC-0074 rule 8).

## Threats

TODO(architect): one line `- <flow>: <STRIDE letters>: <mitigation>` (or `accepted: <reason>` for an accepted risk) for each data flow of the diagram; a flow that carries a data item of `docs/domain/data.md` ends `(class: <class>)` (SPEC-0074 rule 8).

## Operations

TODO(architect): what is traced and what is alerted beyond the needs, one line `- traced: <what>` or `- alerted: <when>` each.

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
