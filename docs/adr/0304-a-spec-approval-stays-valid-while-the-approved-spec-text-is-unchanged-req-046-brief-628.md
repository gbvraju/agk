# ADR-0304: A spec approval stays valid while the approved spec text is unchanged (REQ-046, brief 628)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0261, ADR-0265, ADR-0297, SPEC-0039, SPEC-0032
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

`merge_cleared.py` held a pull request with an `Approval: SPEC-<n>` line unless a spec approver's
`Approve: <sha> SPEC-<n>` named its current head (SPEC-0039 rule 5, `spec approval`). On
2026-11-06 the owner posted a second approval on #592, #603, #616 and #627 because the head had
moved (a merge of the default branch, or the conductor's `Status: Approved` commit) although the
spec text had not changed (conductor catch log row 14, #605, kind `kit-gap`). The CI reader,
`check_specs.py`, already compared the spec text at the approved sha with the head, but allowed any
change of the status line and did not ask the approved sha to be in the head's history. The ADR
number and amendment 124 were reserved for brief #628 in the brief.

## Decision

1. **One text, one approval (amendment 124, SPEC-0039 rule 5 and SPEC-0032 rule 5).** An
   `Approve: <sha> SPEC-<n>` by an account in `spec_approvers` counts for the current head when the
   spec file's text at the head equals its text at the approved sha, or differs only in that its
   first `- Status:` line is `- Status: Draft` at the sha and `- Status: Approved` at the head
   (`common.status_flip_only`). Any other change of the spec file needs a new approval.
2. **Other files may change.** A merge of the default branch and the ruling files under
   `docs/runs/decisions/` change files other than the spec; the conductor's verdict on the head
   reviews them, as today.
3. **Fail closed.** In `merge_cleared.py` the approved sha must resolve to a commit that is the
   head or an ancestor of it, the head must be readable (it is fetched from `refs/pull/<n>/head`,
   the ref the check before the merge of amendment 123 already fetches, only when it is not already
   present), and the spec must be the one file `docs/specs/<nnnn>-*.md` at the head and exist at
   the same path at the approved sha. An unreadable blob, a renamed spec, two files of one number,
   an unknown sha or one outside the history counts as unapproved (`spec approval (rule 5)`).
   `check_specs.py` adds the same history rule and the same one allowed difference. An approval
   that names the head exactly still counts without reading git, as before.
4. **Unchanged.** Who may approve, the `agk:approve` label hold, the short form `Approve:
   SPEC-<n>` (which `merge_cleared.py` still does not count, having no runs to pin it), the routing
   labels and `check_final_clearance.py` (which read approvals without a sha) do not change.

## Consequences

A merge of main or the status commit no longer asks the owner to approve the same text again; the
conductor's next pass merges once the rest is green. A text change of the spec still needs a new
approval, in both readers. The command now runs up to four local `git` reads per approval line
that does not name the head, and at most one fetch that the check before the merge makes anyway.

## Residual

- 2026-11-06: the check compares only the spec file; a change elsewhere that alters what the spec
  means (a referenced file, a requirement text) is the conductor's verdict to catch, as before
  (due 2026-12-31).
