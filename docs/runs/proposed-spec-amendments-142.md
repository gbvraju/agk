# Proposed spec amendments 142 (SPEC-0030 and SPEC-0021; REQ-037)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0361 (brief #775), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0030-a-conductor-role-reviews-every-pull-request-posts-the-verdic.md` and
`docs/specs/0021-when-a-fix-list-verdict-s-only-item-is-the-final-commit-and.md`. The number 142 is the one brief #775
reserved. This amendment is not applied to the spec text in this pull request; the owner decides it, and it needs a
person's `Approve: SPEC-0030` and `Approve: SPEC-0021`; no session posts them.

1. **SPEC-0030 rule 4, the `Contexts:` line.** A brief also has exactly one line `Contexts:` stating each of the contexts
   `kit` (AGK's own repository), `github` (a project in GitHub mode), `local` (local mode), `personal` (personal mode) and
   `stacks` (a project with more than one stack), each with how the change works there or `not applicable: <reason>`.
   Entries are `<names> (<how>)` or `<names>: <how>`, separated by top-level semicolons; names may be grouped.
   `check_brief.py` refuses a brief without the line or with a context missing, naming the rule and the context, never the
   text. A red-branch brief of the router needs none.
2. **SPEC-0030 rule 4, the spec section.** `check_specs.py` refuses a new spec, a spec whose status changes and an amended
   Approved spec without a `## Contexts` section stating every context. A spec Approved before this rule is not refused
   until it is next amended.
3. **SPEC-0030 rule 3, the owner's hold.** `session.py plan`, `next` and `claim` skip a brief with `held by the owner:
   <reason>` when a comment on it by a person in `spec_approvers` has the first line `Hold: #<brief> <reason>`; a later
   first line `Release: #<brief>` by an approver ends the hold, and the latest such line decides. `plan` prints one `HELD:`
   line per held brief and one `HOLD IGNORED:` line per `Hold:` by anyone else, and the conductor's report carries both.
4. **SPEC-0030 rule 6, the review.** A change of behaviour in a context the brief's line marks `not applicable` is a fix
   list item citing rule 4.
5. **SPEC-0021 rule 1.** Such an item is a numbered item, so the fix list that holds it is not covered and clears no final
   commit in advance.
