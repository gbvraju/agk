# ADR-0132: Approving a spec without typing a commit id (REQ-039, build (g) of SPEC-0032)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0122, ADR-0137
- Requirements: REQ-039

Protected classes: `.github/`, `.claude/`, `scripts/agk/`, `tests/kit/`

## Context

Build (g) of SPEC-0032 on #179 (assigned to `builder-c` on #204; ADR-0132 and amendment 68 were reserved on #179). The maintainer approved the direction: "dropping the commit id is fine if it has no use; if it has meaning, find
the best way to take the reviewer's approval without manual errors or effort". The id of `Approve: <sha> SPEC-<n>` has one use: it pins the text that was approved. That pin can be derived from the pull request's own
history, so the person need not type it. The tests were written first (`tests/kit/test_approve_short.py`; before the code 11 of its 24 cases failed).

## Decision

1. **The short line.** A first line `Approve: SPEC-<n>` of a comment by an account in `spec_approvers` approves the spec as it was at the comment: the text of the last commit that precedes the comment in the saved
   timeline of the pull request. It counts while the spec at the head equals that text apart from its status line (`unchanged_since`, as for the long line); a later commit that changes only other files, or only the
   status line, does not matter. Only the order of the timeline events is used, never a commit date (a commit's dates are set by its author). A comment that is not in the timeline, a comment before every commit and an
   unreadable timeline count for nothing (fail closed).
2. **The long line** `Approve: <sha> SPEC-<n>` is checked as before.
3. **The review.** A GitHub review in state `APPROVED` by a listed approver approves, at its own `commit_id`, the spec its first line `Approve: SPEC-<n>` names, else the one spec the pull request sets `Approved`; with
   two or more and no named line it counts for nothing. A review in any other state counts for nothing as a review (its body's long line still counts as before). Today GitHub refuses an author's review of their own pull
   request, so this path waits for the separation of accounts (lane F).
4. **The wiring.** `check_specs.py` takes `--timeline FILE`; the `governance` workflow saves the timeline beside the comments and reviews (`issues/<n>/timeline`, `issues: read`, already granted) and passes it, and
   writes `[]` when the call fails or the event is not a pull request. `reviewers.py` (`approval_shas`, `person_approvals`) gives the clearance check and the router the same reading, so the label `agk:approve` and
   `check_final_clearance.py` accept the short line and an approving review. The conductor role file and the guide show the exact line to paste: `Approval: SPEC-<n> <path> Draft -> Approved, waiting for a person: post
   "Approve: SPEC-<n>"`; the router reads this line and the old one.
5. Amendment 68 (`docs/runs/proposed-spec-amendments-68.md`) is applied to SPEC-0032 rule 5. A flow-mode fragment `changelog.d/req-039-approve-short.md` records the change. The pull request changes
   `.github/workflows/`, so the maintainer merges it.

## Readings taken where the brief leaves a point open

Recorded as questions in the pull request, the most conservative reading each: the timeline of GitHub lists the commits of the pull request and its comments in one order, and a `committed` event carries `sha` and no
push time, so the order of the events stands for "pushed after the comment" (verify: that the REST timeline lists a pushed commit after an earlier comment and keeps the order of later pages; a reading that fails is closed,
the long line then works); the pin of the short line is checked by `check_specs` in `governance` only, where the timeline is saved, and the router and the clearance check ask only whether a listed person approved the
spec, because they do not read the timeline; a review in state `APPROVED` with a body that is not an `Approve:` line still approves the one spec of a pull request that sets one.

## Consequences

- A person approves with one short line and cannot mistype a sha; an approval stops counting by itself when the spec changes after it.
- A person who edits the spec after approving must approve again; a push that touches only other files does not cost the approval.
- The residual of one account (SPEC-0032 rule 6) is unchanged.

## Residual

- 2026-10-25: the order of the REST timeline is relied on, not measured on a pull request with many pages of events (due 2026-12-31).
- 2026-10-25: the router and the clearance check do not pin the short line; only `check_specs` does (due 2026-12-31).
