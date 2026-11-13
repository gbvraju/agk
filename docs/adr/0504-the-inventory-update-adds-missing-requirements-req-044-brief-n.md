# ADR-0504: The inventory update adds missing requirements

- Status: Accepted
- Date: 2026-11-13
- Deciders: maintainers
- Related: SPEC-0037, brief #456, brief #1185, plan #661
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

`design.py inventory` wrote `docs/design/inventory.md` once and refused when the file existed, and it left every
requirement's `- Screens:` slot empty, the kit's own REQ-001 to REQ-099 included. The prototype path writes the
inventory first (the import map names its screens and states, SPEC-0037 rule 15) and the plan's intake adds REQ-101 and
up later. In the co-owner's trial of 2026-11-13, `check_design.py` rule 3 then failed for each new requirement with no
section and for each kit requirement with neither a screen nor a no-screen reason, and the only way on was to edit the
inventory by hand.

## Decision

1. `design.py inventory` on an existing inventory keeps every line of the file and only appends, at the end of the
   Requirements part and in number order, a `### REQ-<n> — <title>` section with `- Specs:` and an empty `- Screens:`
   for each requirement of `docs/requirements.md` that has none, printing one `added REQ-<n>` line each. It never
   removes or rewrites a section, and a second run adds nothing.
2. An existing file with no `## Requirements` part is refused, naming the rule, and is left unchanged.
3. On a new inventory and on an update alike, a kit requirement (REQ-001 to REQ-099, `PROJECT_FIRST_REQ` of
   `common.py`) reads `- Screens: no screen: a rule of the kit` instead of an empty slot. A project requirement's slot
   is never filled: the check, not the script, decides that the inventory is complete.
4. `docs/guides/planning.md` step 6 names the one `design.py inventory` run after the intake.
5. `check_design.py` rule 3 is unchanged. `design_inventory.py` gains only `sectioned_requirements(text)`, which the
   update reads.

## Consequences

After the intake one `design.py inventory` run leaves only the new requirements' `Screens:` slots to fill, and the
design check passes once they are filled, with no hand-built sections. The kit-only test of brief #456 now uses invented
project requirements REQ-101 to REQ-103, since REQ-001 to REQ-003 are the kit's and no longer get an empty slot, and its
refusal test names the missing Requirements part.

## Residual

- 2026-11-13: a requirement retired or removed from `docs/requirements.md` keeps its section, which the check reports
  as naming no requirement; the person removes it by hand (due 2027-01-31).
