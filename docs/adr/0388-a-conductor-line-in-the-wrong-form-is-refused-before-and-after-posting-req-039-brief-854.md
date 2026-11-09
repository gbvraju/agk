# ADR-0388: A conductor line in the wrong form is refused before and after posting

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0178, ADR-0330, ADR-0310, brief #854, conductor catch log rows 24 and 25
- Requirements: REQ-039

Protected classes: `.claude/`, `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Three merges were blocked by a conductor line that AGK would not read: a `Final:` line naming a path twice over, and a
`Verdict: fix list` with no items on a pull request with no Proposed ADR, twice. `conductor.py check-verdict` existed but
nothing refused a post that skipped it. Three briefs stayed open after their pull request merged, four builders reserved
another brief's ADR number, and the plan could not offer the fix of a red default branch. The review checklist changes on
conductor catch log rows 24 and 25, which record these incidents.

## Decision

1. `conductor.py check-verdict FILE [--pr N]` reads a line by one check. It refuses, by the rule's name and never a value,
   a first line that is neither a verdict with a sha nor a `Correction:` with text (a `Final:` first line is read by
   nothing), an `Approval:` line of another shape, the problems of `common.verdict_problem`, and with `--pr` a verdict on
   another head, a `Final:` path the head does not have, and a fix list with no numbered item and no `Final:` line on a pull
   request with no Proposed ADR (it must be `cleared`). A read that fails is an error, never `ok`.
2. `conductor_guard.py` refuses a comment whose first line starts `Verdict:`, `Final:` or `Correction:` unless that check
   accepts it. For a comment on an issue of the origin repository the guard reads the pull request with GET, the one network
   read of the guard; a read that fails denies the post.
3. The router reads the same lines as they stand on each routing. A line it cannot read, while it is the newest conductor
   line, sets `agk:review` (this replaces brief 238 answer 2, under which the reply changed no label), with one comment
   `Unreadable: <rule> (comment <id>)`. A line that `Correction needed:` already answers gets no second comment. A read that
   fails after posting flags nothing: the merge guard fails closed.
4. On a merge the router closes the brief named by `Finishes: #n` or by `Closes #n` beside `Brief: #n` of the same number.
   The checklist says that the last pull request of a brief without either line is a fix item.
5. `session.py claim` and `next --take` write the brief's own `Reserved:` numbers and refuse one that an open pull request of
   another brief adds, an earlier open brief reserves, or a live take of another brief holds, naming both. A brief with no
   `Reserved:` line takes the next free numbers, which now step over every open brief's `Reserved:` numbers.
6. The red-branch issue the router opens is a record, not a brief: the brief rules do not read it and the plan offers it. A
   brief that fixes a red default branch carries `Wave:` of the current wave.
7. The plan reads the merged pull requests for the merge rate while the branch is red. The merge-queue limit stays off for the
   red-branch fix, so that the fix is offered at once.
8. `conductor.py sweep` prints `HELD VERDICT #<n>` for a head with a ready `Report:`, green checks and no verdict when that
   report and the conductor's last comment are older than 15 minutes. A refused session merge never holds a verdict.
9. The rule budget does not grow (ADR-0310): the words added to `.claude/agents/conductor.md` and
   `config/review-checklist.md` are removed from the same files with their meaning kept.

## Consequences

A wrong line is refused before it reaches a pull request, and one that gets through is visible at the conductor's next pass.
Each verdict posted through the guard costs one to three GET requests. Two sessions can no longer write the same reserved
number. An old `Verdict:` line that was not read at its head is flagged only for its shape.

## Residual

- 2026-11-09: a `Final:` first line edited into a good line is read on the next routing, not by the edit's own event when the
  workflow's filter does not start on it; the workflow is unchanged.
- 2026-11-09: a read that fails after posting flags nothing, so a wrong line may wait for the next routing.
- 2026-11-09: of two open briefs that reserve one number, the earlier may be claimed and the later is refused, the plan's own
  reading (Q-854-1).
