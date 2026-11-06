# ADR-0297: merge_cleared.py runs governance on the merge before merging, and may merge the red-branch fix (REQ-046, brief 610)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0261, ADR-0273, ADR-0284, SPEC-0039, SPEC-0032
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

ADR-0261 gives the conductor one guarded merge; ADR-0273 runs governance on the merge commit after
each merge and stops on red; ADR-0284 passes the merged body to that run. Twice on 2026-11-06
(#598 and #609) a pull request whose CI had passed against an older default branch was merged after
the branch had gained a check it failed. The branch turned red after the merge, every later merge
was held (`held: the default branch is red (rule 5)`), and the red-branch fix could not merge
itself, so the owner merged it by hand. The ADR number and amendment 123 were reserved for brief
#610 in the brief.

## Decision

1. **Before the merge (amendment 123, rule 6).** After every other hold of rules 3 to 5 and 7
   passes, the command fetches the default branch and the head (`refs/pull/<n>/head`), builds the
   merge with `git merge-tree --write-tree`, makes it one commit on the fetched default branch
   (`git commit-tree`, one parent, the shape of the squash merge; an object only, no ref and no
   file of the checkout), and runs on it, in a detached worktree in a temporary folder outside the
   checkout, the same governance run as after the merge: the heavy lock with its timeout, `env -i`
   with `PATH`, `HOME`, `AGK_PR_BODY` and `AGK_RECORD_COMMENTS` (amendment 122, the Final comments
   of the records in that commit's history), `AGK_BASE=<the fetched default branch>`. Green merges as
   today. Red holds with `held: the merge with the default branch fails governance (<step>)`, exit
   3, nothing merged, recorded or filed; the step is `fetch`, `merge-tree`, `worktree`, `heavy
   lock`, `make governance` or `governance not finished` (an exception, interrupt or termination
   during the run). A merge that conflicts holds as `conflict (rule 5)`. The worktree and the folder
   are removed in every case.
2. **The red-branch fix (amendment 123, rule 5).** While the default branch is red, a pull request
   whose first `Brief:` line is exactly `Brief: #<n>`, where `<n>` is the one open issue titled
   `The default branch is red`, is not held for the red branch; every other hold, and the check of
   decision 1, still apply. Every other pull request, and every pull request while more than one
   such issue is open, stays held.
3. **Closing it (amendment 123, rule 6).** When that pull request merges and the run after the
   merge is green, the command posts one comment on the red-branch issue naming the merge commit
   and the pull request, then closes it as completed. A red run after the merge updates it as
   ADR-0273 says and leaves it open. When the close cannot be written, the merge stands and the
   line ends `: the red-branch issue cannot be closed (rule 6)`, exit 1.
4. **Rule 8.** The check of decision 1 runs governance on a tree that holds the cleared head, which
   rule 8 said happened only after the merge; amendment 123 says the check runs only on the merge
   of a cleared head with the default branch, under `env -i`, so no token reaches it. No other
   command of a pull request's head runs.

## Consequences

A cleared head that predates a new check on the default branch is held before it merges, so the
branch is not turned red by it; the conductor's next pass merges it once the head is updated. While
the branch is red, its fix merges through the same guarded command without a person. Each merge
now runs governance twice under the heavy lock, which doubles the time the `merge-cleared` lock is
held. With `auto_merge` off nothing changes.

## Residual

- 2026-11-06: the default branch can move between the check and the merge; the run after the merge
  (ADR-0273) still catches what the check could not see (due 2026-12-31).
- 2026-11-06: a red-branch issue that the command itself opened is not the router's (`is_red`), so
  the router does not close it; the command closes it only through the red-branch fix of decision
  3 (due 2026-12-31).
