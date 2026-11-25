# Proposed spec amendments 243 (SPEC-0037; REQ-044)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0798 (brief #1930), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md` (rule 3, its check sentence). This file
proposes the line and does not edit the spec. A later pull request applies it word for word, on a person's
`Approve: SPEC-0037`; no session posts it.

The sentence (brief #1930): "A requirement intake passes in a project with a signed screen list: while the inventory's
digest has its `inventory` sign-off row, a requirement with no section is reported as waiting for an inventory pull
request, not failed; a changed or unsigned inventory is checked in full as today."

## Items

1. **SPEC-0037 rule 3, the check sentence.** After "or an inventory in which a requirement of `docs/requirements.md` has
   neither a screen nor a `no screen:` reason" add ", except that, while the inventory's digest has its `inventory`
   row, a requirement with no section is listed as waiting for an inventory pull request and passes (amendment 243)".

No other rule changes.
