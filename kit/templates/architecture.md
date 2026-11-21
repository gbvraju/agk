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

## Stack

The stack record: {{stack_adr}}. Before writing code, read this record and the chosen stack's standards pack.
