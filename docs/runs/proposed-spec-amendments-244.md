# Proposed spec amendments 244 (SPEC-0039; REQ-046)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0799 (brief #1931), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` (rule 5, the hold list).
This file proposes the lines and does not edit the spec. A later pull request applies them word for word, on a person's
`Approve: SPEC-0039`; no session posts it.

The sentence (brief #1931): "The guarded merge holds two more things for the person: a pull request that adds a design
sign-off row without the listed approver's `Approve: inventory|design` line naming its head, and one that widens
`allowed` in `config/licences.toml`, which only the owner's own merge lands."

## Items

1. **SPEC-0039 rule 5, after the `spec approval` item.** Add the item: "one that adds a row to
   `docs/design/signoffs.md` (a row absent at the merge base) without the `Approve: design|inventory` line of an account
   in `spec_approvers`, never through an app of `agent_apps`, naming that row's kind, version and head, a solo
   confirmation counting as the line (`design approval`, amendment 244); a patch GitHub does not show, or a row of
   another shape, holds".
2. **SPEC-0039 rule 5, after the `protected class` item.** Add the item: "one whose diff adds an id to `allowed` of
   `config/licences.toml`, adds the file with an id outside the kit's default list, or removes it, ids compared
   case-folded; a rename, a missing patch or a line of another form holds, and removing ids only does not (`licence
   widening`, lifted only by the owner's `--owner` merge as `protected class` is, amendment 244)".

No other rule changes.
