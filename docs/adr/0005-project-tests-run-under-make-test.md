# ADR-0005: Project tests run under make test

- Status: Proposed
- Date: 2026-10-14
- Deciders: maintainers
- Related: ADR-0004
- Amends: ADR-0004
- Requirements: REQ-009

## Context

ADR-0004 decision 6 adopted the installer of SPEC-0001. The `Makefile` it shipped ran only `tests/kit` (and
`tests/kit_dev` in the kit), so an installed repository's `make test` ignored the project's own tests. Found
while preparing the live proof. ADR-0004 is Accepted and immutable except its Status, so this ADR amends it.

Protected classes: `Makefile`, `pyproject.toml`, `kit/`, `tests/kit_dev/`.

## Decision

1. The `Makefile` `test` target runs `$(PY) -m pytest tests -q`. This amends the Makefile part of ADR-0004
   decision 6: installed repositories run `tests/kit` and the project's own tests, the kit runs `tests/kit` and
   `tests/kit_dev`.
2. `testpaths` is `["tests"]` in this repository's `pyproject.toml` and in `kit/templates/pyproject.toml`.
3. `tests/kit_dev/` gains tests that a sample project test is collected and run by `make test` and that a failing
   one makes it fail, and a test that the Makefile target and both `testpaths` stay as decided.
4. SPEC-0001 rule 18 is amended accordingly, applied on maintainers' instruction (`docs/runs/proposed-spec-amendments-1.md`).

## Consequences

- A project cannot add tests that `make test` silently skips.
- A project test file named like a kit test (`test_*.py` basename) under `tests/` can collide with it; projects
  should keep distinct basenames.

## Residual

- 2026-10-14: approved specs are not yet protected by a check (ADR-0004 residual, principle 6).
