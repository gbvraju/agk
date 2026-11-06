# Proposed spec amendments 123 (SPEC-0039; REQ-046)

Date: 2026-11-06 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0297 (brief #610), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 123 is the one
reserved for brief #610 in the brief. This amendment is applied to the spec text in the same pull request. It needs a
person's `Approve: SPEC-0039` on the pull request; no session posts it.

1. **Governance on the would-be merge, before the merge (rule 6).** Before the merge, after every hold of rules 3 to 5
   and 7 passes, the command fetches the default branch and the head (`refs/pull/<n>/head`), builds their merge with
   `git merge-tree --write-tree` as one commit on the fetched default branch (`git commit-tree`, one parent, the shape
   of the squash merge; an object only, no ref and no file of the checkout), and runs on it, in a detached worktree in a
   temporary folder outside the checkout, the same governance run as after the merge (the heavy lock, `env -i` with
   `PATH`, `HOME`, `AGK_PR_BODY` and, after amendment 122, `AGK_RECORD_COMMENTS`), with
   `AGK_BASE=<the fetched default branch>`, then removes both in every case.
   Green merges. Red, or a step that cannot run, holds with `held: the merge with the default branch fails governance
   (<step>)`, exit 3, and nothing is merged, recorded or filed; a conflict holds as `conflict` (rule 5).
2. **The red-branch fix (rule 5).** While the default branch is red, a pull request whose first `Brief:` line is
   exactly `Brief: #<n>`, `<n>` being the one open issue `The default branch is red`, is not held for the red branch;
   every other hold and the check of item 1 still apply. Every other pull request stays held, and with more than one
   such issue open nothing merges.
3. **Closing the red-branch issue (rule 6).** When that pull request merges and the run after the merge is green, the
   command posts one comment on the issue naming the merge commit and the pull request, then closes it as completed. A
   red run after the merge updates the issue as before and leaves it open. A close that cannot be written leaves the
   merge in place, and the line of rule 2 ends `: the red-branch issue cannot be closed (rule 6)`, exit 1.
4. **Rule 8.** Its parenthesis "governance runs only on the default branch after the merge, by rule 6" becomes
   "governance runs only on the merge of the cleared head with the default branch, before the merge and after it, by
   the bounded run of rule 6". No other command of a pull request's head runs.
5. **Tests.** The Tests line of rules 6 and 7 gains the cases of brief #610 answer 4.
