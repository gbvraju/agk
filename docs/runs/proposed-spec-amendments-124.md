# Proposed spec amendments 124 (SPEC-0039, SPEC-0032; REQ-046)

Date: 2026-11-06 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0304 (brief #628), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` and
`docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md`. The number 124 is the one
reserved for brief #628 in the brief. This amendment is applied to the spec texts in the same pull request. It needs a
person's `Approve:` on the pull request; no session posts it.

1. **SPEC-0039 rule 5 (`spec approval`).** An `Approve: <sha> SPEC-<n>` line by an account in `spec_approvers` counts for
   the head when the spec file's text at the head equals its text at `<sha>`, apart from its first `- Status:` line going
   from `Draft` to `Approved`, and nothing else; files other than the spec may change between `<sha>` and the head. An
   unreadable blob, a renamed spec, an approved sha that is not the head or an ancestor of it counts as unapproved.
2. **SPEC-0032 rule 5.** The person's `Approve: <head> SPEC-<n>` approves the text of the spec at that head; it stays the
   approval of a later head of the same pull request while the spec's text is unchanged by the same rule as item 1, so a
   merge of the default branch or the status commit needs no new approval.
3. **Tests.** The Tests line of SPEC-0039 rule 5 gains the cases of brief #628 answer 5.
