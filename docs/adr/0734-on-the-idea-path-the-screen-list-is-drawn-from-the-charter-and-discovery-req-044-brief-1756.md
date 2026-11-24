# ADR-0734: On the path from an idea, the screen list is drawn from the charter and discovery (REQ-044)

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1756, SPEC-0037, amendment 217, ADR-0504
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `skills/`, `docs/specs/`

## Context

On the path from an idea (`docs/guides/planning.md`, "From an idea") the product's requirements reach
`docs/requirements.md` only after `/agk:plan-intake`, after the design step. `design.py inventory` wrote one section
per requirement, so in a clean sample project of 2026-11-22 it wrote only the kit's three sections, each `no screen: a
rule of the kit`, and an empty Screens part; `check_design.py` printed `ok design` although the discovery document
said `- Screens: yes`. The prototype then had nothing to draw.

## Decision

1. With no product requirement (none from REQ-101 up) and an Accepted `docs/adr/<n>-project-charter.md`, a new
   skeleton keeps the kit's requirement sections and adds one `### M<n> — <the milestone line>` section for each
   milestone of the newest Accepted charter, with `- Sources:` naming the charter and each discovery document whose
   `Screens` is `yes` or `open`, and an empty Screens slot. A charter with no Milestones item is refused naming
   `docs/adr/`; a Proposed charter is not a source. With a product requirement present the skeleton is today's, and an
   existing inventory is only appended to as before (brief #1185), so a signed-off inventory stays as signed.
2. `design_inventory.inventory_problems` checks a milestone section as a requirement's, with `Sources` in place of
   `Specs`, and fails an inventory with no screen when a discovery document says `Screens: yes` or `open` outside its
   quoted blocks, naming SPEC-0037 rule 3 and `docs/design/`. With every discovery document at `Screens: no`, or
   none, an inventory with no screen passes as today.
3. The `design` skill's inventory step names the idea path's sources. SPEC-0037 rule 3 changes only through amendment
   217, approved by the owner.

## Consequences

A project on the idea path gets a screen list to fill before the prototype, and an empty one no longer passes. A
project with product requirements, or whose discovery says `Screens: no`, sees no change. The vision's "Who it serves"
is not a source (Q-1756-1, the brief's Q-W1-1).

## Residual

- Q-1756-1 (2026-11-22): the vision is not read; the charter's milestones and discovery are the sources, the
  conservative reading of the brief.
