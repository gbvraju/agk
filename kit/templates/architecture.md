# Architecture

The architecture record of this project (SPEC-0072 rule 5). The foundation build writes it once from the playbook
`{{work_type}}`; it changes only by an ADR of the project (`docs/architecture.md` is a protected path). The `layers`
step of `make governance` fails an import from one layer into another that the allowed directions below do not list.

Its required parts (amendment 204, brief #1595): the `architecture-record` step of `make governance` fails a missing
section, an outside service missing from the diagram, and a `Needs` number other than the quoted needs answer. A
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

## Layers

| Layer | Paths |
|-------|-------|
{{layers}}

## Allowed directions

{{allow}}

Any other import between two layers is refused. A new direction needs an ADR of the project that names it.

## Stack

The stack record: {{stack_adr}}. Before writing code, read this record and the chosen stack's standards pack.
