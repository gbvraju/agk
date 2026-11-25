# ADR-0798: A signed screen list lists a new requirement as waiting, not failed (REQ-044)

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1930, SPEC-0037 rule 3 (amendment 217), SPEC-0012 rule 11 (C2), ADR-0249, ADR-0104, ADR-0252,
  ADR-0795, amendment 243
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

In a project with a signed screen list (`docs/design/inventory.md` with an `inventory` row in
`docs/design/signoffs.md`), no requirement intake could pass both of its checks: without a section for the new
requirement `check_design.py` failed it (`the requirement has no section`), and with one `intake.py check` failed C2.
An inventory pull request cannot go first either, since a section for a requirement not yet in `docs/requirements.md`
fails (`the section names no requirement`). SPEC-0037 rule 3 (amendment 217) already says a signed inventory stays as
signed when requirements land later and a section is added only by a new inventory pull request; its check sentence was
never reconciled with that. Seen live twice (the v1 acceptance run). The owner's word (2026-11-25, the steward chat,
quoted as data): "Yes, file draft briefs 1 to 5 and the first slices of SPEC-0073 and SPEC-0074".

## Decision

1. **A signed inventory waits, it does not fail.** While the inventory's current digest
   (`design_signoff.inventory_digest`) has an `inventory` row (`design_signoff.rows`), a product requirement with no
   section is no problem of `design_inventory.inventory_problems`; `design_inventory.waiting_requirements` lists them and
   `check_design.py` prints `design: rule 3: <REQ id> waits for an inventory pull request` for each and passes. A
   product requirement is `REQ-101` up in a project (`mode` init or adopt) and every requirement in the kit's own tree;
   milestone sections are unchanged.
2. **Everything else as strict as today.** An unsigned inventory, a row for another digest only, or an inventory changed
   since its sign-off is checked in full. Every other rule 3 problem fails a signed inventory too. A malformed sign-off
   table is refused naming `rule 9` and `docs/design/signoffs.md`, never read as signed.
3. **The intake check is unchanged.** C2 does not accept `docs/design/inventory.md` (`Q-ISL-1`).
4. SPEC-0037 changes only by amendment 243, applied on a person's `Approve: SPEC-0037`, never by the build.

## Consequences

A requirement intake in a project with a signed screen list merges; the inventory pull request that adds the waiting
sections changes the digest, is checked in full and needs a new `Approve: inventory <head>`. A test runs one intake
through `intake.py check` and `check_design.py` together, so a later rule that makes them disagree again fails a test.

## Residual

A requirement whose status is `dropped` is counted like any other (conservative). Recorded 2026-11-25.
