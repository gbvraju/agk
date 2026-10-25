# Proposed spec amendments 68 (SPEC-0032; REQ-039)

Date: 2026-10-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0132. The path: `docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md`. The number 68 was reserved for build (g) on #179 by the conductor.

1. **SPEC-0032 rule 5, the short line.** The person posts one comment whose first line is `Approve: SPEC-<n>`, with no commit id. It approves the spec as it was at the comment: the text at the `head_sha` of the latest `pull_request` workflow run of the pull request created before the comment (GitHub sets the time of a push; a commit's own date is the author's and is never used), and counts while the spec at the head equals that text apart from its status line. The long line `Approve: <head> SPEC-<n>` still works. A comment with no run before it counts for nothing.
2. **SPEC-0032 rule 5, the review.** A GitHub review in state `APPROVED` by an account in `spec_approvers` approves, at its own `commit_id`, the spec its first line `Approve: SPEC-<n>` names, else the one spec the pull request sets `Approved`; with two or more and no line it counts for nothing.
3. **SPEC-0032 rule 5, the `Approval:` line.** The conductor's line shows the line to paste: `Approval: SPEC-<n> <path> Draft -> Approved, waiting for a person: post "Approve: SPEC-<n>"`. The router reads this form and the old one.
4. **SPEC-0032 rule 5, the check.** `check_specs.py` takes the saved runs (`--runs`); the `governance` workflow saves them beside the comments.
