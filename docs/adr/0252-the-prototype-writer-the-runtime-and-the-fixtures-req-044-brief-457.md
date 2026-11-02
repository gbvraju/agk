# ADR-0252: the prototype writer, the kit's runtime and the fixture set (REQ-044, brief 457)

- Status: Proposed
- Date: 2026-11-02
- Deciders: maintainers
- Related: ADR-0204, ADR-0248, ADR-0249, SPEC-0037
- Requirements: REQ-044

Protected classes: `kit/`, `scripts/agk/`, `skills/`, `tests/kit_dev/`

## Context

SPEC-0037 (Approved; ADR-0204) has a design phase deliver a click-through prototype (rules 4 to 6), drawn only from an
agreed inventory (rule 3) and carrying an existing theme over (rule 12). Brief #457 is build (c) of rule 14, after the
standard (#455, ADR-0248) and the inventory and sign-off record (#456, ADR-0249). The person ruled on 2026-10-30 that
the prototype uses the kit's own small, hashed, offline navigation runtime with a state bar and demo mode on every
screen (ruling 1), and that v1 is regenerated from the inventory with the theme carried over (ruling 3). ADR-0204
decision 3 names the classes the builds change; this ADR names the ones this build changes, because the protected-path
check counts only an ADR of the same pull request (`Q-S0037-9`).

## Decision

1. (filled in as the build proceeds)

## Consequences

(filled in as the build proceeds)
