# ADR-0446: A customer's click-through prototype is imported unchanged as a signed-off design version

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: SPEC-0037, SPEC-0029, amendment 161, brief #1056, plan #661
- Requirements: REQ-044, REQ-036

## Context

A project may start from a click-through prototype that its customer made, and the owner asked that it be delivered with
AGK "without losing anything" (brief #1056). On the default branch SPEC-0037 builds a prototype only from the kit:
`design_prototype_check.py` fails any page with a script other than the kit's runtime, a stylesheet other than
`standard.css` and `theme.css`, a colour outside the tokens or data outside the fixture set (rules 5 to 7), sign-off
(`reviewers.py` `APPROVE_DESIGN`, `design_signoff.py`) and the comparison (`design_compare.py`) read only `v<n>`, and
rule 13 keeps reference material out of a prototype. A customer's prototype can therefore only be kept as reference and
redrawn by hand, and nothing proves that each of its screens reached the inventory.

## Decision

1. `/agk:design import <folder>` copies the folder byte for byte into a new imported version
   `docs/design/imported/i<n>/files/`, the next free number, never overwritten, and writes `manifest.json` (each file's
   path, size and SHA-256, and one digest of the list) and `external.txt` beside it (amendment 161 items 1 and 3).
2. `map.md` maps every page and picture page of the import to a screen and state of the inventory, or out with a reason;
   the check fails an unmapped page, an unknown file, screen or state, an `out:` row with no reason, and an inventory
   state marked `yes` that neither an imported nor a kit page covers (item 2).
3. The manifest and map checks replace rules 5 to 7 for an imported version, whose pages no check or workflow ever runs;
   rule 13 still holds outside `docs/design/imported/` (item 3).
4. `Approve: design i<n> <full head ID>` by an account in `spec_approvers` freezes the imported version as rule 9 freezes
   a kit version; any later change is a new version `i<n+1>` (item 4).
5. A UI brief's `Screens:` line may name `i<n>`, and `design_compare.py --version i<n>` compares a build with it by
   pixels and visible text only, offline, `pixels: not run` without a browser (item 5).
6. A project may hold kit versions and imported versions side by side; the guides say when to import and when to draw
   (item 6).

## Consequences

A customer's prototype becomes the signed-off design itself, held by its digest, and the map turns "nothing lost" into a
check. Imported pages are never held to the kit's standard (tokens, accessibility, fixture data), so those guarantees
apply only to kit versions and to what the builds produce. This pull request changes documents only; four builds follow
from the default branch after the owner's `Approve: <head> SPEC-0037`, each with its own ADR naming the protected classes
it changes: (a) the import and the map check, (b) the sign-off, (c) the `Screens:` line and the comparison, (d) the guides
and doctor.

## Residual

- 2026-11-11: an imported prototype may hold real names and data of the customer; no check can tell them from invented
  ones, so what may be committed to the project's repository is the person's call before the import; the secret scan
  runs over the copy like any tracked file, with no ignore entry (due 2026-12-31).
- 2026-11-11: imported pages are not checked for accessibility, tokens or data; a build compared with them inherits
  whatever they lack, and only the person's review catches it (due 2026-12-31).
- 2026-11-11: the comparison renders a customer's page in a headless browser, which runs its scripts; it is held offline
  and to the version folder by `design_compare.py`, a kit-only script the builder runs, never a check or a workflow
  (due 2026-12-31).
- 2026-11-11: the version prefix, PDF and exported frames, `external.txt` and sign-off, the tolerance and the copy layout
  are the owner's (`Q-S0037-12` to `Q-S0037-19`) (due 2026-11-30).
