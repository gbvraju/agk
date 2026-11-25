# ADR-0799: The guarded merge holds an unapproved design sign-off row and a widened licence list (REQ-046)

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1931, SPEC-0039 rule 5 (the hold list), SPEC-0037 rules 3 and 9, ADR-0265, ADR-0449, ADR-0483,
  ADR-0570, ADR-0676, ADR-0684, amendment 244
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The v1 acceptance run (#1772, IB-11 and IB-16) found two things that the guarded merge let through with no person. A
pull request that added a design sign-off row to `docs/design/signoffs.md` merged without the listed approver's
`Approve: inventory|design` line, because `check_final_clearance.py` counts that line only with `--comments`, which
local governance and the merge's own governance run never pass. And a pull request that widened `allowed` in
`config/licences.toml` merged on a covered fix list, because no hold names that file. The owner's word (2026-11-25, the
steward chat, quoted as data): "Yes, file draft briefs 1 to 5 and the first slices of SPEC-0073 and SPEC-0074".

## Decision

1. **`design approval`.** After `spec approval`, `merge_cleared.hold_list` holds a pull request when a row it adds to
   `docs/design/signoffs.md` has no `Approve: design|inventory` line by an account in `spec_approvers` naming that
   row's kind, version and head. An added row is one in the file's patch absent from its removed rows (the merge base),
   read by `design_signoff.parse_rows`. It is judged by `check_final_clearance.rows_unapproved`, the governance step's
   own judge, over `reviewers.confirmed_comments`, so a solo confirmation counts and a line posted through an app of
   `agent_apps` never does. A missing patch, a row of another shape or a malformed `agent_apps` holds (fail closed).
   The hold is not owner-only: `--owner` never lifts it. A pull request that adds no row is not held (`Q-MH-1`).
2. **`licence widening`.** A pull request holds, owner-only like `protected class`, when its patch of
   `config/licences.toml` adds an id to `allowed` that it does not remove, adds the file with an id outside the kit's
   `DEFAULT` (`gates/licences.py`), or removes the file (absent is `DEFAULT`) over a list that lacked a default id. Ids
   are compared case-folded. A rename, another status, a missing patch or a changed line that is not part of the
   `allowed` list holds (fail closed). Removing ids only does not hold. The owner's `--owner` merge lands it, and no
   new first line is added (`Q-MH-2`).
3. **What does not change.** Every other hold, its order and its words; the hosted workflow's `check_final_clearance`
   step; the conductor guard; the router; no label, check or API call is added. A hold names the rule and the class,
   never an id or a sha (principle 8).
4. SPEC-0039 rule 5 changes only by amendment 244, applied on a person's `Approve: SPEC-0039`, never by this build.

## Consequences

A screen list or prototype sign-off, and a wider licence list, no longer merge without the person, in hosted and local
mode alike. The merger and the governance step share one judge of an added row, so a later line kind added to one is
added to both.

## Residual

The licence hold reads the patch, not the files at both ends, so a line that adds an id already on an unchanged line
holds when it need not (conservative). A head file of another form holds rather than being refused: the file is data
of the pull request, and `licences.py` refuses it in governance.
Recorded 2026-11-25.
