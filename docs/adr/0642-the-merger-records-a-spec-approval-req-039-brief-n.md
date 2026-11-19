# ADR-0642: The merger records a spec approval in the merge (REQ-039)

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: brief #1520, Q-1418-1, #1511, brief #797, brief #628, ADR-0304, ADR-0373, SPEC-0021 rule 3a
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

A cloud builder cannot make the one-line `- Status: Draft` -> `Approved` commit of a spec its owner approved (Q-1418-1 on
#1511), and the merger holds such a head twice: `route.py` labels it `agk:approve` (brief #797 answer 4), which
`merge_cleared.py` holds as `spec approval`, and `merge_cleared.py` holds it as `an approved spec still reads Draft`. The
owner's answer: the merger records the approval in the merge, as it records an ADR's `Final:` accept.

## Decision

1. With `[flow] auto_merge = true` and `merge_queue` off, for each spec the pull request adds or changes that reads
   `Draft` at the head and that a `spec_approvers` account approved for the head's text (`Approve: <sha> SPEC-<n>`, or
   `Approve: SPEC-<n>` pinned to the head of the latest `pull_request` run before it, the text kept apart from the
   status flip, ADR-0304), the squash message gains `SPEC-nnnn Approved (Approve <comment id>)` beside the ADR lines
   and `Merged-by: merge_cleared.py`, and neither hold applies to it. A spec read as approved whose approval does not
   pin the head's text still holds. With `auto_merge` off (`--owner`) or `merge_queue` on (GitHub writes that squash
   message), both holds stay as before. A body or commit that already holds such a line is held.
2. `common.approval_records(root, ref)` reads those lines with the squash-commit rule of `final_records`, and
   `common.approved_specs(root, ref)` is each spec whose file at REF says Approved or that a record names.
3. `check_specs.py` counts a recorded spec as Approved: rule a, rule (1) (a change other than the status flip needs an
   amendment) and rule 5 (the flip of a recorded spec needs no new `Approve:` line). `check_specs.py --pending` lists
   each recorded spec whose file still says Draft; the release pull request flips it.
4. `route.py` gives such a head its other label, not `agk:approve`, under the same settings.

## Consequences

An approved intake merges as Draft with its approval in the merge commit, and a build of its requirement passes rule a.
Local mode and GitHub mode alike (the record is in the merge commit). Personal mode is not applicable (SPEC-0041 rule
15). With `spec_approvers` still `@REPLACE-ME` no approval counts, so no record is written.

## Residual

`facts.py` still shows such a spec as Draft until the release flips it (Q-1520-1, 2026-11-19).
