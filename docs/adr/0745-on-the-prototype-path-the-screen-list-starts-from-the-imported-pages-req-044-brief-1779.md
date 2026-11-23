# ADR-0745: On the prototype path the screen list starts from the imported pages (REQ-044)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: brief #1779, SPEC-0037, amendment 219, ADR-0734, ADR-0504
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `docs/specs/`

## Context

A project that starts from a customer's prototype (`docs/guides/planning.md`, "From a prototype") has no product
requirement and no charter before plan-intake, so `design.py inventory` wrote no screen. In a sample project with a
five-page import on main at ee47218b the only map `check_design.py` accepted marked every page `out` (`ok design`), and
`design_import.py source --version i1` wrote `0 headings`: none of the customer's page text reached the plan.

## Decision

1. With no product requirement (none from REQ-101 up) and an imported version under `docs/design/imported/`, a new
   skeleton also holds one `### <page slug>` section in its Screens part for each entry of the `pages` list of the
   newest imported version's `manifest.json`: `- Sources: docs/design/imported/i<n>/files/<page>` and the Flow,
   Pattern, Links to and seven State slots empty. The slug is the file's name without its extension (a PDF page adds
   `-page-<n>`), lower case, each run of other characters one `-`, and `-2`, `-3` for a slug already used. With an
   Accepted charter too, both sets of sections are written. An existing inventory is only appended to as before
   (brief #1185), so the page sections are written on a new skeleton only.
2. `design_inventory.inventory_problems` accepts the optional `Sources` line in a screen section.
   `design_inventory.all_out_problems`, run by `check_design.py`, fails each imported version whose `map.md` has rows
   that are all `out:` while the inventory lists no screen or is absent, naming SPEC-0037 rule 15 and
   `docs/design/imported/`.
3. SPEC-0037 rules 3 and 15 change only through amendment 219, approved by the owner. The planning guide's step 1
   says that on a new project the inventory may come from the import.

## Consequences

A project on the prototype path gets a screen list to fill from the customer's pages, and the map of those pages then
carries their text into the plan's source. A project with product requirements sees no change, and its map may still
mark pages out with a reason. Files under `files/` are never copied into the inventory; only their paths are named.

## Residual

- Q-1779-1 (2026-11-23): the page sections are written on a new skeleton only, not appended to an existing inventory,
  the conservative reading of answer 1 ("writes one screen section"), as amendment 217's milestones are.
